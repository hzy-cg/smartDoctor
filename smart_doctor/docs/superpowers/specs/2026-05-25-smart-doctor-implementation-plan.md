# SmartDoctor V1 实施计划

> 对应设计文档：2026-05-25-smart-doctor-design.md v2.2
> 计划日期：2026-05-25
> 最后修订：2026-06-07（新增阶段六：知识库系统优化，含检索增强）

## 总览

V1 目标：跑通"选择医生 → 文字问诊 → RAG 增强 → 回复"的核心闭环。

分为 **5 个阶段、22 个任务**，按依赖关系顺序执行。每个任务标注预估工时（人天）和验收标准。

---

## 阶段一：项目骨架搭建（1-2 天）

本阶段搭建后端和前端的基础骨架，确保项目可编译、可运行、可连接数据库。

### 任务 1.1：后端项目初始化

| 项 | 内容 |
|---|---|
| 文件 | `pyproject.toml`, `app/main.py`, `app/config.py` |
| 工时 | 0.5 天 |
| 依赖 | 无 |

**内容**：
- 创建 `pyproject.toml`，定义依赖：fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic, python-jose, passlib, redis, chromadb, openai, httpx
- 创建 `app/main.py`：FastAPI 应用入口，CORS 配置
- 创建 `app/config.py`：基于 pydantic-settings 的配置管理，读取 .env
- 创建 `.env.example`
- 验证：`uvicorn app.main:app --reload` 可启动

**验收**：`curl http://localhost:8000/docs` 可见 Swagger 文档页

---

### 任务 1.2：数据库初始化

| 项 | 内容 |
|---|---|
| 文件 | `app/infrastructure/persistence/database.py`, Alembic 配置 |
| 工时 | 0.5 天 |
| 依赖 | 任务 1.1 |

**内容**：
- 创建 `app/infrastructure/persistence/database.py`：异步 SQLAlchemy 引擎 + Session 工厂
- 配置 Alembic：`alembic init migrations`
- 创建初始迁移（空）
- 验证：`alembic upgrade head` 成功

**验收**：数据库迁移可正常执行

---

### 任务 1.3：前端项目初始化

| 项 | 内容 |
|---|---|
| 文件 | Vue3 脚手架完整项目 |
| 工时 | 0.5 天 |
| 依赖 | 无 |

**内容**：
- `npm create vite@latest frontend -- --template vue-ts`
- 安装依赖：naive-ui, pinia, vue-router, axios, markdown-it
- 配置 vite.config.ts（代理 /api 到后端）
- 创建基础路由：`/login`, `/chat`, `/doctors`, `/knowledge`, `/history`
- 验证：`npm run dev` 可启动，页面可访问

**验收**：前端开发服务器正常启动，路由跳转正常

---

## 阶段二：领域层 + 基础设施层（3-4 天）

本阶段实现 Clean Architecture 的核心：领域实体、仓储接口、ORM 模型、仓储实现。这是架构的根基。

### 任务 2.1：定义所有 ORM 模型

| 项 | 内容 |
|---|---|
| 文件 | `app/infrastructure/persistence/models/*.py` |
| 工时 | 1 天 |
| 依赖 | 任务 1.2 |

**内容**：
- 创建所有 SQLAlchemy 模型：User, Conversation, Message, DoctorRole, DigitalHuman, KnowledgeDoc, DoctorKnowledge, Department, Favorite, AuditLog, OutboxEvent
- 按设计文档中的表结构定义字段、类型、约束、索引
- 生成 Alembic 迁移并执行
- 验证：`alembic upgrade head` 所有表创建成功

**验收**：数据库中所有表结构正确创建

---

### 任务 2.2：定义领域实体和值对象

| 项 | 内容 |
|---|---|
| 文件 | `app/domain/entities/*.py`, `app/domain/value_objects/*.py` |
| 工时 | 0.5 天 |
| 依赖 | 任务 2.1 |

