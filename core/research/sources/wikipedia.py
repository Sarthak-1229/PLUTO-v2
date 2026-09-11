"""
Wikipedia search source.
"""

import logging
import requests
from typing import List, Optional

from .base import BaseSource, SearchDocument

logger = logging.getLogger(__name__)


class WikipediaSource(BaseSource):
    """Search source for Wikipedia articles."""

    def __init__(self):
        super().__init__("wikipedia")
        self.api_url = "https://en.wikipedia.org/w/api.php"

    def search(self, query: str, max_results: int = 10) -> List[SearchDocument]:
        """Search Wikipedia."""
        results = []
        try:
            # Search
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": max_results,
                "format": "json",
                "origin": "*"
            }
            resp = requests.get(self.api_url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get('query', {}).get('search', []):
                title = item.get('title', '')
                snippet = item.get('snippet', '').replace('<[^>]+>', '').strip()

                # Get full extract
                extract = self._get_extract(title)

                results.append(SearchDocument(
                    id=f"wiki-{title}",
                    source="wikipedia",
                    title=f"Wikipedia: {title}",
                    url=f"https://en.wikipedia.org/wiki/{title}",
                    snippet=snippet[:300],
                    excerpt=extract,
                    content=extract,
                    relevance_score=0.9
                ))

        except Exception as e:
            logger.warning(f"Wikipedia search failed: {e}")

        return results[:max_results]

    def _get_extract(self, title: str) -> str:
        """Get article extract."""
        try:
            params = {
                "action": "query",
                "titles": title,
                "prop": "extracts",
                "explaintext": True,
                "format": "json",
                "origin": "*"
            }
            resp = requests.get(self.api_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get('query', {}).get('pages', {})
            for page_id, page in pages.items():
                return page.get('extract', '')[:2000]
        except Exception:
            pass
        return ""

    def get_details(self, doc_id: str) -> Optional[SearchDocument]:
        """Get detailed content for a Wikipedia article."""
        # Title is embedded in doc_id
        title = doc_id.replace("wiki-", "")
        try:
            params = {
                "action": "query",
                "titles": title,
                "prop": "extracts|info|revisions",
                "exintro": True,
                "explaintext": True,
                "propexintromaxlines": 10,
                "rvprop": "content",
                "rvlimit": 1,
                "format": "json",
                "origin": "*"
            }
            resp = requests.get(self.api_url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get('query', {}).get('pages', {})
            for page_id, page in pages.items():
                extract = page.get('extract', '')
                revisions = page.get('revisions', [])
                content = revisions[0].get('*', '') if revisions else extract

                return SearchDocument(
                    id=doc_id,
                    source="wikipedia",
                    title=f"Wikipedia: {title}",
                    url=f"https://en.wikipedia.org/wiki/{title}",
                    snippet=extract[:300],
                    excerpt=extract,
                    content=content[:5000],
                    relevance_score=0.95
                )
        except Exception as e:
            logger.warning(f"Wikipedia details failed: {e}")
            return None
