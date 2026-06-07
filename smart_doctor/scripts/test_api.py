from app.main import app
from fastapi.testclient import TestClient

c = TestClient(app)

r = c.get("/health")
print("Health:", r.json())

r2 = c.post("/api/v1/auth/register?username=admin&password=123456")
print("Register:", r2.json())

r3 = c.post("/api/v1/auth/login?username=admin&password=123456")
print("Login:", r3.json()["code"])
