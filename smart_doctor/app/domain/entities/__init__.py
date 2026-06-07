from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.entities.doctor_role import DoctorRoleEntity
from app.domain.entities.conversation import ConversationEntity, MessageEntity
from app.domain.entities.diagnosis_session import DiagnosisSession
from app.domain.entities.knowledge_doc import KnowledgeDocEntity

__all__ = [
    "DoctorRoleEntity",
    "ConversationEntity",
    "MessageEntity",
    "DiagnosisSession",
    "KnowledgeDocEntity",
]
