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
    # 多玩家：末条标注当前行动玩家
    assert messages[-1] == {"role": "user", "content": "[冒险者的行动] 我推开门"}
    assert len(messages) == 4  # 系统 + 场景 + 历史 + 玩家输入


def test_build_context_custom_player_name() -> None:
    """指定玩家名时标注该玩家的行动。"""
    session = FakeSession()
    messages = dm_engine.build_context(
        session, [], "我观察四周", player_name="幽灵"
    )
    assert messages[-1]["content"] == "[幽灵的行动] 我观察四周"


def test_build_context_injects_roster() -> None:
    """状态栏包含队伍名单（增强队伍感）。"""
    session = FakeSession()
    messages = dm_engine.build_context(
        session, [], "有人跟上来吗", roster=["刀锋", "幽灵"]
    )
    status = messages[1]["content"]
    assert "当前场景：赛博朋克" in status
    assert "队伍成员：刀锋、幽灵" in status
    assert "当前局面" in status


def test_build_context_digests_long_history() -> None:
    """超窗长局：早期剧情折叠为摘要，同时保留最近窗口。"""
    session = FakeSession()
    long_history = []
    for i in range(30):
        role = "assistant" if i % 2 else "user"
        long_history.append({"role": role, "content": f"第{i}轮内容"})
    messages = dm_engine.build_context(session, long_history, "继续")
    digest = [m for m in messages if "早期剧情摘要" in m["content"]]
    assert digest, "长局应注入早期剧情摘要"
    # 人设 + 状态栏 + 摘要 + 最近窗口 + 行动
    assert len(messages) == dm_engine.MAX_HISTORY + 4
    # 状态栏仍存在
    assert any("当前场景" in m["content"] for m in messages)


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
