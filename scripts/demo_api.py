"""API 三通 Demo：一键验证 LLM / 生图 / TTS 三个 AI 能力。

用法：
    python scripts/demo_api.py

前提：
    .env 已配置 SILICONFLOW_API_KEY（生图与 LLM 需要；TTS 免费无需 Key）
"""
import os
import sys

# 将项目根目录加入模块搜索路径，保证任意位置运行都能 import src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_settings
from src.services.image_service import generate_image
from src.services.llm_service import chat
from src.services.tts_service import synthesize

settings = get_settings()


def demo_llm() -> str:
    """① LLM：DM 剧情生成。"""
    print("\n[1/3] 测试 LLM（DeepSeek-V4-Flash）...")
    text = chat(
        [
            {"role": "system", "content": "你是跑团主持人，回复简短。"},
            {"role": "user", "content": "欢迎玩家，用一句话介绍当前场景"},
        ],
        max_tokens=100,
    )
    print(f"  ✓ LLM 返回: {text}")
    return text


def demo_image() -> str:
    """② 生图：场景图生成。"""
    print("\n[2/3] 测试生图（Qwen-Image）...")
    url = generate_image("a cyberpunk tavern at night, neon lights")
    print(f"  ✓ 生图返回 URL: {url[:60]}...")
    return url


def demo_tts() -> str:
    """③ TTS：语音合成。"""
    print("\n[3/3] 测试 TTS（edge-tts）...")
    audio = synthesize("欢迎来到赛博世界，冒险者。")
    out_path = "demo_tts.mp3"
    with open(out_path, "wb") as f:
        f.write(audio)
    print(f"  ✓ TTS 生成音频: {out_path}（{len(audio)} 字节）")
    return out_path


def main() -> None:
    print("=== AI 赛博 DM · API 三通 Demo ===")
    if not settings.siliconflow_api_key:
        print("❌ 未配置 SILICONFLOW_API_KEY，请在 .env 中设置")
        return
    demo_llm()
    demo_image()
    demo_tts()
    print("\n=== 三通 Demo 全部通过 ✅ ===")


if __name__ == "__main__":
    main()
