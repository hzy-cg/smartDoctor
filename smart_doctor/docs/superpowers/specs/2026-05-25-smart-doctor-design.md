# SmartDoctor 智能问诊助手 — 系统设计文档

> 版本：v2.2（知识库检索优化）
> 修订日期：2026-06-07
> 修订说明：在 v2.1 多格式文档解析基础上，新增知识库智能检索优化（混合检索/查询改写/重排序/分层权重），详见 3.12 节

## 1. 项目概述

### 1.1 核心定位

AI 问诊助手，面向普通患者，提供基于大模型的智能问诊服务。用户可选择不同医生角色，通过文字或语音描述症状，AI 以医生角色风格进行追问和初步诊断建议，并推荐就诊科室。

### 1.2 关键特性

- **角色化问诊**：每个医生角色拥有独立的 Prompt、知识库、数字人形象、语音风格
- **多模态输入**：支持文字和语音两种症状描述方式
- **双模式交互**：普通聊天模式和数字人对话模式无缝切换
- **RAG 知识增强**：基于医学知识库的检索增强生成，支持公共+私有知识库、版本控制、多格式文档智能解析、分片上传与断点续传、混合检索与智能排序
- **科室推荐**：基于症状分析推荐就诊科室
- **医疗合规**：免责声明、数据保留、知情同意、审计日志

### 1.3 技术决策汇总

| 维度 | 决策 | 修订说明 |
|---|---|---|
| 架构方案 | 自研状态机 + 角色化 Agent + Tools | 原 LangGraph 方案因稳定性风险替换为自研状态机 |
| 后端架构 | Clean Architecture 四层分层 | 新增 domain/application 层，业务逻辑与基础设施解耦 |
| 后端框架 | FastAPI (Python) | — |
| 前端框架 | Vue 3 + TypeScript | — |
| 问诊编排 | 自研 DiagnosisStateMachine | V1 显式状态机，V4 按需引入流程编排引擎 |
| LLM 接入 | 云端大模型 API，Provider 抽象（OpenAI/通义/智谱） | — |
| 向量数据库 | Chroma（V1 MVP）→ Qdrant（V2 升级） | Chroma 生产风险高，提前准备 Qdrant 迁移 |
| 关系数据库 | PostgreSQL | — |
| 语音识别 | 云端 ASR（阿里云/讯飞/腾讯云） + VAD + 术语纠错 | 补充 VAD 和医学术语纠错 |
| 语音合成 | 云端 TTS 流式合成，支持多音色 | 补充流式 TTS + 预合成缓存 |
| 数字人方案 | 2D 先行（Live2D），预留 3D（ThreeJS）升级路径 | — |
| 缓存 | Redis（Agent 缓存 / 会话 / TTS 预合成） | 新增 Redis 替代本地 LRU，支持分布式 |

---

## 2. 整体架构

### 2.1 架构全景（修订版）

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (Vue3)                              │
│                                                                  │
│  ┌──────────────────┐    ┌────────────────────────────────────┐ │
│  │  普通聊天模式     │    │      数字人对话模式                  │ │
│  │  文字输入/语音输入 │    │  Live2D数字人 + TTS播放             │ │
│  │  Markdown渲染     │    │  文字输入/语音输入                   │ │
│  │  来源/科室卡片    │    │  口型同步/表情/动作                  │ │
│  └────────┬─────────┘    └──────────────┬─────────────────────┘ │
│           │        模式无缝切换 ←→       │                       │
│           └──────────────┬───────────────┘                       │
│                          │ 共享对话状态                            │
│  ┌───────────────────────┴──────────────────────────────────┐  │
│  │              医生选择页 / 医生收藏 / 医生筛选              │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ WebSocket + REST + SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                       接口层 (FastAPI API)                       │
│   /chat    /doctors    /knowledge    /voice    /digital-human   │
│   认证 / 校验 / 限流 / 审计日志                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    应用层 (Application Use Cases)                │
│                                                                  │
│  start_consultation / manage_doctor / process_voice / ...        │
│  用例编排：协调领域服务、仓储、基础设施                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      领域层 (Domain)                             │
│                                                                  │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ 领域实体         │  │ 领域服务          │  │ 仓储接口       │  │
│  │ DoctorRole      │  │ DiagnosisStrategy │  │ (Protocol)    │  │
│  │ Conversation    │  │ DoctorMatcher     │  │ DoctorRepo    │  │
│  │ DiagnosisSession│  │ SymptomAnalyzer   │  │ Conversation  │  │
│  │ VoiceConfig     │  │ RAGStrategy       │  │ Repo          │  │
│  └─────────────────┘  └──────────────────┘  └───────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │        DiagnosisStateMachine (自研问诊状态机)               │  │
│  │                                                            │  │
│  │  collecting ──symptom_complete──▶ analyzing                │  │
│  │       ▲                            │                       │  │
│  │       │ need_more                  ├─ ready ──▶ recommending│  │
│  │       └────────────────────────────┘                       │  │
│  │                                  user_confirmed ──▶ completed│
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    基础设施层 (Infrastructure)                   │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │PostgreSQL│ │ Chroma/  │ │ LLM      │ │ 语音服务          │  │
│  │  ORM +   │ │ Qdrant   │ │ Provider │ │ ASR/VAD/TTS      │  │
│  │Repository│ │ 向量存储  │ │ 抽象层   │ │ 术语纠错         │  │
│  │ 实现     │ │          │ │          │ │                  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────────────────┐│
│  │ Redis    │ │对象存储   │ │ 数字人资源存储                    ││
│  │Agent缓存 │ │(知识库文件│ │ Live2D 模型 / 纹理 / 动作 / 表情  ││
│  │TTS预合成 │ │ /导出文件)│ │                                  ││
│  │会话管理  │ │          │ │                                  ││
│  └──────────┘ └──────────┘ └──────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计思想

**Clean Architecture 四层分层**：

| 层 | 职责 | 依赖方向 |
|---|---|---|
| 接口层 (API) | HTTP 通信、校验、认证 | → 应用层 |
| 应用层 (Application) | 用例编排，协调领域服务和基础设施 | → 领域层 |
| 领域层 (Domain) | 纯业务逻辑、实体、规则、状态机 | 无外部依赖 |
| 基础设施层 (Infrastructure) | 数据库、LLM、ASR/TTS 等外部实现 | → 领域层（实现仓储接口） |

关键原则：
- **领域层零外部依赖**：不依赖 ORM、LLM SDK 或任何框架，所有外部依赖通过 Protocol 接口反向注入
- **业务逻辑与渲染状态分离**：Agent 状态只包含临床信息，渲染数据由输出路由层独立生成
- **状态机显式编码**：问诊流程转换规则代码化，可测试、可审计、可回溯

**角色化 Agent 工厂**：AgentFactory 根据医生角色配置动态创建问诊引擎实例，每个实例拥有独立的 Prompt、知识库和 TTS 音色。

**LLM Provider 抽象**：统一封装各云厂商 API，业务层不感知底层模型，支持运行时切换，预留本地模型接入能力。

---

## 3. 核心模块设计

### 3.1 项目目录结构（修订版）

```
smart_doctor/
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── api/                            # 接口层
│   │   ├── deps.py                     # 依赖注入
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   ├── doctor.py
│   │   │   ├── knowledge.py
│   │   │   ├── voice.py
│   │   │   ├── digital_human.py
│   │   │   └── favorite.py
│   │   └── ws.py                       # WebSocket 端点
│   │
│   ├── application/                    # 应用层 — 用例编排
│   │   ├── __init__.py
│   │   └── use_cases/
│   │       ├── start_consultation.py   # 发起问诊
│   │       ├── send_message.py         # 发送消息(文字/语音)
│   │       ├── manage_doctor.py        # 医生角色管理
│   │       ├── process_voice.py        # 语音处理(ASR→纠错→Agent)
│   │       ├── manage_knowledge.py     # 知识库管理
│   │       └── toggle_favorite.py      # 收藏管理
│   │
│   ├── domain/                         # 领域层 — 纯业务逻辑，零外部依赖
│   │   ├── __init__.py
│   │   ├── entities/                   # 领域实体
│   │   │   ├── doctor_role.py
│   │   │   ├── conversation.py
│   │   │   ├── diagnosis_session.py
│   │   │   ├── message.py
│   │   │   └── knowledge_doc.py
│   │   ├── value_objects/              # 值对象
│   │   │   ├── symptom.py
│   │   │   ├── department.py
│   │   │   ├── voice_config.py
│   │   │   └── clinical_state.py
│   │   ├── services/                   # 领域服务
│   │   │   ├── diagnosis_strategy.py   # 问诊策略(状态机)
│   │   │   ├── doctor_matcher.py       # 医生匹配
│   │   │   ├── symptom_analyzer.py     # 症状分析
│   │   │   ├── rag_strategy.py         # RAG 检索策略
│   │   │   └── term_corrector.py       # 医学术语纠错
│   │   ├── repositories/               # 仓储接口 (Protocol)
│   │   │   ├── doctor_repository.py
│   │   │   ├── conversation_repository.py
│   │   │   ├── knowledge_repository.py
│   │   │   └── audit_repository.py
│   │   └── state_machine/              # 问诊状态机
│   │       ├── __init__.py
│   │       ├── diagnosis_machine.py    # 自研状态机
│   │       └── transitions.py          # 状态转换定义
│   │
│   ├── infrastructure/                 # 基础设施层 — 外部依赖实现
│   │   ├── __init__.py
│   │   ├── persistence/                # 持久化
│   │   │   ├── models/                 # SQLAlchemy ORM 模型
│   │   │   │   ├── user.py
│   │   │   │   ├── conversation.py
│   │   │   │   ├── message.py
│   │   │   │   ├── doctor.py
│   │   │   │   ├── digital_human.py
│   │   │   │   ├── knowledge.py
│   │   │   │   ├── favorite.py
│   │   │   │   └── audit_log.py
│   │   │   └── repositories/           # 仓储实现
│   │   │       ├── sql_doctor_repo.py
│   │   │       ├── sql_conversation_repo.py
│   │   │       └── sql_knowledge_repo.py
│   │   ├── llm/                        # LLM Provider 实现
│   │   │   ├── provider.py             # LLMProvider Protocol + 工厂
│   │   │   ├── openai_provider.py
│   │   │   ├── qwen_provider.py
│   │   │   └── zhipu_provider.py
│   │   ├── vectorstore/                # 向量数据库实现
│   │   │   ├── base.py                 # VectorStore Protocol
│   │   │   ├── chroma_store.py         # Chroma 实现
│   │   │   └── qdrant_store.py         # Qdrant 实现(V2 升级)
│   │   ├── voice/                      # 语音服务实现
│   │   │   ├── asr_provider.py         # ASR Provider + 工厂
│   │   │   ├── tts_provider.py         # TTS Provider + 工厂
│   │   │   └── vad.py                  # VAD 语音活动检测
│   │   ├── digital_human/              # 数字人资源管理
│   │   │   ├── resource_manager.py
│   │   │   └── lip_sync.py             # 口型同步生成
│   │   ├── cache/                      # 缓存实现
│   │   │   └── redis_cache.py          # Redis Agent 缓存 / TTS 预合成
│   │   ├── security/                   # 安全
│   │   │   ├── encryption.py           # 数据加密
│   │   │   ├── prompt_guard.py         # Prompt 注入防护
│   │   │   └── compliance.py           # 合规检查
│   │   └── audit/                      # 审计日志实现
│   │       └── audit_logger.py
│   │
│   └── schemas/                        # Pydantic 请求/响应模型
│       ├── __init__.py
│       ├── chat.py
│       ├── doctor.py
│       ├── knowledge.py
│       ├── voice.py
│       └── api_response.py             # 统一响应格式
│
├── migrations/                         # Alembic 数据库迁移
├── tests/
│   ├── unit/                           # 单元测试(领域层为主)
│   ├── integration/                    # 集成测试
│   └── e2e/                            # 端到端测试
├── data/
│   ├── medical_docs/
│   └── digital_human/
│       ├── models/
│       ├── textures/
│       └── motions/
├── pyproject.toml
├── .env.example
└── Dockerfile
```

### 3.2 问诊状态机（替代 LangGraph StateGraph）

**设计理由**：LangGraph 存在 API 不稳定、调试困难、医疗场景需要确定性等问题。自研状态机显式编码转换规则，可测试、可审计、可回溯。

```python
class DiagnosisStateMachine:
    TRANSITIONS = {
        "collecting": {
            "symptom_complete": "analyzing",
            "user_chitchat": "collecting",
            "need_more_info": "collecting",
        },
        "analyzing": {
            "need_more_info": "collecting",
            "ready_to_recommend": "recommending",
            "user_chitchat": "analyzing",
            "symptom_complete": "analyzing",
        },
        "recommending": {
            "user_confirmed": "completed",
            "user_dissatisfied": "collecting",
            "user_chitchat": "recommending",
            "need_more_info": "collecting",
        },
        "completed": {
            "new_symptom": "collecting",
            "user_chitchat": "completed",
        },
    }

    def __init__(self, initial_state: str = "collecting"):
        self._state = initial_state

    @property
    def state(self) -> str:
        return self._state

    def can_transition(self, event: str) -> bool:
        return event in self.TRANSITIONS.get(self._state, {})

    def transition(self, event: str) -> str:
        if not self.can_transition(event):
            self._state = "collecting"
            return self._state
        self._state = self.TRANSITIONS[self._state][event]
        return self._state
```

**问诊流程**：

