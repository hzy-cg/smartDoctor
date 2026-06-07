from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
import bcrypt

from app.config import get_settings
from app.api.deps import get_current_user
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.user import User
from app.infrastructure.security.compliance import record_consent
from app.schemas.api_response import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6)


class AuthResponse(BaseModel):
    user_id: str
    token: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        existing = await db.execute(select(User).where(User.username == req.username))
    except Exception as e:
        logger.exception("DB error in register: %s", e)
        raise HTTPException(status_code=503, detail="数据库连接异常，请稍后重试")

    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=req.username,
        hashed_password=_hash_password(req.password),
    )
    db.add(user)
    await db.flush()
    token = _create_token(str(user.id))
    return ApiResponse(data=AuthResponse(user_id=str(user.id), token=token))


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.username == req.username))
    except Exception as e:
        logger.exception("DB error in login: %s", e)
        raise HTTPException(status_code=503, detail="数据库连接异常，请稍后重试")

    user = result.scalar_one_or_none()
    if not user or not _verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = _create_token(str(user.id))
    return ApiResponse(data=AuthResponse(user_id=str(user.id), token=token))


def _create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/consent")
async def consent(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    await record_consent(user_id, db)
    await db.commit()
    return ApiResponse(data={"message": "知情同意书已签署"})
