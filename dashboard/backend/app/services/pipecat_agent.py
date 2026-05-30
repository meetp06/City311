"""PipecatMunicipalAgent — orchestrates a single 311 conversation turn.

For demo reliability the agent uses deterministic intent routing rather than a
live LLM. The comments mark exactly where a production Pipecat pipeline would
attach the Twilio transport, AWS Nova Sonic STS service, NVIDIA NIM ASR, and
the tool/function-calling layer.

Production pipeline sketch (Pipecat):

    pipeline = Pipeline([
        twilio_transport.input(),        # Twilio Media Streams -> frames
        nova_sonic_service,              # AWS Bedrock Nova Sonic (speech<->speech)
        tool_processor,                  # function calling -> app.tools
        twilio_transport.output(),       # frames -> Twilio Media Streams
    ])
    # NVIDIA NIM is invoked inside tool_processor for address verification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .. import tools
from ..events import event_bus
from ..models import TranscriptLine
from ..state import store
from .nvidia_nim import NvidiaNimASRService
from .nova_sonic import AWSNovaSonicService

EMERGENCY_KEYWORDS = (
    "fire",
    "gun",
    "shooting",
    "bleeding",
    "not breathing",
    "heart attack",
    "gas leak",
    "explosion",
    "someone is hurt",
)


@dataclass
class TurnResult:
    intent: str
    assistant_text: str
    sentiment: str
    language: str


class PipecatMunicipalAgent:
    def __init__(self) -> None:
        self.nova = AWSNovaSonicService()
        self.nim = NvidiaNimASRService()

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _detect_language(text: str) -> str:
        if re.search(r"[áéíóúñ¿¡]", text, re.IGNORECASE) or any(
            w in text.lower() for w in ("hola", "calle", "agua", "necesito")
        ):
            return "Spanish"
        return "English"

    @staticmethod
    def _detect_sentiment(text: str) -> str:
        lowered = text.lower()
        if any(w in lowered for w in ("frustrated", "angry", "ridiculous", "terrible", "furious")):
            return "frustrated"
        if any(w in lowered for w in ("thank", "great", "appreciate", "perfect")):
            return "positive"
        return "neutral"

    @staticmethod
    def _extract_location(text: str) -> str:
        # Grab "on/at/near/for <something>" phrases; fall back to whole text.
        m = re.search(r"(?:on|at|near|outside|for)\s+([A-Za-z0-9 ,.'/&-]+)", text)
        loc = (m.group(1) if m else text).strip()
        # Trim trailing clause noise like "is broken" / "near my house".
        loc = re.split(r"\b(is broken|is out|outside my|near my|by my)\b", loc)[0]
        return loc.strip(" .,")

    # -- main entry point ------------------------------------------------
    async def process_user_turn(
        self, text: str, caller_phone: Optional[str] = None, call_id: Optional[str] = None
    ) -> TurnResult:
        """Process one citizen utterance: route intent, call tools, respond."""
        language = self._detect_language(text)
        sentiment = self._detect_sentiment(text)
        lowered = text.lower()

        # Record + broadcast the citizen line.
        if call_id:
            line = TranscriptLine(role="citizen", text=text)
            store.append_transcript(call_id, line)
        await event_bus.publish(
            "transcript_update",
            {"role": "citizen", "text": text, "call_id": call_id},
        )

        intent, assistant_text = await self._route(lowered, text, caller_phone)

        # Update call metadata if we have a live call.
        if call_id and (call := store.get_call(call_id)):
            call.intent = intent
            call.sentiment = sentiment
            call.language = language

        # Record + broadcast the assistant response.
        if call_id:
            store.append_transcript(call_id, TranscriptLine(role="assistant", text=assistant_text))
        await event_bus.publish(
            "ai_response",
            {"role": "assistant", "text": assistant_text, "intent": intent, "call_id": call_id},
        )

        return TurnResult(
            intent=intent, assistant_text=assistant_text, sentiment=sentiment, language=language
        )

    # -- deterministic intent router ------------------------------------
    async def _route(self, lowered: str, raw: str, caller_phone: Optional[str]) -> tuple[str, str]:
        # 1) Emergencies first.
        if any(k in lowered for k in EMERGENCY_KEYWORDS):
            await tools.escalate_to_human("Possible life-safety emergency", caller_phone)
            return (
                "emergency",
                "This sounds like an emergency. Please hang up and call 911 right away. "
                "I've also flagged a human agent to follow up.",
            )

        # 2) Explicit human request / strong frustration.
        if "human" in lowered or "agent" in lowered or "person" in lowered or "representative" in lowered:
            res = await tools.escalate_to_human("Caller requested a human agent", caller_phone)
            return (
                "escalation",
                f"Of course — I'm connecting you with a human agent now. "
                f"Your reference number is {res['ticket_id']}. "
                f"You're number {res['queue_position']} in the queue.",
            )

        # 3) Service categories.
        if "pothole" in lowered:
            loc = await self._verify_location(self._extract_location(raw))
            res = await tools.create_pothole_ticket(loc, raw)
            return ("pothole", self._ticket_reply("pothole", loc, res["ticket_id"]))

        if "trash" in lowered or "garbage" in lowered:
            if "missed" in lowered or "didn" in lowered or "not picked" in lowered:
                loc = self._extract_location(raw)
                res = await tools.escalate_to_human(f"Missed garbage pickup at {loc}", caller_phone)
                return (
                    "missed_garbage",
                    f"I'm sorry your pickup was missed. I've filed a follow-up, reference "
                    f"{res['ticket_id']}, and a crew will be notified.",
                )
            loc = self._extract_location(raw)
            res = await tools.check_trash_schedule(loc)
            return (
                "trash_schedule",
                f"For {loc}, the next trash pickup is {res['next_pickup_day']}, "
                f"and recycling is {res['recycling_week']}. Please have bins out by 7 AM.",
            )

        if "streetlight" in lowered or "street light" in lowered or "light is" in lowered:
            loc = await self._verify_location(self._extract_location(raw))
            res = await tools.report_broken_streetlight(loc)
            return ("broken_streetlight", self._ticket_reply("streetlight outage", loc, res["ticket_id"]))

        if "water" in lowered or "leak" in lowered or "pipe" in lowered:
            severity = "severe" if any(w in lowered for w in ("badly", "severe", "gushing", "flooding")) else "moderate"
            loc = await self._verify_location(self._extract_location(raw))
            res = await tools.report_water_leak(loc, severity)
            extra = " Because this is severe, I've marked it urgent for same-day dispatch." if severity == "severe" else ""
            return ("water_leak", self._ticket_reply("water leak", loc, res["ticket_id"]) + extra)

        if "graffiti" in lowered:
            loc = await self._verify_location(self._extract_location(raw))
            res = await tools.report_graffiti(loc, raw)
            return ("graffiti", self._ticket_reply("graffiti report", loc, res["ticket_id"]))

        if "abandoned" in lowered or ("vehicle" in lowered and "car" in lowered):
            loc = await self._verify_location(self._extract_location(raw))
            res = await tools.report_abandoned_vehicle(loc, raw)
            return ("abandoned_vehicle", self._ticket_reply("abandoned vehicle", loc, res["ticket_id"]))

        if "noise" in lowered or "loud" in lowered:
            res = await tools.get_city_policy("noise")
            return ("noise_complaint", f"{res['answer']} I can file a complaint if you give me the address.")

        if "parking" in lowered or "permit" in lowered:
            res = await tools.get_city_policy("parking")
            return ("parking_issue", res["answer"])

        # 4) Knowledge / fallback.
        policy = await tools.get_city_policy(lowered)
        if policy["found"]:
            return ("policy_lookup", policy["answer"])

        return (
            "general",
            "I can help with potholes, trash pickup, streetlights, water leaks, graffiti, "
            "abandoned vehicles, noise, and parking. What would you like to report?",
        )

    async def _verify_location(self, location: str) -> str:
        """Run the address through NVIDIA NIM for a cleaner string."""
        verified = await self.nim.transcribe_address(location)
        return verified["address"]

    @staticmethod
    def _ticket_reply(kind: str, location: str, ticket_id: str) -> str:
        return (
            f"Thank you. I've filed a {kind} at {location}. "
            f"Your ticket number is {ticket_id}. Is there anything else I can help with?"
        )
