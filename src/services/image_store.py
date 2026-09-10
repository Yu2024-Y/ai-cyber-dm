"""场景图本地化存储：把生成结果下载到本地，避免第三方临时链接过期。

- save_remote_image：下载远程图 → 存到 static/generated/，返回可访问的相对路径
- 下载失败时原样返回原 URL（前端仍可临时显示），不抛异常
"""
import hashlib
import urllib.request
from pathlib import Path

GENERATED_DIR = Path(__file__).resolve().parents[2] / "static" / "generated"
_TIMEOUT = 30


def _filename_for(key: str) -> str:
    """按 key（如生图 prompt）生成稳定文件名，相同输入可复用已下载结果。"""
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:12] + ".png"


def save_remote_image(url: str, *, key: str, dest_dir: Path | None = None) -> str:
    """下载远程图片到本地，返回相对访问路径；失败则返回原 url。"""
    if not url:
        return url
    target_dir = dest_dir or GENERATED_DIR
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        name = _filename_for(key)
        path = target_dir / name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=_TIMEOUT) as resp:
                path.write_bytes(resp.read())
        return f"/static/generated/{name}"
    except Exception:  # noqa: BLE001  下载失败退回原链，保证展示不中断
        return url
