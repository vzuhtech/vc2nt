import os
from dataclasses import dataclass


@dataclass
class Config:
    telegram_bot_token: str
    # OpenAI
    openai_api_key: str | None
    # Yandex Maps
    yandex_maps_api_key: str | None
    # DB
    database_url: str


def _resolve_database_url() -> str:
    # Prefer a proper URL if provided
    raw = os.environ.get("DATABASE_URL")
    if raw and "://" in raw:
        return raw
    # Try Railway/PG parts
    host = os.environ.get("PGHOST") or os.environ.get("POSTGRES_HOST")
    port = os.environ.get("PGPORT") or os.environ.get("POSTGRES_PORT") or "5432"
    user = os.environ.get("PGUSER") or os.environ.get("POSTGRES_USER")
    password = os.environ.get("PGPASSWORD") or os.environ.get("POSTGRES_PASSWORD")
    dbname = os.environ.get("PGDATABASE") or os.environ.get("POSTGRES_DB")
    if host and user and password and dbname:
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"
    # Fallback to sqlite
    return "sqlite:///data.db"


def load_config() -> Config:
    return Config(
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        yandex_maps_api_key=os.environ.get("YANDEX_MAPS_API_KEY"),
        database_url=_resolve_database_url(),
    )