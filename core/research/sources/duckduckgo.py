"""
DuckDuckGo search source.
"""

import logging
import re
from typing import List, Optional
from urllib.parse import quote, unquote
import requests
from bs4 import BeautifulSoup

from .base import BaseSource, SearchDocument

logger = logging.getLogger(__name__)


class DuckDuckGoSource(BaseSource):
    """Search source using DuckDuckGo."""

    def __init__(self):
        super().__init__("duckduckgo")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def search(self, query: str, max_results: int = 10) -> List[SearchDocument]:
        """Search DuckDuckGo."""
        results = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')

            for result in soup.select('result-link')[:max_results * 2]:
                title_tag = result.select_one('a.result__a')
                snippet_tag = result.select_one('a.result__snippet')

                if title_tag and snippet_tag:
                    title = title_tag.get_text(strip=True)
                    href = title_tag.get('href', '')

                    # Extract real URL from DuckDuckGo redirect
                    if '/l/?uddg=' in href:
                        match = re.search(r'/l/\?uddg=([^&]+)', href)
                        if match:
                            href = unquote(match.group(1))

                    snippet = snippet_tag.get_text(strip=True)

                    # Skip suspicious content
                    if title and href and len(title) > 3:
                        if any(word in title.lower() for word in ['xxx', 'adult', 'porn', 'free download', 'torrent']):
                            continue

                        results.append(SearchDocument(
                            id=f"ddg-{len(results)}",
                            source="duckduckgo",
                            title=title,
                            url=href,
                            snippet=snippet[:300] if snippet else "",
                            excerpt="",
                            relevance_score=0.8
                        ))

                if len(results) >= max_results:
                    break

        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")

        return results[:max_results]

    def get_details(self, doc_id: str) -> Optional[SearchDocument]:
        """Get detailed content (already included in search)."""
        return None
