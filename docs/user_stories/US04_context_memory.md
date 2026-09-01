# US04 上下文记忆管理

优先级：P0 ｜ 故事点：3 ｜ 对应 Sprint 2

## Card

- **As a**：跑团玩家
- **I want**：长对话中 DM 记住之前的剧情
- **So that**：冒险连贯，不因对话过长而"失忆"

## Conversation

- 前置条件：玩家进入会话并产生多轮对话
- 描述：DM 引擎维护上下文：最近 N 轮用原文（滑动窗口），更早内容压缩为剧情摘要；上下文超限时自动摘要；关键状态（角色属性、物品）持久化
- 验收：超过 30 轮对话后仍能引用早期关键信息；上下文窗口不无限膨胀

## Confirmation

```gherkin
Feature: 上下文记忆管理
  Scenario: 长对话不失忆
    Given 玩家进行了超过 30 轮对话
    When 玩家提到第 5 轮捡到的"铁剑"
    Then DM 回应中引用该物品，剧情衔接正确
  Scenario: 上下文压缩
    Given 会话历史超过窗口上限
    When 系统触发摘要压缩
    Then 早期对话被压缩为摘要，关键信息保留
```

---

## 故事级 6 图

### 图 1：用例 / 边界图（Story Context & Scope）

```mermaid
graph TD
    Player[玩家]
    subgraph US04[US04 功能边界]
        UC1[多轮对话历史]
        UC2[滑动窗口管理]
        UC3[摘要压缩]
    end
    DM[DMEngine]
    LLM[DeepSeek-V4-Flash]
    Player --> UC1 --> UC2 --> DM
    UC3 --> UC2
    DM --> LLM
    Note["前置条件：产生多轮对话\n后置条件：上下文不超限"]
```

### 图 2：组件 / 数据流图（Story Component / Data Flow）

```mermaid
flowchart LR
    H[(历史消息)] -->|"最近N轮"| WIN[滑动窗口]
    H -->|"更早消息"| SUM[摘要压缩]
    SUM -->|"剧情摘要"| WIN
    WIN -->|"组装上下文"| DM[DMEngine]
    DM --> LLM[DeepSeek-V4-Flash]
    LLM -->|"剧情回复"| H
```

### 图 3：领域类与数据契约图（Pydantic Schema）

```mermaid
classDiagram
    class ContextWindow {
        +list~Message~ recent
        +str summary
        +int max_rounds
        +trim() void
    }
    class MemoryManager {
        +build_context(session, history) str
        +compress(history) str
        +append(message) void
    }
    class Message {
        +str role
        +str content
    }
    MemoryManager --> ContextWindow
    MemoryManager --> Message
```

### 图 4：数据实体关系 / 持久化模型（Story Data Entity）

```mermaid
erDiagram
    SESSION ||--o{ MESSAGE : contains
    SESSION {
        int id PK
        string summary
    }
    MESSAGE {
        int id PK
        int session_id FK
        string role
        text content
        datetime created_at
    }
```

### 图 5：端到端时序图（Story Sequence Diagram）

```mermaid
sequenceDiagram
    participant U as 前端
    participant DM as DMEngine
    participant MM as MemoryManager
    participant DB as SQLite
    participant LLM as DeepSeek-V4-Flash

    U->>DM: 玩家指令
    DM->>MM: build_context(session, history)
    MM->>DB: 查询历史消息
    DB-->>MM: 历史列表
    MM->>MM: 滑动窗口 + 摘要组装
    MM-->>DM: 上下文文本
    DM->>LLM: 带上下文的请求
    LLM-->>DM: 剧情回复
    DM->>MM: append(新消息)
```

### 图 6：微观状态机与活动流程图（Story State Machine）

```mermaid
stateDiagram-v2
    [*] --> NORMAL: 对话在窗口内
    NORMAL --> NEAR_LIMIT: 接近窗口上限
    NEAR_LIMIT --> COMPRESSING: 触发摘要压缩
    COMPRESSING --> NORMAL: 压缩完成(窗口释放)
    COMPRESSING --> OVERSIZE: 压缩后仍超限
    OVERSIZE --> COMPRESSING: 再次压缩(丢弃最早)
    OVERSIZE --> [*]: 强制截断
```
