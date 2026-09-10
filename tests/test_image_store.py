"""场景图本地化存储单测：下载成功 / 失败回退 / 命中缓存。"""
from src.services import image_store


class _FakeResp:
    """最小 urlopen 上下文管理器替身。"""

    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_save_remote_image_writes_local(tmp_path, monkeypatch) -> None:
    """下载成功 → 写入本地并返回 /static/generated/ 相对路径。"""
    monkeypatch.setattr(
        image_store.urllib.request,
        "urlopen",
        lambda url, timeout=30: _FakeResp(b"PNGDATA"),
    )
    out = image_store.save_remote_image(
        "https://example.com/a.png", key="prompt-1", dest_dir=tmp_path
    )
    assert out.startswith("/static/generated/") and out.endswith(".png")
    files = list(tmp_path.glob("*.png"))
    assert len(files) == 1
    assert files[0].read_bytes() == b"PNGDATA"


def test_save_remote_image_fallback_on_failure(tmp_path, monkeypatch) -> None:
    """下载失败 → 原样返回原 URL（前端仍可临时显示）。"""

    def boom(url, timeout=30):
        raise RuntimeError("network down")

    monkeypatch.setattr(image_store.urllib.request, "urlopen", boom)
    url = "https://example.com/b.png"
    assert image_store.save_remote_image(url, key="k", dest_dir=tmp_path) == url


def test_save_remote_image_reuses_cache(tmp_path, monkeypatch) -> None:
    """相同 key 第二次调用命中缓存，不再重复下载。"""
    calls = []

    def counting(url, timeout=30):
        calls.append(url)
        return _FakeResp(b"X")

    monkeypatch.setattr(image_store.urllib.request, "urlopen", counting)
    a = image_store.save_remote_image("https://e/1.png", key="same", dest_dir=tmp_path)
    b = image_store.save_remote_image("https://e/1.png", key="same", dest_dir=tmp_path)
    assert a == b
    assert len(calls) == 1  # 只下载一次
