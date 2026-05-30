"""In-memory demo store for calls, tickets, evaluations, and prompt versions.

This is intentionally simple and process-local. Swap for a real database
(Postgres, DynamoDB, etc.) behind the same accessor methods for production.
"""

from __future__ import annotations

import itertools
from typing import Optional

from .models import (
    Call,
    EvaluationResult,
    PromptVersion,
    Ticket,
    ToolCall,
    TranscriptLine,
)

_ticket_counter = itertools.count(1)
_call_counter = itertools.count(1)
_eval_counter = itertools.count(1)


class Store:
    def __init__(self) -> None:
        self.calls: dict[str, Call] = {}
        self.tickets: list[Ticket] = []
        self.tool_calls: list[ToolCall] = []
        self.evaluations: list[EvaluationResult] = []
        self.prompt_versions: list[PromptVersion] = [
            PromptVersion(version="v1.0", notes="Baseline production prompt.")
        ]
        # Seed data disabled — dashboard shows only real bot activity.
        # self._seed()

    # ---- ID helpers -----------------------------------------------------
    def next_ticket_id(self, category_code: str = "311") -> str:
        return f"{category_code}-{next(_ticket_counter):05d}"

    def next_call_id(self) -> str:
        return f"call_{next(_call_counter):04d}"

    def next_eval_id(self) -> str:
        return f"eval_{next(_eval_counter):04d}"

    # ---- Calls ----------------------------------------------------------
    def add_call(self, call: Call) -> Call:
        self.calls[call.call_id] = call
        return call

    def get_call(self, call_id: str) -> Optional[Call]:
        return self.calls.get(call_id)

    def append_transcript(self, call_id: str, line: TranscriptLine) -> None:
        call = self.calls.get(call_id)
        if call:
            call.transcript.append(line)

    def list_calls(self) -> list[Call]:
        return sorted(
            self.calls.values(), key=lambda c: c.started_at, reverse=True
        )

    # ---- Tickets --------------------------------------------------------
    def add_ticket(self, ticket: Ticket) -> Ticket:
        self.tickets.append(ticket)
        return ticket

    def list_tickets(self) -> list[Ticket]:
        return list(reversed(self.tickets))

    # ---- Tool calls -----------------------------------------------------
    def add_tool_call(self, tool_call: ToolCall) -> ToolCall:
        self.tool_calls.append(tool_call)
        return tool_call

    def list_tool_calls(self) -> list[ToolCall]:
        return list(reversed(self.tool_calls))

    # ---- Evaluations ----------------------------------------------------
    def add_evaluation(self, result: EvaluationResult) -> EvaluationResult:
        self.evaluations.append(result)
        return result

    def list_evaluations(self) -> list[EvaluationResult]:
        return list(self.evaluations)

    # ---- Prompt versions ------------------------------------------------
    def current_prompt_version(self) -> PromptVersion:
        return self.prompt_versions[-1]

    def add_prompt_version(self, version: PromptVersion) -> PromptVersion:
        self.prompt_versions.append(version)
        return version

    # ---- Seed demo data -------------------------------------------------
    def _seed(self) -> None:
        from .models import Priority, TicketStatus, Call, CallStatus, TranscriptLine, EvaluationResult
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        # 6 tickets
        self.tickets.extend([
            Ticket(
                ticket_id="POT-240530-001",
                category="Pothole",
                location="Market Street near 5th Avenue",
                description="Large pothole, approx 2 feet wide in the right lane",
                status=TicketStatus.OPEN,
                priority=Priority.NORMAL,
                created_at=(now - timedelta(minutes=12)).isoformat(),
            ),
            Ticket(
                ticket_id="STL-240530-002",
                category="Broken Streetlight",
                location="Elm Street & Pine Avenue",
                description="Streetlight outage reported by citizen",
                status=TicketStatus.OPEN,
                priority=Priority.NORMAL,
                created_at=(now - timedelta(minutes=25)).isoformat(),
            ),
            Ticket(
                ticket_id="WTR-240530-003",
                category="Water Leak",
                location="Pine Street 200 block",
                description="Water leak reported. Severity: severe.",
                status=TicketStatus.OPEN,
                priority=Priority.URGENT,
                created_at=(now - timedelta(minutes=40)).isoformat(),
            ),
            Ticket(
                ticket_id="GRF-240530-004",
                category="Graffiti",
                location="Oak Avenue underpass",
                description="Spray paint on concrete wall, about 6 feet wide",
                status=TicketStatus.OPEN,
                priority=Priority.LOW,
                created_at=(now - timedelta(minutes=55)).isoformat(),
            ),
            Ticket(
                ticket_id="ESC-240530-005",
                category="Escalation",
                location="N/A",
                description="Escalated to human agent. Reason: Caller frustrated with repeated pothole issue.",
                status=TicketStatus.ESCALATED,
                priority=Priority.URGENT,
                created_at=(now - timedelta(minutes=70)).isoformat(),
            ),
            Ticket(
                ticket_id="ABV-240530-006",
                category="Abandoned Vehicle",
                location="Cedar Lane near the park",
                description="Abandoned vehicle: blue sedan, no plates, flat tires.",
                status=TicketStatus.OPEN,
                priority=Priority.NORMAL,
                created_at=(now - timedelta(minutes=85)).isoformat(),
            ),
        ])

        # 8 tool calls
        self.tool_calls.extend([
            ToolCall(tool="create_pothole_ticket", args={"location": "Market Street near 5th"}, result={"ok": True}, status="success", timestamp=(now - timedelta(minutes=12)).isoformat()),
            ToolCall(tool="check_trash_schedule", args={"address": "120 Oak Avenue"}, result={"day": "Tuesday"}, status="success", timestamp=(now - timedelta(minutes=18)).isoformat()),
            ToolCall(tool="report_broken_streetlight", args={"location": "Elm & Pine"}, result={"ok": True}, status="success", timestamp=(now - timedelta(minutes=25)).isoformat()),
            ToolCall(tool="report_water_leak", args={"location": "Pine Street", "severity": "severe"}, result={"ok": True}, status="success", timestamp=(now - timedelta(minutes=40)).isoformat()),
            ToolCall(tool="get_city_policy", args={"topic": "noise"}, result={"found": True}, status="success", timestamp=(now - timedelta(minutes=50)).isoformat()),
            ToolCall(tool="report_graffiti", args={"location": "Oak Avenue underpass"}, result={"ok": True}, status="success", timestamp=(now - timedelta(minutes=55)).isoformat()),
            ToolCall(tool="report_abandoned_vehicle", args={"location": "Cedar Lane near park"}, result={"ok": True}, status="success", timestamp=(now - timedelta(minutes=65)).isoformat()),
            ToolCall(tool="escalate_to_human", args={"reason": "Frustrated caller"}, result={"ok": True}, status="success", timestamp=(now - timedelta(minutes=70)).isoformat()),
        ])

        # Add an initial ended call
        self.calls["call-civora-001"] = Call(
            call_id="call-civora-001",
            caller_phone="+1 (555) 867-5309",
            status=CallStatus.ENDED,
            language="en",
            intent="Report Pothole",
            sentiment="neutral",
            started_at=(now - timedelta(minutes=15)).isoformat(),
            ended_at=(now - timedelta(minutes=12)).isoformat(),
            duration_seconds=187,
            transcript=[
                TranscriptLine(role="assistant", text="Hello, you've reached City 311. How can I help you today?", timestamp=(now - timedelta(minutes=14, seconds=30)).isoformat()),
                TranscriptLine(role="citizen", text="Yeah, there's a huge pothole on Market Street near 5th Avenue.", timestamp=(now - timedelta(minutes=14)).isoformat()),
                TranscriptLine(role="assistant", text="Got it. Just to confirm — that's Market Street near 5th Avenue?", timestamp=(now - timedelta(minutes=13, seconds=30)).isoformat()),
                TranscriptLine(role="citizen", text="Yes, that's right.", timestamp=(now - timedelta(minutes=13, seconds=10)).isoformat()),
                TranscriptLine(role="assistant", text="I've filed a pothole report. Your ticket ID is P-O-T-00001. A crew should be out to inspect within 3–5 business days. Anything else I can help with?", timestamp=(now - timedelta(minutes=13)).isoformat()),
                TranscriptLine(role="citizen", text="No, that's all. Thanks!", timestamp=(now - timedelta(minutes=12, seconds=30)).isoformat()),
                TranscriptLine(role="assistant", text="Thanks for calling 311. Have a good day!", timestamp=(now - timedelta(minutes=12)).isoformat()),
            ]
        )

        # Seed evaluations
        self.evaluations.extend([
            EvaluationResult(
                run_id="eval-1",
                task_success_rate=0.68,
                address_capture_accuracy=0.70,
                escalation_precision=0.75,
                average_latency_ms=920,
                citizen_sentiment_score=0.65,
                hallucination_rate=0.12,
                overall_score=0.72,
                prompt_version="v1.0",
                created_at=(now - timedelta(hours=2)).isoformat(),
            ),
            EvaluationResult(
                run_id="eval-2",
                task_success_rate=0.80,
                address_capture_accuracy=0.82,
                escalation_precision=0.88,
                average_latency_ms=830,
                citizen_sentiment_score=0.78,
                hallucination_rate=0.07,
                overall_score=0.81,
                prompt_version="v1.1",
                created_at=(now - timedelta(hours=1)).isoformat(),
            ),
            EvaluationResult(
                run_id="eval-3",
                task_success_rate=0.92,
                address_capture_accuracy=0.88,
                escalation_precision=0.95,
                average_latency_ms=780,
                citizen_sentiment_score=0.85,
                hallucination_rate=0.03,
                overall_score=0.91,
                prompt_version="v1.2",
                created_at=(now - timedelta(minutes=5)).isoformat(),
            )
        ])

        # Seed prompt versions
        self.prompt_versions.extend([
            PromptVersion(version="v1.1", notes="Added address confirmation, emergency 911 redirect, anti-hallucination rules.", created_at=(now - timedelta(hours=1)).isoformat()),
            PromptVersion(version="v1.2", notes="Refined escalation logic, privacy guardrails, shorter turn length.", created_at=(now - timedelta(minutes=5)).isoformat()),
        ])


store = Store()
