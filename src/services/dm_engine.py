"""DM 引擎：多轮对话组装 + 剧情生成（S2-1 核心，主持人质量增强）。

思路（基于现有架构增强，非重写）：
- 系统人设 = 一份完整"主持人操作框架"（节奏 / 一致性 / 检定 / 失败推进 / 埋钩子）
- 每轮注入"状态栏"：当前场景 + 队伍名单 + 当前局面（最新一段剧情的精炼回放）
- 长局：超过窗口的早期剧情折叠为"早期剧情摘要"，保证跨轮不遗忘
- 检定：DM 明确被告知——最近有 🎲 结果时必须照结果叙事，不得忽略或另掷

- build_context：组装系统提示/状态栏/摘要/历史/玩家输入
- generate_stream：流式生成剧情回复（SSE 用）
- generate：非流式生成（测试/降级用）
- 输入校验：空输入 / 超长输入拦截
"""
from src.services import llm_service

SYSTEM_PROMPT = (
    "你是一名资深 TRPG 主持人（Game Master），风格是电影感、克制而冷峻的赛博朋克 noir。"
    "目标是让小队感觉『活在一个会自己转动的世界里』。\n\n"
    "【主持原则】\n"
    "1. 忠于事实：严格以状态栏的当前场景、当前局面、队伍名单与早期剧情摘要为准；"
    "不遗忘、不推翻已发生的人和事。\n"
    "2. 接住行动：先回应当前行动玩家（对 ta 用第二人称），同时让队友处境可见——"
    "他们在哪、听到什么，点名邀请他们参与，别演独角戏。\n"
    "3. 该判定就判定：明显成败点提示玩家用骰子面板检定并给难度直觉；"
    "若上下文最近一次掷骰已有 🎲 结果（→ 成功/失败），必须严格按它叙述后果，"
    "不许忽略、不许另掷。\n"
    "4. 失败也要推进：检定失败不是剧情卡死，而是代价式后果——受伤/暴露/时间被拖住/"
    "失去机会但换来一条新线索。\n"
    "5. 世界要有钩子：每轮结尾埋一条可行动的线索或选择（悬念、倒计时、可疑 NPC、"
    "一扇可撬的门），让玩家知道下一步能做什么。\n"
    "6. 具体可感：环境用细节（气味/灯光/雨声/义体嗡鸣）而非形容词堆砌；"
    "NPC 一两笔画像即可；整体 2~5 句，紧凑有画面，别写论文。\n"
    "7. 边界：你只描述世界、NPC 与判定后果，永远不替玩家决定行动、不代他们说话。\n"
    "8. 语言：全程中文，第二人称称呼当前行动玩家，其他人用角色名。\n"
    "9. 基调：赛博朋克近未来——霓虹、雨、义体、企业与底层的张力；"
    "可轻度超现实，但不出现奇幻魔法设定。\n"
    "10. 高亮：只在关键名词/地点/数字/人名上用一对 ** 括起（例如 **夜莺**、**3号泵房**、"
    "**DC 14**），其余文本一律不附加任何符号。\n"
    "11. 检定门控：\n"
    "  - 玩家做了明显需要成败判定的行动、而该行动还没有对应的 🎲 结果时：不要替他判定结果，"
    "也不要往下推进剧情。结尾明确给出\"需要哪种检定 + 难度\"，并请他去掷骰（🎲 面板或回复"
    "『掷骰 d20 难度X』），保持悬念等他掷。\n"
    "  - 若你刚要求检定、他却送来另一件行动而没掷：提醒他先完成刚才的检定，仍不推进。\n"
    "  - 当收到对该掷骰的结算请求或新的 🎲 结果消息时：立即按结果结算之前那个行动并继续推进，"
    "成败严格照 🎲。\n"
    "  - 若他在明显不需要检定的日常行动上掷了骰：不要无视也不要小题大做——成功给一点小亮点，"
    "失败只造成小口误/小尴尬，并轻描淡写提醒这种动作其实不必掷。\n"
    "  - 若出现 🎲 结果却看不出它在检验哪个行动：反问一句这检定是为哪件事而掷，或结合最近剧情"
    "氛围给个轻结果。"
)

# 终章指令：到达幕数上限或玩家手动结束时注入，要求收束本局
FINALE_INSTRUCTION = (
    "【终章】本局已到收尾时刻：请用一段完整叙事给出结局——"
    "交代主线悬念的收束、每位玩家角色的去向与代价，并留一个有余味的尾声；"
    "不要再抛出新的钩子或新任务，不要再询问玩家下一步。"
)