**内容**：
- 创建领域实体（纯 Python dataclass/Pydantic，无 ORM 依赖）：DoctorRoleEntity, ConversationEntity, DiagnosisSession, MessageEntity, KnowledgeDocEntity
- 创建值对象：Symptom, Department, VoiceConfig, ClinicalState
- 不依赖任何外部库

**验收**：实体可独立于 ORM 创建和测试

---

### 任务 2.3：定义仓储接口（Protocol）

| 项 | 内容 |
|---|---|
| 文件 | `app/domain/repositories/*.py` |
| 工时 | 0.5 天 |
| 依赖 | 任务 2.2 |

**内容**：
- 定义 Protocol 接口：DoctorRepository, ConversationRepository, KnowledgeRepository, AuditRepository
- 每个接口定义 CRUD 方法签名（异步）

```python
class DoctorRepository(Protocol):
    async def get_by_id(self, id: str) -> DoctorRoleEntity | None: ...
    async def list_active(self, specialty: str | None, ...) -> list[DoctorRoleEntity]: ...
    async def save(self, doctor: DoctorRoleEntity) -> None: ...
    async def delete(self, id: str) -> None: ...
```

**验收**：接口定义清晰，可被 mocking 用于单元测试

---

### 任务 2.4：实现仓储

| 项 | 内容 |
|---|---|
| 文件 | `app/infrastructure/persistence/repositories/*.py` |
| 工时 | 1 天 |
| 依赖 | 任务 2.1, 2.2, 2.3 |

**内容**：
- 实现 SQL 仓储：SqlDoctorRepository, SqlConversationRepository, SqlKnowledgeRepository, SqlAuditRepository
- 实现 ORM → 领域实体 的双向转换
- 包含 Outbox 事件写入逻辑

**验收**：仓储可正确执行 CRUD，ORM 模型与领域实体转换正确

---

### 任务 2.5：实现 LLM Provider

| 项 | 内容 |
|---|---|
| 文件 | `app/infrastructure/llm/*.py` |
| 工时 | 1 天 |
| 依赖 | 任务 1.1 |

**内容**：
- 定义 LLMProvider Protocol（chat, chat_stream）
- 实现 OpenAIProvider, QwenProvider, ZhipuProvider
- 实现 create_llm 工厂函数（根据配置创建）
- 实现基础重试逻辑（3 次重试 + 指数退避）
- 验证：可调用 OpenAI API 获取回复

**验收**：`create_llm("openai", model="gpt-4o-mini")` 可正常对话

---

## 阶段三：领域服务 + 应用层（3-4 天）

本阶段实现核心业务逻辑：状态机、RAG 策略、Agent 工厂、用例编排。

### 任务 3.1：实现 DiagnosisStateMachine

| 项 | 内容 |
|---|---|
| 文件 | `app/domain/state_machine/*.py` |
| 工时 | 0.5 天 |
| 依赖 | 无（纯领域逻辑，无外部依赖） |

**内容**：
- 实现自研状态机：collecting / analyzing / recommending / completed
- 定义 TRANSITIONS 映射表
- 实现 transition() 和 can_transition() 方法
- 编写单元测试（覆盖所有合法/非法转换）

**验收**：单元测试全部通过

---

### 任务 3.2：实现 RAG 策略

| 项 | 内容 |
|---|---|
| 文件 | `app/domain/services/rag_strategy.py`, `app/infrastructure/vectorstore/` |
| 工时 | 1 天 |
| 依赖 | 任务 2.5（需要 Embedding） |

**内容**：
- 领域层 `RAGStrategy`：定义检索策略（先私有后公共，合并去重）
- 基础设施层 `ChromaVectorStore`：实现 VectorStore Protocol
- 实现文档上传 → 分块 → Embedding → 存 Chroma 流水线
- 实现查询接口
- 知识库按版本隔离：`doctor_{id}_v{version}` / `common_v{version}`
- 验证：上传一篇 PDF 后可检索到相关内容

**验收**：上传文档后可正确分块、向量化、检索

---

