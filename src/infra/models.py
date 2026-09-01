"""SQLAlchemy 数据模型。"""
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.database import Base


class Session(Base):
    """跑团会话表。"""

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
