"""S1-7 LLM 服务单测（mock 外部 API，不消耗真实额度）。"""
from unittest.mock import MagicMock

import pytest

from src.services import llm_service


def _make_response(content: str) -> MagicMock:
    """构造模拟的 OpenAI 响应对象。"""
    resp = MagicMock()
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp.choices = [choice]
    return resp


def test_chat_returns_text(monkeypatch) -> None:
    """chat 返回模型回复文本。"""
    monkeypatch.setattr(llm_service.settings, "siliconflow_api_key", "sk-test")

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _make_response("欢迎来到赛博世界")
    monkeypatch.setattr(llm_service, "_get_client", lambda: fake_client)

    result = llm_service.chat([{"role": "user", "content": "你好"}])
    assert result == "欢迎来到赛博世界"
    fake_client.chat.completions.create.assert_called_once()


def test_chat_passes_arguments(monkeypatch) -> None:
    """chat 把消息与模型参数传给 OpenAI。"""
    monkeypatch.setattr(llm_service.settings, "siliconflow_api_key", "sk-test")

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _make_response("OK")
    monkeypatch.setattr(llm_service, "_get_client", lambda: fake_client)

    messages = [{"role": "user", "content": "检定力量"}]
    llm_service.chat(messages, max_tokens=500)
    fake_client.chat.completions.create.assert_called_once()
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == llm_service.settings.llm_model
    assert kwargs["max_tokens"] == 500
    assert kwargs["messages"] == messages


def test_chat_requires_key() -> None:
    """未配置 API Key 时抛出 RuntimeError。"""
    llm_service.settings.siliconflow_api_key = ""
    with pytest.raises(RuntimeError):
        llm_service.chat([{"role": "user", "content": "hi"}])
