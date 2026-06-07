import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import auth, chat, doctor, knowledge, favorite, upload
from app.api import ws
from app.infrastructure.persistence.database import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified on startup")
    except Exception as e:
        logger.warning("Database connection check failed on startup: %s", e)

    yield

    await engine.dispose()
    logger.info("Database engine disposed on shutdown")


app = FastAPI(
    title="SmartDoctor",
    description="AI 智能问诊助手",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(doctor.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(favorite.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(ws.router)


@app.get("/health")
async def health():
    try:
        from app.infrastructure.persistence.database import engine as async_engine
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "degraded", "db": f"error: {e}"}