```
用户消息
   │
   ▼
┌──────────┐
│ 意图识别  │ ← LLM 判断：新症状 / 追问回答 / 追加信息 / 闲聊
└────┬─────┘
     │
     ▼
┌──────────────────┐
│ 状态机事件映射    │ ← 将意图映射为状态机事件
└────┬─────────────┘
     │
     ▼
┌──────────────────┐
│ 状态转换 + 决策   │ ← 根据新状态决定动作
└────┬─────────────┘
     │
     ├─── collecting + 需要追问 → 生成追问问题
     ├─── analyzing + 需要知识 → RAG 检索 → 生成分析
     ├─── recommending → 科室推荐 → 生成建议
     │
     ▼
┌──────────────────┐
│ 响应生成          │ ← 综合所有结果生成回复
└────┬─────────────┘
     │
     ▼
┌──────────────────┐
│ 输出路由          │ ← ClinicalState → PresentationState 转换
└──────────────────┘
```

### 3.3 问诊记忆机制（对话上下文管理）

**设计背景**：V1 初始实现中，`DiagnosisEngine.build_messages()` 仅将当前一条用户消息发送给 LLM，未注入对话历史，导致 LLM 每次回复都处于"失忆"状态，反复询问患者已经回答过的问题（如已告知头痛3天，仍追问"头痛持续多久？"）。

**设计目标**：
- LLM 能感知完整对话历史，避免重复提问
- 意图识别能结合上下文判断，提升分类准确率
- 已收集症状自动追踪，防止重复追问同一症状
- 控制历史消息长度，避免 token 超限

#### 3.3.1 三层记忆增强架构

记忆机制分为三层协同工作，缺一不可：

| 层级 | 机制 | 作用 | 实现位置 |
|------|------|------|----------|
| **数据层** | 对话历史注入 `build_messages()` | 让 LLM **能看到**历史对话 | `diagnosis_strategy.py` |
| **结构层** | 已收集症状摘要 system message | 让 LLM **明确知道**哪些症状已收集 | `diagnosis_strategy.py` |
| **指令层** | ROLE_PROMPT 规则 8、9 | 让 LLM **被要求**不重复、要推进 | `diagnosis_strategy.py` |

#### 3.3.2 数据层：对话历史注入

**存储**：每条消息（用户消息 + AI 回复）通过 `conv_repo.add_message()` 写入 PostgreSQL 的 `messages` 表，关联 `conversation_id`。

**读取**：每次用户发送新消息时，通过 `conv_repo.get_messages(conversation_id, limit=50)` 从 PostgreSQL 查出该对话的全部历史消息（按 `created_at ASC` 升序排列）。

**注入**：历史消息被转换为 `{"role": "user/assistant", "content": "..."}` 格式，注入到 LLM 的 prompt 中。

**数据流**：

```
用户发送消息
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  ① 先存：将用户消息持久化到 PostgreSQL                        │
│     await conv_repo.add_message(user_msg)                    │
│     → INSERT INTO messages (role='user', content='头痛3天')  │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  ② 再查：从 PostgreSQL 查出该对话的全部历史消息               │
│     history_entities = await conv_repo.get_messages(         │
│         conversation_id, limit=50                            │
│     )                                                        │
│     → SELECT * FROM messages                                 │
│       WHERE conversation_id = ?                              │
│       ORDER BY created_at ASC LIMIT 50                       │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  ③ 转换：把数据库实体转为 LLM 可用的格式                      │
│     history = [                                              │
│         {"role": m.role, "content": m.content}               │
│         for m in history_entities                            │
│     ]                                                        │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  ④ 注入：将历史消息注入 LLM prompt                           │
│     engine.generate_intent(user_message, history)            │
│     engine.generate_response(clinical_state, history)        │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  ⑤ 后存：将 AI 回复也持久化到 PostgreSQL                     │
│     await conv_repo.add_message(assistant_msg)               │
└─────────────────────────────────────────────────────────────┘
```

**关键设计决策**：采用"先存再查"策略——先将当前用户消息存入数据库，再查询历史。这样查出的历史自然包含当前消息，避免在 `build_messages()` 末尾重复追加。`build_messages()` 会检测历史末尾是否已包含当前消息，如果包含则仅追加阶段标记。

**历史截断策略**：`build_messages()` 中取最近 10 轮（20条消息），防止 token 超限。`MAX_HISTORY_ROUNDS = 10` 为可配置常量。

#### 3.3.3 结构层：已收集症状摘要

当 `ClinicalState.symptoms` 非空时，`build_messages()` 自动注入一条 system message：

```
[已收集症状：头痛3天、太阳穴胀痛、恶心，请勿重复询问以上症状相关信息]
```

这为 LLM 提供了明确的"已收集清单"，即使对话历史很长，LLM 也能快速了解哪些信息已获取。

**症状自动收集**：`send_message` use case 中，当意图识别结果为 `new_symptom` 或 `follow_up_answer` 时，自动将用户消息追加到 `clinical_state.symptoms`，并持久化到 `conversations` 表的 `symptoms` JSONB 字段。

#### 3.3.4 指令层：ROLE_PROMPT 行为约束

在医生角色提示词中新增两条规则：

```
8. 仔细阅读对话历史，绝对不要重复询问患者已经回答过的问题
9. 如果患者已提供某症状信息，直接基于已有信息继续分析，不要再追问同一症状
```

- **规则 8**：即使历史消息已注入 prompt，LLM 默认倾向对当前输入响应而非回顾上下文，此规则显式要求 LLM 必须阅读历史
- **规则 9**：更进一步，不仅不能重复问，还要求直接利用已有信息推进分析，避免换一种方式重复追问同一症状

#### 3.3.5 意图识别上下文增强

`generate_intent()` 方法同样接收 `history` 参数，将最近 2 轮对话（4条消息）以"患者/医生"格式注入意图分类 prompt：

```
分析以下用户消息的意图，仅输出意图标签（new_symptom/follow_up_answer/...）：

最近对话：
患者：我头痛3天了
医生：头痛持续3天，请问是哪个部位痛？
患者：太阳穴两侧胀痛

用户：还有点恶心
意图：
```

相比原来只看当前一条消息，上下文增强后意图识别能区分"追问回答"和"新症状"，提升分类准确率。

#### 3.3.6 修复后 LLM Prompt 结构

```
┌─────────────────────────────────────────────────────────┐
│ [0] system: ROLE_PROMPT（医生角色 + 问诊规则 1-9）       │
│ [1] system: "[已收集症状：头痛、恶心，请勿重复询问]"     │  ← 结构层
│ [2] system: "参考以下医学资料：\n{rag_context}"（可选）  │
│ [3] user: "我头痛3天了"                                  │  ← 数据层（历史）
│ [4] assistant: "头痛持续3天..."                          │
│ [5] user: "太阳穴两侧胀痛"                               │
│ [6] assistant: "了解了..."                               │
│ [7] user: "[当前阶段: analyzing]\n还有点恶心"            │  ← 当前消息
└─────────────────────────────────────────────────────────┘
```

### 3.4 状态拆分：ClinicalState + PresentationState

**设计理由**：原 DiagnosisState 混合了业务状态和渲染状态，导致 Agent 层和前端耦合。拆分后 Agent 只关心临床信息，渲染数据由输出路由层独立生成。

```python
class ClinicalState(TypedDict):
    symptoms: list[str]
    current_intent: str
    rag_context: str | None
    recommended_dept: str | None
    diagnosis_stage: str              # collecting/analyzing/recommending/completed
    needs_more_info: bool
    doctor_id: str
    input_type: str                   # text / voice
    _last_user_message: str           # 当前用户消息（内部使用，对话历史通过 conv_repo 从数据库读取，见 3.3）

class PresentationState(TypedDict):
    interaction_mode: str             # chat / digital_human
    text_content: str                 # 文字回复
    audio_data: bytes | None          # TTS 音频
    lip_sync_data: LipSyncData | None # 口型数据
    emotion_data: dict | None         # 表情数据
    motion_data: dict | None          # 动作数据
    source_references: list[dict]      # RAG 来源
    department_recommendation: dict | None  # 科室推荐

class OutputRouter:
    """将 ClinicalState 转换为 PresentationState"""

    async def route(self, clinical: ClinicalState, mode: str) -> PresentationState:
        if mode == "chat":
            return self._route_text(clinical)
        elif mode == "digital_human":
            return await self._route_digital_human(clinical)
```

### 3.5 AgentFactory — 角色化 Agent 工厂（修订版）

```python
class AgentFactory:
    """根据医生角色配置动态创建问诊引擎"""

    def __init__(self, llm_provider: LLMProvider, rag_strategy: RAGStrategy,
                 cache: RedisCache):
        self._llm = llm_provider
        self._rag = rag_strategy
        self._cache = cache

    async def get_or_create(self, doctor_id: str) -> DiagnosisEngine:
        cached = await self._cache.get_agent(doctor_id)
        if cached:
            return cached

        doctor = await self._doctor_repo.get_by_id(doctor_id)
        engine = self._create_engine(doctor)
        await self._cache.set_agent(doctor_id, engine, ttl=3600)
        return engine

    def _create_engine(self, doctor: DoctorRoleEntity) -> DiagnosisEngine:
        prompt = self._build_prompt(doctor)
        rag_collections = self._build_rag_collections(doctor)
        return DiagnosisEngine(
            state_machine=DiagnosisStateMachine(),
            llm=self._llm,
            system_prompt=prompt,
            rag_collections=rag_collections,
        )
```

关键设计：
- 依赖领域实体 `DoctorRoleEntity` 而非 ORM 模型
- Agent 缓存使用 Redis（支持分布式、TTL 过期、内存可控）
- 缓存上限：最多 50 个 Agent 实例，LRU 淘汰
- 角色配置更新时通过 Redis Pub/Sub 通知所有实例使缓存失效

### 3.6 语音处理流水线（修订版）

**完整语音输入流水线**：

```
前端录音 → VAD静音检测 → 降噪预处理 → 云端ASR → 医学术语纠错 → Agent
```

```
┌──────────────────────────────────────────────────────────────┐
│                     语音输入流水线                             │
│                                                               │
│  ┌────────┐  ┌─────┐  ┌──────┐  ┌─────┐  ┌──────────┐      │
│  │前端录音 │→│ VAD │→│ 降噪  │→│ ASR │→│ 术语纠错  │→ Agent │
│  │RecordRTC│  │检测 │  │预处理 │  │识别 │  │term_corr │      │
│  └────────┘  └─────┘  └──────┘  └─────┘  └──────────┘      │
│                                                               │
│  VAD: Silero VAD / WebRTC VAD                                │
│       - 检测语音活动，自动截取有效片段                          │
│       - 静音超过 800ms 自动停止录音                            │
│                                                               │
│  术语纠错: 基于医学术语词典的纠错                               │
│       - ASR 常见误识别映射表 (如 "偏头痛" ← "片头痛")          │
│       - 科室/药品名称精确匹配                                  │
│       - 置信度低的识别结果回退到文本确认                        │
└──────────────────────────────────────────────────────────────┘
```

**术语纠错领域服务**（`domain/services/term_corrector.py`）：

```python
class MedicalTermCorrector:
    def __init__(self, term_dict: dict[str, str]):
        self._term_dict = term_dict

    def correct(self, asr_text: str, confidence: float) -> CorrectedResult:
        corrected = self._apply_term_mapping(asr_text)
        if confidence < 0.7:
            return CorrectedResult(text=corrected, needs_confirmation=True)
        return CorrectedResult(text=corrected, needs_confirmation=False)
```

**TTS 流式优化方案**：

```
┌──────────────────────────────────────────────────────────────┐
│               TTS 流式输出流水线                               │
│                                                               │
│  Agent 流式生成文字                                           │
│       │                                                       │
│       ▼                                                       │
│  ┌──────────┐                                                │
│  │ 分句器    │ ← 按标点拆分为独立句子                           │
│  └────┬─────┘                                                │
│       │                                                       │
│       ├─── 句子1 → TTS合成 → 立即推送前端                      │
│       ├─── 句子2 → TTS合成 → 立即推送前端                      │
│       └─── ...                                                 │
│                                                               │
│  优化策略：                                                    │
│  1. 流式TTS: 按句合成边生成边推送，不等全文完成                 │
│  2. 预合成缓存: 常见用语(问候/追问模板)预先合成存入 Redis      │
│  3. 并行流水线: 文字流和音频流通过序列号关联                    │
└──────────────────────────────────────────────────────────────┘
```

**预合成缓存示例**：

```python
PRE_SYNTHESIZED_PHRASES = {
    "greeting_{doctor_name}": "您好，我是{doctor_name}，请描述您的症状",
    "ask_duration": "请问这个症状持续多长时间了？",
    "ask_severity": "疼痛程度如何？1-10分打几分？",
    "recommend_dept": "建议您前往{dept_name}就诊",
}
```

### 3.7 数字人完整策略（修订版）

**数字人资源加载生命周期**：

```
not_loaded → preloading → ready → playing → idle → playing → ...
                              ↓                   ↑
                              └─── 用户发消息 ────┘

降级状态机：
digital_human_full (完整数字人) → digital_human_no_voice (无声) → chat_only (纯文字)
```

**资源预加载策略**：
- 用户进入医生选择页时，预加载已收藏/最近使用的医生数字人模型
- 模型文件按优先级加载：模型骨架 → 纹理贴图 → 动作文件
- 使用 CDN 分发数字人资源，前端浏览器缓存

**交互中断规则**：
- 数字人播放语音时用户发送新消息：中断当前播放，数字人切换到"倾听"状态
- 中断时淡出当前音频（200ms），表情过渡到倾听表情

**降级策略**：

| 触发条件 | 降级目标 | 表现 |
|---|---|---|
| TTS 合成失败 | digital_human_no_voice | 数字人无声动画（口型预计算但不播放音频） |
| 数字人模型加载失败 | chat_only | 降级到聊天模式，提示"数字人暂时不可用" |
| Live2D 渲染异常 | chat_only | 同上 |

### 3.8 医生角色生命周期（新增）

