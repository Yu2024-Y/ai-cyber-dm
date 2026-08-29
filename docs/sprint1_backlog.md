# Sprint 1 Backlog（Day 3-4：需求定义与 MVP 骨架）

> 课程：工程实践（基于敏捷方法的 AI 原生应用开发实践）
> 团队规模：3 人 ｜ 迭代时长：2 个工作日 ｜ 更新：2026-08-29

---

## Sprint 目标

完成核心需求拆解与系统骨架搭建。

## 任务清单（12 项 / 29 SP）

优先级说明：**P0** = 本 Sprint 必须完成｜**P1** = 重要，时间紧可最后做

| # | 优先级 | 任务 | 类型 | SP | 验收标准 |
|---|:---:|------|------|:---:|---------|
| S1-1 | P0 | 初始化公开 GitHub 仓库 + 完整目录拓扑（README、.gitignore、AGENTS.md、.env.example、LICENSE） | 基建 | 2 | 仓库公开；拓扑目录齐全；.env.example 含配置模板且无真实 Key |
| S1-2 | P0 | GitHub Projects 看板 + Issue/PR 模板 + main 分支保护 | 协作 | 2 | 看板 5 列（Backlog/To Do/In Progress/In Review/Done）；模板分 User Story/Bug；main 禁直接 push |
| S1-3 | P1 | GitHub Actions CI 骨架（pytest + ruff，PR 触发） | CI | 3 | 提交 PR 自动跑通；空跑一次绿灯 |
| S1-4 | P0 | FastAPI 项目骨架（src/api·services·domain·infra 分层；配置；/health；全局异常处理） | 代码 | 3 | uvicorn 可启动；/health 返回 200；分层清晰 |
| S1-5 | P0 | SQLite 数据层（SQLAlchemy + Session 模型 + 建表 + 基础 CRUD） | 代码 | 3 | 首次启动自动建表；CRUD 单测通过 |
| S1-6 | P0 | 系统架构图（docs/system_design.md 六图初版） | 文档 | 3 | 6 张 Mermaid 图可渲染；与架构设计一致 |
| S1-7 | P0 | LLM 服务封装（DeepSeek-V4-Flash，openai SDK + 超时/错误处理） | 代码 | 3 | 本地 .env 配置后能返回剧情文本 |
| S1-8 | P0 | 生图服务封装（Qwen-Image，images/generations + 错误处理 + 取图 URL） | 代码 | 3 | 调用能返回图片 URL |
| S1-9 | P0 | TTS 服务封装（edge-tts 生成 mp3 保存） | 代码 | 2 | 能生成 mp3 文件 |
| S1-10 | P0 | API 三通 Demo（页面/脚本一键验证 LLM+生图+TTS） | Demo | 2 | 演示时 3 个能力各跑通一次 |
| S1-11 | P1 | 基础单元测试（health、CRUD、各 API 封装的 mock 测试） | 测试 | 3 | pytest 全绿 |
| S1-12 | P0 | 核心需求拆解 → User Story 清单（US01~US08 + US 文档骨架） | 需求 | 2 | docs/user_stories/ 有清单 + 1 个核心 US 六图 |

**小计：P0 × 9 项 / 21 SP｜ P1 × 3 项 / 8 SP｜ 合计 12 项 / 29 SP**

## 3 人分工

| 成员 | 职责 | 任务 | SP |
|------|------|------|:---:|
| A | 架构/需求/LLM | S1-2、S1-6、S1-7、S1-12 | 10 |
| B | 后端/数据/测试 | S1-4、S1-5、S1-11 | 9 |
| C | AI接入/DevOps/Demo | S1-3、S1-8、S1-9 | 8 |
| 全员 | 协作 | S1-1、S1-10 | — |

## DoD（完成定义）

- [ ] 看板 12 项全转 Done
- [ ] CI 绿灯通过
- [ ] API 三通 Demo 可演示
- [ ] `docs/system_design.md` + `docs/sprint1_report.md` 已提交
- [ ] 所有提交遵循 Angular 语义化规范（feat:/fix:/test:/docs:）

## 执行纪律

1. **Code Review**：每个 PR 至少 1 名组员审查 + CI 绿灯后方可合并
2. **看板同步**：每天收工前集体更新 GitHub Projects 状态
3. **分支纪律**：feature 分支开发，main 只进 PR
4. **每日同步**：上午定计划、下午对进度
