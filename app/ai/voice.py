import io
from datetime import datetime

import av
import numpy as np
from groq import Groq

from app.core.config import settings
from app.ai.opik import create_span_context, PerformanceMonitor, opik_context, track_agent_call

client = Groq(api_key=settings.GROQ_API_KEY)

SAMPLE_RATE = 16000
MIN_SECONDS = 1.2
SILENCE_RMS = 0.008


def webm_to_pcm(webm: bytes) -> np.ndarray:
    buf = io.BytesIO(webm)
    container = av.open(buf)

    stream = container.streams.audio[0]
    resampler = av.audio.resampler.AudioResampler(
        format="flt",
        layout="mono",
        rate=SAMPLE_RATE
    )

    pcm = []

    for packet in container.demux(stream):
        for frame in packet.decode():
            frames = resampler.resample(frame)
            for f in frames:
                pcm.append(f.to_ndarray().reshape(-1))

    if not pcm:
        return np.array([], dtype=np.float32)

    return np.concatenate(pcm)


def is_silence(pcm: np.ndarray) -> bool:
    if pcm.size == 0:
        return True
    rms = np.sqrt(np.mean(pcm ** 2))
    return rms < SILENCE_RMS


def pcm_to_wav(pcm: np.ndarray) -> io.BytesIO:
    pcm16 = np.clip(pcm * 32768, -32768, 32767).astype(np.int16)
    pcm16 = pcm16.reshape(1, -1)

    buf = io.BytesIO()
    out = av.open(buf, "w", format="wav")

    stream = out.add_stream("pcm_s16le", rate=SAMPLE_RATE)
    stream.layout = "mono"

    frame = av.AudioFrame.from_ndarray(pcm16, layout="mono")
    frame.sample_rate = SAMPLE_RATE

    for packet in stream.encode(frame):
        out.mux(packet)
    for packet in stream.encode(None):
        out.mux(packet)   

    out.close()
    buf.seek(0)
    buf.name = "audio.wav"
    return buf
@track_agent_call(agent_name="Voice Transcription", agent_type="audio", tags={"language": "various"})
async def transcribe_audio(webm: bytes, language: str) -> str | None:
    start_time = datetime.now()

    # Create an Opik span for this transcription call so we can
    # monitor latency, audio characteristics, and failures.
    with create_span_context(
        name="Voice Transcription",
        span_type="audio",
        metadata={"language": language}
    ):
        try:
            pcm = webm_to_pcm(webm)

            duration = pcm.size / SAMPLE_RATE if pcm.size else 0.0
            silence = is_silence(pcm)

            # Record basic audio metadata on the span
            try:
                opik_context.update_current_span(
                    metadata={
                        "audio_duration_sec": duration,
                        "is_silence": silence,
                        "sample_rate": SAMPLE_RATE,
                        "raw_bytes": len(webm),
                    }
                )
            except Exception:
                pass

            if duration < MIN_SECONDS or silence:
                # Too short or silent – treat as filtered input
                PerformanceMonitor.record_latency(
                    operation="voice_transcription",
                    latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    success=True,
                    metadata={"filtered": True}
                )
                return None

            wav = pcm_to_wav(pcm)

            result = client.audio.transcriptions.create(
                file=wav,
                model="whisper-large-v3",
                language=language,
                temperature=0.0,
            )

            text = (result.text or "").strip()

            # Record successful transcription metrics
            PerformanceMonitor.record_latency(
                operation="voice_transcription",
                latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                success=True,
                metadata={
                    "transcribed": bool(text),
                    "text_length": len(text),
                },
            )

            return text if len(text) > 1 else None

        except Exception as e:
            print("Internal Transcription Error:", e)

            # Track failure in Opik so we can debug production issues
            try:
                PerformanceMonitor.record_latency(
                    operation="voice_transcription",
                    latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    success=False,
                    metadata={"error": str(e)},
                )
            except Exception:
                pass

            return None

@track_agent_call(agent_name="Voice Translation", agent_type="llm", tags={"type": "translation"})
async def translate_text(text: str, from_lang: str, to_lang: str) -> str:
    start_time = datetime.now()
    
    if from_lang == to_lang:
        return text

    with create_span_context(
        name="Voice Translation",
        span_type="llm",
        metadata={"from_lang": from_lang, "to_lang": to_lang, "input_length": len(text)}
    ):
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a professional translator. Translate the text exactly, preserving meaning. Output ONLY the translation without quotes or explanations."},
                    {"role": "user", "content": f"Translate this from {from_lang} to {to_lang}: {text}"}
                ],
                temperature=0.1
            )
            translated_text = completion.choices[0].message.content.strip()
            
            # Record successful translation metrics
            PerformanceMonitor.record_latency(
                operation="voice_translation",
                latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                success=True,
                metadata={
                    "from_lang": from_lang,
                    "to_lang": to_lang,
                    "input_length": len(text),
                    "output_length": len(translated_text)
                },
            )
            
            return translated_text
        except Exception as e:
            print(f"Translation Error: {e}")
            
            # Track failure in Opik
            try:
                PerformanceMonitor.record_latency(
                    operation="voice_translation",
                    latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    success=False,
                    metadata={"error": str(e)},
                )
            except Exception:
                pass
            
            return text
