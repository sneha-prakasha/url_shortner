"""Small helpers: base62 codes, user-agent parsing, URL checks."""
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Added to the row id so even link #1 gets a 5-character code (62^4 = 14,776,336)
CODE_OFFSET = 62**4

ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")

# These words can never be used as short codes (they are real routes)
RESERVED = {
    "api", "app", "health", "docs", "redoc", "openapi", "login", "signup",
    "static", "assets", "admin", "favicon", "robots", "dashboard", "links",
}


def base62_encode(number: int) -> str:
    """12345 -> '3d7'. Every id maps to a different short, URL-safe string."""
    if number == 0:
        return ALPHABET[0]
    chars = []
    while number > 0:
        number, rem = divmod(number, 62)
        chars.append(ALPHABET[rem])
    return "".join(reversed(chars))


def code_for_id(link_id: int) -> str:
    return base62_encode(link_id + CODE_OFFSET)


def to_naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Accept aware or naive datetimes, return naive UTC (what the DB stores)."""
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def is_valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc) and len(url) <= 2048


def parse_user_agent(ua: Optional[str]) -> tuple[str, str]:
    """Very small User-Agent parser -> (device, browser). Good enough for analytics."""
    s = (ua or "").lower()

    if any(w in s for w in ("bot", "crawler", "spider", "preview", "curl", "wget", "python-requests")):
        device = "bot"
    elif "ipad" in s or "tablet" in s or ("android" in s and "mobile" not in s):
        device = "tablet"
    elif "mobi" in s or "iphone" in s or "android" in s:
        device = "mobile"
    else:
        device = "desktop"

    # Order matters: Edge and Opera also say "Chrome", Chrome also says "Safari"
    if "edg/" in s or "edge/" in s:
        browser = "Edge"
    elif "opr/" in s or "opera" in s:
        browser = "Opera"
    elif "firefox" in s or "fxios" in s:
        browser = "Firefox"
    elif "chrome" in s or "crios" in s:
        browser = "Chrome"
    elif "safari" in s:
        browser = "Safari"
    else:
        browser = "Other"
    return device, browser


def referrer_host(referer: Optional[str]) -> Optional[str]:
    if not referer:
        return None
    host = urlparse(referer).hostname
    if not host:
        return None
    return host.removeprefix("www.")[:255]
