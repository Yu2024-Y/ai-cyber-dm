"""DM 引擎：多轮对话组装 + 剧情生成（S2-1 核心）。

- build_context：组装系统提示、场景、历史消息、玩家输入
- generate_stream：流式生成剧情回复（SSE 用）
- generate：非流式生成（测试/降级用）
- 输入校验：空输入 / 超长输入拦截
"""
from src.services import llm_service

SYSTEM_PROMPT = """你是"AI 赛博 DM"——赛博朋克世界观的跑团主持人。
职责：
1. 根据玩家输入推进剧情，保持世界观一致
2. 对玩家的行动给出生动、沉浸的剧情回应，使用第二人称叙述
3. 玩家可以任意行动，你需要合理判定结果并推进故事
4. 玩家提到"检定/掷骰"时，说明进行的检定并给出结果
保持神秘感和戏剧性，不要跳出主持人的角色。"""

MAX_INPUT_LEN = 500
MAX_HISTORY = 10


class InputError(ValueError):
    """玩家输入校验错误。"""


def build_context(session, history: list[dict], user_input: str) -> list[dict]:
    """组装发送给 LLM 的消息列表。

    参数：
        session：会话对象，需有 scene 属性
        history：历史消息 [{"role": "user"|"assistant", "content": "..."}]
        user_input：玩家本次输入
    返回：OpenAI 格式消息列表
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "system", "content": f"当前场景：{session.scene}"})
    messages.extend(history[-MAX_HISTORY:])
    messages.append({"role": "user", "content": user_input})
    return messages


def _validate(user_input: str) -> None:
    """输入校验：空输入 / 超长输入拦截。"""
    if not user_input or not user_input.strip():
        raise InputError("输入不能为空")
    if len(user_input) > MAX_INPUT_LEN:
        raise InputError(f"输入过长（超过 {MAX_INPUT_LEN} 字）")


def generate_stream(session, history: list[dict], user_input: str, *, max_tokens: int = 800):
    """流式生成剧情回复（SSE 用），逐段 yield 文本。

    校验失败抛 InputError。
    """
    _validate(user_input)
    messages = build_context(session, history, user_input)
    yield from llm_service.chat_stream(messages, max_tokens=max_tokens)


def generate(session, history: list[dict], user_input: str, *, max_tokens: int = 800) -> str:
    """非流式生成剧情回复（测试与降级用）。"""
    _validate(user_input)
    messages = build_context(session, history, user_input)
    return llm_service.chat(messages, max_tokens=max_tokens)
