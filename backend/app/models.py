"""Database tables: users, links, clicks."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Naive UTC time. We store every datetime as UTC and convert in the browser."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    links: Mapped[list["Link"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    long_url: Mapped[str] = mapped_column(Text)
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    owner: Mapped[User] = relationship(back_populates="links")
    clicks: Mapped[list["Click"]] = relationship(
        back_populates="link", cascade="all, delete-orphan", passive_deletes=True
    )


class Click(Base):
    """One row per visit to a short link (this powers the analytics)."""

    __tablename__ = "clicks"
    __table_args__ = (Index("ix_clicks_link_time", "link_id", "clicked_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    link_id: Mapped[int] = mapped_column(ForeignKey("links.id", ondelete="CASCADE"))
    clicked_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    device: Mapped[str] = mapped_column(String(20), default="desktop")
    browser: Mapped[str] = mapped_column(String(30), default="Other")
    referrer_host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="link")  # "link" or "qr"

    link: Mapped[Link] = relationship(back_populates="clicks")
