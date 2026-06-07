-- Migration: Add knowledge_uploads table (v2.1)
-- Run: psql -h 192.168.1.106 -U postgres -d smart_doctor -f migrations/add_knowledge_uploads.sql

CREATE TABLE IF NOT EXISTS knowledge_uploads (
    id UUID PRIMARY KEY,
    doctor_id UUID NOT NULL,
    filename VARCHAR(512) NOT NULL,
    file_size BIGINT DEFAULT 0 NOT NULL,
    chunk_size INTEGER DEFAULT 2097152 NOT NULL,
    total_chunks INTEGER DEFAULT 0 NOT NULL,
    received_chunks INTEGER DEFAULT 0 NOT NULL,
    status VARCHAR(16) DEFAULT 'pending' NOT NULL,
    temp_file_path VARCHAR(1024),
    file_type VARCHAR(16),
    error_message VARCHAR(1024),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
