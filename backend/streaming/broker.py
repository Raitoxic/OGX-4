from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Set


class SSEBroker:
    """In-process per-task Server-Sent Events pub/sub broker (thread-safe across sync & async routes)."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._event_counter: int = 0
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, task_id: str) -> asyncio.Queue:
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers[task_id].add(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        subs = self._subscribers.get(task_id)
        if subs and queue in subs:
            subs.discard(queue)
            if not subs:
                self._subscribers.pop(task_id, None)

    def _enqueue_on_loop(self, task_id: str, queue: asyncio.Queue, envelope: Dict[str, Any]) -> None:
        try:
            queue.put_nowait(envelope)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
                queue.put_nowait(envelope)
            except Exception:
                self.unsubscribe(task_id, queue)

    def publish(self, task_id: str, event_type: str, data: Dict[str, Any]) -> None:
        subs = self._subscribers.get(task_id)
        if not subs:
            return
        self._event_counter += 1
        envelope = {
            "id": str(self._event_counter),
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "emitted_at_ms": int(time.time() * 1000),
            "task_id": task_id,
            "data": data,
        }
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        for queue in list(subs):
            if self._loop and self._loop.is_running() and current_loop is not self._loop:
                self._loop.call_soon_threadsafe(self._enqueue_on_loop, task_id, queue, envelope)
            else:
                self._enqueue_on_loop(task_id, queue, envelope)

    async def stream(
        self,
        task_id: str,
        initial_payload: Dict[str, Any],
        heartbeat_seconds: float = 15.0,
    ) -> AsyncGenerator[str, None]:
        queue = self.subscribe(task_id)
        try:
            # Immediately sync current persisted task snapshot on connect/reconnect
            init_data = json.dumps(initial_payload, default=str)
            yield f"event: task_snapshot\ndata: {init_data}\n\n"

            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=heartbeat_seconds)
                    payload_str = json.dumps(msg, default=str)
                    yield f"id: {msg['id']}\nevent: {msg['event']}\ndata: {payload_str}\n\n"
                except asyncio.TimeoutError:
                    heartbeat = json.dumps(
                        {"timestamp": datetime.now(timezone.utc).isoformat(), "task_id": task_id}
                    )
                    yield f"event: heartbeat\ndata: {heartbeat}\n\n"
        finally:
            self.unsubscribe(task_id, queue)


sse_broker = SSEBroker()
