from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio
from app.ai.voice import transcribe_audio

router = APIRouter(prefix="/voice", tags=["voice"])


class ConnectionManager:
    def __init__(self):
        # room_id -> list of websocket connections
        self.rooms: Dict[str, List[WebSocket]] = {}
        # websocket -> preferred language code
        self.languages: Dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket, room_id: str, language: str):
        await ws.accept()
        self.rooms.setdefault(room_id, []).append(ws)
        self.languages[ws] = language
        print(f"✅ Connected to room {room_id} ({language})")

    def disconnect(self, ws: WebSocket, room_id: str):
        if room_id in self.rooms:
            self.rooms[room_id].remove(ws)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        if ws in self.languages:
            del self.languages[ws]

    async def broadcast_bytes(self, room_id: str, data: bytes, sender: WebSocket):
        for ws in self.rooms.get(room_id, []):
            if ws != sender:
                await ws.send_bytes(data)

    async def broadcast_text(self, room_id: str, payload: dict, language: str | None = None):
        """Broadcast JSON text payload to connections in a room.

        If `language` is provided, only send to connections whose
        registered language matches.
        """
        for ws in self.rooms.get(room_id, []):
            if language is not None and self.languages.get(ws) != language:
                continue
            await ws.send_text(json.dumps(payload))


manager = ConnectionManager()


# 🔥 Background transcription task
async def transcribe_and_broadcast(
    webm_bytes: bytes,
    room_id: str,
    language: str
):
    text = await transcribe_audio(webm_bytes, language)

    if text:
        print("📝", text)
        await manager.broadcast_text(
            room_id,
            {
                "type": "text",
                "text": text,
                "language": language,
            },
            language=language,
        )


@router.websocket("/ws/{room_id}/{language}")
async def voice_ws(websocket: WebSocket, room_id: str, language: str):
    await manager.connect(websocket, room_id, language)

    try:
        while True:
            # ⏱ Receive audio
            webm_bytes = await websocket.receive_bytes()

            if not webm_bytes or len(webm_bytes) < 1000:
                continue

            await manager.broadcast_bytes(
                room_id,
                webm_bytes,
                sender=websocket
            )

            asyncio.create_task(
                transcribe_and_broadcast(
                    webm_bytes,
                    room_id,
                    language
                )
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        print("❌ Disconnected")

    except Exception as e:
        manager.disconnect(websocket, room_id)
        print("WS error:", e)
