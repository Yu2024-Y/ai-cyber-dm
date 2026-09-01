"""数据库连接与会话管理（SQLite + SQLAlchemy）。

首次启动时调用 init_db() 自动建表。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite 多线程访问需要
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：为请求提供一个数据库会话，用完自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """首次启动自动建表。"""
    from src.infra import models  # noqa: F401  确保模型注册到 Base.metadata
    Base.metadata.create_all(bind=engine)
