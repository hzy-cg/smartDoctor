import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.persistence.models.audit_log import AuditLog


class SqlAuditRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def log(self, user_id: uuid.UUID | None, action: str,
                  resource_type: str | None = None,
                  resource_id: uuid.UUID | None = None,
                  detail: dict | None = None,
                  ip_address: str | None = None) -> None:
        entry = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address,
        )
        self._session.add(entry)
        await self._session.flush()

    async def query(self, user_id: uuid.UUID | None = None, action: str | None = None,
                    limit: int = 50, offset: int = 0) -> list[dict]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [
            {
                "id": str(r.id),
                "user_id": str(r.user_id) if r.user_id else None,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": str(r.resource_id) if r.resource_id else None,
                "ip_address": r.ip_address,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.scalars().all()
        ]
