"""
Backchannel-Filtered Voice Agent - Intelligent Interruption Handling Demo

This example demonstrates the complete solution for the LiveKit Intelligent
Interruption Handling challenge.

THE PROBLEM:
When the AI agent is speaking, users often say "yeah", "ok", "hmm" to show
they're listening (backchanneling). The default VAD treats these as
interruptions, causing the agent to stop mid-sentence.

THE SOLUTION:
This agent uses intelligent backchannel detection to:
- IGNORE "yeah/ok/hmm" when the agent is speaking
- INTERRUPT for "stop/wait/no" even mid-sentence
- PROCESS "yeah/ok" normally when the agent is silent

HANDLING FALSE-START VAD:
The solution uses a two-layer defense:
1. Layer 1 (VAD thresholds): min_interruption_duration=1.0 and 
   min_interruption_words=2 prevent audio pause for quick backchannels
2. Layer 2 (STT filter): Backchannel filter at on_end_of_turn ignores 
   backchannels even if they get through

TEST SCENARIOS:
1. The Long Explanation: Say "yeah", "ok" while agent talks -> Agent continues
2. The Passive Affirmation: Say "yeah" when agent is silent -> Agent responds
3. The Correction: Say "no stop" while agent talks -> Agent stops immediately
4. The Mixed Input: Say "yeah okay but wait" -> Agent stops (contains "but wait")

RUN:
    python backchannel_agent.py console   # Local testing with microphone
    python backchannel_agent.py dev       # Connect to LiveKit room

Author: LiveKit Intelligent Interruption Challenge
"""

from __future__ import annotations

import logging
import os
import sys

# Add interrupt_handler to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.voice.events import (
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
)
from livekit.plugins import deepgram, groq, silero, cartesia

# Import our backchannel handling module
from interrupt_handler import (
    InterruptionConfig,
    configure_global_detector,
    get_global_detector,
    InterruptDecision,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("backchannel_agent")

# Reduce noise from other loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def setup_backchannel_filter():
    """
    Configure the backchannel filter with custom settings.
    
    You can customize which words are ignored or trigger interruption.
    """
    config = InterruptionConfig()
    
    # Enable debug mode to see all decisions in logs
    config.debug_mode = True
    
    # Add any custom words if needed
    # config.add_ignore_word("gotcha")
    # config.add_interrupt_word("cancel")
    
    # Configure the global detector
    detector = configure_global_detector(config)
    
    logger.info(
        "Backchannel filter configured: "
        f"ignore_words={len(config.ignore_words)}, "
        f"interrupt_words={len(config.interrupt_words)}, "
        f"debug={config.debug_mode}"
    )
    
    return detector


async def entrypoint(ctx: JobContext):
    """Main entrypoint for the backchannel-filtered agent."""
    
    # Setup the backchannel filter BEFORE connecting
    detector = setup_backchannel_filter()
    
    await ctx.connect()
    
    # Create the agent session with VAD and interruption settings tuned
    # to prevent false-start interruptions from backchannels
    session = AgentSession(
        # Speech-to-Text: Deepgram Nova 3
        stt=deepgram.STT(model="nova-3"),
        
        # LLM: Groq (fast inference)
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        
        # Text-to-Speech: Cartesia
        tts=cartesia.TTS(),
        
        # Voice Activity Detection: Silero (high threshold to filter noise)
        vad=silero.VAD.load(
            min_speech_duration=0.25,     # Ignore short noise bursts (<250ms)
            min_silence_duration=0.6,     # Wait 600ms of silence before end of speech
            activation_threshold=0.75,    # HIGH threshold - only clear voice triggers
        ),
        
        # CRITICAL: Interruption settings to prevent pause on backchannels
        # Higher thresholds = short "yeah/ok" won't trigger audio pause
        min_interruption_duration=1.0,   # 1 second minimum - quick "yeah" won't pause
        min_interruption_words=2,         # Need 2+ words to interrupt
        
        # Turn detection settings
        min_endpointing_delay=0.3,       # Faster response after silence
        
        # Disable false interruption recovery (we handle it via backchannel filter)
        resume_false_interruption=False,
    )
    
    # Track statistics for demo purposes
    stats = {"ignored": 0, "interrupted": 0, "processed": 0}
    
    # Event handlers for logging
    @session.on("agent_state_changed")
    def on_agent_state(event: AgentStateChangedEvent):
        logger.info(f"Agent state: {event.old_state} -> {event.new_state}")
    
    @session.on("user_input_transcribed")
    def on_transcript(event: UserInputTranscribedEvent):
        if event.is_final:
            # Analyze for logging (actual filtering is in agent_activity.py)
            is_speaking = (session.agent_state == "speaking")
            result = detector.analyze(event.transcript, agent_speaking=is_speaking)
            
            if result.decision == InterruptDecision.IGNORE:
                stats["ignored"] += 1
                logger.info(
                    f"TRANSCRIPT [IGNORED]: '{event.transcript}' "
                    f"(backchannel={result.is_backchannel})"
                )
            elif result.decision == InterruptDecision.INTERRUPT:
                stats["interrupted"] += 1
                logger.info(
                    f"TRANSCRIPT [INTERRUPT]: '{event.transcript}' "
                    f"(has_interrupt={result.has_interrupt_word})"
                )
            else:
                stats["processed"] += 1
                logger.info(f"TRANSCRIPT [PROCESS]: '{event.transcript}'")
    
    # Create the agent with demo instructions
    agent = Agent(
        instructions="""You are a helpful assistant demonstrating intelligent 
interruption handling.

BEHAVIOR RULES:
1. When the user asks a question, give a LONG detailed answer (at least 3-4 sentences).
2. While you are speaking, if the user says "yeah", "ok", "hmm", "uh-huh" - you IGNORE it and continue speaking.
3. If the user says "stop", "wait", "no", "but" - you STOP immediately.
4. When you are silent and the user says "yeah" or "ok" - you RESPOND to it.

HOW TO START:
1. Greet the user briefly
2. Ask them: "Ask me any question - like 'Tell me about space' or 'Explain AI'. 
   While I'm answering, try saying 'yeah' or 'ok' and watch me continue speaking.
   But if you say 'stop', I'll stop immediately."

WHEN ANSWERING:
- Give detailed, multi-sentence responses
- Speak continuously for at least 15-20 seconds
- This gives the user time to test backchannel words

EXAMPLES OF GOOD TOPICS TO EXPLAIN:
- "Tell me about the solar system" - You explain planets, orbits, distances
- "Explain how computers work" - You explain CPU, memory, storage
- "What is artificial intelligence" - You explain ML, neural networks, applications

Remember: Keep talking through "yeah/ok" but stop for "stop/wait"."""
    )
    
    # Start the session
    await session.start(agent=agent, room=ctx.room)
    
    logger.info("Backchannel-filtered agent started")
    logger.info("Test scenarios:")
    logger.info("  1. Say 'yeah', 'ok', 'hmm' while agent speaks -> Should continue")
    logger.info("  2. Say 'yeah' when agent is silent -> Should respond")
    logger.info("  3. Say 'stop' or 'wait' anytime -> Should stop")
    logger.info("  4. Say 'yeah but wait' -> Should stop (contains 'but wait')")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
