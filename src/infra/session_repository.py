"""会话与消息数据访问层（CRUD，S2-4 扩展）。"""
from sqlalchemy.orm import Session as DbSession

from src.infra.models import Message
from src.infra.models import Session as SessionModel


def create_session(db: DbSession, name: str, scene: str = "赛博朋克") -> SessionModel:
    """新建会话。"""
    session = SessionModel(name=name, scene=scene)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DbSession, session_id: int) -> SessionModel | None:
    """按 ID 查询会话。"""
    return db.get(SessionModel, session_id)


def list_sessions(db: DbSession) -> list[SessionModel]:
    """列出全部会话。"""
    return db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()


def save_message(db: DbSession, session_id: int, role: str, content: str) -> Message:
    """保存一条对话消息。"""
    msg = Message(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def list_messages(
    db: DbSession, session_id: int, *, limit: int = 50
) -> list[Message]:
    """查询会话历史消息（按时间正序）。"""
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .all()
    )
