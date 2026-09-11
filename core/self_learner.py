"""
Self-Learning Module for PLUTO v2.

Searches the internet when available, falls back to knowledge base + LLM
when offline. Works like Claude/ChatGPT online, and provides solid answers
from training data when offline.
"""

import logging
import time
import socket
from typing import List

from core.research.engine import get_research_engine
from core.brain import LLMReasoner
from core.knowledge_base import get_knowledge_base
from core import config

logger = logging.getLogger(__name__)


class SelfLearner:
    """AI that searches internet when available, uses KB + LLM when offline."""

    def __init__(self):
        self.kb = get_knowledge_base()
        self.llm = LLMReasoner()
        self.search = get_research_engine()

        # Topics that benefit extra search depth
        self.deep_search_topics = [
            "quantum", "machine learning", "ai", "climate", "space",
            "mars", "nasa", "physics", "biology", "medicine",
            "technology", "computing", "research", "study",
        ]

    def is_online(self) -> bool:
        """Check if internet is available."""
        if config.OFFLINE_MODE:
            return False
        try:
            # Try to reach a reliable host
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            try:
                socket.create_connection(("1.1.1.1", 53), timeout=2)
                return True
            except OSError:
                return False

    def answer(self, query: str) -> str:
        """
        Provide answer using internet if available, otherwise KB + LLM.
        """
        logger.info(f"SelfLearner: Answering '{query}'")

        # Check if we should use online mode
        if self.is_online():
            return self._answer_online(query)
        else:
            return self._answer_offline(query)

    def _answer_online(self, query: str) -> str:
        """Answer using internet search (like Claude/ChatGPT)."""
        logger.info(f"SelfLearner: Online mode - searching for '{query}'")

        # Determine search depth
        is_deep = any(kw in query.lower() for kw in self.deep_search_topics)
        max_results = 10 if is_deep else 7

        # Search the internet
        research_result = self.search.search(query, max_results=max_results, depth='standard')
        results = research_result.documents

        logger.info(f"SelfLearner: Found {len(results)} results for '{query}'")

        # Store important results
        for result in results[:5]:
            self.kb.store_knowledge(
                query=query,
                source=getattr(result, 'source', 'web'),
                title=getattr(result, 'title', 'Unknown'),
                content=getattr(result, 'excerpt', getattr(result, 'snippet', '')),
                url=getattr(result, 'url', ''),
                tags=self._extract_tags(query),
            )

        # Generate comprehensive answer
        answer = self._generate_answer(query, research_result)

        # Increment usage
        for entry in self.kb.get_relevant_knowledge(query, limit=5):
            self.kb.increment_usage(entry.get('id', ''))

        return answer

    def _answer_offline(self, query: str) -> str:
        """Answer using knowledge base and LLM training data."""
        logger.info(f"SelfLearner: Offline mode - using KB + LLM for '{query}'")

        # First, check if we have relevant knowledge
        relevant = self.kb.get_relevant_knowledge(query, limit=3)

        if relevant:
            # We have stored knowledge - use it
            answer = self._answer_from_knowledge(query, relevant)
        else:
            # No stored knowledge - use LLM's training data
            answer = self._answer_from_llm(query)

        return answer

    def _answer_from_knowledge(self, query: str, knowledge: List[dict]) -> str:
        """Generate answer from stored knowledge."""
        context_parts = []
        for i, entry in enumerate(knowledge, 1):
            title = entry.get('title', 'Untitled')
            content = entry.get('content', entry.get('excerpt', ''))
            url = entry.get('url', '')

            if content:
                context_parts.append(f"[Source {i}: {title}]({url})\n{content[:500]}")
            else:
                context_parts.append(f"[Source {i}: {title}]({url})\nNo detailed content available.")

        context = "\n\n---\n\n".join(context_parts)

        prompt = f"""You are PLUTO, an AI assistant. You have the following stored knowledge about "{query}":

{context}

Based on this knowledge, provide a clear, accurate answer to the question. If the knowledge doesn't fully answer the question, provide the best answer you can from what you have."""

        try:
            answer = self.llm.reason(prompt)
            if answer and len(answer) > 20:
                return answer
        except Exception as e:
            logger.error(f"Knowledge-based answer failed: {e}")

        # Fallback to just formatting the knowledge
        return self._format_knowledge_answer(query, knowledge)

    def _answer_from_llm(self, query: str) -> str:
        """Generate answer from LLM training data (no internet)."""
        prompt = f"""You are PLUTO, an AI assistant running in offline mode. You don't have internet access, so you must answer based on your training knowledge.

Question: {query}

Please provide a comprehensive, accurate answer based on what you know. Include:
1. A clear direct answer
2. Key facts and details
3. Relevant context and background

Be helpful and informative even without live research."""

        try:
            answer = self.llm.reason(prompt)
            if answer and len(answer) > 20:
                return f"(Offline mode - answer from training data)\n\n{answer}"
        except Exception as e:
            logger.error(f"LLM answer failed: {e}")

        return f"I'm currently offline and cannot search the internet. Based on my training, here's what I know about '{query}': This is an interesting topic. Would you like to connect to the internet for more current information?"

    def _generate_answer(self, query: str, research_result) -> str:
        """Generate comprehensive answer from research results."""
        results = research_result.documents

        # Build rich context from search results
        context_parts = []
        for i, result in enumerate(results[:5], 1):
            title = getattr(result, 'title', 'Untitled')
            excerpt = getattr(result, 'excerpt', getattr(result, 'snippet', ''))
            url = getattr(result, 'url', '')

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
            snippet = getattr(r, 'snippet', getattr(r, 'excerpt', ''))
            if snippet:
                snippets.append(f"{i}. {getattr(r, 'title', 'Untitled')}: {snippet}")

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

    def _format_knowledge_answer(self, query: str, knowledge: List[dict]) -> str:
        """Format stored knowledge into an answer."""
        lines = [f"Based on my stored knowledge about '{query}':\n"]
        for i, entry in enumerate(knowledge[:5], 1):
            title = entry.get('title', 'Untitled')
            content = entry.get('content', entry.get('excerpt', ''))
            if content:
                lines.append(f"{i}. **{title}**: {content[:200]}...")
            else:
                lines.append(f"{i}. **{title}**: (No detailed content)")
        return "\n".join(lines)

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

        # Only search if online
        if self.is_online():
            results = self.search.search(topic, max_results=10, force_search=True)
        else:
            results = []
            logger.warning(f"Cannot train on '{topic}' - offline mode")

        # Store all results
        stored = []
        for result in results:
            entry = self.kb.store_knowledge(
                query=topic,
                source=getattr(result, 'source', 'web'),
                title=getattr(result, 'title', 'Unknown'),
                content=getattr(result, 'excerpt', getattr(result, 'snippet', '')),
                url=getattr(result, 'url', ''),
                tags=[topic.lower().replace(' ', '_')],
            )
            stored.append(entry)

        # Generate summary
        if results:
            context = "\n\n".join([
                f"[{i}] {getattr(r, 'title', 'Unknown')}: {getattr(r, 'excerpt', getattr(r, 'snippet', ''))[:300]}"
                for i, r in enumerate(results[:5], 1)
            ])

            prompt = f"Summarize the key facts about '{topic}' based on this research:\n\n{context}"
            try:
                summary = self.llm.reason(prompt)
            except:
                summary = "Training complete with web research."
        else:
            summary = "Could not find results for this topic (offline mode)."

        return {
            'topic': topic,
            'sources_found': len(results),
            'entries_stored': len(stored),
            'summary': summary[:500] if summary else '',
            'offline': not self.is_online()
        }

    def get_learning_stats(self) -> dict:
        """Return statistics about the learning system."""
        kb_stats = self.kb.get_stats()
        return {
            **kb_stats,
            'learning_enabled': True,
            'search_strategies': ['DuckDuckGo', 'Wikipedia', 'Site-specific'],
            'offline_mode': not self.is_online(),
        }


# Singleton instance
_learner_instance = None

def get_self_learner() -> SelfLearner:
    """Get or create the singleton SelfLearner instance."""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = SelfLearner()
    return _learner_instance

    def _generate_answer(self, query: str, research_result) -> str:
        results = research_result.documents
        """Generate a comprehensive answer using search results."""

        # Build rich context from search results
        context_parts = []
        for i, result in enumerate(results[:5], 1):
            title = getattr(result, 'title', 'Untitled')
            excerpt = getattr(result, 'excerpt', getattr(result, 'snippet', ''))
            url = getattr(result, 'url', '')

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
