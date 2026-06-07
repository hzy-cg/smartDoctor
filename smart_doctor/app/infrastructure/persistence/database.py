import logging
import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_is_testing = os.environ.get("TESTING", "").lower() == "true"

_pool_config = {
    "poolclass": NullPool,
} if _is_testing else {
    "poolclass": AsyncAdaptedQueuePool,
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 900,
    "pool_pre_ping": True,
    "pool_reset_on_return": "rollback",
}

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={
        "timeout": 10,
        "command_timeout": 60,
        # SSL disabled for local development; enable in production via environment variable
        "ssl": False,
        "server_settings": {
            "application_name": "smart_doctor",
        },
    },
    **_pool_config,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    session = async_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()