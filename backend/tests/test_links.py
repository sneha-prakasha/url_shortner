from datetime import datetime, timedelta, timezone

import redis as redis_lib

from app.models import Link, utcnow

CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"


def make(client, auth, **body):
    body.setdefault("url", "https://example.com/some/very/long/page")
    return client.post("/api/links", json=body, headers=auth)


# ---------------------------------------------------------------- create
def test_create_and_redirect_with_302(client, auth):
    r = make(client, auth)
    assert r.status_code == 201
    link = r.json()
    assert link["short_url"] == f"http://short.test/{link['code']}"
    assert len(link["code"]) >= 5

    r = client.get(f"/{link['code']}")
    assert r.status_code == 302  # 302, not 301, so every click is counted
    assert r.headers["location"] == "https://example.com/some/very/long/page"


def test_same_url_returns_same_link(client, auth):
    first = make(client, auth).json()
    second = make(client, auth)
    assert second.status_code == 200
    assert second.json()["id"] == first["id"]
    assert len(client.get("/api/links", headers=auth).json()) == 1


def test_invalid_urls_rejected(client, auth):
    for bad in ["not a url", "javascript:alert(1)", "ftp://x.com", "example.com", ""]:
        assert make(client, auth, url=bad).status_code == 422


def test_cannot_shorten_own_domain(client, auth):
    assert make(client, auth, url="http://short.test/abc").status_code == 422


def test_custom_alias(client, auth):
    r = make(client, auth, alias="sneha-resume")
    assert r.status_code == 201
    assert r.json()["code"] == "sneha-resume"
    assert r.json()["is_custom"] is True
    assert client.get("/sneha-resume").status_code == 302


def test_alias_rules(client, auth):
    make(client, auth, alias="taken")
    assert make(client, auth, url="https://other.com", alias="taken").status_code == 409
    assert make(client, auth, url="https://other.com", alias="api").status_code == 409  # reserved
    assert make(client, auth, url="https://other.com", alias="a").status_code == 422     # too short
    assert make(client, auth, url="https://other.com", alias="bad alias!").status_code == 422


def test_expiry_must_be_in_future(client, auth):
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert make(client, auth, expires_at=past).status_code == 422


# ---------------------------------------------------------------- redirect rules
def test_unknown_code_is_404(client):
    assert client.get("/doesnotexist").status_code == 404


def test_expired_link_is_410(client, auth, db):
    link = make(client, auth).json()
    row = db.get(Link, link["id"])
    row.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    assert client.get(f"/{link['code']}").status_code == 410


def test_expiry_is_checked_on_cached_hits_too(client, auth, redis_fake):
    import json

    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    link = make(client, auth, expires_at=future).json()
    key = f"link:{link['code']}"
    assert client.get(f"/{link['code']}").status_code == 302  # fills the cache
    assert 0 < redis_fake.ttl(key) <= 3600                    # TTL never goes past the expiry

    # Simulate the moment the expiry passes while the entry is still in Redis
    entry = json.loads(redis_fake.get(key))
    entry["expires"] = (utcnow() - timedelta(seconds=5)).isoformat()
    redis_fake.set(key, json.dumps(entry))
    assert client.get(f"/{link['code']}").status_code == 410


def test_pause_and_resume(client, auth):
    link = make(client, auth).json()
    assert client.get(f"/{link['code']}").status_code == 302  # cached now

    r = client.patch(f"/api/links/{link['id']}", json={"is_active": False}, headers=auth)
    assert r.status_code == 200
    assert client.get(f"/{link['code']}").status_code == 410  # cache was invalidated

    client.patch(f"/api/links/{link['id']}", json={"is_active": True}, headers=auth)
    assert client.get(f"/{link['code']}").status_code == 302


def test_delete(client, auth):
    link = make(client, auth).json()
    client.get(f"/{link['code']}")
    assert client.delete(f"/api/links/{link['id']}", headers=auth).status_code == 204
    assert client.get(f"/{link['code']}").status_code == 404
    assert client.get("/api/links", headers=auth).json() == []


