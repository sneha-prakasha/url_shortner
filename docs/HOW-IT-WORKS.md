# How snip. works (read this before any interview)

## 1. The big picture

Four containers, one public port:

| Container | What it is | Why |
|---|---|---|
| `web` | nginx + the built React files | Serves the UI and forwards `/api/*` and short codes to the API |
| `api` | FastAPI (Python) | All the logic: auth, links, redirects, analytics |
| `db` | MySQL | The permanent data: users, links, clicks |
| `redis` | Redis | A fast cache + counters for rate limiting |

Inside Docker, containers reach each other by **service name**. That is why the API connects to host `db` and not `localhost`: `localhost` inside the API container means the API container itself.

## 2. Creating a short link

```
React form  ->  POST /api/links  (JWT in the Authorization header)
  1. rate limit check (Redis)             too many requests -> 429
  2. get_current_user (decode JWT)        bad token -> 401
  3. validate URL (http/https only)       bad URL -> 422
  4. custom alias?   check format, reserved words, already taken -> 409
  5. same user + same URL already exists?  return the existing link
  6. otherwise INSERT the row, get its id, code = base62(id + 62^4)
  7. return { code, short_url, ... }
```

**Why base62 of the row id?** The id is unique (the database guarantees it), so the code is unique with no guessing and no collision checks. Base62 uses `0-9 a-z A-Z`, which is URL-safe and short. We add `62^4` so even link #1 gets a 5-character code.

## 3. Opening a short link (the important flow)

```
GET /aB3x9
  1. Redis GET link:aB3x9
        hit  -> we have the long URL, no database needed
        miss -> SELECT from MySQL, then SET in Redis (expires in 1 hour)
  2. Is it paused? -> 410.  Expired? -> 410.   (checked on EVERY request, even cached ones)
  3. Send  302 Found  + Location: <long url>
  4. AFTER the response is sent, a background task writes the click row to MySQL
```

This pattern is called **cache-aside**.

**Why is it faster?** Redis keeps data in memory, so a lookup takes well under a millisecond, while a MySQL query reads from disk and goes through more work. Redirects are read-heavy (one link, millions of visits), so caching them is the biggest win.

**Why log the click in a background task?** The visitor should not wait for a database write. They get their redirect first, and the click is saved a moment later.

**Cache invalidation:** when you pause, edit or delete a link, the code calls `cache.delete_link(code)`. Without it Redis would keep serving the old URL for up to an hour.

## 4. 301 vs 302

- **301 (permanent):** browsers remember it and go straight to the target next time. They never contact us again, so repeat clicks are **not counted**.
- **302 (temporary):** the browser asks us every time, so every click is counted. We use 302 because analytics is the point.

## 5. Rate limiting (fixed window)

For each IP and each type of request we keep a counter in Redis: `rl:create:<ip>`.

```
count = INCR key
if count == 1: EXPIRE key 60     # window starts on the first request
if count > limit: return 429
```

Defaults: 20 link creations per minute, 10 login/signup attempts per minute (stops password guessing). Limitation to mention: a fixed window allows a burst at the window edge. A sliding window or token bucket fixes that.

## 6. Authentication

- Passwords are hashed with **bcrypt** (slow on purpose, salted). We never store the real password.
- Login returns a **JWT**: a signed token containing the user id and an expiry. The browser sends it in `Authorization: Bearer <token>`.
- The server does not store sessions. It just checks the signature using `SECRET_KEY`. (That is why `SECRET_KEY` must be secret and long.)
- Wrong email and wrong password return the same message, so attackers cannot find out which emails exist.
- Every query for links filters by `user_id`, and other people's links return 404, so users can't see each other's data.

## 7. Database tables

```
users   id, email (unique), password_hash, created_at
links   id, user_id -> users, code (unique), long_url, label, is_custom,
        is_active, created_at, expires_at
clicks  id, link_id -> links, clicked_at, device, browser, referrer_host, source
        index on (link_id, clicked_at)
```

`ON DELETE CASCADE` means deleting a link deletes its clicks. The index on `(link_id, clicked_at)` makes the per-link analytics queries fast.

## 8. Analytics

Every redirect inserts a row into `clicks`. The dashboard runs `GROUP BY` queries:
clicks per day (`GROUP BY DATE(clicked_at)`), per device, browser and referrer. Days with zero clicks are filled in by the API so the chart has no gaps. A QR code points to `/<code>?src=qr`, so scans are counted separately from normal clicks.

## 9. Interview questions you should be able to answer

1. **Why FastAPI?** Fast, async-capable, automatic request validation with Pydantic, and free API docs at `/api/docs`.
2. **How do you make sure short codes are unique?** Base62 of the database id; the id is unique, plus a UNIQUE index on `code`.
3. **Walk me through a redirect.** Section 3 above.
4. **Why Redis? What if it goes down?** Speed for read-heavy redirects. Our cache functions catch Redis errors, so the app falls back to MySQL.
5. **What is cache invalidation, and where do you do it?** When a link changes, we delete its cache key.
6. **301 or 302, and why?** Section 4.
7. **How do you prevent abuse?** Rate limiting, URL validation (http/https only, so no `javascript:` links), blocking links to our own domain (redirect loops), reserved aliases.
8. **Why is the DB host `db`, not `localhost`?** Docker's internal network resolves service names.
9. **Why a volume for MySQL?** Containers are disposable. A volume keeps the data when the container is recreated.
10. **Why does the API wait for MySQL?** MySQL takes a while to start. The compose `healthcheck` + `depends_on: service_healthy` and the retry loop in `init_db()` stop the API from crashing at boot.
11. **How would you scale this to millions of links?** More API containers behind a load balancer (the API is stateless thanks to JWT), a managed MySQL (RDS) with read replicas, ElastiCache for Redis, write clicks to a queue and insert in batches, and a CDN in front.
12. **What would you improve?** Sliding-window rate limits, database migrations (Alembic), a unsafe-URL blocklist, a custom domain with HTTPS, and click aggregation tables for very large datasets.

## 10. Things to try yourself (best way to learn it)

- Change the rate limit to 3 per minute in `.env`/`config.py` and watch the 429.
- Add a new field, e.g. a `password` on a link, in `models.py` + `schemas.py` + the route.
- Turn Redis off (`docker compose stop redis`) and see that redirects still work.
- Open `docker compose exec redis redis-cli` and run `KEYS *`, `TTL link:<code>`.
- Open `docker compose exec db mysql -u snip -p snip` and run `SELECT * FROM clicks LIMIT 5;`.
