"""
OkChat — WebSocket Connection Manager
Manages active WebSocket connections keyed by session_id.
Redis Pub/Sub is used as the backplane so that messages from
any API pod reach the correct connection regardless of which
pod the client is connected to.
"""
import asyncio
import json
from typing import Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from okchat.core.logging import get_logger

logger = get_logger(__name__)

PUBSUB_CHANNEL_PREFIX = "okchat:ws:"


class ConnectionManager:
    """
    Manages active WebSocket connections.

    Architecture:
    - Local dict maps session_id → WebSocket for direct sends.
    - Redis Pub/Sub channel per session for cross-pod delivery.
    - On message received via Redis, find local WS and deliver.
    """

    def __init__(self, redis: Redis) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._redis = redis
        self._pubsub_tasks: dict[str, asyncio.Task[None]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self._connections[session_id] = websocket
        logger.info("ws.connected", session_id=session_id)

        # Start listening to Redis channel for cross-pod messages
        task = asyncio.create_task(
            self._listen_redis(session_id),
            name=f"ws_redis_listener_{session_id}",
        )
        self._pubsub_tasks[session_id] = task

    async def disconnect(self, session_id: str) -> None:
        """Clean up connection and cancel Redis listener."""
        self._connections.pop(session_id, None)

        if task := self._pubsub_tasks.pop(session_id, None):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        logger.info("ws.disconnected", session_id=session_id)

    async def send_to_session(self, session_id: str, data: dict[str, Any]) -> None:
        """
        Send data to a specific session.
        First tries local delivery, then Redis Pub/Sub for cross-pod.
        """
        if websocket := self._connections.get(session_id):
            try:
                await websocket.send_json(data)
                return
            except Exception as exc:
                logger.warning("ws.local_send_failed", session_id=session_id, error=str(exc))

        # Publish to Redis so another pod can deliver it
        await self._redis.publish(
            f"{PUBSUB_CHANNEL_PREFIX}{session_id}",
            json.dumps(data),
        )

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Send to all locally connected sessions (single pod)."""
        dead: list[str] = []
        for session_id, ws in self._connections.items():
            try:
                await ws.send_json(data)
            except WebSocketDisconnect:
                dead.append(session_id)

        for session_id in dead:
            await self.disconnect(session_id)

    async def _listen_redis(self, session_id: str) -> None:
        """Background task: listen to Redis Pub/Sub and deliver to local WS."""
        pubsub = self._redis.pubsub()
        channel = f"{PUBSUB_CHANNEL_PREFIX}{session_id}"
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                if websocket := self._connections.get(session_id):
                    try:
                        data = json.loads(message["data"])
                        await websocket.send_json(data)
                    except Exception as exc:
                        logger.warning(
                            "ws.redis_deliver_failed",
                            session_id=session_id,
                            error=str(exc),
                        )
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    @property
    def active_connections_count(self) -> int:
        return len(self._connections)
