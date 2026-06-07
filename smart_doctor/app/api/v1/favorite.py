import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.infrastructure.persistence.database import get_db
from app.schemas.api_response import ApiResponse
from app.schemas.favorite import FavoriteToggleRequest, FavoriteResponse
from app.infrastructure.persistence.repositories import SqlDoctorRepository

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("")
async def toggle_favorite(
    req: FavoriteToggleRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    repo = SqlDoctorRepository(db)
    try:
        doctor_uuid = uuid.UUID(req.doctor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的 doctor_id")
    doctor = await repo.get_by_id(doctor_uuid)
    if not doctor:
        raise HTTPException(status_code=404, detail="医生不存在")
    action = await repo.toggle_favorite(uuid.UUID(user_id), doctor_uuid)
    return ApiResponse(data={
        "user_id": user_id,
        "doctor_id": req.doctor_id,
        "action": action,
    })


@router.get("")
async def list_favorites(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    repo = SqlDoctorRepository(db)
    favorites = await repo.get_favorites(uuid.UUID(user_id))
    return ApiResponse(data=[
        FavoriteResponse(
            id=str(f.id),
            user_id=str(f.user_id),
            doctor_id=str(f.doctor_id),
            created_at=f.created_at,
        ) for f in favorites
    ])