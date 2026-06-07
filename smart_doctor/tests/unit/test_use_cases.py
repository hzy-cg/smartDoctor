import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.application.use_cases.start_consultation import start_consultation
from app.application.use_cases.send_message import send_message
from app.domain.services import AgentFactory
from app.domain.value_objects import ClinicalState
from app.domain.state_machine import DiagnosisStateMachine


class TestStartConsultation:
    @pytest.mark.asyncio
    async def test_start_consultation(self):
        conv_repo = AsyncMock()
        from app.domain.entities import ConversationEntity
        conv = ConversationEntity(
            id=uuid.uuid4(), user_id=uuid.uuid4(), doctor_id=uuid.uuid4(),
            title="神经内科问诊",
        )
        conv_repo.create.return_value = conv

        llm = AsyncMock()
        factory = AgentFactory(llm=llm, rag_strategy=None)

        uid = uuid.uuid4()
        did = uuid.uuid4()
        result_conv, result_sm = await start_consultation(
            user_id=uid, doctor_id=did,
            doctor_name="张医生", doctor_title="主任医师",
            doctor_specialty="神经内科", doctor_expertise="头痛",
            conv_repo=conv_repo, factory=factory,
        )
        assert result_conv.title == "神经内科问诊"
        assert isinstance(result_sm, DiagnosisStateMachine)
        conv_repo.create.assert_called_once()


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_send_message_new_symptom(self):
        conv_repo = AsyncMock()
        doctor_repo = AsyncMock()

        from app.domain.entities import DoctorRoleEntity
        doctor = DoctorRoleEntity(
            id=uuid.uuid4(), name="张医生", title="主任医师",
            specialty="神经内科", expertise="头痛",
        )
        doctor_repo.get_by_id.return_value = doctor

        llm = AsyncMock()
        llm.chat.side_effect = ["new_symptom", "请问持续多久了？"]
        factory = AgentFactory(llm=llm, rag_strategy=None)

        sm = DiagnosisStateMachine()
        cs = ClinicalState(conversation_id=uuid.uuid4())

        conv_id = uuid.uuid4()
        user_id = uuid.uuid4()
        doctor_id = doctor.id

        result = await send_message(
            conversation_id=conv_id,
            user_id=user_id,
            doctor_id=doctor_id,
            user_message="我头痛",
            input_type="text",
            state_machine=sm,
            clinical_state=cs,
            conv_repo=conv_repo,
            doctor_repo=doctor_repo,
            factory=factory,
        )
        assert result["user_message"].content == "我头痛"
        assert result["assistant_message"].content == "请问持续多久了？"
        assert conv_repo.add_message.call_count == 2