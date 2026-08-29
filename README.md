# AI 赛博 DM 与无限跑团引擎

基于敏捷方法的 AI 原生应用开发实践 · 课程项目

利用 `DeepSeek-V4-Flash` 扮演跑团 / 剧本杀主持人（DM），实时处理玩家自由指令、判定骰子检定、推进剧情分支，并调用生图 API 渲染场景卡片与 NPC 角色画像，配合微软 `edge-tts` 实现剧情语音播报。

## 核心能力

- 自由指令主持：玩家任意输入，AI 实时回应并推进剧情
- 骰子检定：Pydantic 结构化数值检定，结果影响剧情走向
- 场景 / 角色卡：异步生成场景与 NPC 画像
- 语音播报：关键剧情 edge-tts 中文配音

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python + FastAPI + SQLite |
| LLM | DeepSeek-V4-Flash（SiliconFlow） |
| 生图 | Qwen/Qwen-Image（SiliconFlow） |
| 语音 | edge-tts（微软免费） |
| 测试 | Pytest + Behave(Gherkin BDD) |

## 项目结构

```
├── .github/          # CI 流水线 + Issue/PR 模板
├── docs/             # 架构设计、User Story、Sprint 报告
├── src/              # 后端源代码
├── tests/            # 单元测试 + BDD 验收测试
├── eval/             # 评测数据集与评分脚本
├── .env.example      # 环境变量模板
├── AGENTS.md         # 团队 AI 协作规则
└── README.md
```

## 文档

- [系统设计（架构图）](docs/system_design.md)
- [Sprint 1 Backlog](docs/sprint1_backlog.md)

## License

[MIT](LICENSE)
