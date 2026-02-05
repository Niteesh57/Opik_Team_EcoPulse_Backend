import io
import av
import numpy as np
from groq import Groq
from app.core.config import settings

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


async def transcribe_audio(webm: bytes, language: str) -> str | None:
    try:
        pcm = webm_to_pcm(webm)

        duration = pcm.size / SAMPLE_RATE
        if duration < MIN_SECONDS or is_silence(pcm):
            return None

        wav = pcm_to_wav(pcm)

        result = client.audio.transcriptions.create(
            file=wav,
            model="whisper-large-v3",
            language=language,
            temperature=0.0,
        )

        text = result.text.strip()
        return text if len(text) > 1 else None

    except Exception as e:
        print("Internal Transcription Error:", e)
        return None
