"""
SEC EDGAR research source for financial/company data.
"""

import logging
from typing import List, Optional
from .base import BaseSource, SearchDocument

logger = logging.getLogger(__name__)


class SECSource(BaseSource):
    """Search source for SEC filings and financial data."""

    def __init__(self):
        super().__init__("sec")

    def search(self, query: str, max_results: int = 10) -> List[SearchDocument]:
        """Search SEC EDGAR for company filings."""
        import requests

        results = []
        try:
            # Search for companies
            search_url = "https://efts.sec.gov/LATEST/search-index?q={}".format(
                requests.utils.quote(query)
            )

            # Try CIK lookup
            cik_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=&dateoption=&company={}&search_text=&owner=exclude&count=5".format(
                requests.utils.quote(query)
            )

            # Direct filing search
            filings_url = "https://efts.sec.gov/LATEST/query?query={}&forms=&dateRange=srt&startDT=&endDT=&ownership=exclude".format(
                requests.utils.quote(query)
            )

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            resp = requests.get(filings_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                import re
                # Extract filing information
                filings = re.findall(r'<div class="block[^"]*">(.*?)</div>', resp.text, re.DOTALL)
                for filing in filings[:max_results]:
                    title_match = re.search(r'<h2[^>]*>(.*?)</h2>', filing)
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filing)

                    if title_match:
                        title = title_match.group(1).strip()
                        results.append(SearchDocument(
                            id=f"sec-{len(results)}",
                            source="sec",
                            title=title,
                            url=filings_url,
                            snippet=title[:200],
                            published_date=date_match.group(1) if date_match else "",
                            tags=["sec", "financial", "filing"],
                            relevance_score=0.9
                        ))
        except Exception as e:
            logger.warning(f"SEC search failed: {e}")

        return results

    def get_company_filings(self, ticker: str, form_type: str = "10-K", max_results: int = 5) -> List[SearchDocument]:
        """Get specific filings for a company."""
        import requests

        results = []
        try:
            url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type={form_type}&dateb=&owner=exclude&count={max_results}"
            resp = requests.get(url, timeout=15)

            if resp.status_code == 200:
                import re
                filings = re.findall(r'<a href="(/cgi-bin/browse-edgar\?[^"]+)"[^>]*>([^<]+)</a>', resp.text)
                for filing_url, title in filings[:max_results]:
                    results.append(SearchDocument(
                        id=f"sec-{ticker}-{form_type}-{len(results)}",
                        source="sec",
                        title=f"{ticker} {form_type}",
                        url=f"https://www.sec.gov{filing_url}",
                        snippet=f"{ticker} {form_type} filing",
                        tags=["sec", ticker.lower(), form_type.lower()],
                        relevance_score=1.0
                    ))
        except Exception as e:
            logger.warning(f"SEC company search failed: {e}")

        return results

    def get_details(self, doc_id: str) -> Optional[SearchDocument]:
        """Get detailed content for a SEC filing."""
        return None
