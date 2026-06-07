from typing import Protocol
from uuid import UUID


class AuditRepository(Protocol):
    async def log(self, user_id: UUID | None, action: str, resource_type: str | None = None,
                  resource_id: UUID | None = None, detail: dict | None = None,
                  ip_address: str | None = None) -> None: ...
    async def query(self, user_id: UUID | None = None, action: str | None = None,
                    limit: int = 50, offset: int = 0) -> list[dict]: ...
