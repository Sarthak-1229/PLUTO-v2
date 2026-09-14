"""
DuckDuckGo search source.
"""

import logging
from typing import List, Optional

from .base import BaseSource, SearchDocument

logger = logging.getLogger(__name__)


class DuckDuckGoSource(BaseSource):
    """Search source using DuckDuckGo."""

    def __init__(self):
        super().__init__("duckduckgo")

    def search(self, query: str, max_results: int = 10) -> List[SearchDocument]:
        """Search DuckDuckGo."""
        results = []
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))

            for res in raw_results:
                title = res.get("title", "").strip()
                href = res.get("href", "").strip()
                snippet = res.get("body", "").strip()

                if not title or len(title) < 3:
                    continue

                # Filter adult/spam terms
                if any(word in title.lower() for word in ['xxx', 'adult', 'porn', 'free download', 'torrent']):
                    continue

                results.append(SearchDocument(
                    id=f"ddg-{len(results)}",
                    source="duckduckgo",
                    title=title,
                    url=href,
                    snippet=snippet[:400] if snippet else "",
                    excerpt=snippet[:1000] if snippet else "",
                    content=snippet[:1000] if snippet else "",
                    relevance_score=0.85
                ))

        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")

        return results[:max_results]

    def get_details(self, doc_id: str) -> Optional[SearchDocument]:
        """Get detailed content (already included in search)."""
        return None
