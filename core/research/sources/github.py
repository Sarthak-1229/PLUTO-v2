"""
GitHub research source for code and technical projects.
"""

import logging
from typing import List, Optional
from .base import BaseSource, SearchDocument

logger = logging.getLogger(__name__)


class GitHubSource(BaseSource):
    """Search source for GitHub repositories."""

    def __init__(self):
        super().__init__("github")

    def search(self, query: str, max_results: int = 10) -> List[SearchDocument]:
        """Search GitHub repositories."""
        import requests

        results = []
        try:
            url = "https://api.github.com/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max_results
            }
            resp = requests.get(url, params=params, timeout=15)

            if resp.status_code == 403:
                logger.warning("GitHub API rate limit exceeded")
                return results

            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                results.append(SearchDocument(
                    id=f"github-{item.get('id')}",
                    source="github",
                    title=item.get("full_name", "Untitled"),
                    url=item.get("html_url", ""),
                    snippet=item.get("description", ""),
                    content=self._get_readme(item),
                    published_date=item.get("created_at", "")[:10],
                    authors=[item.get("owner", {}).get("login", "Unknown")],
                    tags=self._extract_tags(item),
                    relevance_score=self._calc_relevance(item),
                    metadata={
                        "stars": item.get("stargazers_count", 0),
                        "forks": item.get("forks_count", 0),
                        "language": item.get("language", ""),
                        "topics": item.get("topics", [])
                    }
                ))
        except Exception as e:
            logger.warning(f"GitHub search failed: {e}")

        return results

    def _get_readme(self, repo: dict) -> str:
        """Get README content for a repository."""
        import requests

        owner = repo.get("owner", {}).get("login")
        name = repo.get("name")

        if not owner or not name:
            return ""

        try:
            url = f"https://api.github.com/repos/{owner}/{name}/readme"
            resp = requests.get(url, timeout=10)

            if resp.status_code == 200:
                import base64
                content = resp.json().get("content", "")
                return base64.b64decode(content).decode('utf-8', errors='ignore')[:2000]
        except Exception:
            pass

        return ""

    def _extract_tags(self, repo: dict) -> List[str]:
        """Extract tags from repository."""
        tags = []
        if repo.get("language"):
            tags.append(repo["language"])
        for topic in repo.get("topics", [])[:5]:
            tags.append(topic)
        return tags

    def _calc_relevance(self, repo: dict) -> float:
        """Calculate relevance score."""
        stars = repo.get("stargazers_count", 0)
        forks = repo.get("forks_count", 0)
        return min(1.0, (stars / 1000) * 0.7 + (forks / 500) * 0.3)

    def get_details(self, doc_id: str) -> Optional[SearchDocument]:
        """Get detailed info for a GitHub repo."""
        return None
