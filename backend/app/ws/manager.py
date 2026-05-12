"""WebSocket broadcast manager.

Single in-memory broadcaster. For multi-process scaling switch to Redis pub/sub
(replace `_publish` with redis.publish, run a per-process subscriber loop).
"""
import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger

log = get_logger(__name__)


class Broadcaster:
    def __init__(self):
        # site_id -> set of WebSockets
        self._site_subs: dict[str, set[WebSocket]] = defaultdict(set)
        self._global_subs: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def subscribe_site(self, site_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._site_subs[site_id].add(ws)

    async def subscribe_global(self, ws: WebSocket) -> None:
        async with self._lock:
            self._global_subs.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._global_subs.discard(ws)
            for s in self._site_subs.values():
                s.discard(ws)

    async def _send_safe(self, ws: WebSocket, payload: dict) -> bool:
        try:
            await ws.send_text(json.dumps(payload, default=str))
            return True
        except Exception:
            return False

    async def broadcast_reading(
        self,
        *,
        site_id: str,
        sensor_id: str,
        ts: str,
        value: float,
        quality: str,
    ) -> None:
        msg: dict[str, Any] = {
            "event": "reading",
            "site_id": site_id,
            "sensor_id": sensor_id,
            "ts": ts,
            "value": value,
            "quality": quality,
        }
        await self._fanout(site_id, msg)

    async def broadcast_alert(self, *, site_id: str, alert: dict) -> None:
        msg = {"event": "alert", "site_id": site_id, "alert": alert}
        await self._fanout(site_id, msg)

    async def _fanout(self, site_id: str, msg: dict) -> None:
        targets: list[WebSocket] = list(self._global_subs) + list(self._site_subs.get(site_id, set()))
        if not targets:
            return
        results = await asyncio.gather(
            *(self._send_safe(t, msg) for t in targets), return_exceptions=True
        )
        for ws, ok in zip(targets, results):
            if ok is False or isinstance(ok, Exception):
                await self.disconnect(ws)


broadcaster = Broadcaster()
