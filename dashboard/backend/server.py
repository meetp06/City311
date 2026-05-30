"""FastAPI application entrypoint for the Municipal 311 City Assistant."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Literal, Dict, Any
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse


def _require_demo_enabled() -> None:
    """Gate /api/demo/* and /api/evals/run endpoints.

    These endpoints can mutate dashboard state and burn Cekura credits, so
    they are disabled by default. Set ``DEMO_ENDPOINTS_ENABLED=1`` to re-enable
    them during local development. The deployed (public) instance leaves this
    unset, which makes these endpoints return 403.
    """
    if os.environ.get("DEMO_ENDPOINTS_ENABLED") != "1":
        raise HTTPException(
            status_code=403,
            detail="Demo and evaluation endpoints are disabled on this instance.",
        )

from app.cekura_client import CekuraClient
from app.config import settings
from app.events import event_bus
from app.models import Call, CallStatus, TranscriptRequest, Priority, TicketStatus, TranscriptLine, Ticket, ToolCall
from app.services.pipecat_agent import PipecatMunicipalAgent
from app.state import store
from app.twilio_routes import router as twilio_router

app = FastAPI(title="Municipal 311 City Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(twilio_router)

agent = PipecatMunicipalAgent()
cekura = CekuraClient()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/")
async def root() -> dict:
    return {
        "service": settings.service_name,
        "status": "running",
        "mock_mode": settings.mock_mode,
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


# ---------------------------------------------------------------------------
# Webhook integration from voice bot
# ---------------------------------------------------------------------------
class WebhookEvent(BaseModel):
    event_type: Literal["call_started", "transcript_added", "ticket_created", "tool_called", "call_ended"]
    call_id: str
    data: Dict[str, Any]

@app.post("/api/webhook/event")
async def receive_webhook_event(event: WebhookEvent) -> dict:
    if event.event_type == "call_started":
        caller_phone = event.data.get("caller_phone", "+1 (555) 311-0000")
        call = Call(
            call_id=event.call_id,
            caller_phone=caller_phone,
            status=CallStatus.ACTIVE,
        )
        store.add_call(call)
        await event_bus.publish("call_started", call.model_dump())
    
    elif event.event_type == "transcript_added":
        role = event.data.get("role", "assistant")
        text = event.data.get("text", "")
        line = TranscriptLine(role=role, text=text)
        store.append_transcript(event.call_id, line)
        await event_bus.publish("transcript_added", {
            "call_id": event.call_id,
            "role": role,
            "text": text,
            "timestamp": line.timestamp,
        })
        
    elif event.event_type == "ticket_created":
        raw_status = str(event.data.get("status", "open")).strip().lower().replace(" ", "_").replace("-", "_")
        try:
            status_val = TicketStatus(raw_status)
        except ValueError:
            status_val = TicketStatus.OPEN

        raw_priority = str(event.data.get("priority", "normal")).strip().lower().replace(" ", "_").replace("-", "_")
        try:
            priority_val = Priority(raw_priority)
        except ValueError:
            priority_val = Priority.NORMAL

        ticket = Ticket(
            ticket_id=event.data.get("ticket_id", "311-00000"),
            category=event.data.get("category", "General"),
            location=event.data.get("location", "N/A"),
            description=event.data.get("description", ""),
            status=status_val,
            priority=priority_val,
        )
        store.add_ticket(ticket)
        await event_bus.publish("ticket_created", ticket.model_dump())
        
    elif event.event_type == "tool_called":
        tool_call = ToolCall(
            tool=event.data.get("tool", ""),
            args=event.data.get("args", {}),
            result=event.data.get("result", {}),
            status=event.data.get("status", "success"),
        )
        store.add_tool_call(tool_call)
        await event_bus.publish("tool_called", tool_call.model_dump())
        
    elif event.event_type == "call_ended":
        call = store.get_call(event.call_id)
        if call:
            call.status = CallStatus.ENDED
            call.ended_at = datetime.now(timezone.utc).isoformat()
            try:
                started = datetime.fromisoformat(call.started_at)
                ended = datetime.fromisoformat(call.ended_at)
                call.duration_seconds = int((ended - started).total_seconds())
            except Exception:
                pass
        await event_bus.publish("call_ended", {"call_id": event.call_id})
        
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Calls & tickets
# ---------------------------------------------------------------------------
@app.get("/api/calls")
async def get_calls() -> dict:
    calls = [c.model_dump() for c in store.list_calls()]
    active = [c for c in calls if c["status"] == CallStatus.ACTIVE.value]
    return {"active": active, "recent": calls}


@app.get("/api/tickets")
async def get_tickets() -> dict:
    return {"tickets": [t.model_dump() for t in store.list_tickets()]}


@app.get("/api/tool-calls")
async def get_tool_calls() -> dict:
    return {"tool_calls": [t.model_dump() for t in store.list_tool_calls()]}


# ---------------------------------------------------------------------------
# Demo controls
# ---------------------------------------------------------------------------
@app.post("/api/demo/start-call")
async def start_demo_call(payload: dict | None = None) -> dict:
    _require_demo_enabled()
    phone = (payload or {}).get("caller_phone", "+1 (555) 311-0199")
    call = Call(call_id=store.next_call_id(), caller_phone=phone, status=CallStatus.ACTIVE)
    store.add_call(call)
    await event_bus.publish("call_started", call.model_dump())
    await event_bus.publish(
        "ai_response",
        {
            "role": "assistant",
            "text": "Hello, you've reached the city 311 assistant. How can I help you today?",
            "call_id": call.call_id,
        },
    )
    return {"call": call.model_dump()}


@app.post("/api/demo/transcript")
async def demo_transcript(req: TranscriptRequest) -> dict:
    _require_demo_enabled()
    # Use the most recent active call if none specified.
    call_id = req.call_id
    if not call_id:
        active = [c for c in store.list_calls() if c.status == CallStatus.ACTIVE]
        call_id = active[0].call_id if active else None

    result = await agent.process_user_turn(
        req.text, caller_phone=req.caller_phone, call_id=call_id
    )
    return {
        "intent": result.intent,
        "assistant_text": result.assistant_text,
        "sentiment": result.sentiment,
        "language": result.language,
        "call_id": call_id,
    }


@app.post("/api/demo/end-call")
async def end_demo_call(payload: dict | None = None) -> dict:
    _require_demo_enabled()
    call_id = (payload or {}).get("call_id")
    if not call_id:
        active = [c for c in store.list_calls() if c.status == CallStatus.ACTIVE]
        call_id = active[0].call_id if active else None
    if call_id and (call := store.get_call(call_id)):
        call.status = CallStatus.ENDED
        await event_bus.publish("call_ended", {"call_id": call_id})
    return {"call_id": call_id, "status": "ended"}


# ---------------------------------------------------------------------------
# Evaluations (Cekura)
# ---------------------------------------------------------------------------
@app.post("/api/evals/run")
async def run_evaluation() -> dict:
    _require_demo_enabled()
    job = await cekura.run_scenarios()
    # Brief simulated test runtime for a believable demo loading state.
    await asyncio.sleep(1.2 if settings.mock_mode else 0)
    result = await cekura.get_results(job["job_id"])
    return {
        "result": result.model_dump(),
        "prompt_versions": [v.model_dump() for v in store.prompt_versions],
    }


@app.get("/api/evals/history")
async def eval_history() -> dict:
    return {
        "history": [e.model_dump() for e in store.list_evaluations()],
        "prompt_versions": [v.model_dump() for v in store.prompt_versions],
    }


# ---------------------------------------------------------------------------
# Server-Sent Events stream
# ---------------------------------------------------------------------------
@app.get("/api/events/stream")
async def events_stream() -> StreamingResponse:
    async def generator():
        queue = await event_bus.subscribe()
        # Initial hello so EventSource opens cleanly.
        yield 'data: {"type": "connected", "data": {}}\n\n'
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive comment to prevent proxies from closing the stream.
                    yield ": keep-alive\n\n"
        finally:
            await event_bus.unsubscribe(queue)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
