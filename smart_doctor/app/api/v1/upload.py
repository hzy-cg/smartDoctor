"""
分片上传 API（v2.1 新增）

端点：
- POST /knowledge/upload/init        — 初始化上传
- POST /knowledge/upload/{id}/chunk/{n} — 上传分片
- POST /knowledge/upload/{id}/complete — 完成上传
- GET  /knowledge/upload/{id}/status  — 查询进度
- DELETE /knowledge/upload/{id}       — 取消上传
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.infrastructure.persistence.database import get_db
from app.schemas.api_response import ApiResponse
from app.schemas.upload import (
    UploadInitRequest,
    UploadInitResponse,
    UploadStatusResponse,
    UploadCompleteResponse,
)
from app.application.use_cases.manage_upload import (
    init_upload,
    write_chunk,
    complete_upload,
    get_upload_status,
    cancel_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge/upload", tags=["upload"])


@router.post("/init")
async def upload_init(
    req: UploadInitRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """初始化分片上传会话"""
    try:
        model = await init_upload(
            doctor_id=req.doctor_id,
            filename=req.filename,
            file_size=req.file_size,
            file_type=req.file_type,
            chunk_size=req.chunk_size,
            session=db,
        )
        await db.commit()
    except Exception as e:
        logger.exception("Upload init failed: %s", e)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"上传初始化失败：{str(e)}")

    return ApiResponse(data=UploadInitResponse(
        upload_id=str(model.id),
        chunk_size=model.chunk_size,
        total_chunks=model.total_chunks,
        received_chunks=model.received_chunks,
    ))


@router.post("/{upload_id}/chunk/{chunk_index}")
async def upload_chunk(
    upload_id: str,
    chunk_index: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """上传单个分片（multipart/form-data）"""
    try:
        chunk_data = await file.read()
        model = await write_chunk(
            upload_id=uuid.UUID(upload_id),
            chunk_index=chunk_index,
            chunk_data=chunk_data,
            session=db,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Upload chunk failed: upload_id=%s chunk=%d", upload_id, chunk_index)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"分片上传失败：{str(e)}")

    progress = (model.received_chunks / model.total_chunks) * 100 if model.total_chunks > 0 else 0
    return ApiResponse(data={
        "upload_id": str(model.id),
        "chunk_index": chunk_index,
        "received_chunks": model.received_chunks,
        "total_chunks": model.total_chunks,
        "progress_percent": round(progress, 1),
        "status": model.status,
    })


@router.post("/{upload_id}/complete")
async def upload_complete(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """完成上传，校验文件完整性并触发解析流水线（解析→分块→向量化→入库）"""
    from app.application.use_cases.manage_upload import process_uploaded_file
    from app.application.use_cases.manage_knowledge import upload_knowledge
    from app.infrastructure.persistence.repositories import SqlKnowledgeRepository
    from app.infrastructure.vectorstore.chroma_store import ChromaVectorStore
    from app.schemas.knowledge import KnowledgeResponse

    try:
        # Step 1: 完成上传会话
        model = await complete_upload(
            upload_id=uuid.UUID(upload_id),
            session=db,
        )

        # Step 2: 解析文件
        parsed = await process_uploaded_file(model, db)

        # Step 3: 知识入库（分块 + 向量化）
        doc_repo = SqlKnowledgeRepository(db)
        vector_store = ChromaVectorStore()

        # 获取上传会话中的 doctor_id
        doctor_id = str(model.doctor_id)

        entity = await upload_knowledge(
            doctor_id=doctor_id,
            filename=model.filename,
            content=parsed["text"],
            doc_repo=doc_repo,
            vector_store=vector_store,
            parsed_meta={
                "file_type": parsed["file_type"],
                "encoding": parsed["encoding"],
                "parse_method": parsed["parse_method"],
                "page_count": parsed["page_count"],
                "parse_duration_ms": parsed["parse_duration_ms"],
                "file_size": parsed["file_size"],
                "segments": parsed.get("segments", []),
            },
        )

        await db.commit()

        logger.info(
            "Upload pipeline complete: upload_id=%s doc_id=%s type=%s method=%s",
            upload_id, entity.id, parsed["file_type"], parsed["parse_method"],
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Upload complete failed: upload_id=%s", upload_id)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"上传处理失败：{str(e)}")

    return ApiResponse(data=UploadCompleteResponse(
        upload_id=str(model.id),
        message=f"文件解析完成（{parsed['parse_method']}, {parsed['page_count']}页, {entity.chunk_count}个分块）",
        doc_id=str(entity.id),
    ))


@router.get("/{upload_id}/status")
async def upload_status(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """查询上传进度"""
    try:
        model = await get_upload_status(
            upload_id=uuid.UUID(upload_id),
            session=db,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")

    if not model:
        raise HTTPException(status_code=404, detail="上传会话不存在")

    progress = (model.received_chunks / model.total_chunks) * 100 if model.total_chunks > 0 else 0
    return ApiResponse(data=UploadStatusResponse(
        upload_id=str(model.id),
        filename=model.filename,
        file_size=model.file_size,
        chunk_size=model.chunk_size,
        total_chunks=model.total_chunks,
        received_chunks=model.received_chunks,
        progress_percent=round(progress, 1),
        status=model.status,
        error_message=model.error_message,
        created_at=model.created_at,
        updated_at=model.updated_at,
    ))


@router.delete("/{upload_id}")
async def upload_cancel(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """取消上传并清理临时文件"""
    try:
        await cancel_upload(upload_id=uuid.UUID(upload_id), session=db)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"取消上传失败：{str(e)}")

    return ApiResponse(message="上传已取消")
