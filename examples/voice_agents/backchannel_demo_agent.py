"""
Backchannel-Filtered Demo Agent

Demonstrates intelligent interruption handling:
- Backchannels like "yeah", "ok", "hmm" are ignored while agent speaks
- Commands like "stop", "wait" interrupt immediately
- When agent is silent, all input is processed
"""

from __future__ import annotations

import logging
import os
import sys

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

from interrupt_handler import (
    InterruptionConfig,
    InterruptDecision,
    InterruptionHandler,   # ✅ USE HANDLER, NOT DETECTOR
)

# ---------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backchannel_demo")

# ---------------------------------------------------------------------


class Stats:
    def __init__(self):
        self.ignored = 0
        self.interrupted = 0
        self.processed = 0

    def summary(self):
        logger.info(
            "\nBackchannel Summary\n"
            f"  Ignored:      {self.ignored}\n"
            f"  Interrupted: {self.interrupted}\n"
            f"  Processed:   {self.processed}"
        )


stats = Stats()


async def entrypoint(ctx: JobContext):
    logger.info("Starting Backchannel Demo Agent")

    # -----------------------------------------------------------------
    # INTERRUPTION CONFIG + HANDLER
    # -----------------------------------------------------------------
    config = InterruptionConfig()
    config.debug_mode = True

    handler = InterruptionHandler(config)

    await ctx.connect()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=cartesia.TTS(),
        vad=silero.VAD.load(),
        allow_interruptions=True,
    )

    # -----------------------------------------------------------------
    # AGENT STATE TRACKING (CRITICAL)
    # -----------------------------------------------------------------
    @session.on("agent_state_changed")
    def on_agent_state(event: AgentStateChangedEvent):
        handler.set_agent_speaking(event.new_state == "speaking")

    # -----------------------------------------------------------------
    # TRANSCRIPT HANDLING (CRITICAL FIX)
    # -----------------------------------------------------------------
    @session.on("user_input_transcribed")
    async def on_transcript(event: UserInputTranscribedEvent):
        if not event.is_final:
            return

        transcript = event.transcript.strip()

        decision = handler.handle_transcript(transcript)

        if decision == InterruptDecision.IGNORE:
            stats.ignored += 1
            logger.info(f"Ignored backchannel: '{transcript}'")
            return  # ✅ swallow completely

        if decision == InterruptDecision.INTERRUPT:
            stats.interrupted += 1
            logger.info(f"Interrupting agent: '{transcript}'")
            await session.interrupt(force=True)
            return

        # NORMAL PROCESSING
        stats.processed += 1
        logger.info(f"Processed: '{transcript}'")

    # -----------------------------------------------------------------
    # AGENT
    # -----------------------------------------------------------------
    agent = Agent(
        instructions=(
            "I will demonstrate interruption handling. "
            "Say 'yeah' while I speak and I will continue. "
            "Say 'stop' and I will stop."
        )
    )

    await session.start(agent=agent, room=ctx.room)


def main():
    try:
        cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
    except KeyboardInterrupt:
        logger.info("Agent stopped")
    finally:
        stats.summary()


if __name__ == "__main__":
    main()
