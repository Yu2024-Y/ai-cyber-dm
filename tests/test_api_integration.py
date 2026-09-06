"""API 集成测试：真实走 HTTP 路由（TestClient + 内存 SQLite）。

覆盖：角色目录 / 战役创建与加入 / 占位冲突 / 掷骰落库 /
      SSE 流式对话（mock 模型）/ 模型异常时的本地兜底。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.infra import models  # noqa: F401  确保模型注册
from src.infra.database import Base, get_db
from src.main import app
from src.services import dm_engine


@pytest.fixture()
def client():
    """为每个测试提供独立的内存库 + TestClient。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _new_game(client, name: str = "试炼") -> int:
    resp = client.post("/api/games", json={"name": name})
    assert resp.status_code == 200
    return resp.json()["game"]["id"]


def test_roles_endpoint(client) -> None:
    """角色目录可拉取且角色数足够团队使用。"""
    resp = client.get("/api/roles")
    assert resp.status_code == 200
    roles = resp.json()["roles"]
    assert len(roles) >= 6
    keys = [r["key"] for r in roles]
    assert len(keys) == len(set(keys))


def test_create_join_and_occupy(client) -> None:
    """新建战役 → 双角色加入 → 重复占用 409 → 成员名单正确。"""
    gid = _new_game(client, "夜雾")
    # 刀锋先加入
    r = client.post(f"/api/games/{gid}/join", json={"role_key": "blade"})
    assert r.status_code == 200
    assert r.json()["player"]["name"] == "刀锋"
    # 同一角色重复加入 → 409
    dup = client.post(f"/api/games/{gid}/join", json={"role_key": "blade"})
    assert dup.status_code == 409
    # 幽灵再加入成功
    assert client.post(f"/api/games/{gid}/join", json={"role_key": "ghost"}).status_code == 200
    # 未知角色 400；成员名单 2 人
    assert client.post(f"/api/games/{gid}/join", json={"role_key": "nobody"}).status_code == 400
    players = client.get(f"/api/games/{gid}/players").json()["players"]
    assert {p["name"] for p in players} == {"刀锋", "幽灵"}
    # 大厅列表包含该战役
    names = [g["name"] for g in client.get("/api/games").json()["games"]]
    assert "夜雾" in names


def test_unknown_game_404(client) -> None:
    """不存在的战役访问返回 404。"""
    assert client.get("/api/games/999").status_code == 404
    assert client.post("/api/games/999/join", json={"role_key": "blade"}).status_code == 404


def test_roll_records_and_broadcast(client) -> None:
    """掷骰返回真实判定、写入消息（可被队友轮询到）。"""
    gid = _new_game(client)
    client.post(f"/api/games/{gid}/join", json={"role_key": "blade"})
    r = client.post(
        f"/api/games/{gid}/roll",
        json={"player_name": "刀锋", "formula": "1d20", "difficulty": 8, "nonce": "r-1"},
    )
    assert r.status_code == 200
    dice = r.json()["dice"]
    assert 1 <= dice["result"] <= 20
    assert dice["success"] == (dice["result"] >= 8)
    # 掷骰作为行动消息落库
    msgs = client.get(f"/api/games/{gid}/messages?after_id=0").json()["messages"]
    assert len(msgs) == 1
    assert msgs[0]["player"] == "刀锋"
    assert "🎲" in msgs[0]["content"]


def test_roll_bad_input(client) -> None:
    """非法公式 / 越界难度返回 400。"""
    gid = _new_game(client)
    client.post(f"/api/games/{gid}/join", json={"role_key": "ghost"})
    assert client.post(
        f"/api/games/{gid}/roll", json={"player_name": "幽灵", "formula": "abc", "difficulty": 8}
    ).status_code == 400
    assert client.post(
        f"/api/games/{gid}/roll", json={"player_name": "幽灵", "formula": "1d20", "difficulty": 99}
    ).status_code == 400


def test_chat_stream_with_mock_model(client, monkeypatch) -> None:
    """对话路由 SSE 流式（mock 模型），并落库 user+assistant。"""
    gid = _new_game(client)
    client.post(f"/api/games/{gid}/join", json={"role_key": "ghost"})

    monkeypatch.setattr(
        dm_engine.llm_service,
        "chat_stream",
        lambda messages, max_tokens=900: iter(["你", "推", "开", "了", "门"]),
    )
    resp = client.post(
        f"/api/games/{gid}/chat",
        json={"content": "我推开门", "player_name": "幽灵", "nonce": "c-1"},
    )
    assert resp.status_code == 200
    assert resp.text == "你推开了门"
    msgs = client.get(f"/api/games/{gid}/messages?after_id=0").json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["player"] == "幽灵"
    assert msgs[1]["content"] == "你推开了门"


def test_chat_resolve_after_roll(client, monkeypatch) -> None:
    """掷骰后 resolve=True 自动结算（不再追加新的用户行动）。"""
    gid = _new_game(client)
    client.post(f"/api/games/{gid}/join", json={"role_key": "ghost"})

    roll = client.post(
        f"/api/games/{gid}/roll",
        json={"player_name": "幽灵", "formula": "1d20", "difficulty": 12, "nonce": "r-1"},
    )
    assert roll.status_code == 200

    captured = {}

    def fake_chat(messages, max_tokens=900):  # noqa: ARG001
        captured["last_user"] = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        return iter(["结算：", "你通过了检定。"])

    monkeypatch.setattr(dm_engine.llm_service, "chat_stream", fake_chat)
    resp = client.post(
        f"/api/games/{gid}/chat",
        json={"content": "", "player_name": "幽灵", "nonce": "c-1", "resolve": True},
    )
    assert resp.status_code == 200
    assert resp.text == "结算：你通过了检定。"
    # 结算输入取自骰子消息（🎲），且未新增第二条用户行动
    assert "🎲" in captured["last_user"]
    msgs = client.get(f"/api/games/{gid}/messages?after_id=0").json()["messages"]
    user_msgs = [m for m in msgs if m["role"] == "user"]
    assert len(user_msgs) == 1  # 只有掷骰那一条用户消息
    assert msgs[-1]["role"] == "assistant"


def test_chat_resolve_without_roll_400(client, monkeypatch) -> None:
    """还没掷骰就请求结算 → 400。"""
    gid = _new_game(client)
    client.post(f"/api/games/{gid}/join", json={"role_key": "blade"})
    resp = client.post(
        f"/api/games/{gid}/chat",
        json={"content": "", "player_name": "刀锋", "nonce": "c-2", "resolve": True},
    )
    assert resp.status_code == 400


def test_chat_fallback_when_model_fails(client, monkeypatch) -> None:
    """模型异常时返回本地兜底剧情，对话不中断。"""
    gid = _new_game(client)
    client.post(f"/api/games/{gid}/join", json={"role_key": "blade"})

    def broken(messages, max_tokens=900):  # noqa: ARG001
        raise RuntimeError("network down")

    monkeypatch.setattr(dm_engine.llm_service, "chat_stream", broken)
    resp = client.post(
        f"/api/games/{gid}/chat",
        json={"content": "我四下张望", "player_name": "刀锋", "nonce": "c-2"},
    )
    assert resp.status_code == 200
    assert "雨陡然大了" in resp.text  # 兜底剧情出现
    msgs = client.get(f"/api/games/{gid}/messages?after_id=0").json()["messages"]
    assert msgs[-1]["role"] == "assistant"
    assert "雨陡然大了" in msgs[-1]["content"]
