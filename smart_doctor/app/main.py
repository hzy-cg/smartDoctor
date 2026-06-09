import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import auth, chat, doctor, knowledge, favorite, upload
from app.api import ws
from app.infrastructure.persistence.database import engine

logger = logging.getLogger(__name__)


def _preload_models():
    """在后台线程预加载 Reranker 模型，避免首次请求阻塞"""
    import threading

    def _load():
        try:
            from app.domain.services.reranker import CrossEncoderReranker
            reranker = CrossEncoderReranker()
            reranker.preload()
            # 存入 chat 模块的全局变量，与 _get_factory 共享实例
            from app.api.v1 import chat
            chat._reranker_instance = reranker
        except Exception as e:
            logger.warning("Reranker preload failed: %s (will use TF-IDF fallback)", e)

    t = threading.Thread(target=_load, daemon=True)
    t.start()
    logger.info("Reranker model preloading started in background")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified on startup")
    except Exception as e:
        logger.warning("Database connection check failed on startup: %s", e)

    # 后台预加载 Reranker 模型，不阻塞启动
    _preload_models()

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
