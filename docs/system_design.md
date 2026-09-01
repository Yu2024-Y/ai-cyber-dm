# AI 赛博 DM 与无限跑团引擎 — 系统设计文档

> 版本：v0.1（Kick-off 初版）｜ 更新：2026-08-29
> 对应课程：《工程实践（基于敏捷方法的 AI 原生应用开发实践）》Sprint 1 交付物

---

## 1. 项目概述

**选题**：AI 赛博 DM 与无限跑团 / 剧本杀引擎（AI-DM & Immersive RPG Engine）

利用 `DeepSeek-V4-Flash` 的逻辑推理能力，由 AI 扮演跑团 / 剧本杀主持人（DM）。系统实时判决玩家输入的自由指令、判定随机骰子检定、演进剧情分支，并调用生图 API 渲染场景卡片与 NPC 角色画像，配合微软 `edge-tts` 实现语音播报。

**三大核心技术难点**：
1. 多轮对话上下文记忆管理
2. Pydantic 结构化数值检定
3. SSE 流式文本与生图异步同步

**技术栈**：Python 3.11 + FastAPI + SQLite + 原生前端（HTML/CSS/JS）

---

## 2. 技术栈明细

| 层次 | 选型 | 用途 |
|------|------|------|
| 后端框架 | FastAPI + uvicorn | REST API + SSE 流式输出 |
| 数据校验 | Pydantic v2 | 骰子检定结果、DTO 数据契约 |
| 数据库 | SQLite + SQLAlchemy 2.0 | 会话/历史/卡片持久化 |
| LLM | `deepseek-ai/DeepSeek-V4-Flash`（SiliconFlow） | 剧情生成、DM 主持 |
| 生图 | `Qwen/Qwen-Image`（SiliconFlow） | 场景卡 / NPC 角色卡 |
| 语音 | `edge-tts`（微软免费，本地） | 剧情语音播报 |
| 客户端 | openai SDK（OpenAI 兼容格式） | SiliconFlow API 调用 |
| 测试 | Pytest + Behave(Gherkin) | 单元测试 + BDD 验收 |
| 容器化 | Dockerfile + docker-compose | 部署封装 |

---

## 3. 功能模型（Functional Model）

### 3.1 系统顶层用例图（Use Case Diagram）

```mermaid
graph TD
    Player[玩家/Player]
    Op[运维人员/Operator]

    subgraph System["AI 赛博 DM 系统边界"]
        UC1[创建/加载跑团会话]
        UC2[输入自由指令与 DM 对话]
        UC3[骰子检定判定]
        UC4[剧情分支演进]
        UC5[生成场景卡/NPC角色卡]
        UC6[剧情语音播报]
        UC7[查看剧情分支树]
        UC8[保存/恢复会话]
    end

    LLMAPI[SiliconFlow LLM API<br/>DeepSeek-V4-Flash]
    IMGAPI[SiliconFlow 生图 API<br/>Qwen-Image]
    TTS[edge-tts 本地服务]

    Player --> UC1
    Player --> UC2
    Player --> UC3
    Player --> UC4
    Player --> UC5
    Player --> UC6
    Player --> UC7
    Op --> UC8

    UC2 -.->|extend 调用外部大模型| LLMAPI
    UC5 -.->|extend 调用外部生图模型| IMGAPI
    UC6 -.->|extend 调用语音合成| TTS
```

**Actor 说明**：玩家（主参与者）、运维人员（次要参与者）、外部大模型 API（外部系统）。

### 3.2 系统数据流图（DFD / Level-0）

