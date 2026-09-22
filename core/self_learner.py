"""
Self-Learning Module for PLUTO v2.

Searches the internet when available, falls back to knowledge base + LLM
when offline. Response length adapts to question complexity.
"""

import logging
import re
import socket
from typing import List, Literal

from core.research.engine import get_research_engine
from core.brain import LLMReasoner, LLMUnavailableError
from core.knowledge_base import get_knowledge_base
from core import config

logger = logging.getLogger(__name__)

# Silence threshold for RMS-based detection (0.0 to 1.0 normalized)
SILENCE_THRESHOLD = 0.08
SILENCE_CONSECUTIVE_SECONDS = 1.5
MAX_RECORDING_SECONDS = 15

# Context window (tokens) for the research path. The KB/web synthesis prompts
# pack multiple source excerpts (~500 chars each) plus the question, so this is
# set well above the simple-path window (1024) to avoid truncating that context
# — which would produce exactly the vague/shallow answers we're trying to fix.
RESEARCH_NUM_CTX = 4096

# Max output tokens for research-synthesis answers. num_ctx (above) controls how
# much source material the model can *read*; this caps how much it *writes*.
# ~300 tokens keeps answers tight (roughly 250-350 tokens / a few short
# paragraphs) so a long generation doesn't dominate latency, without shrinking
# the context window it reasons over.
RESEARCH_NUM_PREDICT = 300


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
        """Check if internet is available. Returns False on any timeout/error."""
        if config.OFFLINE_MODE:
            return False
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except (OSError, socket.timeout):
            try:
                socket.create_connection(("1.1.1.1", 53), timeout=2)
                return True
            except (OSError, socket.timeout):
                return False

    def answer(self, query: str) -> tuple[str, str]:
        """Provide answer using KB/LLM first, then internet if needed and available.

        Returns:
            Tuple of (answer_text, answer_source) where answer_source is one of:
            "local_model", "web_research", "knowledge_base_cache"
        """
        logger.info(f"SelfLearner: Answering '{query}'")
        query_stripped = query.strip()
        if not query_stripped:
            return "How can I assist you today?", "local_model"

        # Classify the query to determine routing
        query_type = self.classify_query(query_stripped)
        logger.info(f"Query classified as: {query_type}")

        # Smalltalk/simple queries bypass research and KB - send directly to LLM
        if query_type in ("smalltalk", "simple"):
            system_prompt = ("You are PLUTO, a fast and smart local voice AI. "
                           "Reply briefly in 1-3 sentences. No headers, sections, or bullet templates.")
            # Small context window for the brief (1-3 sentence) direct path.
            # 1024 comfortably holds the short prompt + a few-sentence answer
            # while keeping this path far cheaper than the research path.
            # LLMUnavailableError propagates: an outage here is a real failure,
            # not something to paper over with a fabricated reply.
            answer = self.llm.reason(query_stripped, system_prompt=system_prompt, num_ctx=1024)
            if answer and len(answer.strip()) > 2:
                return answer.strip(), "local_model"
            raise LLMUnavailableError("LLM returned an empty direct answer.")

        # For research queries: check KB, then online search
        if query_type == "research":
            # Test true external connectivity ONCE (not per source). This is a
            # short-timeout probe of external DNS hosts — see is_online() — and
            # is independent of whether the local Ollama LLM is reachable.
            online = self.is_online()

            # Check knowledge base for verified stored facts
            relevant = self.kb.get_relevant_knowledge(query_stripped, limit=3)
            if relevant:
                ans = self._answer_from_knowledge(query_stripped, relevant)
                if ans and len(ans.strip()) > 5:
                    return self._maybe_offline_note(ans, online), "knowledge_base_cache"

            # Only attempt a live web search when we actually have internet.
            # When offline we skip this entirely so we never block on a doomed
            # request waiting for a timeout. A network/scraping failure while
            # online is recoverable — fall through to the local LLM. An LLM
            # outage is not, so let LLMUnavailableError propagate.
            if online:
                try:
                    online_ans = self._answer_online(query_stripped)
                    if online_ans and len(online_ans.strip()) > 5:
                        return online_ans, "web_research"
                except LLMUnavailableError:
                    raise
                except Exception as exc:
                    logger.warning(f"Online search error: {exc}")

            # Fallback to the local LLM (KB was thin/empty, or the web step
            # failed/was skipped). LLMUnavailableError propagates to the API
            # error boundary instead of being masked by a canned apology.
            llm_ans = self._answer_from_llm(query_stripped)
            return self._maybe_offline_note(llm_ans, online), "local_model"

        # Default fallback (shouldn't reach here)
        return self._answer_from_llm(query_stripped), "local_model"

    @staticmethod
    def _maybe_offline_note(answer: str, online: bool) -> str:
        """Append an offline disclaimer to a research answer when there is no
        internet, so the user knows it came from local knowledge only."""
        if online:
            return answer
        note = "(answered from local knowledge only — no internet connection detected)"
        return f"{answer.rstrip()}\n\n_{note}_"

    def classify_query(self, text: str) -> Literal["smalltalk", "simple", "research"]:
        """Classify a query to determine routing strategy.

        Returns:
            "smalltalk": greetings, filler phrases
            "simple": arithmetic, short factual questions answerable without search
            "research": named entities, current events, explicit research requests
        """
        t = text.lower().strip()

        # Smalltalk patterns
        smalltalk_patterns = [
            r'^(hi|hello|hey|hii?|howdy|good\s+(morning|afternoon|evening))\b',
            r'^(thanks|thank\s+you|ty)\b',
            r'^(how\s+are\s+you|what\'?s\s+up|what\'s\s上)\b',
            r'^(bye|goodbye|see\s+you)\b',
        ]
        for pattern in smalltalk_patterns:
            if re.search(pattern, t):
                return "smalltalk"

        # Simple patterns: math, short definitions
        # Handle various math formats including "100 x 5000", "15% of 340", "15 percent of 340"
        math_patterns = [
            r'^\s*(what\s+is|calculate|solve|compute)?\s*\d+\s*[\+\-\*\/×÷\^]\s*\d+\s*$',
            r'\d+\s*[xX]\s*\d+',  # "100 x 5000" or "100 X 5000"
            r'\d+\s*[\*×]\s*\d+',  # "100 * 5000" or "100 × 5000"
            r'\d+\s*%\s+of\s+\d+',  # "15% of 340"
            r'\d+\s+percent\s+of\s+\d+',  # "15 percent of 340"
            r'what\s+is\s+\d+\s*%\s+of\s+\d+',  # "what is 15% of 340"
            r'what\s+is\s+\d+\s+percent\s+of\s+\d+',  # "what is 15 percent of 340"
        ]
        for pattern in math_patterns:
            if re.search(pattern, t):
                return "simple"

        # Explicit research triggers — queries that genuinely need current info or
        # multi-source depth. Checked BEFORE the broad simple heuristics so that
        # time-sensitive / named-entity queries (e.g. "who is the current CEO of
        # Nvidia") are not swallowed by the generous "what/who is ..." patterns.
        research_keywords = [
            r'\b(research|look\s+up|find\s+out|sources?\s+on)\b',
            r'\b(who\s+is|who\s+was|who\s+made|who\s+created)\b',   # named entities / people
            r'\b(latest|recent|current|currently|news|today|2024|2025|2026)\b',  # time-sensitive
            r'\b(explain|describe|elaborate|analyze|compare)\b',    # in-depth explanatory
            r'\btell\s+me\s+about\b',                               # open-ended deep dive
        ]
        for pattern in research_keywords:
            if re.search(pattern, t):
                return "research"

        # Broad "simple factual" heuristics — general knowledge answerable by the
        # local model without a web search. These are intentionally generous and
        # run only after the research triggers above have had first refusal.
        simple_factual = [
            r'^\s*(what|which)\s+is\s+the\s+',       # "what is the square root of 144"
            r'^\s*(what|which)\s+(is|are)\s+[a-z]',  # "what is inflation", "what are primes"
            r'^\s*define\b',                          # "define inflation"
            r'^\s*(when|where)\s+(was|is|did|do)\b',  # "when was the printing press invented"
            r'^\s*how\s+(many|much|do|does|did|to)\b',  # "how many continents are there"
            r'\bsquare\s+root\b',
            r'\bconvert\b.*\b(to|into)\b',            # unit conversions
        ]
        for pattern in simple_factual:
            if re.search(pattern, t):
                return "simple"

        # ------------------------------------------------------------------
        # Uncertain / ambiguous case.
        #
        # Previously this defaulted to "research", which triggered a KB lookup
        # plus (when online) a full multi-source web search AND a synthesis LLM
        # call for *every* unclassified query — a heavy, slow path taken for
        # anything the fast heuristics didn't recognize.
        #
        # The cost asymmetry favors "simple": a wrong "simple" guess costs only a
        # slightly-too-brief local answer, whereas a wrong "research" guess costs
        # a full multi-source web search. So we now default to "simple" and let
        # the local model answer directly and cheaply.
        # ------------------------------------------------------------------
        return "simple"

    def _answer_online(self, query: str) -> str:
        """Answer using internet search."""
        logger.info(f"Online mode - searching for '{query}'")

        research_result = self.search.search(query, max_results=6, depth='standard')
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

        return self._generate_answer(query, research_result)

    def _answer_from_knowledge(self, query: str, knowledge: List[dict]) -> str:
        """Generate answer from stored knowledge."""
        context_parts = []
        for i, entry in enumerate(knowledge, 1):
            title = entry.get('title', 'Untitled')
            content = entry.get('content', entry.get('excerpt', ''))
            url = entry.get('url', '')

            if content:
                context_parts.append(f"[Source {i}: {title}]({url})\n{content[:500]}")

        context = "\n\n---\n\n".join(context_parts)

        system_prompt = (
            "You are PLUTO, an intelligent, helpful AI assistant. Answer using the "
            "knowledge provided. Keep it under ~250 words. Lead with the concrete "
            "specifics — name the actual algorithms/methods/entities, give one "
            "worked example with a real number, and cite real dates or figures. "
            "Do NOT open with a long generic definition or filler; put the "
            "specifics first because the answer length is capped."
        )
        user_prompt = f"Knowledge:\n{context}\n\nQuestion: {query}\n\nAnswer:"

        # Research synthesis needs a large context window to hold the
        # multi-source knowledge without truncation (see RESEARCH_NUM_CTX), and
        # a capped output length (see RESEARCH_NUM_PREDICT).
        # If the LLM is down, LLMUnavailableError propagates: we must NOT dress
        # up an unrelated raw KB row as a synthesized answer.
        answer = self.llm.reason(
            user_prompt,
            system_prompt=system_prompt,
            num_ctx=RESEARCH_NUM_CTX,
            num_predict=RESEARCH_NUM_PREDICT,
        )
        if answer and len(answer.strip()) > 5:
            return answer.strip()
        # Empty/too-short generation despite a healthy LLM: surface honestly.
        raise LLMUnavailableError("LLM returned an empty knowledge-synthesis answer.")

    def _answer_from_llm(self, query: str) -> str:
        """Generate answer from LLM training data."""
        system_prompt = (
            "You are PLUTO, an intelligent AI assistant. Answer in under ~250 "
            "words. Lead with the concrete specifics — name the actual "
            "algorithms/methods/entities, give one worked example with a real "
            "number, and cite real dates or figures where relevant. Do NOT open "
            "with a long generic definition or filler; put the specifics first "
            "because the answer length is capped."
        )
        user_prompt = f"Question: {query}\nAnswer:"

        # LLMUnavailableError propagates so the API can report an honest error
        # rather than returning a canned "unable to generate" string that looks
        # like a normal answer.
        answer = self.llm.reason(
            user_prompt,
            system_prompt=system_prompt,
            num_ctx=RESEARCH_NUM_CTX,
            num_predict=RESEARCH_NUM_PREDICT,
        )
        if answer and len(answer.strip()) > 5:
            return answer.strip()
        raise LLMUnavailableError("LLM returned an empty answer.")

    def _generate_answer(self, query: str, research_result) -> str:
        """Generate answer from research results."""
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
            return self._answer_from_llm(query)

        system_prompt = (
            "You are PLUTO, an AI assistant. Using the provided search results, "
            "answer in under ~250 words. Lead with the concrete specifics — quote "
            "actual figures, named entities, dates, and real examples found in the "
            "sources. Do NOT open with a long generic definition or filler; put "
            "the specifics first because the answer length is capped."
        )
        user_prompt = f"Search Results:\n{context}\n\nQuestion: {query}\n\nAnswer:"

        # LLMUnavailableError propagates (no point falling back to _answer_from_llm,
        # which uses the same downed LLM); only an empty-but-healthy generation
        # falls through to a plain-LLM attempt.
        answer = self.llm.reason(
            user_prompt,
            system_prompt=system_prompt,
            num_ctx=RESEARCH_NUM_CTX,
            num_predict=RESEARCH_NUM_PREDICT,
        )
        if answer and len(answer.strip()) > 5:
            return answer.strip()

        return self._answer_from_llm(query)

    def _format_knowledge_answer(self, query: str, knowledge: List[dict]) -> str:
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


# Silence detection for STT
def detect_silence(audio_data: list, threshold: float = SILENCE_THRESHOLD) -> int:
    """Count consecutive seconds of near-silence in audio data.

    Args:
        audio_data: List of audio sample values (normalized -1.0 to 1.0).
        threshold: RMS threshold below which audio is considered silence.

    Returns:
        Number of consecutive silence seconds detected.
    """
    import math
    sample_rate = 16000  # Assume 16kHz
    samples_per_chunk = sample_rate  # 1 second chunks

    silence_count = 0
    for i in range(0, len(audio_data), samples_per_chunk):
        chunk = audio_data[i:i + samples_per_chunk]
        if not chunk:
            break

        # Calculate RMS
        rms = math.sqrt(sum(x * x for x in chunk) / len(chunk))
        if rms < threshold:
            silence_count += 1
        else:
            break

    return silence_count


# Singleton instance
_learner_instance = None

def get_self_learner() -> SelfLearner:
    """Get or create the singleton SelfLearner instance."""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = SelfLearner()
    return _learner_instance
