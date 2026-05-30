"""A tiny in-process pub/sub event bus built on asyncio.Queue.

Backend components publish dashboard events here; the SSE endpoint
(`GET /api/events/stream`) subscribes and forwards them to the frontend.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[str]] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event to every subscriber.

        Wire format is SSE-friendly JSON: {"type": ..., "data": ..., "ts": ...}
        """
        payload = json.dumps(
            {
                "type": event_type,
                "data": data,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
        async with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                # Drop events for slow consumers rather than blocking producers.
                pass


# Module-level singleton used everywhere.
event_bus = EventBus()
