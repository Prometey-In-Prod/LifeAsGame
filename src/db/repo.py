from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import (
    Category,
    DailyLog,
    Transaction,
    Vitamin,
    WorkoutSession,
    WorkoutSet,
)


def compute_sleep_hours(bedtime: time, wakeup: time) -> float:
    """Длительность сна из времени отхода ко сну и подъёма.

    Если подъём не позже отхода ко сну — считаем, что сон перешёл через полночь.
    """
    base = date(2000, 1, 1)
    start = datetime.combine(base, bedtime)
    end = datetime.combine(base, wakeup)
    if end <= start:
        end += timedelta(days=1)
    return round((end - start).total_seconds() / 3600, 2)


def get_active_vitamins(session: Session) -> list[Vitamin]:
    return list(session.scalars(select(Vitamin).where(Vitamin.active).order_by(Vitamin.id)))


def get_categories(session: Session, kind: str) -> list[Category]:
    return list(
        session.scalars(
            select(Category)
            .where(Category.kind == kind, Category.active)
            .order_by(Category.id)
        )
    )


def get_daily_log(session: Session, log_date: date) -> DailyLog | None:
    return session.scalar(select(DailyLog).where(DailyLog.log_date == log_date))


def upsert_daily_log(session: Session, log_date: date, **fields) -> DailyLog:
    """Создать или частично обновить запись дня (только переданные поля).

    fields может содержать vitamin_ids: list[int]. Сон пересчитывается, если в записи
    (с учётом ранее сохранённых значений) есть и время отхода ко сну, и время подъёма.
    """
    vitamin_ids = fields.pop("vitamin_ids", None)

    log = session.scalar(select(DailyLog).where(DailyLog.log_date == log_date))
    if log is None:
        log = DailyLog(log_date=log_date)
        session.add(log)

    for key, value in fields.items():
        setattr(log, key, value)

    if log.bedtime and log.wakeup:
        log.sleep_hours = compute_sleep_hours(log.bedtime, log.wakeup)

    if vitamin_ids is not None:
        log.vitamins = list(
            session.scalars(select(Vitamin).where(Vitamin.id.in_(vitamin_ids)))
        )

    session.commit()
    return log


def add_transaction(
    session: Session,
    txn_date: date,
    kind: str,
    category_id: int,
    amount: float,
    note: str | None = None,
) -> Transaction:
    txn = Transaction(
        txn_date=txn_date,
        kind=kind,
        category_id=category_id,
        amount=amount,
        note=note,
    )
    session.add(txn)
    session.commit()
    return txn


def start_workout(session: Session) -> WorkoutSession:
    ws = WorkoutSession()
    session.add(ws)
    session.commit()
    return ws


def add_workout_set(
    session: Session,
    session_id: int,
    exercise: str,
    set_number: int,
    reps: int,
    weight_kg: float | None,
) -> WorkoutSet:
    s = WorkoutSet(
        session_id=session_id,
        exercise=exercise,
        set_number=set_number,
        reps=reps,
        weight_kg=weight_kg,
    )
    session.add(s)
    session.commit()
    return s


def get_workout_sets(session: Session, session_id: int) -> list[WorkoutSet]:
    return list(
        session.scalars(
            select(WorkoutSet)
            .where(WorkoutSet.session_id == session_id)
            .order_by(WorkoutSet.id)
        )
    )


def finish_workout(session: Session, session_id: int, note: str | None = None) -> None:
    ws = session.get(WorkoutSession, session_id)
    if ws is not None:
        ws.ended_at = datetime.now()
        if note:
            ws.note = note
        session.commit()


def delete_workout_session(session: Session, session_id: int) -> None:
    ws = session.get(WorkoutSession, session_id)
    if ws is not None:
        session.delete(ws)
        session.commit()
