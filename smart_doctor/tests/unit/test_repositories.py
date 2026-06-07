import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.persistence.repositories.sql_conversation_repo import SqlConversationRepository
from app.infrastructure.persistence.repositories.sql_doctor_repo import SqlDoctorRepository
from app.infrastructure.persistence.repositories.sql_audit_repo import SqlAuditRepository
from app.infrastructure.persistence.repositories.sql_knowledge_repo import SqlKnowledgeRepository


class TestSqlConversationRepository:
    @pytest.mark.asyncio
    async def test_create_conversation(self):
        session = AsyncMock()
        repo = SqlConversationRepository(session)
        from app.domain.entities import ConversationEntity
        conv = ConversationEntity(
            id=uuid.uuid4(), user_id=uuid.uuid4(), doctor_id=uuid.uuid4(),
            title="测试问诊",
        )
        await repo.create(conv)
        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_message(self):
        session = AsyncMock()
        repo = SqlConversationRepository(session)
        from app.domain.entities import MessageEntity
        msg = MessageEntity(
            id=uuid.uuid4(), conversation_id=uuid.uuid4(),
            role="user", content="我头痛",
        )
        await repo.add_message(msg)
        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(self):
        session = AsyncMock()
        repo = SqlConversationRepository(session)
        await repo.delete(uuid.uuid4())
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_update_existing(self):
        session = AsyncMock()
        mock_model = MagicMock()
        mock_model.id = uuid.uuid4()
        mock_model.user_id = uuid.uuid4()
        mock_model.doctor_id = uuid.uuid4()
        mock_model.title = "测试"
        mock_model.interaction_mode = "text"
        mock_model.diagnosis_stage = "collecting"
        mock_model.symptoms = []
        mock_model.summary = None
        mock_model.knowledge_version = None
        mock_model.expires_at = None
        mock_model.created_at = None
        mock_model.updated_at = None
        session.get.return_value = mock_model
        repo = SqlConversationRepository(session)
        from app.domain.entities import ConversationEntity
        conv = ConversationEntity(
            id=mock_model.id, user_id=mock_model.user_id,
            doctor_id=mock_model.doctor_id, title="更新标题",
        )
        result = await repo.update(conv)
        session.flush.assert_called_once()
        assert mock_model.title == "更新标题"


class TestSqlDoctorRepository:
    @pytest.mark.asyncio
    async def test_save_doctor(self):
        session = AsyncMock()
        mock_model = MagicMock()
        mock_model.id = uuid.uuid4()
        mock_model.name = "张医生"
        mock_model.title = "主任医师"
        mock_model.specialty = "神经内科"
        mock_model.expertise = "头痛"
        mock_model.experience = None
        mock_model.education = None
        mock_model.avatar_url = None
        mock_model.rating = 0.0
        mock_model.lifecycle_state = "active"
        mock_model.has_digital_human = False
        mock_model.created_at = None
        mock_model.updated_at = None
        session.merge.return_value = mock_model
        repo = SqlDoctorRepository(session)
        from app.domain.entities import DoctorRoleEntity
        doctor = DoctorRoleEntity(
            id=uuid.uuid4(), name="张医生", title="主任医师",
            specialty="神经内科", expertise="头痛",
        )
        await repo.save(doctor)
        session.merge.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_doctor(self):
        session = AsyncMock()
        repo = SqlDoctorRepository(session)
        await repo.delete(uuid.uuid4())
        assert session.execute.call_count == 4


class TestSqlAuditRepository:
    @pytest.mark.asyncio
    async def test_log(self):
        session = AsyncMock()
        repo = SqlAuditRepository(session)
        await repo.log(user_id=uuid.uuid4(), action="login")
        session.add.assert_called_once()
        session.flush.assert_called_once()


class TestSqlKnowledgeRepository:
    @pytest.mark.asyncio
    async def test_save(self):
        session = AsyncMock()
        repo = SqlKnowledgeRepository(session)
        from app.domain.entities import KnowledgeDocEntity
        doc = KnowledgeDocEntity(
            id=uuid.uuid4(), filename="test.pdf", file_path="/data/test.pdf",
            file_type="pdf", chunk_count=10, version=1,
        )
        await repo.save(doc)
        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(self):
        session = AsyncMock()
        repo = SqlKnowledgeRepository(session)
        await repo.delete(uuid.uuid4())
        session.execute.assert_called_once()