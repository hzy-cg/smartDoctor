from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class ClinicalState:
    conversation_id: UUID
    doctor_id: UUID | None = None
    symptoms: list[str] = field(default_factory=list)
    current_intent: str = ""
    rag_context: str | None = None
    rag_sources: list[dict] = field(default_factory=list)
    recommended_dept: str | None = None
    diagnosis_stage: str = "collecting"
    needs_more_info: bool = True
    input_type: str = "text"
    _last_user_message: str = ""
