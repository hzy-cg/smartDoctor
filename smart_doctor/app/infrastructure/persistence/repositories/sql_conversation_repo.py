import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.infrastructure.persistence.models.conversation import Conversation as ConversationModel
from app.infrastructure.persistence.models.conversation import Message as MessageModel
from app.domain.entities import ConversationEntity, MessageEntity


class SqlConversationRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, conversation_id: uuid.UUID) -> ConversationEntity | None:
        stmt = select(ConversationModel).where(ConversationModel.id == conversation_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._conv_to_entity(model) if model else None

    async def list_by_user(self, user_id: uuid.UUID, limit: int = 50,
                           offset: int = 0) -> list[ConversationEntity]:
        stmt = (select(ConversationModel)
                .where(ConversationModel.user_id == user_id)
                .order_by(ConversationModel.updated_at.desc())
                .offset(offset).limit(limit))
        result = await self._session.execute(stmt)
        return [self._conv_to_entity(m) for m in result.scalars().all()]

    async def create(self, conversation: ConversationEntity) -> ConversationEntity:
        model = ConversationModel(
            id=conversation.id,
            user_id=conversation.user_id,
            doctor_id=conversation.doctor_id,
            title=conversation.title,
            interaction_mode=conversation.interaction_mode,
            diagnosis_stage=conversation.diagnosis_stage,
            symptoms=conversation.symptoms,
            summary=conversation.summary,
            knowledge_version=conversation.knowledge_version,
            expires_at=conversation.expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._conv_to_entity(model)

    async def update(self, conversation: ConversationEntity) -> ConversationEntity:
        model = await self._session.get(ConversationModel, conversation.id)
        if model:
            model.title = conversation.title
            model.interaction_mode = conversation.interaction_mode
            model.diagnosis_stage = conversation.diagnosis_stage
            model.symptoms = conversation.symptoms
            model.summary = conversation.summary
            model.knowledge_version = conversation.knowledge_version
            model.updated_at = datetime.now(timezone.utc)
            await self._session.flush()
            return self._conv_to_entity(model)
        raise ValueError(f"Conversation {conversation.id} not found")

    async def delete(self, conversation_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(MessageModel).where(MessageModel.conversation_id == conversation_id)
        )
        await self._session.execute(
            delete(ConversationModel).where(ConversationModel.id == conversation_id)
        )

    async def add_message(self, message: MessageEntity) -> MessageEntity:
        model = MessageModel(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            input_type=message.input_type,
            audio_url=message.audio_url,
            tool_calls=message.tool_calls,
            metadata=message.extra_metadata,
            disclaimer_shown=message.disclaimer_shown,
        )
        self._session.add(model)
        await self._session.flush()
        return self._msg_to_entity(model)

    async def get_messages(self, conversation_id: uuid.UUID,
                           limit: int = 100, offset: int = 0) -> list[MessageEntity]:
        stmt = (select(MessageModel)
                .where(MessageModel.conversation_id == conversation_id)
                .order_by(MessageModel.created_at.asc())
                .offset(offset)
                .limit(limit))
        result = await self._session.execute(stmt)
        return [self._msg_to_entity(m) for m in result.scalars().all()]

    def _conv_to_entity(self, model: ConversationModel) -> ConversationEntity:
        return ConversationEntity(
            id=model.id,
            user_id=model.user_id,
            doctor_id=model.doctor_id,
            title=model.title,
            interaction_mode=model.interaction_mode,
            diagnosis_stage=model.diagnosis_stage,
            symptoms=model.symptoms,
            summary=model.summary,
            knowledge_version=model.knowledge_version,
            expires_at=model.expires_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _msg_to_entity(self, model: MessageModel) -> MessageEntity:
        return MessageEntity(
            id=model.id,
            conversation_id=model.conversation_id,
            role=model.role,
            content=model.content,
            input_type=model.input_type,
            audio_url=model.audio_url,
            tool_calls=model.tool_calls,
            extra_metadata=model.extra_metadata,
            disclaimer_shown=model.disclaimer_shown,
            created_at=model.created_at,
        )
