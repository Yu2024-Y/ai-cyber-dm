"""FastAPI 应用入口（Sprint 1）。

分层约定：
  src/api       路由层
  src/services  业务服务层（DM 引擎 / 骰子检定 / 生图 / TTS）
  src/domain    Pydantic 数据契约
  src/infra     数据持久化与外部 API 适配
"""
from fastapi import FastAPI

from src.config import get_settings
from src.infra.database import init_db

settings = get_settings()

# 首次启动自动建表（S1-5）
init_db()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI 赛博 DM 与无限跑团引擎：LLM 主持 + 骰子检定 + 场景图 + 语音播报",
)


@app.get("/health")
def health() -> dict:
    """健康检查端点：CI 与部署探活使用。"""
    return {"status": "ok"}
