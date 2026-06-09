import uuid
import time
import logging
import json
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.infrastructure.persistence.database import get_db
from app.schemas.api_response import ApiResponse
from app.schemas.chat import ConversationResponse, MessageResponse, StartChatRequest, SendMessageRequest
from app.infrastructure.persistence.repositories import SqlConversationRepository, SqlDoctorRepository
from app.infrastructure.llm import create_llm
from app.domain.services import AgentFactory
from app.domain.services.diagnosis_strategy import RAGStrategy
from app.domain.services.reranker import CrossEncoderReranker
from app.domain.state_machine import DiagnosisStateMachine
from app.domain.value_objects import ClinicalState
from app.application.use_cases import start_consultation, send_message
from app.infrastructure.security.prompt_guard import sanitize_user_input, validate_output
from app.infrastructure.security.compliance import require_consent
from app.infrastructure.vectorstore.chroma_store import ChromaVectorStore

logger = logging.getLogger(__name__)

_SENSITIVE_KEYWORDS = ["自杀方法", "自残方式", "如何制造"]


def _check_chunk_safety(chunk: str) -> bool:
    return not any(kw in chunk for kw in _SENSITIVE_KEYWORDS)


router = APIRouter(prefix="/chat", tags=["chat"])

_agent_factory = None
_session_states: dict[str, tuple] = {}
_session_timestamps: dict[str, float] = {}
_session_lock = asyncio.Lock()

_SESSION_TTL = 1800  # 30 minutes


def _cleanup_sessions():
    now = time.time()
    expired = [k for k, v in _session_timestamps.items() if now - v > _SESSION_TTL]
    for k in expired:
        _session_states.pop(k, None)
        _session_timestamps.pop(k, None)


async def _restore_session_state(conversation_id: str, conv_repo, conv):
    """从数据库恢复会话状态"""
    _cleanup_sessions()
    sm = DiagnosisStateMachine()
    sm._state = conv.diagnosis_stage or "collecting"
    cs = ClinicalState(conversation_id=uuid.UUID(conversation_id))
    cs.diagnosis_stage = conv.diagnosis_stage or "collecting"
    cs.symptoms = list(conv.symptoms) if conv.symptoms else []
    cs.doctor_id = conv.doctor_id
    async with _session_lock:
        _session_states[conversation_id] = (sm, cs)
        _session_timestamps[conversation_id] = time.time()
    return sm, cs


_agent_factory = None
_reranker_instance = None  # 全局单例，与 lifespan 预加载共享


def _get_factory():
    global _agent_factory, _reranker_instance
    if _agent_factory is None:
        llm = create_llm()
        try:
            chroma_store = ChromaVectorStore()
            # 复用全局 reranker 单例（lifespan 中已预加载模型）
            if _reranker_instance is None:
                _reranker_instance = CrossEncoderReranker()
            rag_strategy = RAGStrategy(
                private_store=chroma_store,
                common_store=chroma_store,
                embedding=None,
                reranker=_reranker_instance,
            )
        except Exception as e:
            logger.warning("RAG initialization failed: %s, proceeding without RAG", e)
            rag_strategy = None
        _agent_factory = AgentFactory(llm=llm, rag_strategy=rag_strategy)
    return _agent_factory


@router.post("/conversations")
async def create_conversation(
    req: StartChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
    _: str = Depends(require_consent),
):
    doctor_repo = SqlDoctorRepository(db)
    doctor = await doctor_repo.get_by_id(uuid.UUID(req.doctor_id))
    if not doctor:
        raise HTTPException(status_code=404, detail="医生不存在")
    if not doctor.is_active:
        raise HTTPException(status_code=400, detail="该医生暂不可用")

    conv_repo = SqlConversationRepository(db)
    _cleanup_sessions()
    factory = _get_factory()

    conv, sm = await start_consultation(
        user_id=uuid.UUID(user_id),
        doctor_id=uuid.UUID(req.doctor_id),
        doctor_name=doctor.name,
        doctor_title=doctor.title,
        doctor_specialty=doctor.specialty,
        doctor_expertise=doctor.expertise or "",
        conv_repo=conv_repo,
        factory=factory,
    )
    clinical_state = ClinicalState(conversation_id=conv.id)
    async with _session_lock:
        _session_states[str(conv.id)] = (sm, clinical_state)
        _session_timestamps[str(conv.id)] = time.time()

    return ApiResponse(data=ConversationResponse(
        id=str(conv.id), doctor_id=str(conv.doctor_id),
        title=conv.title, interaction_mode=conv.interaction_mode,
        diagnosis_stage=conv.diagnosis_stage, symptoms=conv.symptoms,
        created_at=conv.created_at, updated_at=conv.updated_at,
    ))


