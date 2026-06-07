import pytest
from uuid import uuid4

from app.infrastructure.persistence.models.user import User
from app.infrastructure.persistence.models.doctor import DoctorRole
from app.infrastructure.persistence.models.conversation import Conversation, Message
from app.infrastructure.persistence.models.knowledge import KnowledgeDoc
from app.infrastructure.persistence.models.audit_log import AuditLog
from app.infrastructure.persistence.models.outbox import OutboxEvent


class TestUserModel:

    def test_user_creation(self):
        user = User(
            id=uuid4(),
            username="testuser",
            hashed_password="hashed_pass",
            is_active=True
        )
        assert user.username == "testuser"
        assert user.is_active is True


class TestDoctorModel:

    def test_doctor_creation(self):
        doctor = DoctorRole(
            id=uuid4(),
            name="张医生",
            title="主任医师",
            specialty="神经内科",
            expertise="头痛、头晕",
            lifecycle_state="active"
        )
        assert doctor.name == "张医生"
        assert doctor.lifecycle_state == "active"


class TestConversationModel:

    def test_conversation_creation(self):
        conv = Conversation(
            id=uuid4(),
            user_id=uuid4(),
            doctor_id=uuid4(),
            title="神经内科问诊",
            diagnosis_stage="collecting"
        )
        assert conv.diagnosis_stage == "collecting"


class TestMessageModel:

    def test_message_creation(self):
        msg = Message(
            id=uuid4(),
            conversation_id=uuid4(),
            role="user",
            content="我头痛",
            input_type="text"
        )
        assert msg.role == "user"


class TestKnowledgeModel:

    def test_knowledge_document_creation(self):
        doc = KnowledgeDoc(
            id=uuid4(),
            filename="诊疗指南.pdf",
            file_path="/uploads/guideline.pdf",
            file_type="pdf"
        )
        assert doc.file_type == "pdf"


class TestOutboxModel:

    def test_outbox_event_creation(self):
        msg = OutboxEvent(
            id=uuid4(),
            event_type="conversation.created",
            payload={"conversation_id": str(uuid4())}
        )
        assert msg.event_type == "conversation.created"