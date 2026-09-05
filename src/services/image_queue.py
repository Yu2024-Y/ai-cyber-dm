"""异步生图队列：限流 + 指数退避重试 + 状态机（S3-2）。

任务状态演进：
  PENDING → RUNNING → VALIDATING → SUCCESS
                            ↓
                          FAILED（重试耗尽 → 调用方降级占位图）
"""
import asyncio
from dataclasses import dataclass


@dataclass
class ImageTask:
    """生图任务数据。"""

    task_id: int
    prompt: str
    status: str = "PENDING"
    image_url: str = ""
    attempts: int = 0
    error: str = ""


class ImageQueue:
    """进程内异步生图队列（限流 + 重试）。"""

    def __init__(self, *, rate_per_minute: int = 2, max_retries: int = 3):
        self._rate = rate_per_minute
        self._max_retries = max_retries
        self._tasks: dict[int, ImageTask] = {}
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._next_id = 1
        self._sem = asyncio.Semaphore(rate_per_minute)

    def submit(self, prompt: str) -> int:
        """提交生图任务，返回 task_id。"""
        task = ImageTask(self._next_id, prompt)
        self._tasks[task.task_id] = task
        self._next_id += 1
        self._queue.put_nowait(task.task_id)
        return task.task_id

    def query(self, task_id: int) -> ImageTask | None:
        """查询任务状态。"""
        return self._tasks.get(task_id)

    async def process_all(self, image_fn):
        """处理队列中所有任务（限流 + 重试）。

        image_fn：异步生图函数 async (prompt: str) -> str。
        """
        while not self._queue.empty():
            task_id = await self._queue.get()
            await self._process_one(task_id, image_fn)

    async def _process_one(self, task_id: int, image_fn):
        task = self._tasks[task_id]
        async with self._sem:
            task.status = "RUNNING"
            try:
                url = await image_fn(task.prompt)
                task.image_url = url
                task.status = "SUCCESS"
            except Exception as e:  # noqa: BLE001  生图失败进入重试
                task.error = str(e)
                task.attempts += 1
                if task.attempts >= self._max_retries:
                    task.status = "FAILED"
                else:
                    task.status = "PENDING"
                    await asyncio.sleep(2 ** task.attempts)  # 指数退避
                    self._queue.put_nowait(task_id)
