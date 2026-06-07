import uuid
from app.domain.entities import DoctorRoleEntity
from app.domain.repositories import DoctorRepository
from app.domain.services import AgentFactory


async def create_doctor(
    name: str, title: str, specialty: str,
    expertise: str | None, experience: str | None,
    education: str | None, repo: DoctorRepository,
) -> DoctorRoleEntity:
    doctor = DoctorRoleEntity(
        id=uuid.uuid4(),
        name=name, title=title, specialty=specialty,
        expertise=expertise, experience=experience, education=education,
    )
    return await repo.save(doctor)


async def activate_doctor(doctor_id: uuid.UUID, repo: DoctorRepository,
                          factory: AgentFactory) -> DoctorRoleEntity:
    doctor = await repo.activate(doctor_id)
    if doctor:
        factory.invalidate(str(doctor_id))
    return doctor


async def deactivate_doctor(doctor_id: uuid.UUID, repo: DoctorRepository,
                            factory: AgentFactory) -> None:
    await repo.deactivate(doctor_id)
    factory.invalidate(str(doctor_id))


async def list_active_doctors(specialty: str | None, repo: DoctorRepository
                              ) -> list[DoctorRoleEntity]:
    return await repo.list_active(specialty=specialty, order_by_rating=True)
