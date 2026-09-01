"""应用配置：从 .env 读取，所有外部依赖参数集中管理。

对应 .env.example 模板，未配置时使用默认值（便于本地与 CI 运行）。
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI 赛博 DM"
    app_version: str = "0.1.0"

    # SiliconFlow API
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"

    # 模型
    llm_model: str = "deepseek-ai/DeepSeek-V4-Flash"
    image_model: str = "Qwen/Qwen-Image"
    vision_model: str = "Qwen/Qwen3.6-35B-A3B"

    # 生图限流（SiliconFlow 免费额度速率）
    image_rate_limit_per_minute: int = 2

    # TTS
    tts_voice: str = "zh-CN-XiaoxiaoNeural"

    # 存储与服务
    database_url: str = "sqlite:///./campaign.db"
    app_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    """缓存配置实例，避免重复读取 .env。"""
    return Settings()
