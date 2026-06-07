import json
import logging
import asyncio
from fastapi import WebSocket
from redis.asyncio import from_url
from app.core.config import settings

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

async def redis_pubsub_listener():
    """Background task to listen to Redis and broadcast updates to all connected sockets."""
    try:
        async_redis = from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = async_redis.pubsub()
        await pubsub.subscribe("ticket_updates")
        logger.info("Started Redis Pub/Sub WebSocket listener")
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    payload = json.loads(message["data"])
                    await manager.broadcast(payload)
            except Exception as e:
                logger.error(f"Error in Redis Pub/Sub listener loop: {e}", exc_info=True)
                await asyncio.sleep(1)
            await asyncio.sleep(0.01)
    except Exception as e:
        logger.error(f"Failed to initialize Redis Pub/Sub listener: {e}", exc_info=True)
