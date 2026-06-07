from pydantic import BaseModel
from datetime import datetime


class DoctorResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    title: str
    specialty: str
    expertise: str | None = None
    experience: str | None = None
    education: str | None = None
    avatar_url: str | None = None
    rating: float
    lifecycle_state: str
    has_digital_human: bool
    created_at: datetime | None = None


class DoctorCreateRequest(BaseModel):
    name: str
    title: str
    specialty: str
    expertise: str | None = None
    experience: str | None = None
    education: str | None = None
