import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def main():
    e = create_async_engine(
        "postgresql+asyncpg://postgres:123456@192.168.1.106:5432/smart_doctor"
    )
    async with e.connect() as conn:
        r = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        )
        tables = [t for t in r.scalars().all() if t != "alembic_version"]
        for t in tables:
            print(t)
        print(f"\nTotal: {len(tables)} tables")
    await e.dispose()


asyncio.run(main())
