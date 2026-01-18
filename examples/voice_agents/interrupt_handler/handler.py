"""
Interruption Handler - Applies backchannel detection to agent behavior.

This module provides a stateful handler that wraps the BackchannelDetector
and manages agent speaking state for easy integration.
"""

from __future__ import annotations

import logging
from typing import Optional

from .config import InterruptionConfig
from .detector import (
    BackchannelDetector,
    InterruptDecision,
    AnalysisResult,
)

logger = logging.getLogger("interrupt_handler.handler")


class InterruptionHandler:
    """
    Applies backchannel detection decisions to agent behavior.
    
    This handler tracks the agent's speaking state and provides
    a simple interface for handling transcripts.
    
    Example:
        handler = InterruptionHandler()
        
        # Update state when agent starts/stops speaking
        handler.set_agent_speaking(True)
        
        # Handle incoming transcripts
        decision = handler.handle_transcript("yeah")
        if decision == InterruptDecision.IGNORE:
            return  # Don't interrupt
    """

    def __init__(self, config: Optional[InterruptionConfig] = None):
        self._config = config or InterruptionConfig()
        self._detector = BackchannelDetector(self._config)
        self._speaking = False

        # Stats tracking
        self.ignored = 0
        self.interrupted = 0
        self.processed = 0

    def set_agent_speaking(self, speaking: bool) -> None:
        """Update the agent's speaking state."""
        self._speaking = speaking

    def handle_transcript(self, transcript: str) -> InterruptDecision:
        """
        Handle an incoming transcript and return the decision.
        
        Args:
            transcript: The user's transcribed speech
            
        Returns:
            InterruptDecision indicating how to handle the transcript
        """
        analysis: AnalysisResult = self._detector.analyze(
            transcript=transcript,
            agent_speaking=self._speaking,
        )

        if analysis.decision == InterruptDecision.IGNORE:
            self.ignored += 1
            logger.debug(f"Ignored backchannel: '{transcript}'")
            return InterruptDecision.IGNORE

        if analysis.decision == InterruptDecision.INTERRUPT:
            self.interrupted += 1
            logger.info(f"Interrupt requested: '{transcript}'")
            return InterruptDecision.INTERRUPT

        self.processed += 1
        return InterruptDecision.PROCESS

    @property
    def stats(self) -> dict:
        """Get statistics about handled transcripts."""
        return {
            "ignored": self.ignored,
            "interrupted": self.interrupted,
            "processed": self.processed,
        }
