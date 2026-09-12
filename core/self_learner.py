"""
Self-Learning Module for PLUTO v2.

Searches the internet when available, falls back to knowledge base + LLM
when offline. Response length adapts to question complexity.
"""

import logging
import re
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
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            try:
                socket.create_connection(("1.1.1.1", 53), timeout=2)
                return True
            except OSError:
                return False

    def answer(self, query: str) -> str:
        """Provide answer using internet if available, otherwise KB + LLM."""
        logger.info(f"SelfLearner: Answering '{query}'")

        # Detect question complexity
        is_simple = self._is_simple_question(query)
        is_complex = self._is_complex_question(query)

        if self.is_online():
            return self._answer_online(query, is_simple=is_simple, is_complex=is_complex)
        else:
            return self._answer_offline(query, is_simple=is_simple, is_complex=is_complex)

    def _is_simple_question(self, query: str) -> bool:
        """Check if this is a simple question needing short answer."""
        simple_patterns = [
            r'^\s*(hi|hello|hey|how are you|good morning|good evening)\s*$',
            r'^\s*(what is 2\+2|what is \d+\s*[\+\-\*/]\s*\d+)\s*$',
            r'^\s*(when was|what year)\s+',
            r'^\s*(who is|who was)\s+',
            r'^\s*(where is|where was)\s+',
            r'^\s*(define|what is the definition of)\s+',
            r'^\s*(translate|convert)\s+',
            r'^\s*(tell me a|give me a)\s+(joke|fact|fun fact)\s*$',
            r'^\s*(is |are )\s+',
            r'^\s*(yes or no|true or false)\s*',
        ]

        query_lower = query.lower().strip()
        for pattern in simple_patterns:
            if re.search(pattern, query_lower):
                return True

        # Very short questions
        words = query.split()
        if len(words) <= 3:
            return True

        return False

    def _is_complex_question(self, query: str) -> bool:
        """Check if this is a complex question needing detailed answer."""
        complex_patterns = [
            r'\b(explain|describe|elaborate|detail)\b',
            r'\b(how does|how do|how did)\b',
            r'\b(compare|contrast)\b',
            r'\b(create a report|write a report)\b',
            r'\b(research|analyze|investigate)\b',
            r'\b(why|because)\b.*\bexplain\b',
            r'\b(list all|list everything)\b',
            r'\b(factors|reasons|causes)\b',
            r'\b(history of|background of)\b',
            r'\b(importance|significance|impact)\b',
        ]

        query_lower = query.lower()
        for pattern in complex_patterns:
            if re.search(pattern, query_lower):
                return True

        return False

    def _answer_online(self, query: str, is_simple: bool = False, is_complex: bool = False) -> str:
        """Answer using internet search with adaptive length."""
        logger.info(f"Online mode - searching for '{query}' (simple={is_simple})")

        # Search fewer results for simple questions
        max_results = 3 if is_simple else 7

        research_result = self.search.search(query, max_results=max_results, depth='standard')
        results = research_result.documents

        # Store results
        for result in results[:5]:
            self.kb.store_knowledge(
                query=query,
                source=getattr(result, 'source', 'web'),
                title=getattr(result, 'title', 'Unknown'),
                content=getattr(result, 'excerpt', getattr(result, 'snippet', '')),
                url=getattr(result, 'url', ''),
                tags=self._extract_tags(query),
            )

        return self._generate_answer(query, research_result, is_simple=is_simple)

    def _answer_offline(self, query: str, is_simple: bool = False, is_complex: bool = False) -> str:
        """Answer using knowledge base and LLM training data."""
        logger.info(f"Offline mode - using KB + LLM for '{query}'")

        relevant = self.kb.get_relevant_knowledge(query, limit=3)

        if relevant:
            return self._answer_from_knowledge(query, relevant, is_simple=is_simple)
        else:
            return self._answer_from_llm(query, is_simple=is_simple)

    def _answer_from_knowledge(self, query: str, knowledge: List[dict], is_simple: bool = False) -> str:
        """Generate answer from stored knowledge with appropriate length."""
        context_parts = []
        for i, entry in enumerate(knowledge, 1):
            title = entry.get('title', 'Untitled')
            content = entry.get('content', entry.get('excerpt', ''))
            url = entry.get('url', '')

            if content:
                context_parts.append(f"[Source {i}: {title}]({url})\n{content[:500]}")
            else:
                context_parts.append(f"[Source {i}: {title}]({url})\nNo detailed content.")

        context = "\n\n---\n\n".join(context_parts)

        if is_simple:
            prompt = f"""You are PLUTO, an AI assistant. You have the following stored knowledge about "{query}":

{context}

Provide a BRIEF, CONCISE answer. One sentence is enough if possible. No elaboration needed."""
        else:
            prompt = f"""You are PLUTO, an AI assistant. You have the following stored knowledge about "{query}":

{context}

Provide a clear, accurate answer to the question."""

        try:
            answer = self.llm.reason(prompt)
            if answer and len(answer) > 20:
                return answer
        except Exception as e:
            logger.error(f"Knowledge answer failed: {e}")

        return self._format_knowledge_answer(query, knowledge, is_simple=is_simple)

    def _answer_from_llm(self, query: str, is_simple: bool = False) -> str:
        """Generate answer from LLM training data with appropriate length."""
        if is_simple:
            prompt = f"""You are PLUTO, an AI assistant in offline mode.

Question: {query}

IMPORTANT: Keep your answer VERY BRIEF. One sentence maximum. Just the direct answer."""
        else:
            prompt = f"""You are PLUTO, an AI assistant in offline mode.

Question: {query}

Provide a helpful, accurate answer based on your knowledge."""

        try:
            answer = self.llm.reason(prompt)
            if answer and len(answer) > 20:
                return answer
        except Exception as e:
            logger.error(f"LLM answer failed: {e}")

        return f"Based on my knowledge: {query}"

    def _generate_answer(self, query: str, research_result, is_simple: bool = False) -> str:
        """Generate answer from research results with adaptive length."""
        results = research_result.documents

        if is_simple:
            # For simple questions, just give a direct answer
            prompt = f"""Based on this research, answer this question concisely in 1-2 sentences: "{query}"

Research snippets:
"""
            for i, result in enumerate(results[:3], 1):
                snippet = getattr(result, 'snippet', getattr(result, 'excerpt', ''))
                if snippet:
                    prompt += f"\n{i}. {snippet[:150]}..."
        else:
            # For complex questions, provide comprehensive answer
            context_parts = []
            for i, result in enumerate(results[:5], 1):
                title = getattr(result, 'title', 'Untitled')
                excerpt = getattr(result, 'excerpt', getattr(result, 'snippet', ''))
                url = getattr(result, 'url', '')

                if excerpt:
                    context_parts.append(f"[Source {i}: {title}]({url})\n{excerpt}")
                else:
                    context_parts.append(f"[Source {i}: {title}]({url})\nNo details.")

            context = "\n\n---\n\n".join(context_parts)
            prompt = f"""You are PLUTO, an AI assistant researching the internet.

Question: {query}

Research Results:
{context}

Provide a comprehensive, well-structured answer with key facts and context."""

        try:
            answer = self.llm.reason(prompt)
            if answer and len(answer) > 20:
                return answer.strip()
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")

        return self._answer_from_snippets(query, results)

    def _answer_from_snippets(self, query: str, results: List[dict]) -> str:
        """Generate answer from snippets when full content unavailable."""
        snippets = []
        for i, r in enumerate(results[:5], 1):
            snippet = getattr(r, 'snippet', getattr(r, 'excerpt', ''))
            if snippet:
                snippets.append(f"{i}. {getattr(r, 'title', 'Untitled')}: {snippet}")

        if not snippets:
            try:
                return self.llm.reason(f"Concise answer to: {query}")
            except:
                return f"Here's what I know: {query}"

        prompt = f"""Answer concisely based on these results for "{query}":
{chr(10).join(snippets[:3])}"""

        try:
            answer = self.llm.reason(prompt)
            return answer if answer and len(answer) > 10 else self._format_snippets(snippets)
        except:
            return self._format_snippets(snippets)

    def _format_knowledge_answer(self, query: str, knowledge: List[dict], is_simple: bool = False) -> str:
        """Format stored knowledge into answer."""
        if is_simple:
            # Just give direct answer
            return f"The answer is based on stored knowledge about '{query}'."
        else:
            lines = [f"Based on stored knowledge about '{query}':\n"]
            for i, entry in enumerate(knowledge[:3], 1):
                title = entry.get('title', 'Untitled')
                content = entry.get('content', entry.get('excerpt', ''))
                if content:
                    lines.append(f"{i}. **{title}**: {content[:200]}...")
            return "\n".join(lines)

    def _format_snippets(self, snippets: List[str]) -> str:
        """Format search snippets into answer."""
        if not snippets:
            return "No specific information found."

        lines = ["Here's what I found:\n"]
        for snippet in snippets[:3]:
            lines.append(f"- {snippet}")

        return "\n".join(lines)

    def _extract_tags(self, query: str) -> List[str]:
        """Extract relevant tags from query."""
        tags = []
        query_lower = query.lower()

        tag_map = {
            'ai': ['artificial intelligence', 'machine learning', 'neural network'],
            'quantum': ['quantum', 'qubit', 'superposition', 'entanglement'],
            'climate': ['climate', 'environment', 'sustainability'],
            'space': ['space', 'mars', 'nasa', 'exploration'],
            'tech': ['technology', 'computer', 'software', 'coding'],
            'science': ['science', 'physics', 'chemistry', 'biology'],
        }

        for tag, keywords in tag_map.items():
            if any(kw in query_lower for kw in keywords):
                tags.append(tag)

        return tags

    def get_learning_stats(self) -> dict:
        """Return statistics about the learning system."""
        kb_stats = self.kb.get_stats()
        return {
            **kb_stats,
            'learning_enabled': True,
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
