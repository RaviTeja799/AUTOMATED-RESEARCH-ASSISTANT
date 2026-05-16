"""
Document processing service — optimized pipeline.

Improvements vs original:
- Embedding generation is async (non-blocking)
- PDF extraction runs in thread executor (non-blocking)
- list_papers() uses asyncio.gather() — parallel chunk fetches, no N+1
- Stale comments referencing Elasticsearch removed
"""
import asyncio
import time
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any

import aiofiles

from app.models.schemas import PaperUploadResponse, PaperInfo, PaperMetadata, DocumentChunk
from app.services.embedding_service import EmbeddingService
from app.processing.pdf_extractor import PDFExtractor
from app.processing.preprocessor import TextPreprocessor
from app.processing.text_chunker import TextChunker
from app.core.config import settings
from app.utils.logger import app_logger


class DocumentService:
    """PDF ingestion pipeline — extract → chunk → embed → index."""

    def __init__(self, es_client, embedding_service: EmbeddingService):
        self.store = es_client          # QdrantVectorStore
        self.embedding_service = embedding_service
        self.pdf_extractor = PDFExtractor()
        self.preprocessor = TextPreprocessor()
        self.chunker = TextChunker()
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        app_logger.info("DocumentService initialized")

    # ── Upload pipeline ───────────────────────────────────────────────────────

    async def process_document(self, file_content: bytes, filename: str) -> PaperUploadResponse:
        start = time.time()
        paper_id = str(uuid.uuid4())

        try:
            app_logger.info(f"Processing: {filename} ({paper_id})")

            # 1. Save file async
            file_path = self.upload_dir / f"{paper_id}_{filename}"
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_content)

            # 2. Extract PDF in thread executor (blocking I/O + CPU)
            loop = asyncio.get_event_loop()
            try:
                raw_text, page_map = await loop.run_in_executor(
                    None, self.pdf_extractor.extract_text, file_path
                )
                metadata = await loop.run_in_executor(
                    None, self.pdf_extractor.extract_metadata, file_path, raw_text
                )
            except Exception as e:
                app_logger.error(f"PDF extraction failed: {e}")
                return self._fail(paper_id, filename, f"PDF extraction failed: {e}", start)

            # 3. Preprocess in executor
            cleaned_text = await loop.run_in_executor(
                None, self._preprocess, raw_text
            )

            # 4. Detect sections in executor
            sections = await loop.run_in_executor(
                None, self.preprocessor.detect_sections, cleaned_text
            ) or {"full_text": cleaned_text}

            # 5. Chunk
            chunks = await loop.run_in_executor(
                None,
                lambda: self.chunker.chunk_by_sections(
                    text=cleaned_text,
                    paper_id=paper_id,
                    sections=sections,
                    page_map=page_map,
                ),
            )
            if not chunks:
                return self._fail(paper_id, filename, "No chunks created", start, metadata)

            # 6. Embed async (non-blocking)
            chunk_texts = [c.text for c in chunks]
            try:
                embeddings = await self.embedding_service.embed_documents_async(chunk_texts)
            except Exception as e:
                app_logger.error(f"Embedding failed: {e}")
                return self._fail(paper_id, filename, f"Embedding failed: {e}", start, metadata)

            for chunk, emb in zip(chunks, embeddings):
                chunk.embedding = emb

            # 7. Index in Qdrant
            try:
                indexed = await self.store.index_chunks(
                    chunks=chunks,
                    paper_metadata=metadata.model_dump(exclude_none=True),
                )
            except Exception as e:
                app_logger.error(f"Qdrant indexing failed: {e}")
                return self._fail(paper_id, filename, f"Indexing failed: {e}", start, metadata)

            elapsed = time.time() - start
            app_logger.info(f"Processed {filename}: {len(chunks)} chunks in {elapsed:.1f}s")
            return PaperUploadResponse(
                paper_id=paper_id,
                filename=filename,
                status="success",
                message=f"Successfully processed {len(chunks)} chunks",
                metadata=metadata,
                num_chunks=len(chunks),
                processing_time=elapsed,
            )

        except Exception as e:
            app_logger.error(f"Unexpected error: {e}", exc_info=True)
            return self._fail(paper_id, filename, f"Unexpected error: {e}", start)

    def _preprocess(self, raw_text: str) -> str:
        cleaned = self.preprocessor.clean_text(raw_text)
        return self.preprocessor.remove_references_section(cleaned)

    def _fail(self, paper_id, filename, msg, start, metadata=None) -> PaperUploadResponse:
        return PaperUploadResponse(
            paper_id=paper_id,
            filename=filename,
            status="failed",
            message=msg,
            metadata=metadata or PaperMetadata(),
            num_chunks=0,
            processing_time=time.time() - start,
        )

    # ── Read operations ───────────────────────────────────────────────────────

    async def get_paper_info(self, paper_id: str) -> Optional[PaperInfo]:
        try:
            chunks = await self.store.get_paper_chunks(paper_id)
            if not chunks:
                return None
            first = chunks[0]
            meta = first.get("paper_metadata", {})
            return PaperInfo(
                paper_id=paper_id,
                filename=f"{paper_id}.pdf",
                metadata=PaperMetadata(**meta) if meta else PaperMetadata(),
                num_chunks=len(chunks),
                upload_date=first.get("created_at"),
                sections=list({c.get("section") for c in chunks if c.get("section")}),
            )
        except Exception as e:
            app_logger.error(f"get_paper_info error: {e}")
            return None

    async def list_papers(self, skip: int = 0, limit: int = 10) -> List[PaperInfo]:
        """Parallel fetch — one gather() instead of N sequential awaits."""
        try:
            paper_ids = await self.store.get_paper_ids()
            paginated = paper_ids[skip : skip + limit]
            infos = await asyncio.gather(
                *[self.get_paper_info(pid) for pid in paginated],
                return_exceptions=False,
            )
            return [p for p in infos if p is not None]
        except Exception as e:
            app_logger.error(f"list_papers error: {e}")
            return []

    async def delete_paper(self, paper_id: str) -> bool:
        try:
            await self.store.delete_paper(paper_id)
            for fp in self.upload_dir.glob(f"{paper_id}_*"):
                fp.unlink(missing_ok=True)
            return True
        except Exception as e:
            app_logger.error(f"delete_paper error: {e}")
            return False

    async def get_paper_text(self, paper_id: str) -> Optional[str]:
        chunks = await self.store.get_paper_chunks(paper_id)
        if not chunks:
            return None
        return "\n\n".join(c["text"] for c in chunks)

    async def get_paper_sections(self, paper_id: str) -> Dict[str, str]:
        chunks = await self.store.get_paper_chunks(paper_id)
        if not chunks:
            return {}
        sections: Dict[str, List] = {}
        for c in chunks:
            sec = c.get("section", "unknown")
            sections.setdefault(sec, []).append(c)
        return {
            sec: "\n\n".join(c["text"] for c in sorted(cs, key=lambda x: x.get("chunk_index", 0)))
            for sec, cs in sections.items()
        }
