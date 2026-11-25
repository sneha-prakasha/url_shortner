"""The hot path: /<code>  ->  302 redirect to the long URL.

302 (temporary) and NOT 301 (permanent): browsers cache a 301 forever and would
skip us on repeat visits, so those clicks would never be counted.
"""
import io
from datetime import datetime
from typing import Optional

import segno
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from .. import cache
from ..config import settings
from ..database import SessionLocal, get_db
from ..models import Click, Link, utcnow
from ..utils import parse_user_agent, referrer_host

router = APIRouter(tags=["redirect"])


def _page(title: str, message: str, status: int) -> HTMLResponse:
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#0a0f14;
color:#e8edf2;font-family:system-ui,sans-serif;text-align:center}}
h1{{font-size:64px;margin:0;color:#ff6b2c}}p{{color:#8b97a5}}</style></head>
<body><div><h1>{title}</h1><p>{message}</p></div></body></html>"""
    return HTMLResponse(html, status_code=status)


def log_click(link_id: int, user_agent: Optional[str], referer: Optional[str], source: str) -> None:
    """Runs AFTER the redirect was sent, so logging never slows the visitor down."""
    device, browser = parse_user_agent(user_agent)
    db = SessionLocal()
    try:
        db.add(Click(
            link_id=link_id, device=device, browser=browser,
            referrer_host=referrer_host(referer),
            source="qr" if source == "qr" else "link",
        ))
        db.commit()
    finally:
        db.close()


@router.get("/api/qr/{code}.svg")
def qr_code(code: str, db: Session = Depends(get_db)):
    """QR image for a short link. The QR carries ?src=qr so scans show up separately."""
    if not db.query(Link.id).filter(Link.code == code).first():
        raise HTTPException(404, "Link not found")
    buffer = io.BytesIO()
    segno.make(f"{settings.BASE_URL}/{code}?src=qr", error="m").save(
        buffer, kind="svg", scale=10, border=2, dark="#0b1118", light="#ffffff"
    )
    return Response(buffer.getvalue(), media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=3600"})


@router.get("/{code}")
def follow(
    code: str,
    request: Request,
    background: BackgroundTasks,
    src: str = "link",
    db: Session = Depends(get_db),
):
    # 1) try Redis
    entry = cache.get_link(code)

    # 2) miss -> database, then fill the cache
    if entry is None:
        link = db.query(Link).filter(Link.code == code).first()
        if link is None:
            return _page("404", "This short link doesn't exist.", 404)
        entry = {
            "id": link.id,
            "url": link.long_url,
            "active": link.is_active,
            "expires": link.expires_at.isoformat() if link.expires_at else None,
        }
        ttl = settings.CACHE_TTL_SECONDS
        if link.expires_at:  # never cache past the expiry moment
            ttl = min(ttl, int((link.expires_at - utcnow()).total_seconds()))
        if ttl > 0:
            cache.set_link(code, entry, ttl)

    # 3) checks run on every request, cached or not
    if not entry["active"]:
        return _page("Paused", "This link has been turned off by its owner.", 410)
    if entry["expires"] and datetime.fromisoformat(entry["expires"]) <= utcnow():
        return _page("Expired", "This link has expired.", 410)

    background.add_task(
        log_click, entry["id"], request.headers.get("user-agent"),
        request.headers.get("referer"), src,
    )
    return RedirectResponse(entry["url"], status_code=302)
