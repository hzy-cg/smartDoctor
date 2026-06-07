import uuid
from app.domain.entities import ConversationEntity, MessageEntity
from app.domain.repositories import ConversationRepository
from app.domain.services import AgentFactory, DiagnosisStateMachine
from app.domain.value_objects import ClinicalState


async def start_consultation(
    user_id: uuid.UUID,
    doctor_id: uuid.UUID,
    doctor_name: str,
    doctor_title: str,
    doctor_specialty: str,
    doctor_expertise: str,
    conv_repo: ConversationRepository,
    factory: AgentFactory,
) -> tuple[ConversationEntity, DiagnosisStateMachine]:
    engine = factory.get_or_create(
        doctor_id=str(doctor_id),
        doctor_name=doctor_name,
        doctor_title=doctor_title,
        doctor_specialty=doctor_specialty,
        doctor_expertise=doctor_expertise,
    )
    conversation = ConversationEntity(
        id=uuid.uuid4(),
        user_id=user_id,
        doctor_id=doctor_id,
        title=f"{doctor_specialty}问诊",
        diagnosis_stage="collecting",
    )
    conv = await conv_repo.create(conversation)
    state_machine = DiagnosisStateMachine()
    return conv, state_machine