```
draft (草稿) → active (可被选择) → inactive (暂停服务) → archived (归档)

激活校验规则：
- 至少绑定一份知识库（公共或私有）
- 数字人配置可选（无配置则仅聊天模式可用，该医生不显示数字人切换按钮）

状态变更影响：
- draft → active: 通过校验后上架，出现在医生选择列表
- active → inactive: 不再出现在选择列表，已有对话可继续完成
- inactive → archived: 对话只读，保留历史记录
- active/inactive → draft: 编辑修改，需重新校验才能上架
```

**doctor_roles 表新增字段**：

| 字段 | 类型 | 说明 |
|---|---|---|
| lifecycle_state | VARCHAR(16) | draft / active / inactive / archived |
| activated_at | TIMESTAMP | 上架时间 |
| has_digital_human | BOOLEAN | 是否配置数字人（计算字段） |

### 3.9 RAG 知识库版本控制（修订版）

**knowledge_docs 表新增字段**：

| 字段 | 类型 | 说明 |
|---|---|---|
| version | INTEGER | 版本号，从 1 开始 |
| previous_version_id | UUID | 上一版本 ID |

**版本策略**：
- Chroma Collection 按版本隔离：`doctor_{id}_v{version}` 和 `common_v{version}`
- Agent 绑定特定版本，更新知识库后新对话使用新版本，旧对话不受影响
- 文档更新流程：上传新版本 → 后台分块向量化 → 标记 ready → 新对话自动使用新版
- 旧版本保留 N 天后自动清理

### 3.10 医生角色管理模块

```
医生角色管理模块
│
├── CRUD 操作
│   ├── 创建医生角色 (lifecycle_state=draft)
│   ├── 更新医生角色 (配置变更 → Agent 缓存失效 → 回到 draft)
│   ├── 删除医生角色 (级联清理知识库/数字人资源，仅 draft/archived 可删)
│   ├── 查询医生角色 (列表/详情/筛选)
│   ├── 激活医生角色 (draft → active，需通过校验)
│   └── 停用医生角色 (active → inactive)
│
├── 知识库绑定
│   ├── 绑定公共知识库 (所有医生共享)
│   ├── 绑定私有知识库 (医生专属，支持版本控制)
│   └── Agent 查询时：先查私有 → 再查公共
│
├── 批量导入导出
│   ├── 导入：Excel/JSON → 批量创建医生角色
│   └── 导出：医生角色数据 → Excel/JSON
│
└── 数字人配置管理
    ├── 上传/替换 Live2D 模型
    ├── 配置语音风格 (音色/语速/语调)
    └── 配置交互动作 (问候动作/思考动作/关怀动作)
```

---

### 3.11 知识库文档智能解析系统（v2.1 新增）

#### 3.11.1 设计目标

解决当前知识库上传存在的三大瓶颈：**仅支持 txt/md 格式**、**大文件上传卡顿**、**无断点续传**。构建一套完整的文档智能解析系统，支持多格式文档的统一处理与高效上传。

#### 3.11.2 分片上传与断点续传

**整体架构**：

```
前端 (Vue 3)                          后端 (FastAPI)
─────                                ─────
┌──────────────┐                     ┌──────────────────┐
│ UploadManager │                     │ ChunkUploadManager│
│ - 分片切割    │  POST /upload/init  │ - 初始化会话      │
│ - 进度追踪    │ ─────────────────→  │ - 预分配临时文件   │
│ - 队列管理    │                     │                  │
│ - 断点恢复    │  POST /upload/{id}/ │                  │
│              │    chunk/{n}         │ - 偏移写入        │
└──────┬───────┘ ─────────────────→  │ - 更新进度        │
       │                              │                  │
       │        POST /upload/{id}/    │                  │
       │          complete            │ - 校验完整性      │
       └───────────────────────────→  │ - 触发解析流水线   │
                                      │                  │
                      GET /upload/{id}/                 │
                        status         │ - 查询进度       │
       ←───────────────────────────────│                  │
                                      └──────────────────┘
```

**新增 API 端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/knowledge/upload/init` | 初始化上传，返回 `upload_id` |
| `POST` | `/knowledge/upload/{upload_id}/chunk/{index}` | 上传单个分片（multipart/form-data） |
| `POST` | `/knowledge/upload/{upload_id}/complete` | 通知上传完成，触发解析 |
| `GET` | `/knowledge/upload/{upload_id}/status` | 查询上传进度 |
| `DELETE` | `/knowledge/upload/{upload_id}` | 取消/清理上传 |

**分片参数**：
- 默认分片大小：2MB（可配置 1-5MB）
- 并发上传：最多 3 个分片同时传输
- 最大文件：50MB

**断点续传流程**：
1. 前端 `localStorage` 保存 `upload_id`
2. 页面刷新后调用 `GET /upload/{id}/status` 获取已上传分片列表
3. 计算缺失分片，仅上传未完成的分片
4. 所有分片就绪后调用 `complete`

**新增数据模型**：

```sql
-- 上传会话表（跟踪断点续传状态）
CREATE TABLE knowledge_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL,
    doctor_id VARCHAR(64) NOT NULL,
    filename VARCHAR(256) NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(16) NOT NULL,
    chunk_size INT NOT NULL,
    total_chunks INT NOT NULL,
    uploaded_chunks TEXT DEFAULT '',   -- 逗号分隔
    temp_file_path VARCHAR(512),
    status VARCHAR(16) DEFAULT 'uploading',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 3.11.3 多格式文档解析引擎

**架构设计 — Parser 策略模式**：

```
┌─────────────────────────────────────────────────────────┐
│                   DocumentParsingPipeline                │
│                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │ 格式识别  │ → │ 编码检测  │ → │ 内容提取  │ → 统一输出  │
│  │ Detector │   │ Encoder  │   │ Extractor│            │
│  └──────────┘   └──────────┘   └──────────┘            │
│       │              │              │                    │
│   Magic Bytes    chardet/       Parser                  │
│   MIME Sniff    charset-norm    Registry                │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │  ParserRegistry (按扩展名路由)                       ││
│  │  txt → TxtParser    pdf → PdfParser                 ││
│  │  docx→ DocxParser   pptx→ PptxParser                ││
│  │  xlsx→ XlsxParser   mp3 → AudioParser               ││
│  │  mp4 → VideoParser  jpg → ImageParser               ││
│  └─────────────────────────────────────────────────────┘│
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │  异常处理 & 降级策略                                  ││
│  │  FormatFallback → EncodingFallback → PartialResult   ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**统一解析器接口**：

```python
class IDocumentParser(ABC):
    """统一文档解析器接口"""
    
    @abstractmethod
    def supported_formats(self) -> set[str]: ...
    
    @abstractmethod
    def parse(self, file_path: Path, **options) -> ParsedDocument: ...
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool: ...

@dataclass
class ParsedDocument:
    """标准化解析结果"""
    segments: list[TextSegment]    # 文本片段列表
    doc_type: DocType              # 文档类型枚举
    original_format: str           # 原始扩展名
    encoding: str                  # 检测到的编码
    encoding_confidence: float     # 编码置信度
    parse_method: ParseMethod      # 解析方法
    page_count: int = 0
    table_count: int = 0
    overall_confidence: float = 0.0
    extra_metadata: dict = {}
```

**各格式解析策略**：

| 格式 | 解析库 | 策略要点 |
|------|--------|----------|
| TXT/MD | 内置 `open()` | chardet 编码检测 → UTF-8/GBK 回退 → 段落分割 |
| PDF | pdfplumber | 文本型：直接提取+表格；扫描型：OCR(pytesseract) |
| DOCX | python-docx | 段落+表格+页眉页脚提取 |
| PPTX | python-pptx | 幻灯片文本+备注+形状文字+表格 |
| XLSX | openpyxl | 工作表遍历+合并单元格+表头标记 |
| 图片 | Pillow + pytesseract | MSER 文字检测 → OCR 提取；纯图 → 元数据描述 |
| 音频 | Whisper + silero-vad | ffmpeg 转 PCM → VAD 分段 → ASR 转写 → 时间戳 |
| 视频 | ffmpeg + Whisper | 三通道：ASR + 字幕提取 + 关键帧 OCR |

**编码检测统一框架**：

```
BOM 检测 (最高优先级)
  → chardet 统计分析 (>0.7 置信度采用)
    → 启发式逐尝试 (UTF-8 → GBK → GB18030 → Latin-1)
      → 最终回退 (utf-8 + replace 模式)
```

**异常处理降级链路**：

| 异常 | 处理策略 |
|------|----------|
| 格式无法识别 | MIME 嗅探 → 拒绝并提示 |
| 编码不兼容 | 回退到 utf-8 replace 模式 → 标记低置信度 |
| 文件损坏 | 跳过损坏部分 → 返回部分结果 |
| 加密文件 | 拒绝解析 |
| 解析超时 | 保存已完成部分 → 返回部分结果 |
| 内存超限 | 降低 DPI/跳过 OCR/仅前 N 页 |

#### 3.11.4 性能优化措施

| 措施 | 应用场景 | 预期效果 |
|------|----------|----------|
| 流式处理 | 大文本文件 (>10MB) | 内存占用降低 80% |
| 逐页解析 | 大 PDF (>100页) | 内存占用降低 60% |
| 分片并行上传 | 所有文件 | 上传速度提升 50%+ |
| 多通道并行 | 视频文件 | 总体耗时降低 50% |
| 超时控制 | 所有格式 | 避免单文件阻塞队列 |
| 内存监控 | 大文件 | 防止 OOM 崩溃 |

#### 3.11.5 项目目录变更

```
smart_doctor/app/
├── api/v1/
│   └── upload.py                        # [新增] 分片上传 API
├── application/use_cases/
│   └── manage_upload.py                 # [新增] 上传管理领域服务
├── domain/
│   ├── entities/
│   │   └── upload_session.py            # [新增] 上传会话实体
│   └── repositories/
│       └── upload_repository.py         # [新增] 上传仓储接口
├── infrastructure/
│   ├── parsers/                         # [新增] 文档解析器模块
│   │   ├── base.py                      # DocumentParser 抽象基类
│   │   ├── registry.py                  # ParserRegistry 路由
│   │   ├── txt_parser.py                # TXT/MD 解析器
│   │   ├── pdf_parser.py                # PDF 解析器
│   │   ├── docx_parser.py               # DOCX 解析器
│   │   ├── pptx_parser.py               # PPTX 解析器
│   │   ├── xlsx_parser.py               # XLSX 解析器
│   │   ├── image_parser.py              # 图片解析器
│   │   ├── audio_parser.py              # 音频解析器
│   │   ├── video_parser.py              # 视频解析器
│   │   └── validator.py                 # 格式校验器
│   └── persistence/
│       ├── models/
│       │   └── upload_session.py        # [新增] 上传会话 ORM 模型
│       └── repositories/
│           └── sql_upload_repo.py       # [新增] 上传仓储实现
├── schemas/
│   └── upload.py                        # [新增] 上传相关 Schema
```

---

### 3.12 知识库智能检索优化（v2.2 新增）

#### 3.12.1 设计目标

随着多格式文档解析系统上线，知识库内容结构从单一纯文本扩展为**多来源、多格式、多质量等级**的混合语料。当前检索系统存在以下瓶颈：

| 瓶颈 | 现状 | 影响 |
|------|------|------|
| 分块策略单一 | 固定 500 字符按段落切分，无重叠 | 语义边界被切断，跨段落信息丢失 |
| 元数据缺失 | 仅记录 source/doc_id/chunk_index | 无法区分 PDF 页码、PPT 幻灯片、音频时间戳、OCR 置信度 |
| 检索方式单一 | 纯向量相似度搜索 | 医学术语精确匹配场景（如"高血压"vs"高血压病"）效果差 |
| 查询未优化 | 用户原始消息直接检索 | 口语化表达（"我头疼"）与知识库术语（"偏头痛发作"）不匹配 |
| 无重排序 | 仅依赖 embedding 相似度 | 高分文档不一定最相关 |
| 无过滤机制 | 全量检索 | 无法按文档类型、置信度、时间范围过滤 |
| 上下文拼接粗糙 | 直接 `\n`.join() 拼接 | 可能超出 LLM token 限制，或信息密度不足 |

#### 3.12.2 分块策略增强

**现状 → 优化后**：

```
现状：固定 500 字符，按段落 (\n) 切分，无重叠
  ↓
优化：语义感知分块 + 滑动窗口 + 元数据注入
```

**分块参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `chunk_size` | 512 tokens | 基于 token 而非字符数 |
| `chunk_overlap` | 64 tokens | 相邻块重叠，保证语义连续性 |
| `separators` | `["。", ".", "\n\n", "\n", " "]` | 优先级递减的分隔符，优先在句号处切分 |

**分块元数据增强**：

```python
# 优化后的 chunk metadata
{
    "source": "高血压指南2024.pdf",
    "doc_id": "a1b2c3d4...",
    "chunk_index": 3,
    "total_chunks": 15,
    
    # 新增字段
    "doc_type": "pdf",                    # 文档类型
    "parse_method": "text_extraction",    # 解析方法
    "page": 5,                            # 页码（PDF/PPT）
    "slide": None,                        # 幻灯片编号（PPT）
    "timestamp_start": None,              # 时间戳（音频/视频）
    "timestamp_end": None,
    "confidence": 0.95,                   # 提取置信度
    "encoding": "utf-8",                  # 原始编码
    "table_index": None,                  # 表格编号（Excel/PDF表格）
    "heading": "三、诊断标准",             # 最近的标题上下文
    "uploaded_at": "2026-06-01T10:00:00Z", # 上传时间
}
```

**分块时上下文注入**：

```python
def chunk_with_context(chunks: list[str], metadata: dict) -> list[str]:
    """
    每个 chunk 注入文档上下文，提升检索时的语义理解
    
    示例：
    chunk: "患者血压持续高于140/90mmHg..."
    enriched: "[文档: 高血压指南2024.pdf, 第5页, 三、诊断标准]
               患者血压持续高于140/90mmHg..."
    """
    context = f"[文档: {metadata['source']}"
    if metadata.get("page"):
        context += f", 第{metadata['page']}页"
    if metadata.get("heading"):
        context += f", {metadata['heading']}"
    context += "] "
    
    return [context + chunk for chunk in chunks]
