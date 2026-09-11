"""
arXiv academic papers search source.
"""

import logging
import requests
from typing import List, Optional
from xml.etree import ElementTree as ET

from .base import BaseSource, SearchDocument

logger = logging.getLogger(__name__)


class ArxivSource(BaseSource):
    """Search source for arXiv academic papers."""

    def __init__(self):
        super().__init__("arxiv")
        self.api_url = "http://export.arxiv.org/api/query"

    def search(self, query: str, max_results: int = 10) -> List[SearchDocument]:
        """Search arXiv."""
        results = []
        try:
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            resp = requests.get(self.api_url, params=params, timeout=15)
            resp.raise_for_status()

            root = ET.fromstring(resp.text)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
                "opensearch": "http://a9.com/-/spec/opensearch/1.1/"
            }

            for entry in root.findall("atom:entry", ns)[:max_results]:
                title_elem = entry.find("atom:title", ns)
                summary_elem = entry.find("atom:summary", ns)
                id_elem = entry.find("atom:id", ns)
                published = entry.find("atom:published", ns)
                authors = entry.findall("atom:author", ns)

                title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None else "Untitled"
                summary = summary_elem.text.replace('\n', ' ').strip()[:1500] if summary_elem is not None else ""
                paper_url = id_elem.text if id_elem is not None else ""
                date = published.text[:10] if published is not None else ""

                author_list = []
                for author in authors[:5]:
                    name = author.find("atom:name", ns)
                    if name is not None:
                        author_list.append(name.text)

                # Extract categories
                categories = []
                for cat in entry.findall("atom:category", ns):
                    term = cat.get('term', '')
                    if term:
                        categories.append(term)

                results.append(SearchDocument(
                    id=f"arxiv-{paper_url}",
                    source="arxiv",
                    title=title,
                    url=paper_url,
                    snippet=f"Published: {date}",
                    excerpt=summary,
                    content=summary,
                    published_date=date,
                    authors=author_list,
                    tags=categories[:5],
                    relevance_score=0.95
                ))

        except Exception as e:
            logger.warning(f"arXiv search failed: {e}")

        return results

    def get_details(self, doc_id: str) -> Optional[SearchDocument]:
        """Get full paper details."""
        # Try to extract paper ID from URL
        import re
        match = re.search(r'arxiv\.org/abs/([\d\.]+)', doc_id)
        if match:
            paper_id = match.group(1)
            return self._get_paper_details(paper_id)
        return None

    def _get_paper_details(self, paper_id: str) -> Optional[SearchDocument]:
        """Get detailed paper information."""
        try:
            # Get abs page
            abs_url = f"https://arxiv.org/abs/{paper_id}"
            resp = requests.get(abs_url, timeout=15)
            resp.raise_for_status()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Extract title
            title_elem = soup.find('title')
            title = title_elem.get_text(strip=True).replace(f'[{paper_id}]', '').strip()

            # Extract abstract
            abstract_elem = soup.find('blockquote', class_='abstract mathjax')
            abstract = ""
            if abstract_elem:
                abstract = abstract_elem.get_text(strip=True)

            # Extract authors
            authors = []
            for author in soup.select('.author'):
                authors.append(author.get_text(strip=True))

            # Extract comments
            comments_elem = soup.find('td', class_='ltx_comment')
            comments = comments_elem.get_text(strip=True) if comments_elem else ""

            return SearchDocument(
                id=f"arxiv-full-{paper_id}",
                source="arxiv",
                title=title,
                url=abs_url,
                snippet=abstract[:300] if abstract else "",
                excerpt=abstract,
                content=abstract + ("\n\nComments: " + comments if comments else ""),
                authors=authors[:10],
                relevance_score=1.0
            )
        except Exception as e:
            logger.warning(f"arXiv details failed: {e}")
            return None
