"""S1-5 数据层单测：自动建表 + 会话 CRUD。"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infra import models  # noqa: F401  确保模型注册
from src.infra.database import Base
from src.infra.session_repository import create_session, get_session, list_sessions

# 使用内存 SQLite 测试，不影响真实数据库文件
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db():
    """每个测试独立建表/清空。"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_create_and_get_session(db) -> None:
    """新建会话后可按 ID 查询。"""
    s = create_session(db, "赛博酒馆")
    assert s.id is not None
    assert s.name == "赛博酒馆"

    fetched = get_session(db, s.id)
    assert fetched is not None
    assert fetched.name == "赛博酒馆"
    assert fetched.status == "active"


def test_get_missing_session(db) -> None:
    """查询不存在的会话返回 None。"""
    assert get_session(db, 999) is None


def test_list_sessions(db) -> None:
    """能列出全部会话。"""
    create_session(db, "会话一")
    create_session(db, "会话二", scene="奇幻")
    sessions = list_sessions(db)
    assert len(sessions) == 2
    scenes = {s.scene for s in sessions}
    assert scenes == {"赛博朋克", "奇幻"}
