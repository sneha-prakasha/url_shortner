"""Create, list, inspect, edit and delete links (all require login)."""
import secrets
from datetime import datetime, timedelta, time as dtime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import cache
from ..config import settings
from ..database import get_db
from ..models import Click, Link, User, utcnow
from ..ratelimit import rate_limit
from ..schemas import (
    DayCount, LinkCreate, LinkDetail, LinkOut, LinkUpdate, NamedCount, Overview, Stats,
)
from ..security import get_current_user
from ..utils import (
    ALIAS_RE, ALPHABET, RESERVED, code_for_id, is_valid_http_url, to_naive_utc,
)

router = APIRouter(prefix="/api", tags=["links"])


# ---------------------------------------------------------------- helpers
def to_out(link: Link, clicks: int) -> LinkOut:
    return LinkOut(
        id=link.id,
        code=link.code,
        short_url=f"{settings.BASE_URL}/{link.code}",
        long_url=link.long_url,
        label=link.label,
        clicks=clicks,
        is_custom=link.is_custom,
        is_active=link.is_active,
        is_expired=link.expires_at is not None and link.expires_at <= utcnow(),
        created_at=link.created_at,
        expires_at=link.expires_at,
    )


def get_owned_link(db: Session, user: User, link_id: int) -> Link:
    link = db.get(Link, link_id)
    # 404 (not 403) so people can't discover which ids exist
    if link is None or link.user_id != user.id:
        raise HTTPException(404, "Link not found")
    return link


def click_count(db: Session, link_id: int) -> int:
    return db.query(func.count(Click.id)).filter(Click.link_id == link_id).scalar() or 0


def _breakdown(db: Session, column, link_ids: list[int], default: str) -> list[NamedCount]:
    rows = (
        db.query(column, func.count(Click.id))
        .filter(Click.link_id.in_(link_ids))
        .group_by(column)
        .all()
    )
    merged: dict[str, int] = {}
    for name, count in rows:  # NULL referrers become "Direct"
        key = name or default
        merged[key] = merged.get(key, 0) + count
    items = [NamedCount(name=k, count=v) for k, v in merged.items()]
    return sorted(items, key=lambda i: i.count, reverse=True)[:10]


def build_stats(db: Session, link_ids: list[int], days: int = 30) -> Stats:
    """Analytics for one link, or for all of a user's links at once."""
    today = utcnow().date()
    first_day = today - timedelta(days=days - 1)
    empty_days = [DayCount(date=str(first_day + timedelta(days=i)), clicks=0) for i in range(days)]

    if not link_ids:
        return Stats(total=0, by_day=empty_days, devices=[], browsers=[], referrers=[], sources=[])

    total = db.query(func.count(Click.id)).filter(Click.link_id.in_(link_ids)).scalar() or 0

    day_col = func.date(Click.clicked_at)
    rows = (
        db.query(day_col, func.count(Click.id))
        .filter(Click.link_id.in_(link_ids), Click.clicked_at >= datetime.combine(first_day, dtime.min))
        .group_by(day_col)
        .all()
    )
    per_day = {str(day)[:10]: count for day, count in rows}
    by_day = [DayCount(date=d.date, clicks=per_day.get(d.date, 0)) for d in empty_days]

    return Stats(
        total=total,
        by_day=by_day,
        devices=_breakdown(db, Click.device, link_ids, "unknown"),
        browsers=_breakdown(db, Click.browser, link_ids, "Other"),
        referrers=_breakdown(db, Click.referrer_host, link_ids, "Direct"),
        sources=_breakdown(db, Click.source, link_ids, "link"),
    )


def _clear_cache(link: Link) -> None:
    cache.delete_link(link.code)


