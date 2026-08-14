import asyncio
import base64
import logging
import os
import wave
from dataclasses import dataclass
from io import BytesIO

import edge_tts
from google import genai


VOICES = {
    "en-PK": "en-PK-AsadNeural",
    "ur-PK": "ur-PK-UzmaNeural",
}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpeechAudio:
    content: bytes
    content_type: str


async def _stream_speech(text: str, language: str) -> bytes:
    communicate = edge_tts.Communicate(text, VOICES[language])
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
    if not audio:
        raise RuntimeError("The speech service returned no audio.")
    return bytes(audio)


def _pcm_to_wav(pcm: bytes) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(pcm)
    return output.getvalue()


def _synthesize_with_gemini(text: str, language: str) -> SpeechAudio:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured on the server.")

    locale = "Pakistani Urdu" if language == "ur-PK" else "Pakistani English"
    prompt = (
        f"Read the following text aloud naturally in {locale}. "
        "Do not translate, paraphrase, add, or omit any words.\n\n"
        f"Transcript:\n{text}"
    )
    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview"),
        input=prompt,
        response_format={"type": "audio"},
        generation_config={
            "speech_config": [
                {"voice": os.getenv("GEMINI_TTS_VOICE", "Sulafat")},
            ]
        },
    )
    encoded_audio = interaction.output_audio.data
    pcm = base64.b64decode(encoded_audio) if isinstance(encoded_audio, str) else bytes(encoded_audio)
    if not pcm:
        raise RuntimeError("Gemini returned no speech audio.")
    return SpeechAudio(content=_pcm_to_wav(pcm), content_type="audio/wav")


def synthesize_speech(text: str, language: str) -> SpeechAudio:
    try:
        audio = asyncio.run(_stream_speech(text, language))
        return SpeechAudio(content=audio, content_type="audio/mpeg")
    except Exception:
        logger.warning("Edge TTS failed; falling back to Gemini TTS", exc_info=True)
        return _synthesize_with_gemini(text, language)
