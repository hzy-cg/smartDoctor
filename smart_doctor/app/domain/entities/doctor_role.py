from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class DoctorRoleEntity:
    id: UUID
    name: str
    title: str
    specialty: str
    expertise: str | None = None
    experience: str | None = None
    education: str | None = None
    avatar_url: str | None = None
    rating: float = 5.0
    lifecycle_state: str = "draft"
    has_digital_human: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.lifecycle_state == "active"

    @property
    def display_name(self) -> str:
        return f"{self.name} {self.title}"
