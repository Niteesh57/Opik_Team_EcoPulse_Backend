from fastapi import WebSocket, WebSocketDisconnect, APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional
import uuid
import json
from datetime import datetime
from app.dependencies import get_current_active_user
from app.models.user import User as UserModel
from app.database import SessionLocal
from jose import JWTError, jwt
from app.core.config import settings


router = APIRouter(prefix="/voice", tags=["voice"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        print(f"New connection to room {room_id}")

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)

    async def broadcast(self, data: bytes, room_id: str, sender: WebSocket):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                if connection != sender:
                    await connection.send_bytes(data)

manager = ConnectionManager()

@router.websocket("/ws/{room_id}/{language_code}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, language_code: str):
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_bytes()
            await manager.broadcast(data, room_id, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)