@router.post("/conversations/{conversation_id}/messages")
async def send_message_to_conversation(
    conversation_id: str,
    req: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
    _: str = Depends(require_consent),
):
    conv_repo = SqlConversationRepository(db)
    conv = await conv_repo.get_by_id(uuid.UUID(conversation_id))
    if not conv or str(conv.user_id) != user_id:
        raise HTTPException(status_code=404, detail="对话不存在")

    _cleanup_sessions()

    sanitized_content = sanitize_user_input(req.content)
    if sanitized_content != req.content:
        logger.warning("User input sanitized for conversation %s", conversation_id)

    state = _session_states.get(conversation_id)
    if state is None:
        sm, cs = await _restore_session_state(conversation_id, conv_repo, conv)
    else:
        sm, cs = state
        _session_timestamps[conversation_id] = time.time()

    doctor_repo = SqlDoctorRepository(db)
    factory = _get_factory()

    try:
        result = await send_message(
            conversation_id=uuid.UUID(conversation_id),
            user_id=uuid.UUID(user_id),
            doctor_id=conv.doctor_id,
            user_message=sanitized_content,
            input_type=req.input_type,
            state_machine=sm,
            clinical_state=cs,
            conv_repo=conv_repo,
            doctor_repo=doctor_repo,
            factory=factory,
        )
        async with _session_lock:
            _session_states[conversation_id] = (result["state_machine"], result["clinical_state"])
            _session_timestamps[conversation_id] = time.time()

        assistant_content = result["assistant_message"].content
        if not validate_output(assistant_content):
            logger.warning("Assistant output flagged by security validator")
            assistant_content = "抱歉，当前回答无法提供，请重新提问。"

        DISCLAIMER = "\n\n---\n*以上分析仅供参考，不能替代专业医生诊断，如有不适请及时就医。*"
        if DISCLAIMER not in assistant_content:
            assistant_content += DISCLAIMER

        return ApiResponse(data={
            "user_message": MessageResponse(
                id=str(result["user_message"].id),
                conversation_id=str(result["user_message"].conversation_id),
                role="user", content=result["user_message"].content,
                input_type=result["user_message"].input_type,
                created_at=result["user_message"].created_at,
            ),
            "assistant_message": MessageResponse(
                id=str(result["assistant_message"].id),
                conversation_id=str(result["assistant_message"].conversation_id),
                role="assistant", content=assistant_content,
                input_type="text",
                created_at=result["assistant_message"].created_at,
            ),
            "sources": result.get("rag_sources", []),
        })
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"AI 服务暂时不可用：{str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/conversations/{conversation_id}/stream")
async def stream_message_to_conversation(
    conversation_id: str,
    req: SendMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
    _: str = Depends(require_consent),
):
    conv_repo = SqlConversationRepository(db)
    conv = await conv_repo.get_by_id(uuid.UUID(conversation_id))
    if not conv or str(conv.user_id) != user_id:
        raise HTTPException(status_code=404, detail="对话不存在")

    _cleanup_sessions()

    sanitized_content = sanitize_user_input(req.content)
    if sanitized_content != req.content:
        logger.warning("User input sanitized for conversation %s", conversation_id)

    doctor_repo = SqlDoctorRepository(db)
    factory = _get_factory()

    doctor = await doctor_repo.get_by_id(conv.doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="医生不存在")

    engine = factory.get_or_create(
        doctor_id=str(conv.doctor_id),
        doctor_name=doctor.name,
        doctor_title=doctor.title,
        doctor_specialty=doctor.specialty,
        doctor_expertise=doctor.expertise or "",
    )

    state = _session_states.get(conversation_id)
    if state is None:
        sm, cs = await _restore_session_state(conversation_id, conv_repo, conv)
    else:
        sm, cs = state
        _session_timestamps[conversation_id] = time.time()

    cs._last_user_message = sanitized_content

    history_entities = await conv_repo.get_messages(uuid.UUID(conversation_id), limit=50)
    history = [{"role": m.role, "content": m.content} for m in history_entities]

    intent = await engine.generate_intent(sanitized_content, history)
    event = sm.intent_to_event(intent, sm.state)

    try:
        new_stage = sm.transition(event)
    except Exception:
        new_stage = "collecting"

    cs.diagnosis_stage = new_stage
    cs.current_intent = intent
    if intent in ("new_symptom", "follow_up_answer") and sanitized_content not in cs.symptoms:
        cs.symptoms.append(sanitized_content)

    from app.domain.entities import MessageEntity
    user_msg = MessageEntity(
        id=uuid.uuid4(),
        conversation_id=uuid.UUID(conversation_id),
        role="user",
        content=sanitized_content,
        input_type=req.input_type,
    )
    await conv_repo.add_message(user_msg)

    # Capture variables for background task closure
    _conv_id = uuid.UUID(conversation_id)
    _user_id = uuid.UUID(user_id)
    _doctor_id = conv.doctor_id
    _new_stage = new_stage
    _symptoms = list(cs.symptoms)

    async def _save_assistant_message(full_response: str):
        """Background task to save assistant message and update conversation."""
        assistant_msg = MessageEntity(
            id=uuid.uuid4(),
            conversation_id=_conv_id,
            role="assistant",
            content=full_response,
        )
        await conv_repo.add_message(assistant_msg)

        from app.domain.entities import ConversationEntity
        await conv_repo.update(ConversationEntity(
            id=_conv_id,
            user_id=_user_id,
            doctor_id=_doctor_id,
            diagnosis_stage=_new_stage,
            symptoms=_symptoms,
        ))

    async def generate():
        full_response = ""
        unsafe_detected = False
        try:
            async for chunk in engine.generate_response_stream(cs, history, doctor_id=str(conv.doctor_id)):
                if not _check_chunk_safety(chunk):
                    logger.warning("Sensitive content detected in stream chunk, skipping")
                    unsafe_detected = True
                    continue
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            if not validate_output(full_response) or unsafe_detected:
                full_response = "抱歉，当前回答无法提供，请重新提问。"
                yield f"data: {json.dumps({'type': 'override', 'content': full_response})}\n\n"

            DISCLAIMER = "\n\n---\n*以上分析仅供参考，不能替代专业医生诊断，如有不适请及时就医。*"
            if DISCLAIMER not in full_response:
                full_response += DISCLAIMER
                yield f"data: {json.dumps({'type': 'chunk', 'content': DISCLAIMER})}\n\n"

            async with _session_lock:
                _session_states[conversation_id] = (sm, cs)
                _session_timestamps[conversation_id] = time.time()

            yield f"data: {json.dumps({'type': 'done', 'sources': cs.rag_sources})}\n\n"
        except Exception as e:
            logger.exception("Stream error for conversation %s", conversation_id)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            # Ensure assistant message is saved even if client disconnects
            try:
                await _save_assistant_message(full_response)
            except Exception:
                logger.exception("Failed to save assistant message for conversation %s", conversation_id)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    conv_repo = SqlConversationRepository(db)
    convs = await conv_repo.list_by_user(uuid.UUID(user_id))
    return ApiResponse(data=[
        ConversationResponse(
            id=str(c.id), doctor_id=str(c.doctor_id), title=c.title,
            interaction_mode=c.interaction_mode,
            diagnosis_stage=c.diagnosis_stage,
            symptoms=c.symptoms,
            created_at=c.created_at, updated_at=c.updated_at,
        ) for c in convs
    ])


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    conv_repo = SqlConversationRepository(db)
    conv = await conv_repo.get_by_id(uuid.UUID(conversation_id))
    if not conv or str(conv.user_id) != user_id:
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = await conv_repo.get_messages(uuid.UUID(conversation_id), limit=limit, offset=offset)
    return ApiResponse(data=[
        MessageResponse(
            id=str(m.id), conversation_id=str(m.conversation_id),
            role=m.role, content=m.content,
            input_type=m.input_type, created_at=m.created_at,
        ) for m in messages
    ])
