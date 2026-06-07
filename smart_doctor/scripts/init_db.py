import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def main():
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:123456@192.168.1.106:5432/postgres",
        isolation_level="AUTOCOMMIT",
    )
    async with engine.connect() as conn:
        r = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname='smart_doctor'")
        )
        if r.scalar():
            print("Database already exists")
        else:
            await conn.execute(text("CREATE DATABASE smart_doctor"))
            print("Database created")
    await engine.dispose()

    e2 = create_async_engine(
        "postgresql+asyncpg://postgres:123456@192.168.1.106:5432/smart_doctor"
    )
    async with e2.connect() as conn:
        r = await conn.execute(text("SELECT 1"))
        print("PostgreSQL OK:", r.scalar())
    await e2.dispose()


asyncio.run(main())
