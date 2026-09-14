"""
Main research engine for PLUTO v2.
Orchestrates searches across multiple sources.
"""

import logging
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .sources.base import SearchDocument
from .sources.pubmed import PubMedSource
from .sources.news import NewsSource
from .sources.github import GitHubSource
from .sources.sec import SECSource
from .sources.duckduckgo import DuckDuckGoSource
from .sources.wikipedia import WikipediaSource
from .sources.arxiv import ArxivSource
from .extractors.web import WebExtractor
from .extractors.pdf import PDFExtractor
from .verification import FactVerifier

logger = logging.getLogger(__name__)


@dataclass
class ResearchQuery:
    """A research query with metadata."""
    query: str
    query_type: str  # 'fact', 'news', 'academic', 'code', 'financial', 'general'
    sources: List[str] = field(default_factory=list)
    max_results: int = 10
    depth: str = 'standard'  # 'quick', 'standard', 'deep', 'expert'
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ResearchResult:
    """Complete research result."""
    query: str
    documents: List[SearchDocument] = field(default_factory=list)
    summary: str = ""
    key_findings: List[str] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)
    search_time: float = 0.0
    verified: bool = False
    confidence: float = 0.0
    error: Optional[str] = None


class ResearchEngine:
    """Main research orchestration engine."""

    def __init__(self):
        # Initialize sources
        self.sources = {
            'duckduckgo': DuckDuckGoSource(),
            'wikipedia': WikipediaSource(),
            'arxiv': ArxivSource(),
            'pubmed': PubMedSource(),
            'news': NewsSource(),
            'github': GitHubSource(),
            'sec': SECSource(),
        }

        self.web_extractor = WebExtractor()
        self.pdf_extractor = PDFExtractor()
        self.verifier = FactVerifier()

        # Query type routing
        self.query_routers = {
            'quantum': ['arxiv', 'wikipedia', 'duckduckgo'],
            'machine learning': ['arxiv', 'github', 'wikipedia', 'duckduckgo'],
            'ai': ['arxiv', 'github', 'wikipedia', 'duckduckgo'],
            'climate': ['pubmed', 'arxiv', 'wikipedia', 'news', 'duckduckgo'],
            'space': ['nasa', 'wikipedia', 'news', 'duckduckgo'],
            'mars': ['nasa', 'wikipedia', 'news', 'duckduckgo'],
            'medicine': ['pubmed', 'wikipedia', 'news', 'duckduckgo'],
            'biology': ['pubmed', 'arxiv', 'wikipedia', 'duckduckgo'],
            'finance': ['sec', 'news', 'duckduckgo'],
            'stock': ['sec', 'news', 'duckduckgo'],
            'code': ['github', 'duckduckgo'],
            'programming': ['github', 'duckduckgo'],
            'python': ['github', 'duckduckgo'],
            'javascript': ['github', 'duckduckgo'],
            'news': ['news', 'duckduckgo'],
            'current events': ['news', 'duckduckgo'],
        }

    def search(self, query: str, max_results: int = 10, depth: str = 'standard') -> ResearchResult:
        """
        Perform comprehensive research on a query.

        Args:
            query: The research question
            max_results: Maximum documents to return
            depth: Search depth ('quick', 'standard', 'deep', 'expert')

        Returns:
            ResearchResult with all findings
        """
        start_time = time.time()
        logger.info(f"ResearchEngine: Starting search for '{query}' (depth={depth})")

        result = ResearchResult(query=query)

        # Determine query type and sources
        query_type = self._classify_query(query)
        sources = self._get_sources(query, query_type, depth)

        logger.info(f"ResearchEngine: Using sources {sources} for query type '{query_type}'")

        # Execute parallel searches
        documents = []
        sources_used = []

        for source_name in sources:
            if source_name in self.sources:
                try:
                    source_docs = self.sources[source_name].search(query, max_results)
                    documents.extend(source_docs)
                    sources_used.append(source_name)
                    logger.info(f"ResearchEngine: Got {len(source_docs)} docs from {source_name}")
                except Exception as e:
                    logger.warning(f"ResearchEngine: Source {source_name} failed: {e}")

        # Deduplicate and rank
        documents = self._deduplicate_and_rank(documents, query)

        # Enrich top results with full web extraction only for deep/expert searches
        if depth in ('deep', 'expert'):
            top_docs = documents[:min(2, len(documents))]
            for doc in top_docs:
                if not doc.content:
                    try:
                        doc.content = self.web_extractor.extract(doc.url, max_length=2000).get('content', '')
                    except Exception:
                        pass

        # Verify key claims
        if len(documents) > 1:
            claim = self._extract_claim(query)
            doc_dicts = [{'title': d.title, 'content': d.content, 'excerpt': d.excerpt}
                        for d in documents[:5]]
            verification = self.verifier.verify(claim, doc_dicts)
            result.verified = verification.verified
            result.confidence = verification.confidence

        # Calculate search time
        result.search_time = time.time() - start_time
        result.documents = documents[:max_results]
        result.sources_used = sources_used

        logger.info(f"ResearchEngine: Completed in {result.search_time:.2f}s, found {len(documents)} docs")

        return result

    def _classify_query(self, query: str) -> str:
        """Classify the type of query."""
        query_lower = query.lower()

        for pattern, query_type in [
            ('quantum', 'quantum'),
            ('machine learning|ml|neural network', 'ai'),
            ('artificial intelligence|ai', 'ai'),
            ('climate|environment|sustainability', 'climate'),
            ('space|nasa|planet|star|galaxy', 'space'),
            ('mars|mars mission', 'mars'),
            ('medicine|drug|treatment|patient', 'medicine'),
            ('biology|gene|dna|cell', 'biology'),
            ('finance|stock|market|invest', 'finance'),
            ('code|programming|software|github', 'code'),
            ('python|javascript|java|c\\+\\+', 'programming'),
            ('news|latest|today|recent', 'news'),
        ]:
            import re
            if re.search(pattern, query_lower):
                return query_type

        return 'general'

    def _get_sources(self, query: str, query_type: str, depth: str) -> List[str]:
        """Get appropriate sources for the query."""
        # Check specific routers
        for pattern, sources in self.query_routers.items():
            if pattern.lower() in query.lower():
                return sources

        # Default based on depth
        if depth == 'quick':
            return ['duckduckgo']
        elif depth == 'standard':
            return ['duckduckgo', 'wikipedia']
        elif depth == 'deep':
            return ['duckduckgo', 'wikipedia', 'arxiv', 'news']
        else:  # expert
            return ['duckduckgo', 'wikipedia', 'arxiv', 'pubmed', 'news', 'github']

    def _deduplicate_and_rank(self, documents: List[SearchDocument], query: str) -> List[SearchDocument]:
        """Remove duplicates and rank by relevance."""
        seen_urls = set()
        unique_docs = []

        for doc in documents:
            # Normalize URL for deduplication
            url = doc.url.lower().strip()
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Boost relevance for trusted sources
            if doc.source == 'wikipedia':
                doc.relevance_score = max(doc.relevance_score, 0.9)
            elif doc.source == 'arxiv':
                doc.relevance_score = max(doc.relevance_score, 0.85)
            elif doc.source == 'pubmed':
                doc.relevance_score = max(doc.relevance_score, 0.85)

            unique_docs.append(doc)

        # Sort by relevance
        unique_docs.sort(key=lambda x: x.relevance_score, reverse=True)
        return unique_docs

    def _extract_claim(self, query: str) -> str:
        """Extract the main claim/fact from the query."""
        # Simple extraction: take the core question
        return query.rstrip('?').strip()

    def generate_summary(self, result: ResearchResult) -> str:
        """Generate a summary from research results."""
        if not result.documents:
            return "No results found for your query."

        docs = result.documents[:5]
        lines = [f"Research on '{result.query}':\n"]

        # Key findings
        for i, doc in enumerate(docs, 1):
            excerpt = doc.excerpt or doc.snippet or ""
            if excerpt:
                lines.append(f"{i}. **{doc.title}**")
                lines.append(f"   {excerpt[:200]}...")
                lines.append("")

        # Sources
        lines.append(f"Sources: {', '.join(result.sources_used)}")

        if result.verified:
            lines.append(f"✓ Verified with {result.confidence:.0%} confidence")
        else:
            lines.append(f"? Unverified - cross-check recommended")

        return "\n".join(lines)


# Singleton instance
_engine = None

def get_research_engine() -> ResearchEngine:
    """Get or create the singleton ResearchEngine instance."""
    global _engine
    if _engine is None:
        _engine = ResearchEngine()
    return _engine
