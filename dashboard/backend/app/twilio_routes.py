"""Twilio Programmable Voice webhook + Media Streams WebSocket handler.

`POST /twilio/voice` returns TwiML connecting the call to the media WebSocket.
`WS /twilio/media` accepts Twilio Media Stream events. In demo/mock mode we
don't require real audio decoding — we simulate transcript + AI activity so the
dashboard lights up during a live phone call.
"""

from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from .config import settings
from .events import event_bus
from .models import Call, CallStatus
from .services.pipecat_agent import PipecatMunicipalAgent
from .state import store

router = APIRouter(tags=["twilio"])
_agent = PipecatMunicipalAgent()


@router.post("/twilio/voice")
async def twilio_voice(request: Request) -> Response:
    """Return TwiML that connects the inbound call to Pipecat Cloud."""
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://api.pipecat.daily.co/ws/twilio">
      <Parameter name="_pipecatCloudServiceHost" value="civora-311.flexible-chickadee-apricot-837"/>
    </Stream>
  </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@router.websocket("/twilio/media")
async def twilio_media(ws: WebSocket) -> None:
    await ws.accept()
    call: Call | None = None
    media_packets = 0

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "connected":
                continue

            if event == "start":
                start = msg.get("start", {})
                caller = start.get("customParameters", {}).get("from") or "+1 (555) 311-0000"
                call = Call(
                    call_id=store.next_call_id(),
                    caller_phone=caller,
                    status=CallStatus.ACTIVE,
                )
                store.add_call(call)
                await event_bus.publish("call_started", call.model_dump())
                # Greet the caller.
                await event_bus.publish(
                    "ai_response",
                    {
                        "role": "assistant",
                        "text": "Hello, you've reached the city 311 assistant. How can I help you today?",
                        "call_id": call.call_id,
                    },
                )

            elif event == "media":
                # In MOCK_MODE we don't transcribe real audio. Every N media
                # packets we simulate a citizen utterance so the demo flows.
                media_packets += 1
                if settings.mock_mode and call and media_packets % 120 == 0:
                    sample = "There is a large pothole on Market Street near 5th."
                    await _agent.process_user_turn(
                        sample, caller_phone=call.caller_phone, call_id=call.call_id
                    )
                # Production: decode base64 mu-law and feed Nova Sonic / Pipecat.
                _ = msg.get("media", {}).get("payload")  # base64 mu-law audio

            elif event == "stop":
                if call:
                    call.status = CallStatus.ENDED
                    await event_bus.publish("call_ended", {"call_id": call.call_id})
                break

    except WebSocketDisconnect:
        if call:
            call.status = CallStatus.ENDED
            await event_bus.publish("call_ended", {"call_id": call.call_id})
