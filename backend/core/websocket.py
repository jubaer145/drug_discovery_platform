import asyncio
import json
import logging
from datetime import datetime, timezone

import redis
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections with Redis pubsub for cross-process updates."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)

    def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        conns = self.active_connections.get(job_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(job_id, None)

    async def send_progress(self, job_id: str, message: dict) -> None:
        """Send progress update to all connected clients for a job."""
        conns = self.active_connections.get(job_id, [])
        dead = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.remove(ws)
        if not conns:
            self.active_connections.pop(job_id, None)

    async def broadcast_to_job(self, job_id: str, data: dict) -> None:
        """Alias for send_progress."""
        await self.send_progress(job_id, data)


manager = ConnectionManager()


def send_progress_update(
    job_id: str,
    step: str,
    progress_pct: int,
    message: str,
    status: str = "running",
    completed_steps: list[str] | None = None,
    pending_steps: list[str] | None = None,
) -> None:
    """Publish a progress update to Redis pubsub (called from Celery tasks).

    This function is synchronous and safe to call from Celery workers.
    The WebSocket handler subscribes to the Redis channel and forwards messages.
    """
    from core.config import settings

    progress = {
        "job_id": job_id,
        "status": status,
        "step": step,
        "progress_pct": min(progress_pct, 100),
        "message": message,
        "completed_steps": completed_steps or [],
        "current_step": step,
        "pending_steps": pending_steps or [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        r = redis.Redis.from_url(settings.redis_url)
        r.publish(f"job_progress:{job_id}", json.dumps(progress))
        # Also store latest progress for late-joining clients
        r.set(f"job_progress_latest:{job_id}", json.dumps(progress), ex=3600)
    except Exception as e:
        logger.warning(f"Could not publish progress for {job_id}: {e}")


async def subscribe_to_job_progress(job_id: str, websocket: WebSocket) -> None:
    """Subscribe to Redis pubsub for a job and forward messages to the WebSocket.

    This runs as an asyncio task alongside the WebSocket connection.
    """
    import redis.asyncio as aioredis
    from core.config import settings

    try:
        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"job_progress:{job_id}")

        # Send latest cached progress for late-joining clients
        latest = await r.get(f"job_progress_latest:{job_id}")
        if latest:
            try:
                await websocket.send_json(json.loads(latest))
            except Exception:
                return

        async for msg in pubsub.listen():
            if msg["type"] == "message":
                data = json.loads(msg["data"])
                try:
                    await websocket.send_json(data)
                except Exception:
                    break
                # Close when job completes
                if data.get("status") in ("completed", "failed", "cancelled"):
                    break

        await pubsub.unsubscribe(f"job_progress:{job_id}")
        await r.aclose()
    except Exception as e:
        logger.warning(f"Redis pubsub error for {job_id}: {e}")
