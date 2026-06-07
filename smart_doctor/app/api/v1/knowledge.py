import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories import SqlKnowledgeRepository
from app.infrastructure.vectorstore.chroma_store import ChromaVectorStore
from app.schemas.api_response import ApiResponse
from app.schemas.knowledge import KnowledgeUploadRequest, KnowledgeResponse
from app.application.use_cases import upload_knowledge, list_knowledge, delete_knowledge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_vector_store = None


def _get_vector_store() -> ChromaVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaVectorStore()
    return _vector_store


@router.post("/upload")
async def upload(
    req: KnowledgeUploadRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    doc_repo = SqlKnowledgeRepository(db)
    vector_store = _get_vector_store()

    try:
        entity = await upload_knowledge(
            doctor_id=req.doctor_id,
            filename=req.filename,
            content=req.content,
            doc_repo=doc_repo,
            vector_store=vector_store,
        )
        await db.commit()
    except Exception as e:
        logger.exception("Knowledge upload failed: %s", e)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"知识上传失败：{str(e)}")

    return ApiResponse(data=KnowledgeResponse(
        id=str(entity.id),
        filename=entity.filename,
        file_path=entity.file_path,
        file_type=entity.file_type,
        chunk_count=entity.chunk_count,
        version=entity.version,
        status=entity.status,
        collection_name=entity.collection_name,
        uploaded_at=entity.uploaded_at,
    ))


@router.get("")
async def list_docs(
    doctor_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    doc_repo = SqlKnowledgeRepository(db)

    try:
        entities = await list_knowledge(doctor_id=doctor_id, doc_repo=doc_repo)
    except Exception as e:
        logger.exception("Knowledge list failed: %s", e)
        raise HTTPException(status_code=500, detail=f"知识列表获取失败：{str(e)}")

    return ApiResponse(data=[
        KnowledgeResponse(
            id=str(e.id),
            filename=e.filename,
            file_path=e.file_path,
            file_type=e.file_type,
            chunk_count=e.chunk_count,
            version=e.version,
            status=e.status,
            collection_name=e.collection_name,
            uploaded_at=e.uploaded_at,
        ) for e in entities
    ])


@router.delete("/{doc_id}")
async def delete_doc(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    doc_repo = SqlKnowledgeRepository(db)
    vector_store = _get_vector_store()

    try:
        existing = await doc_repo.get_by_id(uuid.UUID(doc_id))
        if not existing:
            raise HTTPException(status_code=404, detail="知识文档不存在")

        await delete_knowledge(
            doc_id=uuid.UUID(doc_id),
            doc_repo=doc_repo,
            vector_store=vector_store,
        )
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        logger.exception("Knowledge delete failed: %s", e)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"知识删除失败：{str(e)}")

    return ApiResponse(message="知识文档已删除")