"""
Configuration for Intelligent Interruption Handling.

This module provides configurable settings for backchannel detection
and interruption filtering. All settings can be overridden via
environment variables for easy deployment configuration.

Environment Variables:
    BACKCHANNEL_IGNORE_WORDS: Comma-separated list of words to ignore
    BACKCHANNEL_INTERRUPT_WORDS: Comma-separated list of interrupt words
    BACKCHANNEL_DEBUG: Enable debug logging (true/false)

Author: LiveKit Intelligent Interruption Challenge
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import FrozenSet, Set


@dataclass
class InterruptionConfig:
    """
    Configuration for the backchannel-aware interruption handler.
    
    This configuration defines which words should be treated as
    passive acknowledgements (backchannels) versus active interruptions.
    
    Attributes:
        ignore_words: Words to ignore when agent is speaking
        interrupt_words: Words that always trigger interruption
        debug_mode: Enable verbose logging for debugging
    
    Example:
        config = InterruptionConfig()
        config.add_ignore_word("gotcha")  # Add custom backchannel
        config.add_interrupt_word("cancel")  # Add custom interrupt
    """
    
    # Backchannel words - passive acknowledgements to IGNORE when agent speaks
    ignore_words: Set[str] = field(default_factory=lambda: {
        # Affirmative backchannels
        "yeah", "yep", "yes", "yea", "ya", "yup",
        "ok", "okay", "k", "okey", "okee",
        "sure", "alright", "right", "all right",
        "got it", "i see", "i understand", "understood",
        "go on", "continue", "go ahead", "keep going",
        "cool", "nice", "great", "good", "fine",
        
        # Acknowledgement sounds
        "hmm", "hm", "mm", "mhm", "mmhmm", "mhmm", "mmhm",
        "uh-huh", "uh huh", "uhuh", "aha", "a-ha",
        
        # Filler/thinking sounds
        "uh", "um", "er", "eh", "ah", "oh", "ooh",
        
        # Short confirmations
        "true", "correct", "exactly", "indeed",
    })
    
    # Interrupt words - ALWAYS trigger interruption, even in mixed phrases
    interrupt_words: Set[str] = field(default_factory=lambda: {
        # Stop commands
        "stop", "wait", "hold on", "hold", "pause",
        "quiet", "silence", "enough", "shut up",
        
        # Negation/correction (indicates disagreement)
        "no", "nope", "nah", "wrong", "incorrect",
        "actually", "but", "however", "although",
        
        # Attention/interjection
        "hang on", "one second", "one moment", "just a moment",
        "excuse me", "hey", "listen", "sorry",
        
        # Questions (user wants to interject)
        "what", "why", "how", "when", "where", "who",
        "can you", "could you", "would you", "will you",
        "what about", "how about",
    })
    
    # Enable debug logging
    debug_mode: bool = False
    
    @classmethod
    def from_env(cls) -> "InterruptionConfig":
        """
        Create configuration from environment variables.
        
        This allows runtime configuration without code changes,
        useful for testing different word lists in production.
        """
        config = cls()
        
        # Override ignore words
        if env_ignore := os.getenv("BACKCHANNEL_IGNORE_WORDS"):
            config.ignore_words = {
                word.strip().lower() 
                for word in env_ignore.split(",") 
                if word.strip()
            }
        
        # Override interrupt words
        if env_interrupt := os.getenv("BACKCHANNEL_INTERRUPT_WORDS"):
            config.interrupt_words = {
                word.strip().lower()
                for word in env_interrupt.split(",")
                if word.strip()
            }
        
        # Debug mode
        config.debug_mode = os.getenv(
            "BACKCHANNEL_DEBUG", ""
        ).lower() in ("true", "1", "yes")
        
        return config
    
    def add_ignore_word(self, word: str) -> None:
        """Add a word to the ignore (backchannel) list."""
        self.ignore_words.add(word.lower().strip())
    
    def add_interrupt_word(self, word: str) -> None:
        """Add a word to the interrupt list."""
        self.interrupt_words.add(word.lower().strip())
    
    def remove_ignore_word(self, word: str) -> None:
        """Remove a word from the ignore list."""
        self.ignore_words.discard(word.lower().strip())
    
    def remove_interrupt_word(self, word: str) -> None:
        """Remove a word from the interrupt list."""
        self.interrupt_words.discard(word.lower().strip())
    
    def get_frozen(self) -> tuple[FrozenSet[str], FrozenSet[str]]:
        """Get immutable copies of word sets for thread safety."""
        return frozenset(self.ignore_words), frozenset(self.interrupt_words)
