from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.user import User

import logging

logger = logging.getLogger(__name__)


async def require_consent(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> str:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证",
        )

    import uuid as _uuid
    result = await db.execute(
        select(User).where(User.id == _uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if not user.consent_given:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要签署知情同意书后才能使用问诊服务",
        )

    return user_id


async def record_consent(
    user_id: str,
    db: AsyncSession,
) -> None:
    import uuid as _uuid
    from datetime import datetime, timezone

    result = await db.execute(
        select(User).where(User.id == _uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if user:
        user.consent_given = True
        user.consent_at = datetime.now(timezone.utc)
        await db.flush()
        logger.info(f"User {user_id} consented at {datetime.now(timezone.utc).isoformat()}")