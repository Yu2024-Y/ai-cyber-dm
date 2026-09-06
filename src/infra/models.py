"""SQLAlchemy 数据模型：会话、消息、骰子检定记录、战役玩家。"""
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.database import Base


class Session(Base):
    """跑团会话表（一局游戏/战役）。"""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scene: Mapped[str] = mapped_column(String(255), default="赛博朋克")
    summary: Mapped[str] = mapped_column(String(2000), default="")
    turn: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="session")
    players: Mapped[list["Player"]] = relationship(back_populates="session")


class Message(Base):
    """会话消息表（历史对话）。

    player：发送者（user 为该玩家角色名，assistant 为空表示 DM）
    nonce：客户端生成的请求标识，用于多端去重/区分"自己发的"
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    player: Mapped[str] = mapped_column(String(50), default="")
    nonce: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    session: Mapped["Session"] = relationship(back_populates="messages")


class Player(Base):
    """战役玩家（谁加入了这局、用的哪个预设角色）。"""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    role_key: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(50))
    color: Mapped[str] = mapped_column(String(20), default="#58a6ff")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    session: Mapped["Session"] = relationship(back_populates="players")


class DiceRoll(Base):
    """骰子检定记录表。"""

    __tablename__ = "dice_rolls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    formula: Mapped[str] = mapped_column(String(50))
    result: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[int] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
