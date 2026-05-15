"""
Document processing service with full PDF ingestion pipeline.
"""
import time
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.schemas import (
    PaperUploadResponse,
    PaperInfo,
    PaperMetadata,
    DocumentChunk,
)
from app.services.embedding_service import EmbeddingService
from app.processing.pdf_extractor import PDFExtractor
from app.processing.preprocessor import TextPreprocessor
from app.processing.text_chunker import TextChunker
from app.core.config import settings
from app.utils.logger import app_logger


class DocumentService:
    """Service for document processing and management."""
    
    def __init__(
        self,
        es_client,   # QdrantVectorStore or any compatible store
        embedding_service: EmbeddingService,
    ):
        """
        Initialize document service.
        
        Args:
            es_client: Elasticsearch client
            embedding_service: Embedding service
        """
        self.es_client = es_client
        self.embedding_service = embedding_service
        self.pdf_extractor = PDFExtractor()
        self.preprocessor = TextPreprocessor()
        self.chunker = TextChunker()
        
        # Ensure upload directory exists
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        app_logger.info("DocumentService initialized with full pipeline")
    
    async def process_document(
        self,
        file_content: bytes,
        filename: str,
    ) -> PaperUploadResponse:
        """
        Process uploaded document through full pipeline.
        
        Pipeline:
        1. Save file to disk
        2. Extract text and metadata from PDF
        3. Preprocess and clean text
        4. Detect sections
        5. Chunk text semantically
        6. Generate embeddings for chunks
        7. Index in Elasticsearch
        
        Args:
            file_content: PDF file content
            filename: Original filename
            
        Returns:
            Upload response with paper ID and metadata
        """
        start_time = time.time()
        paper_id = str(uuid.uuid4())
        
        try:
            app_logger.info(f"Processing document: {filename} (paper_id: {paper_id})")
            
            # Step 1: Save file
            file_path = self.upload_dir / f"{paper_id}_{filename}"
            file_path.write_bytes(file_content)
            app_logger.info(f"Saved file to: {file_path}")
            
            # Step 2: Extract text and metadata
            try:
                raw_text, page_map = self.pdf_extractor.extract_text(file_path)
                metadata = self.pdf_extractor.extract_metadata(file_path, raw_text)
                app_logger.info(f"Extracted {len(raw_text)} characters from {len(page_map)} pages")
            except Exception as e:
                app_logger.error(f"PDF extraction failed: {e}")
                return PaperUploadResponse(
                    paper_id=paper_id,
                    filename=filename,
                    status="failed",
                    message=f"Failed to extract text from PDF: {str(e)}",
                    metadata=PaperMetadata(),
                    num_chunks=0,
                    processing_time=time.time() - start_time,
                )
            
            # Step 3: Preprocess text
            cleaned_text = self.preprocessor.clean_text(raw_text)
            
            # Remove references section (not useful for retrieval)
            cleaned_text = self.preprocessor.remove_references_section(cleaned_text)
            
            app_logger.info(f"Cleaned text: {len(cleaned_text)} characters")
            
            # Step 4: Detect sections
            sections = self.preprocessor.detect_sections(cleaned_text)
            
            if not sections:
                # If no sections detected, use full text
                sections = {"full_text": cleaned_text}
                app_logger.warning("No sections detected, using full text")
            
            # Step 5: Chunk text
            chunks = self.chunker.chunk_by_sections(
                text=cleaned_text,
                paper_id=paper_id,
                sections=sections,
                page_map=page_map,
            )
            
            if not chunks:
                app_logger.error("No chunks created")
                return PaperUploadResponse(
                    paper_id=paper_id,
                    filename=filename,
                    status="failed",
                    message="Failed to create chunks from document",
                    metadata=metadata,
                    num_chunks=0,
                    processing_time=time.time() - start_time,
                )
            
            app_logger.info(f"Created {len(chunks)} chunks")
            
            # Step 6: Generate embeddings
            chunk_texts = [chunk.text for chunk in chunks]
            
            try:
                embeddings = self.embedding_service.embed_documents(chunk_texts)
                app_logger.info(f"Generated {len(embeddings)} embeddings")
            except Exception as e:
                app_logger.error(f"Embedding generation failed: {e}")
                return PaperUploadResponse(
                    paper_id=paper_id,
                    filename=filename,
                    status="failed",
                    message=f"Failed to generate embeddings: {str(e)}",
                    metadata=metadata,
                    num_chunks=len(chunks),
                    processing_time=time.time() - start_time,
                )
            
            # Attach embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
            # Step 7: Index in Elasticsearch
            paper_metadata_dict = metadata.model_dump(exclude_none=True)
            
            try:
                indexed_count = await self.es_client.index_chunks(
                    chunks=chunks,
                    paper_metadata=paper_metadata_dict,
                )
                app_logger.info(f"Indexed {indexed_count} chunks in Elasticsearch")
            except Exception as e:
                app_logger.error(f"Elasticsearch indexing failed: {e}")
                return PaperUploadResponse(
                    paper_id=paper_id,
                    filename=filename,
                    status="failed",
                    message=f"Failed to index in Elasticsearch: {str(e)}",
                    metadata=metadata,
                    num_chunks=len(chunks),
                    processing_time=time.time() - start_time,
                )
            
            processing_time = time.time() - start_time
            
            app_logger.info(
                f"Successfully processed {filename}: "
                f"{len(chunks)} chunks, {processing_time:.2f}s"
            )
            
            return PaperUploadResponse(
                paper_id=paper_id,
                filename=filename,
                status="success",
                message=f"Successfully processed {len(chunks)} chunks",
                metadata=metadata,
                num_chunks=len(chunks),
                processing_time=processing_time,
            )
            
        except Exception as e:
            app_logger.error(f"Unexpected error processing document: {e}", exc_info=True)
            return PaperUploadResponse(
                paper_id=paper_id,
                filename=filename,
                status="failed",
                message=f"Unexpected error: {str(e)}",
                metadata=PaperMetadata(),
                num_chunks=0,
                processing_time=time.time() - start_time,
            )
    
    async def get_paper_info(self, paper_id: str) -> Optional[PaperInfo]:
        """
        Get paper information from Elasticsearch.
        
        Args:
            paper_id: Paper ID
            
        Returns:
            Paper information or None if not found
        """
        try:
            chunks = await self.es_client.get_paper_chunks(paper_id)
            
            if not chunks:
                return None
            
            # Get metadata from first chunk
            first_chunk = chunks[0]
            paper_metadata = first_chunk.get("paper_metadata", {})
            
            # Build PaperInfo
            paper_info = PaperInfo(
                paper_id=paper_id,
                filename=f"{paper_id}.pdf",  # Reconstruct filename
                metadata=PaperMetadata(**paper_metadata) if paper_metadata else PaperMetadata(),
                num_chunks=len(chunks),
                upload_date=first_chunk.get("created_at"),
                sections=list(set(chunk.get("section") for chunk in chunks if chunk.get("section"))),
            )
            
            return paper_info
            
        except Exception as e:
            app_logger.error(f"Error getting paper info: {e}")
            return None
    
    async def list_papers(
        self,
        skip: int = 0,
        limit: int = 10,
    ) -> List[PaperInfo]:
        """
        List all papers from Elasticsearch.
        
        Args:
            skip: Number to skip
            limit: Maximum to return
            
        Returns:
            List of paper information
        """
        try:
            # Get all unique paper IDs
            paper_ids = await self.es_client.get_paper_ids()
            
            # Apply pagination
            paginated_ids = paper_ids[skip : skip + limit]
            
            # Get info for each paper
            papers = []
            for paper_id in paginated_ids:
                paper_info = await self.get_paper_info(paper_id)
                if paper_info:
                    papers.append(paper_info)
            
            app_logger.info(f"Listed {len(papers)} papers")
            return papers
            
        except Exception as e:
            app_logger.error(f"Error listing papers: {e}")
            return []
    
    async def delete_paper(self, paper_id: str) -> bool:
        """
        Delete a paper from Elasticsearch and file system.
        
        Args:
            paper_id: Paper ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            # Delete from Elasticsearch
            deleted_count = await self.es_client.delete_paper(paper_id)
            
            if deleted_count == 0:
                app_logger.warning(f"Paper not found: {paper_id}")
                return False
            
            # Delete file from disk
            for file_path in self.upload_dir.glob(f"{paper_id}_*"):
                file_path.unlink()
                app_logger.info(f"Deleted file: {file_path}")
            
            app_logger.info(f"Deleted paper: {paper_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"Error deleting paper: {e}")
            return False
    
    async def get_paper_text(self, paper_id: str) -> Optional[str]:
        """
        Get full text of a paper by concatenating chunks.
        
        Args:
            paper_id: Paper ID
            
        Returns:
            Full paper text or None
        """
        try:
            chunks = await self.es_client.get_paper_chunks(paper_id)
            
            if not chunks:
                return None
            
            # Sort by chunk index and concatenate
            sorted_chunks = sorted(chunks, key=lambda x: x.get("chunk_index", 0))
            full_text = "\n\n".join(chunk["text"] for chunk in sorted_chunks)
            
            return full_text
            
        except Exception as e:
            app_logger.error(f"Error getting paper text: {e}")
            return None
    
    async def get_paper_sections(self, paper_id: str) -> Dict[str, str]:
        """
        Get paper text organized by sections.
        
        Args:
            paper_id: Paper ID
            
        Returns:
            Dictionary mapping section names to text
        """
        try:
            chunks = await self.es_client.get_paper_chunks(paper_id)
            
            if not chunks:
                return {}
            
            # Group chunks by section
            sections = {}
            for chunk in chunks:
                section = chunk.get("section", "unknown")
                if section not in sections:
                    sections[section] = []
                sections[section].append(chunk)
            
            # Sort chunks within each section and concatenate
            section_texts = {}
            for section, section_chunks in sections.items():
                sorted_chunks = sorted(section_chunks, key=lambda x: x.get("chunk_index", 0))
                section_texts[section] = "\n\n".join(chunk["text"] for chunk in sorted_chunks)
            
            return section_texts
            
        except Exception as e:
            app_logger.error(f"Error getting paper sections: {e}")
            return {}