### 任务 3.3：实现 AgentFactory + DiagnosisEngine

| 项 | 内容 |
|---|---|
| 文件 | `app/domain/services/diagnosis_strategy.py`, `app/application/use_cases/start_consultation.py` |
| 工时 | 1 天 |
| 依赖 | 任务 3.1, 3.2, 2.4, 2.5 |

**内容**：
- 实现 `AgentFactory`：按医生角色创建 DiagnosisEngine
- 实现 `DiagnosisEngine`：组合状态机 + LLM + RAG + Prompt
- 实现 `_build_prompt()`：将医生角色属性注入 System Prompt
- 实现 Agent 缓存（V1 用字典 + LRU，V2 换 Redis）
- 实现 ClinicalState → PresentationState 的 OutputRouter
- 实现意图识别：LLM 判断用户意图 → 映射为状态机事件
- 验证：选择医生 → 发消息 → Agent 按角色风格回复

**验收**：
- 选择不同医生，AI 以不同角色风格回复
- 问诊流程按状态机推进（症状收集 → 分析 → 推荐）

---

### 任务 3.4：实现 Use Cases

| 项 | 内容 |
|---|---|
| 文件 | `app/application/use_cases/*.py` |
| 工时 | 1 天 |
| 依赖 | 任务 3.3 |

**内容**：
- `start_consultation.py`：创建对话，初始化状态机
- `send_message.py`：用户消息 → 意图识别 → 状态转换 → Agent 回复 → 持久化
- `manage_doctor.py`：医生 CRUD（含生命周期校验）
- `manage_knowledge.py`：知识库上传/删除（含版本控制）
- `toggle_favorite.py`：收藏/取消收藏

**验收**：每个 Use Case 可通过集成测试验证

---

## 阶段四：API 层 + 前端页面（3-4 天）

本阶段实现对外接口和用户界面，形成可用的产品。

### 任务 4.1：实现 API 路由

| 项 | 内容 |
|---|---|
| 文件 | `app/api/v1/*.py`, `app/api/ws.py`, `app/api/deps.py`, `app/schemas/*.py` |
| 工时 | 1.5 天 |
| 依赖 | 任务 3.4 |

**内容**：
- 实现 deps.py：依赖注入（get_db, get_current_user, get_agent_factory）
- 实现 auth.py：注册、登录、JWT 签发/验证、知情同意
- 实现 chat.py：创建对话、发送消息（SSE 流式）、历史列表
- 实现 doctor.py：列表、详情、筛选（管理员 CRUD 另行实现）
- 实现 knowledge.py：文档上传、列表、删除
- 实现 favorite.py：收藏/取消/列表
- 实现 ws.py：WebSocket 端点（认证 + 心跳 + 流式消息）
- 实现 `app/schemas/api_response.py`：统一响应格式
- 实现全局异常处理器

**验收**：
- 所有 API 在 Swagger 文档中可见
- 注册 → 登录 → 签署知情同意 → 选择医生 → 发消息 → 流式接收回复，全链路可走通

---

### 任务 4.2：前端页面开发

| 项 | 内容 |
|---|---|
| 文件 | `frontend/src/views/*.vue`, `frontend/src/components/**/*.vue` |
| 工时 | 2 天 |
| 依赖 | 任务 4.1 |

**内容**：

**4.2.1 登录页**
- 登录/注册表单
- 知情同意弹窗（首次登录后弹出）
- JWT Token 存储

**4.2.2 医生选择页**
- 医生卡片网格布局（头像/姓名/职称/评分/擅长）
- 科室筛选下拉、职称筛选、评分排序
- 收藏/取消收藏按钮
- "开始问诊"按钮 → 跳转聊天页

**4.2.3 聊天页（核心）**
- 左侧对话列表（可新建/切换/删除对话）
- 右侧聊天主区域：
  - 消息气泡（用户/AI 区分样式）
  - Markdown 渲染 AI 回复
  - RAG 来源引用卡片（可展开）
  - 科室推荐卡片
  - 免责声明标签
