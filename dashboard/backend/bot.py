"""Standalone bot runner — exercise the agent loop from the terminal.

This is handy for quickly sanity-checking intent routing and tool calls without
the frontend or a phone. In production this file would build and run the full
Pipecat pipeline (Twilio transport + Nova Sonic + tools).

Usage:
    cd backend
    python bot.py
"""

from __future__ import annotations

import asyncio

from app.config import settings
from app.models import Call, CallStatus
from app.prompts import SYSTEM_PROMPT
from app.services.pipecat_agent import PipecatMunicipalAgent
from app.state import store

SAMPLE_TURNS = [
    "There is a huge pothole on Market Street near 5th.",
    "When is trash pickup for 120 Oak Avenue?",
    "A water pipe is leaking badly outside my house on Pine Street.",
    "The streetlight on Pine and 8th is broken.",
    "I need a human. I am very frustrated.",
]


async def main() -> None:
    print(f"[bot] mock_mode={settings.mock_mode}")
    print(f"[bot] system prompt loaded ({len(SYSTEM_PROMPT)} chars)\n")

    agent = PipecatMunicipalAgent()
    call = store.add_call(
        Call(call_id=store.next_call_id(), caller_phone="+1 (555) 311-0001", status=CallStatus.ACTIVE)
    )

    for turn in SAMPLE_TURNS:
        print(f"  citizen  > {turn}")
        result = await agent.process_user_turn(turn, caller_phone=call.caller_phone, call_id=call.call_id)
        print(f"  intent   = {result.intent} | sentiment={result.sentiment} | lang={result.language}")
        print(f"  assistant> {result.assistant_text}\n")

    print(f"[bot] tickets filed: {len(store.tickets)}")
    print(f"[bot] tool calls:   {len(store.tool_calls)}")


if __name__ == "__main__":
    asyncio.run(main())
