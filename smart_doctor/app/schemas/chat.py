from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class ConversationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    doctor_id: str
    title: str | None = None
    interaction_mode: str
    diagnosis_stage: str
    symptoms: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MessageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    conversation_id: str
    role: str
    content: str
    input_type: str
    created_at: datetime | None = None


class StartChatRequest(BaseModel):
    doctor_id: str


class SendMessageRequest(BaseModel):
    content: str = Field(..., max_length=4000)
    input_type: str = "text"
