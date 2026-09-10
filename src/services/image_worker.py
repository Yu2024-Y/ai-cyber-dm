"""后台生图 worker：消费场景卡队列，滑动窗口限流 + 指数退避已隔离。

启动方式：FastAPI lifespan 里 `asyncio.create_task(image_worker.run())`。

image_fn 在独立线程中执行阻塞的 generate_image，避免卡住事件循环。
"""
import asyncio

from src.services import image_service, image_store, scene_service


async def _generate(prompt: str) -> str:
    """限流放行后在线程池中调用生图 API，并把结果本地化存储。"""
    async with scene_service.limiter:
        url = await asyncio.to_thread(image_service.generate_image, prompt)
    # 下载到本地（失败时回退原链），避免第三方临时链接过期
    return await asyncio.to_thread(image_store.save_remote_image, url, key=prompt)


async def run() -> None:
    """持续消费队列（限流等待 + 空闲轮询）。"""
    while True:
        await scene_service.scene_cards.queue.process_all(_generate)
        await asyncio.sleep(0.5)