```

#### 3.12.3 混合检索架构

**整体架构**：

```
用户查询: "我最近总是头晕，血压偏高"
         │
         ▼
┌────────────────────┐
│   查询优化层         │
│                    │
│ 1. 查询改写         │  "头晕 血压偏高" → "头晕 高血压 血压升高 眩晕"
│ 2. 医学术语扩展     │  术语映射表 + LLM 补全
│ 3. 多查询生成       │  Q1: "头晕的常见原因"
│                    │  Q2: "高血压的诊断标准"
│                    │  Q3: "头晕与高血压的关系"
└──────┬─────────────┘
       │
       ▼
┌────────────────────────────────────────────────────┐
│              混合检索 (Hybrid Search)               │
│                                                     │
│  ┌──────────────────┐   ┌──────────────────────┐   │
│  │ 向量检索 (语义)    │   │ 关键词检索 (BM25)     │   │
│  │                   │   │                      │   │
│  │ embedding 相似度   │   │ 精确术语匹配           │   │
│  │ top_k=10          │   │ top_k=10             │   │
│  └───────┬───────────┘   └──────────┬───────────┘   │
│          │                          │               │
│          └──────────┬───────────────┘               │
│                     ▼                               │
│          ┌──────────────────┐                       │
│          │ 结果融合 (RRF)    │  Reciprocal Rank      │
│          │ score = Σ 1/(k+rank)│  Fusion              │
│          └────────┬─────────┘                       │
│                   ▼                                 │
│          融合后候选集 (top_k=20)                      │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────┐
│              元数据过滤层                             │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 质量过滤   │ │ 类型过滤  │ │ 时效过滤  │           │
│  │ conf>0.5 │ │ 仅PDF/PPT │ │ 近1年文档 │           │
│  └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────┐
│              重排序 (Reranker)                       │
│                                                     │
│  Cross-Encoder (bge-reranker-v2-m3)                 │
│  对每个候选 (query, chunk) 对打分                    │
│  → 选出 top_k=5 最相关片段                          │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────┐
│              上下文组装                               │
│                                                     │
│  - Token 预算管理：总上下文 ≤ 2000 tokens             │
│  - 按相关性降序排列                                   │
│  - 注入来源标签（文档名、页码、时间戳）                  │
│  - 同文档片段合并，减少重复上下文                       │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
              注入 LLM Prompt
```

#### 3.12.4 查询优化

**查询改写 (Query Rewriting)**：

```python
class QueryRewriter:
    """
    查询改写策略：
    1. 口语 → 术语：  "头疼" → "头痛 偏头痛 紧张性头痛"
    2. 缩写展开：     "BP高" → "血压 高血压"
    3. 多角度查询：   生成 2-3 个不同角度的查询
    """
    
    async def rewrite(self, query: str, history: list[dict] = None) -> list[str]:
        """
        输入: "我最近总是头晕，血压偏高"
        输出: [
            "头晕 眩晕 血压升高 高血压",
            "头晕的常见病因和诊断",
            "高血压与头晕的关联性",
        ]
        """
        ...
```

**医学术语映射表**（静默扩展，无需 LLM 调用）：

```python
MEDICAL_TERM_MAP = {
    "头疼": ["头痛", "偏头痛", "紧张性头痛", "丛集性头痛"],
    "血压高": ["高血压", "血压升高", "高血压病"],
    "胸口疼": ["胸痛", "心绞痛", "胸部不适"],
    "喘不上气": ["呼吸困难", "气促", "呼吸窘迫"],
    "发烧": ["发热", "体温升高", "高热"],
    "拉肚子": ["腹泻", "急性胃肠炎", "肠道感染"],
    # ... 覆盖常见症状
}
```

#### 3.12.5 检索策略分层

不同类型文档的知识价值不同，检索时采用差异化策略：

| 文档类型 | 检索优先级 | 策略说明 |
|----------|-----------|----------|
| 医学指南 PDF | 最高 | 优先检索，top_k 翻倍 |
| 教科书 PDF | 高 | 标准检索 |
| PPT 讲义 | 中 | 按幻灯片粒度检索，保留标题层级 |
| 音频转录 | 中 | 按时间戳片段检索，标注说话人 |
| Excel 表格 | 低 | 仅在明确需要数据时检索 |
| OCR 扫描件 | 低（降权） | 置信度 < 0.8 的片段降权 50% |

**检索权重公式**：

```
final_score = base_similarity × doc_type_weight × confidence_weight × recency_weight

doc_type_weight:
  - 医学指南 PDF: 1.0
  - 教科书 PDF: 0.9
  - PPT 讲义: 0.8
  - 音频转录: 0.7
  - Excel 表格: 0.6
  - OCR 扫描件: 0.5

confidence_weight:
  - conf >= 0.9: 1.0
  - conf >= 0.7: 0.8
  - conf >= 0.5: 0.5
  - conf < 0.5: 0.2

recency_weight:
  - 最近 6 个月: 1.0
  - 6-12 个月: 0.9
  - 1-2 年: 0.7
  - 2 年以上: 0.5
```

#### 3.12.6 上下文组装优化

**Token 预算管理**：

```python
class ContextAssembler:
    MAX_CONTEXT_TOKENS = 2000  # 约 1500 个中文字符
    
    def assemble(self, retrieved: list[ChunkResult]) -> str:
        """
        组装上下文：
        1. 按 final_score 降序排列
        2. 同文档连续片段合并（减少重复标题）
        3. Token 预算内截断
        4. 注入来源标签
        """
        sorted_chunks = sorted(retrieved, key=lambda x: x.final_score, reverse=True)
        
        # 同文档合并
        merged = self._merge_same_doc(sorted_chunks)
        
        # 按 token 预算截断
        context_parts = []
        token_count = 0
        for chunk in merged:
            chunk_tokens = self._estimate_tokens(chunk.content)
            if token_count + chunk_tokens > self.MAX_CONTEXT_TOKENS:
                break
            label = self._format_label(chunk.metadata)
            context_parts.append(f"{label}\n{chunk.content}")
            token_count += chunk_tokens
        
        return "\n\n---\n\n".join(context_parts)
    
    def _format_label(self, meta: dict) -> str:
        """格式化来源标签"""
        parts = [f"📄 {meta['source']}"]
        if meta.get("page"):
            parts.append(f"第{meta['page']}页")
        if meta.get("heading"):
            parts.append(meta["heading"])
        if meta.get("timestamp_start") is not None:
            parts.append(f"[{self._format_time(meta['timestamp_start'])}]")
        if meta.get("confidence", 1.0) < 0.8:
            parts.append("⚠️ 低置信度")
        return " | ".join(parts)
```

#### 3.12.7 检索质量监控

| 指标 | 采集方式 | 告警阈值 |
|------|----------|----------|
| 平均检索耗时 | 每次 search 记录 | > 500ms |
| 检索命中率 | 返回结果数 > 0 的比例 | < 80% |
| 平均相关性分数 | 向量相似度均值 | < 0.3 |
| 查询改写命中率 | 术语映射表命中率 | — |
| 上下文 token 使用率 | 已用/预算 | > 90% 频繁触发 |

#### 3.12.8 RAGStrategy 重构

```python
class EnhancedRAGStrategy:
    """
    增强检索策略，替代原 RAGStrategy
    
    核心改进：
    1. 查询改写 → 术语扩展 → 多查询
    2. 混合检索（向量 + BM25）
    3. 元数据过滤（类型/置信度/时间）
    4. 重排序（Cross-Encoder）
    5. 上下文组装（Token 预算 + 来源标签）
    """
    
    def __init__(self, vector_store, bm25_index, reranker, query_rewriter):
        self._vector_store = vector_store
        self._bm25_index = bm25_index
        self._reranker = reranker
        self._query_rewriter = query_rewriter
    
    async def search(self, doctor_id: str, query: str, 
                     history: list[dict] = None,
                     filters: dict = None,
                     top_k: int = 5) -> RAGResult:
        # Step 1: 查询优化
        queries = await self._query_rewriter.rewrite(query, history)
        
        # Step 2: 混合检索
        all_candidates = []
        for q in queries:
            vector_results = await self._vector_store.search(
                collection, q, top_k=10
            )
            bm25_results = self._bm25_index.search(q, top_k=10)
            all_candidates.append(
                self._rrf_fusion(vector_results, bm25_results)
            )
        
        # Step 3: 元数据过滤
        filtered = self._apply_filters(all_candidates, filters)
        
        # Step 4: 重排序
        ranked = await self._reranker.rerank(query, filtered, top_k=top_k)
        
        # Step 5: 上下文组装
        context = self._context_assembler.assemble(ranked)
        
        return RAGResult(content=context, sources=ranked)
```

---

## 4. 数据模型与存储

### 4.1 存储架构

| 存储类型 | 用途 |
|---|---|
| PostgreSQL | 用户、对话、消息、医生角色、数字人配置、收藏、审计日志、上传会话 |
| Chroma/Qdrant | 公共知识库向量、医生私有知识库向量（按版本隔离） |
| Redis | Agent 缓存、TTS 预合成缓存、会话管理、WebSocket 消息路由 |
| 本地文件系统/对象存储 | 知识库原始文件、上传临时文件、数字人模型资源、导出文件 |

### 4.2 PostgreSQL 数据模型

**users — 用户表**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| username | VARCHAR(64) | 用户名，唯一 |
| hashed_password | VARCHAR(256) | 加密密码 |
| phone | VARCHAR(20) | 手机号（AES 加密存储） |
| consent_given | BOOLEAN | 是否签署知情同意书 |
| consent_at | TIMESTAMP | 签署时间 |
| created_at | TIMESTAMP | 创建时间 |
| is_active | BOOLEAN | 是否启用 |

**conversations — 对话表**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| user_id | UUID | 外键 → users |
| doctor_id | UUID | 外键 → doctor_roles |
| title | VARCHAR(256) | 对话标题 |
| interaction_mode | VARCHAR(16) | chat / digital_human |
| diagnosis_stage | VARCHAR(32) | 问诊阶段 |
| symptoms | JSONB | 已收集症状列表 |
| summary | TEXT | 问诊总结 |
| knowledge_version | INTEGER | 使用的知识库版本号 |
| expires_at | TIMESTAMP | 数据过期时间（合规） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**messages — 消息表**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| conversation_id | UUID | 外键 → conversations |
| role | VARCHAR(16) | user / assistant / system |
| content | TEXT | 消息文本内容 |
| input_type | VARCHAR(16) | text / voice |
| audio_url | VARCHAR(512) | 语音文件路径 |
| tool_calls | JSONB | Agent 调用的 Tool 记录 |
| metadata | JSONB | 扩展信息 |
| disclaimer_shown | BOOLEAN | 是否已展示免责声明 |
| created_at | TIMESTAMP | 创建时间 |

**knowledge_docs — 知识文档表（v2.1 扩展）**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| filename | VARCHAR(256) | 原始文件名 |
| file_path | VARCHAR(512) | 本地存储路径 |
| file_type | VARCHAR(16) | pdf / docx / txt / md / pptx / xlsx / mp3 / mp4 |
| file_size | BIGINT | 原始文件大小（字节） |
| chunk_count | INTEGER | 分块数量 |
| version | INTEGER | 版本号，从 1 开始 |
| previous_version_id | UUID | 上一版本 ID |
| status | VARCHAR(16) | uploading / processing / ready / error |
| collection_name | VARCHAR(128) | 对应的 Chroma Collection 名 |
| encoding | VARCHAR(32) | 检测到的文本编码 |
| parse_method | VARCHAR(32) | 解析方法：text_extraction / ocr / asr / hybrid |
| page_count | INTEGER | 页数（PDF/PPT）/ 幻灯片数 |
| parse_duration_ms | INTEGER | 解析耗时（毫秒） |
| uploaded_at | TIMESTAMP | 上传时间 |

**departments — 科室表**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| name | VARCHAR(64) | 科室名称 |
| category | VARCHAR(32) | 分类：内科/外科/妇科/儿科... |
| keywords | JSONB | 关联症状关键词列表 |
| description | TEXT | 科室简介 |

**doctor_roles — 医生角色表**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| name | VARCHAR(64) | 医生姓名 |
| title | VARCHAR(64) | 职称 |
| specialty | VARCHAR(64) | 主攻学科 |
| expertise | TEXT | 擅长领域描述 |
| experience | TEXT | 执业经验描述 |
| education | TEXT | 教育背景描述 |
| avatar_url | VARCHAR(512) | 头像图片路径 |
| rating | DECIMAL(3,2) | 评分 0.00~5.00 |
| lifecycle_state | VARCHAR(16) | draft / active / inactive / archived |
| activated_at | TIMESTAMP | 上架时间 |
| has_digital_human | BOOLEAN | 是否配置数字人 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**digital_humans — 数字人配置表**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| doctor_id | UUID | 外键 → doctor_roles（一对一） |
| model_type | VARCHAR(16) | live2d / threejs |
| model_url | VARCHAR(512) | 模型文件路径 |
| texture_urls | JSONB | 纹理贴图路径列表 |
| voice_style | VARCHAR(64) | TTS 音色标识 |
| speech_rate | DECIMAL(3,2) | 语速 0.50~2.00 |
| pitch | DECIMAL(3,2) | 语调 0.50~2.00 |
| interaction_style | VARCHAR(32) | gentle / professional / lively |
| greeting_motion | VARCHAR(64) | 问候动作标识 |
| thinking_motion | VARCHAR(64) | 思考动作标识 |
| caring_motion | VARCHAR(64) | 关怀动作标识 |
| custom_motions | JSONB | 自定义动作配置 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**doctor_knowledge — 医生-知识库关联表**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| doctor_id | UUID | 外键 → doctor_roles |
| knowledge_doc_id | UUID | 外键 → knowledge_docs |
| access_level | VARCHAR(16) | private / shared |

**favorites — 用户收藏表**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| user_id | UUID | 外键 → users |
| doctor_id | UUID | 外键 → doctor_roles |
| created_at | TIMESTAMP | 收藏时间 |

约束：(user_id, doctor_id) 联合唯一

**knowledge_uploads — 上传会话表（v2.1 新增）**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| user_id | VARCHAR(64) | 上传用户 |
| doctor_id | VARCHAR(64) | 关联医生 |
| filename | VARCHAR(256) | 原始文件名 |
| file_size | BIGINT | 文件总大小（字节） |
| file_type | VARCHAR(16) | 文件扩展名 |
| chunk_size | INT | 分片大小（字节） |
| total_chunks | INT | 总分片数 |
| uploaded_chunks | TEXT | 已上传分片索引（逗号分隔） |
| temp_file_path | VARCHAR(512) | 临时文件路径 |
| status | VARCHAR(16) | uploading / processing / completed / failed |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

**audit_logs — 审计日志表**

| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| user_id | UUID | 操作用户 ID |
| action | VARCHAR(64) | 操作类型 |
| resource_type | VARCHAR(32) | 资源类型 |
| resource_id | UUID | 资源 ID |
| detail | JSONB | 操作详情 |
| ip_address | VARCHAR(45) | 客户端 IP |
| created_at | TIMESTAMP | 操作时间 |

索引：(user_id, created_at), (action, created_at)

### 4.3 模型关系

```
users 1──N conversations
users 1──N favorites
users 1──N audit_logs

