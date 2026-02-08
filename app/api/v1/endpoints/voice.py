from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio
from datetime import datetime
from app.core.config import settings
import os
from elevenlabs.client import ElevenLabs
from app.ai.voice import transcribe_audio, translate_text
from app.ai.opik import track_agent_call, create_span_context, PerformanceMonitor

# Initialize ElevenLabs
# Best practice: Use an environment variable for your API key
ELEVEN_CLIENT = ElevenLabs(api_key=settings.ELEVEN_API_KEY)
# Choose a voice ID (e.g., "JBFqnCBsd6RMkjVDRZzb" for George)
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"

router = APIRouter(prefix="/voice", tags=["voice"])

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}
        self.languages: Dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket, room_id: str, language: str):
        await ws.accept()
        self.rooms.setdefault(room_id, []).append(ws)
        self.languages[ws] = language
        print(f"✅ Connected to room {room_id} ({language})")

    def disconnect(self, ws: WebSocket, room_id: str):
        if room_id in self.rooms:
            if ws in self.rooms[room_id]:
                self.rooms[room_id].remove(ws)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        if ws in self.languages:
            del self.languages[ws]

    async def broadcast_bytes(self, room_id: str, data: bytes, sender: WebSocket = None):
        """Broadcasts audio bytes (WebM from users or MP3 from ElevenLabs)"""
        for ws in self.rooms.get(room_id, []):
            if ws != sender:
                await ws.send_bytes(data)

    async def broadcast_text(self, room_id: str, payload: dict):
        for ws in self.rooms.get(room_id, []):
            await ws.send_text(json.dumps(payload))

    async def broadcast_same_language(self, room_id: str, data: bytes, sender: WebSocket, language: str):
        """Broadcasts audio bytes only to users speaking the same language"""
        for ws in self.rooms.get(room_id, []):
            if ws != sender:
                user_lang = self.languages.get(ws)
                if user_lang == language:
                    await ws.send_bytes(data)

manager = ConnectionManager()


@track_agent_call(agent_name="Voice TTS", agent_type="audio", tags={"provider": "elevenlabs"})
async def generate_speech_bytes(text: str) -> bytes:
    """Converts text to speech and returns the audio bytes."""
    start_time = datetime.now()
    try:
        with create_span_context(
            name="Voice TTS Generation",
            span_type="audio",
            metadata={"text_length": len(text)}
        ):
            # Generate audio using the low-latency Turbo model
            audio_stream = ELEVEN_CLIENT.text_to_speech.convert(
                text=text,
                voice_id=DEFAULT_VOICE_ID,
                model_id="eleven_turbo_v2_5",
                output_format="mp3_44100_128"
            )
            # Collect the stream into bytes
            audio_bytes = b"".join([chunk for chunk in audio_stream if chunk])
            
            PerformanceMonitor.record_latency(
                operation="voice_tts",
                latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                success=True,
                metadata={
                   "text_length": len(text),
                   "audio_bytes": len(audio_bytes)
                },
            )
            return audio_bytes
    except Exception as e:
        print(f"ElevenLabs Error: {e}")
        PerformanceMonitor.record_latency(
            operation="voice_tts",
            latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
            success=False,
            metadata={"error": str(e)},
        )
        return b""

async def transcribe_and_broadcast(webm_bytes: bytes, room_id: str, source_language: str):
    text = await transcribe_audio(webm_bytes, source_language)

    if text:
        print("📝", text)
        
        # Group users by language to optimize translation and TTS calls
        users_by_lang = {}
        room_users = manager.rooms.get(room_id, [])
        for ws in room_users:
            lang = manager.languages.get(ws, "en") # Default to 'en'
            users_by_lang.setdefault(lang, []).append(ws)

        for target_lang, users in users_by_lang.items():
            # 1. Translate text if needed
            if target_lang != source_language:
                final_text = await translate_text(text, source_language, target_lang)
            else:
                final_text = text
            
            # 2. Send text payload
            payload = {
                "type": "text",
                "text": final_text,
                "language": target_lang,
                "lang_code": target_lang
            }
            json_payload = json.dumps(payload)
            for ws in users:
                try:
                    await ws.send_text(json_payload)
                except Exception as e:
                    print(f"Error sending text to user: {e}")

            # 3. Generate and send audio (personalized TTS)
            # Only generate if we have a valid text AND it is a translation (different language)
            # Users with the same language already heard the original audio.
            if final_text and target_lang != source_language:
                audio_bytes = await generate_speech_bytes(final_text)
                if audio_bytes:
                    for ws in users:
                        try:
                            # We send raw audio bytes. 
                            # The client must distinguish between original user audio and TTS audio 
                            # if they are both sent as binary messages.
                            # Usually clients handle this, or we might need a protocol wrapper.
                            # For this codebase, it seems raw bytes are treated as audio to play.
                            await ws.send_bytes(audio_bytes)
                        except Exception as e:
                            print(f"Error sending audio to user: {e}")

@router.websocket("/ws/{room_id}/{language}")
async def voice_ws(websocket: WebSocket, room_id: str, language: str):
    await manager.connect(websocket, room_id, language)
    try:
        while True:
            webm_bytes = await websocket.receive_bytes()

            if not webm_bytes or len(webm_bytes) < 1000:
                continue

            # Broadcast original user audio only to users with the same language
            await manager.broadcast_same_language(room_id, webm_bytes, sender=websocket, language=language)

            # Process transcription and TTS in the background
            asyncio.create_task(transcribe_and_broadcast(webm_bytes, room_id, language))

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        print("❌ Disconnected")
    except Exception as e:
        manager.disconnect(websocket, room_id)
        print("WS error:", e)