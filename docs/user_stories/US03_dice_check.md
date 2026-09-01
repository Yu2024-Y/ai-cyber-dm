# US03 骰子检定判定

> 核心用户故事（含 6 图建模）｜ 优先级：P0 ｜ 故事点：5 ｜ 对应 Sprint 2

---

## Card（卡片）

- **用户角色（As a）**：跑团玩家
- **需求（I want）**：发起骰子检定（如"检定力量"）
- **价值（So that）**：系统用随机骰子 + 属性修正判定成功/失败，让剧情由"命运"决定

## Conversation（对话）

- **前置条件**：玩家已进入会话；角色具备属性值（力量/敏捷等）
- **故事描述**：玩家输入"检定力量对抗 DC 15"等指令，系统生成骰子公式（如 `d20+2`），调用 LLM 输出结构化检定结果，用 Pydantic 强校验，判定成功/失败并影响后续剧情分支
- **验收标准**：
  1. 检定结果结构化，字段包含：公式、数值、难度 DC、成败、理由
  2. Pydantic 校验非法时自动重试（最多 2 次）
  3. 检定结果被持久化并影响剧情

## Confirmation（Gherkin BDD）

```gherkin
Feature: 骰子检定判定
  Scenario: 玩家发起力量检定
    Given 玩家角色力量属性为 14
    When 玩家输入"检定力量对抗 DC 15"
    Then 系统掷出 d20+2 并得出结果
    And 结果包含数值、成败、理由
    And 判定结果被记录并影响剧情

  Scenario: 检定输出不符合契约
    Given 玩家发起检定
    When 大模型返回的检定结果格式不符合数据契约
    Then 系统自动重试解析，最多 2 次
    And 成功后返回结构化结果
    And 重试耗尽则返回错误提示
```

---

## 故事级 6 图

### 图 1：用例 / 边界图（Story Context & Scope）

```mermaid
graph TD
    Player[玩家]
    subgraph US03[US03 功能边界]
        UC1[发起检定指令]
        UC2[掷骰计算]
        UC3[判定成败]
    end
    Dice[DiceService]
    LLM[DeepSeek-V4-Flash]
    Player --> UC1 --> UC2 --> Dice
    Dice -->|结构化输出| UC3
    Note["前置条件：US01 会话 + 角色属性"]
```

### 图 2：组件 / 数据流图（Story Component / Data Flow）

```mermaid
flowchart LR
    U[玩家] -->|"检定力量对抗 DC15"| API["POST /api/dice"]
    API --> DICE[DiceService]
    DICE -->|"生成检定指令"| LLM[DeepSeek-V4-Flash]
    LLM -->|"JSON 检定结果"| DICE
    DICE -->|"Pydantic 校验"| VALID{合法?}
    VALID -->|是| RESULT[返回结构化结果]
    VALID -->|否·重试| LLM
    RESULT --> DB[(SQLite DiceRoll)]
    RESULT --> U[玩家]
```

### 图 3：领域类与数据契约图（Pydantic Schema）

```mermaid
classDiagram
    class DiceRequest {
        +int session_id
        +str expression
        +int dc
    }
    class DiceRoll {
        +str formula
        +int result
        +int difficulty
        +bool success
        +str reason
        +validate() bool
    }
    class DiceService {
        +roll(expression) int
        +judge(roll, dc) bool
        +parse_llm_output(text) DiceRoll
    }
    DiceService --> DiceRequest
    DiceService --> DiceRoll
```

### 图 4：数据实体关系 / 持久化模型（Story Data Entity）

```mermaid
erDiagram
    SESSION ||--o{ DICE_ROLL : records
    DICE_ROLL {
        int id PK
        int session_id FK
        string formula
        int result
        int difficulty
        boolean success
        string reason
        datetime created_at
    }
```

### 图 5：端到端时序图（Story Sequence Diagram）

```mermaid
sequenceDiagram
    participant U as 前端
    participant API as FastAPI
    participant DICE as DiceService
    participant LLM as DeepSeek-V4-Flash
    participant DB as SQLite

    U->>API: POST /api/dice {session_id, expression, dc}
    API->>DICE: 请求检定
    DICE->>LLM: 检定指令(要求 JSON 输出)
    LLM-->>DICE: 检定 JSON
    DICE->>DICE: Pydantic 校验
    alt 校验通过
        DICE->>DB: 保存 DiceRoll
        DICE-->>U: 返回 {result, success, reason}
    else 校验失败
        DICE->>LLM: 重试(最多2次)
    end
```

### 图 6：微观状态机与活动流程图（Story State Machine）

```mermaid
stateDiagram-v2
    [*] --> REQUESTED: 收到检定指令
    REQUESTED --> ROLLING: 生成骰子公式
    ROLLING --> PARSING: LLM 返回结果
    PARSING --> VALIDATING: Pydantic 校验
    VALIDATING --> SUCCESS: 校验通过
    VALIDATING --> RETRY: 校验失败
    RETRY --> PARSING: 重新解析(≤2次)
    RETRY --> FAILED: 重试耗尽
    SUCCESS --> [*]
    FAILED --> [*]
```