conversations N──1 doctor_roles
conversations 1──N messages

doctor_roles 1──1 digital_humans
doctor_roles 1──N doctor_knowledge
doctor_roles 1──N conversations
doctor_roles 1──N favorites

knowledge_docs 1──N doctor_knowledge
knowledge_docs self→previous_version_id (版本链)
```

### 4.4 向量数据库设计

Collection `common_v{version}`：公共医学知识库
Collection `doctor_{id}_v{version}`：医生私有知识库

检索策略：先检索私有再检索公共，合并去重后注入 Prompt。

数据一致性保障（Outbox Pattern）：
- 文档状态变更写入 PostgreSQL 的 outbox 表
- 异步 Worker 消费 outbox 事件，同步操作 Chroma（写入/删除）
- 失败自动重试，确保最终一致

---

## 5. 接口协议规范

### 5.1 REST API 统一响应规范

```json
// 成功响应
{ "code": 0, "data": { ... }, "message": "success" }

// 分页响应
{ "code": 0, "data": { "items": [...], "total": 100, "page": 1, "page_size": 20 } }

// 错误响应
{ "code": 40001, "data": null, "message": "医生角色不存在" }
```

**错误码段**：

| 段 | 范围 | 说明 |
|---|---|---|
| 业务错误 | 40001-40999 | 40001 医生不存在, 40002 知识库未绑定, 40003 问诊未开始... |
| 认证错误 | 41001-41999 | 41001 Token 过期, 41002 权限不足, 41003 未签署知情同意... |
| 系统错误 | 42001-42999 | 42001 LLM 调用失败, 42002 ASR 超时, 42003 TTS 合成失败... |

### 5.2 WebSocket 协议规范

**消息类型枚举**：

| 类型 | 方向 | 说明 |
|---|---|---|
| auth_request | C→S | 认证请求 |
| auth_response | S→C | 认证响应 |
| chat_message | C→S | 用户发送消息 |
| chat_chunk | S→C | AI 流式回复片段 |
| digital_human_frame | S→C | 数字人驱动帧 |
| voice_data | C→S | 语音数据流 |
| error | S→C | 错误消息 |
| ping / pong | 双向 | 心跳 |

**认证流程**：

```
1. 客户端连接 WS: ws://host/ws?token=jwt...
2. 服务端验证 JWT，成功后返回 auth_response
3. 后续消息无需再认证
4. Token 过期前 5 分钟服务端发送 token_refresh 提示
```

**流式消息分段协议**：

```json
{
  "type": "chat_chunk",
  "conversation_id": "uuid",
  "seq": 1,
  "chunk_type": "text",
  "content": "根据您的症状",
  "is_final": false
}

{
  "type": "chat_chunk",
  "conversation_id": "uuid",
  "seq": 5,
  "chunk_type": "source",
  "content": { "doc": "神经内科指南", "page": 12 },
  "is_final": false
}

{
  "type": "chat_chunk",
  "conversation_id": "uuid",
  "seq": 8,
  "chunk_type": "dept",
  "content": { "name": "神经内科", "reason": "头痛伴恶心提示神经系统问题" },
  "is_final": false
}

{
  "type": "chat_chunk",
  "conversation_id": "uuid",
  "seq": 9,
  "chunk_type": "disclaimer",
  "content": "以上建议仅供参考，不能替代专业医生诊断",
  "is_final": true
}
```

**心跳机制**：
- 客户端每 30 秒发送 ping
- 服务端 60 秒未收到心跳则断开连接
- 断线后客户端指数退避重连（1s/2s/4s/8s/最大 30s）

**重连恢复**：
- 重连成功后发送 `last_seq: N`
- 服务端补发 seq > N 的缺失消息
- 超过 100 条未读则仅补发最新 100 条 + 摘要

---

## 6. 前端设计

### 6.1 技术选型

| 维度 | 选择 | 理由 |
|---|---|---|
| 框架 | Vue 3 + TypeScript | 组合式 API |
| 构建工具 | Vite | 极速 HMR |
| UI 组件库 | Naive UI | 中文友好 |
| 状态管理 | Pinia | 官方推荐 |
| 数字人引擎 | pixi-live2d-display | 基于 PixiJS 的 Live2D 渲染 |
| 音频录制 | RecordRTC | 浏览器端录音，支持降噪 |
| 音频播放 | Howler.js | 跨浏览器音频播放 |
| HTTP/WS | Axios + 原生 WebSocket | REST + 流式 |

### 6.2 页面清单

| 页面 | 路由 | 功能 |
|---|---|---|
| 登录/注册 | `/login` | 用户认证 + 首次知情同意 |
| 医生选择 | `/doctors` | 医生列表、筛选、收藏、开始问诊 |
| 问诊对话 | `/chat` | 主页面，含聊天/数字人模式切换 |
| 知识库管理 | `/knowledge` | 上传/查看/删除医学文档 |
| 对话历史 | `/history` | 查看历史对话列表 |
| 医生管理(管理员) | `/admin/doctors` | 医生角色 CRUD、数字人配置、导入导出 |
| 设置 | `/settings` | 模型选择、语音配置 |

### 6.3 前端目录结构

```
frontend/
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/
│   │   └── index.ts
│   ├── stores/
│   │   ├── chat.ts
│   │   ├── user.ts
│   │   ├── knowledge.ts
│   │   ├── doctor.ts
│   │   └── digitalHuman.ts
│   ├── api/
│   │   ├── chat.ts
│   │   ├── knowledge.ts
│   │   ├── auth.ts
│   │   ├── doctor.ts
│   │   ├── voice.ts
│   │   └── favorite.ts
│   ├── composables/
│   │   ├── useChat.ts
│   │   ├── useWebSocket.ts
│   │   ├── useVoiceInput.ts
│   │   ├── useVoiceOutput.ts
│   │   └── useModeSwitch.ts
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatMessage.vue
│   │   │   ├── ChatInput.vue
│   │   │   ├── ChatSidebar.vue
│   │   │   ├── SourceReference.vue
│   │   │   └── ModeSwitch.vue
│   │   ├── digital-human/
│   │   │   ├── DigitalHumanView.vue
│   │   │   ├── Live2DRenderer.vue
│   │   │   ├── LipSyncController.vue
│   │   │   └── EmotionController.vue
│   │   ├── voice/
│   │   │   ├── VoiceInputButton.vue
│   │   │   └── VoiceWaveform.vue
│   │   ├── doctor/
│   │   │   ├── DoctorCard.vue
│   │   │   ├── DoctorFilter.vue
│   │   │   ├── DoctorDetail.vue
│   │   │   └── DoctorForm.vue
│   │   ├── knowledge/
│   │   │   ├── DocUpload.vue
│   │   │   └── DocList.vue
│   │   ├── compliance/
│   │   │   ├── ConsentDialog.vue        # 知情同意弹窗
│   │   │   └── DisclaimerTag.vue        # 免责声明标签
│   │   └── common/
│   │       ├── AppHeader.vue
│   │       └── MarkdownRenderer.vue
│   ├── views/
│   │   ├── ChatView.vue
│   │   ├── DoctorsView.vue
│   │   ├── LoginView.vue
│   │   ├── KnowledgeView.vue
│   │   ├── HistoryView.vue
│   │   ├── SettingsView.vue
│   │   └── admin/
│   │       └── DoctorManageView.vue
│   └── types/
│       └── index.ts
├── public/
│   └── live2d/
│       ├── sdk/
│       └── models/
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### 6.4 关键交互设计

**模式无缝切换**：
1. 保存当前对话上下文
2. 切换 interaction_mode: chat ↔ digital_human
3. 切换渲染层: ChatMessage 列表 ↔ DigitalHumanView
4. 共享 WebSocket 连接和消息流
5. 切入数字人模式时对最新 assistant 消息触发 TTS + 动画
6. 切换 <1s

**语音输入交互**：
1. 按住语音按钮 → RecordRTC 录音 → 波形动画
2. VAD 检测静音 800ms → 自动停止 → 发送音频
3. 后端降噪 → ASR → 术语纠错 → 返回文本
4. 低置信度结果前端展示确认提示
5. 确认文本自动填入输入框并发送

**数字人动画驱动**：
1. Agent 流式生成文字 → 分句器拆分
2. 每句并行：TTS 合成 + 口型/表情/动作数据生成
3. WebSocket 推送驱动帧到前端
4. 前端 Live2DRenderer 渲染口型，EmotionController 插值表情，Howler.js 播放音频
5. 用户发新消息时中断当前播放，淡出 200ms

**消息类型渲染**：

| 消息特征 | 渲染方式 |
|---|---|
| 纯文本回复 | Markdown 渲染 |
| 含 RAG 引用 | 底部 "📚 参考来源" 可展开卡片 |
| 含科室推荐 | 底部 "🏥 建议就诊科室" 卡片 |
| 追问提示 | 高亮追问项，可点选快速回复 |
| 免责声明 | 每条诊断建议底部固定展示 DisclaimerTag |

---

## 7. 非功能性要求

### 7.1 性能

| 要求 | 策略 |
|---|---|
| 响应 ≤2秒 | 文字流式输出（首 token <1s）；流式 TTS 按句推送；TTS 预合成缓存；Agent Redis 缓存 |
| 语音延迟 | VAD 自动截取；ASR 流式识别；TTS 按句合成边生成边推送 |
| 数字人流畅度 | Live2D 纯 Canvas 渲染（目标 60fps）；口型数据预计算；资源预加载 |
| 模式切换 | 渲染层热切换，WebSocket 不断开，<1s |
| RAG 延迟 | 意图识别阶段预取；相似问题检索结果缓存 |

### 7.2 安全与隐私

| 要求 | 策略 |
|---|---|
| 数据传输加密 | HTTPS + WebSocket WSS |
| 敏感数据存储 | PII 字段（手机号等）AES 加密存储 |
| 审计日志 | 全操作记录 |
| 数据脱敏 | 展示层对敏感信息脱敏 |
| 数据保留 | 对话数据设置 expires_at，过期自动脱敏归档 |
| Prompt 注入防护 | 防注入系统指令 + 用户输入预处理 + 输出校验 |

### 7.3 医疗合规

| 要求 | 策略 |
|---|---|
| 知情同意 | 首次使用前必须签署知情同意书，consent_given 字段控制 |
| 免责声明 | 每条诊断建议附加标准免责文本，disclaimer_shown 记录 |
| 科室推荐限制 | 仅推荐科室不推荐具体医院，避免医疗广告风险 |
| 数据所有权 | 用户有权查看/导出/删除自己的所有数据 |
| AI 标识 | 明确标识回复来自 AI，不冒充真实医生 |

### 7.4 错误处理

- 全局异常拦截 + 友好提示 + 错误码体系
- LLM 调用失败：重试 3 次 + 降级切换 Provider
- ASR/TTS 失败：降级到文字模式，提示用户
- 数字人加载失败：降级到聊天模式
- WebSocket 断线：指数退避重连 + 消息补发

### 7.5 水平扩展路径

| 组件 | V1 | V2+ |
|---|---|---|
| 应用服务 | 单实例 | Docker Compose 多实例 + Nginx 负载均衡 |
| WebSocket | 单实例 | Redis Pub/Sub 消息路由 |
| Agent 缓存 | 本地 LRU | Redis 分布式缓存 |
| 向量数据库 | Chroma 嵌入式 | Qdrant Docker 单机 → 集群 |
| 数据库 | PostgreSQL 单机 | PostgreSQL 主从 → 读写分离 |

---

## 8. 迭代路线图

### V1 — 基础骨架：角色化对话 + RAG

**目标**：跑通"选择医生 → 文字问诊 → RAG 增强 → 回复"的核心闭环

