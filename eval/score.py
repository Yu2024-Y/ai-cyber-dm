"""eval 评测评分脚本：检查回复对期望关键词的覆盖。

用法：
    1. 准备评测集 eval/evalset.json
    2. 提供回复（真实 LLM 或测试用）→ 计算覆盖率

评分逻辑：每个用例的回复需覆盖全部 expected 关键词才算通过。
"""
import json
from pathlib import Path
from typing import Any


def load_evalset(path: str | Path = "eval/evalset.json") -> list[dict[str, Any]]:
    """加载评测数据集。"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_coverage(reply: str, expected: list[str]) -> bool:
    """回复是否覆盖全部期望关键词。"""
    return all(keyword in reply for keyword in expected)


def score_replies(replies: dict[int, str], cases: list[dict[str, Any]]) -> dict[str, Any]:
    """对回复集合评分。

    参数：
        replies: {case_id: 回复文本}
        cases: 评测集（含 id/expected）
    返回：统计结果 {total, passed, rate, details}
    """
    passed = 0
    details = []
    for case in cases:
        reply = replies.get(case["id"], "")
        ok = check_coverage(reply, case["expected"])
        passed += int(ok)
        details.append({"id": case["id"], "passed": ok, "reply": reply[:50]})
    return {
        "total": len(cases),
        "passed": passed,
        "rate": round(passed / len(cases), 2) if cases else 0,
        "details": details,
    }
