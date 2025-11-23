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

# ---------- Users (Authentication) ----------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    
    # Role: 'org_admin' (manage org users + surveys) or 'org_user' (view only)
    role: Mapped[str] = mapped_column(String(20), default="org_user")
    
    # Profile picture URL
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Required: link to organization (no system admins in DB)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")

    __table_args__ = (
        CheckConstraint("role IN ('org_admin', 'org_user')", name="chk_users_role"),
        Index("ix_users_role_active", "role", "is_active"),
    )

# ---------- Organizations (formerly Clients) ----------
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # e.g., "novak-realty"
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    # human name
    name: Mapped[str] = mapped_column(String(160), index=True)
    # optional subdomain, e.g., "ace.novak.si"
    subdomain: Mapped[Optional[str]] = mapped_column(String(160))
    # on/off
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    users: Mapped[list[User]] = relationship(
        "User", back_populates="organization", cascade="all, delete-orphan"
    )
    surveys: Mapped[list["Survey"]] = relationship(
        "Survey", back_populates="organization", cascade="all, delete-orphan"
    )
    survey_responses: Mapped[list["SurveyResponse"]] = relationship(
        "SurveyResponse", back_populates="organization", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="organization", cascade="all, delete-orphan"
    )
    leads: Mapped[list["Lead"]] = relationship(
        "Lead", back_populates="organization", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_organizations_active_slug", "active", "slug"),
    )


# Backward compatibility alias
Client = Organization


# ---------- Surveys ----------
class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    # Human-readable name
    name: Mapped[str] = mapped_column(String(160), index=True)
    # URL slug (unique per org)
    slug: Mapped[str] = mapped_column(String(80), index=True)
    # Survey type: 'regular' or 'ab_test'
    survey_type: Mapped[str] = mapped_column(String(20), default="regular")
    # Status: 'draft', 'live', 'archived'
    status: Mapped[str] = mapped_column(String(20), default="draft")
    
    # Survey flow JSON (for regular surveys)
    flow_json: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # A/B test variants (only used when survey_type='ab_test')
    variant_a_flow: Mapped[Optional[dict]] = mapped_column(JSON)
    variant_b_flow: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    organization: Mapped[Organization] = relationship("Organization", back_populates="surveys")
    responses: Mapped[list["SurveyResponse"]] = relationship(
        "SurveyResponse", back_populates="survey", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        CheckConstraint("survey_type IN ('regular', 'ab_test')", name="chk_surveys_type"),
        CheckConstraint("status IN ('draft', 'live', 'archived')", name="chk_surveys_status"),
        UniqueConstraint("organization_id", "slug", name="uq_surveys_org_slug"),
        Index("ix_surveys_org_status", "organization_id", "status"),
    )


# ---------- Survey Responses (formerly Lead data) ----------
class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    survey_id: Mapped[int] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    
    # Session tracking
    sid: Mapped[str] = mapped_column(String(64), index=True)
    
    # A/B test variant (null for regular surveys, 'a' or 'b' for A/B tests)
    variant: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    
    # Contact information
    name: Mapped[str] = mapped_column(String(160), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(60), default="")
    
    # Survey answers and scoring
    survey_answers: Mapped[Optional[dict]] = mapped_column(JSON)  # {node_id: answer}
    score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    interest: Mapped[str] = mapped_column(String(16), default="Low")  # Low/Medium/High
    
    # Survey lifecycle
    survey_started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    survey_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    survey_progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100 percentage
    
    # Additional metadata
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    survey: Mapped[Survey] = relationship("Survey", back_populates="responses")
    organization: Mapped[Organization] = relationship("Organization", back_populates="survey_responses")
    
    __table_args__ = (
        CheckConstraint("variant IS NULL OR variant IN ('a', 'b')", name="chk_responses_variant"),
        CheckConstraint("interest IN ('Low', 'Medium', 'High')", name="chk_responses_interest"),
        Index("ix_responses_survey_completed", "survey_id", "survey_completed_at"),
        Index("ix_responses_org_score", "organization_id", "score"),
    )


# ---------- Conversations (one per visitor/session) ----------
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    # Your existing SID from the frontend
    sid: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # optional denormalized tracking
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    organization: Mapped[Organization] = relationship("Organization", back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    events: Mapped[list[Event]] = relationship(
        "Event", back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "sid", name="uq_conversations_org_sid"),
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


# ---------- Leads (DEPRECATED - keeping for backward compatibility) ----------
class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )

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

    organization: Mapped[Organization] = relationship("Organization", back_populates="leads")
    conversation: Mapped[Optional[Conversation]] = relationship("Conversation")
    
    # Backward compatibility alias
    @property
    def client_id(self):
        return self.organization_id

    __table_args__ = (
        Index("ix_leads_org_stage", "organization_id", "stage"),
        Index("ix_leads_org_sid", "organization_id", "sid"),
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
