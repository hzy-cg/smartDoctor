import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON

from app.infrastructure.persistence.database import Base


class DoctorRole(Base):
    __tablename__ = "doctor_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    specialty: Mapped[str] = mapped_column(String(64), nullable=False)
    expertise: Mapped[str | None] = mapped_column(nullable=True)
    experience: Mapped[str | None] = mapped_column(nullable=True)
    education: Mapped[str | None] = mapped_column(nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    rating: Mapped[float] = mapped_column(default=5.0, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    has_digital_human: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    digital_human: Mapped["DigitalHuman"] = relationship(back_populates="doctor", uselist=False)
    doctor_knowledge: Mapped[list["DoctorKnowledge"]] = relationship(back_populates="doctor")


class DigitalHuman(Base):
    __tablename__ = "digital_humans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("doctor_roles.id"), unique=True, nullable=False)
    model_type: Mapped[str] = mapped_column(String(16), default="live2d", nullable=False)
    model_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    texture_urls: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    voice_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    speech_rate: Mapped[float] = mapped_column(default=1.0, nullable=False)
    pitch: Mapped[float] = mapped_column(default=1.0, nullable=False)
    interaction_style: Mapped[str] = mapped_column(String(32), default="professional", nullable=False)
    greeting_motion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    thinking_motion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    caring_motion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    custom_motions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    doctor: Mapped["DoctorRole"] = relationship(back_populates="digital_human")


class DoctorKnowledge(Base):
    __tablename__ = "doctor_knowledge"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("doctor_roles.id"), nullable=False)
    knowledge_doc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_docs.id"), nullable=False)
    access_level: Mapped[str] = mapped_column(String(16), default="shared", nullable=False)

    doctor: Mapped["DoctorRole"] = relationship(back_populates="doctor_knowledge")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint('user_id', 'doctor_id', name='uq_user_doctor_favorite'),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("doctor_roles.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
