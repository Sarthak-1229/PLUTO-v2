"""
Self-Learning Knowledge Base for PLUTO v2.

Stores searched information and retrieves it when answering questions.
Enables the AI to learn from the internet and improve over time.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


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

    def get_relevant_knowledge(self, query: str, limit: int = 3) -> List[dict]:
        """Find relevant stored knowledge for a query."""
        query_lower = query.lower()
        matching = []

        for entry in self.knowledge["entries"]:
            # Check if query terms appear in title, content, or tags
            score = 0
            for term in query_lower.split():
                if len(term) > 2:  # Skip short words
                    if term in entry.get("title", "").lower():
                        score += 3
                    if term in entry.get("content", "").lower():
                        score += 1
                    if term in [tag.lower() for tag in entry.get("tags", [])]:
                        score += 2

            if score > 0:
                matching.append((score, entry))

        # Sort by relevance score
        matching.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in matching[:limit]]

    def store_knowledge(self, query: str, source: str, title: str,
                        content: str, url: str, tags: List[str] = None):
        """Store new knowledge entry."""
        entry = {
            "id": str(int(time.time() * 1000)),
            "query": query,
            "source": source,
            "title": title,
            "content": content[:2000],  # Limit content length
            "url": url,
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
            "sources": list(set(e.get("source", "") for e in self.knowledge["entries"])),
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