- 底部输入区：文字输入 + 发送按钮
- 当前医生信息展示
- 流式接收 SSE/WebSocket 消息（逐字渲染）

**4.2.4 知识库管理页**
- 文档上传组件（拖拽上传 PDF/Word/TXT）
- 文档列表（文件名/类型/状态/分块数）
- 删除按钮

**4.2.5 通用组件**
- AppHeader：导航栏
- MarkdownRenderer：Markdown 渲染
- ConsentDialog：知情同意弹窗
- DisclaimerTag：免责声明标签

**验收**：所有页面可正常渲染和交互，与后端 API 联通

---

### 任务 4.3：API + 前端联调

| 项 | 内容 |
|---|---|
| 工时 | 0.5 天 |
| 依赖 | 任务 4.1, 4.2 |

**内容**：
- 全流程走查：注册 → 登录 → 同意 → 选择医生 → 对话 → RAG 检索 → 历史
- 修复前后端对接问题
- 修复 UI 细节

**验收**：全流程无阻塞错误

---

## 阶段五：安全合规 + 测试（2-3 天）

### 任务 5.1：安全与合规实现

| 项 | 内容 |
|---|---|
| 文件 | `app/infrastructure/security/*.py`, `app/infrastructure/audit/*.py` |
| 工时 | 1 天 |
| 依赖 | 任务 4.1 |

**内容**：
- `encryption.py`：手机号 AES 加密存储
- `prompt_guard.py`：防注入系统指令 + 用户输入预处理 + 输出校验
- `compliance.py`：知情同意守卫（中间件检查 consent_given）
- `audit_logger.py`：审计日志记录（登录/对话/管理操作）
- 数据保留：conversations 设置 expires_at（默认 180 天）
- 每条诊断建议注入 DisclaimerTag

**验收**：
- 未签署知情同意的用户无法发起问诊
- 手机号在数据库中为密文
- 审计日志正常记录

---

### 任务 5.2：单元测试

| 项 | 内容 |
|---|---|
| 文件 | `tests/unit/*.py` |
| 工时 | 1 天 |
| 依赖 | 任务 3.1, 3.2, 3.3 |

**内容**：
- 状态机测试：所有合法/非法转换
- RAG 策略测试：检索顺序、合并去重
- AgentFactory 测试：角色 Prompt 注入、缓存逻辑
- OutputRouter 测试：ClinicalState → PresentationState 转换
- 仓储接口 Mock 测试

**验收**：核心领域逻辑测试覆盖率 ≥80%

---

### 任务 5.3：集成测试

| 项 | 内容 |
|---|---|
| 文件 | `tests/integration/*.py` |
| 工时 | 0.5 天 |
| 依赖 | 任务 4.3 |

**内容**：
- API 集成测试：注册 → 登录 → 创建对话 → 发送消息 → 验证回复
- 医生角色 CRUD 测试
- 知识库上传/检索测试
- 使用 httpx.AsyncClient + 测试数据库

**验收**：核心 API 链路测试通过

---

## 阶段六：知识库系统优化（V1.1，预计 7-10 天）

本阶段解决 V1 知识库上传的三大瓶颈：仅支持 txt/md 格式、大文件上传卡顿、无断点续传。详见设计文档 3.11 节。

### 任务 6.1：分片上传后端实现

| 项 | 内容 |
|---|---|
| 文件 | `app/api/v1/upload.py`, `app/schemas/upload.py`, `app/application/use_cases/manage_upload.py` |
| 工时 | 1.5 天 |
| 依赖 | 任务 1.2, 2.4 |

**内容**：
- 创建 `knowledge_uploads` 表（SQL 迁移脚本）
- 定义 Schema：`UploadInitRequest/Response`, `UploadChunkRequest`, `UploadStatusResponse`
- 实现 5 个 API 端点：init / chunk / complete / status / cancel
- 实现 `ChunkUploadManager`：临时文件预分配、偏移写入、分片完整性校验
- 实现 `UploadSessionRepository` 仓储
- 验证：使用 curl 模拟分片上传 10MB 文件

