import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models.user import User as UserModel
from app.schemas.api_response import ApiResponse
from app.schemas.doctor import DoctorResponse, DoctorCreateRequest
from app.infrastructure.persistence.repositories import SqlDoctorRepository
from app.application.use_cases.manage_doctor import create_doctor, activate_doctor, deactivate_doctor
from app.domain.services import AgentFactory

router = APIRouter(prefix="/doctors", tags=["doctors"])

_doctor_factory = None


async def require_admin(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> str:
    result = await db.execute(select(UserModel).where(UserModel.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not getattr(user, 'is_admin', False):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user_id


def _get_factory() -> AgentFactory:
    global _doctor_factory
    if _doctor_factory is None:
        from app.infrastructure.llm import create_llm
        from app.domain.services.diagnosis_strategy import RAGStrategy
        from app.infrastructure.vectorstore.chroma_store import ChromaVectorStore
        llm = create_llm()
        try:
            chroma_store = ChromaVectorStore()
            rag_strategy = RAGStrategy(private_store=chroma_store, common_store=chroma_store, embedding=None)
        except Exception:
            rag_strategy = None
        _doctor_factory = AgentFactory(llm=llm, rag_strategy=rag_strategy)
    return _doctor_factory


@router.get("")
async def list_doctors(specialty: str | None = None,
                       lifecycle_state: str | None = None,
                       db: AsyncSession = Depends(get_db),
                       user_id: str = Depends(get_current_user)):
    repo = SqlDoctorRepository(db)
    if lifecycle_state:
        doctors = await repo.list_all(lifecycle_state=lifecycle_state, specialty=specialty)
    else:
        doctors = await repo.list_active(specialty=specialty, order_by_rating=True)
    return ApiResponse(data=[
        DoctorResponse(
            id=str(d.id), name=d.name, title=d.title,
            specialty=d.specialty, expertise=d.expertise,
            experience=d.experience, education=d.education,
            avatar_url=d.avatar_url, rating=d.rating,
            lifecycle_state=d.lifecycle_state,
            has_digital_human=d.has_digital_human,
            created_at=d.created_at,
        ) for d in doctors
    ])


@router.get("/{doctor_id}")
async def get_doctor(doctor_id: str, db: AsyncSession = Depends(get_db),
                     user_id: str = Depends(get_current_user)):
    repo = SqlDoctorRepository(db)
    doctor = await repo.get_by_id(uuid.UUID(doctor_id))
    if not doctor:
        raise HTTPException(status_code=404, detail="医生不存在")
    return ApiResponse(data=DoctorResponse(
        id=str(doctor.id), name=doctor.name, title=doctor.title,
        specialty=doctor.specialty, expertise=doctor.expertise,
        experience=doctor.experience, education=doctor.education,
        avatar_url=doctor.avatar_url, rating=doctor.rating,
        lifecycle_state=doctor.lifecycle_state,
        has_digital_human=doctor.has_digital_human,
        created_at=doctor.created_at,
    ))


@router.post("/create")
async def create_doctor_endpoint(req: DoctorCreateRequest,
                                 db: AsyncSession = Depends(get_db),
                                 user_id: str = Depends(get_current_user)):
    repo = SqlDoctorRepository(db)
    doctor = await create_doctor(
        name=req.name, title=req.title, specialty=req.specialty,
        expertise=req.expertise, experience=req.experience,
        education=req.education, repo=repo,
    )
    return ApiResponse(data=DoctorResponse(
        id=str(doctor.id), name=doctor.name, title=doctor.title,
        specialty=doctor.specialty, expertise=doctor.expertise,
        experience=doctor.experience, education=doctor.education,
        avatar_url=doctor.avatar_url, rating=doctor.rating,
        lifecycle_state=doctor.lifecycle_state,
        has_digital_human=doctor.has_digital_human,
        created_at=doctor.created_at,
    ))


@router.put("/{doctor_id}/activate")
async def activate_doctor_endpoint(doctor_id: str,
                                   db: AsyncSession = Depends(get_db),
                                   user_id: str = Depends(require_admin)):
    repo = SqlDoctorRepository(db)
    factory = _get_factory()
    try:
        doctor = await activate_doctor(uuid.UUID(doctor_id), repo, factory)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not doctor:
        raise HTTPException(status_code=404, detail="医生不存在")
    return ApiResponse(data=DoctorResponse(
        id=str(doctor.id), name=doctor.name, title=doctor.title,
        specialty=doctor.specialty, expertise=doctor.expertise,
        experience=doctor.experience, education=doctor.education,
        avatar_url=doctor.avatar_url, rating=doctor.rating,
        lifecycle_state=doctor.lifecycle_state,
        has_digital_human=doctor.has_digital_human,
        created_at=doctor.created_at,
    ))


@router.put("/{doctor_id}/deactivate")
async def deactivate_doctor_endpoint(doctor_id: str,
                                     db: AsyncSession = Depends(get_db),
                                     user_id: str = Depends(require_admin)):
    repo = SqlDoctorRepository(db)
    factory = _get_factory()
    try:
        await deactivate_doctor(uuid.UUID(doctor_id), repo, factory)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ApiResponse(data=None, message="医生已停用")