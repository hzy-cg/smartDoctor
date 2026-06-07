from datetime import datetime
from pydantic import BaseModel, Field


class UploadInitRequest(BaseModel):
    """初始化上传会话请求"""
    doctor_id: str
    filename: str = Field(..., min_length=1, max_length=512)
    file_size: int = Field(..., gt=0, le=100 * 1024 * 1024)  # 最大 100MB
    file_type: str | None = None
    chunk_size: int = Field(default=2 * 1024 * 1024, ge=512 * 1024, le=10 * 1024 * 1024)  # 512KB ~ 10MB


class UploadInitResponse(BaseModel):
    """初始化上传会话响应"""
    upload_id: str
    chunk_size: int
    total_chunks: int
    received_chunks: int


class UploadStatusResponse(BaseModel):
    """上传状态查询响应"""
    upload_id: str
    filename: str
    file_size: int
    chunk_size: int
    total_chunks: int
    received_chunks: int
    progress_percent: float
    status: str  # pending / uploading / completed / failed / cancelled
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UploadCompleteResponse(BaseModel):
    """上传完成响应"""
    upload_id: str
    message: str
    doc_id: str | None = None  # 解析并入库后的知识文档 ID
