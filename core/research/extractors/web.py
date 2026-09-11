"""
Web content extractor for research documents.
"""

import logging
import re
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebExtractor:
    """Extract structured content from web pages."""

    def __init__(self):
        self.stop_words = set([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'shall', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our',
            'their', 'not', 'no', 'nor', 'so', 'if', 'then', 'than', 'too', 'very'
        ])

    def extract(self, url: str, max_length: int = 5000) -> dict:
        """Extract main content from a URL."""
        import requests

        try:
            resp = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside',
                           'iframe', 'noscript', 'form']):
                tag.decompose()

            # Extract title
            title = self._extract_title(soup)

            # Extract meta description
            description = self._extract_description(soup)

            # Extract main content
            content = self._extract_content(soup, max_length)

            # Extract authors
            authors = self._extract_authors(soup)

            # Extract publication date
            pub_date = self._extract_date(soup)

            # Extract key points
            key_points = self._extract_key_points(content)

            return {
                'title': title,
                'description': description,
                'content': content,
                'authors': authors,
                'publication_date': pub_date,
                'key_points': key_points,
                'word_count': len(content.split()),
                'read_time': max(1, len(content.split()) // 200),
                'url': url
            }

        except Exception as e:
            logger.warning(f"Web extraction failed for {url}: {e}")
            return {
                'title': '',
                'description': '',
                'content': '',
                'authors': [],
                'publication_date': '',
                'key_points': [],
                'word_count': 0,
                'read_time': 0,
                'url': url
            }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try og:title first
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content']

        # Try Twitter title
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            return twitter_title['content']

        # Fallback to <title>
        title = soup.find('title')
        if title:
            return title.get_text(strip=True)

        return ''

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description."""
        desc = soup.find('meta', attrs={'name': 'description'})
        if desc and desc.get('content'):
            return desc['content']

        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content']

        return ''

    def _extract_content(self, soup: BeautifulSoup, max_length: int) -> str:
        """Extract main article content."""
        # Try common content selectors
        selectors = [
            'article', 'main', '#content', '.content', '.post', '.entry',
            '.article-content', '.story-body', '[role="main"]'
        ]

        for selector in selectors:
            content = soup.select_one(selector)
            if content:
                text = content.get_text(separator='\n', strip=True)
                if len(text) > 200:
                    return text[:max_length]

        # Fallback: get all paragraph text
        paragraphs = soup.find_all('p')
        text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs[:20]])
        return text[:max_length]

    def _extract_authors(self, soup: BeautifulSoup) -> list:
        """Extract author names."""
        authors = []

        # Try various author selectors
        selectors = [
            'meta[name="author"]',
            'meta[property="article:author"]',
            '.author', '.byline', '[rel="author"]',
            '.article-author', '.post-author'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                author = elem.get('content', elem.get_text(strip=True))
                if author and author not in authors:
                    authors.append(author)

        return authors[:3]

    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date."""
        selectors = [
            'meta[property="article:published_time"]',
            'meta[name="publish_date"]',
            'time[datetime]',
            '.published-date', '.date'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                date = elem.get('datetime', elem.get_text(strip=True))
                if date:
                    return date[:10]  # Return YYYY-MM-DD

        return ''

    def _extract_key_points(self, content: str, max_points: int = 5) -> list:
        """Extract key points from content."""
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        points = []

        for line in lines[:50]:
            # Look for bullet points, numbered lists, or important sentences
            if any(line.startswith(p) for p in ['•', '-', '*', '1.', '2.', '3.']):
                points.append(line)
            elif len(line) > 50 and len(line) < 200:
                # Short, substantive sentences
                points.append(line)

            if len(points) >= max_points:
                break

        return points[:max_points]

    def extract_table(self, html: str) -> list:
        """Extract tables from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        tables = []

        for table in soup.find_all('table')[:3]:
            rows = []
            for row in table.find_all('tr')[:10]:
                cells = [cell.get_text(strip=True) for cell in row.find_all(['th', 'td'])]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)

        return tables
