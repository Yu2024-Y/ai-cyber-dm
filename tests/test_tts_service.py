"""S1-9 TTS 服务单测（mock edge_tts，不实际联网合成）。"""
from unittest.mock import MagicMock

from src.services import tts_service


def test_synthesize_returns_audio(monkeypatch) -> None:
    """synthesize 返回音频字节。"""
    async def fake_stream():
        yield {"type": "audio", "data": b"\xff\xf3MP3DATA"}
        yield {"type": "end"}

    fake_comm = MagicMock()
    fake_comm.stream.return_value = fake_stream()
    monkeypatch.setattr(tts_service.edge_tts, "Communicate", lambda text, voice: fake_comm)

    audio = tts_service.synthesize("你好，欢迎来到赛博世界")
    assert isinstance(audio, bytes)
    assert audio == b"\xff\xf3MP3DATA"


def test_synthesize_uses_default_voice(monkeypatch) -> None:
    """未指定 voice 时使用配置默认音色。"""
    async def fake_stream():
        yield {"type": "end"}

    fake_comm = MagicMock()
    fake_comm.stream.return_value = fake_stream()
    captured = {}
    monkeypatch.setattr(tts_service.edge_tts, "Communicate",
                        lambda text, voice: captured.update(text=text, voice=voice) or fake_comm)

    tts_service.synthesize("测试")
    assert captured["voice"] == tts_service.settings.tts_voice
    assert captured["text"] == "测试"