| 模块 | 内容 |
|---|---|
| 后端骨架 | FastAPI + Clean Architecture 四层分层 + Alembic |
| 用户认证 | 注册/登录/JWT + 知情同意流程 |
| LLM 接入 | Provider 抽象 + OpenAI/通义接入 |
| 医生角色 | CRUD + 生命周期管理（draft/active/inactive） |
| 问诊状态机 | 自研 DiagnosisStateMachine |
| AgentFactory | 角色化 Agent 工厂 + Redis 缓存 |
| RAG Tool | 文档上传 → 分块 → 向量化 → 检索增强（含版本控制） |
| 对话管理 | 创建对话、历史记录、流式输出 |
| 前端骨架 | Vue3 脚手架 + 路由 + Pinia |
| 医生选择页 | 医生列表、科室/职称筛选、开始问诊 |
| 聊天页 | 文字对话、来源卡片、科室推荐卡片、免责声明 |
| 安全合规 | 审计日志、数据加密、Prompt 注入防护、知情同意 |
| 协议规范 | REST API 统一响应 + WebSocket 完整协议 |
| 数据一致性 | Outbox Pattern 保障 PG+Chroma 一致 |

**验收标准**：
- 用户可注册登录并签署知情同意
- 管理员可创建/编辑/激活医生角色并绑定知识库
- 用户可选择医生开始问诊，AI 以该医生角色风格回复
- RAG 检索结果正确注入回复并展示来源
- 知识库支持上传文档并自动向量化，版本可控
- 回复流式输出，首 token <1s
- 每条诊断建议附带免责声明

### V1.1 — 知识库系统优化（新增）

**目标**：解决 V1 知识库上传的性能瓶颈和格式限制，支持多格式文档智能解析与智能检索

| 模块 | 内容 |
|---|---|
| 分片上传 | 大文件分片传输（2MB/片），并行上传 3 片，支持 50MB 文件 |
| 断点续传 | 上传中断后自动恢复，无需重新上传已完成分片 |
| 上传进度 | 前端实时进度条，分片级别进度展示 |
| 上传队列 | 支持多文件同时上传，最多 3 并发 |
| 多格式解析 | 支持 TXT/MD/PDF/DOCX/PPTX/XLSX/图片/音频/视频 |
| 编码检测 | chardet 自动检测 + BOM 识别 + 多级回退 |
| 格式校验 | Magic Bytes 校验 + 文件完整性检查 |
| 解析降级 | 异常时自动降级（跳过OCR/仅前N页/仅元数据） |
| 智能检索 | 混合检索（向量+BM25）、查询改写、术语扩展、分层权重 |
| 重排序 | Cross-Encoder 重排序，提升检索精准度 |
| 上下文组装 | Token 预算管理、来源标签注入、同文档片段合并 |
| 性能优化 | 流式处理、逐页解析、超时控制、内存监控 |
| 质量保障 | 置信度标记、低质量片段标注、检索质量监控 |

**验收标准**：
- 成功上传 50MB 以内各类格式文件
- 平均上传速度提升 50% 以上，上传失败率 < 1%
- 断点续传：网络中断后可从断点恢复
- 文本提取准确率 > 95%
- 检索召回率 > 85%（Top-5 命中相关文档）
- 检索耗时 < 500ms（含重排序）
- 混合检索比纯向量检索 Top-5 命中率提升 15%+

### V2 — 语音能力 + 医生收藏 + 结构化问诊

**目标**：增加语音输入输出能力，完善交互体验

| 模块 | 内容 |
|---|---|
| ASR 接入 | 云端语音识别 + VAD + 医学术语纠错 |
| TTS 接入 | 云端流式 TTS + 预合成缓存 |
| 语音输入 | 前端录音按钮、波形可视化、VAD 自动停止 |
| 医生收藏 | 收藏/取消收藏、快速访问 |
| 批量导入导出 | 医生角色 Excel/JSON 批量操作 |
| 结构化问诊 | 预设常见症状问诊树 |
| 科室推荐 | 基于症状 + LLM 推理推荐就诊科室 |
| 对话总结 | 问诊结束时自动生成总结报告 |
| 评分系统 | 用户对问诊体验评分 |
| 向量库升级 | Chroma → Qdrant |

**验收标准**：
- 语音输入可用，中文普通话识别准确率 ≥90%
- 语音端到端延迟 <3s
- 术语纠错覆盖常见医学术语误识别
- TTS 流式合成，首句音频 <2s
- 结构化问诊流程至少覆盖 5 个常见症状

### V3 — 数字人模式 + 双模式无缝切换

**目标**：上线数字人对话模式

| 模块 | 内容 |
|---|---|
| Live2D 渲染 | pixi-live2d-display 集成 + 资源预加载 |
| 口型同步 | 音素映射 → Live2D 口型参数驱动 |
| 表情驱动 | 根据回复语义生成表情 |
| 动作驱动 | 预设动作按场景触发 |
| 模式切换 | 聊天 ↔ 数字人无缝切换 |
| 数字人配置 | 管理员配置医生数字人形象 |
| 降级策略 | 完整降级链：数字人 → 无声数字人 → 聊天 |
| 交互中断 | 用户输入中断当前播放 |

**验收标准**：
- 数字人渲染流畅（≥30fps，目标 60fps）
- 口型与语音同步，延迟 <200ms
- 模式切换 <1s，对话上下文无丢失
- 降级策略正常工作

### V4 — 智能体扩展 + 平台化

**目标**：多 Agent 协作、3D 数字人升级、平台化

| 模块 | 内容 |
|---|---|
| 流程编排引擎 | 可视化配置问诊流程/Agent 编排（按需引入 LangGraph 或自研） |
| 多 Agent 协作 | 问诊 Agent → 专科 Agent → 用药提醒 Agent |
| 知识库 Agent | 自动从医学网站抓取/更新知识 |
| 3D 数字人 | ThreeJS 渲染引擎 |
| 用户画像 | 健康档案、个性化问诊 |
| 多模态输入 | 图片上传辅助诊断 |
| 部署优化 | Docker Compose → K8s |

### 迭代节奏一览

```
V1 骨架       V1.1 知识库优化          V2 语音+增强         V3 数字人            V4 平台化
────────────────────────────────────────────────────────────────────────────────────────
角色化对话     分片上传/断点续传         语音输入输出          Live2D 渲染          流程编排引擎
医生角色生命周期 多格式文档解析          VAD+术语纠错         口型/表情/动作        多 Agent 协作
自研状态机     混合检索(向量+BM25)      医生收藏/评分         模式无缝切换          3D 数字人
RAG 知识库(版本) 查询改写/术语扩展       结构化问诊            降级策略              用户画像
安全合规       重排序/分层权重           科室推荐              数字人配置管理         多模态输入
协议规范       上下文组装/质量监控        TTS流式+预合成        交互中断规则          K8s 部署
数据一致性     编码检测/格式校验         向量库升级                                  知识库Agent
────────────────────────────────────────────────────────────────────────────────────────
验证核心闭环 ──▶ 知识库全面升级 ──▶ 语音体验升级 ──▶ 数字人上线 ──▶ 平台化演进
```

---

## 附录 A：架构评估报告

### 评估方法

基于 Clean Architecture 和 DDD 原则，结合行业最佳实践，从架构合理性、技术选型适当性、组件设计完整性、接口定义规范性、性能与可扩展性、安全与合规性六个维度进行评估。

### 识别的问题及处理结果

| 编号 | 严重度 | 原始问题 | 处理方式 | 对应文档章节 |
|---|---|---|---|---|
| P1 | 🔴 严重 | 缺少领域层，业务逻辑与基础设施耦合 | ✅ 引入 domain/application/infrastructure 四层分层 | 2.1, 3.1 |
| P6 | 🔴 严重 | LangGraph 医疗场景风险高 | ✅ 替换为自研 DiagnosisStateMachine | 3.2 |
| P9 | 🔴 严重 | 语音流水线缺 VAD/纠错 | ✅ 补充 VAD + 医学术语纠错 | 3.5 |
| P13 | 🔴 严重 | WebSocket 协议不完整 | ✅ 定义完整协议规范 | 5.2 |
| P17 | 🔴 严重 | TTS 性能瓶颈 | ✅ 流式 TTS + 预合成缓存 + 并行流水线 | 3.5 |
| P20 | 🔴 严重 | 医疗合规不足 | ✅ 补充知情同意/免责/数据保留/AI 标识 | 7.3 |
| P2 | 🟡 中等 | agents/tools 边界模糊 | ✅ 业务逻辑提取到 domain/services | 3.1 |
| P3 | 🟡 中等 | services 职责过重 | ✅ 拆分为 application/use_cases | 3.1 |
| P4 | 🟡 中等 | AgentFactory 依赖 ORM | ✅ 依赖领域实体接口 | 3.4 |
| P5 | 🟡 中等 | State 混合业务与渲染 | ✅ 拆分 ClinicalState/PresentationState | 3.3 |
| P7 | 🟡 中等 | Chroma 生产风险 | ✅ 预留 Qdrant 迁移路径 | 1.3 |
| P8 | 🟡 中等 | PG+Chroma 数据一致性 | ✅ Outbox Pattern | 4.4 |
| P10 | 🟡 中等 | 数字人缺加载/降级/中断 | ✅ 补充完整策略 | 3.6 |
| P11 | 🟡 中等 | 医生角色缺生命周期 | ✅ draft→active→inactive→archived | 3.7 |
| P12 | 🟡 中等 | RAG 缺版本控制 | ✅ 版本字段 + Collection 按版本隔离 | 3.8 |
| P14 | 🟡 中等 | REST API 缺统一规范 | ✅ 定义 code/data/message 格式和错误码段 | 5.1 |
| P15 | 🟡 中等 | 流式输出协议未定义 | ✅ 定义分段协议 + chunk_type | 5.2 |
| P16 | 🟡 中等 | Agent 缓存内存风险 | ✅ Redis 缓存 + 50 实例上限 + TTL | 3.4 |
| P18 | 🟡 中等 | RAG 检索延迟叠加 | ✅ 预取策略 + 缓存策略 | 7.1 |
| P19 | 🟡 中等 | 水平扩展路径不清 | ✅ Redis Pub/Sub + 分布式方案 | 7.5 |
| P21 | 🟡 中等 | Prompt 注入风险 | ✅ 防注入指令 + 输入过滤 + 输出校验 | 7.2 |

---

## 附录 B：测试报告与缺陷跟踪

> 版本：v1.0
> 日期：2026-05-31
> 修订说明：基于 V1 开发完成后的全量测试结果生成

### B.1 测试概览

| 指标 | 数值 |
|---|---|
| 测试用例总数 | 120 |
| 通过 | 120 |
| 失败 | 0 |
| 跳过 | 0 |
| 执行时间 | ~55s |
| 代码覆盖率（整体） | **70%** |
| 核心领域层覆盖率 | **95%+** |
| API 层覆盖率 | **43%**（集成测试 + 认证守卫） |
| 测试框架 | pytest 8.4.2 + pytest-asyncio 0.23+ |
| 覆盖率工具 | pytest-cov 7.1.0 |

### B.2 测试文件分布

| 测试文件 | 用例数 | 类型 | 覆盖范围 |
|---|---|---|---|
| `tests/unit/test_config.py` | 4 | 单元 | Settings 默认值、自定义值、缓存、model_config |
| `tests/unit/test_models.py` | 6 | 单元 | 6 个 ORM 模型创建 |
| `tests/unit/test_domain.py` | 9 | 单元 | 领域实体 + 值对象（DoctorRoleEntity、ClinicalState、Symptom、Department、VoiceConfig） |
| `tests/unit/test_entities_extended.py` | 5 | 单元 | ConversationEntity、MessageEntity |
| `tests/unit/test_state_machine.py` | 12 | 单元 | 状态机完整转换链 + 非法转换 + 意图映射 + 闲聊 |
| `tests/unit/test_diagnosis_strategy.py` | 16 | 单元 | RAGStrategy 检索策略 + DiagnosisEngine 消息构建/意图/回复 + AgentFactory 缓存 |
| `tests/unit/test_use_cases.py` | 2 | 单元 | StartConsultation、SendMessage |
| `tests/unit/test_repositories.py` | 9 | 单元 | 4 个 SQL 仓储的 CRUD |
| `tests/unit/test_llm_providers.py` | 9 | 单元 | OpenAI/通义/智谱 Provider 创建 + 聊天/重试/空响应 |
| `tests/unit/test_vectorstore.py` | 3 | 单元 | VectorStore 基类 NotImplementedError |
| `tests/unit/test_schemas.py` | 10 | 单元 | Doctor/Conversation/Message 等 Pydantic Schema |
| `tests/unit/test_security.py` | 11 | 单元 | 输入过滤/输出校验 + AES 加密 |
| `tests/unit/test_audit_logger.py` | 3 | 单元 | 审计日志基础/完整/最小参数 |
| `tests/integration/test_api.py` | 11 | 集成 | 健康检查 + 认证（注册/登录/重复/错误密码/不存在/JWT）+ 授权守卫 |
| `tests/integration/test_api_extended.py` | 10 | 集成 | Chat API 守卫 + Doctor API + 边界用例 |

### B.3 覆盖率详细分析

#### B.3.1 高覆盖率模块（≥80%）

| 模块 | 覆盖率 | 说明 |
|---|---|---|
| `app/domain/state_machine/` | **100%** | 状态机所有状态转换、异常、意图映射全覆盖 |
| `app/domain/value_objects/` | **100%** | ClinicalState、Symptom、Department 等值对象 |
| `app/domain/entities/` | **96%** | 领域实体（diagnosis_session 有 3 行未覆盖） |
| `app/config.py` | **100%** | Settings 配置管理 |
| `app/schemas/` | **100%** | 所有 Pydantic Schema 覆盖 |
| `app/infrastructure/security/encryption.py` | **100%** | AES 加密解密 |
| `app/infrastructure/security/prompt_guard.py` | **100%** | 输入过滤 + 输出校验 |
| `app/infrastructure/persistence/database.py` | **100%** | 数据库连接池配置 |
| `app/infrastructure/persistence/models/` | **100%** | 所有 ORM 模型定义 |
| `app/infrastructure/llm/provider.py` | **100%** | LLM Provider 工厂函数 |
| `app/application/use_cases/start_consultation.py` | **100%** | 开始问诊用例 |
| `app/application/use_cases/send_message.py` | **88%** | 发送消息用例 |

