"""S3-4 频控与重试单测。"""
import pytest

from src.services.rate_limiter import RateLimiter, retry_with_backoff


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit() -> None:
    """窗口内未超限时直接放行。"""
    limiter = RateLimiter(max_calls=3, window_seconds=60)
    for _ in range(3):
        await limiter.acquire()  # 不应阻塞


@pytest.mark.asyncio
async def test_retry_succeeds_after_failure() -> None:
    """失败后重试成功。"""
    calls = []

    async def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("temp")
        return "ok"

    result = await retry_with_backoff(flaky, max_retries=3, base_delay=0.01)
    assert result == "ok"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_retry_exhausts() -> None:
    """重试耗尽后抛异常。"""
    calls = []

    async def always_fail():
        calls.append(1)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await retry_with_backoff(always_fail, max_retries=2, base_delay=0.01)
    assert len(calls) == 3  # 初始 + 2 次重试
