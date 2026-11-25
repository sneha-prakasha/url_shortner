"""Request/response shapes (Pydantic validates incoming JSON for us)."""
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _iso_utc(value: Optional[datetime]) -> Optional[str]:
    # Stored as naive UTC; add "Z" so the browser knows it is UTC
    return value.isoformat() + "Z" if value else None


# ---------- auth ----------
class Credentials(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address")
        return v

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, v: str) -> str:
        if len(v.encode()) > 72:  # bcrypt limit
            raise ValueError("Password is too long (max 72 bytes)")
        return v


class UserOut(BaseModel):
    id: int
    email: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- links ----------
class LinkCreate(BaseModel):
    url: str
    alias: Optional[str] = None
    label: Optional[str] = Field(default=None, max_length=100)
    expires_at: Optional[datetime] = None

    @field_validator("alias", "label", mode="before")
    @classmethod
    def blank_to_none(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class LinkUpdate(BaseModel):
    label: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None  # send null to remove the expiry


class LinkOut(BaseModel):
    id: int
    code: str
    short_url: str
    long_url: str
    label: Optional[str]
    clicks: int
    is_custom: bool
    is_active: bool
    is_expired: bool
    created_at: datetime
    expires_at: Optional[datetime]

    @field_serializer("created_at", "expires_at")
    def _ser_dt(self, v):
        return _iso_utc(v)


class NamedCount(BaseModel):
    name: str
    count: int


class DayCount(BaseModel):
    date: str
    clicks: int


class Stats(BaseModel):
    total: int
    by_day: list[DayCount]
    devices: list[NamedCount]
    browsers: list[NamedCount]
    referrers: list[NamedCount]
    sources: list[NamedCount]


class LinkDetail(BaseModel):
    link: LinkOut
    stats: Stats


class Overview(BaseModel):
    total_links: int
    total_clicks: int
    clicks_7d: int
    stats: Stats
    top_links: list[LinkOut]
