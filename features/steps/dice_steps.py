"""骰子检定 BDD 步骤定义。"""
from behave import given, step, then, when

from src.services import dice_service


@given('玩家进行检定 "{formula}" 对抗难度 {dc:d}')
def step_given_check(context, formula, dc):
    context.formula = formula
    context.dc = dc


@when("掷骰完成")
def step_when_roll(context):
    context.result = dice_service.perform_check(context.formula, context.dc)


@when("系统校验公式")
def step_when_validate(context):
    try:
        dice_service.roll(context.formula)
        context.error = None
    except dice_service.DiceError as e:
        context.error = e


@then("系统返回结构化的检定结果")
def step_then_result(context):
    assert context.result is not None
    assert context.result.formula == context.formula


@then("结果包含公式、数值、难度与成败")
def step_then_fields(context):
    r = context.result
    assert r.formula
    assert isinstance(r.result, int)
    assert isinstance(r.difficulty, int)
    assert r.success in (True, False)


@step("抛出无效公式错误")
def step_then_error(context):
    assert context.error is not None


@then("判定结果为失败")
def step_then_failure(context):
    assert context.result.success is False
