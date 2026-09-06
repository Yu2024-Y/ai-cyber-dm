"""FastAPI 应用入口。

分层约定：
  src/api       路由层
  src/services  业务服务层（DM 引擎 / 骰子检定 / 生图 / TTS）
  src/domain    Pydantic 数据契约
  src/infra     数据持久化与外部 API 适配
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router as api_router
from src.config import get_settings
from src.infra.database import init_db
from src.services import image_worker

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动后台生图 worker；关闭时取消任务。"""
    worker = asyncio.create_task(image_worker.run())
    try:
        yield
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass


# 首次启动自动建表
init_db()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI 赛博 DM 与无限跑团引擎：LLM 主持 + 骰子检定 + 场景图 + 语音播报",
    lifespan=lifespan,
)

app.include_router(api_router)

# 前端静态资源（S2-7）
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    """前端 MVP 页面。"""
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    """健康检查端点：CI 与部署探活使用。"""
    return {"status": "ok"}
