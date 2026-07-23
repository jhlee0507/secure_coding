import os
from datetime import timedelta
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    INSTANCE_DIR = BASE_DIR / "instance"

    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "development-only-change-this-secret-before-production"
    )
    APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'market.sqlite3'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 1 * 1024 * 1024
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _as_bool(os.environ.get("COOKIE_SECURE"), False)

    WTF_CSRF_TIME_LIMIT = timedelta(hours=1)
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    INITIAL_DEMO_BALANCE = int(os.environ.get("INITIAL_DEMO_BALANCE", "100000"))
