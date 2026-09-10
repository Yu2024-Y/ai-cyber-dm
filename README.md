# AI 赛博 DM 与无限跑团引擎 ✨

基于敏捷方法的 AI 原生应用开发实践 · 课程项目

利用 `DeepSeek-V4-Flash` 扮演跑团 / 剧本杀主持人（DM），实时处理玩家自由指令、判定骰子检定、推进剧情分支，并调用生图 API 渲染场景卡片与 NPC 角色画像，配合微软 `edge-tts` 实现剧情语音播报。支持**多人在线同局**：先在大厅创建/进入战役，各自选择角色后共同行动。

## 核心能力

- 🏟️ **战役大厅**：每局独立存档（剧情 / 场景 / 剧情树互不串扰），可随时新建或继续
- 🧑🚀 **预设角色**：6 个架空角色（刀锋/幽灵/铁砧/灵犀/扳机/迷雾），同一角色仅限一位玩家占用
- 👥 **真·多人**：同浏览器多标签页 / 局域网多设备加入同一战役，消息增量同步、约 2 秒级互见
- 🎲 **结算协议（grounding）**：成败判定与模型解耦——由外部骰子工具真随机结算并落库，再回灌上下文，模型只能按真实结果续写，从机制上抑制幻觉
- 🎯 **检定门控**：高风险行动先提示难度、等待玩家掷骰，掷完自动结算推进；日常动作乱掷轻处理
- 🏁 **结局机制**：一局默认 10 幕，到达上限自动进入【终章】收束剧情；也可随时"结束本局"生成结局
- 🖼️ **场景卡**：异步生成场景图（限流 2 张/分、失败降级占位图、结果本地缓存避免第三方链接过期）
- 🌳 **剧情分支树**：随对话实时生长的剧情走向可视化
- 🔊 **语音播报**：关键剧情 edge-tts 中文配音（按句切块、新语音打断旧语音）
- 🛡️ **输入防护**：长度校验 + Prompt 注入检测，命中即拒绝且不写入历史
- 🧯 **抗失败兜底**：模型/网络异常时自动切换本地预设剧情，演示不中断

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python + FastAPI + SQLite(SQLAlchemy 2.0) |
| 流式 | SSE（Server-Sent Events） |
| LLM | DeepSeek-V4-Flash（SiliconFlow） |
| 生图 | Qwen/Qwen-Image（SiliconFlow） |
| 语音 | edge-tts（微软免费） |
| 前端 | 原生 HTML / CSS / JS（大厅 / 选角 / 游戏 三视图） |
| 测试 | Pytest（单元 + API 集成） + Behave(Gherkin BDD) |
| 部署 | Docker + docker-compose + GHCR 镜像 |

## 项目结构

```
├── .github/          # CI 流水线（测试与代码质量 / 镜像构建与推送）+ Issue/PR 模板
├── docs/             # 架构设计、User Story、Sprint 报告
├── src/              # 后端源代码
├── tests/            # 单元测试 + API 集成测试 + BDD 验收测试
├── eval/             # 评测数据集与评分脚本
├── static/           # 前端页面 + 生图本地缓存（generated/ 不入库）
├── Dockerfile        # 容器镜像定义
├── docker-compose.yml # 一键启动编排
├── .env.example      # 环境变量模板
├── AGENTS.md         # 团队 AI 协作规则
└── README.md
```

## 本地运行（开发）

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env        # 填入 SILICONFLOW_API_KEY（可跳过，见下）
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

打开 <http://127.0.0.1:8000> → 输入战役名「开始新战役」→ 选角色 → 开跑。

### 局域网多人联机

```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

队友连同一 Wi-Fi，浏览器访问 `http://<你的局域网IP>:8000`（`ipconfig` 可查），各自进入同一战役、选择不同角色即可。
注意：需放行防火墙 8000 端口；校园/公共 Wi-Fi 的 AP 隔离会导致设备互连失败（可改用手机热点）。

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

## API 一览（均按战役隔离）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/roles` | 预设角色目录 |
| GET/POST | `/api/games` | 战役列表 / 新建战役 |
| GET | `/api/games/{id}` | 战役详情（含第几幕 / 状态） |
| POST | `/api/games/{id}/join` | 选择角色加入（同名冲突 409） |
| GET | `/api/games/{id}/players` | 战役内玩家 |
| GET | `/api/games/{id}/messages?after_id=` | 消息增量拉取（多人轮询） |
| POST | `/api/games/{id}/chat` | SSE 流式对话；`resolve=true` 为掷骰结算 |
| POST | `/api/games/{id}/roll` | 掷骰检定（真随机 + 落库 + 广播） |
| POST | `/api/games/{id}/finish` | 手动结束本局（生成终章结局） |
| GET | `/api/games/{id}/story` | 剧情分支树 |
| POST/GET | `/api/games/{id}/scene/task/{tid}` | 触发场景图 / 查询生成状态 |
| GET | `/api/tts?text=` | 语音合成（mp3） |

## 质量与工程化

- **测试**：`pytest`（单元 + `TestClient` + 内存库的 API 集成，含"未掷先结 400""注入拦截""自动终章"等边界）；`ruff check` 全绿
- **CI**：`.github/workflows/ci.yml` 跑测试与代码质量；`docker.yml` 构建并推送 GHCR 镜像
- **评测**：`eval/` 提供评测集与关键词覆盖评分脚本
- **协作**：GitHub Projects 看板 + Issue/PR 模板 + main 分支保护 + PR 交叉审核

## 团队成员

- 淦昱阳
- 陈昱彤
- 熊梓翔

## 文档

- [系统设计（架构图）](docs/system_design.md)
- [Sprint 1 Backlog](docs/sprint1_backlog.md)
- [Sprint 1 迭代报告](docs/sprint1_report.md)
- [Sprint 2 迭代报告](docs/sprint2_report.md)
- [Sprint 3 迭代报告](docs/sprint3_report.md)
- [Sprint 4 迭代报告](docs/sprint4_report.md)

## License

[MIT](LICENSE)
