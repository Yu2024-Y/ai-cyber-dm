"""安全服务：输入校验 + Prompt 注入防护（S3-3）。

- validate_input：空/超长输入拦截
- check_injection：检测越权指令（Prompt 注入）
- sanitize：校验 + 防护，返回清理后的安全输入
"""
INJECTION_PATTERNS = [
    "忽略",
    "忽略之前的设定",
    "无视系统",
    "你现在是",
    "扮演",
    "系统提示",
]


class SecurityError(ValueError):
    """输入校验或安全拦截。"""


def validate_input(content: str, *, max_len: int = 500) -> None:
    """输入校验：空输入 / 超长输入拦截。"""
    if not content or not content.strip():
        raise SecurityError("输入不能为空")
    if len(content) > max_len:
        raise SecurityError(f"输入过长（超过 {max_len} 字）")


def check_injection(content: str) -> None:
    """Prompt 注入防护：检测越权指令。"""
    low = content.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in low:
            raise SecurityError(f"检测到越权指令：{pattern}")


def sanitize(content: str) -> str:
    """输入校验 + 注入防护，返回清理后的安全输入。"""
    validate_input(content)
    check_injection(content)
    return content.strip()
