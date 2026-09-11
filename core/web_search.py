"""
Advanced web search module for PLUTO v2.

Provides multiple search strategies to ensure we ALWAYS find relevant information.
Uses DuckDuckGo, Wikipedia, Brave Search API (optional), and direct web scraping.
"""

import logging
import re
import time
from typing import Optional, List
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Trusted high-quality domains
TRUSTED_DOMAINS = [
    'wikipedia.org', 'bbc.com', 'reuters.com', 'nasa.gov',
    'nature.com', 'arxiv.org', 'britannica.com', 'scientificamerican.com',
    'mit.edu', 'stanford.edu', 'harvard.edu', 'caltech.edu',
    'ieee.org', 'acm.org', 'science.org', 'sciencedirect.com',
    'google.com', 'microsoft.com', 'amazon.com', 'ibm.com',
    'forbes.com', 'techcrunch.com', 'wired.com', 'theverge.com',
]


class WebSearchEngine:
    """Multi-source web search engine."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def search(self, query: str, max_results: int = 10, force_search: bool = True) -> List[dict]:
        """
        Search across multiple sources to ensure comprehensive results.

        Args:
            query: The search query
            max_results: Maximum number of results to return
            force_search: If True, always search even if we have cached results

        Returns:
            List of search results with title, url, snippet, excerpt
        """
        logger.info(f"WebSearch: Searching for '{query}' (force={force_search})")

        all_results = []
        seen_urls = set()

        # Strategy 1: DuckDuckGo (primary)
        ddg_results = self._search_ddg(query, max_results=max_results)
        for r in ddg_results:
            if self._add_result(r, seen_urls, all_results):
                pass

        # Strategy 2: Wikipedia (always try for factual topics)
        wiki_results = self._search_wikipedia(query, max_results=3)
        for r in wiki_results:
            self._add_result(r, seen_urls, all_results)

        # Strategy 3: Direct site searches for specific domains
        if len(all_results) < 3:
            for domain in ['wikipedia.org', 'nasa.gov', 'nature.com']:
                site_results = self._search_site(query, domain, max_results=2)
                for r in site_results:
                    self._add_result(r, seen_urls, all_results)

        # Strategy 4: Extract more content from top results
        all_results = self._enrich_results(all_results[:max_results])

        logger.info(f"WebSearch: Found {len(all_results)} results for '{query}'")
        return all_results[:max_results]

    def _add_result(self, result: dict, seen_urls: set, all_results: list) -> bool:
        """Add a result if it's unique and valid."""
        url = result.get('url', '')
        title = result.get('title', '')

        if not url or not title:
            return False

        if url in seen_urls:
            return False

        # Skip suspicious content
        if any(word in title.lower() for word in ['xxx', 'adult', 'porn', 'free download', 'torrent']):
            return False

        seen_urls.add(url)
        all_results.append(result)
        return True

    def _search_ddg(self, query: str, max_results: int = 10) -> List[dict]:
        """Search DuckDuckGo."""
        results = []
        try:
            # Try the ddgs library first
            try:
                from ddgs import DDGS
                with DDGS() as ddg:
                    raw = ddg.text(query, max_results=max_results * 2) or []
                    for item in raw:
                        title = item.get('title', '').strip()
                        url = item.get('href', '').strip()
                        snippet = item.get('body', '').strip()

                        if title and url and len(title) > 3:
                            results.append({
                                'source': 'duckduckgo',
                                'title': title,
                                'url': url,
                                'snippet': snippet[:300] if snippet else '',
                                'excerpt': None,
                            })
            except ImportError:
                pass

            # Fallback: HTML scraping
            if not results:
                url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    for link in soup.select('a.result__a')[:max_results]:
                        title = link.get_text(strip=True)
                        href = link.get('href', '')
                        if title and href and len(title) > 3:
                            # Extract real URL from DuckDuckGo redirect
                            if '/l/?uddg=' in href:
                                match = re.search(r'/l/\?uddg=([^&]+)', href)
                                if match:
                                    href = unquote(match.group(1))

                            snippet_elem = link.find_parent('div').find_next_sibling('div')
                            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''

                            results.append({
                                'source': 'duckduckgo',
                                'title': title,
                                'url': href,
                                'snippet': snippet[:300],
                                'excerpt': None,
                            })
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")

        return results

    def _search_wikipedia(self, query: str, max_results: int = 3) -> List[dict]:
        """Search Wikipedia."""
        results = []
        try:
            # Search
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": max_results,
                "format": "json",
                "origin": "*",
            }
            resp = self.session.get(search_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get('query', {}).get('search', []):
                title = item.get('title', '')
                snippet = item.get('snippet', '').replace('<[^>]+>', '').strip()

                # Get full extract
                extract = self._get_wikipedia_extract(title)

                results.append({
                    'source': 'wikipedia',
                    'title': f'Wikipedia: {title}',
                    'url': f'https://en.wikipedia.org/wiki/{title}',
                    'snippet': snippet[:300],
                    'excerpt': extract,
                })
        except Exception as e:
            logger.warning(f"Wikipedia search failed: {e}")

        return results

    def _get_wikipedia_extract(self, title: str, timeout: int = 5) -> Optional[str]:
        """Get extract from Wikipedia page."""
        try:
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "titles": title,
                "prop": "extracts",
                "explaintext": True,
                "format": "json",
                "origin": "*",
            }
            resp = self.session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get('query', {}).get('pages', {})
            for page_id, page in pages.items():
                return page.get('extract', '')[:1000]
        except Exception:
            pass
        return None

    def _search_site(self, query: str, domain: str, max_results: int = 2) -> List[dict]:
        """Search a specific site."""
        results = []
        try:
            search_url = f"https://html.duckduckgo.com/html/?q=site:{domain}+{quote(query)}"
            resp = self.session.get(search_url, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for link in soup.select('a.result__a')[:max_results]:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    if title and href and domain in href:
                        if '/l/?uddg=' in href:
                            match = re.search(r'/l/\?uddg=([^&]+)', href)
                            if match:
                                href = unquote(match.group(1))

                        results.append({
                            'source': f'site:{domain}',
                            'title': title,
                            'url': href,
                            'snippet': '',
                            'excerpt': None,
                        })
        except Exception as e:
            logger.debug(f"Site search failed for {domain}: {e}")

        return results

    def _enrich_results(self, results: List[dict]) -> List[dict]:
        """Extract more content from result pages."""
        for result in results:
            if result.get('excerpt'):
                continue  # Already enriched

            try:
                resp = self.session.get(result['url'], timeout=8)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')

                    # Try to find main content
                    for selector in ['article', 'main', '#content', '.content', '.post', '.entry']:
                        content = soup.select_one(selector)
                        if content:
                            for p in content.find_all('p'):
                                text = p.get_text(strip=True)
                                if text and len(text) > 50:
                                    result['excerpt'] = text[:600]
                                    break
                            if result.get('excerpt'):
                                break

                    # Fallback: first substantial paragraph
                    if not result.get('excerpt'):
                        for p in soup.find_all('p'):
                            text = p.get_text(strip=True)
                            if text and len(text) > 50:
                                result['excerpt'] = text[:600]
                                break
            except Exception as e:
                logger.debug(f"Failed to enrich {result.get('url')}: {e}")

            # Ensure we have some content
            if not result.get('excerpt'):
                result['excerpt'] = result.get('snippet', '')[:300]

        return results

    def scrape_page(self, url: str, max_length: int = 2000) -> Optional[str]:
        """Scrape the main content from a webpage."""
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Remove scripts and styles
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()

            # Find main content
            for selector in ['article', 'main', '#content', '.content', '.post', '.entry']:
                content = soup.select_one(selector)
                if content:
                    text = content.get_text(separator='\n', strip=True)[:max_length]
                    return text if len(text) > 100 else None

            # Fallback: body text
            text = soup.get_text(separator='\n', strip=True)[:max_length]
            return text if len(text) > 100 else None
        except Exception as e:
            logger.warning(f"Page scrape failed: {e}")
            return None


# Singleton instance
_search_engine = None

def get_web_search() -> WebSearchEngine:
    """Get or create the singleton WebSearchEngine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = WebSearchEngine()
    return _search_engine
