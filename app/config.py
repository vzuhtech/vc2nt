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


def load_config() -> Config:
    return Config(
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        yandex_maps_api_key=os.environ.get("YANDEX_MAPS_API_KEY"),
        database_url=os.environ.get("DATABASE_URL", "sqlite:///data.db"),
    )