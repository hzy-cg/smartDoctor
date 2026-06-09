import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.infrastructure.persistence.database import Base


class UploadSession(Base):
    """
    上传会话表（v2.1 新增）
    记录分片上传的会话状态，支持断点续传和进度追踪。
    """
    __tablename__ = "knowledge_uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    chunk_size: Mapped[int] = mapped_column(Integer, default=2 * 1024 * 1024, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    received_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    received_chunk_map: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # comma-separated received chunk indices, e.g. "0,1,2,3" — used for deduplication (v2.2 fix)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    # pending / uploading / completed / failed / cancelled
    temp_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
