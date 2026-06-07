from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ConversationEntity:
    id: UUID
    user_id: UUID
    doctor_id: UUID
    title: str | None = None
    interaction_mode: str = "chat"
    diagnosis_stage: str = "collecting"
    symptoms: list[str] | None = None
    summary: str | None = None
    knowledge_version: int | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class MessageEntity:
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    input_type: str = "text"
    audio_url: str | None = None
    tool_calls: dict | None = None
    extra_metadata: dict | None = None
    disclaimer_shown: bool = True
    created_at: datetime | None = None
