"""
LiveKit Intelligent Interruption Handler

A context-aware backchannel filtering system that distinguishes between
passive acknowledgements ("yeah", "ok", "hmm") and active interruptions
("stop", "wait", "no").

Usage:
    from interrupt_handler import get_global_detector, InterruptionConfig
    
    # Use default configuration
    detector = get_global_detector()
    
    # Or configure with custom settings
    config = InterruptionConfig()
    config.add_ignore_word("gotcha")
    configure_global_detector(config)
"""

from .config import InterruptionConfig
from .detector import (
    BackchannelDetector,
    InterruptDecision,
    AnalysisResult,
    get_global_detector,
    configure_global_detector,
)
from .handler import InterruptionHandler

__all__ = [
    # Configuration
    "InterruptionConfig",
    # Core detector
    "BackchannelDetector",
    "InterruptDecision",
    "AnalysisResult",
    # Global singleton
    "get_global_detector",
    "configure_global_detector",
    # Handler
    "InterruptionHandler",
]
