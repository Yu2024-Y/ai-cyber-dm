"""上下文记忆服务：滑动窗口 + 摘要压缩（S2-3 核心）。

- trim：滑动窗口，只保留最近 N 轮对话
- compress：把早期对话压缩为剧情摘要
- manage：统一管理，返回（窗口内消息，压缩摘要）
"""
MAX_WINDOW = 10  # 保留最近 10 轮
MAX_HISTORY_LEN = 30  # 超过 30 轮触发摘要压缩
MAX_SUMMARY_ITEMS = 5  # 摘要最多提取的关键点数量


def trim(history: list[dict], *, max_window: int = MAX_WINDOW) -> list[dict]:
    """滑动窗口：只保留最近 max_window 轮对话。"""
    return history[-max_window:]


def compress(history: list[dict]) -> str:
    """把早期对话压缩为一句剧情摘要。

    MVP 采用规则摘要：提取玩家（user）关键内容拼接；
    后续可升级为 LLM 摘要。
    """
    if not history:
        return ""
    key_points = [m["content"][:50] for m in history if m.get("role") == "user"]
    summary = "；".join(key_points[-MAX_SUMMARY_ITEMS:])
    return f"剧情要点：{summary}"


def manage(
    history: list[dict],
    *,
    max_window: int = MAX_WINDOW,
    max_history: int = MAX_HISTORY_LEN,
) -> tuple[list[dict], str]:
    """管理上下文：返回（窗口内消息，压缩摘要）。

    - 历史未超限：只返回窗口内消息，无摘要
    - 历史超限：早期消息压缩为摘要，窗口保留最近部分
    """
    if len(history) <= max_history:
        return trim(history, max_window=max_window), ""
    older = history[:-max_window]
    summary = compress(older)
    return trim(history, max_window=max_window), summary
