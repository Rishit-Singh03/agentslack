import asyncio

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class ConnectionManager:
    def __init__(self):
        self.connections: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def connect(self, socket: WebSocket):
        await socket.accept()
        self.connections.add(socket)

    def disconnect(self, socket: WebSocket):
        self.connections.discard(socket)

    async def broadcast(self, event_type: str, data):
        async with self.lock:
            for socket in tuple(self.connections):
                try:
                    await socket.send_json({"type": event_type, "data": jsonable_encoder(data)})
                except Exception:
                    self.disconnect(socket)


manager = ConnectionManager()
