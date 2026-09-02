"""S2-2 骰子检定服务单测。"""
import pytest

from src.services import dice_service


def test_roll_valid_formula() -> None:
    """合法公式能掷出数值。"""
    result = dice_service.roll("1d20+3")
    assert 4 <= result <= 23  # 1~20 + 3


def test_roll_plain_formula() -> None:
    """无修正的公式。"""
    result = dice_service.roll("2d6")
    assert 2 <= result <= 12


def test_roll_negative_modifier() -> None:
    """负修正。"""
    result = dice_service.roll("1d20-1")
    assert 0 <= result <= 19


def test_roll_invalid_formula() -> None:
    """无效公式抛异常。"""
    with pytest.raises(dice_service.DiceError):
        dice_service.roll("abc")
    with pytest.raises(dice_service.DiceError):
        dice_service.roll("1d")


def test_perform_check_success(monkeypatch) -> None:
    """结果达到 DC 判定成功。"""
    monkeypatch.setattr(dice_service.random, "randint", lambda lo, hi: 17)
    dc = dice_service.perform_check("1d20+2", 15, reason="力量检定")
    assert dc.success is True
    assert dc.result == 19  # 17 + 2
    assert dc.difficulty == 15
    assert dc.reason == "力量检定"


def test_perform_check_failure(monkeypatch) -> None:
    """结果低于 DC 判定失败。"""
    monkeypatch.setattr(dice_service.random, "randint", lambda lo, hi: 8)
    dc = dice_service.perform_check("1d20", 15)
    assert dc.success is False
    assert dc.result == 8


def test_parse_llm_output_valid() -> None:
    """合法 JSON 能解析为 DiceRoll。"""
    dc = dice_service.parse_llm_output(
        '{"formula": "1d20+3", "result": 17, "difficulty": 15, '
        '"success": true, "reason": "力量检定"}'
    )
    assert dc.formula == "1d20+3"
    assert dc.result == 17
    assert dc.success is True


def test_parse_llm_output_invalid() -> None:
    """非法 JSON / 字段缺失抛 DiceError（供重试）。"""
    with pytest.raises(dice_service.DiceError):
        dice_service.parse_llm_output("这不是 JSON")
    with pytest.raises(dice_service.DiceError):
        dice_service.parse_llm_output('{"formula": "1d20"}')  # 缺必填字段