**验收**：分片上传 API 全部可用，文件可完整重组

---

### 任务 6.2：分片上传前端实现

| 项 | 内容 |
|---|---|
| 文件 | `frontend/src/utils/UploadManager.ts`, `frontend/src/views/KnowledgeView.vue` |
| 工时 | 1.5 天 |
| 依赖 | 任务 6.1 |

**内容**：
- 实现 `UploadManager` 类：分片切割、并发上传控制（最多 3 片）、进度汇总
- 实现断点续传：`localStorage` 保存 `upload_id`，页面刷新后恢复
- 改造 `KnowledgeView.vue` 上传弹窗：
  - 多文件选择（accept 扩展为所有支持格式）
  - 实时进度条（百分比 + 分片进度）
  - 上传队列展示（文件名 + 进度 + 取消按钮）
  - 大文件时仅显示文件信息，不绑定到响应式系统
- 验证：上传 30MB 文件，观察进度条和分片日志

**验收**：前端可正常分片上传大文件，进度实时更新，断点续传可用

---

### 任务 6.3：多格式解析器实现

| 项 | 内容 |
|---|---|
| 文件 | `app/infrastructure/parsers/*.py`, `app/infrastructure/parsers/validator.py` |
| 工时 | 2 天 |
| 依赖 | 任务 6.1 |

**内容**：
- 创建 `DocumentParser` 抽象基类和 `ParserRegistry` 注册表
- 实现解析器：TxtParser, PdfParser, DocxParser, PptxParser, XlsxParser
- 实现 `EncodingDetector`：BOM → chardet → 启发式逐尝试 → 回退
- 实现 `FileValidator`：Magic Bytes 校验 + 文件大小限制 + 扩展名白名单
- 实现 `ParsedDocument` 统一输出结构（含 `TextSegment` 置信度标记）
- 各解析器单元测试
- 安装依赖：pdfplumber, python-docx, python-pptx, openpyxl, xlrd, chardet
- 验证：每种格式上传 1 个文件，验证文本提取结果

**验收**：所有格式解析器可正确提取文本，编码检测准确

---

### 任务 6.4：解析器集成到上传流程

| 项 | 内容 |
|---|---|
| 文件 | `app/application/use_cases/manage_knowledge.py`（修改） |
| 工时 | 0.5 天 |
| 依赖 | 任务 6.3 |

**内容**：
- 修改 `upload_knowledge` 流程：文件上传完成 → 解析器提取内容 → 分块 → 向量化
- 新增 `process_uploaded_file()` 函数：格式校验 → 解析 → 走现有流程
- 在 `complete` API 中触发解析流水线
- 解析结果存入 `knowledge_docs` 新增字段（encoding, parse_method, page_count）
- 验证：上传 PDF 文件，确认解析结果正确存入 ChromaDB

**验收**：端到端流程：上传 PDF → 解析 → 分块 → 向量化 → 可检索

---

### 任务 6.5：异常处理与降级策略

| 项 | 内容 |
|---|---|
| 文件 | `app/infrastructure/parsers/*.py`（修改） |
| 工时 | 0.5 天 |
| 依赖 | 任务 6.3 |

**内容**：
- 实现 `ParsePipeline` 降级链路：标准解析 → 跳过OCR → 仅前N页 → 仅元数据
- 实现 `MemoryGuard`：解析过程内存监控，超阈值自动降级
- 实现 `TimeoutParser`：超时控制，超时返回部分结果
- 异常分类：FormatUnknownError, EncodingError, CorruptedFileError, EncryptedFileError
- 解析日志记录：编码检测结果、解析方法、耗时、置信度
- 验证：上传损坏 PDF、加密 PDF、超大文件，验证降级行为

**验收**：异常场景有合理降级处理，不崩溃，不丢失已处理数据

---

### 任务 6.6：性能压测与优化

