"""S3-2 异步生图队列单测（mock 生图函数）。"""
import pytest

from src.services.image_queue import ImageQueue


@pytest.mark.asyncio
async def test_submit_creates_task() -> None:
    """提交任务返回 task_id，初始 PENDING。"""
    q = ImageQueue()
    tid = q.submit("cyberpunk street")
    assert tid == 1
    assert q.query(tid).status == "PENDING"


@pytest.mark.asyncio
async def test_process_success() -> None:
    """生图成功 → SUCCESS + URL。"""
    q = ImageQueue()

    async def fake_image(prompt: str) -> str:
        return "https://example.com/scene.png"

    tid = q.submit("cyberpunk street")
    await q.process_all(fake_image)
    task = q.query(tid)
    assert task.status == "SUCCESS"
    assert task.image_url == "https://example.com/scene.png"


@pytest.mark.asyncio
async def test_retry_then_success() -> None:
    """失败一次后重试成功。"""
    q = ImageQueue(max_retries=3)
    calls = []

    async def flaky_image(prompt: str) -> str:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("network error")
        return "https://example.com/retry.png"

    tid = q.submit("scene")
    await q.process_all(flaky_image)
    task = q.query(tid)
    assert task.status == "SUCCESS"
    assert len(calls) == 2  # 失败1次 + 成功1次


@pytest.mark.asyncio
async def test_fail_after_retries() -> None:
    """重试耗尽 → FAILED（供调用方降级占位图）。"""
    q = ImageQueue(max_retries=2)
    calls = []

    async def always_fail(prompt: str) -> str:
        calls.append(1)
        raise RuntimeError("boom")

    tid = q.submit("scene")
    await q.process_all(always_fail)
    task = q.query(tid)
    assert task.status == "FAILED"
    assert len(calls) >= 2  # 达到重试上限
