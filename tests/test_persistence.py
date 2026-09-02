"""S2-4 会话持久化单测：消息存储与查询。"""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from src.infra import models  # noqa: F401  确保模型注册
from src.infra.database import Base
from src.infra.session_repository import (
    create_session,
    list_messages,
    save_message,
)

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_save_and_list_messages(db) -> None:
    """能保存并查询会话消息。"""
    s = create_session(db, "赛博酒馆")
    save_message(db, s.id, "user", "我推开门")
    save_message(db, s.id, "assistant", "你推开了门")

    messages = list_messages(db, s.id)
    assert len(messages) == 2
    assert messages[0].content == "我推开门"
    assert messages[1].role == "assistant"


def test_messages_isolated_per_session(db) -> None:
    """不同会话的消息互不干扰。"""
    s1 = create_session(db, "会话一")
    s2 = create_session(db, "会话二")
    save_message(db, s1.id, "user", "A")
    save_message(db, s2.id, "user", "B")

    assert len(list_messages(db, s1.id)) == 1
    assert len(list_messages(db, s2.id)) == 1


def test_tables_created(db) -> None:
    """建表包含 sessions/messages/dice_rolls。"""
    tables = inspect(engine).get_table_names()
    assert "sessions" in tables
    assert "messages" in tables
    assert "dice_rolls" in tables
