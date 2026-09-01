"""S1-8 生图服务单测（mock 外部 API，不消耗真实额度）。"""
from unittest.mock import MagicMock

import pytest

from src.services import image_service


def test_generate_image_returns_url(monkeypatch) -> None:
    """generate_image 返回图片 URL。"""
    monkeypatch.setattr(image_service.settings, "siliconflow_api_key", "sk-test")

    fake_client = MagicMock()
    img = MagicMock()
    img.url = "https://example.com/scene.png"
    fake_client.images.generate.return_value.data = [img]
    monkeypatch.setattr(image_service, "_get_client", lambda: fake_client)

    url = image_service.generate_image("a cyberpunk tavern")
    assert url == "https://example.com/scene.png"
    fake_client.images.generate.assert_called_once()


def test_generate_passes_arguments(monkeypatch) -> None:
    """generate_image 把模型与尺寸参数传给 OpenAI。"""
    monkeypatch.setattr(image_service.settings, "siliconflow_api_key", "sk-test")

    fake_client = MagicMock()
    img = MagicMock()
    img.url = "https://example.com/npc.png"
    fake_client.images.generate.return_value.data = [img]
    monkeypatch.setattr(image_service, "_get_client", lambda: fake_client)

    image_service.generate_image("portrait of a ranger", size="768x1344")
    kwargs = fake_client.images.generate.call_args.kwargs
    assert kwargs["model"] == image_service.settings.image_model
    assert kwargs["prompt"] == "portrait of a ranger"
    assert kwargs["size"] == "768x1344"


def test_generate_requires_key() -> None:
    """未配置 API Key 时抛出 RuntimeError。"""
    image_service.settings.siliconflow_api_key = ""
    with pytest.raises(RuntimeError):
        image_service.generate_image("a cat")
