# US01 创建与加载跑团会话

优先级：P0 ｜ 故事点：3 ｜ 对应 Sprint 2

## Card

- **As a**：跑团玩家
- **I want**：新建或加载一个跑团会话
- **So that**：能开始游戏或继续之前的冒险

## Conversation

- 前置条件：无
- 描述：玩家输入会话名称并选择场景主题（如"赛博朋克"），系统创建会话并初始化角色；或从历史会话列表选择加载
- 验收：能创建会话、能加载历史会话、会话有唯一标识

## Confirmation

```gherkin
Feature: 创建与加载会话
  Scenario: 新建会话
    Given 玩家未进入任何会话
    When 玩家创建会话"赛博酒馆"，主题"赛博朋克"
    Then 系统创建会话并返回会话 ID
  Scenario: 加载会话
    Given 玩家有历史会话
    When 玩家选择历史会话并进入
    Then 系统加载该会话的剧情与角色状态
```

---

## 故事级 6 图

### 图 1：用例 / 边界图（Story Context & Scope）

```mermaid
graph TD
    Player[玩家]
    subgraph US01[US01 功能边界]
        UC1[创建新会话]
        UC2[加载历史会话]
        UC3[初始化角色与场景]
    end
    SVC[SessionService]
    Player --> UC1
    Player --> UC2
    UC1 --> UC3
    UC2 --> UC3
    UC3 --> SVC
    Note["前置条件：无\n后置条件：返回会话 ID"]
```

### 图 2：组件 / 数据流图（Story Component / Data Flow）

```mermaid
flowchart LR
    U[玩家] -->|"创建/加载请求"| API["POST /api/sessions"]
    API --> SVC[SessionService]
    SVC -->|"写入/读取"| DB[(SQLite sessions 表)]
    SVC -->|"返回会话ID"| U
```

### 图 3：领域类与数据契约图（Pydantic Schema）

```mermaid
classDiagram
    class SessionRequest {
        +str name
        +str scene
    }
    class Session {
        +int id
        +str name
        +str scene
        +str summary
        +int turn
        +str status
        +datetime created_at
    }
    class SessionService {
        +create(request) Session
        +load(id) Session
        +list() list~Session~
    }
    SessionService --> SessionRequest
    SessionService --> Session
```

### 图 4：数据实体关系 / 持久化模型（Story Data Entity）

```mermaid
erDiagram
    SESSION {
        int id PK
        string name
        string scene
        string summary
        int turn
        string status
        datetime created_at
    }
```

### 图 5：端到端时序图（Story Sequence Diagram）

```mermaid
sequenceDiagram
    participant U as 前端
    participant API as FastAPI
    participant SVC as SessionService
    participant DB as SQLite

    U->>API: POST /api/sessions {name, scene}
    API->>SVC: create(request)
    SVC->>DB: INSERT sessions
    DB-->>SVC: 会话记录
    SVC-->>U: 返回 {session_id, name, scene}
```

### 图 6：微观状态机与活动流程图（Story State Machine）

```mermaid
stateDiagram-v2
    [*] --> CREATED: 创建会话
    CREATED --> ACTIVE: 开始游戏
    ACTIVE --> PAUSED: 保存退出
    PAUSED --> ACTIVE: 加载继续
    ACTIVE --> ENDED: 剧情完结
    ENDED --> [*]
```
