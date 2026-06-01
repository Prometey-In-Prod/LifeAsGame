from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


daily_vitamin = Table(
    "daily_vitamin",
    Base.metadata,
    Column(
        "daily_log_id", ForeignKey("daily_log.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("vitamin_id", ForeignKey("vitamin.id", ondelete="CASCADE"), primary_key=True),
)


class DailyLog(Base):
    __tablename__ = "daily_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    log_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    bedtime: Mapped[time | None] = mapped_column(Time)
    wakeup: Mapped[time | None] = mapped_column(Time)
    sleep_hours: Mapped[float | None] = mapped_column(Float)
    sleep_quality: Mapped[int | None] = mapped_column(Integer)
    trained: Mapped[bool] = mapped_column(Boolean, default=False)
    training_note: Mapped[str | None] = mapped_column(String(255))
    work_hours: Mapped[float | None] = mapped_column(Float)
    mood: Mapped[int | None] = mapped_column(Integer)
    energy: Mapped[int | None] = mapped_column(Integer)
    day_rating: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    vitamins: Mapped[list[Vitamin]] = relationship(
        secondary=daily_vitamin, back_populates="days"
    )


class Vitamin(Base):
    __tablename__ = "vitamin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    days: Mapped[list[DailyLog]] = relationship(
        secondary=daily_vitamin, back_populates="vitamins"
    )


class Category(Base):
    __tablename__ = "category"
    __table_args__ = (UniqueConstraint("name", "kind", name="uq_category_name_kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))  # income | expense | saving | debt
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Transaction(Base):
    __tablename__ = "transaction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    txn_date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(20))  # income | expense | saving | debt
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped[Category] = relationship()


class WorkoutSession(Base):
    __tablename__ = "workout_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    note: Mapped[str | None] = mapped_column(String(255))

    sets: Mapped[list[WorkoutSet]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class WorkoutSet(Base):
    __tablename__ = "workout_set"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("workout_session.id", ondelete="CASCADE")
    )
    exercise: Mapped[str] = mapped_column(String(100), index=True)
    set_number: Mapped[int] = mapped_column(Integer)
    reps: Mapped[int] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Float)

    session: Mapped[WorkoutSession] = relationship(back_populates="sets")
