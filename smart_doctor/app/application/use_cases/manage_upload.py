"""
分片上传用例（v2.2 更新）

管理上传会话生命周期：初始化 → 接收分片 → 完成 → 触发知识解析流水线

v2.2 更新:
  - process_uploaded_file 集成 ParsePipeline 多级降级解析
  - 异常分类处理（损坏/加密/超时/内存超限）
"""
import logging
import os
import uuid

from app.infrastructure.persistence.models.upload_session import UploadSession
from app.infrastructure.parsers.validator import FileValidator
from app.infrastructure.parsers.parse_pipeline import ParsePipeline
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

# 上传临时文件目录（相对于 smart_doctor/）
_UPLOAD_TEMP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "uploads", "temp"
)


def _ensure_temp_dir():
    os.makedirs(_UPLOAD_TEMP_DIR, exist_ok=True)


async def init_upload(
    doctor_id: str,
    filename: str,
    file_size: int,
    file_type: str | None,
    chunk_size: int,
    session: AsyncSession,
) -> UploadSession:
    """初始化上传会话，预分配临时文件"""
    _ensure_temp_dir()

    total_chunks = (file_size + chunk_size - 1) // chunk_size
    upload_id = uuid.uuid4()
    temp_path = os.path.join(_UPLOAD_TEMP_DIR, f"{upload_id}.tmp")

    model = UploadSession(
        id=upload_id,
        doctor_id=uuid.UUID(doctor_id),
        filename=filename,
        file_size=file_size,
        chunk_size=chunk_size,
        total_chunks=total_chunks,
        received_chunks=0,
        status="pending",
        temp_file_path=temp_path,
        file_type=file_type,
    )
    session.add(model)

    # 预分配临时文件占位
    with open(temp_path, "wb") as f:
        f.truncate(file_size)

    await session.flush()
    await session.refresh(model)
    logger.info(
        "Upload session initialized: id=%s filename=%s size=%d chunks=%d",
        upload_id, filename, file_size, total_chunks,
    )
    return model


