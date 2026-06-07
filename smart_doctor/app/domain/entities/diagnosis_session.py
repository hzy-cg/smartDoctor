# NOTE: This entity is currently unused; ClinicalState serves a similar role.
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class DiagnosisSession:
    id: UUID | None = None
    conversation_id: UUID | None = None
    doctor_id: UUID | None = None
    symptoms: list[str] = field(default_factory=list)
    stage: str = "collecting"
    rag_context: str | None = None
    recommended_dept: str | None = None
    needs_more_info: bool = True
    created_at: datetime | None = None

    @property
    def is_collecting(self) -> bool:
        return self.stage == "collecting"

    @property
    def is_analyzing(self) -> bool:
        return self.stage == "analyzing"

    @property
    def is_recommending(self) -> bool:
        return self.stage == "recommending"
