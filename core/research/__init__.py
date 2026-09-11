"""
Research module for PLUTO v2.
Comprehensive research engine with multiple sources.
"""

from .engine import ResearchEngine
from .sources.base import BaseSource
from .sources.pubmed import PubMedSource
from .sources.news import NewsSource
from .sources.github import GitHubSource
from .sources.sec import SECSource
from .extractors.web import WebExtractor
from .extractors.pdf import PDFExtractor
from .verification import FactVerifier

__all__ = [
    'ResearchEngine',
    'BaseSource',
    'PubMedSource',
    'NewsSource',
    'GitHubSource',
    'SECSource',
    'WebExtractor',
    'PDFExtractor',
    'FactVerifier',
]
