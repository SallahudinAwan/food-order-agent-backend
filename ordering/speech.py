import asyncio

import edge_tts


VOICES = {
    "en-PK": "en-PK-AsadNeural",
    "ur-PK": "ur-PK-UzmaNeural",
}


async def _stream_speech(text: str, language: str) -> bytes:
    communicate = edge_tts.Communicate(text, VOICES[language])
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
    if not audio:
        raise RuntimeError("The speech service returned no audio.")
    return bytes(audio)


def synthesize_speech(text: str, language: str) -> bytes:
    return asyncio.run(_stream_speech(text, language))
