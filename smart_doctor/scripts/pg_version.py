import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def main():
    e = create_async_engine(
        "postgresql+asyncpg://postgres:123456@192.168.1.106:5432/smart_doctor"
    )
    async with e.connect() as conn:
        r = await conn.execute(text("SELECT version()"))
        print(r.scalar())
    await e.dispose()


asyncio.run(main())
