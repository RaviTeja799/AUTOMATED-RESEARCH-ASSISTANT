"""
Text preprocessing and cleaning for academic papers.
"""
import re
from typing import Dict, List, Tuple, Optional

from app.utils.logger import app_logger


class TextPreprocessor:
    """Clean and preprocess extracted text from PDFs."""
    
    # Common academic section headers
    SECTION_PATTERNS = [
        # Standard sections
        r'^(abstract|introduction|background|related\s+work|literature\s+review)',
        r'^(methodology|methods|approach|experimental\s+setup)',
        r'^(results|findings|experiments|evaluation)',
        r'^(discussion|analysis)',
        r'^(conclusion|conclusions|summary|future\s+work)',
        r'^(references|bibliography|citations)',
        r'^(appendix|appendices|supplementary)',
        # Numbered sections
        r'^\d+\.?\s+(abstract|introduction|background|related\s+work)',
        r'^\d+\.?\s+(methodology|methods|approach)',
        r'^\d+\.?\s+(results|findings|experiments)',
        r'^\d+\.?\s+(discussion|analysis)',
        r'^\d+\.?\s+(conclusion|summary)',
    ]
    
    def __init__(self):
        """Initialize preprocessor."""
        self.section_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.SECTION_PATTERNS]
        app_logger.info("TextPreprocessor initialized")
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize whitespace
        text = self._normalize_whitespace(text)
        
        # Remove headers/footers
        text = self._remove_headers_footers(text)
        
        # Fix hyphenation
        text = self._fix_hyphenation(text)
        
        # Remove page numbers
        text = self._remove_page_numbers(text)
        
        # Clean special characters
        text = self._clean_special_chars(text)
        
        # Normalize quotes
        text = self._normalize_quotes(text)
        
        return text.strip()
    
    def detect_sections(self, text: str) -> Dict[str, str]:
        """
        Detect and extract sections from text.
        
        Args:
            text: Cleaned text
            
        Returns:
            Dictionary mapping section names to content
        """
        sections = {}
        lines = text.split('\n')
        
        current_section = "unknown"
        current_content = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if line is a section header
            section_name = self._is_section_header(line_stripped)
            
            if section_name:
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = section_name
                current_content = []
            else:
                # Add to current section
                if line_stripped:
                    current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        app_logger.info(f"Detected {len(sections)} sections: {list(sections.keys())}")
        return sections
    
    def extract_headings(self, text: str) -> List[Tuple[str, int]]:
        """
        Extract headings with their positions.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (heading, position) tuples
        """
        headings = []
        lines = text.split('\n')
        position = 0
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if line looks like a heading
            if self._looks_like_heading(line_stripped):
                headings.append((line_stripped, position))
            
            position += len(line) + 1  # +1 for newline
        
        return headings
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving structure."""
        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)
        
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text
    
    def _remove_headers_footers(self, text: str) -> str:
        """Remove common headers and footers."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip very short lines at start/end of pages
            if len(line_stripped) < 5:
                continue
            
            # Skip lines that look like headers/footers
            if self._is_header_footer(line_stripped):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _is_header_footer(self, line: str) -> bool:
        """Check if line is likely a header or footer."""
        # Page numbers
        if re.match(r'^\d+$', line):
            return True
        
        # Copyright notices
        if re.search(r'©|copyright|all rights reserved', line, re.IGNORECASE):
            return True
        
        # URLs
        if re.search(r'https?://|www\.', line):
            return True
        
        # Very short lines with numbers
        if len(line) < 20 and re.search(r'\d', line):
            return True
        
        return False
    
    def _fix_hyphenation(self, text: str) -> str:
        """Fix word hyphenation at line breaks."""
        # Fix hyphenated words at line breaks
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        return text
    
    def _remove_page_numbers(self, text: str) -> str:
        """Remove standalone page numbers."""
        # Remove lines that are just numbers
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip if line is just a number
            if re.match(r'^\d+$', line_stripped):
                continue
            
            # Skip if line is "Page X" or similar
            if re.match(r'^page\s+\d+$', line_stripped, re.IGNORECASE):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _clean_special_chars(self, text: str) -> str:
        """Clean special characters while preserving meaning."""
        # Replace smart quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Replace em/en dashes
        text = text.replace('—', '-').replace('–', '-')
        
        # Remove zero-width spaces
        text = text.replace('\u200b', '')
        
        # Remove soft hyphens
        text = text.replace('\xad', '')
        
        return text
    
    def _normalize_quotes(self, text: str) -> str:
        """Normalize quote characters."""
        # Convert all quote variants to standard quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[''']", "'", text)
        
        return text
    
    def _is_section_header(self, line: str) -> Optional[str]:
        """
        Check if line is a section header.
        
        Returns section name if header, None otherwise.
        """
        if not line or len(line) > 100:
            return None
        
        # Check against section patterns
        for pattern in self.section_regex:
            match = pattern.match(line)
            if match:
                # Extract section name
                section_name = match.group(1).lower().strip()
                # Normalize section name
                section_name = re.sub(r'\s+', '_', section_name)
                return section_name
        
        return None
    
    def _looks_like_heading(self, line: str) -> bool:
        """Check if line looks like a heading."""
        if not line or len(line) > 100:
            return False
        
        # Check for numbered headings (1., 1.1, etc.)
        if re.match(r'^\d+(\.\d+)*\.?\s+[A-Z]', line):
            return True
        
        # Check for all caps headings
        if line.isupper() and len(line.split()) <= 5:
            return True
        
        # Check for title case headings
        words = line.split()
        if len(words) <= 6 and all(word[0].isupper() for word in words if word):
            return True
        
        return False
    
    def remove_references_section(self, text: str) -> str:
        """Remove references section from text."""
        # Find references section
        patterns = [
            r'\n\s*references\s*\n',
            r'\n\s*bibliography\s*\n',
            r'\n\s*\d+\.?\s+references\s*\n',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Remove everything after references
                text = text[:match.start()]
                app_logger.info("Removed references section")
                break
        
        return text
    
    def extract_abstract(self, text: str) -> Optional[str]:
        """Extract abstract from text."""
        # Look for abstract section
        pattern = r'abstract\s*\n(.*?)(?:\n\s*(?:introduction|1\.|keywords))'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        if match:
            abstract = match.group(1).strip()
            # Clean up
            abstract = re.sub(r'\s+', ' ', abstract)
            return abstract
        
        return None
    
    def split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split on double newlines
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean and filter
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        # Filter out very short paragraphs (likely artifacts)
        paragraphs = [p for p in paragraphs if len(p) > 50]
        
        return paragraphs


# Export
__all__ = ['TextPreprocessor']
