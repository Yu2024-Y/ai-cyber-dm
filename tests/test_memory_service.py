"""S2-3 上下文记忆服务单测。"""
from src.services import memory_service


def test_trim_keeps_recent() -> None:
    """滑动窗口保留最近 N 轮。"""
    history = [{"role": "user", "content": f"消息{i}"} for i in range(15)]
    result = memory_service.trim(history, max_window=10)
    assert len(result) == 10
    assert result[-1]["content"] == "消息14"


def test_compress_extracts_key_points() -> None:
    """摘要提取玩家关键内容。"""
    history = [
        {"role": "user", "content": "我捡起铁剑"},
        {"role": "assistant", "content": "你获得铁剑"},
        {"role": "user", "content": "我走进工厂"},
    ]
    summary = memory_service.compress(history)
    assert "铁剑" in summary
    assert "工厂" in summary
    assert "剧情要点" in summary


def test_manage_within_window() -> None:
    """历史未超限时无摘要。"""
    history = [{"role": "user", "content": f"消息{i}"} for i in range(10)]
    window, summary = memory_service.manage(history)
    assert len(window) == 10
    assert summary == ""


def test_manage_exceeds_window() -> None:
    """历史超限时生成摘要并保留窗口。"""
    history = [{"role": "user", "content": f"消息{i}"} for i in range(40)]
    window, summary = memory_service.manage(history)
    assert len(window) == 10
    assert summary != ""
    assert "消息" in summary
