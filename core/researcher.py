"""
Module for researching topics and compiling reports.

Uses multiple strategies:
1. DuckDuckGo HTML search (when available)
2. LLM knowledge base (fallback)
3. Generates comprehensive report from available information
"""

import logging
import time
from pathlib import Path
from typing import Optional

from core import config

logger = logging.getLogger(__name__)


def search_topic(query: str, max_results: int = 5) -> list[dict]:
    """Search for information on the given topic.

    Tries multiple search methods and falls back to LLM knowledge if needed.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of dicts with keys: title, url, snippet, excerpt.
    """
    logger.info(f"Researching: {query}")

    # Try DuckDuckGo search first
    results = _search_ddg(query, max_results)

    # If no results, use LLM knowledge
    if not results:
        logger.info(f"No web results for '{query}', using LLM knowledge")
        results = _get_llm_knowledge(query)

    return results


def _search_ddg(query: str, max_results: int) -> list[dict]:
    """Search using DuckDuckGo HTML scraping."""
    results = []
    try:
        import requests
        from bs4 import BeautifulSoup

        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for i, result in enumerate(soup.select("result-link")[:max_results]):
            title_tag = result.select_one("a.result__a")
            url_tag = result.select_one("a.result__snippet")

            if title_tag and url_tag:
                title = title_tag.get_text(strip=True)
                href = title_tag.get("href", "")
                snippet = url_tag.get_text(strip=True)

                if title and href and len(title) > 3:
                    results.append({
                        "title": title,
                        "url": href,
                        "snippet": snippet[:200],
                        "excerpt": None,
                    })
    except Exception as exc:
        logger.warning(f"DDG search failed: {exc}")

    return results


def _get_llm_knowledge(query: str) -> list[dict]:
    """Generate knowledge-based results from LLM.

    This provides a fallback when web search is unavailable.
    """
    # Import here to avoid circular imports
    from core.brain import LLMReasoner

    reasoner = LLMReasoner()
    prompt = f"""Provide a comprehensive overview of "{query}".
Format your response as a structured report with:
1. Key facts and information
2. Important developments
3. Current state
4. Future outlook

Keep it concise but informative."""

    try:
        response = reasoner.reason(prompt)
        return [{
            "title": f"Knowledge Summary: {query}",
            "url": "(LLM Knowledge Base)",
            "snippet": response,
            "excerpt": response,
        }]
    except Exception as exc:
        logger.error(f"LLM knowledge generation failed: {exc}")
        return [{
            "title": f"Topic: {query}",
            "url": "(No sources available)",
            "snippet": "No information available.",
            "excerpt": "Unable to fetch information at this time.",
        }]


def compile_report(topic: str, results: list[dict]) -> str:
    """Compile a markdown report from search results.

    Args:
        topic: The research topic.
        results: List of search result dicts.

    Returns:
        Absolute path to the saved markdown file.
    """
    slug = topic.lower().replace(" ", "-").replace("/", "-")
    reports_dir = Path(config.REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{slug}.md"

    lines = [
        f"# {topic}",
        "",
        f"**Compiled:** {time.strftime('%Y-%m-%d %H:%M')}  ",
        f"**Sources:** {len(results)}  ",
        "",
        "---",
        "",
    ]

    # Add source list
    lines.append("## Sources")
    lines.append("")
    for i, item in enumerate(results, 1):
        lines.append(f"{i}. **{item['title']}**")
        if item.get('url') and item['url'] != '(No sources available)':
            lines.append(f"   - {item['url']}")
        if item.get('snippet'):
            lines.append(f"   - {item['snippet'][:150]}...")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Add excerpts
    lines.append("## Content")
    lines.append("")
    for item in results:
        if item.get("excerpt"):
            lines.append(f"### {item['title']}")
            lines.append("")
            lines.append(item['excerpt'])
            lines.append("")

    markdown = "\n".join(lines)
    report_path.write_text(markdown, encoding="utf-8")

    logger.info(f"Report saved to: {report_path}")
    return str(report_path.resolve())


if __name__ == "__main__":
    # Demo
    demo_topic = "quantum computing"
    demo_results = search_topic(demo_topic)
    report_file = compile_report(demo_topic, demo_results)
    print(f"Report written to {report_file}")
    print(f"\nFound {len(demo_results)} results:")
    for i, r in enumerate(demo_results[:5], 1):
        print(f"\n{i}. {r['title']}")
        print(f"   URL: {r.get('url', 'N/A')}")
        if r.get('excerpt'):
            print(f"   Excerpt: {r['excerpt'][:100]}...")