# ---------------------------------------------------------------- redis
def test_cache_aside(client, auth, redis_fake):
    link = make(client, auth).json()
    key = f"link:{link['code']}"
    assert redis_fake.get(key) is None

    client.get(f"/{link['code']}")           # miss -> DB -> cache filled
    assert redis_fake.get(key) is not None
    assert 0 < redis_fake.ttl(key) <= 3600

    assert client.get(f"/{link['code']}").status_code == 302  # served from cache


def test_works_when_redis_is_down(client, auth):
    from app import cache

    class BrokenRedis:
        def __getattr__(self, name):
            def fail(*a, **k):
                raise redis_lib.ConnectionError("down")
            return fail

    link = make(client, auth).json()
    cache.set_client(BrokenRedis())
    assert client.get(f"/{link['code']}").status_code == 302  # just slower, not broken


def test_rate_limit_on_create(client, auth):
    # CREATE_LIMIT_PER_MIN is 5 in tests
    codes = [make(client, auth, url=f"https://example.com/{i}").status_code for i in range(6)]
    assert codes[:5] == [201] * 5
    assert codes[5] == 429


# ---------------------------------------------------------------- analytics
def test_clicks_are_logged_and_aggregated(client, auth):
    link = make(client, auth).json()
    code = link["code"]
    client.get(f"/{code}", headers={"user-agent": CHROME, "referer": "https://www.google.com/"})
    client.get(f"/{code}", headers={"user-agent": CHROME})
    client.get(f"/{code}?src=qr", headers={"user-agent": "Mozilla/5.0 (iPhone) Mobile Safari/604"})

    detail = client.get(f"/api/links/{link['id']}", headers=auth).json()
    stats = detail["stats"]
    assert detail["link"]["clicks"] == 3
    assert stats["total"] == 3
    assert stats["by_day"][-1]["clicks"] == 3 and len(stats["by_day"]) == 30
    assert {d["name"]: d["count"] for d in stats["devices"]} == {"desktop": 2, "mobile": 1}
    assert {d["name"]: d["count"] for d in stats["referrers"]} == {"google.com": 1, "Direct": 2}
    assert {d["name"]: d["count"] for d in stats["sources"]} == {"link": 2, "qr": 1}


def test_overview(client, auth):
    a = make(client, auth, url="https://a.com").json()
    b = make(client, auth, url="https://b.com").json()
    for _ in range(3):
        client.get(f"/{a['code']}")
    client.get(f"/{b['code']}")

    data = client.get("/api/overview", headers=auth).json()
    assert data["total_links"] == 2
    assert data["total_clicks"] == 4
    assert data["clicks_7d"] == 4
    assert data["top_links"][0]["id"] == a["id"]


def test_links_list_has_click_counts(client, auth):
    link = make(client, auth).json()
    client.get(f"/{link['code']}")
    client.get(f"/{link['code']}")
    rows = client.get("/api/links", headers=auth).json()
    assert rows[0]["clicks"] == 2


# ---------------------------------------------------------------- ownership
def test_users_cannot_see_each_others_links(client, auth):
    link = make(client, auth).json()
    other = client.post("/api/auth/signup", json={"email": "other@example.com", "password": "password123"})
    h2 = {"Authorization": f"Bearer {other.json()['access_token']}"}

    assert client.get("/api/links", headers=h2).json() == []
    assert client.get(f"/api/links/{link['id']}", headers=h2).status_code == 404
    assert client.patch(f"/api/links/{link['id']}", json={"label": "x"}, headers=h2).status_code == 404
    assert client.delete(f"/api/links/{link['id']}", headers=h2).status_code == 404


def test_update_label_and_expiry(client, auth):
    link = make(client, auth).json()
    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    r = client.patch(f"/api/links/{link['id']}", json={"label": "Resume", "expires_at": future}, headers=auth)
    assert r.json()["label"] == "Resume" and r.json()["expires_at"].endswith("Z")
    r = client.patch(f"/api/links/{link['id']}", json={"expires_at": None}, headers=auth)
    assert r.json()["expires_at"] is None and r.json()["label"] == "Resume"


# ---------------------------------------------------------------- qr
def test_qr_svg(client, auth):
    link = make(client, auth).json()
    r = client.get(f"/api/qr/{link['code']}.svg")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in r.content
    assert client.get("/api/qr/nope.svg").status_code == 404


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
