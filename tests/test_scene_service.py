"""场景卡服务单测：Prompt 构造 + 同会话去重/冷却 + 任务快照。"""
from src.services.image_queue import ImageQueue
from src.services.scene_service import SceneCards, build_image_prompt


def test_build_image_prompt_embeds_story() -> None:
    """Prompt 包含赛博风格词、场景与剧情文本。"""
    prompt = build_image_prompt("赛博酒馆", "你推开酒馆的门，霓虹灯闪烁。")
    assert "cyberpunk" in prompt
    assert "赛博酒馆" in prompt
    assert "霓虹灯闪烁" in prompt
    assert len(prompt) > 20


def test_ensure_dedups_running_task() -> None:
    """任务进行中时再次触发 → 复用同一 task_id，不重复排队。"""
    cards = SceneCards(queue=ImageQueue())
    t1 = cards.ensure(1, "街道", "你走进一条小巷。")
    t2 = cards.ensure(1, "街道", "你走进一条小巷。")
    assert t1 == t2


def test_ensure_reuses_recent_completed() -> None:
    """最近完成的任务未超冷却 → 复用（避免频繁生图打满限流）。"""
    cards = SceneCards(queue=ImageQueue())
    t1 = cards.ensure(1, "街道", "你环顾四周。")
    cards.queue.query(t1).status = "SUCCESS"  # 模拟已完成
    t2 = cards.ensure(1, "街道", "你环顾四周。")
    assert t1 == t2


def test_ensure_force_creates_new() -> None:
    """force=True（手动再画一张）→ 无视冷却新建任务。"""
    cards = SceneCards(queue=ImageQueue())
    t1 = cards.ensure(1, "街道", "你环顾四周。", force=True)
    t2 = cards.ensure(1, "街道", "你环顾四周。", force=True)
    assert t2 > t1


def test_task_snapshot_fields() -> None:
    """task() 返回供前端轮询的状态快照。"""
    cards = SceneCards(queue=ImageQueue())
    t1 = cards.ensure(1, "酒馆", "酒保看了你一眼。")
    snap = cards.task(t1)
    assert snap is not None
    assert snap["task_id"] == t1
    assert snap["status"] in ("PENDING", "RUNNING", "SUCCESS", "FAILED")
    assert "image_url" in snap
    assert cards.task(99999) is None
