import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.audit_log import AuditLog


class AuditLogger:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def log(self, user_id: uuid.UUID | None = None, action: str = "",
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
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(entry)
        await self._session.flush()
