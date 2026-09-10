"""安全服务：输入校验 + Prompt 注入防护（S3-3）。

- validate_input：空/超长输入拦截
- check_injection：检测越权指令（Prompt 注入）
- sanitize：校验 + 防护，返回清理后的安全输入
"""
INJECTION_PATTERNS = [
    # 越权指令（真注入）：故意避开"扮演/忽略"等正常跑团常用词，防止误伤
    "忽略之前的",
    "忽略以上",
    "无视系统",
    "无视之前",
    "系统提示词",
    "系统提示",
    "你现在是",
    "越狱",
    "泄露提示",
    "输出你的提示",
    "ignore previous",
    "ignore above",
    "jailbreak",
    "developer mode",
    "repeat the system prompt",
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
