import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from jose import JWTError, jwt
from sqlalchemy import select

from app.config import get_settings
from app.infrastructure.llm import create_llm
from app.infrastructure.persistence.database import async_session
from app.infrastructure.persistence.models.conversation import Conversation
from app.infrastructure.persistence.repositories import SqlConversationRepository
from app.domain.entities import MessageEntity
from app.infrastructure.security.prompt_guard import sanitize_user_input, validate_output

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

_active_connections: dict[str, WebSocket] = {}

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = create_llm()
    return _llm


async def authenticate_websocket(websocket: WebSocket) -> str | None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return None
        return user_id
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return None


@router.websocket("/ws/chat/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: str):
    user_id = await authenticate_websocket(websocket)
    if not user_id:
        return

    # Verify conversation belongs to the current user
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
            )
            conv = result.scalar_one_or_none()
            if not conv or str(conv.user_id) != user_id:
                await websocket.close(code=4003, reason="Conversation not found or access denied")
                return
    except ValueError:
        await websocket.close(code=4002, reason="Invalid conversation_id")
        return

    await websocket.accept()
    _active_connections[f"{user_id}:{conversation_id}"] = websocket
    logger.info("WebSocket connected: user=%s conversation=%s", user_id, conversation_id)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg.get("type") != "message":
                continue

            content = msg.get("content", "")
            if not content.strip():
                await websocket.send_json({"type": "error", "content": "Empty message"})
                continue

            content = sanitize_user_input(content)

            # Persist user message
            try:
                async with async_session() as db_session:
                    conv_repo = SqlConversationRepository(db_session)
                    user_msg = MessageEntity(
                        id=uuid.uuid4(),
                        conversation_id=uuid.UUID(conversation_id),
                        role="user",
                        content=content,
                        input_type="text",
                    )
                    await conv_repo.add_message(user_msg)
                    await db_session.commit()
            except Exception:
                logger.exception("Failed to persist user message for conversation %s", conversation_id)

            await websocket.send_json({
                "type": "message_ack",
                "content": content,
            })

            await websocket.send_json({
                "type": "assistant_message_start",
                "conversation_id": conversation_id,
            })

            try:
                llm = _get_llm()
                stream = llm.chat_stream(
                    messages=[{"role": "user", "content": content}],
                    temperature=0.7,
                    max_tokens=1024,
                )
                full_response = ""
                async for chunk in stream:
                    full_response += chunk
                    await websocket.send_json({
                        "type": "assistant_message_delta",
                        "content": chunk,
                    })

                if not validate_output(full_response):
                    logger.warning("WebSocket assistant output flagged by security validator")
                    full_response = "抱歉，当前回答无法提供，请重新提问。"
                    await websocket.send_json({
                        "type": "assistant_message_delta",
                        "content": full_response,
                    })

                DISCLAIMER = "\n\n---\n*以上分析仅供参考，不能替代专业医生诊断，如有不适请及时就医。*"
                if DISCLAIMER not in full_response:
                    await websocket.send_json({
                        "type": "assistant_message_delta",
                        "content": DISCLAIMER,
                    })

                # Persist assistant message
                try:
                    async with async_session() as db_session:
                        conv_repo = SqlConversationRepository(db_session)
                        assistant_msg = MessageEntity(
                            id=uuid.uuid4(),
                            conversation_id=uuid.UUID(conversation_id),
                            role="assistant",
                            content=full_response,
                        )
                        await conv_repo.add_message(assistant_msg)
                        await db_session.commit()
                except Exception:
                    logger.exception("Failed to persist assistant message for conversation %s", conversation_id)
            except Exception as e:
                logger.exception("WebSocket LLM error for conversation %s", conversation_id)
                await websocket.send_json({
                    "type": "error",
                    "content": f"AI 服务暂时不可用：{str(e)}",
                })

            await websocket.send_json({
                "type": "assistant_message_end",
                "conversation_id": conversation_id,
            })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: user=%s conversation=%s", user_id, conversation_id)
    except Exception as e:
        logger.exception("WebSocket error for conversation %s: %s", conversation_id, e)
    finally:
        _active_connections.pop(f"{user_id}:{conversation_id}", None)