"""
Self-Learning Module for PLUTO v2.

ALWAYS searches the internet for answers - never relies solely on training data.
Mimics the behavior of Claude, ChatGPT, and Gemini by fetching current information.
"""

import logging
import time
from typing import List

from core.web_search import get_web_search
from core.brain import LLMReasoner
from core.knowledge_base import get_knowledge_base

logger = logging.getLogger(__name__)


class SelfLearner:
    """AI that ALWAYS searches the internet for current information."""

    def __init__(self):
        self.kb = get_knowledge_base()
        self.llm = LLMReasoner()
        self.search = get_web_search()

        # Topics that benefit extra search depth
        self.deep_search_topics = [
            "quantum", "machine learning", "ai", "climate", "space",
            "mars", "nasa", "physics", "biology", "medicine",
            "technology", "computing", "research", "study",
        ]

    def answer(self, query: str) -> str:
        """
        Always search the internet and provide a comprehensive answer.
        Never says "I don't know" - always finds information.
        """
        logger.info(f"SelfLearner: Answering '{query}'")

        # Determine search depth
        is_deep = any(kw in query.lower() for kw in self.deep_search_topics)
        max_results = 10 if is_deep else 7

        # Search the internet
        results = self.search.search(query, max_results=max_results, force_search=True)

        logger.info(f"SelfLearner: Found {len(results)} results for '{query}'")

        # Store important results
        for result in results[:5]:
            self.kb.store_knowledge(
                query=query,
                source=result.get('source', 'web'),
                title=result.get('title', 'Unknown'),
                content=result.get('excerpt', result.get('snippet', '')),
                url=result.get('url', ''),
                tags=self._extract_tags(query),
            )

        # Generate comprehensive answer
        answer = self._generate_answer(query, results)

        # Increment usage
        for entry in self.kb.get_relevant_knowledge(query, limit=5):
            self.kb.increment_usage(entry['id'])

        return answer

    def _generate_answer(self, query: str, results: List[dict]) -> str:
        """Generate a comprehensive answer using search results."""

        # Build rich context from search results
        context_parts = []
        for i, result in enumerate(results[:5], 1):
            title = result.get('title', 'Untitled')
            excerpt = result.get('excerpt', result.get('snippet', ''))
            url = result.get('url', '')

            if excerpt:
                context_parts.append(f"[Source {i}: {title}]({url})\n{excerpt}")
            else:
                context_parts.append(f"[Source {i}: {title}]({url})\nNo detailed excerpt available.")

        context = "\n\n---\n\n".join(context_parts)

        # Create a comprehensive prompt
        prompt = f"""You are PLUTO, an AI assistant that provides accurate, up-to-date information by researching the internet.

Question: {query}

Research Results (from live web search):
{context}

Based on this research, provide a comprehensive, well-structured answer to the question. Include:
1. A clear direct answer
2. Key facts and details
3. Relevant context and background
4. Any important nuances or caveats

If the research doesn't fully cover the question, still provide the best answer you can based on what you found, and note any gaps.

IMPORTANT: Never say "I don't know" or "I couldn't find information." Always provide a helpful answer based on the research above."""

        try:
            answer = self.llm.reason(prompt)
            if answer and len(answer) > 20:
                # Clean up the answer
                answer = answer.strip()
                # Remove any "[Source" references that might leak
                answer = answer.replace('[Source', 'Source:')
                return answer
        except Exception as exc:
            logger.error(f"Answer generation failed: {exc}")

        # Fallback: generate from snippets only
        return self._answer_from_snippets(query, results)

    def _answer_from_snippets(self, query: str, results: List[dict]) -> str:
        """Generate answer from snippets when full content isn't available."""
        snippets = []
        for i, r in enumerate(results[:5], 1):
            snippet = r.get('snippet', r.get('excerpt', ''))
            if snippet:
                snippets.append(f"{i}. {r.get('title', 'Untitled')}: {snippet}")

        if not snippets:
            # Last resort: just give a direct answer
            try:
                return self.llm.reason(f"Provide a concise, accurate answer to: {query}")
            except:
                return f"Here's what I can tell you about '{query}': This is an interesting topic. Would you like me to search for more specific information?"

        context = "\n\n".join(snippets)
        prompt = f"""Based on these search results, answer the question: "{query}"

Results:
{context}

Provide a clear, informative answer."""

        try:
            answer = self.llm.reason(prompt)
            return answer if answer and len(answer) > 10 else self._format_snippets(snippets)
        except:
            return self._format_snippets(snippets)

    def _format_snippets(self, snippets: List[str]) -> str:
        """Format search snippets into a readable answer."""
        if not snippets:
            return "I searched but couldn't find specific information. Please try rephrasing your question."

        lines = ["Here's what I found:\n"]
        for snippet in snippets[:5]:
            lines.append(f"- {snippet}")

        return "\n".join(lines)

    def _extract_tags(self, query: str) -> List[str]:
        """Extract relevant tags from query."""
        tags = []
        query_lower = query.lower()

        tag_map = {
            'ai': ['artificial intelligence', 'machine learning', 'neural network', 'deep learning'],
            'quantum': ['quantum', 'qubit', 'superposition', 'entanglement'],
            'climate': ['climate', 'environment', 'sustainability', 'green energy'],
            'space': ['space', 'mars', 'nasa', 'exploration', 'astronomy'],
            'tech': ['technology', 'computer', 'software', 'coding', 'programming'],
            'science': ['science', 'physics', 'chemistry', 'biology'],
            'medicine': ['medicine', 'health', 'medical', 'biology', 'gene'],
        }

        for tag, keywords in tag_map.items():
            if any(kw in query_lower for kw in keywords):
                tags.append(tag)

        return tags

    def train_on_topic(self, topic: str) -> dict:
        """Explicitly train the AI on a specific topic."""
        logger.info(f"Training on topic: {topic}")

        # Search thoroughly
        results = self.search.search(topic, max_results=10, force_search=True)

        # Store all results
        stored = []
        for result in results:
            entry = self.kb.store_knowledge(
                query=topic,
                source=result.get('source', 'web'),
                title=result.get('title', 'Unknown'),
                content=result.get('excerpt', result.get('snippet', '')),
                url=result.get('url', ''),
                tags=[topic.lower().replace(' ', '_')],
            )
            stored.append(entry)

        # Generate summary
        if results:
            context = "\n\n".join([
                f"[{i}] {r.get('title', 'Unknown')}: {r.get('excerpt', r.get('snippet', ''))[:300]}"
                for i, r in enumerate(results[:5], 1)
            ])

            prompt = f"Summarize the key facts about '{topic}' based on this research:\n\n{context}"
            try:
                summary = self.llm.reason(prompt)
            except:
                summary = "Training complete with web research."
        else:
            summary = "Could not find results for this topic."

        return {
            'topic': topic,
            'sources_found': len(results),
            'entries_stored': len(stored),
            'summary': summary[:500] if summary else '',
        }

    def get_learning_stats(self) -> dict:
        """Return statistics about the learning system."""
        kb_stats = self.kb.get_stats()
        return {
            **kb_stats,
            'learning_enabled': True,
            'search_strategies': ['DuckDuckGo', 'Wikipedia', 'Site-specific'],
        }


# Singleton instance
_learner_instance = None

def get_self_learner() -> SelfLearner:
    """Get or create the singleton SelfLearner instance."""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = SelfLearner()
    return _learner_instance
