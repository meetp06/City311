"""Pydantic models shared across the API and the in-memory store."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class CallStatus(str, Enum):
    RINGING = "ringing"
    ACTIVE = "active"
    ENDED = "ended"


class Ticket(BaseModel):
    ticket_id: str
    category: str
    location: str
    description: str = ""
    status: TicketStatus = TicketStatus.OPEN
    priority: Priority = Priority.NORMAL
    created_at: str = Field(default_factory=_now)


class TranscriptLine(BaseModel):
    role: str  # "citizen" | "assistant" | "system"
    text: str
    timestamp: str = Field(default_factory=_now)


class ToolCall(BaseModel):
    tool: str
    args: dict
    result: dict
    status: str = "success"  # "success" | "error"
    timestamp: str = Field(default_factory=_now)


class Call(BaseModel):
    call_id: str
    caller_phone: str = "+1 (555) 000-0000"
    status: CallStatus = CallStatus.ACTIVE
    language: str = "English"
    intent: str = "—"
    sentiment: str = "neutral"
    started_at: str = Field(default_factory=_now)
    ended_at: Optional[str] = None
    duration_seconds: int = 0
    transcript: list[TranscriptLine] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    run_id: str
    task_success_rate: float
    address_capture_accuracy: float
    escalation_precision: float
    average_latency_ms: int
    citizen_sentiment_score: float
    hallucination_rate: float
    overall_score: float
    prompt_version: str
    created_at: str = Field(default_factory=_now)


class PromptVersion(BaseModel):
    version: str
    notes: str
    created_at: str = Field(default_factory=_now)


class TranscriptRequest(BaseModel):
    text: str
    caller_phone: Optional[str] = None
    call_id: Optional[str] = None
