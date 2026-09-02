"""S2-1 DM 引擎单测（mock LLM 服务）。"""
import pytest

from src.services import dm_engine


class FakeSession:
    """测试用会话对象。"""

    scene = "赛博朋克"
    summary = "玩家已进入废弃工厂，手持铁剑。"


def test_build_context_includes_scene_and_input() -> None:
    """组装的消息包含系统提示、场景、历史与玩家输入。"""
    session = FakeSession()
    history = [{"role": "user", "content": "我检查门"}]
    messages = dm_engine.build_context(session, history, "我推开门")

    assert messages[0]["role"] == "system"
    assert any("当前场景" in m["content"] for m in messages)
    assert messages[-1] == {"role": "user", "content": "我推开门"}
    assert len(messages) == 4  # 系统 + 场景 + 历史 + 玩家输入


def test_empty_input_raises() -> None:
    """空输入被拦截。"""
    session = FakeSession()
    with pytest.raises(dm_engine.InputError):
        list(dm_engine.generate_stream(session, [], "   "))


def test_too_long_input_raises() -> None:
    """超长输入被拦截。"""
    session = FakeSession()
    with pytest.raises(dm_engine.InputError):
        list(dm_engine.generate_stream(session, [], "x" * 501))


def test_generate_stream_yields_text(monkeypatch) -> None:
    """流式生成逐段返回剧情。"""
    session = FakeSession()
    monkeypatch.setattr(
        dm_engine.llm_service, "chat_stream",
        lambda messages, max_tokens=800: iter(["你", "推", "开", "了", "门"]),
    )
    chunks = list(dm_engine.generate_stream(session, [], "我推开门"))
    assert "".join(chunks) == "你推开了门"


def test_generate_returns_full_text(monkeypatch) -> None:
    """非流式生成返回完整剧情。"""
    session = FakeSession()
    monkeypatch.setattr(
        dm_engine.llm_service, "chat",
        lambda messages, max_tokens=800: "你推开了门，灰尘簌簌落下。",
    )
    result = dm_engine.generate(session, [], "我推开门")
    assert result == "你推开了门，灰尘簌簌落下。"
