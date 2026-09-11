"""
Module for researching topics and compiling reports.
"""

import time
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import ddg
from pathlib import Path

# Assuming core.config.REPORTS_DIR is defined elsewhere in the project
from core import config


def search_topic(query: str, max_results: int = 5) -> list:
    """Search for information on the given topic.

    Uses DuckDuckGo search via ``duckduckgo_search`` to fetch result metadata.
    For each result it attempts to fetch the page and extracts the first paragraph as an excerpt.
    Network errors are retried with exponential back‑off up to three attempts.

    Returns a list of dictionaries with the keys:
        - title:   Title of the result.
        - url:     URL of the result.
        - snippet: Short snippet provided by the search engine.
        - excerpt: First paragraph from the page (or ``None`` if unavailable).
    """
    raw_results = ddg(query, max_results=max_results) or []
    enriched = []
    for res in raw_results:
        title = res.get("title") or ""
        url = res.get("href") or res.get("url") or ""
        snippet = res.get("body") or ""
        excerpt = None
        if url:
            backoff = 1
            for attempt in range(3):
                try:
                    resp = requests.get(url, timeout=3)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Find the first non‑empty paragraph
                    p = soup.find("p", string=lambda text: text and text.strip())
                    if p:
                        excerpt = p.get_text(strip=True)
                    break  # success, stop retrying
                except requests.exceptions.RequestException:
                    if attempt < 2:
                        time.sleep(backoff)
                        backoff *= 2
                    else:
                        excerpt = None
        enriched.append({"title": title, "url": url, "snippet": snippet, "excerpt": excerpt})
    return enriched


def compile_report(topic: str, results: list) -> str:
    """Compile a markdown report for *topic* using *results*.

    The function creates a slug from the topic, writes a markdown file under
    ``core.config.REPORTS_DIR`` and returns the absolute path to the file.
    """
    slug = topic.lower().replace(" ", "-")
    reports_dir = Path(config.REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{slug}.md"

    # Build markdown content
    md_lines = [f"# {topic}", "", f"Report compiled for **{topic}**.", ""]
    md_lines.append("## Sources")
    for item in results:
        md_lines.append(f"- [{item.get('title', '')}]({item.get('url', '')})")
    md_lines.append("")
    md_lines.append("## Excerpts")
    for item in results:
        excerpt = item.get("excerpt")
        if excerpt:
            md_lines.append(f"> {excerpt}")
            md_lines.append("")
    markdown = "\n".join(md_lines)

    report_path.write_text(markdown, encoding="utf-8")
    return str(report_path.resolve())


if __name__ == "__main__":
    demo_topic = "Mars exploration"
    demo_results = search_topic(demo_topic)
    report_file = compile_report(demo_topic, demo_results)
    print(f"Report written to {report_file}")