| 项 | 内容 |
|---|---|
| 工时 | 1 天 |
| 依赖 | 任务 6.4, 6.5 |

**内容**：
- 单文件 50MB 上传压测（记录耗时、内存峰值）
- 多文件并发上传测试（3 个文件同时上传）
- 断点续传场景测试（模拟 50% 处断网 → 恢复）
- 大 PDF（100+ 页）解析性能测试
- 大 Excel（10000+ 行）解析性能测试
- 优化：并行解析 + 异步写入 + 流式处理
- 临时文件清理策略（定时清理 24h 前的文件）
- 验证：验收标准全部达标

**验收**：50MB 文件上传成功，速度提升 50%+，失败率 <1%

---

### 任务 6.7：数据库迁移

| 项 | 内容 |
|---|---|
| 工时 | 0.5 天 |
| 依赖 | 任务 6.1 |

**内容**：
- 创建 `knowledge_uploads` 表
- `knowledge_docs` 新增字段：`file_size`, `encoding`, `parse_method`, `page_count`, `parse_duration_ms`
- PostgreSQL 9.2 兼容性检查（避免 JSONB 等高级类型）
- 执行迁移脚本 + 验证
- 更新 ORM 模型

**验收**：数据库表结构正确，迁移可回滚

---

### 任务 6.8：分块策略增强

| 项 | 内容 |
|---|---|
| 文件 | `app/application/use_cases/manage_knowledge.py`（修改 `_split_content`） |
| 工时 | 0.5 天 |
| 依赖 | 任务 6.3 |

**内容**：
- 替换 `_split_content` 为基于 token 的语义分块：
  - 使用 `separators` 优先级列表（句号 → 换行 → 空格）
  - 设置 `chunk_overlap=64` tokens 滑动窗口
  - 块大小从 500 字符改为 512 tokens
- 分块时注入文档上下文：`[文档: xxx.pdf, 第N页, 章节标题]`
- 增强 metadata：`doc_type`, `page`, `confidence`, `parse_method`, `heading`, `uploaded_at`
- 单元测试：验证分块边界、重叠、metadata 完整性

**验收**：分块不再切断语义，metadata 包含完整文档上下文

---

### 任务 6.9：查询优化实现

| 项 | 内容 |
|---|---|
| 文件 | `app/domain/services/query_rewriter.py`（新增） |
| 工时 | 0.5 天 |
| 依赖 | 任务 6.3 |

**内容**：
- 实现 `QueryRewriter` 类：
  - 医学术语映射表（50+ 常见口语→术语对）
  - LLM 驱动的多角度查询生成（2-3 个查询）
  - 对话历史感知的查询补全
- 实现 `MedicalTermExpander`：静默术语扩展，无需 LLM 调用
- 查询缓存：相同查询 5 分钟内复用结果
- 验证：输入"头疼"→ 输出"头痛 偏头痛 紧张性头痛"

**验收**：口语化查询可正确映射为医学术语，多查询并行检索

---

### 任务 6.10：混合检索实现

| 项 | 内容 |
|---|---|
| 文件 | `app/domain/services/rag_strategy.py`（新增，重构原 RAGStrategy） |
| 工时 | 1 天 |
| 依赖 | 任务 6.8, 6.9 |

**内容**：
- 实现 `EnhancedRAGStrategy` 替代原 `RAGStrategy`：
  - 向量检索：复用 ChromaVectorStore.search()
  - BM25 关键词检索：使用 rank-bm25 库，内存索引
  - RRF 融合：`score = Σ 1/(k+rank)`，k=60
- 实现元数据过滤层：
  - 质量过滤：`confidence > 0.5`
  - 类型过滤：支持按 `doc_type` 筛选
  - 时效过滤：支持按 `uploaded_at` 范围筛选
- 实现分层权重：`final_score = similarity × doc_type_weight × confidence_weight × recency_weight`
- 集成到 `DiagnosisEngine.generate_response()` 中
- 验证：同一查询，混合检索 Top-5 命中率 > 纯向量检索

