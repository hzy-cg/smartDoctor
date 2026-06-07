import asyncio
from app.infrastructure.persistence.database import get_engine

async def test_db():
    try:
        engine = await get_engine()
        async with engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            print("✓ Database connection: OK")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_db())