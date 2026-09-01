# US02 玩家指令触发 DM 剧情生成

> 核心用户故事（含 6 图建模）｜ 优先级：P0 ｜ 故事点：5 ｜ 对应 Sprint 2

---

## Card（卡片）

- **用户角色（As a）**：跑团玩家
- **需求（I want）**：输入任意自由指令
- **价值（So that）**：DM 实时生成剧情、推进冒险，体验"自由行动"的跑团乐趣

## Conversation（对话）

- **前置条件**：玩家已创建/加载会话（US01），会话状态正常
- **故事描述**：玩家在对话界面输入自由指令（如"我撬开那扇门"），系统调用 DeepSeek-V4-Flash 生成剧情回应，通过 SSE 流式推送给前端展示；剧情与历史上下文衔接
- **验收标准**：
  1. 输入指令后 3 秒内开始流式返回剧情
  2. 剧情内容连贯，引用历史上下文
  3. 支持 SSE 流式"打字机"效果
  4. 空指令/超长指令被拦截并提示

## Confirmation（Gherkin BDD）

```gherkin
Feature: 玩家指令触发 DM 剧情生成
  Scenario: 玩家输入自由指令，DM 生成剧情
    Given 玩家已进入会话"赛博酒馆"
    When 玩家输入"我走向吧台，问老板最近有什么传闻"
    Then 系统调用大模型生成剧情回应
    And 剧情文本通过 SSE 流式返回
    And 前端展示完整剧情内容

  Scenario: 输入为空或超长
    Given 玩家在会话中
    When 玩家输入空白或超过 500 字的指令
    Then 系统返回输入错误提示
    And 不调用大模型
```

---

## 故事级 6 图

### 图 1：用例 / 边界图（Story Context & Scope）

```mermaid
graph TD
    Player[玩家]
    subgraph US02[US02 功能边界]
        UC1[输入自由指令]
        UC2[触发剧情生成]
        UC3[SSE 流式接收剧情]
    end
    DM[DM 引擎]
    LLM[DeepSeek-V4-Flash]
    Player --> UC1
    UC1 --> UC2 --> DM --> LLM
    UC3 --> Player
    Note["前置条件：US01 会话已创建"]
```

### 图 2：组件 / 数据流图（Story Component / Data Flow）

```mermaid
flowchart LR
    U[玩家] -->|自由指令| API["POST /api/chat"]
    API --> SVC[DMEngine]
    SVC -->|组装上下文| LLM[DeepSeek-V4-Flash]
    LLM -->|剧情文本流| SVC
    SVC -->|SSE 推送| U
    SVC -->|保存消息| DB[(SQLite)]
```

### 图 3：领域类与数据契约图（Pydantic Schema）

```mermaid
classDiagram
    class ChatRequest {
        +int session_id
        +str content
    }
    class ChatResponse {
        +int session_id
        +str role
        +str content
    }
    class Message {
        +int session_id
        +str role
        +str content
        +datetime created_at
    }
    class DMEngine {
        +build_context(session) str
        +generate_stream(messages) AsyncIterator[str]
    }
    DMEngine --> ChatRequest
    DMEngine --> ChatResponse
    DMEngine --> Message
```

### 图 4：数据实体关系 / 持久化模型（Story Data Entity）

```mermaid
erDiagram
    SESSION ||--o{ MESSAGE : contains
    MESSAGE {
        int id PK
        int session_id FK
        string role
        text content
        datetime created_at
    }
    SESSION {
        int id PK
        string name
        string scene
        int turn
        string status
    }
```

### 图 5：端到端时序图（Story Sequence Diagram）

```mermaid
sequenceDiagram
    participant U as 前端
    participant API as FastAPI
    participant DM as DMEngine
    participant LLM as DeepSeek-V4-Flash
    participant DB as SQLite

    U->>API: POST /api/chat {session_id, content}
    API->>DM: 组装上下文(历史+摘要+检定指令)
    DM->>LLM: 流式请求(stream=true)
    loop SSE 流式输出
        LLM-->>DM: 剧情文本 chunk
        DM-->>U: SSE data: 文本 chunk
    end
    DM->>DB: 保存 Message
    API-->>U: 流结束事件
```

### 图 6：微观状态机与活动流程图（Story State Machine）

```mermaid
stateDiagram-v2
    [*] --> RECEIVED: 收到指令
    RECEIVED --> VALIDATING: 校验输入
    VALIDATING --> GENERATING: 校验通过
    VALIDATING --> REJECTED: 校验失败(返回提示)
    GENERATING --> STREAMING: 流式输出
    STREAMING --> COMPLETED: 输出完成
    COMPLETED --> [*]
    REJECTED --> [*]
    GENERATING --> RETRY: API 失败/超时
    RETRY --> GENERATING: 指数退避重试
    RETRY --> FAILED: 重试耗尽(返回降级提示)
    FAILED --> [*]
```
