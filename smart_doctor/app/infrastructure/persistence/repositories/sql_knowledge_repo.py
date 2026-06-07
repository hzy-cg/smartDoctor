import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.infrastructure.persistence.models.knowledge import KnowledgeDoc
from app.domain.entities import KnowledgeDocEntity


class SqlKnowledgeRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, doc_id: uuid.UUID) -> KnowledgeDocEntity | None:
        stmt = select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[KnowledgeDocEntity]:
        stmt = select(KnowledgeDoc).order_by(KnowledgeDoc.uploaded_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, doc: KnowledgeDocEntity) -> KnowledgeDocEntity:
        model = KnowledgeDoc(
            id=doc.id,
            filename=doc.filename,
            file_path=doc.file_path,
            file_type=doc.file_type,
            chunk_count=doc.chunk_count,
            version=doc.version,
            previous_version_id=doc.previous_version_id,
            status=doc.status,
            collection_name=doc.collection_name,
        )
        # v2.1 新增字段
        model.file_size = doc.file_size
        model.encoding = doc.encoding
        model.parse_method = doc.parse_method
        model.page_count = doc.page_count
        model.parse_duration_ms = doc.parse_duration_ms
        # 首次保存用 add，更新已有记录用 merge
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, doc_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        )

    async def flush(self) -> None:
        await self._session.flush()

    async def get_latest_version(self, filename: str) -> KnowledgeDocEntity | None:
        stmt = (select(KnowledgeDoc)
                .where(KnowledgeDoc.filename == filename)
                .order_by(KnowledgeDoc.version.desc())
                .limit(1))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    def _to_entity(self, model: KnowledgeDoc) -> KnowledgeDocEntity:
        return KnowledgeDocEntity(
            id=model.id,
            filename=model.filename,
            file_path=model.file_path,
            file_type=model.file_type,
            chunk_count=model.chunk_count,
            version=model.version,
            previous_version_id=model.previous_version_id,
            status=model.status,
            collection_name=model.collection_name,
            uploaded_at=model.uploaded_at,
            # v2.1
            file_size=model.file_size or 0,
            encoding=model.encoding,
            parse_method=model.parse_method,
            page_count=model.page_count,
            parse_duration_ms=model.parse_duration_ms,
        )
