"""
Enhanced knowledge base with multiple sources and smart fallbacks.
"""

import logging
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from core import config

logger = logging.getLogger(__name__)


# ============================================================
# Web Search (DuckDuckGo via ddgs library)
# ============================================================
def _search_ddg(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo using the ddgs library."""
    results = []
    try:
        from ddgs import DDGS
        with DDGS() as ddg:
            raw_results = ddg.text(query, max_results=max_results * 2) or []

        for res in raw_results:
            title = res.get("title", "").strip()
            url = res.get("href", "").strip()
            snippet = res.get("body", "").strip()

            # Filter suspicious content
            if not title or len(title) < 3:
                continue
            if any(word in title.lower() for word in ['xxx', 'adult', 'porn', 'free download', 'torrent']):
                continue

            results.append({
                "source": "web",
                "title": title,
                "url": url,
                "snippet": snippet[:200] if snippet else "",
                "excerpt": None,
            })
    except Exception as exc:
        logger.warning(f"DuckDuckGo search failed: {exc}")

    return results[:max_results]


# ============================================================
# Wikipedia Search
# ============================================================
def search_wikipedia(query: str, max_results: int = 3) -> list[dict]:
    """Search Wikipedia for information."""
    results = []
    try:
        search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": max_results,
            "format": "json",
            "origin": "*",
        }
        resp = requests.get(search_url, params=params, timeout=config.SEARCH_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("query", {}).get("search", []):
            title = item.get("title", "")
            snippet = item.get("snippet", "").replace("<[^>]+>", "").strip()

            extract = _fetch_wikipedia_extract(title)

            results.append({
                "source": "wikipedia",
                "title": f"Wikipedia: {title}",
                "url": f"https://en.wikipedia.org/wiki/{title}",
                "snippet": snippet[:200],
                "excerpt": extract,
            })
    except Exception as exc:
        logger.warning(f"Wikipedia search failed: {exc}")

    return results


def _fetch_wikipedia_extract(title: str, timeout: int = 5) -> Optional[str]:
    """Fetch first paragraph from Wikipedia page."""
    try:
        url = f"https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": True,
            "format": "json",
            "origin": "*",
        }
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            return page.get("extract", "")[:500]
    except Exception:
        pass
    return None


# ============================================================
# arXiv Search
# ============================================================
def search_arxiv(query: str, max_results: int = 3) -> list[dict]:
    """Search arXiv for academic papers."""
    results = []
    try:
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        resp = requests.get(url, params=params, timeout=config.SEARCH_TIMEOUT)
        resp.raise_for_status()

        from xml.etree import ElementTree as ET
        root = ET.fromstring(resp.text)

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
        }

        for entry in root.findall("atom:entry", ns)[:max_results]:
            title_elem = entry.find("atom:title", ns)
            summary_elem = entry.find("atom:summary", ns)
            id_elem = entry.find("atom:id", ns)
            published = entry.find("atom:published", ns)

            title = title_elem.text.strip().replace("\n", " ") if title_elem is not None else "Unknown"
            summary = summary_elem.text.replace("\n", " ").strip()[:400] if summary_elem is not None else ""
            paper_url = id_elem.text if id_elem is not None else ""
            date = published.text[:10] if published is not None else ""

            results.append({
                "source": "arxiv",
                "title": title,
                "url": paper_url,
                "snippet": f"Published: {date}",
                "excerpt": summary,
            })
    except Exception as exc:
        logger.warning(f"arXiv search failed: {exc}")

    return results


# ============================================================
# Main Search Function
# ============================================================
def search_topic(query: str, max_results: int = 5) -> list[dict]:
    """Comprehensive search across multiple knowledge bases.

    Searches in order:
    1. DuckDuckGo (web)
    2. Wikipedia (encyclopedia)
    3. arXiv (academic papers)

    Returns combined, deduplicated results.
    """
    logger.info(f"Researching: {query}")

    all_results = []
    seen_urls = set()

    # 1. Web search
    web_results = _search_ddg(query, max_results=max_results)
    all_results.extend(_filter_results(web_results, seen_urls))

    # 2. Wikipedia
    wiki_results = search_wikipedia(query, max_results=2)
    all_results.extend(_filter_results(wiki_results, seen_urls))

    # 3. arXiv (for technical topics)
    technical_keywords = ["quantum", "machine learning", "ai", "neural", "algorithm", "physics", "math", "computing", "engineering", "robotics", "blockchain"]
    if any(kw in query.lower() for kw in technical_keywords):
        arxiv_results = search_arxiv(query, max_results=2)
        all_results.extend(_filter_results(arxiv_results, seen_urls))

    logger.info(f"Found {len(all_results)} results for: {query}")
    return all_results[:max_results]


def _filter_results(results: list[dict], seen_urls: set) -> list[dict]:
    """Filter out duplicates and low-quality results."""
    filtered = []
    for r in results:
        url = r.get("url", "")
        title = r.get("title", "")

        if url in seen_urls:
            continue
        seen_urls.add(url)

        if not title or len(title) < 3:
            continue
        if any(word in title.lower() for word in ['xxx', 'adult', 'porn', 'free download', 'torrent']):
            continue

        filtered.append(r)

    return filtered


# ============================================================
# Report Compilation
# ============================================================
def compile_report(topic: str, results: list[dict]) -> str:
    """Compile a comprehensive markdown report."""
    slug = topic.lower().replace(" ", "-").replace("/", "-")
    reports_dir = Path(config.REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{slug}.md"

    lines = [
        f"# {topic}",
        "",
        f"**Compiled:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Sources:** {len(results)}  ",
        f"**Knowledge Bases:** DuckDuckGo, Wikipedia, arXiv  ",
        "",
        "=" * 60,
        "",
    ]

    # Group by source
    sources = {"web": [], "wikipedia": [], "arxiv": []}
    for r in results:
        source = r.get("source", "web")
        if source in sources:
            sources[source].append(r)

    # Add sections
    section_titles = {
        "web": "## Web Results",
        "wikipedia": "## Wikipedia",
        "arxiv": "## Academic Papers (arXiv)",
    }

    for source_name, items in sources.items():
        if not items:
            continue

        lines.append(section_titles.get(source_name, "## Results"))
        lines.append("")

        for i, item in enumerate(items, 1):
            lines.append(f"### {i}. {item['title']}")
            lines.append("")
            lines.append(f"**URL:** [{item['url']}]({item['url']})")
            lines.append("")
            if item.get("snippet"):
                lines.append(f"**Preview:** {item['snippet']}")
                lines.append("")
            if item.get("excerpt"):
                lines.append(f"> {item['excerpt']}")
                lines.append("")
            lines.append("---")
            lines.append("")

    # Summary section
    lines.append("## Summary")
    lines.append("")
    if results:
        lines.append(f"This report on **{topic}** was compiled from {len(results)} sources including web searches, Wikipedia, and academic papers.")
        lines.append("")
        lines.append("For the most current and detailed information, please refer to the sources listed above.")
    else:
        lines.append("*Web search returned no results. The LLM will provide knowledge from its training data.*")
    lines.append("")

    markdown = "\n".join(lines)
    report_path.write_text(markdown, encoding="utf-8")

    logger.info(f"Report saved to: {report_path}")
    return str(report_path.resolve())


# ============================================================
# Demo
# ============================================================
if __name__ == "__main__":
    demo_topics = ["artificial intelligence", "quantum computing", "climate change"]

    for topic in demo_topics:
        print(f"\n{'='*60}")
        print(f"Searching: {topic}")
        print(f"{'='*60}")

        results = search_topic(topic, max_results=5)
        report_file = compile_report(topic, results)

        print(f"\nFound {len(results)} results:")
        for i, r in enumerate(results[:5], 1):
            print(f"\n{i}. [{r['source']}] {r['title']}")
            print(f"   {r['url'][:70]}...")

        print(f"\nReport saved to: {report_file}")
