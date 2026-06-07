import uuid
import logging

from app.domain.entities import ConversationEntity, MessageEntity
from app.domain.repositories import ConversationRepository, DoctorRepository
from app.domain.services import AgentFactory, DiagnosisStateMachine
from app.domain.state_machine.diagnosis_machine import InvalidTransitionError
from app.domain.value_objects import ClinicalState

logger = logging.getLogger(__name__)


async def send_message(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    doctor_id: uuid.UUID,
    user_message: str,
    input_type: str,
    state_machine: DiagnosisStateMachine,
    clinical_state: ClinicalState,
    conv_repo: ConversationRepository,
    doctor_repo: DoctorRepository,
    factory: AgentFactory,
):
    clinical_state._last_user_message = user_message

    user_msg = MessageEntity(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role="user",
        content=user_message,
        input_type=input_type,
    )
    await conv_repo.add_message(user_msg)

    doctor = await doctor_repo.get_by_id(doctor_id)
    if not doctor:
        raise ValueError("Doctor not found")

    engine = factory.get_or_create(
        doctor_id=str(doctor_id),
        doctor_name=doctor.name,
        doctor_title=doctor.title,
        doctor_specialty=doctor.specialty,
        doctor_expertise=doctor.expertise or "",
    )

    history_entities = await conv_repo.get_messages(conversation_id, limit=50)
    history = [
        {"role": m.role, "content": m.content}
        for m in history_entities
    ]

    intent = await engine.generate_intent(user_message, history)
    event = state_machine.intent_to_event(intent, state_machine.state)

    try:
        new_stage = state_machine.transition(event)
    except InvalidTransitionError:
        logger.warning(
            "Invalid transition: state=%s event=%s intent=%s, falling back to collecting",
            state_machine.state, event, intent,
        )
        new_stage = "collecting"

    clinical_state.diagnosis_stage = new_stage
    clinical_state.current_intent = intent

    if intent in ("new_symptom", "follow_up_answer") and user_message not in clinical_state.symptoms:
        clinical_state.symptoms.append(user_message)

    response_text = await engine.generate_response(clinical_state, history, doctor_id=str(doctor_id))

    assistant_msg = MessageEntity(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role="assistant",
        content=response_text,
    )
    await conv_repo.add_message(assistant_msg)

    await conv_repo.update(ConversationEntity(
        id=conversation_id,
        user_id=user_id,
        doctor_id=doctor_id,
        diagnosis_stage=new_stage,
        symptoms=clinical_state.symptoms,
    ))

    return {
        "user_message": user_msg,
        "assistant_message": assistant_msg,
        "clinical_state": clinical_state,
        "state_machine": state_machine,
        "rag_sources": clinical_state.rag_sources,
    }
