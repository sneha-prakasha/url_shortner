import os

# Must be set BEFORE the app is imported: in-memory DB, tiny limits, fixed BASE_URL
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"
os.environ["BASE_URL"] = "http://short.test"
os.environ["CREATE_LIMIT_PER_MIN"] = "5"

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import cache  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_state():
    """Every test starts with empty tables and an empty fake Redis."""
    Base.metadata.drop_all(engine)
    init_db()
    fake = fakeredis.FakeRedis(decode_responses=True)
    cache.set_client(fake)
    yield fake


@pytest.fixture
def redis_fake(fresh_state):
    return fresh_state


@pytest.fixture
def client():
    # Not used as a context manager on purpose: tables are created by the fixture above
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def auth(client):
    """Headers for a freshly registered user."""
    r = client.post("/api/auth/signup", json={"email": "sneha@example.com", "password": "password123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
