"""会话与消息数据访问层（CRUD，S2-4 扩展）。"""
from datetime import UTC, datetime

from sqlalchemy.orm import Session as DbSession

from src.infra.models import DiceRoll, Message
from src.infra.models import Session as SessionModel


def create_session(db: DbSession, name: str, scene: str = "赛博朋克") -> SessionModel:
    """新建会话（一局游戏/战役）。"""
    session = SessionModel(name=name, scene=scene)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DbSession, session_id: int) -> SessionModel | None:
    """按 ID 查询会话。"""
    return db.get(SessionModel, session_id)


def list_sessions(db: DbSession) -> list[SessionModel]:
    """列出全部会话（新的在前）。"""
    return db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()


def save_message(
    db: DbSession,
    session_id: int,
    role: str,
    content: str,
    *,
    player: str = "",
    nonce: str = "",
) -> Message:
    """保存一条对话消息。

    player：user 为该玩家角色名，assistant 留空表示 DM
    nonce：客户端请求标识（多端去重/区分"自己发的"）
    """
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        player=player,
        nonce=nonce,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def list_messages(
    db: DbSession, session_id: int, *, limit: int | None = None
) -> list[Message]:
    """查询会话历史消息（按时间正序）。"""
    query = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def list_messages_after(db: DbSession, session_id: int, after_id: int) -> list[Message]:
    """查询 id>after_id 的消息（增量轮询用）。"""
    return (
        db.query(Message)
        .filter(Message.session_id == session_id, Message.id > after_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )


def save_dice_roll(
    db: DbSession,
    session_id: int,
    *,
    formula: str,
    result: int,
    difficulty: int,
    success: bool,
    reason: str = "",
) -> DiceRoll:
    """保存一次骰子检定记录（S2-4 持久化）。"""
    roll = DiceRoll(
        session_id=session_id,
        formula=formula,
        result=result,
        difficulty=difficulty,
        success=success,
        reason=reason,
    )
    db.add(roll)
    db.commit()
    db.refresh(roll)
    return roll


def last_activity_at(db: DbSession, session_id: int) -> datetime:
    """会话最近活动时间（取最后一条消息创建时间，无则用纪元起点）。"""
    last = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .first()
    )
    return last.created_at if last else datetime(1970, 1, 1, tzinfo=UTC)