# ---------------------------------------------------------------- routes
@router.post(
    "/links",
    response_model=LinkOut,
    status_code=201,
    dependencies=[Depends(rate_limit("create", settings.CREATE_LIMIT_PER_MIN))],
)
def create_link(
    payload: LinkCreate,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    url = payload.url.strip()
    if not is_valid_http_url(url):
        raise HTTPException(422, "Enter a full URL starting with http:// or https://")
    # A link pointing at ourselves could create a redirect loop
    if urlparse(url).netloc == urlparse(settings.BASE_URL).netloc:
        raise HTTPException(422, "You can't shorten a link that already points to this site")

    expires_at = to_naive_utc(payload.expires_at)
    if expires_at is not None and expires_at <= utcnow():
        raise HTTPException(422, "Expiry must be in the future")

    # --- custom alias ---
    if payload.alias:
        alias = payload.alias
        if not ALIAS_RE.match(alias):
            raise HTTPException(422, "Alias must be 3-32 characters: letters, numbers, - or _")
        if alias.lower() in RESERVED:
            raise HTTPException(409, "That alias is reserved, please pick another")
        if db.query(Link.id).filter(Link.code == alias).first():
            raise HTTPException(409, "That alias is already taken")
        link = Link(
            user_id=user.id, code=alias, long_url=url, label=payload.label,
            is_custom=True, expires_at=expires_at,
        )
        db.add(link)
        try:
            db.commit()
        except IntegrityError:  # someone grabbed it between our check and the insert
            db.rollback()
            raise HTTPException(409, "That alias is already taken")
        return to_out(link, 0)

    # --- duplicate handling: same user + same URL -> return the existing link ---
    if expires_at is None and not payload.label:
        existing = (
            db.query(Link)
            .filter(Link.user_id == user.id, Link.long_url == url, Link.is_custom.is_(False))
            .first()
        )
        if existing:
            response.status_code = 200
            return to_out(existing, click_count(db, existing.id))

    # --- auto code: base62 of the row id ---
    # We need the id first, so insert with a throw-away code, then replace it.
    link = Link(
        user_id=user.id, code=f"tmp_{secrets.token_hex(8)}", long_url=url,
        label=payload.label, expires_at=expires_at,
    )
    db.add(link)
    db.flush()  # gives link.id without committing yet
    code = code_for_id(link.id)
    # Extremely rare: a custom alias already uses this exact string
    while db.query(Link.id).filter(Link.code == code).first():
        code += secrets.choice(ALPHABET)
    link.code = code
    db.commit()
    return to_out(link, 0)


@router.get("/links", response_model=list[LinkOut])
def list_links(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    counts = (
        db.query(Click.link_id.label("link_id"), func.count(Click.id).label("n"))
        .join(Link, Link.id == Click.link_id)
        .filter(Link.user_id == user.id)
        .group_by(Click.link_id)
        .subquery()
    )
    rows = (
        db.query(Link, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.link_id == Link.id)
        .filter(Link.user_id == user.id)
        .order_by(Link.created_at.desc(), Link.id.desc())
        .all()
    )
    return [to_out(link, n) for link, n in rows]


@router.get("/links/{link_id}", response_model=LinkDetail)
def link_detail(link_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    link = get_owned_link(db, user, link_id)
    stats = build_stats(db, [link.id])
    return LinkDetail(link=to_out(link, stats.total), stats=stats)


@router.patch("/links/{link_id}", response_model=LinkOut)
def update_link(
    link_id: int,
    payload: LinkUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    link = get_owned_link(db, user, link_id)
    sent = payload.model_fields_set  # only touch fields the client actually sent

    if "label" in sent:
        link.label = (payload.label or "").strip() or None
    if "is_active" in sent and payload.is_active is not None:
        link.is_active = payload.is_active
    if "expires_at" in sent:
        expires_at = to_naive_utc(payload.expires_at)
        if expires_at is not None and expires_at <= utcnow():
            raise HTTPException(422, "Expiry must be in the future")
        link.expires_at = expires_at

    db.commit()
    _clear_cache(link)  # otherwise Redis keeps serving the old settings
    return to_out(link, click_count(db, link.id))


@router.delete("/links/{link_id}", status_code=204)
def delete_link(link_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    link = get_owned_link(db, user, link_id)
    db.delete(link)
    db.commit()
    _clear_cache(link)
    return Response(status_code=204)


@router.get("/overview", response_model=Overview)
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    links = db.query(Link).filter(Link.user_id == user.id).all()
    ids = [link.id for link in links]
    stats = build_stats(db, ids)
    clicks_7d = sum(d.clicks for d in stats.by_day[-7:])

    per_link = {}
    if ids:
        per_link = dict(
            db.query(Click.link_id, func.count(Click.id))
            .filter(Click.link_id.in_(ids))
            .group_by(Click.link_id)
            .all()
        )
    top = sorted(links, key=lambda l: per_link.get(l.id, 0), reverse=True)[:5]
    return Overview(
        total_links=len(links),
        total_clicks=stats.total,
        clicks_7d=clicks_7d,
        stats=stats,
        top_links=[to_out(l, per_link.get(l.id, 0)) for l in top],
    )
