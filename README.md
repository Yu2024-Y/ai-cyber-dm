# AI 赛博 DM 与无限跑团引擎 ✨

基于敏捷方法的 AI 原生应用开发实践 · 课程项目

利用 `DeepSeek-V4-Flash` 扮演跑团 / 剧本杀主持人（DM），实时处理玩家自由指令、判定骰子检定、推进剧情分支，并调用生图 API 渲染场景卡片与 NPC 角色画像，配合微软 `edge-tts` 实现剧情语音播报。

## 核心能力

- 🎲 自由指令主持：玩家任意输入，AI 实时回应并推进剧情
- 🎯 骰子检定：Pydantic 结构化数值检定，结果影响剧情走向
- 🖼️ 场景 / 角色卡：异步生成场景与 NPC 画像
- 🔊 语音播报：关键剧情 edge-tts 中文配音

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python + FastAPI + SQLite |
| LLM | DeepSeek-V4-Flash（SiliconFlow） |
| 生图 | Qwen/Qwen-Image（SiliconFlow） |
| 语音 | edge-tts（微软免费） |
| 测试 | Pytest + Behave(Gherkin BDD) |
| 部署 | Docker + docker-compose + GHCR 镜像 |

## 项目结构

```
├── .github/          # CI 流水线 + Issue/PR 模板
├── docs/             # 架构设计、User Story、Sprint 报告
├── src/              # 后端源代码
├── tests/            # 单元测试 + BDD 验收测试
├── eval/             # 评测数据集与评分脚本
├── static/           # 前端页面 + 生图本地缓存
├── Dockerfile        # 容器镜像定义
├── docker-compose.yml # 一键启动编排
├── .env.example      # 环境变量模板
├── AGENTS.md         # 团队 AI 协作规则
└── README.md
```

## Docker 一键启动

前置：安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)（Windows 需启用 WSL2）。

```bash
cp .env.example .env          # 填入 SILICONFLOW_API_KEY（可跳过，见下）
docker compose up -d --build
```

打开 <http://localhost:8000> 即可跑团；健康检查：

```bash
curl http://localhost:8000/health      # → {"status":"ok"}
```

- **密钥只走运行时注入**：镜像内不含 `.env`（`.dockerignore` 已排除），配置由 `docker compose` 的 `env_file` 或 `docker run --env-file .env` 提供。
- **无 Key 也能启动**：缺少 `SILICONFLOW_API_KEY` 时 LLM 走本地兜底剧情、生图任务标记失败，`/health` 仍返回 `ok`。
- **数据持久化**：SQLite 存于命名卷 `dm-data`，生图缓存存于 `dm-generated`；`docker compose down` 不丢数据，`down -v` 才会清空。
- 不用 compose 时：`docker build -t ai-cyber-dm .` + `docker run -p 8000:8000 --env-file .env ai-cyber-dm`。
- CI 在合并到 `main` 后自动构建并推送镜像到 GHCR：`ghcr.io/yu2024-y/ai-cyber-dm`。

## 团队成员

- 淦昱阳
- 陈昱彤
- 熊梓翔

## 文档

- [系统设计（架构图）](docs/system_design.md)
- [Sprint 1 Backlog](docs/sprint1_backlog.md)

## License

[MIT](LICENSE)
