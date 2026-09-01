"""TTS 服务封装：edge-tts 合成中文语音（微软免费接口，无需 API Key）。

依赖配置（config.py）：
  tts_voice
"""
import asyncio

import edge_tts

from src.config import get_settings

settings = get_settings()


def synthesize(text: str, *, voice: str | None = None) -> bytes:
    """合成语音，返回 mp3 音频字节。

    在异步应用中使用时，请改用 await synthesize_async()。
    """
    voice = voice or settings.tts_voice
    return asyncio.run(_synthesize_async(text, voice))


async def synthesize_async(text: str, *, voice: str | None = None) -> bytes:
    """异步合成语音，返回 mp3 音频字节（推荐在 FastAPI 中使用）。"""
    voice = voice or settings.tts_voice
    return await _synthesize_async(text, voice)


async def _synthesize_async(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
    return bytes(audio)
