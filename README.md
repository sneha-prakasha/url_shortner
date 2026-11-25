# snip. – URL shortener with analytics

Paste a long link, get a short one, and see who clicked it. Built with **FastAPI, MySQL, Redis, JWT auth, React + Chart.js, Docker**, and deployed on **AWS EC2**.

```
Browser ──► nginx (web container, port 80/8080)
              ├── /app/...      React dashboard (static files)
              ├── /api/...  ──► FastAPI (api container)
              └── /<code>   ──► FastAPI  ──► Redis (cache) ──► MySQL (on a miss)
```

## Features

- Shorten a URL (base62 code from the row id, so codes never collide)
- 302 redirect, every click logged (time, device, browser, referrer, link vs QR)
- Custom alias (`/sneha-resume`), expiry date, pause / resume, delete
- Redis cache-aside for fast redirects, and per-IP rate limiting
- Signup / login with JWT; each user only sees their own links
- Dashboard + per-link page: clicks over time (Chart.js), referrers, devices, browsers
- QR code for every link (downloadable SVG)
- If Redis goes down the app keeps working, just slower

## Run it on your laptop (needs Docker Desktop)

```bash
cp .env.example .env          # then edit the passwords + SECRET_KEY
docker compose up --build -d  # first build takes a few minutes
```

Open **http://localhost:8080**, click "Create an account", and you're in.

Useful commands:

```bash
docker compose ps                 # are all 4 containers healthy?
docker compose logs -f api        # watch the API log
docker compose down               # stop (data is kept)
docker compose down -v            # stop AND delete the database
docker compose exec api python -m app.seed   # add demo data (demo@snip.dev / demo12345)
```

## Run without Docker (for development)

Needs Python 3.13, Node 22, and Redis running locally. MySQL is optional: without it the app uses a SQLite file.

```bash
# terminal 1 – API
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
BASE_URL=http://localhost:8000 uvicorn app.main:app --reload

# terminal 2 – frontend (proxies /api to port 8000)
cd frontend
npm install
npm run dev                                           # open http://localhost:5173/app/
```

Run the tests (no Redis or MySQL needed, they use fakes):

```bash
cd backend && pytest -q       # 32 tests
```

## Project layout

```
backend/app/
  main.py          app + router wiring
  config.py        settings from environment variables
  database.py      SQLAlchemy engine, waits for MySQL on startup
  models.py        users, links, clicks tables
  security.py      bcrypt passwords + JWT tokens
  cache.py         Redis helpers (cache-aside)
  ratelimit.py     per-IP rate limiter (Redis INCR + EXPIRE)
  utils.py         base62, user-agent parsing, URL checks
  routers/auth.py      signup, login, me
  routers/links.py     create / list / detail / update / delete / overview
  routers/redirect.py  the /<code> redirect + QR image
frontend/src/        React app (pages/, components/, api.js)
frontend/nginx.conf  routing rules for the single public port
docker-compose.yml   the 4 containers
docs/                HOW-IT-WORKS.md, DEPLOY-AWS.md
```

## Learn the project

Read **docs/HOW-IT-WORKS.md** (request flows + interview questions), then deploy with **docs/DEPLOY-AWS.md**.
