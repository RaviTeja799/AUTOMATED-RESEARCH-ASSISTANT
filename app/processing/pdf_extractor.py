"""
PDF text extraction with multiple fallback strategies.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import pdfplumber
from pypdf import PdfReader

from app.utils.logger import app_logger
from app.models.schemas import PaperMetadata


class PDFExtractor:
    """Extract text and metadata from PDF files."""
    
    def __init__(self):
        self.logger = app_logger
    
    def extract_text(self, pdf_path: Path) -> Tuple[str, Dict[int, str]]:
        """
        Extract text from PDF with page information.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (full_text, page_dict)
        """
        try:
            # Try PyMuPDF first (fastest and most reliable)
            return self._extract_with_pymupdf(pdf_path)
        except Exception as e:
            self.logger.warning(f"PyMuPDF extraction failed: {e}, trying pdfplumber")
            try:
                return self._extract_with_pdfplumber(pdf_path)
            except Exception as e2:
                self.logger.warning(f"pdfplumber extraction failed: {e2}, trying pypdf")
                return self._extract_with_pypdf(pdf_path)
    
    def _extract_with_pymupdf(self, pdf_path: Path) -> Tuple[str, Dict[int, str]]:
        """Extract text using PyMuPDF."""
        doc = fitz.open(pdf_path)
        pages = {}
        full_text = []
        
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            pages[page_num] = text
            full_text.append(text)
        
        doc.close()
        return "\n\n".join(full_text), pages
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> Tuple[str, Dict[int, str]]:
        """Extract text using pdfplumber."""
        pages = {}
        full_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages[page_num] = text
                full_text.append(text)
        
        return "\n\n".join(full_text), pages
    
    def _extract_with_pypdf(self, pdf_path: Path) -> Tuple[str, Dict[int, str]]:
        """Extract text using pypdf."""
        reader = PdfReader(pdf_path)
        pages = {}
        full_text = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            pages[page_num] = text
            full_text.append(text)
        
        return "\n\n".join(full_text), pages
    
    def extract_metadata(self, pdf_path: Path, text: str) -> PaperMetadata:
        """
        Extract metadata from PDF.
        
        Args:
            pdf_path: Path to PDF file
            text: Extracted text content
            
        Returns:
            PaperMetadata object
        """
        metadata = PaperMetadata()
        
        try:
            # Get basic PDF info
            doc = fitz.open(pdf_path)
            pdf_metadata = doc.metadata
            metadata.num_pages = len(doc)
            doc.close()
            
            # Extract from PDF metadata
            if pdf_metadata:
                metadata.title = pdf_metadata.get("title")
                author_str = pdf_metadata.get("author", "")
                if author_str:
                    metadata.authors = [a.strip() for a in author_str.split(",")]
            
            # Extract from text content
            if not metadata.title:
                metadata.title = self._extract_title(text)
            
            if not metadata.authors:
                metadata.authors = self._extract_authors(text)
            
            metadata.abstract = self._extract_abstract(text)
            metadata.doi = self._extract_doi(text)
            metadata.keywords = self._extract_keywords(text)
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {e}")
        
        return metadata
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract title from text (usually first significant line)."""
        lines = text.split("\n")
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if len(line) > 20 and len(line) < 200 and not line.isupper():
                return line
        return None
    
    def _extract_authors(self, text: str) -> List[str]:
        """Extract authors from text."""
        # Look for common author patterns
        author_patterns = [
            r"(?:Authors?|By):\s*([^\n]+)",
            r"([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+\s+[A-Z][a-z]+)*)",
        ]
        
        for pattern in author_patterns:
            match = re.search(pattern, text[:2000])
            if match:
                author_str = match.group(1)
                # Split by common delimiters
                authors = re.split(r",|\sand\s", author_str)
                return [a.strip() for a in authors if a.strip()]
        
        return []
    
    def _extract_abstract(self, text: str) -> Optional[str]:
        """Extract abstract from text."""
        # Look for abstract section
        abstract_pattern = r"(?:Abstract|ABSTRACT)[:\s]*\n(.*?)(?:\n\n|\n[A-Z][a-z]+:)"
        match = re.search(abstract_pattern, text[:5000], re.DOTALL | re.IGNORECASE)
        
        if match:
            abstract = match.group(1).strip()
            # Clean up
            abstract = re.sub(r"\s+", " ", abstract)
            return abstract[:1000]  # Limit length
        
        return None
    
    def _extract_doi(self, text: str) -> Optional[str]:
        """Extract DOI from text."""
        doi_pattern = r"(?:doi|DOI)[:\s]*(10\.\d{4,}/[^\s]+)"
        match = re.search(doi_pattern, text[:3000])
        
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        keyword_pattern = r"(?:Keywords?|Index Terms)[:\s]*([^\n]+)"
        match = re.search(keyword_pattern, text[:5000], re.IGNORECASE)
        
        if match:
            keyword_str = match.group(1)
            # Split by common delimiters
            keywords = re.split(r"[,;]", keyword_str)
            return [k.strip() for k in keywords if k.strip()][:10]
        
        return []
    
    def identify_sections(self, text: str) -> Dict[str, str]:
        """
        Identify major sections in the paper.
        
        Returns:
            Dictionary mapping section names to their content
        """
        sections = {}
        
        # Common section headers in academic papers
        section_patterns = [
            r"\n(Abstract|ABSTRACT)\s*\n",
            r"\n(Introduction|INTRODUCTION)\s*\n",
            r"\n(Related Work|RELATED WORK|Literature Review)\s*\n",
            r"\n(Method(?:ology)?|METHOD(?:OLOGY)?)\s*\n",
            r"\n(Experiment(?:s)?|EXPERIMENT(?:S)?)\s*\n",
            r"\n(Results?|RESULTS?)\s*\n",
            r"\n(Discussion|DISCUSSION)\s*\n",
            r"\n(Conclusion|CONCLUSION)\s*\n",
            r"\n(References?|REFERENCES?)\s*\n",
        ]
        
        # Find all section positions
        section_positions = []
        for pattern in section_patterns:
            for match in re.finditer(pattern, text):
                section_name = match.group(1)
                section_positions.append((match.start(), section_name))
        
        # Sort by position
        section_positions.sort()
        
        # Extract content between sections
        for i, (start, name) in enumerate(section_positions):
            if i < len(section_positions) - 1:
                end = section_positions[i + 1][0]
                content = text[start:end].strip()
            else:
                content = text[start:].strip()
            
            sections[name.lower()] = content
        
        return sections
