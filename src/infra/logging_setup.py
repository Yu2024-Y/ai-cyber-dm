"""结构化日志配置（S3-5）：JSON 格式输出。

用法（应用启动时）：
    from src.infra.logging_setup import setup_logging
    setup_logging()
    logger = logging.getLogger("app")
    logger.info("剧情生成", extra={"session_id": 1})
"""
import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    """JSON 格式日志格式器。"""

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "time": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # 附带额外字段（extra 参数）
        for key in ("session_id", "task_id", "duration_ms"):
            val = getattr(record, key, None)
            if val is not None:
                data[key] = val
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    """初始化 JSON 结构化日志（stdout 输出）。"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
