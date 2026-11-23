from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(50))
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    city: Mapped[str] = mapped_column(String(100), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    looking_for: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Conversation(Base):
    """One conversation per pair. user_low_id < user_high_id always."""

    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("user_low_id", "user_high_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_low_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    user_high_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    low_wants_reveal: Mapped[bool] = mapped_column(Boolean, default=False)
    high_wants_reveal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")
