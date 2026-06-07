import uuid
from app.domain.repositories import DoctorRepository


async def toggle_favorite(user_id: str, doctor_id: str, conv_repo: DoctorRepository) -> dict:
    action = await conv_repo.toggle_favorite(uuid.UUID(user_id), uuid.UUID(doctor_id))
    return {
        "user_id": user_id,
        "doctor_id": doctor_id,
        "action": action,
    }