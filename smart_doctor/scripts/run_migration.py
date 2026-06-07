"""Run database migrations directly via SQLAlchemy."""
import asyncio
from app.infrastructure.persistence.database import engine, Base
from app.infrastructure.persistence.models.upload_session import UploadSession  # noqa: F401


async def run():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Migration complete: knowledge_uploads table created (if not exists)")

asyncio.run(run())
