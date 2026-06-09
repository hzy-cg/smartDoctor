-- ============================================================
-- SmartDoctor 数据库初始化脚本
-- 版本: v2.2
-- 数据库: PostgreSQL 9.2+
-- 用法:
--   1. 创建数据库: createdb -U postgres smart_doctor
--   2. 执行初始化: psql -h <host> -U postgres -d smart_doctor -f init_database.sql
--   3. (可选) 创建扩展: psql -h <host> -U postgres -d smart_doctor -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
--
-- 注意:
--   - PostgreSQL 9.2 不支持 JSONB, 使用 JSON 替代
--   - PostgreSQL 9.2 不支持 ADD COLUMN IF NOT EXISTS
--   - SSL 连接已禁用（本地开发环境）
-- ============================================================

BEGIN;

-- -----------------------------------------------------------
-- 1. 用户表 (users)
-- -----------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(64) UNIQUE NOT NULL,
    hashed_password VARCHAR(256) NOT NULL,
    phone           VARCHAR(20),
    consent_given   BOOLEAN DEFAULT FALSE NOT NULL,
    consent_at      TIMESTAMP WITH TIME ZONE,
    is_active       BOOLEAN DEFAULT TRUE NOT NULL,
    is_admin        BOOLEAN DEFAULT FALSE NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);

