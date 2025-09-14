import json
from typing import Dict, List

from fastapi import WebSocket
from sqlalchemy import JSON


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, document_id: str):
        await websocket.accept()
        conns = self.active_connections.setdefault(document_id, [])
        conns.append(websocket)

    async def disconnect(self, websocket: WebSocket, document_id: str):
        conns = self.active_connections.get(document_id)
        if not conns:
            del self.active_connections[document_id]
            return
        try:
            conns.remove(websocket)
        except ValueError:
            print(f"WebSocket {websocket} not found in connections for document {document_id}")
            return

    async def broadcast(
        self, document_id: str, message: dict, exclude: WebSocket | None = None
    ):
        # No active connections for this document
        if document_id not in self.active_connections:
            return
        # Converting message dict to JSON string
        text = json.dumps(message)
        # Getting active connections for this document
        conns = self.active_connections[document_id]
        for connection in conns:
            if connection != exclude:
                try:
                    await connection.send_text(text)
                except Exception as e:
                    print(f"Error sending message to {connection}: {e}")
                    await self.disconnect(document_id, connection)


manager = ConnectionManager()