from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy import String, Float, Integer, DateTime, Text

from .config import load_config


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    user_id: Mapped[int] = mapped_column(Integer, index=True)

    car_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    address_from: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address_to: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    cargo_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    load_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unload_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    remainder: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


_config = load_config()
_engine = create_engine(_config.database_url, future=True)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(_engine)