MAX_INPUT_LEN = 500
MAX_HISTORY = 18  # 保留最近的完整消息条数
_OLD_DIGEST_ASSISTANT_CAP = 5  # 早期摘要最多折叠的 DM 剧情条数
_OLD_DIGEST_CHARS = 60
_STATUS_LAST_CHARS = 220


class InputError(ValueError):
    """玩家输入校验错误。"""


def _clip(text: str, n: int) -> str:
    """压空白并按长度截断。"""
    text = " ".join(text.split())
    if len(text) <= n:
        return text
    return text[:n] + "…"


def _build_status(session, history: list[dict], roster: list[str] | None) -> str:
    """构建每轮注入的"状态栏"（当前场景 + 队伍 + 当前局面）。"""
    roster_txt = "、".join(roster) if roster else "暂无"
    parts = [f"当前场景：{session.scene or '赛博朋克'}", f"队伍成员：{roster_txt}"]
    recent_dm = next(
        (m for m in reversed(history) if m.get("role") == "assistant"), None
    )
    if recent_dm:
        parts.append("当前局面：" + _clip(recent_dm["content"], _STATUS_LAST_CHARS))
    else:
        parts.append("当前局面：故事刚开始，小队刚集结，正在夜色中等第一个委托。")
    return "；".join(parts)


def _early_digest(old_history: list[dict]) -> str:
    """把窗口外的早期 DM 剧情折叠成短摘要（保证长局一致性）。"""
    beats = [m for m in old_history if m.get("role") == "assistant"]
    if not beats:
        beats = old_history[-3:]
    lines = [
        f"· {_clip(m.get('content', ''), _OLD_DIGEST_CHARS)}"
        for m in beats[:_OLD_DIGEST_ASSISTANT_CAP]
    ]
    return "早期剧情摘要：\n" + "\n".join(lines)


def build_context(
    session,
    history: list[dict],
    user_input: str,
    *,
    player_name: str = "冒险者",
    roster: list[str] | None = None,
    finale: bool = False,
) -> list[dict]:
    """组装发送给 LLM 的消息列表。

    参数：
        session：会话对象，需有 scene 属性
        history：历史消息 [{"role": "user"|"assistant", "content": "..."}]
        user_input：玩家本次输入
        player_name：当前行动玩家名（多玩家支持）
        roster：当前战役玩家名单（增强队伍感）
        finale：是否为终章（收束剧情、给出结局）
    返回：OpenAI 格式消息列表
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append(
        {"role": "system", "content": _build_status(session, history, roster)}
    )
    if finale:
        messages.append({"role": "system", "content": FINALE_INSTRUCTION})
    if len(history) > MAX_HISTORY:
        messages.append(
            {"role": "system", "content": _early_digest(history[:-MAX_HISTORY])}
        )
    messages.extend(history[-MAX_HISTORY:])
    # 标注当前行动玩家（多玩家叙事）
    messages.append({"role": "user", "content": f"[{player_name}的行动] {user_input}"})
    return messages


def _validate(user_input: str) -> None:
    """输入校验：空输入 / 超长输入拦截。"""
    if not user_input or not user_input.strip():
        raise InputError("输入不能为空")
    if len(user_input) > MAX_INPUT_LEN:
        raise InputError(f"输入过长（超过 {MAX_INPUT_LEN} 字）")


def generate_stream(
    session,
    history: list[dict],
    user_input: str,
    *,
    player_name: str = "冒险者",
    roster: list[str] | None = None,
    finale: bool = False,
    max_tokens: int = 900,
):
    """流式生成剧情回复（SSE 用），逐段 yield 文本。

    校验失败抛 InputError。
    """
    _validate(user_input)
    messages = build_context(
        session,
        history,
        user_input,
        player_name=player_name,
        roster=roster,
        finale=finale,
    )
    yield from llm_service.chat_stream(messages, max_tokens=max_tokens)


def generate(
    session,
    history: list[dict],
    user_input: str,
    *,
    player_name: str = "冒险者",
    roster: list[str] | None = None,
    finale: bool = False,
    max_tokens: int = 900,
) -> str:
    """非流式生成剧情回复（测试与降级用）。"""
    _validate(user_input)
    messages = build_context(
        session,
        history,
        user_input,
        player_name=player_name,
        roster=roster,
        finale=finale,
    )
    return llm_service.chat(messages, max_tokens=max_tokens)
