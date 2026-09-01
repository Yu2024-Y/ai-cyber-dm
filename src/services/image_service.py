"""生图服务封装：调用 Qwen/Qwen-Image（SiliconFlow，OpenAI 兼容接口）。

依赖配置（config.py）：
  siliconflow_api_key / siliconflow_base_url / image_model
"""
from openai import OpenAI

from src.config import get_settings

settings = get_settings()

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """懒加载 OpenAI 客户端（生图耗时较长，超时放宽到 120s）。"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.siliconflow_api_key,
            base_url=settings.siliconflow_base_url,
            timeout=120.0,
        )
    return _client


def generate_image(prompt: str, *, size: str = "1024x1024") -> str:
    """根据英文 Prompt 生成图片，返回图片 URL。

    注意：SiliconFlow 生图对英文 Prompt 效果更好；免费额度有限流（每分钟 2 次），
    调用方应配合队列/重试使用。
    """
    if not settings.siliconflow_api_key:
        raise RuntimeError("未配置 SILICONFLOW_API_KEY（请在 .env 中设置）")

    resp = _get_client().images.generate(
        model=settings.image_model,
        prompt=prompt,
        size=size,
    )
    return resp.data[0].url
