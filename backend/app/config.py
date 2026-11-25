"""All settings come from environment variables, so the same code runs
on your laptop, inside Docker, and on AWS without changes."""
import os

from sqlalchemy.engine import URL


def _database_url() -> str:
    """Docker passes MYSQL_* pieces; building the URL here safely escapes odd
    characters in the password. DATABASE_URL (if set) wins, SQLite is the fallback."""
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if os.getenv("MYSQL_HOST"):
        return URL.create(
            "mysql+pymysql",
            username=os.getenv("MYSQL_USER", "snip"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            host=os.environ["MYSQL_HOST"],
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.getenv("MYSQL_DATABASE", "snip"),
            query={"charset": "utf8mb4"},
        ).render_as_string(hide_password=False)
    return "sqlite:///./snip.db"


class Settings:
    # MySQL in Docker/AWS, SQLite file for quick local runs and tests
    DATABASE_URL: str = _database_url()
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Used to sign login tokens. CHANGE THIS in production.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    ACCESS_TOKEN_MINUTES: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "1440"))

    # Public address of the app. Short links are built as BASE_URL/<code>
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")

    # Redis cache: how long a code -> url mapping stays cached
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

    # Rate limits (requests per minute, per IP)
    CREATE_LIMIT_PER_MIN: int = int(os.getenv("CREATE_LIMIT_PER_MIN", "20"))
    AUTH_LIMIT_PER_MIN: int = int(os.getenv("AUTH_LIMIT_PER_MIN", "10"))


settings = Settings()
