import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        uname = f"e2e_{uuid.uuid4().hex[:8]}"
        r = await ac.post("/api/v1/auth/register", json={"username": uname, "password": "test123"})
        token = r.json()["data"]["token"]
        yield {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestChatAPI:

    async def test_create_conversation_unauthorized(self, client):
        r = await client.post("/api/v1/chat/conversations", json={
            "doctor_id": str(uuid.uuid4())
        })
        assert r.status_code == 401

    async def test_send_message_unauthorized(self, client):
        r = await client.post(f"/api/v1/chat/conversations/{uuid.uuid4()}/messages", json={
            "content": "测试消息",
            "input_type": "text"
        })
        assert r.status_code == 401

    async def test_get_conversations_unauthorized(self, client):
        r = await client.get("/api/v1/chat/conversations")
        assert r.status_code == 401

    async def test_conversations_list_empty(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/chat/conversations", headers=auth_headers)
            assert r.status_code == 200
            assert r.json()["code"] == 0
            assert isinstance(r.json()["data"], list)


@pytest.mark.asyncio
class TestDoctorAPI:

    async def test_list_doctors_unauthorized(self, client):
        r = await client.get("/api/v1/doctors")
        assert r.status_code == 401

    async def test_list_doctors_authorized(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/doctors", headers=auth_headers)
            assert r.status_code == 200
            assert r.json()["code"] == 0

    async def test_get_doctor_not_found(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            fake_id = str(uuid.uuid4())
            r = await ac.get(f"/api/v1/doctors/{fake_id}", headers=auth_headers)
            assert r.status_code == 404


@pytest.mark.asyncio
class TestEdgeCases:

    async def test_invalid_endpoint(self, client):
        r = await client.get("/api/v1/nonexistent")
        assert r.status_code in [404, 405]

    async def test_health_endpoint_no_auth(self, client):
        r = await client.get("/health")
        assert r.status_code == 200