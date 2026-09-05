"""API 频控与指数退避重试（S3-4）。

- RateLimiter：滑动窗口限流（超限异步等待）
- retry_with_backoff：指数退避重试异步调用
"""
import asyncio
import time
from collections import deque


class RateLimiter:
    """滑动窗口限流器。

    用法：
        limiter = RateLimiter(max_calls=2, window_seconds=60)
        async with limiter:
            await do_call()
    """

    def __init__(self, *, max_calls: int = 2, window_seconds: int = 60):
        self._max = max_calls
        self._window = window_seconds
        self._timestamps: deque[float] = deque()

    async def acquire(self) -> None:
        """获取调用许可；超限时等待窗口释放。"""
        while True:
            now = time.monotonic()
            while self._timestamps and self._timestamps[0] <= now - self._window:
                self._timestamps.popleft()
            if len(self._timestamps) < self._max:
                self._timestamps.append(now)
                return
            await asyncio.sleep(0.5)

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(self, *exc) -> None:
        return None


async def retry_with_backoff(fn, *, max_retries: int = 3, base_delay: float = 1.0):
    """指数退避重试异步调用。

    用法：
        result = await retry_with_backoff(lambda: do_api_call())
    """
    delay = base_delay
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except Exception:
            if attempt >= max_retries:
                raise
            await asyncio.sleep(delay * (2**attempt))