**验收**：混合检索上线，医学精确术语匹配不再漏检

---

### 任务 6.11：重排序实现

| 项 | 内容 |
|---|---|
| 文件 | `app/domain/services/reranker.py`（新增） |
| 工时 | 0.5 天 |
| 依赖 | 任务 6.10 |

**内容**：
- 实现 `CrossEncoderReranker`：
  - 使用 `BAAI/bge-reranker-v2-m3` 或轻量 `ms-marco-MiniLM-L-6-v2`
  - 对候选集 (query, chunk) 逐对打分
  - 选出 Top-K 最相关片段
- 降级策略：reranker 不可用时降级为原始向量分数排序
- 验证：重排序后 Top-3 精度提升 > 10%

**验收**：重排序后检索结果相关性显著提升

---

### 任务 6.12：上下文组装优化

| 项 | 内容 |
|---|---|
| 文件 | `app/domain/services/context_assembler.py`（新增） |
| 工时 | 0.5 天 |
| 依赖 | 任务 6.11 |

**内容**：
- 实现 `ContextAssembler`：
  - Token 预算管理：`MAX_CONTEXT_TOKENS=2000`
  - 按 `final_score` 降序排列
  - 同文档连续片段合并
  - 来源标签注入：`📄 高血压指南2024.pdf | 第5页 | 三、诊断标准`
  - 低置信度标注：`⚠️ 低置信度（OCR提取）`
- 集成到 `DiagnosisEngine.build_messages()` 中
- 验证：上下文始终在 token 预算内，来源信息完整

**验收**：上下文格式规范，token 不超预算，来源可追溯

---

### 任务 6.13：检索质量监控

| 项 | 内容 |
|---|---|
| 文件 | `app/domain/services/rag_strategy.py`（修改） |
| 工时 | 0.5 天 |
| 依赖 | 任务 6.10 |

**内容**：
- 实现检索指标采集：
  - `search_latency_ms`：每次检索耗时
  - `hit_rate`：检索命中率（结果 > 0）
  - `avg_similarity`：平均向量相似度
  - `context_token_usage`：上下文 token 使用率
- 日志记录 + 结构化输出
- 告警阈值：耗时 > 500ms 或命中率 < 80% 时 WARN 日志
- 验证：检索日志可正常输出指标

**验收**：检索质量指标可追踪，异常可告警

---

## 任务依赖图

```
阶段一（骨架）
  1.1 后端初始化 ──┬── 1.2 数据库初始化
  1.3 前端初始化  │
                  │
阶段二（领域+基础设施）         │
  2.1 ORM 模型 ←──┘
  2.2 领域实体 ←── 2.1
  2.3 仓储接口 ←── 2.2
  2.4 仓储实现 ←── 2.1 + 2.2 + 2.3
  2.5 LLM Provider ←── 1.1
                  │
阶段三（领域服务+应用层）      │
  3.1 状态机（独立）             │
  3.2 RAG 策略 ←── 2.5         │
  3.3 AgentFactory ←── 3.1 + 3.2 + 2.4 + 2.5
  3.4 Use Cases ←── 3.3
                  │
阶段四（API+前端）             │
  4.1 API ←── 3.4
  4.2 前端 ←── 4.1
  4.3 联调 ←── 4.1 + 4.2
                  │
阶段五（安全+测试）            │
  5.1 安全合规 ←── 4.1
  5.2 单元测试 ←── 3.1 + 3.2 + 3.3
  5.3 集成测试 ←── 4.3
                  │
阶段六（知识库优化 V1.1）       │
  6.1 分片上传后端 ←── 1.2 + 2.4
  6.2 分片上传前端 ←── 6.1
  6.3 多格式解析器 ←── 6.1
  6.4 解析器集成   ←── 6.3
  6.5 异常处理降级 ←── 6.3
  6.6 性能压测     ←── 6.4 + 6.5
  6.7 数据库迁移   ←── 6.1
  6.8 分块策略增强 ←── 6.3
  6.9 查询优化     ←── 6.3
  6.10 混合检索    ←── 6.8 + 6.9
  6.11 重排序      ←── 6.10
  6.12 上下文组装  ←── 6.11
  6.13 检索质量监控 ←── 6.10
```

