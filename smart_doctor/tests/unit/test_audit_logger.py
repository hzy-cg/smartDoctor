import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.infrastructure.audit.audit_logger import AuditLogger
from app.infrastructure.persistence.models.audit_log import AuditLog


class TestAuditLogger:
    @pytest.mark.asyncio
    async def test_log_basic(self):
        session = AsyncMock()
        logger = AuditLogger(session=session)
        await logger.log(action="user_login")
        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_with_all_params(self):
        session = AsyncMock()
        logger = AuditLogger(session=session)
        uid = uuid.uuid4()
        rid = uuid.uuid4()
        await logger.log(
            user_id=uid,
            action="create_conversation",
            resource_type="conversation",
            resource_id=rid,
            detail={"key": "value"},
            ip_address="127.0.0.1",
        )
        session.add.assert_called_once()
        entry = session.add.call_args[0][0]
        assert isinstance(entry, AuditLog)
        assert entry.action == "create_conversation"
        assert entry.resource_type == "conversation"
        assert entry.ip_address == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_log_minimal(self):
        session = AsyncMock()
        logger = AuditLogger(session=session)
        await logger.log()
        session.add.assert_called_once()
        entry = session.add.call_args[0][0]
        assert entry.action == ""