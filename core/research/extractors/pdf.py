"""
PDF content extractor for research papers.
"""

import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract content from PDF documents."""

    def __init__(self):
        self._pdfplumber = None
        self._pymupdf = None
        self._try_load_libraries()

    def _try_load_libraries(self):
        """Try to load PDF libraries."""
        try:
            import pdfplumber
            self._pdfplumber = pdfplumber
        except ImportError:
            pass

        try:
            import fitz  # PyMuPDF
            self._pymupdf = fitz
        except ImportError:
            pass

    def extract(self, url: str = None, file_path: str = None, max_pages: int = 10) -> dict:
        """Extract content from a PDF."""
        try:
            if self._pdfplumber:
                return self._extract_pdfplumber(url, file_path, max_pages)
            elif self._pymupdf:
                return self._extract_pymupdf(url, file_path, max_pages)
            else:
                logger.warning("No PDF library available. Install pdfplumber or pymupdf.")
                return {}
        except Exception as e:
            logger.warning(f"PDF extraction failed: {e}")
            return {}

    def _extract_pdfplumber(self, url: str, file_path: str, max_pages: int) -> dict:
        """Extract using pdfplumber."""
        import io
        import requests

        pdf_file = None
        if url:
            resp = requests.get(url, timeout=30)
            pdf_file = io.BytesIO(resp.content)
        elif file_path:
            pdf_file = open(file_path, 'rb')

        if not pdf_file:
            return {}

        try:
            with self._pdfplumber.open(pdf_file) as pdf:
                pages = min(len(pdf.pages), max_pages)
                text_content = []

                for i in range(pages):
                    page = pdf.pages[i]
                    text = page.extract_text()
                    if text:
                        text_content.append(f"--- Page {i + 1} ---\n{text}")

                full_text = "\n\n".join(text_content)

                return {
                    'text': full_text,
                    'pages': pages,
                    'total_pages': len(pdf.pages),
                    'word_count': len(full_text.split()),
                    'title': self._extract_title(pdf, full_text),
                    'authors': self._extract_authors(full_text),
                    'abstract': self._extract_abstract(full_text),
                }
        finally:
            if url and pdf_file:
                pdf_file.close()

    def _extract_pymupdf(self, url: str, file_path: str, max_pages: int) -> dict:
        """Extract using PyMuPDF."""
        import io
        import requests

        doc = None
        if url:
            resp = requests.get(url, timeout=30)
            doc = self._pymupdf.open(stream=resp.content, filetype="pdf")
        elif file_path:
            doc = self._pymupdf.open(file_path)

        if not doc:
            return {}

        try:
            pages = min(doc.page_count, max_pages)
            text_content = []

            for i in range(pages):
                page = doc[i]
                text = page.get_text()
                if text.strip():
                    text_content.append(f"--- Page {i + 1} ---\n{text}")

            full_text = "\n\n".join(text_content)

            return {
                'text': full_text,
                'pages': pages,
                'total_pages': doc.page_count,
                'word_count': len(full_text.split()),
                'title': self._extract_title_from_doc(doc, full_text),
                'authors': self._extract_authors(full_text),
                'abstract': self._extract_abstract(full_text),
            }
        finally:
            doc.close()

    def _extract_title(self, pdf, text: str) -> str:
        """Extract title from PDF."""
        # Try PDF metadata first
        if hasattr(pdf, 'metadata') and pdf.metadata:
            title = pdf.metadata.get('Title', '')
            if title:
                return title

        # Extract from text
        lines = text.split('\n')
        for line in lines[:20]:
            line = line.strip()
            if len(line) > 10 and len(line) < 200:
                # Looks like a title
                if line[0].isupper() or line[0].isdigit():
                    return line

        return "Untitled PDF"

    def _extract_title_from_doc(self, doc, text: str) -> str:
        """Extract title from PyMuPDF doc."""
        if doc.metadata and doc.metadata.get('title'):
            return doc.metadata['title']

        lines = text.split('\n')
        for line in lines[:20]:
            line = line.strip()
            if len(line) > 10 and len(line) < 200:
                if line[0].isupper() or line[0].isdigit():
                    return line

        return "Untitled PDF"

    def _extract_authors(self, text: str) -> List[str]:
        """Extract author names from text."""
        import re

        authors = []
        # Common author patterns
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*){1,3})',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        ]

        # Look in first 500 chars
        first_part = text[:500]
        for pattern in patterns:
            matches = re.findall(pattern, first_part)
            for match in matches:
                if len(match) < 100 and match not in authors:
                    authors.append(match)

        return authors[:5]

    def _extract_abstract(self, text: str) -> str:
        """Extract abstract from text."""
        import re

        # Look for abstract section
        abstract_patterns = [
            r'Abstract\s*\n(.+?)(?:\n\n|\nIntroduction|\nKeywords)',
            r'BACKGROUND\s*(.+?)(?:\n\n|\nMethods)',
            r'SUMMARY\s*\n(.+?)(?:\n\n|\nRESULTS)',
        ]

        for pattern in abstract_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                if len(abstract) > 50:
                    return abstract[:1000]

        return ""
