"""
Intelligent text chunking for academic papers.
Preserves semantic coherence by respecting section boundaries.
"""
import re
from typing import List, Dict, Optional
from uuid import uuid4

from app.core.config import settings
from app.models.schemas import DocumentChunk
from app.utils.logger import app_logger


class TextChunker:
    """Chunk text intelligently for embedding and retrieval."""
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        min_chunk_length: int = None
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.min_chunk_length = min_chunk_length or settings.min_chunk_length
        self.logger = app_logger
    
    def chunk_by_sections(
        self,
        text: str,
        paper_id: str,
        sections: Optional[Dict[str, str]] = None,
        page_map: Optional[Dict[int, str]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk text by sections, then by size within sections.
        
        Args:
            text: Full text to chunk
            paper_id: Unique paper identifier
            sections: Dictionary of section names to content
            page_map: Dictionary mapping page numbers to text
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        chunk_index = 0
        
        if sections:
            # Chunk each section separately
            for section_name, section_text in sections.items():
                section_chunks = self._chunk_text(
                    section_text,
                    paper_id,
                    section_name,
                    chunk_index,
                    page_map
                )
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
        else:
            # Chunk entire text
            chunks = self._chunk_text(
                text,
                paper_id,
                None,
                chunk_index,
                page_map
            )
        
        self.logger.info(f"Created {len(chunks)} chunks for paper {paper_id}")
        return chunks
    
    def _chunk_text(
        self,
        text: str,
        paper_id: str,
        section: Optional[str],
        start_index: int,
        page_map: Optional[Dict[int, str]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk a single text segment.
        
        Uses sentence-aware chunking to avoid breaking mid-sentence.
        """
        chunks = []
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence exceeds chunk size
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Create chunk from accumulated sentences
                chunk_text = " ".join(current_chunk)
                
                if len(chunk_text) >= self.min_chunk_length:
                    page_num = self._find_page_number(chunk_text, page_map)
                    
                    chunk = DocumentChunk(
                        chunk_id=str(uuid4()),
                        paper_id=paper_id,
                        text=chunk_text,
                        section=section,
                        page_number=page_num,
                        chunk_index=start_index + len(chunks),
                        metadata={
                            "length": len(chunk_text),
                            "sentence_count": len(current_chunk)
                        }
                    )
                    chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk,
                    self.chunk_overlap
                )
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_length:
                page_num = self._find_page_number(chunk_text, page_map)
                
                chunk = DocumentChunk(
                    chunk_id=str(uuid4()),
                    paper_id=paper_id,
                    text=chunk_text,
                    section=section,
                    page_number=page_num,
                    chunk_index=start_index + len(chunks),
                    metadata={
                        "length": len(chunk_text),
                        "sentence_count": len(current_chunk)
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Uses regex to handle common abbreviations and edge cases.
        """
        # Clean text
        text = re.sub(r"\s+", " ", text).strip()
        
        # Split on sentence boundaries
        # Handle common abbreviations
        text = re.sub(r"(?<=[A-Z])\.(?=[A-Z])", ".<ABBREV>", text)  # U.S.A.
        text = re.sub(r"(?<=Dr|Mr|Mrs|Ms)\.(?=\s)", ".<ABBREV>", text)
        text = re.sub(r"(?<=et al)\.(?=\s)", ".<ABBREV>", text)
        text = re.sub(r"(?<=Fig|Tab|Eq)\.(?=\s)", ".<ABBREV>", text)
        
        # Split on sentence endings
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        
        # Restore abbreviations
        sentences = [s.replace("<ABBREV>", "") for s in sentences]
        
        # Filter out very short sentences
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        return sentences
    
    def _get_overlap_sentences(
        self,
        sentences: List[str],
        overlap_size: int
    ) -> List[str]:
        """Get sentences for overlap based on character count."""
        overlap_sentences = []
        overlap_length = 0
        
        for sentence in reversed(sentences):
            if overlap_length + len(sentence) <= overlap_size:
                overlap_sentences.insert(0, sentence)
                overlap_length += len(sentence)
            else:
                break
        
        return overlap_sentences
    
    def _find_page_number(
        self,
        chunk_text: str,
        page_map: Optional[Dict[int, str]]
    ) -> Optional[int]:
        """Find which page a chunk belongs to."""
        if not page_map:
            return None
        
        # Find the page that contains the beginning of this chunk
        chunk_start = chunk_text[:100]  # Use first 100 chars
        
        for page_num, page_text in page_map.items():
            if chunk_start in page_text:
                return page_num
        
        return None
    
    def chunk_for_summarization(
        self,
        text: str,
        max_chunk_size: int = 4000
    ) -> List[str]:
        """
        Create larger chunks suitable for summarization.
        
        Args:
            text: Text to chunk
            max_chunk_size: Maximum chunk size in characters
            
        Returns:
            List of text chunks
        """
        sentences = self._split_sentences(text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > max_chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