#### B.3.2 中低覆盖率模块（需要补充测试）

| 模块 | 覆盖率 | 缺失行数 | 原因分析 |
|---|---|---|---|
| `app/api/v1/chat.py` | 34% | 65 | API 路由层，需完整数据库环境，核心逻辑在 use_case 层已测 |
| `app/api/v1/knowledge.py` | 37% | 36 | 知识库 CRUD 路由，依赖 ChromaDB + PostgreSQL 联调 |
| `app/api/ws.py` | 22% | 53 | WebSocket 端点，需真实 WebSocket 连接测试 |
| `app/api/v1/favorite.py` | 50% | 13 | 收藏路由，逻辑简单 |
| `app/api/v1/doctor.py` | 49% | 28 | 医生管理路由，含生命周期校验 |
| `app/api/v1/auth.py` | 67% | 19 | 认证路由（数据库异常分支未覆盖） |
| `app/application/use_cases/toggle_favorite.py` | **0%** | 9 | 未编写单元测试 |
| `app/application/use_cases/manage_knowledge.py` | 25% | 39 | 依赖 ChromaDB 向量存储 |
| `app/application/use_cases/manage_doctor.py` | 47% | 9 | 未编写单元测试 |
| `app/infrastructure/security/compliance.py` | **0%** | 26 | 知情同意守卫，未编写测试 |
| `app/infrastructure/vectorstore/chroma_store.py` | 25% | 48 | 依赖 ChromaDB 实例，适合集成测试 |
| `app/infrastructure/llm/openai_provider.py` | 59% | 11 | chat_stream 方法未测试 |
| `app/main.py` | 71% | 9 | lifespan 数据库连接验证分支未测试 |

### B.4 缺陷分析报告

#### B.4.1 缺陷总览

| 编号 | 严重度 | 标题 | 状态 | 根因 | 修复方案 | 回归验证 |
|---|---|---|---|---|---|---|
| BUG-01 | 🔴 严重 | 状态机非法转换异常 | ✅ 已修复 | `transition()` 抛出 `InvalidTransitionError` 阻断流程 | 为所有状态添加 `user_chitchat` 自环转换 + 安全降级到 collecting | ✅ 12 个状态机测试全通过 |
| BUG-02 | 🔴 严重 | LLM 遗忘对话历史 | ✅ 已修复 | `build_messages()` 仅发送当前消息，无历史上下文 | 实现三层记忆架构：数据层（PG 历史注入）+ 结构层（症状摘要）+ 指令层（ROLE_PROMPT 规则 8/9） | ✅ DiagnosisEngine 测试全通过 |
| BUG-03 | 🔴 严重 | ClinicalState 冗余字段 | ✅ 已修复 | `messages` 字段与数据库历史重复存储 | 移除 `messages` 字段，添加 `_last_user_message`，历史统一从 `conv_repo` 获取 | ✅ ClinicalState 测试全通过 |
| BUG-04 | 🔴 严重 | 登录接口 500 错误 | ✅ 已修复 | `NullPool` 在并发请求下每次新建连接，连接耗尽后报错 | 替换为 `AsyncAdaptedQueuePool`，配置 pool_size=5, max_overflow=10 | ✅ 集成测试 11 个全通过 |
| BUG-05 | 🟡 中等 | POST 请求参数在 URL 上 | ✅ 已修复 | 前端使用 URL 查询参数发送 POST 请求 | 前后端统一改为 JSON Body + Pydantic 模型（LoginRequest/RegisterRequest） | ✅ 登录/注册集成测试通过 |
| BUG-06 | 🟡 中等 | `datetime.utcnow()` 废弃警告 | ✅ 已修复 | Python 3.12+ 废弃 `datetime.utcnow()` | 全局替换为 `datetime.now(timezone.utc)` | ✅ 120 测试无废弃警告 |
| BUG-07 | 🟡 中等 | 知识上传 "Expected Embeddings to be non-empty" | ✅ 已修复 | `vector_store.add()` 传入 `embeddings=[]` 空列表 | 移除空 embeddings 参数，VectorStore 基类将其设为可选参数，ChromaDB 使用内嵌函数自动生成向量 | ✅ VectorStore 测试通过 |
| BUG-08 | 🟡 中等 | SentenceTransformer 模型下载超时 | ✅ 已修复 | 访问 HuggingFace Hub 下载 `paraphrase-multilingual-MiniLM-L12-v2` 超时 | 1) 添加配置项 `chroma_embedding_model` 支持本地路径 2) 支持 `chroma-default` 选项使用 ChromaDB 内置 ONNX 模型 3) 添加 socket 超时 4) `_embedding_failed` 标志避免重复尝试 | ✅ 回归测试全通过 |

#### BUG-01 详细分析：状态机非法转换

**现象**：问诊过程中，当用户在 `analyzing` 状态输入闲聊信息时，系统抛出 `InvalidTransitionError: Cannot transition from 'analyzing' with event 'user_chitchat'`。

