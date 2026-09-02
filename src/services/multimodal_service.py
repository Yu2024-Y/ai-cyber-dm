"""多模态集成服务：剧情回复触发语音与场景图（S2-5）。

- 语音：DM 剧情文本 → edge-tts 合成 mp3 并保存
- 生图：生成场景图（MVP 用默认场景模板，S3 完善异步队列）
"""
from pathlib import Path

from src.services import image_service, tts_service

DEFAULT_SCENE_PROMPT = "cyberpunk city street at night, neon lights, moody atmosphere"
MAX_TTS_CHARS = 200


def on_story_reply(
    story_text: str,
    *,
    scene_prompt: str | None = None,
    audio_path: str = "assets/story.mp3",
) -> dict:
    """剧情回复后触发多模态：合成语音 + 生成场景图。

    返回 {"audio": 音频文件路径, "image_url": 场景图URL}。
    """
    result = {}

    # ① 语音（edge-tts 免费）；确保保存目录存在
    audio_path = Path(audio_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio = tts_service.synthesize(story_text[:MAX_TTS_CHARS])
    audio_path.write_bytes(audio)
    result["audio"] = str(audio_path)

    # ② 生图（MVP 用默认场景模板；异步队列在 S3 完善）
    prompt = scene_prompt or DEFAULT_SCENE_PROMPT
    result["image_url"] = image_service.generate_image(prompt)
    return result