```mermaid
flowchart LR
    subgraph Actors["外部实体"]
        U[玩家]
        S[SiliconFlow API]
        T[edge-tts]
    end

    subgraph Process["系统加工（0 层）"]
        P1[输入校验<br/>InputValidator]
        P2[DM 引擎<br/>DMEngine]
        P3[骰子检定<br/>DiceService]
        P4[生图队列<br/>ImageQueue]
        P5[TTS 合成<br/>TTSService]
        P6[会话管理<br/>SessionService]
    end

    subgraph Store["数据存储"]
        DB[(SQLite<br/>会话/消息/卡片)]
        F[(生成的<br/>图片/音频)]
    end

    U -->|"自由指令"| P1
    P1 -->|"校验后指令"| P2
    P2 -->|"上下文组装"| P6
    P6 <--> DB
    P2 -->|"推理请求"| S
    S -->|"剧情文本流"| P2
    P2 -->|"检定指令"| P3
    P3 -->|"检定结果"| DB
    P2 -->|"剧情文本"| U
    P2 -->|"异步生图任务"| P4
    P4 -->|"限流请求"| S
    S -->|"图片URL"| P4
    P4 -->|"图片记录"| DB
    P4 -->|"图片就绪事件"| U
    U -->|"语音请求"| P5
    P5 -->|"合成请求"| T
    T -->|"音频文件"| F
    P5 -->|"音频地址"| U
```

---

## 4. 数据模型（Data Model）

### 4.1 系统领域类图（Domain Class Diagram）

```mermaid
classDiagram
    class Session {
        +int id
        +str name
        +str scene
        +str summary
        +int turn
        +str status
        +create() Session
        +load(id) Session
        +save() None
    }
    class Character {
        +int id
        +int session_id
        +str name
        +dict attributes
        +list skills
        +str image_url
    }
    class Message {
        +int id
        +int session_id
        +str role
        +str content
        +datetime created_at
    }
    class DiceRoll {
        +str formula
        +int result
        +int difficulty
        +bool success
        +str reason
        +validate() bool
    }
    class SceneCard {
        +int id
        +int session_id
        +str prompt
        +str image_url
        +str status
    }
    class DMEngine {
        +build_context(session, history) str
        +generate_stream(messages) AsyncIterator[str]
        +parse_dice(text) list~DiceRoll~
    }
    class DiceService {
        +roll(formula) DiceRoll
        +judge(dc, bonus) bool
    }
    class ImageQueue {
        +submit(session_id, prompt) int
        +process() None
        +query(task_id) str
    }
    class TTSService {
        +synthesize(text) str
    }
    class SessionRepository {
        +save(session) None
        +load(id) Session
        +list_messages(id) list~Message~
    }

    Session "1" o-- "*" Message : 包含
    Session "1" o-- "*" Character : 拥有
    Session "1" o-- "*" SceneCard : 渲染
    DMEngine ..> SessionRepository : 依赖
    DMEngine ..> DiceService : 依赖
    DMEngine ..> ImageQueue : 触发
    DMEngine ..> TTSService : 触发
    DiceService ..> DiceRoll : 产出
    ImageQueue ..> SceneCard : 产出
```

**关键契约（Pydantic Schema 示例）**：

```python
class DiceRoll(BaseModel):
    """骰子检定数据契约 —— 由 LLM 结构化输出解析"""
    formula: str          # 如 "1d20+3"
    result: int           # 掷骰结果
    difficulty: int       # 难度值 DC
    success: bool         # 是否成功
    reason: str           # 判定理由

class SceneCard(BaseModel):
    """场景卡数据契约"""
    session_id: int
    prompt: str           # 生图英文 Prompt
    image_url: str | None = None
    status: Literal["PENDING", "RUNNING", "VALIDATING", "SUCCESS", "FAILED"]
```

### 4.2 数据库实体关系图（ER Diagram / Schema）

```mermaid
erDiagram
    SESSION ||--o{ MESSAGE : "contains"
    SESSION ||--o{ CHARACTER : "has"
    SESSION ||--o{ SCENE_CARD : "renders"
    SESSION {
        int id PK
        string name
        string scene
        string summary
        int turn
        string status
        datetime created_at
        datetime updated_at
    }
    MESSAGE {
        int id PK
        int session_id FK
        string role
        text content
        datetime created_at
    }
    CHARACTER {
        int id PK
        int session_id FK
        string name
        json attributes
        json skills
        string image_url
    }
    SCENE_CARD {
        int id PK
        int session_id FK
        string prompt
        string image_url
        string status
        datetime created_at
    }
```

