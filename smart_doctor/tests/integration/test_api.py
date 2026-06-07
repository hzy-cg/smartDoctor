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
        r = await ac.post("/api/v1/auth/register", json={
            "username": uname, "password": "test123"
        })
        token = r.json()["data"]["token"]
        yield {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestHealthCheck:
    async def test_health(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
class TestAuthRoute:

    async def test_register_success(self, client):
        uname = f"t_{uuid.uuid4().hex[:8]}"
        r = await client.post("/api/v1/auth/register", json={
            "username": uname, "password": "test123"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert data["data"]["token"]

    async def test_register_duplicate(self, client):
        uname = f"dup_{uuid.uuid4().hex[:8]}"
        r1 = await client.post("/api/v1/auth/register", json={
            "username": uname, "password": "test123"
        })
        assert r1.status_code == 200
        r2 = await client.post("/api/v1/auth/register", json={
            "username": uname, "password": "test123"
        })
        assert r2.status_code == 400

    async def test_login_success(self, client):
        uname = f"li_{uuid.uuid4().hex[:8]}"
        await client.post("/api/v1/auth/register", json={
            "username": uname, "password": "test123"
        })
        r = await client.post("/api/v1/auth/login", json={
            "username": uname, "password": "test123"
        })
        assert r.status_code == 200
        assert r.json()["code"] == 0
        assert r.json()["data"]["token"]

    async def test_login_wrong_password(self, client):
        uname = f"bad_{uuid.uuid4().hex[:8]}"
        await client.post("/api/v1/auth/register", json={
            "username": uname, "password": "test123"
        })
        r = await client.post("/api/v1/auth/login", json={
            "username": uname, "password": "wrong"
        })
        assert r.status_code == 401

    async def test_login_nonexistent(self, client):
        r = await client.post("/api/v1/auth/login", json={
            "username": "nobody_xyz", "password": "test123"
        })
        assert r.status_code == 401

    async def test_jwt_token_structure(self, client):
        uname = f"jwt_{uuid.uuid4().hex[:8]}"
        r = await client.post("/api/v1/auth/register", json={
            "username": uname, "password": "test123"
        })
        token = r.json()["data"]["token"]
        assert len(token) > 50
        assert token.count(".") == 2


@pytest.mark.asyncio
class TestAuthMiddleware:

    async def test_doctors_unauthorized(self, client):
        r = await client.get("/api/v1/doctors")
        assert r.status_code == 401

    async def test_chat_unauthorized(self, client):
        r = await client.post("/api/v1/chat/conversations",
                              json={"doctor_id": str(uuid.uuid4())})
        assert r.status_code == 401

    async def test_chat_get_unauthorized(self, client):
        r = await client.get("/api/v1/chat/conversations")
        assert r.status_code == 401

    async def test_doctors_authorized(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/doctors", headers=auth_headers)
            assert r.status_code == 200
            assert r.json()["code"] == 0

    async def test_chat_list_authorized(self, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/chat/conversations", headers=auth_headers)
            assert r.status_code == 200
            assert r.json()["code"] == 0