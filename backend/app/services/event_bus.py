import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class EventBus:
    """Simple asyncio pub/sub for pushing bot events to WebSocket clients."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.remove(queue)

    async def publish(self, event: dict[str, Any]):
        logger.debug(f"Event: {event}")
        for queue in self._subscribers:
            await queue.put(event)


event_bus = EventBus()
