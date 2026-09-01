# US05 会话历史持久化与断点续玩

优先级：P0 ｜ 故事点：3 ｜ 对应 Sprint 2

## Card

- **As a**：跑团玩家
- **I want**：会话状态被保存
- **So that**：退出后能恢复继续玩

## Conversation

- 前置条件：玩家创建会话并产生历史
- 描述：会话、消息、角色、检定结果存入 SQLite；玩家可列出历史会话并恢复；重启服务后数据不丢失
- 验收：数据写入 SQLite；重启后能恢复会话；消息按时间顺序保存

## Confirmation

```gherkin
Feature: 会话持久化与断点续玩
  Scenario: 恢复会话
    Given 玩家有已保存的历史会话
    When 玩家重新进入会话
    Then 系统恢复剧情、角色属性与对话历史
  Scenario: 数据持久
    Given 服务重启
    When 玩家重新加载会话
    Then 历史数据完整可读
```

---

## 故事级 6 图

### 图 1：用例 / 边界图（Story Context & Scope）

```mermaid
graph TD
    Player[玩家]
    subgraph US05[US05 功能边界]
        UC1[保存会话状态]
        UC2[恢复历史会话]
        UC3[列出历史会话]
    end
    SVC[SessionRepository]
    Player --> UC1
    Player --> UC2
    Player --> UC3
    UC1 --> SVC
    UC2 --> SVC
    UC3 --> SVC
    Note["前置条件：会话存在历史数据\n后置条件：数据写入 SQLite"]
```

### 图 2：组件 / 数据流图（Story Component / Data Flow）

```mermaid
flowchart LR
    U[玩家] -->|"保存/恢复"| API[SessionService]
    API --> REPO[SessionRepository]
    REPO -->|"INSERT/SELECT"| DB[(SQLite)]
    REPO -->|"数据返回"| U
```

### 图 3：领域类与数据契约图（Pydantic Schema）

```mermaid
classDiagram
    class SessionRepository {
        +save(session) void
        +load(id) Session
        +list() list~Session~
    }
    class Session {
        +int id
        +str name
        +str scene
        +str summary
        +int turn
        +str status
    }
    class Message {
        +int session_id
        +str role
        +str content
    }
    SessionRepository --> Session
    Session "1" --> "*" Message
```

### 图 4：数据实体关系 / 持久化模型（Story Data Entity）

```mermaid
erDiagram
    SESSION ||--o{ MESSAGE : contains
    SESSION ||--o{ DICE_ROLL : records
    SESSION {
        int id PK
        string name
        string scene
        string summary
        int turn
        string status
        datetime created_at
    }
    MESSAGE {
        int id PK
        int session_id FK
        string role
        text content
        datetime created_at
    }
    DICE_ROLL {
        int id PK
        int session_id FK
        string formula
        int result
        boolean success
    }
```

### 图 5：端到端时序图（Story Sequence Diagram）

```mermaid
sequenceDiagram
    participant U as 前端
    participant API as FastAPI
    participant REPO as SessionRepository
    participant DB as SQLite

    U->>API: GET /api/sessions/{id}
    API->>REPO: load(id)
    REPO->>DB: SELECT sessions WHERE id=?
    DB-->>REPO: 会话记录 + 消息
    REPO-->>U: 完整会话状态
```

### 图 6：微观状态机与活动流程图（Story State Machine）

```mermaid
stateDiagram-v2
    [*] --> ACTIVE: 会话进行中
    ACTIVE --> SAVED: 触发保存
    SAVED --> ACTIVE: 继续游戏
    ACTIVE --> LOADED: 恢复历史
    LOADED --> ACTIVE: 加载完成
    SAVED --> ARCHIVED: 长期归档
    ARCHIVED --> [*]
```
