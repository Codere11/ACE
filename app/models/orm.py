# app/models/orm.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.db import Base

# ---------- Clients ----------
class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # e.g., "novak-realty"
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    # human name
    name: Mapped[str] = mapped_column(String(160), index=True)
    # optional subdomain, e.g., "ace.novak.si"
    subdomain: Mapped[Optional[str]] = mapped_column(String(160))
    # per-client LLM key you may proxy/use
    deepseek_api_key: Mapped[Optional[str]] = mapped_column(String(200))
    # raw JSON pulled from your /data/*.json for this client (or path to it)
    conversation_config: Mapped[Optional[dict]] = mapped_column(JSON)
    conversation_flow: Mapped[Optional[dict]] = mapped_column(JSON)
    # on/off
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation", back_populates="client", cascade="all, delete-orphan"
    )
    leads: Mapped[list[Lead]] = relationship(
        "Lead", back_populates="client", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_clients_active_slug", "active", "slug"),
    )


# ---------- Conversations (one per visitor/session) ----------
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    # Your existing SID from the frontend
    sid: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # optional denormalized tracking
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    client: Mapped[Client] = relationship("Client", back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    events: Mapped[list[Event]] = relationship(
        "Event", back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("client_id", "sid", name="uq_conversations_client_sid"),
    )


# ---------- Messages ----------
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant" | "staff"
    text: Mapped[str] = mapped_column(Text)
    # epoch seconds in your Pydantic schema => store as DateTime too
    ts_epoch: Mapped[int] = mapped_column(Integer)  # keep 1:1 with current API
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        CheckConstraint("role in ('user','assistant','staff')", name="chk_messages_role"),
        Index("ix_messages_conv_ts", "conversation_id", "ts_epoch"),
    )


# ---------- Leads (per client) ----------
class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)

    # Link to conversation if you want
    conversation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), index=True
    )

    # Fields aligned with your Pydantic Lead model
    sid: Mapped[str] = mapped_column(String(64), index=True)  # store visitor sid
    name: Mapped[str] = mapped_column(String(160), default="")
    industry: Mapped[str] = mapped_column(String(120), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str] = mapped_column(String(60), default="awareness")
    compatibility: Mapped[bool] = mapped_column(Boolean, default=False)
    interest: Mapped[str] = mapped_column(String(16), default="Low")
    phone: Mapped[bool] = mapped_column(Boolean, default=False)
    email: Mapped[bool] = mapped_column(Boolean, default=False)
    adsExp: Mapped[bool] = mapped_column(Boolean, default=False)
    lastMessage: Mapped[str] = mapped_column(Text, default="")
    lastSeenSec: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    # Survey tracking
    survey_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    survey_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    survey_answers: Mapped[Optional[dict]] = mapped_column(JSON)  # {node_id: answer}
    survey_progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100 percentage
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    client: Mapped[Client] = relationship("Client", back_populates="leads")
    conversation: Mapped[Optional[Conversation]] = relationship("Conversation")

    __table_args__ = (
        Index("ix_leads_client_stage", "client_id", "stage"),
        Index("ix_leads_client_sid", "client_id", "sid"),
    )


# ---------- Events (analytics stream) ----------
class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(80), index=True)  # e.g., "click_quick_reply"
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    ts_epoch: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="events")
