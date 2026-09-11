"""
PubMed research source for biomedical literature.
"""

import logging
import xml.etree.ElementTree as ET
from typing import List, Optional
from .base import BaseSource, SearchDocument

logger = logging.getLogger(__name__)


class PubMedSource(BaseSource):
    """Search source for PubMed biomedical literature."""

    def __init__(self):
        super().__init__("pubmed")

    def search(self, query: str, max_results: int = 10) -> List[SearchDocument]:
        """Search PubMed for biomedical literature."""
        import requests

        results = []
        try:
            # Search PubMed
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "sort": "relevance",
                "retmode": "xml"
            }
            resp = requests.get(search_url, params=params, timeout=15)
            resp.raise_for_status()

            root = ET.fromstring(resp.text)
            id_list = root.find(".//IdList")
            if id_list is None:
                return results

            pmids = [id.text for id in id_list.findall("Id") if id.text]

            if not pmids:
                return results

            # Get detailed records
            details_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            params = {
                "db": "pubmed",
                "id": ",".join(pmids[:max_results]),
                "retmode": "xml"
            }
            resp = requests.get(details_url, params=params, timeout=15)
            resp.raise_for_status()

            root = ET.fromstring(resp.text)
            for article in root.findall(".//PubmedArticle"):
                doc = self._parse_article(article, query)
                if doc:
                    results.append(doc)

        except Exception as e:
            logger.warning(f"PubMed search failed: {e}")

        return results

    def _parse_article(self, article, query: str) -> Optional[SearchDocument]:
        """Parse a PubMed article XML element."""
        try:
            # Title
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text.strip() if title_elem is not None else "Untitled"

            # PMID
            pmid_elem = article.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""

            # Abstract
            abstract_elems = article.findall(".//AbstractText")
            abstract = " ".join([a.text.strip() for a in abstract_elems if a.text])

            # Authors
            authors = []
            for author in article.findall(".//Author"):
                last_name = author.find("LastName")
                first_name = author.find("ForeName")
                if last_name is not None:
                    author_name = last_name.text
                    if first_name is not None and first_name.text:
                        author_name = f"{first_name.text} {author_name}"
                    authors.append(author_name)

            # Publication date
            pub_date = article.find(".//PubDate/Year")
            year = pub_date.text if pub_date is not None else ""

            # Journal
            journal = article.find(".//Title")
            journal_name = journal.text if journal is not None else ""

            # DOI
            doi_elem = article.find(".//ELocationId[@EIdType='doi']")
            doi = doi_elem.text if doi_elem is not None else ""
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            if doi:
                url = f"https://doi.org/{doi}"

            # Keywords
            keywords = []
            for keyword in article.findall(".//Keyword"):
                keywords.append(keyword.text)

            return SearchDocument(
                id=f"pubmed-{pmid}",
                source="pubmed",
                title=title,
                url=url,
                snippet=abstract[:300] if abstract else "",
                content=abstract,
                excerpt=abstract[:500] if abstract else "",
                published_date=year,
                authors=authors[:5],
                tags=keywords,
                relevance_score=1.0
            )

        except Exception as e:
            logger.warning(f"Failed to parse PubMed article: {e}")
            return None

    def get_details(self, doc_id: str) -> Optional[SearchDocument]:
        """Get detailed content for a PubMed article."""
        # Already included in search results
        return None
