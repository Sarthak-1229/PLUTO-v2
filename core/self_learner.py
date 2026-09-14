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
        """Provide answer using KB/LLM first, then internet if needed and available."""
        logger.info(f"SelfLearner: Answering '{query}'")
        query_stripped = query.strip()
        if not query_stripped:
            return "How can I assist you today?"

        query_lower = query_stripped.lower()

        # 0. Instant handling for basic greetings & simple math
        if re.match(r'^(hi|hello|hey|hii|howdy|good morning|good afternoon|good evening)\b', query_lower):
            return "Hello! How can I help you today?"
        
        if re.match(r'^\s*(what is|calculate|solve|compute)?\s*(\d+\s*[\+\-\*/×÷\^]\s*\d+)\s*$', query_lower):
            m = re.search(r'(\d+\s*[\+\-\*/×÷\^]\s*\d+)', query_lower)
            if m:
                try:
                    expr = m.group(1).replace('×', '*').replace('÷', '/').replace('^', '**')
                    return f"{eval(expr)}"
                except Exception:
                    pass

        # Detect question complexity
        is_simple = self._is_simple_question(query)
        is_complex = self._is_complex_question(query)

        # 1. Check knowledge base for verified stored facts
        relevant = self.kb.get_relevant_knowledge(query, limit=3)
        if relevant:
            ans = self._answer_from_knowledge(query, relevant, is_simple=is_simple)
            if ans and len(ans.strip()) > 5:
                return ans

        # 2. If online, perform live web search & learn into KB
        if self.is_online():
            try:
                online_ans = self._answer_online(query, is_simple=is_simple, is_complex=is_complex)
                if online_ans and len(online_ans.strip()) > 5:
                    return online_ans
            except Exception as exc:
                logger.warning(f"Online search error: {exc}")

        # 3. Local LLM (Qwen) answering (offline or search fallback)
        return self._answer_from_llm(query, is_simple=is_simple)

    def _is_simple_question(self, query: str) -> bool:
        """Check if this is a simple question needing short answer."""
        query_lower = query.lower().strip()

        # Greetings
        if re.match(r'^\s*(hi|hello|hey|how are you|good morning|good evening|hii)\s*$', query_lower):
            return True

        # Math calculations
        if re.match(r'^\s*(what is|calculate|solve|compute)?\s*\d+\s*[\+\-\*/×\*]\s*\d+\s*$', query_lower):
            return True

        # Simple fact questions
        simple_patterns = [
            r'^\s*(when was|who is|who was|where is|where was|which is)\s+',
            r'^\s*(define|what is a|what is the)\s+',
            r'^\s*(tell me a|give me a)\s+(joke|fact)\s*$',
            r'^\s*(is |are )\s+',
            r'^\s*(yes or no|true or false)\s*',
        ]

        for pattern in simple_patterns:
            if re.search(pattern, query_lower):
                return True

        # Very short questions (unless complex keyword detected)
        words = query.split()
        if len(words) <= 5 and not self._is_complex_question(query):
            return True

        return False

    def _is_complex_question(self, query: str) -> bool:
        """Check if this is a complex question needing detailed answer."""
        complex_patterns = [
            r'\b(explain|describe|elaborate|detail|detailed|in-depth)\b',
            r'\b(how does|how do|how did)\b',
            r'\b(compare|contrast|difference between)\b',
            r'\b(create a report|write a report|generate report)\b',
            r'\b(research|analyze|investigate)\b',
            r'\b(why|because)\b.*\bexplain\b',
            r'\b(list all|list everything|give a breakdown)\b',
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

        max_results = 3 if is_simple else 6
        research_result = self.search.search(query, max_results=max_results, depth='standard')
        results = research_result.documents

        # Store high quality results in knowledge base
        for result in results[:4]:
            content = getattr(result, 'excerpt', getattr(result, 'snippet', ''))
            if content and len(content.strip()) > 20:
                self.kb.store_knowledge(
                    query=query,
                    source=getattr(result, 'source', 'web'),
                    title=getattr(result, 'title', 'Unknown'),
                    content=content,
                    url=getattr(result, 'url', ''),
                    tags=self._extract_tags(query),
                )

        return self._generate_answer(query, research_result, is_simple=is_simple)

    def _answer_from_knowledge(self, query: str, knowledge: List[dict], is_simple: bool = False) -> str:
        """Generate answer from stored knowledge with appropriate length."""
        context_parts = []
        for i, entry in enumerate(knowledge, 1):
            title = entry.get('title', 'Untitled')
            content = entry.get('content', entry.get('excerpt', ''))
            url = entry.get('url', '')

            if content:
                context_parts.append(f"[Source {i}: {title}]({url})\n{content[:500]}")

        context = "\n\n---\n\n".join(context_parts)

        if is_simple:
            system_prompt = "You are PLUTO, an intelligent, helpful voice AI. Give a direct, factual, and concise answer in 1-2 sentences. Avoid preamble."
            user_prompt = f"Knowledge:\n{context}\n\nQuestion: {query}\n\nConcise Answer:"
        else:
            system_prompt = "You are PLUTO, an intelligent, helpful AI assistant. Provide a clear, well-structured, and accurate answer based on the knowledge provided."
            user_prompt = f"Knowledge:\n{context}\n\nQuestion: {query}\n\nAnswer:"

        try:
            answer = self.llm.reason(user_prompt, system_prompt=system_prompt)
            if answer and len(answer.strip()) > 5:
                return answer.strip()
        except Exception as e:
            logger.error(f"Knowledge answer failed: {e}")

        return self._format_knowledge_answer(query, knowledge, is_simple=is_simple)

    def _answer_from_llm(self, query: str, is_simple: bool = False) -> str:
        """Generate answer from LLM training data with appropriate length."""
        if is_simple:
            system_prompt = "You are PLUTO, a fast and smart local voice AI. Answer concisely in 1-2 sentences. Be direct and avoid boilerplate."
            user_prompt = f"Question: {query}\nAnswer:"
        else:
            system_prompt = "You are PLUTO, an intelligent AI assistant. Provide a comprehensive, accurate, and helpful response."
            user_prompt = f"Question: {query}\nAnswer:"

        try:
            answer = self.llm.reason(user_prompt, system_prompt=system_prompt)
            if answer and len(answer.strip()) > 5:
                return answer.strip()
        except Exception as e:
            logger.error(f"LLM answer failed: {e}")

        return "I am currently unable to generate a response for this query."

    def _generate_answer(self, query: str, research_result, is_simple: bool = False) -> str:
        """Generate answer from research results with adaptive length."""
        results = research_result.documents

        # Build context from search results
        context_parts = []
        for i, result in enumerate(results[:4], 1):
            title = getattr(result, 'title', 'Untitled')
            excerpt = getattr(result, 'excerpt', getattr(result, 'snippet', ''))
            url = getattr(result, 'url', '')

            if excerpt and len(excerpt.strip()) > 15:
                context_parts.append(f"[{title}]({url}): {excerpt[:400]}")

        context = "\n\n".join(context_parts)

        if not context:
            return self._answer_from_llm(query, is_simple=is_simple)

        if is_simple:
            system_prompt = "You are PLUTO, an AI assistant. Using the provided search results, provide a direct, factual answer in 1-2 sentences. Keep it brief and accurate."
            user_prompt = f"Search Results:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        else:
            system_prompt = "You are PLUTO, an AI assistant. Using the provided search results, provide a clear, accurate, and well-structured answer."
            user_prompt = f"Search Results:\n{context}\n\nQuestion: {query}\n\nAnswer:"

        try:
            answer = self.llm.reason(user_prompt, system_prompt=system_prompt)
            if answer and len(answer.strip()) > 5:
                return answer.strip()
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")

        return self._answer_from_llm(query, is_simple=is_simple)

    def _format_knowledge_answer(self, query: str, knowledge: List[dict], is_simple: bool = False) -> str:
        """Format stored knowledge into answer."""
        if not knowledge:
            return "No specific information found in knowledge base."
        first = knowledge[0]
        content = first.get('content', first.get('excerpt', ''))
        return content[:300] if content else f"Information found regarding {query}."

    def _extract_tags(self, query: str) -> List[str]:
        """Extract relevant tags from query."""
        tags = []
        query_lower = query.lower()

        tag_map = {
            'ai': ['artificial intelligence', 'machine learning', 'neural network', 'deep learning', 'llm'],
            'quantum': ['quantum', 'qubit', 'superposition', 'entanglement'],
            'climate': ['climate', 'environment', 'sustainability', 'global warming'],
            'space': ['space', 'mars', 'nasa', 'exploration', 'astronomy', 'planet'],
            'tech': ['technology', 'computer', 'software', 'coding', 'programming'],
            'science': ['science', 'physics', 'chemistry', 'biology', 'medicine'],
            'entertainment': ['movie', 'film', 'actor', 'actress', 'director', 'cinema', 'bollywood', 'hollywood'],
        }

        for tag, keywords in tag_map.items():
            if any(kw in query_lower for kw in keywords):
                tags.append(tag)

        return tags

    def train_on_topic(self, topic: str) -> dict:
        """Train AI on a specific topic by searching and storing knowledge."""
        try:
            if not self.is_online():
                return {"status": "offline", "message": "Currently in offline mode", "topic": topic}
            research_result = self.search.search(topic, max_results=5, depth='deep')
            docs = getattr(research_result, 'documents', [])
            count = 0
            for doc in docs:
                content = getattr(doc, 'excerpt', getattr(doc, 'snippet', ''))
                if content:
                    self.kb.store_knowledge(
                        query=topic,
                        source=getattr(doc, 'source', 'web'),
                        title=getattr(doc, 'title', topic),
                        content=content,
                        url=getattr(doc, 'url', ''),
                        tags=self._extract_tags(topic),
                    )
                    count += 1
            return {"status": "success", "topic": topic, "stored_entries": count}
        except Exception as e:
            logger.error(f"train_on_topic error: {e}")
            return {"status": "error", "error": str(e), "topic": topic}

    def should_learn(self, topic: str) -> bool:
        """Determine if learning is needed for this topic."""
        return True

    def learn_and_answer(self, topic: str) -> str:
        """Learn and answer query."""
        return self.answer(topic)

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
