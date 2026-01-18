"""
Backchannel and interruption detection logic.

This module provides a pure, stateless detector that analyzes
transcribed user speech and determines whether it should be
ignored (backchannel), treated as an interruption, or processed
normally based on the agent's speaking state.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Set

from .config import InterruptionConfig

logger = logging.getLogger("interrupt_handler.detector")


class InterruptDecision(Enum):
    """Decision for handling a user transcript."""
    IGNORE = auto()
    INTERRUPT = auto()
    PROCESS = auto()


@dataclass(frozen=True)
class AnalysisResult:
    """
    Result of analyzing a transcript.

    This object is immutable and contains only facts derived
    from the analysis (no side effects).
    """
    decision: InterruptDecision
    transcript: str
    normalized: str
    is_backchannel: bool
    has_interrupt_word: bool
    agent_was_speaking: bool
    analysis_time_ms: float


class BackchannelDetector:
    """
    Stateless detector for backchannels vs interruptions.

    The detector itself does NOT track agent state, metrics,
    or outcomes. It simply analyzes input and returns a decision.
    """

    def __init__(self, config: Optional[InterruptionConfig] = None):
        self._config = config or InterruptionConfig()

        self._ignore_pattern = self._build_pattern(self._config.ignore_words)
        self._interrupt_pattern = self._build_pattern(self._config.interrupt_words)

        logger.info(
            "BackchannelDetector initialized "
            "(ignore_words=%d, interrupt_words=%d)",
            len(self._config.ignore_words),
            len(self._config.interrupt_words),
        )

    @staticmethod
    def _build_pattern(words: Set[str]) -> re.Pattern:
        """
        Build a regex pattern for matching words or phrases.

        Words and phrases are sorted by length (longest first)
        to avoid partial matches overriding longer phrases.
        """
        if not words:
            return re.compile(r"(?!)")

        sorted_words = sorted(words, key=len, reverse=True)
        escaped = [re.escape(word) for word in sorted_words]

        # NOTE:
        # Word boundaries work well for single words.
        # Multi-word phrases rely on substring matching.
        pattern = r'(' + '|'.join(escaped) + r')'
        return re.compile(pattern, re.IGNORECASE)

    @staticmethod
    def _normalize(transcript: str) -> str:
        """
        Normalize transcript text for analysis.

        - Lowercases
        - Removes punctuation
        - Collapses whitespace
        """
        text = transcript.lower().strip()
        text = re.sub(r"[.,!?;:]+", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _contains_interrupt_word(self, normalized: str) -> bool:
        """Check whether transcript contains an interrupt word or phrase."""
        return bool(self._interrupt_pattern.search(normalized))

    def _is_backchannel_only(self, normalized: str) -> bool:
        """
        Determine if transcript consists only of backchannel words.

        If removing all ignore words leaves no meaningful content,
        the transcript is considered a backchannel.
        """
        if not normalized:
            return False

        remaining = self._ignore_pattern.sub("", normalized)
        remaining = re.sub(r"[^\w\s]", "", remaining).strip()

        return len(remaining) == 0

    def analyze(
        self,
        transcript: str,
        *,
        agent_speaking: bool,
    ) -> AnalysisResult:
        """
        Analyze a transcript and return an interruption decision.

        Decision matrix:
        - Agent silent        → PROCESS
        - Agent speaking +
            - interrupt word  → INTERRUPT
            - backchannel only→ IGNORE
            - otherwise       → INTERRUPT
        """
        start = time.perf_counter()

        normalized = self._normalize(transcript)
        has_interrupt = self._contains_interrupt_word(normalized)
        is_backchannel = self._is_backchannel_only(normalized)

        if not agent_speaking:
            decision = InterruptDecision.PROCESS
        elif has_interrupt:
            decision = InterruptDecision.INTERRUPT
        elif is_backchannel:
            decision = InterruptDecision.IGNORE
        else:
            decision = InterruptDecision.INTERRUPT

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        result = AnalysisResult(
            decision=decision,
            transcript=transcript,
            normalized=normalized,
            is_backchannel=is_backchannel,
            has_interrupt_word=has_interrupt,
            agent_was_speaking=agent_speaking,
            analysis_time_ms=elapsed_ms,
        )

        if self._config.debug_mode:
            logger.debug(
                "AnalysisResult(decision=%s, transcript=%r, backchannel=%s, interrupt=%s)",
                result.decision.name,
                transcript,
                is_backchannel,
                has_interrupt,
            )

        return result

    def should_ignore(self, transcript: str, *, agent_speaking: bool) -> bool:
        """
        Convenience method for integration - returns True if transcript should be ignored.
        
        This is the primary method used by the agent integration to determine
        whether to ignore a backchannel.
        
        Args:
            transcript: The user's transcribed speech
            agent_speaking: Whether the agent is currently speaking
            
        Returns:
            True if the transcript should be ignored (is a backchannel while speaking)
        """
        result = self.analyze(transcript, agent_speaking=agent_speaking)
        return result.decision == InterruptDecision.IGNORE


# =============================================================================
# Global Singleton Pattern
# =============================================================================

_global_detector: BackchannelDetector | None = None


def get_global_detector() -> BackchannelDetector:
    """
    Get the global detector instance, creating with defaults if needed.
    
    This provides a shared detector instance for use across the agent.
    
    Returns:
        The global BackchannelDetector instance
    """
    global _global_detector
    if _global_detector is None:
        _global_detector = BackchannelDetector()
    return _global_detector


def configure_global_detector(config: InterruptionConfig) -> BackchannelDetector:
    """
    Configure and return the global detector with custom settings.
    
    Call this before starting the agent to customize backchannel detection.
    
    Args:
        config: Custom configuration for the detector
        
    Returns:
        The configured global BackchannelDetector instance
    """
    global _global_detector
    _global_detector = BackchannelDetector(config)
    return _global_detector
