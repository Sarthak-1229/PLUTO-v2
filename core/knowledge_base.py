"""
Self-Learning Knowledge Base for PLUTO v2.

Stores searched information and retrieves it when answering questions.
Enables the AI to learn from the internet and improve over time.
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and',
    'any', 'are', 'aren\'t', 'as', 'at', 'be', 'because', 'been', 'before', 'being',
    'below', 'between', 'both', 'but', 'by', 'can', 'can\'t', 'cannot', 'could',
    'did', 'do', 'does', 'doing', 'don\'t', 'down', 'during', 'each', 'few', 'for',
    'from', 'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers',
    'herself', 'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'isn\'t',
    'it', 'its', 'itself', 'just', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor',
    'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours',
    'ourselves', 'out', 'over', 'own', 'same', 'she', 'should', 'so', 'some', 'such',
    'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there',
    'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up',
    'very', 'was', 'wasn\'t', 'we', 'were', 'what', 'when', 'where', 'which', 'while',
    'who', 'whom', 'why', 'with', 'won\'t', 'would', 'you', 'your', 'yours', 'yourself',
    'yourselves', 'tell', 'give', 'please', 'know', 'say', 'find'
}


class KnowledgeBase:
    """Stores and retrieves learned knowledge for the AI."""

    def __init__(self, db_path: str = "knowledge_db.json"):
        self.db_path = Path(db_path)
        self.knowledge = self._load()

    def _load(self) -> dict:
        """Load knowledge database from file."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning(f"Failed to load knowledge base: {exc}")
        return {"entries": [], "stats": {"total_searches": 0, "total_queries": 0}}

    def _save(self):
        """Save knowledge database to file."""
        try:
            self.db_path.write_text(
                json.dumps(self.knowledge, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as exc:
            logger.error(f"Failed to save knowledge base: {exc}")

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords excluding stopwords."""
        words = re.findall(r'\b[a-zA-Z0-9_\-]{3,}\b', text.lower())
        return [w for w in words if w not in STOPWORDS]

    def get_relevant_knowledge(self, query: str, limit: int = 3) -> List[dict]:
        """Find strictly relevant stored knowledge for a query."""
        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        matching = []

        for entry in self.knowledge["entries"]:
            title = entry.get("title", "").lower()
            content = entry.get("content", "").lower()
            original_query = entry.get("query", "").lower()
            tags = [t.lower() for t in entry.get("tags", [])]

            score = 0
            matched_keywords = 0

            for kw in keywords:
                kw_matched = False
                if kw in original_query:
                    score += 6
                    kw_matched = True
                if kw in title:
                    score += 4
                    kw_matched = True
                if any(kw in tag for tag in tags):
                    score += 3
                    kw_matched = True
                if kw in content:
                    score += 1
                    kw_matched = True

                if kw_matched:
                    matched_keywords += 1

            # Require either high keyword match ratio (>= 50%) or strong keyword overlap (score >= 8)
            match_ratio = matched_keywords / len(keywords) if keywords else 0
            if (match_ratio >= 0.5 and score >= 5) or score >= 10:
                matching.append((score, entry))

        # Sort by relevance score
        matching.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in matching[:limit]]

    def store_knowledge(self, query: str, source: str, title: str,
                        content: str, url: str, tags: List[str] = None):
        """Store new knowledge entry avoiding exact duplicates."""
        if not title and not content:
            return None

        # Check for near duplicates
        for existing in self.knowledge["entries"]:
            if url and existing.get("url") == url:
                existing["usage_count"] = existing.get("usage_count", 0) + 1
                self._save()
                return existing
            if title and existing.get("title") == title:
                return existing

        entry = {
            "id": str(int(time.time() * 1000)),
            "query": query,
            "source": source,
            "title": title,
            "content": (content or "")[:2000],  # Limit content length
            "url": url or "",
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "usage_count": 0,
        }

        self.knowledge["entries"].append(entry)
        self.knowledge["stats"]["total_searches"] += 1
        self._save()

        logger.info(f"Stored knowledge: {title} from {source}")
        return entry

    def increment_usage(self, entry_id: str):
        """Mark a knowledge entry as used."""
        for entry in self.knowledge["entries"]:
            if entry["id"] == entry_id:
                entry["usage_count"] = entry.get("usage_count", 0) + 1
                self._save()
                return
        logger.warning(f"Knowledge entry not found: {entry_id}")

    def get_stats(self) -> dict:
        """Return knowledge base statistics."""
        return {
            "total_entries": len(self.knowledge["entries"]),
            "total_searches": self.knowledge["stats"]["total_searches"],
            "total_queries": self.knowledge["stats"]["total_queries"],
            "sources": list(set(e.get("source", "") for e in self.knowledge["entries"] if e.get("source"))),
        }

    def clear_old_entries(self, max_age_days: int = 30):
        """Remove entries older than max_age_days with low usage."""
        cutoff = time.time() - (max_age_days * 86400)
        original_count = len(self.knowledge["entries"])

        self.knowledge["entries"] = [
            e for e in self.knowledge["entries"]
            if datetime.fromisoformat(e["created_at"]).timestamp() > cutoff
            or e.get("usage_count", 0) > 0
        ]

        if len(self.knowledge["entries"]) != original_count:
            self._save()
            logger.info(f"Cleaned {original_count - len(self.knowledge['entries'])} old entries")


# Singleton instance
_kb_instance = None

def get_knowledge_base() -> KnowledgeBase:
    """Get or create the singleton KnowledgeBase instance."""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance
