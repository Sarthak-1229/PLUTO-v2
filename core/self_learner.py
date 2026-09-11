"""
Self-Learning Module for PLUTO v2.

When the AI encounters a question outside its knowledge base,
it searches the internet, stores the knowledge, and uses it for future answers.
"""

import json
import logging
import re
from typing import Optional, List

from core.researcher import search_topic, compile_report
from core.brain import LLMReasoner
from core.knowledge_base import get_knowledge_base

logger = logging.getLogger(__name__)


class SelfLearner:
    """Enables the AI to learn from the internet and improve over time."""

    def __init__(self):
        self.kb = get_knowledge_base()
        self.llm = LLMReasoner()

        # Topics the AI should always have knowledge about
        self.high_priority_topics = [
            "artificial intelligence", "machine learning", "deep learning",
            "quantum computing", "climate change", "renewable energy",
            "space exploration", "mars", "biology", "physics",
            "mathematics", "history", "technology", "coding",
        ]

    def should_learn(self, query: str) -> bool:
        """Determine if we should search the internet for this query."""
        # Always learn for high-priority topics
        query_lower = query.lower()
        for topic in self.high_priority_topics:
            if topic in query_lower:
                return True

        # Check if we already know the answer
        relevant = self.kb.get_relevant_knowledge(query, limit=1)
        if relevant:
            return False  # We already have this knowledge

        # Default: search for anything
        return True

    def learn_and_answer(self, query: str) -> str:
        """Learn from the internet and provide an improved answer."""
        logger.info(f"SelfLearner: Searching for knowledge about: {query}")

        # 1. Search the internet
        results = search_topic(query, max_results=5)

        if not results:
            logger.warning(f"SelfLearner: No results found for '{query}'")
            return self._fallback_answer(query)

        # 2. Store the knowledge
        for result in results:
            self.kb.store_knowledge(
                query=query,
                source=result.get("source", "web"),
                title=result.get("title", "Unknown"),
                content=result.get("excerpt", result.get("snippet", "")),
                url=result.get("url", ""),
                tags=self._extract_tags(query, result),
            )

        # 3. Generate an improved answer using learned knowledge
        answer = self._generate_improved_answer(query, results)

        # 4. Increment usage stats
        for entry in self.kb.get_relevant_knowledge(query, limit=5):
            self.kb.increment_usage(entry["id"])

        logger.info(f"SelfLearner: Learned and answered '{query}'")
        return answer

    def _generate_improved_answer(self, query: str, results: List[dict]) -> str:
        """Generate a better answer using the learned information."""
        # Build a context from search results
        context_parts = []
        for i, result in enumerate(results[:3], 1):
            excerpt = result.get("excerpt", result.get("snippet", ""))
            if excerpt:
                context_parts.append(f"[Source {i}] {excerpt}")

        if not context_parts:
            return self._fallback_answer(query)

        context = "\n\n".join(context_parts)

        # Ask LLM to synthesize an answer from the context
        prompt = f"""Based on the following research information, answer the question: "{query}"

Research Context:
{context}

Please provide a comprehensive, accurate answer based on this research. If the research doesn't fully answer the question, acknowledge that and provide the best answer you can."""

        try:
            answer = self.llm.reason(prompt)
            if answer and len(answer) > 20:
                return answer
        except Exception as exc:
            logger.error(f"SelfLearner: LLM generation failed: {exc}")

        return self._fallback_answer(query)

    def _fallback_answer(self, query: str) -> str:
        """Provide a fallback answer when learning fails."""
        # Try the standard LLM answer
        try:
            answer = self.llm.reason(f"Please answer this question: {query}")
            if answer and len(answer) > 10:
                return f"(I searched but didn't find specific information. Here's what I know: {answer})"
        except:
            pass

        return f"I couldn't find specific information about '{query}' through my research. Could you try rephrasing your question or ask about a different topic?"

    def _extract_tags(self, query: str, result: dict) -> List[str]:
        """Extract relevant tags from query and result."""
        tags = []

        # Extract from query
        query_lower = query.lower()
        tag_keywords = {
            "ai": ["artificial intelligence", "machine learning", "neural network"],
            "quantum": ["quantum computing", "qubit", "superposition"],
            "climate": ["climate change", "global warming", "environment"],
            "space": ["space", "mars", "nasa", "exploration"],
            "tech": ["technology", "computer", "software", "coding"],
            "science": ["science", "physics", "chemistry", "biology"],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in query_lower for kw in keywords):
                tags.append(tag)

        # Add source as tag
        source = result.get("source", "")
        if source:
            tags.append(source)

        return list(set(tags))  # Remove duplicates

    def get_learning_stats(self) -> dict:
        """Return statistics about the learning system."""
        kb_stats = self.kb.get_stats()
        return {
            **kb_stats,
            "learning_enabled": True,
            "high_priority_topics": len(self.high_priority_topics),
        }

    def train_on_topic(self, topic: str) -> dict:
        """Explicitly train the AI on a specific topic."""
        logger.info(f"Training on topic: {topic}")

        # Search for the topic
        results = search_topic(topic, max_results=5)

        # Store each result
        stored = []
        for result in results:
            entry = self.kb.store_knowledge(
                query=topic,
                source=result.get("source", "web"),
                title=result.get("title", "Unknown"),
                content=result.get("excerpt", result.get("snippet", "")),
                url=result.get("url", ""),
                tags=[topic.lower().replace(" ", "_")],
            )
            stored.append(entry)

        # Generate a summary
        if results:
            context = "\n\n".join([
                f"[{i}] {r.get('title', 'Unknown')}: {r.get('excerpt', r.get('snippet', ''))[:200]}"
                for i, r in enumerate(results[:3], 1)
            ])

            prompt = f"Summarize the key facts about '{topic}' based on this research:\n\n{context}"
            try:
                summary = self.llm.reason(prompt)
            except:
                summary = "Training complete."
        else:
            summary = "No results found for this topic."

        return {
            "topic": topic,
            "sources_found": len(results),
            "entries_stored": len(stored),
            "summary": summary,
        }


# Singleton instance
_learner_instance = None

def get_self_learner() -> SelfLearner:
    """Get or create the singleton SelfLearner instance."""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = SelfLearner()
    return _learner_instance
