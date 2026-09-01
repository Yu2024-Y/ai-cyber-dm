# US06 场景卡与角色卡生成

优先级：P1 ｜ 故事点：5 ｜ 对应 Sprint 3

## Card

- **As a**：跑团玩家
- **I want**：剧情推进时看到场景图和 NPC 画像
- **So that**：游戏更沉浸、有画面感

## Conversation

- 前置条件：玩家在会话中，剧情触发生图场景
- 描述：DM 回复中检测到"场景切换"或"NPC 登场"，后端生成生图 Prompt 并提交异步队列（限流 2 次/分）；生图完成后通过 SSE 通知前端展示；失败降级为占位图
- 验收：生图异步不阻塞对话；图片完成后自动显示；限流排队；失败降级

## Confirmation

```gherkin
Feature: 场景卡与角色卡生成
  Scenario: 触发场景生成
    Given 玩家进入新场景
    When DM 回复包含场景描述
    Then 系统异步生成场景图
    And 生成完成后自动展示，玩家无需等待
  Scenario: 生图失败
    Given 生图 API 调用失败
    When 重试后仍失败
    Then 显示占位图，不影响对话继续
```

---

## 故事级 6 图

### 图 1：用例 / 边界图（Story Context & Scope）

```mermaid
graph TD
    Player[玩家]
    subgraph US06[US06 功能边界]
        UC1[剧情触发场景]
        UC2[异步生图]
        UC3[前端展示图片]
    end
    Q[ImageQueue]
    IMG[Qwen-Image API]
    Player --> UC3
    UC1 --> UC2 --> Q --> IMG
    UC2 --> UC3
    Note["前置条件：S1-8 生图服务已接入\n后置条件：图片URL返回并展示"]
```

### 图 2：组件 / 数据流图（Story Component / Data Flow）

```mermaid
flowchart LR
    DM[DMEngine] -->|"触发场景"| Q[ImageQueue]
    Q -->|"限流控制"| IMG[Qwen-Image API]
    IMG -->|"图片URL"| Q
    Q -->|"SSE 推送"| U[前端]
    U -->|"GET"| API["/api/images/{id}"]
    API --> DB[(SQLite scene_cards)]
    DB -->|"URL"| U
```

### 图 3：领域类与数据契约图（Pydantic Schema）

```mermaid
classDiagram
    class SceneCard {
        +int session_id
        +str prompt
        +str image_url
        +str status
    }
    class ImageQueue {
        +submit(session_id, prompt) int
        +process() void
        +query(task_id) str
    }
    class ImageService {
        +generate_image(prompt) str
    }
    ImageQueue --> SceneCard
    ImageQueue --> ImageService
```

### 图 4：数据实体关系 / 持久化模型（Story Data Entity）

```mermaid
erDiagram
    SESSION ||--o{ SCENE_CARD : renders
    SCENE_CARD {
        int id PK
        int session_id FK
        string prompt
        string image_url
        string status
        datetime created_at
    }
```

### 图 5：端到端时序图（Story Sequence Diagram）

```mermaid
sequenceDiagram
    participant U as 前端
    participant DM as DMEngine
    participant Q as ImageQueue
    participant IMG as Qwen-Image API
    participant DB as SQLite

    U->>DM: 玩家指令(进入新场景)
    DM->>Q: 提交生图任务(prompt)
    Q->>IMG: 限流后调用 generate_image
    IMG-->>Q: 图片URL
    Q->>DB: 保存 SceneCard
    Q-->>U: SSE 推送"图片就绪"
    U->>DB: 获取图片URL
    DB-->>U: 展示场景图
```

### 图 6：微观状态机与活动流程图（Story State Machine）

```mermaid
stateDiagram-v2
    [*] --> PENDING: 提交生图任务
    PENDING --> RUNNING: 队列出队/限流放行
    RUNNING --> VALIDATING: 生图 API 返回
    VALIDATING --> SUCCESS: 校验通过(URL合法)
    VALIDATING --> FAILED: 校验失败
    RUNNING --> FAILED: API 错误/超时
    FAILED --> RUNNING: 重试(Tenacity 指数退避)
    FAILED --> DEAD: 重试耗尽(占位图降级)
    SUCCESS --> [*]
    DEAD --> [*]
```
