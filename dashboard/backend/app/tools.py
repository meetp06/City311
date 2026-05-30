"""Mock city-service tool functions for the 311 assistant.

Each function is typed, side-effecting against the in-memory store, and emits
both a ToolCall record and the relevant dashboard events. Replace the bodies
with real database / city-API calls for production; keep the signatures.
"""

from __future__ import annotations

import random
from typing import Optional

from .events import event_bus
from .models import Priority, Ticket, TicketStatus, ToolCall
from .state import store

# Mock knowledge base for get_city_policy.
_CITY_POLICY: dict[str, str] = {
    "trash": "Residential trash is collected weekly. Bins must be at the curb by 7 AM.",
    "recycling": "Recycling is collected every other week on your regular pickup day.",
    "pothole": "Reported potholes are typically assessed within 3 business days.",
    "parking": "Street parking permits are issued by the Department of Transportation.",
    "noise": "Quiet hours are 10 PM to 7 AM. Noise complaints are routed to code enforcement.",
    "water": "Water main issues are prioritized by severity; severe leaks get same-day dispatch.",
}


async def _record(tool: str, args: dict, result: dict, status: str = "success") -> None:
    """Persist a ToolCall and broadcast it to the dashboard."""
    tc = ToolCall(tool=tool, args=args, result=result, status=status)
    store.add_tool_call(tc)
    await event_bus.publish("tool_called", tc.model_dump())


async def _file_ticket(
    *,
    category: str,
    code: str,
    location: str,
    description: str,
    priority: Priority,
) -> Ticket:
    ticket = Ticket(
        ticket_id=store.next_ticket_id(code),
        category=category,
        location=location or "location unconfirmed",
        description=description,
        status=TicketStatus.OPEN,
        priority=priority,
    )
    store.add_ticket(ticket)
    await event_bus.publish("ticket_created", ticket.model_dump())
    return ticket


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------
async def check_trash_schedule(address: str) -> dict:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    day = random.choice(days)
    result = {
        "address": address,
        "next_pickup_day": day,
        "recycling_week": random.choice(["this week", "next week"]),
        "note": "Place bins curbside by 7 AM.",
    }
    await _record("check_trash_schedule", {"address": address}, result)
    return result


async def create_pothole_ticket(location: str, description: str) -> dict:
    ticket = await _file_ticket(
        category="Pothole",
        code="POT",
        location=location,
        description=description,
        priority=Priority.NORMAL,
    )
    result = ticket.model_dump()
    await _record(
        "create_pothole_ticket",
        {"location": location, "description": description},
        result,
    )
    return result


async def report_broken_streetlight(location: str) -> dict:
    ticket = await _file_ticket(
        category="Broken Streetlight",
        code="LGT",
        location=location,
        description="Streetlight outage reported by citizen.",
        priority=Priority.NORMAL,
    )
    result = ticket.model_dump()
    await _record("report_broken_streetlight", {"location": location}, result)
    return result


async def report_water_leak(location: str, severity: str = "moderate") -> dict:
    severe = severity.lower() in {"severe", "high", "bad", "major"}
    ticket = await _file_ticket(
        category="Water Leak",
        code="WTR",
        location=location,
        description=f"Water leak reported. Severity: {severity}.",
        priority=Priority.URGENT if severe else Priority.HIGH,
    )
    result = ticket.model_dump()
    await _record(
        "report_water_leak",
        {"location": location, "severity": severity},
        result,
    )
    return result


async def report_graffiti(location: str, description: str) -> dict:
    ticket = await _file_ticket(
        category="Graffiti",
        code="GRF",
        location=location,
        description=description,
        priority=Priority.LOW,
    )
    result = ticket.model_dump()
    await _record(
        "report_graffiti",
        {"location": location, "description": description},
        result,
    )
    return result


async def report_abandoned_vehicle(location: str, vehicle_description: str) -> dict:
    ticket = await _file_ticket(
        category="Abandoned Vehicle",
        code="VEH",
        location=location,
        description=f"Abandoned vehicle: {vehicle_description}.",
        priority=Priority.NORMAL,
    )
    result = ticket.model_dump()
    await _record(
        "report_abandoned_vehicle",
        {"location": location, "vehicle_description": vehicle_description},
        result,
    )
    return result


async def escalate_to_human(reason: str, caller_phone: Optional[str] = None) -> dict:
    ticket = await _file_ticket(
        category="Escalation",
        code="ESC",
        location="N/A",
        description=f"Escalated to human agent. Reason: {reason}.",
        priority=Priority.URGENT,
    )
    ticket.status = TicketStatus.ESCALATED
    result = {
        **ticket.model_dump(),
        "caller_phone": caller_phone,
        "queue_position": random.randint(1, 4),
    }
    await _record(
        "escalate_to_human",
        {"reason": reason, "caller_phone": caller_phone},
        result,
    )
    return result


async def get_city_policy(topic: str) -> dict:
    key = next((k for k in _CITY_POLICY if k in topic.lower()), None)
    answer = _CITY_POLICY.get(
        key, "I don't have that policy on file. I can connect you with a human agent."
    )
    result = {"topic": topic, "answer": answer, "found": key is not None}
    await _record("get_city_policy", {"topic": topic}, result)
    return result
