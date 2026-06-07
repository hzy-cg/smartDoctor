from pydantic import BaseModel
from datetime import datetime


class FavoriteToggleRequest(BaseModel):
    doctor_id: str


class FavoriteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    user_id: str
    doctor_id: str
    created_at: datetime | None = None