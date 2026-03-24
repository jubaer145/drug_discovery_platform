from typing import Dict
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[job_id] = websocket

    def disconnect(self, job_id: str) -> None:
        self.active_connections.pop(job_id, None)

    async def send_progress(self, job_id: str, message: dict) -> None:
        ws = self.active_connections.get(job_id)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, message: dict) -> None:
        for ws in self.active_connections.values():
            await ws.send_json(message)


manager = WebSocketManager()
