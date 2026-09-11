"""
News research source for current events.
"""

import logging
from typing import List, Optional
from .base import BaseSource, SearchDocument

logger = logging.getLogger(__name__)


class NewsSource(BaseSource):
    """Search source for news articles."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("news", api_key)
        self.api_key = api_key or ""

    def search(self, query: str, max_results: int = 10) -> List[SearchDocument]:
        """Search for news articles."""
        import requests

        results = []

        # Try NewsAPI if key available
        if self.api_key:
            news_results = self._search_newsapi(query, max_results)
            results.extend(news_results)

        # Always try DuckDuckGo News as fallback
        news_results = self._search_ddg_news(query, max_results)
        results.extend(news_results)

        return results[:max_results]

    def _search_newsapi(self, query: str, max_results: int) -> List[SearchDocument]:
        """Search using NewsAPI.org."""
        import requests

        results = []
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "apiKey": self.api_key,
                "pageSize": max_results,
                "sortBy": "publishedAt",
                "language": "en"
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            for article in data.get("articles", []):
                results.append(SearchDocument(
                    id=f"news-{article.get('url', '')}",
                    source="news",
                    title=article.get("title", "Untitled"),
                    url=article.get("url", ""),
                    snippet=article.get("description", ""),
                    content=article.get("content", ""),
                    published_date=article.get("publishedAt", "")[:10],
                    authors=[article.get("author", "Unknown")],
                    tags=[article.get("source", {}).get("name", "")],
                    relevance_score=1.0
                ))
        except Exception as e:
            logger.warning(f"NewsAPI search failed: {e}")

        return results

    def _search_ddg_news(self, query: str, max_results: int) -> List[SearchDocument]:
        """Search DuckDuckGo News."""
        import requests
        from bs4 import BeautifulSoup

        results = []
        try:
            url = f"https://html.duckduckgo.com/html/?q=news+{query}"
            resp = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            soup = BeautifulSoup(resp.text, 'html.parser')
            for link in soup.select('a.result__a')[:max_results]:
                title = link.get_text(strip=True)
                href = link.get('href', '')

                if '/l/?uddg=' in href:
                    from urllib.parse import unquote
                    import re
                    match = re.search(r'/l/\?uddg=([^&]+)', href)
                    if match:
                        href = unquote(match.group(1))

                if title and href and len(title) > 5:
                    results.append(SearchDocument(
                        id=f"news-ddg-{len(results)}",
                        source="news",
                        title=title,
                        url=href,
                        snippet="",
                        relevance_score=0.8
                    ))
        except Exception as e:
            logger.warning(f"DDG News search failed: {e}")

        return results

    def get_details(self, doc_id: str) -> Optional[SearchDocument]:
        """Get detailed content for a news article."""
        return None
