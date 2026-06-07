import pytest
from uuid import uuid4

from app.domain.entities import DoctorRoleEntity, ConversationEntity, MessageEntity
from app.domain.value_objects import ClinicalState, Symptom, Department, VoiceConfig


class TestDoctorRoleEntity:

    def test_display_name(self):
        doctor = DoctorRoleEntity(
            id=uuid4(), name="张医生", title="主任医师", specialty="神经内科"
        )
        assert doctor.display_name == "张医生 主任医师"

    def test_is_active(self):
        doctor = DoctorRoleEntity(
            id=uuid4(), name="test", title="主任", specialty="内科",
            lifecycle_state="active"
        )
        assert doctor.is_active is True

    def test_default_state_is_draft(self):
        doctor = DoctorRoleEntity(
            id=uuid4(), name="test", title="主任", specialty="内科"
        )
        assert doctor.lifecycle_state == "draft"
        assert doctor.is_active is False


class TestClinicalState:

    def test_default_values(self):
        conv_id = uuid4()
        cs = ClinicalState(conversation_id=conv_id)
        assert cs.conversation_id == conv_id
        assert cs.diagnosis_stage == "collecting"
        assert cs.symptoms == []
        assert cs.input_type == "text"
        assert cs.needs_more_info is True

    def test_custom_values(self):
        conv_id = uuid4()
        cs = ClinicalState(
            conversation_id=conv_id,
            doctor_id=uuid4(),
            symptoms=["头痛", "发热"],
            diagnosis_stage="analyzing",
        )
        assert cs.diagnosis_stage == "analyzing"
        assert len(cs.symptoms) == 2


class TestValueObjects:

    def test_symptom_creation(self):
        s = Symptom(name="头痛", location="前额", duration="3天", severity=7)
        assert s.name == "头痛"
        assert s.severity == 7

    def test_symptom_minimal(self):
        s = Symptom(name="头痛")
        assert s.name == "头痛"
        assert s.location is None

    def test_department(self):
        d = Department(name="神经内科", category="内科",
                       keywords=["头痛", "头晕"])
        assert d.name == "神经内科"
        assert len(d.keywords) == 2

    def test_voice_config(self):
        vc = VoiceConfig(voice_style="gentle", speech_rate=1.2)
        assert vc.voice_style == "gentle"
        assert vc.speech_rate == 1.2
