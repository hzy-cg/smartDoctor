from datetime import datetime
from pydantic import BaseModel, Field


class KnowledgeUploadRequest(BaseModel):
    doctor_id: str
    filename: str
    content: str = Field(..., max_length=5_000_000)


class KnowledgeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    filename: str
    file_path: str
    file_type: str
    chunk_count: int
    version: int
    status: str
    collection_name: str | None = None
    uploaded_at: datetime | None = None