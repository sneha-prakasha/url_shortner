"""Database connection (SQLAlchemy). Works with MySQL and SQLite."""
import time

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if is_sqlite:
    kwargs = {"connect_args": {"check_same_thread": False}}
    if ":memory:" in settings.DATABASE_URL:
        kwargs["poolclass"] = StaticPool  # one shared in-memory DB (used by tests)
    engine = create_engine(settings.DATABASE_URL, **kwargs)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_conn, _):
        # SQLite ignores foreign keys unless asked, we need ON DELETE CASCADE
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
else:
    # pool_pre_ping drops dead connections instead of crashing after MySQL restarts
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one DB session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(retries: int = 30, delay: float = 2.0):
    """Create tables. Retries because in Docker the API can start before MySQL is ready."""
    from . import models  # noqa: F401  (registers the tables)

    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(engine)
            return
        except Exception as exc:  # noqa: BLE001
            if attempt == retries:
                raise
            print(f"[db] not ready ({exc.__class__.__name__}), retry {attempt}/{retries}...")
            time.sleep(delay)
