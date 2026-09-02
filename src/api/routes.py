"""API 路由层：/api/chat（SSE 流式剧情生成）。"""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from src.infra import session_repository
from src.infra.database import get_db
from src.services import dm_engine

router = APIRouter(prefix="/api")

DbDep = Annotated[DbSession, Depends(get_db)]


class ChatRequest(BaseModel):
    """对话请求体。"""

    session_id: int
    content: str


@router.post("/chat")
def chat(req: ChatRequest, db: DbDep):
    """玩家输入 → DM 剧情生成（SSE 流式）。"""
    session = session_repository.get_session(db, req.session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"detail": "会话不存在"})

    # 历史消息：S2-4 持久化完善前，先以会话摘要作为上下文
    history = [{"role": "assistant", "content": session.summary}] if session.summary else []
    try:
        stream = dm_engine.generate_stream(session, history, req.content)
        return StreamingResponse(stream, media_type="text/event-stream")
    except dm_engine.InputError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
