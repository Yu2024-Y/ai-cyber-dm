"""LLM 服务封装：调用 DeepSeek-V4-Flash（SiliconFlow，OpenAI 兼容接口）。

依赖配置（config.py）：
  siliconflow_api_key / siliconflow_base_url / llm_model
"""
from openai import OpenAI

from src.config import get_settings

settings = get_settings()

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """懒加载 OpenAI 客户端（带超时）。"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.siliconflow_api_key,
            base_url=settings.siliconflow_base_url,
            timeout=60.0,
        )
    return _client


def chat(messages: list[dict], *, max_tokens: int = 1000) -> str:
    """非流式调用大模型，返回完整回复文本。"""
    if not settings.siliconflow_api_key:
        raise RuntimeError("未配置 SILICONFLOW_API_KEY（请在 .env 中设置）")

    resp = _get_client().chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def chat_stream(messages: list[dict], *, max_tokens: int = 1000):
    """流式调用大模型，逐段 yield 回复文本（SSE 用）。

    用法：
        for chunk in chat_stream(messages):
            yield chunk   # 每段文本
    """
    if not settings.siliconflow_api_key:
        raise RuntimeError("未配置 SILICONFLOW_API_KEY（请在 .env 中设置）")

    resp = _get_client().chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in resp:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta
