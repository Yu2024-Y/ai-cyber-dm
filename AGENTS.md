# 团队 AI 协作规则（AGENTS.md）

本文件用于约束团队在使用 AI 编程辅助（OpenCode / VS Code）时的工程规范。

## 架构约束

- 后端必须遵循分层：`src/api`（路由）、`src/services`（业务）、`src/domain`（Pydantic 契约）、`src/infra`（数据/外部 API）
- 数据契约一律使用 Pydantic v2 定义，禁止裸 dict 跨层传递
- LLM / 生图 / TTS 统一封装为服务类，禁止在路由层直接调用外部 API

## 代码规范

- Python 使用 ruff 检查，遵循 PEP8
- 提交信息遵循 Angular 语义化规范：`feat:` `fix:` `test:` `docs:` `refactor:` `chore:`
- 禁止直接向 `main` 分支推送，必须走 PR + Code Review + CI 绿灯

## 安全红线

- 真实 API Key 只存在于本地 `.env`，已被 `.gitignore` 排除，严禁写入任何代码或提交
- 日志中禁止输出完整 API Key / 敏感输入

## 测试要求

- 新功能必须配套单元测试或 BDD（Gherkin）验收测试
- 涉及外部 API 的测试使用 mock，不依赖真实额度

## 文档要求

- 系统改动须同步更新 `docs/system_design.md`
- 每轮 Sprint 结束提交对应 `sprintN_report.md`