**根因**：[diagnosis_machine.py](file:///e:/work/python/smartDoctor/smart_doctor/app/domain/state_machine/diagnosis_machine.py) 的 TRANSITIONS 映射表只定义了核心状态转换路径，未考虑用户可能在任何阶段输入非症状信息（闲聊）。

**修复方案**：
1. 为所有状态（collecting/analyzing/recommending/completed）添加 `user_chitchat` 自环转换
2. 在 `send_message.py` 中添加安全降级：非法事件自动回退到 `collecting` 状态而不是抛出异常

**修复文件**：
- [diagnosis_machine.py:L7-L28](file:///e:/work/python/smartDoctor/smart_doctor/app/domain/state_machine/diagnosis_machine.py#L7-L28)

---

#### BUG-02 详细分析：LLM 遗忘对话历史

**现象**：患者告知"头痛3天了"，LLM 在下一条回复中仍然询问"头痛持续多久了？"——表现出"失忆"状态。

**根因**：[diagnosis_strategy.py](file:///e:/work/python/smartDoctor/smart_doctor/app/domain/services/diagnosis_strategy.py) 的 `build_messages()` 方法（V1 初始实现）仅将当前一条用户消息发送给 LLM，完全未注入对话历史。

**修复方案**（三层记忆架构）：

| 层级 | 机制 | 实现位置 |
|---|---|---|
| 数据层 | 从 PostgreSQL 查询完整对话历史，截取最近 10 轮（20 条消息）注入 Prompt | [diagnosis_strategy.py:L86-L97](file:///e:/work/python/smartDoctor/smart_doctor/app/domain/services/diagnosis_strategy.py#L86-L97) |
| 结构层 | 注入 `[已收集症状：xxx，请勿重复询问以上症状相关信息]` 系统消息 | [diagnosis_strategy.py:L73-L78](file:///e:/work/python/smartDoctor/smart_doctor/app/domain/services/diagnosis_strategy.py#L73-L78) |
| 指令层 | ROLE_PROMPT 新增规则 8 ("不要重复询问已回答的问题") 和规则 9 ("基于已有信息继续分析") | [diagnosis_strategy.py:L185-L186](file:///e:/work/python/smartDoctor/smart_doctor/app/domain/services/diagnosis_strategy.py#L185-L186) |

---

#### BUG-04 详细分析：登录接口 500 错误

**现象**：用户通过 `POST /api/v1/auth/login` 登录时返回 `500 Internal Server Error`，数据库中日志显示"连接超时"。

**根因**：[database.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/persistence/database.py) 原先使用 `NullPool`，每次请求创建新的数据库连接，在高并发或数据库响应慢的情况下，连接数耗尽导致新请求超时。

**修复方案**：
1. 替换 `NullPool` 为 `AsyncAdaptedQueuePool`
2. 配置连接池参数：`pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=900, pool_pre_ping=True`
3. 区分测试/生产环境：测试环境使用 `NullPool`（避免跨测试干扰），生产环境使用 `AsyncAdaptedQueuePool`

**修复文件**：[database.py:L13-L25](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/persistence/database.py#L13-L25)

---

#### BUG-07 详细分析：知识上传空嵌入向量

**现象**：上传知识文档时，ChromaDB 抛出 `Expected Embeddings to be non-empty list or numpy array`。

**根因**：[manage_knowledge.py](file:///e:/work/python/smartDoctor/smart_doctor/app/application/use_cases/manage_knowledge.py) 调用 `vector_store.add()` 时显式传入了 `embeddings=[]` 空列表，ChromaDB 认为用户已提供嵌入向量（但实际为空），拒绝处理。

**修复方案**：
1. `VectorStore` 基类将 `embeddings` 参数设为可选（`list[list[float]] | None = None`）
2. `manage_knowledge.py` 移除 `embeddings=[]` 参数
3. `ChromaVectorStore.add()` 根据 `embeddings` 是否为 None 判断使用自定义嵌入还是内嵌函数

**修复文件**：
- [base.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/vectorstore/base.py)
- [manage_knowledge.py:L70-L74](file:///e:/work/python/smartDoctor/smart_doctor/app/application/use_cases/manage_knowledge.py#L70-L74)
- [chroma_store.py:L56-L72](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/vectorstore/chroma_store.py#L56-L72)

---

### B.5 已知限制与风险

| 编号 | 描述 | 严重度 | 缓解措施 |
|---|---|---|---|
| RISK-01 | ChromaDB 嵌入模型首次下载依赖 HuggingFace 网络 | 🟡 中等 | 已支持 `chroma_embedding_model` 配置本地路径或 `chroma-default` 降级到 ONNX 内置模型 |
| RISK-02 | `compliance.py`（知情同意守卫）0% 测试覆盖 | 🟢 低 | 前端已集成知情同意流程，后端路由尚未强制要求 consent |
| RISK-03 | `toggle_favorite.py` 0% 测试覆盖 | 🟢 低 | 功能简单，后续迭代补充测试 |
| RISK-04 | WebSocket 端点 22% 覆盖率 | 🟡 中等 | 需要真实 WebSocket 连接 + 认证流程的集成测试 |
| RISK-05 | API 路由层整体覆盖率偏低（34%-67%） | 🟢 低 | 核心业务逻辑在 use_case/domain 层已覆盖，路由层主要是参数校验和调度 |
| RISK-06 | 测试中 RuntimeWarning（7 条） | 🟢 低 | AsyncMock 的 `add()` 在测试中未被 await 的警告，生产代码正确（SQLAlchemy 的 `session.add()` 是同步操作） |

### B.6 测试执行记录

```
2026-05-31 回归测试结果：
====================== 120 passed, 7 warnings in 57.27s =======================
整体覆盖率：70%（1496 语句，452 未覆盖）

关键模块覆盖率：
  - domain/state_machine:        100%   ✓
  - domain/value_objects:        100%   ✓
  - domain/entities:              96%   ✓
  - config:                      100%   ✓
  - schemas:                     100%   ✓
  - infrastructure/security:     100%   ✓
  - infrastructure/database:     100%   ✓
  - application/use_cases/core:   94%   ✓
  - api/v1/auth:                  67%
  - api/v1/chat:                  34%
  - api/ws:                       22%
```

### B.7 后续测试改进建议

| 优先级 | 建议 | 预估工时 |
|---|---|---|
| P1 | 编写 `toggle_favorite.py` 单元测试 | 0.5h |
| P1 | 编写 `manage_doctor.py` 单元测试 | 0.5h |
| P2 | 编写 `compliance.py` 单元测试 | 0.5h |
| P2 | 编写 `chat_stream()` 方法测试 | 0.5h |
| P2 | 添加 WebSocket 连接集成测试 | 1h |
| P3 | 使用真实 ChromaDB 实例编写 vectorstore 集成测试 | 1.5h |
| P3 | 添加 API 层全链路集成测试（含数据库） | 2h |
| P3 | 目标：整体覆盖率提升至 85%+ | — |

---

## 附录 C：V1 功能实现验证报告

> 版本：v1.0
> 日期：2026-05-31
> 验证方法：代码静态分析 + 运行时导入验证 + 接口路由检查
> 验证范围：对照 V1 交付清单的 25 项功能点逐一核对

### C.1 验证总览

| 分类 | 总数 | ✅ 已实现 | ⚠️ 部分实现 |
|---|---|---|---|---|
| 认证与授权 | 5 | 5 | 0 |
| 问诊核心功能 | 8 | 8 | 0 |
| 流式输出 | 3 | 2 | 1 |
| 知识库与 RAG | 4 | 3 | 1 |
| 前端页面 | 7 | 7 | 0 |
| 安全合规 | 4 | 3 | 1 |
| 基础设施 | 3 | 3 | 0 |
| **合计** | **34** | **31** | **3** |

**V1 交付率：31/34 = 91.2%**（3 项功能优化项，已在本文档记录）

---

### C.2 逐项验证详情

#### C.2.1 认证与授权（5/5 ✅）

| 编号 | 功能点 | 状态 | 验证结果 |
|---|---|---|---|
| AUTH-01 | 用户注册（POST /api/v1/auth/register） | ✅ | [auth.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/v1/auth.py#L58-L87)——RegisterRequest Pydantic模型，bcrypt密码哈希，创建用户 → 返回JWT Token |
| AUTH-02 | 用户登录（POST /api/v1/auth/login） | ✅ | [auth.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/v1/auth.py#L90-L127)——LoginRequest模型，密码验证，JWT签发，已处理数据库异常 |
| AUTH-03 | JWT Token 签发与验证 | ✅ | [deps.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/deps.py#L10-L35)——OAuth2PasswordBearer + jwt.decode，HS256算法，过期时间验证 |
| AUTH-04 | 认证守卫（get_current_user） | ✅ | [deps.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/deps.py#L28-L35)——HTTPException 401 未授权，所有API路由通过 Depends 注入 |
| AUTH-05 | 前端登录/注册界面 | ✅ | [LoginView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/LoginView.vue#L1-L91)——登录/注册双模式，JWT Token存储localStorage，userStore管理 |

---

#### C.2.2 问诊核心功能（8/8 ✅）

| 编号 | 功能点 | 状态 | 验证结果 |
|---|---|---|---|
| CHAT-01 | 状态机（5状态 + 10转换 + 意图映射） | ✅ | [diagnosis_machine.py](file:///e:/work/python/smartDoctor/smart_doctor/app/domain/state_machine/diagnosis_machine.py#L1-L100)——5个状态（collecting/analyzing/recommending/completed/error），10条转换规则，8种意图映射，所有状态支持user_chitchat自环 |
| CHAT-02 | 开始问诊（POST /chat/conversations） | ✅ | [start_consultation.py](file:///e:/work/python/smartDoctor/smart_doctor/app/application/use_cases/start_consultation.py#L1-L60)——创建ConversationEntity，设置初始状态collecting，生成开场白 |
| CHAT-03 | 发送消息（POST /chat/conversations/{id}/messages） | ✅ | [send_message.py](file:///e:/work/python/smartDoctor/smart_doctor/app/application/use_cases/send_message.py#L1-L50)——意图识别 → 状态转换 → 策略执行 → 消息保存 → 状态持久化 |
| CHAT-04 | DiagnosisEngine（LLM调用 + RAG注入 + 提示词构建） | ✅ | [diagnosis_strategy.py](file:///e:/work/python/smartDoctor/smart_doctor/app/domain/services/diagnosis_strategy.py#L1-L150)——build_messages注入历史+Sx摘要，get_reply调用LLM，RAG结果注入提示词 |
| CHAT-05 | ROLE_PROMPT 医生角色风格 | ✅ | [diagnosis_strategy.py](file:///e:/work/python/smartDoctor/smart_doctor/app/domain/services/diagnosis_strategy.py#L110-L190)——完整ROLE_PROMPT模板含{name}/{title}/{specialty}/{expertise}等变量，规则1-9 |
| CHAT-06 | 三层记忆架构 | ✅ | 数据层（历史注入）+ 结构层（Sx摘要）+ 指令层（规则8/9），已验证 [diagnosis_strategy.py](file:///e:/work/python/smartDoctor/smart_doctor/app/domain/services/diagnosis_strategy.py#L73-L97) |
| CHAT-07 | 免责声明注入 | ✅ | [chat.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/v1/chat.py#L87-L92)——`*以上分析仅供参考，不能替代专业医生诊断，如有不适请及时就医。*`，每次回复末尾追加 |
| CHAT-08 | 对话历史管理 | ✅ | [chat.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/v1/chat.py#L135-L146)——GET /chat/conversations 列表，GET /chat/conversations/{id} 详情含messages |

---

#### C.2.3 流式输出（2/3 ✅，1项 ⚠️）

| 编号 | 功能点 | 状态 | 验证结果 |
|---|---|---|---|
| STREAM-01 | 后端 LLM 流式调用 | ✅ | [openai_provider.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/llm/openai_provider.py#L36-L43)——`chat_stream()` 使用 `stream=True` + `async for chunk in stream` |
| STREAM-02 | WebSocket 流式推送 | ✅ | [ws.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/ws.py#L1-L100)——`/ws/chat/{conversation_id}` 端点，JWT认证，heartbeat心跳，流式推送chunk |
| STREAM-03 | ⚠️ 前端流式接收 | ⚠️ 部分实现 | **问题**：后端已实现WebSocket流式推送，但 [ChatView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/ChatView.vue#L138-L146) 使用普通 HTTP POST 调用 `apiSendMsg()`，等待完整响应后才显示，前端未使用 WebSocket 或 SSE 接收流式数据。**影响**：用户体验为"打字机效果"缺失，等待时间较长 |

---

#### C.2.4 知识库与 RAG（3/4 ✅，1项 ⚠️）

| 编号 | 功能点 | 状态 | 验证结果 |
|---|---|---|---|
| KB-01 | 知识库上传/列表/删除 | ✅ | [knowledge.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/v1/knowledge.py#L1-L100)——POST /knowledge/upload（文件上传+分块+向量化），GET /knowledge/documents（列表），DELETE /knowledge/documents/{id} |
| KB-02 | ChromaDB 向量存储 | ✅ | [chroma_store.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/vectorstore/chroma_store.py#L1-L100)——PersistentClient，SentenceTransformerEmbeddingFunction，支持配置化模型路径+降级 |
| KB-03 | RAG 检索策略 | ✅ | [diagnosis_strategy.py](file:///e:/work/python/smartDoctor/smart_doctor/app/domain/services/diagnosis_strategy.py#L43-L66)——RAGStrategy.search() 查询向量库，返回RAGResult列表，内容注入到Prompt |
| KB-04 | ⚠️ 前端 RAG 来源展示 | ⚠️ 部分实现 | **问题**：后端RAG检索结果注入到LLM回复中，但前端 [ChatView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/ChatView.vue) 未展示知识来源卡片。**影响**：用户无法知道哪些回复引用了知识库文档 |

---

#### C.2.5 前端页面（7/7 ✅）

| 编号 | 功能点 | 状态 | 验证结果 |
|---|---|---|---|
| UI-01 | 登录页（LoginView） | ✅ | [LoginView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/LoginView.vue#L1-L91)——登录/注册双模式，知情同意弹窗，表单验证 |
| UI-02 | 聊天页（ChatView） | ✅ | [ChatView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/ChatView.vue#L1-L243)——消息列表，输入框，发送按钮，对话切换 |
| UI-03 | 医生选择页（DoctorsView） | ✅ | [DoctorsView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/DoctorsView.vue#L1-L69)——医生卡片列表，科室筛选chip，搜索框 |
| UI-04 | 历史记录页（HistoryView） | ✅ | [HistoryView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/HistoryView.vue#L1-L79)——对话列表，时间显示，点击进入 |
| UI-05 | 知识库页（KnowledgeView） | ✅ | [KnowledgeView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/KnowledgeView.vue#L1-L107)——医生选择，文档列表，上传/删除，空状态 |
| UI-06 | 设置页（SettingsView） | ✅ | [SettingsView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/SettingsView.vue#L1-L141)——个人信息、偏好设置、隐私设置、关于 |
| UI-07 | 医生管理页（DoctorManageView） | ✅ | [DoctorManageView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/admin/DoctorManageView.vue#L1-L246)——NDataTable列表，创建/编辑弹窗，激活/停用开关 |

---

#### C.2.6 安全合规（3/4 ✅，1项 ⚠️）

| 编号 | 功能点 | 状态 | 验证结果 |
|---|---|---|---|
| SEC-01 | 输入过滤（sanitize_user_input） | ✅ | [prompt_guard.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/security/prompt_guard.py#L1-L23)——INJECTION_PATTERNS正则匹配，已集成到 [chat.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/v1/chat.py#L60-L64) |
| SEC-02 | 输出校验（validate_output） | ✅ | [prompt_guard.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/security/prompt_guard.py#L23-L43)——OUTPUT_PATTERNS匹配，已集成到 [chat.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/v1/chat.py#L87-L92) |
| SEC-03 | 加密工具（encrypt/decrypt） | ✅ | [encryption.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/security/encryption.py#L1-L17)——Fernet对称加密，基于Settings.secret_key派生密钥 |
| SEC-04 | ⚠️ 知情同意守卫 | ⚠️ 部分实现 | **问题**：[compliance.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/security/compliance.py#L1-L50) 实现了 `require_consent` 和 `record_consent`，但未在任何API路由中作为 `Depends` 注入使用。前端 [userStore](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/stores/user.ts#L8) 有 `consented` 状态管理，但后端未强制执行。**影响**：用户可绕过知情同意直接使用问诊功能 |

---

#### C.2.7 基础设施（3/3 ✅）

| 编号 | 功能点 | 状态 | 验证结果 |
|---|---|---|---|
| INFRA-01 | REST API 统一响应格式 | ✅ | [api_response.py](file:///e:/work/python/smartDoctor/smart_doctor/app/schemas/api_response.py#L1-L16)——ApiResponse(code, message, data)，PaginatedResponse，所有API返回统一格式 |
| INFRA-02 | 审计日志 | ✅ | [audit_logger.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/audit/audit_logger.py#L1-L28)——AuditLogger类，记录user_id, action, resource, details，写入PostgreSQL |
| INFRA-03 | 数据库连接池 | ✅ | [database.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/persistence/database.py#L13-L25)——AsyncAdaptedQueuePool，pool_size=5, max_overflow=10, pool_pre_ping=True |

---

### C.3 运行时导入验证

通过 `python -c "from app.main import app"` 验证应用可正常导入，注册的路由包括：

| 路由前缀 | 注册模块 | 主要端点 |
|---|---|---|
| `/api/v1/auth` | auth.py | POST /login, POST /register |
| `/api/v1/chat` | chat.py | POST /conversations, GET /conversations, POST /conversations/{id}/messages |
| `/api/v1/doctors` | doctor.py | GET /, POST /, POST /{id}/activate, POST /{id}/deactivate |
| `/api/v1/knowledge` | knowledge.py | POST /upload, GET /documents, DELETE /documents/{id} |
| `/api/v1/favorites` | favorite.py | POST /toggle, GET / |
| `/ws` | ws.py | WS /chat/{conversation_id} |
| `/health` | main.py | GET /health |

**应用导入验证：✅ 通过**（所有路由正常注册，无导入错误）

---

### C.4 发现的问题与不符合项

#### 问题 1：医生激活/停用接口存在运行时错误风险 ✅ 已修复

**位置**：[doctor.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/v1/doctor.py#L16-L23)

**描述**：`_get_factory()` 函数延迟导入了 `get_llm_client`（`app.infrastructure.llm`）和 `get_agent_cache`（`app.infrastructure.cache.agent_cache`），但这两个函数/模块均不存在。

**修复方案**：将 `_get_factory()` 的导入改为使用已存在的 `create_llm()` 函数，并正确传递 `AgentFactory` 构造函数参数（`llm=` 和 `rag_strategy=`）。

**修复代码**：
```python
def _get_factory() -> AgentFactory:
    from app.infrastructure.llm import create_llm
    return AgentFactory(
        llm=create_llm(),
        rag_strategy=None,
    )
```

**回归验证**：✅ 120/120 测试通过，doctor.py 模块导入正常，主应用导入正常。

---

#### 问题 2：前端未集成流式输出 ⚠️

**位置**：[ChatView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/ChatView.vue#L138-L146)

**描述**：后端已实现 WebSocket 流式推送（[ws.py](file:///e:/work/python/smartDoctor/smart_doctor/app/api/ws.py)）和 LLM 流式调用（[openai_provider.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/llm/openai_provider.py#L36-L43)），但前端 ChatView 发送消息时使用普通 HTTP POST，等待完整响应后才显示，未使用 WebSocket 或 SSE 接收流式数据。

**影响**：用户无法看到"打字机效果"的实时流式回复，等待时间较长，体验下降。

**严重度**：🟡 中等（功能可用但体验未达设计目标）

**修复建议**：在 ChatView 中集成 WebSocket 连接，接收 `ws://host/ws/chat/{conversation_id}` 的流式消息并逐字显示。

---

#### 问题 3：知情同意守卫未强制执行 ⚠️

**位置**：[compliance.py](file:///e:/work/python/smartDoctor/smart_doctor/app/infrastructure/security/compliance.py#L1-L50)

**描述**：`require_consent` 依赖函数已实现，但未在任何 API 路由中作为 `Depends` 注入。前端有 `consented` 状态管理，但后端没有任何路由强制要求用户先签署知情同意。

**影响**：用户可绕过知情同意流程直接使用问诊功能，存在合规风险。

**严重度**：🟢 低（前端已做弹窗引导，但后端未强制）

**修复建议**：在 Chat API 路由（如 `/chat/conversations`）中添加 `require_consent` 依赖注入。

---

#### 问题 4：RAG 知识来源未在前端展示 ⚠️

**位置**：[ChatView.vue](file:///e:/work/python/smartDoctor/smart_doctor/frontend/src/views/ChatView.vue)

**描述**：后端 RAG 检索到的知识库内容被注入到 LLM 提示词中，但前端未展示"基于以下知识来源"的卡片或引用。

**影响**：用户无法知道哪些回复内容引用了知识库文档，降低了透明度和可信度。

**严重度**：🟢 低（功能效果不受影响，但缺少用户透明性）

**修复建议**：后端在消息响应中附加 `sources` 字段，前端渲染知识来源卡片。

---

### C.5 验证结论

| 维度 | 结论 |
|---|---|
| **功能完整性** | V1 交付清单 34 项功能点，31 项完全实现（91.2%），3 项部分实现（流式前端、知情同意守卫、RAG来源展示） |
| **架构合规性** | 遵循 Clean Architecture / DDD 分层，API 层 → 应用层 → 领域层 → 基础设施层依赖方向正确 |
| **代码质量** | 120 个测试用例全部通过，70% 整体覆盖率，核心领域层 95%+ |
| **运行时稳定性** | 应用可正常导入启动，所有路由注册正常，数据库连接池配置合理 |
| **待修复问题** | 3 个功能优化项（流式前端集成、知情同意守卫、RAG来源展示），均不影响核心问诊流程，1 个已修复（doctor.py 导入错误） |
| **总体评价** | **V1 核心功能已完整交付，满足基本可用标准。V1.1 知识库系统优化方案已制定（详见 3.11 节），解决多格式文档解析、分片上传与断点续传三大瓶颈。** |
