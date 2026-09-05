"""S3-5 结构化日志单测：JSON 格式验证。"""
import json
import logging

from src.infra.logging_setup import setup_logging


def test_logging_outputs_json(capsys) -> None:
    """日志输出为可解析的 JSON。"""
    setup_logging()
    logging.getLogger("test").info("hello world")

    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["message"] == "hello world"
    assert data["level"] == "INFO"
    assert "time" in data


def test_logging_includes_extra(capsys) -> None:
    """extra 字段（session_id 等）写入 JSON。"""
    setup_logging()
    logging.getLogger("test").info("gen", extra={"session_id": 7})

    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["session_id"] == 7
