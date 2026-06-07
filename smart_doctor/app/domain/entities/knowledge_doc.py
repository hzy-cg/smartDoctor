from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class KnowledgeDocEntity:
    id: UUID
    filename: str
    file_path: str
    file_type: str
    chunk_count: int = 0
    version: int = 1
    previous_version_id: UUID | None = None
    status: str = "uploading"
    collection_name: str | None = None
    uploaded_at: datetime | None = None
    # v2.1 新增字段
    file_size: int = 0
    encoding: str | None = None
    parse_method: str | None = None
    page_count: int | None = None
    parse_duration_ms: float | None = None
