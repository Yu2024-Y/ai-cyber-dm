"""场景卡服务（US06 集成）：会话级生图状态 + 触发生成编排。

职责：
  - ensure：根据最近剧情触发生成场景图（同会话去重 + 冷却，保护限流）
  - task：按 task_id 查询任务状态快照（供前端轮询）
  - limiter：进程级滑动窗口限流（与后台 worker 共用）

生图失败无需额外处理：任务最终为 FAILED，由前端降级展示占位图。
"""
import time

from src.config import get_settings
from src.services.image_queue import ImageQueue
from src.services.rate_limiter import RateLimiter

settings = get_settings()

_STYLE = "cyberpunk cinematic scene, neon-lit, highly detailed digital art"
MIN_INTERVAL_SEC = 20  # 同一会话两次生图的最小间隔（秒）


def build_image_prompt(scene: str, story_text: str, *, max_len: int = 80) -> str:
    """由场景与剧情文本构造英文生图 Prompt（固定赛博风格词打底）。

    Qwen-Image 对英文 Prompt 效果更佳；故事细节截断拼接即可。
    """
    text = " ".join(story_text.split())[:max_len]
    scene_part = f"scene: {scene or 'cyberpunk city'}"
    story_part = f"story: {text}" if text else "story: a mysterious night"
    return f"{_STYLE}, {scene_part}; {story_part}"


class SceneCards:
    """会话场景图状态机（内存版 MVP，重启后由对话重新触发生成）。"""

    def __init__(
        self,
        *,
        queue: ImageQueue | None = None,
        min_interval: float = MIN_INTERVAL_SEC,
    ):
        self._queue = queue or ImageQueue(
            rate_per_minute=settings.image_rate_limit_per_minute
        )
        self._min_interval = min_interval
        # session_id → (最近任务 task_id, 触发时间戳)
        self._cards: dict[int, tuple[int, float]] = {}

    @property
    def queue(self) -> ImageQueue:
        """底层生图队列（供后台 worker 处理）。"""
        return self._queue

    def ensure(
        self,
        session_id: int,
        scene: str,
        story_text: str,
        *,
        force: bool = False,
    ) -> int:
        """触发生成场景图，返回应轮询的 task_id。

        去重规则（保护限流 2 次/分）：
          - 有任务进行中 → 复用该任务
          - 最近任务完成未超冷却 → 复用（前端直接展示已有图）
          - force=True（手动"再画一张"）→ 无视冷却立即新建
        """
        record = self._cards.get(session_id)
        if record is not None and not force:
            task_id, triggered_at = record
            task = self._queue.query(task_id)
            if task is not None:
                if task.status in ("PENDING", "RUNNING"):
                    return task_id  # 进行中：不重复排队
                if time.time() - triggered_at < self._min_interval:
                    return task_id  # 冷却期：直接复用已有结果
        task_id = self._queue.submit(build_image_prompt(scene, story_text))
        self._cards[session_id] = (task_id, time.time())
        return task_id

    def task(self, task_id: int) -> dict | None:
        """查询任务状态快照（前端轮询用）。"""
        task = self._queue.query(task_id)
        if task is None:
            return None
        return {
            "task_id": task.task_id,
            "status": task.status,
            "image_url": task.image_url,
            "error": task.error,
            "attempts": task.attempts,
        }


# 进程级共享实例：路由（触发/查询）与后台 worker（消费）共用
scene_cards = SceneCards()

# 滑动窗口限流：严格按免费额度 2 次/分放行外部生图调用
limiter = RateLimiter(
    max_calls=settings.image_rate_limit_per_minute, window_seconds=60
)