async def write_chunk(
    upload_id: uuid.UUID,
    chunk_index: int,
    chunk_data: bytes,
    session: AsyncSession,
) -> UploadSession:
    """将分片写入临时文件指定偏移位置"""
    result = await session.execute(
        select(UploadSession).where(UploadSession.id == upload_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise ValueError(f"Upload session not found: {upload_id}")

    if model.status in ("completed", "failed", "cancelled"):
        raise ValueError(f"Upload session already {model.status}: {upload_id}")

    if chunk_index < 0 or chunk_index >= model.total_chunks:
        raise ValueError(
            f"Chunk index {chunk_index} out of range [0, {model.total_chunks - 1}]"
        )

    # 偏移写入临时文件
    offset = chunk_index * model.chunk_size
    expected_bytes = model.chunk_size
    if chunk_index == model.total_chunks - 1:
        # 最后一块可能不足 chunk_size
        expected_bytes = model.file_size - offset

    if len(chunk_data) != expected_bytes:
        raise ValueError(
            f"Chunk {chunk_index}: expected {expected_bytes} bytes, got {len(chunk_data)}"
        )

    with open(model.temp_file_path, "r+b") as f:
        f.seek(offset)
        f.write(chunk_data)

    model.received_chunks += 1
    model.status = "uploading"
    await session.flush()
    await session.refresh(model)

    logger.debug(
        "Chunk written: upload_id=%s chunk=%d/%d received=%d",
        upload_id, chunk_index + 1, model.total_chunks, model.received_chunks,
    )
    return model


async def complete_upload(
    upload_id: uuid.UUID,
    session: AsyncSession,
) -> UploadSession:
    """标记上传完成，校验完整性"""
    result = await session.execute(
        select(UploadSession).where(UploadSession.id == upload_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise ValueError(f"Upload session not found: {upload_id}")

    if model.received_chunks != model.total_chunks:
        missing = model.total_chunks - model.received_chunks
        raise ValueError(
            f"Upload incomplete: {missing} chunk(s) missing ({model.received_chunks}/{model.total_chunks})"
        )

    # 校验文件完整性（对比文件大小）
    if model.temp_file_path and os.path.exists(model.temp_file_path):
        actual_size = os.path.getsize(model.temp_file_path)
        if actual_size != model.file_size:
            raise ValueError(
                f"File size mismatch: expected {model.file_size}, got {actual_size}"
            )

    model.status = "completed"
    await session.flush()
    await session.refresh(model)
    logger.info("Upload completed: id=%s filename=%s", upload_id, model.filename)
    return model


async def process_uploaded_file(
    upload_session: UploadSession,
    session: AsyncSession,
) -> dict:
    """
    解析已上传文件并返回结构化结果（v2.2 集成多级降级流水线）。

    降级链路:
      Level 1 → 标准解析（完整提取）
      Level 2 → 跳过 OCR + 仅前 50 页
      Level 3 → 仅前 10 页
      Level 4 → 仅元数据（解析失败）

    Args:
        upload_session: 已完成的 UploadSession
        session: 数据库会话

    Returns:
        {"text": str, "file_type": str, "encoding": str, "parse_method": str,
         "level": int, "page_count": int, "parse_duration_ms": float,
         "file_size": int, "segments": list[dict]}

    Raises:
        ValueError: 文件校验失败（损坏/加密/过大）
    """
    file_path = upload_session.temp_file_path
    file_type = (upload_session.file_type or
                 upload_session.filename.rsplit(".", 1)[-1] if "." in upload_session.filename else "txt")
    file_type = file_type.lower()

    # 使用多级降级解析流水线
    pipeline = ParsePipeline()
    doc = await pipeline.parse(file_path, file_type=file_type)

    level = getattr(doc, "level", 1)

    logger.info(
        "File parsed: path=%s type=%s method=%s level=%d pages=%d duration=%.0fms error=%s",
        file_path, file_type, doc.parse_method, level, doc.page_count,
        doc.parse_duration_ms, doc.error,
    )

    # Level 4: 完全失败，仅元数据 — 抛出明确异常
    if level >= 4 or not doc.text.strip():
        error_msg = doc.error or "无法解析文件内容"
        if "损坏" in str(error_msg) or "不匹配" in str(error_msg):
            raise ValueError(f"文件已损坏或格式错误: {error_msg}")
        if "加密" in str(error_msg) or "密码" in str(error_msg):
            raise ValueError(f"文件已加密，无法解析: {error_msg}")
        if "过大" in str(error_msg) or "超过" in str(error_msg):
            raise ValueError(error_msg)
        # 通用解析失败
        raise ValueError(f"文件解析失败: {error_msg}")

    # 文本截断（大文档保护）
    text = doc.text
    max_chars = 500_000  # ~75K tokens
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[文档过长，已截断后续内容]"
        logger.warning("Document truncated: %d chars → %d", len(doc.text), max_chars)

    result = {
        "text": text,
        "file_type": file_type,
        "encoding": doc.encoding or "unknown",
        "parse_method": doc.parse_method,
        "level": level,
        "page_count": doc.page_count,
        "parse_duration_ms": doc.parse_duration_ms,
        "file_size": upload_session.file_size,
        "segments": [
            {"page": s.page, "heading": s.heading, "confidence": s.confidence}
            for s in doc.segments[:20]  # 保留前 20 个 segment 的元数据
        ],
    }

    # 降级日志
    if level > 1:
        logger.warning(
            "Parse degraded to level %d: file=%s method=%s error=%s",
            level, upload_session.filename, doc.parse_method, doc.error,
        )

    return result


async def get_upload_status(
    upload_id: uuid.UUID,
    session: AsyncSession,
) -> UploadSession | None:
    """查询上传状态"""
    result = await session.execute(
        select(UploadSession).where(UploadSession.id == upload_id)
    )
    return result.scalar_one_or_none()


async def cancel_upload(
    upload_id: uuid.UUID,
    session: AsyncSession,
) -> None:
    """取消上传并清理临时文件"""
    result = await session.execute(
        select(UploadSession).where(UploadSession.id == upload_id)
    )
    model = result.scalar_one_or_none()
    if model:
        model.status = "cancelled"
        if model.temp_file_path and os.path.exists(model.temp_file_path):
            try:
                os.remove(model.temp_file_path)
            except OSError:
                pass
        await session.flush()
        logger.info("Upload cancelled: id=%s", upload_id)


async def cleanup_temp_files(
    session: AsyncSession,
    max_age_hours: int = 24,
) -> int:
    """
    清理过期的临时上传文件（v2.2 新增）。

    清理条件：
      1. 已完成且超过 max_age_hours 的上传
      2. 已取消/失败的上传
      3. 孤儿临时文件（数据库无记录但磁盘存在）

    Args:
        session: 数据库会话
        max_age_hours: 最大保留时间（小时）

    Returns:
        int: 清理的文件数量
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import or_

    cleaned = 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    # 1. 清理数据库中已完成/已取消/失败的过期记录
    result = await session.execute(
        select(UploadSession).where(
            or_(
                UploadSession.status.in_(("completed", "cancelled", "failed")),
                UploadSession.updated_at < cutoff,
            )
        )
    )
    expired = result.scalars().all()

    for model in expired:
        if model.temp_file_path and os.path.exists(model.temp_file_path):
            try:
                os.remove(model.temp_file_path)
                cleaned += 1
                logger.debug("Cleaned expired temp file: %s", model.temp_file_path)
            except OSError as e:
                logger.warning("Failed to clean temp file %s: %s", model.temp_file_path, e)
        await session.delete(model)

    if expired:
        await session.flush()
        logger.info("Cleaned %d expired upload sessions", len(expired))

    # 2. 清理孤儿临时文件（磁盘有但数据库无记录）
    _ensure_temp_dir()
    try:
        for fname in os.listdir(_UPLOAD_TEMP_DIR):
            if not fname.endswith(".tmp"):
                continue
            fpath = os.path.join(_UPLOAD_TEMP_DIR, fname)
            try:
                file_mtime = datetime.fromtimestamp(
                    os.path.getmtime(fpath), tz=timezone.utc,
                )
                if file_mtime < cutoff:
                    os.remove(fpath)
                    cleaned += 1
                    logger.debug("Cleaned orphan temp file: %s", fpath)
            except OSError:
                pass
    except OSError:
        pass

    if cleaned > 0:
        logger.info("Temp file cleanup: removed %d files", cleaned)

    return cleaned
