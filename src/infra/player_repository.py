"""战役玩家数据访问层（谁加入了这局、用的哪个角色）。"""
from sqlalchemy.orm import Session as DbSession

from src.infra.models import Player


def add_player(
    db: DbSession,
    session_id: int,
    *,
    role_key: str,
    name: str,
    color: str,
) -> Player:
    """登记一名玩家加入战役。"""
    player = Player(
        session_id=session_id, role_key=role_key, name=name, color=color
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def list_players(db: DbSession, session_id: int) -> list[Player]:
    """列出战役内的全部玩家（按加入先后）。"""
    return (
        db.query(Player)
        .filter(Player.session_id == session_id)
        .order_by(Player.created_at.asc(), Player.id.asc())
        .all()
    )


def player_count(db: DbSession, session_id: int) -> int:
    """战役内玩家数。"""
    return (
        db.query(Player).filter(Player.session_id == session_id).count()
    )


def name_taken(db: DbSession, session_id: int, name: str) -> bool:
    """该角色名是否已被本战役的其他玩家占用。"""
    return (
        db.query(Player)
        .filter(Player.session_id == session_id, Player.name == name)
        .first()
        is not None
    )