-- -----------------------------------------------------------
-- 2. 医生角色表 (doctor_roles)
-- -----------------------------------------------------------
CREATE TABLE doctor_roles (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name              VARCHAR(64) NOT NULL,
    title             VARCHAR(64) NOT NULL,
    specialty         VARCHAR(64) NOT NULL,
    expertise         TEXT,
    experience        TEXT,
    education         TEXT,
    avatar_url        VARCHAR(512),
    rating            FLOAT DEFAULT 5.0 NOT NULL,
    lifecycle_state   VARCHAR(16) DEFAULT 'draft' NOT NULL,
    activated_at      TIMESTAMP WITH TIME ZONE,
    has_digital_human BOOLEAN DEFAULT FALSE NOT NULL,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------
-- 3. 数字人表 (digital_humans)
-- -----------------------------------------------------------
CREATE TABLE digital_humans (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id          UUID NOT NULL REFERENCES doctor_roles(id) ON DELETE CASCADE,
    model_type         VARCHAR(16) DEFAULT 'live2d' NOT NULL,
    model_url          VARCHAR(512),
    texture_urls       JSON,
    voice_style        VARCHAR(64),
    speech_rate        FLOAT DEFAULT 1.0 NOT NULL,
    pitch              FLOAT DEFAULT 1.0 NOT NULL,
    interaction_style  VARCHAR(32) DEFAULT 'professional' NOT NULL,
    greeting_motion    VARCHAR(64),
    thinking_motion    VARCHAR(64),
    caring_motion      VARCHAR(64),
    custom_motions     JSON,
    created_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_digital_human_doctor ON digital_humans(doctor_id);

-- -----------------------------------------------------------
-- 4. 科室表 (departments)
-- -----------------------------------------------------------
CREATE TABLE departments (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(64) NOT NULL,
    category    VARCHAR(32),
    keywords    JSON,
    description TEXT
);

-- -----------------------------------------------------------
-- 5. 知识库文档表 (knowledge_docs)
-- -----------------------------------------------------------
CREATE TABLE knowledge_docs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename            VARCHAR(256) NOT NULL,
    file_path           VARCHAR(512) NOT NULL,
    file_type           VARCHAR(16) NOT NULL,
    chunk_count         INTEGER DEFAULT 0 NOT NULL,
    version             INTEGER DEFAULT 1 NOT NULL,
    previous_version_id UUID,
    status              VARCHAR(16) DEFAULT 'uploading' NOT NULL,
    collection_name     VARCHAR(128),
    uploaded_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- v2.1 解析元数据字段
    file_size           BIGINT DEFAULT 0 NOT NULL,
    encoding            VARCHAR(32),
    parse_method        VARCHAR(32),
    page_count          INTEGER,
    parse_duration_ms   FLOAT
);

-- -----------------------------------------------------------
-- 6. 医生-知识关联表 (doctor_knowledge)
-- -----------------------------------------------------------
CREATE TABLE doctor_knowledge (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id        UUID NOT NULL REFERENCES doctor_roles(id) ON DELETE CASCADE,
    knowledge_doc_id UUID NOT NULL REFERENCES knowledge_docs(id) ON DELETE CASCADE,
    access_level     VARCHAR(16) DEFAULT 'shared' NOT NULL
);

-- -----------------------------------------------------------
-- 7. 收藏表 (favorites)
-- -----------------------------------------------------------
CREATE TABLE favorites (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    doctor_id  UUID NOT NULL REFERENCES doctor_roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_user_doctor_favorite ON favorites(user_id, doctor_id);

-- -----------------------------------------------------------
-- 8. 会话表 (conversations)
-- -----------------------------------------------------------
CREATE TABLE conversations (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    doctor_id         UUID NOT NULL REFERENCES doctor_roles(id) ON DELETE CASCADE,
    title             VARCHAR(256),
    interaction_mode  VARCHAR(16) DEFAULT 'chat' NOT NULL,
    diagnosis_stage   VARCHAR(32) DEFAULT 'collecting' NOT NULL,
    symptoms          JSON,
    summary           TEXT,
    knowledge_version INTEGER,
    expires_at        TIMESTAMP WITH TIME ZONE,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_user_doctor ON conversations(user_id, doctor_id);

-- -----------------------------------------------------------
-- 9. 消息表 (messages)
-- -----------------------------------------------------------
CREATE TABLE messages (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id  UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role             VARCHAR(16) NOT NULL,
    content          TEXT NOT NULL,
    input_type       VARCHAR(16) DEFAULT 'text' NOT NULL,
    audio_url        VARCHAR(512),
    tool_calls       JSON,
    extra_metadata   JSON,
    disclaimer_shown BOOLEAN DEFAULT TRUE NOT NULL,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);

-- -----------------------------------------------------------
-- 10. 分片上传会话表 (knowledge_uploads)
-- -----------------------------------------------------------
CREATE TABLE knowledge_uploads (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id         UUID NOT NULL,
    filename          VARCHAR(512) NOT NULL,
    file_size         BIGINT DEFAULT 0 NOT NULL,
    chunk_size        INTEGER DEFAULT 2097152 NOT NULL,
    total_chunks      INTEGER DEFAULT 0 NOT NULL,
    received_chunks   INTEGER DEFAULT 0 NOT NULL,
    received_chunk_map VARCHAR(2048),
    -- comma-separated received chunk indices, e.g. "0,1,2,3"
    status            VARCHAR(16) DEFAULT 'pending' NOT NULL,
    -- pending / uploading / completed / failed / cancelled
    temp_file_path    VARCHAR(1024),
    file_type         VARCHAR(16),
    error_message     VARCHAR(1024),
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE
);

-- -----------------------------------------------------------
-- 11. 审计日志表 (audit_logs)
-- -----------------------------------------------------------
CREATE TABLE audit_logs (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID,
    action        VARCHAR(64) NOT NULL,
    resource_type VARCHAR(32),
    resource_id   UUID,
    detail        JSON,
    ip_address    VARCHAR(45),
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- -----------------------------------------------------------
-- 12. 事件发件箱表 (outbox_events)
-- -----------------------------------------------------------
CREATE TABLE outbox_events (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type   VARCHAR(64) NOT NULL,
    payload      JSON NOT NULL,
    status       VARCHAR(16) DEFAULT 'pending' NOT NULL,
    retry_count  INTEGER DEFAULT 0 NOT NULL,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMIT;

-- ============================================================
-- 初始化完成提示
-- ============================================================
SELECT 'SmartDoctor v2.2 数据库初始化完成!' AS message;
SELECT COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema = 'public';
