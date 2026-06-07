import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.infrastructure.persistence.models.doctor import DoctorRole as DoctorRoleModel
from app.infrastructure.persistence.models.doctor import DigitalHuman, DoctorKnowledge, Favorite
from app.domain.entities import DoctorRoleEntity


class SqlDoctorRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, doctor_id: uuid.UUID) -> DoctorRoleEntity | None:
        stmt = select(DoctorRoleModel).where(DoctorRoleModel.id == doctor_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_active(self, specialty: str | None = None, title: str | None = None,
                          order_by_rating: bool = False) -> list[DoctorRoleEntity]:
        stmt = select(DoctorRoleModel).where(DoctorRoleModel.lifecycle_state == "active")
        if specialty:
            stmt = stmt.where(DoctorRoleModel.specialty == specialty)
        if title:
            stmt = stmt.where(DoctorRoleModel.title == title)
        if order_by_rating:
            stmt = stmt.order_by(DoctorRoleModel.rating.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_all(self, lifecycle_state: str | None = None, specialty: str | None = None) -> list[DoctorRoleEntity]:
        stmt = select(DoctorRoleModel)
        if lifecycle_state:
            stmt = stmt.where(DoctorRoleModel.lifecycle_state == lifecycle_state)
        if specialty:
            stmt = stmt.where(DoctorRoleModel.specialty == specialty)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, doctor: DoctorRoleEntity) -> DoctorRoleEntity:
        model = await self._session.merge(self._to_model(doctor))
        await self._session.flush()
        return self._to_entity(model)

    async def delete(self, doctor_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(DigitalHuman).where(DigitalHuman.doctor_id == doctor_id)
        )
        await self._session.execute(
            delete(DoctorKnowledge).where(DoctorKnowledge.doctor_id == doctor_id)
        )
        await self._session.execute(
            delete(Favorite).where(Favorite.doctor_id == doctor_id)
        )
        await self._session.execute(
            delete(DoctorRoleModel).where(DoctorRoleModel.id == doctor_id)
        )

    async def activate(self, doctor_id: uuid.UUID) -> DoctorRoleEntity:
        await self._session.execute(
            update(DoctorRoleModel)
            .where(DoctorRoleModel.id == doctor_id)
            .values(lifecycle_state="active", activated_at=datetime.now(timezone.utc))
        )
        model = await self._session.get(DoctorRoleModel, doctor_id)
        return self._to_entity(model) if model else None

    async def deactivate(self, doctor_id: uuid.UUID) -> None:
        await self._session.execute(
            update(DoctorRoleModel)
            .where(DoctorRoleModel.id == doctor_id)
            .values(lifecycle_state="inactive")
        )

    async def toggle_favorite(self, user_id: uuid.UUID, doctor_id: uuid.UUID) -> str:
        stmt = select(Favorite).where(
            Favorite.user_id == user_id, Favorite.doctor_id == doctor_id
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            await self._session.execute(
                delete(Favorite).where(
                    Favorite.user_id == user_id, Favorite.doctor_id == doctor_id
                )
            )
            await self._session.flush()
            return "removed"
        favorite = Favorite(user_id=user_id, doctor_id=doctor_id)
        self._session.add(favorite)
        await self._session.flush()
        return "added"

    async def get_favorites(self, user_id: uuid.UUID) -> list[Favorite]:
        stmt = select(Favorite).where(Favorite.user_id == user_id).order_by(Favorite.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    def _to_entity(self, model: DoctorRoleModel) -> DoctorRoleEntity:
        return DoctorRoleEntity(
            id=model.id,
            name=model.name,
            title=model.title,
            specialty=model.specialty,
            expertise=model.expertise,
            experience=model.experience,
            education=model.education,
            avatar_url=model.avatar_url,
            rating=model.rating,
            lifecycle_state=model.lifecycle_state,
            has_digital_human=model.has_digital_human,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: DoctorRoleEntity) -> DoctorRoleModel:
        return DoctorRoleModel(
            id=entity.id,
            name=entity.name,
            title=entity.title,
            specialty=entity.specialty,
            expertise=entity.expertise,
            experience=entity.experience,
            education=entity.education,
            avatar_url=entity.avatar_url,
            rating=entity.rating,
            lifecycle_state=entity.lifecycle_state,
            has_digital_human=entity.has_digital_human,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
