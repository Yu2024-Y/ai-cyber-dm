"""骰子检定服务：掷骰 + 结构化判定（S2-2 核心）。

- roll：解析骰子公式（如 "1d20+3"）并掷骰
- perform_check：完整检定（掷骰 + 判定成功/失败）
- parse_llm_output：解析 LLM 返回的检定 JSON（Pydantic 强校验）
- DiceRoll：Pydantic 数据契约
"""
import json
import random
import re

from pydantic import BaseModel, ValidationError

_FORMULA_RE = re.compile(r"^(\d+)d(\d+)([+-]\d+)?$")


class DiceRoll(BaseModel):
    """骰子检定数据契约。"""

    formula: str  # 骰子公式，如 "1d20+3"
    result: int  # 掷骰结果
    difficulty: int  # 难度值 DC
    success: bool  # 是否成功
    reason: str  # 判定理由


class DiceError(ValueError):
    """无效骰子公式。"""


def roll(formula: str) -> int:
    """解析骰子公式并掷骰，返回数值。

    支持的格式：{数量}d{面数}[+/-修正]，如 "1d20+3"、"2d6"、"1d20-1"。
    """
    match = _FORMULA_RE.match(formula.strip())
    if not match:
        raise DiceError(f"无效骰子公式: {formula}")
    num, sides, mod = int(match[1]), int(match[2]), int(match[3] or 0)
    if num < 1 or sides < 2:
        raise DiceError(f"无效骰子公式: {formula}")
    total = sum(random.randint(1, sides) for _ in range(num)) + mod
    return total


def perform_check(formula: str, dc: int, *, reason: str = "") -> DiceRoll:
    """完整检定：掷骰 + 判定（结果 >= DC 为成功）。"""
    result = roll(formula)
    return DiceRoll(
        formula=formula,
        result=result,
        difficulty=dc,
        success=result >= dc,
        reason=reason,
    )


def parse_llm_output(text: str) -> DiceRoll:
    """解析 LLM 返回的检定结果 JSON，Pydantic 强校验。

    校验失败抛 DiceError，调用方应重试（指数退避，S3 完善）。
    """
    try:
        data = json.loads(text)
        return DiceRoll(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise DiceError(f"检定结果解析失败: {e}") from e
