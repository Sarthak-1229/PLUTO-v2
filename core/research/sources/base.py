"""
Base class for all research sources.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SearchDocument:
    """Represents a single search result document."""
    id: str
    source: str
    title: str
    url: str
    snippet: str
    content: str = ""
    excerpt: str = ""
    published_date: Optional[str] = None
    authors: List[str] = None
    tags: List[str] = None
    relevance_score: float = 0.0
    metadata: Dict = None

    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


class BaseSource(ABC):
    """Base class for all research sources."""

    def __init__(self, name: str, api_key: Optional[str] = None):
        self.name = name
        self.api_key = api_key
        self.session_cache = {}

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> List[SearchDocument]:
        """Search for documents matching the query."""
        pass

    @abstractmethod
    def get_details(self, doc_id: str) -> Optional[SearchDocument]:
        """Get detailed content for a specific document."""
        pass

    def extract_content(self, url: str, max_length: int = 3000) -> str:
        """Extract main content from a URL."""
        import requests
        from bs4 import BeautifulSoup

        try:
            if url in self.session_cache:
                return self.session_cache[url]

            resp = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()

            # Find main content
            for selector in ['article', 'main', '#content', '.content', '.post', '.entry']:
                content = soup.select_one(selector)
                if content:
                    text = content.get_text(separator='\n', strip=True)[:max_length]
                    if len(text) > 200:
                        self.session_cache[url] = text
                        return text

            # Fallback
            text = soup.get_text(separator='\n', strip=True)[:max_length]
            self.session_cache[url] = text
            return text

        except Exception as e:
            logger.warning(f"Content extraction failed for {url}: {e}")
            return ""

    def clear_cache(self):
        """Clear the session cache."""
        self.session_cache.clear()