## 工时汇总

| 阶段 | 任务数 | 预估工时 |
|---|---|---|
| 阶段一：项目骨架 | 3 | 1.5 天 |
| 阶段二：领域+基础设施 | 5 | 4 天 |
| 阶段三：领域服务+应用层 | 4 | 3.5 天 |
| 阶段四：API+前端 | 3 | 4 天 |
| 阶段五：安全+测试 | 3 | 2.5 天 |
| 阶段六：知识库优化（V1.1） | 13 | 11 天 |
| **合计** | **31** | **26.5 天** |

> 工时基于单人全职开发估算，实际可能因调试、学习曲线、需求变更等因素浮动 ±30%。
> 阶段六为 V1.1 增量，可在 V1 稳定后独立推进。

## V1 交付清单

- [ ] 用户注册/登录（含 JWT Token）
- [ ] 首次登录签署知情同意书
- [ ] 管理员可创建/编辑/激活医生角色，绑定知识库
- [ ] 医生选择页：列表、筛选（科室/职称）、评分
- [ ] 用户可选择医生开始问诊
- [ ] AI 以选定医生角色风格（姓名/职称/专长）回复
- [ ] 问诊状态机：症状收集 → 分析 → 推荐
- [ ] 流式输出 AI 回复（首 token <1s）
- [ ] 知识库上传 PDF/Word/TXT，自动分块向量化
- [ ] RAG 检索结果注入回复，前端展示来源卡片
- [ ] 每条诊断建议附带免责声明
- [ ] 对话历史可查看/切换/删除
- [ ] 手机号加密存储
- [ ] 全局审计日志
- [ ] WebSocket 完整协议（认证/流式/心跳/重连）
- [ ] REST API 统一响应格式（code/data/message）
- [ ] 核心领域逻辑单元测试覆盖率 ≥80%
- [ ] API 集成测试通过
- [ ] Prompt 注入防护

## V1.1 交付清单（知识库优化）

### 上传与解析
- [ ] 分片上传：支持 50MB 以内文件，2MB/片，并行 3 片
- [ ] 断点续传：网络中断后可从断点恢复
- [ ] 上传进度：前端实时显示上传百分比
- [ ] 上传队列：支持多文件同时上传，最多 3 并发
- [ ] 多格式解析：支持 TXT/MD/PDF/DOCX/PPTX/XLSX
- [ ] 编码自动检测：UTF-8/GBK/GB18030 等多编码兼容
- [ ] 格式校验：Magic Bytes 校验 + 文件完整性检查
- [ ] 解析降级：异常时自动降级（跳过OCR/仅前N页/仅元数据）
- [ ] 性能达标：平均上传速度提升 50%+，失败率 < 1%
- [ ] 文本提取准确率 > 95%

### 智能检索
- [ ] 语义分块：512 tokens/块，64 tokens 重叠，句号优先切分
- [ ] 分块元数据：doc_type/page/confidence/heading/uploaded_at 完整
- [ ] 查询改写：医学术语映射表（50+ 对），口语→术语自动转换
- [ ] 多查询生成：单次查询生成 2-3 个角度的检索语句
- [ ] 混合检索：向量检索 + BM25 关键词检索，RRF 融合
- [ ] 元数据过滤：质量/类型/时效三维过滤
- [ ] 分层权重：doc_type_weight × confidence_weight × recency_weight
- [ ] 重排序：Cross-Encoder 重排序，Top-3 精度提升 > 10%
- [ ] 上下文组装：Token 预算 2000，来源标签注入，同文档合并
- [ ] 检索耗时 < 500ms（含重排序）
- [ ] 混合检索 Top-5 命中率 > 纯向量检索 15%+
- [ ] 检索质量监控：延迟/命中率/相似度指标可追踪
