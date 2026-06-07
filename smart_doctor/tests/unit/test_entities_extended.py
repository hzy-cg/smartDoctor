import pytest
from uuid import uuid4

from app.domain.entities import (
    DoctorRoleEntity, ConversationEntity, MessageEntity,
    KnowledgeDocEntity
)


class TestConversationEntity:

    def test_conversation_creation(self):
        conv = ConversationEntity(
            id=uuid4(),
            user_id=uuid4(),
            doctor_id=uuid4(),
            title="神经内科问诊",
            diagnosis_stage="collecting"
        )
        assert conv.diagnosis_stage == "collecting"
        assert conv.title == "神经内科问诊"

    def test_conversation_with_symptoms(self):
        conv = ConversationEntity(
            id=uuid4(),
            user_id=uuid4(),
            doctor_id=uuid4(),
            title="问诊",
            diagnosis_stage="analyzing",
            symptoms=["头痛", "发热"]
        )
        assert len(conv.symptoms) == 2

    def test_conversation_default_values(self):
        conv = ConversationEntity(
            id=uuid4(),
            user_id=uuid4(),
            doctor_id=uuid4()
        )
        assert conv.diagnosis_stage == "collecting"


class TestMessageEntity:

    def test_user_message(self):
        msg = MessageEntity(
            id=uuid4(),
            conversation_id=uuid4(),
            role="user",
            content="我头痛",
            input_type="text"
        )
        assert msg.role == "user"
        assert msg.content == "我头痛"

    def test_assistant_message(self):
        msg = MessageEntity(
            id=uuid4(),
            conversation_id=uuid4(),
            role="assistant",
            content="请问持续多久了？",
            input_type="text"
        )
        assert msg.role == "assistant"