**索引设计**：`MESSAGE(session_id)`、`SCENE_CARD(session_id, status)` 建复合索引以加速会话历史与卡片查询。

---

## 5. 动态 / 行为模型（Dynamic Model）

### 5.1 端到端核心时序图（System Sequence Diagram）

```mermaid
sequenceDiagram
    participant U as 前端 UI
    participant API as FastAPI 后端
    participant DM as DMEngine
    participant LLM as SiliconFlow<br/>DeepSeek-V4-Flash
    participant Q as ImageQueue
    participant IMG as SiliconFlow<br/>Qwen-Image
    participant DB as SQLite

    U->>API: POST /api/chat {session_id, content}
    API->>DM: 组装上下文(历史+摘要+检定指令)
    DM->>LLM: POST /chat/completions (stream=true)
    loop SSE 流式输出
        LLM-->>DM: 剧情文本 chunk
        DM-->>U: SSE data: 文本 chunk（即时渲染）
    end
    Note over DM: 解析剧情中骰子检定指令
    DM->>DB: 保存 Message + DiceRoll
    DM->>Q: 提交异步生图任务
    Q->>IMG: 限流后调用 images/generations
    IMG-->>Q: 图片 URL
    Q->>DB: 更新 SCENE_CARD 状态
    Q-->>U: SSE data: {type: image_ready, task_id}
    U->>API: GET /api/images/{task_id}
    API-->>U: 图片 URL（前端渲染）
    U->>API: POST /api/tts {text}
    API->>DM: TTSService.synthesize()
    DM-->>U: 音频文件地址（前端播放）
```

### 5.2 系统生命周期状态机图（State Diagram）

**会话状态机**：

```mermaid
stateDiagram-v2
    [*] --> CREATED : 新建会话
    CREATED --> ACTIVE : 开始游戏
    ACTIVE --> PAUSED : 保存并退出
    PAUSED --> ACTIVE : 加载继续
    ACTIVE --> ENDED : 剧情完结
    PAUSED --> ENDED : 归档
    ENDED --> [*]
```

**生图任务状态机**（异步任务 PENDING→RUNNING→VALIDATING→SUCCESS）：

```mermaid
stateDiagram-v2
    [*] --> PENDING : 提交生图任务
    PENDING --> RUNNING : 队列出队/限流放行
    RUNNING --> VALIDATING : 生图 API 返回
    VALIDATING --> SUCCESS : 校验通过(URL合法)
    VALIDATING --> FAILED : 校验失败
    RUNNING --> FAILED : API 错误/超时
    FAILED --> RUNNING : 重试(Tenacity 指数退避)
    FAILED --> DEAD : 重试耗尽
    SUCCESS --> [*]
    DEAD --> [*]
```

---

## 6. 防御性编程设计（质量防线）

| 风险 | 对策 |
|------|------|
| LLM 输出非结构化 | Pydantic 强校验 + 结构化输出指令 + 失败重试 |
| SiliconFlow 限流(429) | asyncio.Semaphore 限流 + Tenacity 指数退避重试 |
| 生图耗时/排队 | 异步队列 + 前端占位图 + SSE 就绪通知 |
| 上下文超长失忆 | 滑动窗口 + 摘要压缩策略 |
| Prompt 注入 | 系统提示隔离、角色越权指令检测、敏感词过滤 |
| 输入恶意内容 | 输入长度/内容校验、HTML 转义 |
| API Key 泄露 | .env 管理、.env.example 模板、gitignore 排除 |
| 外部 API 不可用 | mock 降级模式（预置剧情/占位图）+ 结构化日志 |

---

## 7. 后续演进（Sprint 3-4）

- 剧情分支树可视化（前端 Mermaid/树形图）
- 场景/角色卡动态渲染与浏览
- 评测数据集 `eval/evalset.json` 与轨迹评分脚本
- Docker 容器化一键启动
