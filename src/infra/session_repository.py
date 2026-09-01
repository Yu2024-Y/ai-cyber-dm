"""会话数据访问层（CRUD）。"""
from sqlalchemy.orm import Session as DbSession

from src.infra.models import Session as SessionModel


def create_session(db: DbSession, name: str, scene: str = "赛博朋克") -> SessionModel:
    """新建会话并提交。"""
    session = SessionModel(name=name, scene=scene)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DbSession, session_id: int) -> SessionModel | None:
    """按 ID 查询会话，不存在返回 None。"""
    return db.get(SessionModel, session_id)


def list_sessions(db: DbSession) -> list[SessionModel]:
    """列出全部会话，按创建时间倒序。"""
    return db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()
