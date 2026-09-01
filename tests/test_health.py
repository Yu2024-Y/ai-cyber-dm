"""S1-11 基础单元测试：/health 健康检查端点。"""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health() -> None:
    """访问 /health 应返回 200 与 status=ok。"""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
