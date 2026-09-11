"""
Fact verification across multiple sources.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class FactClaim:
    """A claim that needs verification."""
    claim: str
    source: str
    confidence: float
    evidence: str = ""


@dataclass
class VerificationResult:
    """Result of fact verification."""
    claim: str
    verified: bool
    confidence: float
    supporting_sources: int
    conflicting_sources: int
    consensus: str
    details: str


class FactVerifier:
    """Verify facts across multiple sources."""

    def __init__(self):
        self.claims_cache = {}

    def verify(self, claim: str, documents: List[Dict]) -> VerificationResult:
        """Verify a claim against multiple documents."""
        # Check cache
        if claim in self.claims_cache:
            return self.claims_cache[claim]

        supporting = 0
        conflicting = 0
        supporting_docs = []
        conflicting_docs = []

        # Analyze each document
        for doc in documents:
            content = doc.get('content', '') or doc.get('excerpt', '') or ''
            title = doc.get('title', '')

            if self._is_consistent(claim, content):
                supporting += 1
                supporting_docs.append(doc)
            elif self._is_contradictory(claim, content):
                conflicting += 1
                conflicting_docs.append(doc)

        # Determine verdict
        total = supporting + conflicting
        if total == 0:
            confidence = 0.5
            verified = False
            consensus = "No information found"
        elif supporting > conflicting:
            confidence = supporting / total
            verified = True
            consensus = "Supported by majority of sources"
        elif conflicting > supporting:
            confidence = conflicting / total
            verified = False
            consensus = "Contradicted by majority of sources"
        else:
            confidence = 0.5
            verified = False
            consensus = "Conflicting information - inconclusive"

        # Build details
        details = f"Found {supporting} supporting and {conflicting} conflicting sources."
        if supporting_docs:
            details += f"\nSupporting sources: {[d.get('title', 'Unknown') for d in supporting_docs[:3]]}"
        if conflicting_docs:
            details += f"\nConflicting sources: {[d.get('title', 'Unknown') for d in conflicting_docs[:3]]}"

        result = VerificationResult(
            claim=claim,
            verified=verified,
            confidence=confidence,
            supporting_sources=supporting,
            conflicting_sources=conflicting,
            consensus=consensus,
            details=details
        )

        self.claims_cache[claim] = result
        return result

    def _is_consistent(self, claim: str, content: str) -> bool:
        """Check if content is consistent with claim."""
        claim_words = set(claim.lower().split())
        content_lower = content.lower()

        # Count matching key terms
        matches = sum(1 for word in claim_words if word in content_lower and len(word) > 3)
        return matches >= 2  # At least 2 key terms match

    def _is_contradictory(self, claim: str, content: str) -> bool:
        """Check if content contradicts claim."""
        # Simple heuristic: look for negation patterns
        negations = ['not', 'never', 'false', 'incorrect', 'wrong', 'opposite']
        claim_keywords = set(claim.lower().split())

        for neg in negations:
            if neg in content.lower():
                # Check if negation is near claim keywords
                words = content.lower().split()
                for i, word in enumerate(words):
                    if word == neg:
                        # Check surrounding words
                        context = ' '.join(words[max(0, i-3):i+4])
                        if any(kw in context for kw in claim_keywords):
                            return True
        return False

    def get_consensus(self, documents: List[Dict], topic: str) -> str:
        """Get consensus view from multiple documents."""
        # Extract key claims from each document
        claims = []
        for doc in documents:
            content = doc.get('content', '') or doc.get('excerpt', '')
            if content:
                # Simple sentence splitting
                sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 20]
                claims.extend(sentences[:3])

        # Find common themes
        word_counts = Counter()
        for claim in claims:
            words = set(claim.lower().split())
            for word in words:
                if len(word) > 4:
                    word_counts[word] += 1

        # Get top common words
        common = [word for word, count in word_counts.most_common(10) if count >= 2]

        return f"Common themes in sources: {', '.join(common[:5])}"

    def clear_cache(self):
        """Clear the claims cache."""
        self.claims_cache.clear()
