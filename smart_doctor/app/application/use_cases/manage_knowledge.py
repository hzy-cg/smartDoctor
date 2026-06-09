import logging
import uuid
from typing import Sequence

from app.domain.entities import KnowledgeDocEntity
from app.domain.repositories import KnowledgeRepository
from app.infrastructure.vectorstore.base import VectorStore
from app.application.utils.chunking import split_semantic_chunks, build_chunk_metadata

logger = logging.getLogger(__name__)


def _extract_file_type(filename: str) -> str:
    idx = filename.rfind(".")
    return filename[idx + 1:].lower() if idx != -1 else "txt"


def _make_collection_name(doctor_id: str) -> str:
    return f"doctor_{doctor_id}_knowledge"


async def upload_knowledge(
    doctor_id: str,
    filename: str,
    content: str,
    doc_repo: KnowledgeRepository,
    vector_store: VectorStore,
    *,
    parsed_meta: dict | None = None,
) -> KnowledgeDocEntity:
    """
    上传知识文档：分块 → 向量化 → 入库。

    Args:
        doctor_id: 医生ID
        filename: 文件名
        content: 文档文本内容
        doc_repo: 知识文档仓储
        vector_store: 向量存储
        parsed_meta: 解析元数据（v2.2 新增），包含:
            - file_type: 文件类型
            - encoding: 编码
            - parse_method: 解析方法
            - page_count: 总页数
            - parse_duration_ms: 解析耗时
            - file_size: 文件大小
            - segments: 解析片段列表
    """
    doc_id = uuid.uuid4()
    file_type = _extract_file_type(filename)
    file_path = f"/knowledge/{doctor_id}/{filename}"
    collection_name = _make_collection_name(doctor_id)

    # 构建文档上下文（v2.2 增强）
    doc_context = build_chunk_metadata(
        source_name=filename,
        doc_type=file_type,
        parsed_meta=parsed_meta,
    )

    chunks = split_semantic_chunks(
        content,
        chunk_tokens=512,
        chunk_overlap_tokens=64,
        source_name=filename,
        doc_context=doc_context,
    )
    chunk_count = len(chunks)

    entity = KnowledgeDocEntity(
        id=doc_id,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        chunk_count=chunk_count,
        version=1,
        status="uploading",
        collection_name=collection_name,
        # v2.1 解析元数据
        file_size=parsed_meta.get("file_size", 0),
        encoding=parsed_meta.get("encoding"),
        parse_method=parsed_meta.get("parse_method"),
        page_count=parsed_meta.get("page_count"),
        parse_duration_ms=parsed_meta.get("parse_duration_ms"),
    )
    saved = await doc_repo.save(entity)

    if chunks:
        chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(chunk_count)]
        metadatas = [chunk["metadata"] for chunk in chunks]
        documents = [chunk["content"] for chunk in chunks]
        await vector_store.add(
            collection=collection_name,
            documents=documents,
            metadatas=metadatas,
            ids=chunk_ids,
        )

    # 更新状态：通过仓储层更新 ORM 模型
    await doc_repo.update_status(doc_id, "active")
    await doc_repo.flush()

    logger.info(
        "Knowledge uploaded: doc_id=%s filename=%s chunks=%d type=%s",
        doc_id, filename, chunk_count, file_type,
    )
    return saved


async def list_knowledge(
    doctor_id: str,
    doc_repo: KnowledgeRepository,
) -> Sequence[KnowledgeDocEntity]:
    all_docs = await doc_repo.list_all()
    collection_prefix = _make_collection_name(doctor_id)
    return [d for d in all_docs if d.collection_name == collection_prefix]


async def delete_knowledge(
    doc_id: uuid.UUID,
    doc_repo: KnowledgeRepository,
    vector_store: VectorStore,
) -> None:
    doc = await doc_repo.get_by_id(doc_id)
    if doc and doc.collection_name:
        chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(doc.chunk_count)]
        try:
            await vector_store.delete(collection=doc.collection_name, ids=chunk_ids)
        except Exception as e:
            logger.warning(
                "Failed to delete chunks by ID for doc_id=%s, falling back to delete_collection: %s",
                doc_id, e,
            )
            await vector_store.delete_collection(doc.collection_name)

    await doc_repo.delete(doc_id)

    logger.info("Knowledge deleted: doc_id=%s", doc_id)