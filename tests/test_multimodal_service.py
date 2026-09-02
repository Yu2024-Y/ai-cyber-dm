"""S2-5 多模态集成服务单测（mock TTS/生图）。"""
import os

from src.services import multimodal_service


def test_on_story_reply_triggers_both(monkeypatch, tmp_path) -> None:
    """剧情回复触发语音 + 生图。"""
    audio_path = str(tmp_path / "story.mp3")

    monkeypatch.setattr(multimodal_service.tts_service, "synthesize",
                        lambda text, voice=None: b"\xff\xf3mp3audio")
    monkeypatch.setattr(multimodal_service.image_service, "generate_image",
                        lambda prompt, size="1024x1024": "https://example.com/scene.png")

    result = multimodal_service.on_story_reply(
        "你推开门，霓虹灯闪烁。", audio_path=audio_path
    )

    assert result["audio"] == audio_path
    assert os.path.exists(audio_path)  # 音频已保存
    assert result["image_url"] == "https://example.com/scene.png"


def test_uses_custom_scene_prompt(monkeypatch, tmp_path) -> None:
    """指定场景 prompt 时使用自定义值。"""
    captured = {}

    monkeypatch.setattr(multimodal_service.tts_service, "synthesize",
                        lambda text, voice=None: b"audio")
    monkeypatch.setattr(
        multimodal_service.image_service, "generate_image",
        lambda prompt, size="1024x1024": captured.update(prompt=prompt) or "url",
    )

    multimodal_service.on_story_reply(
        "剧情", scene_prompt="dark alley", audio_path=str(tmp_path / "a.mp3")
    )
    assert captured["prompt"] == "dark alley"
