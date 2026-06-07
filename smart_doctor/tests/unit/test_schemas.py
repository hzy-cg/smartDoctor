import pytest
from uuid import uuid4

from app.schemas.doctor import DoctorResponse, DoctorCreateRequest
from app.schemas.chat import (
    ConversationResponse, MessageResponse,
    StartChatRequest, SendMessageRequest
)
from app.schemas.api_response import ApiResponse, PaginatedResponse


class TestDoctorSchemas:

    def test_doctor_response_creation(self):
        doctor_id = str(uuid4())
        resp = DoctorResponse(
            id=doctor_id,
            name="张医生",
            title="主任医师",
            specialty="神经内科",
            expertise="头痛、头晕",
            rating=5.0,
            lifecycle_state="active",
            has_digital_human=False
        )
        assert resp.id == doctor_id
        assert resp.name == "张医生"

    def test_doctor_create_schema(self):
        create = DoctorCreateRequest(
            name="李医生",
            title="副主任医师",
            specialty="内科",
            expertise="感冒、发烧"
        )
        assert create.name == "李医生"
        assert create.specialty == "内科"

    def test_doctor_response_with_optional_fields(self):
        resp = DoctorResponse(
            id=str(uuid4()),
            name="测试医生",
            title="医师",
            specialty="测试科",
            rating=5.0,
            lifecycle_state="draft",
            has_digital_human=False
        )
        assert resp.expertise is None


class TestChatSchemas:

    def test_conversation_response(self):
        conv_id = str(uuid4())
        resp = ConversationResponse(
            id=conv_id,
            doctor_id=str(uuid4()),
            title="神经内科问诊",
            interaction_mode="text",
            diagnosis_stage="collecting"
        )
        assert resp.diagnosis_stage == "collecting"

    def test_message_response(self):
        resp = MessageResponse(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            role="user",
            content="我最近头痛",
            input_type="text"
        )
        assert resp.role == "user"

    def test_start_chat_request(self):
        req = StartChatRequest(doctor_id=str(uuid4()))
        assert req.doctor_id

    def test_send_message_request(self):
        req = SendMessageRequest(content="头痛持续三天", input_type="text")
        assert req.content == "头痛持续三天"


class TestApiResponseSchemas:

    def test_api_response_success(self):
        resp = ApiResponse(code=0, message="success", data={"key": "value"})
        assert resp.code == 0
        assert resp.message == "success"

    def test_api_response_error(self):
        resp = ApiResponse(code=400, message="Bad Request")
        assert resp.code == 400
        assert resp.data is None

    def test_paginated_response(self):
        resp = PaginatedResponse(
            code=0,
            data={"items": [{"id": 1}, {"id": 2}], "total": 10, "page": 1}
        )
        assert resp.code == 0
        assert resp.data["total"] == 10