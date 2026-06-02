from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.database import engine
from src.db.models import Category, Transaction

KINDS = ("income", "expense", "saving", "debt")

# Числовые метрики дня для трендов и корреляций
DAILY_NUMERIC = ["sleep_hours", "work_hours", "mood", "energy", "day_rating", "weight_kg"]
DAILY_LABELS = {
    "sleep_hours": "Сон, ч",
    "work_hours": "Работа, ч",
    "mood": "Настроение",
    "energy": "Энергия",
    "day_rating": "Оценка дня",
    "weight_kg": "Вес, кг",
    "trained_int": "Тренировка",
    "expense": "Расходы, ₽",
}


# --- Загрузчики данных (pandas) ------------------------------------------

def load_daily_df() -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT log_date, sleep_hours, trained, work_hours, mood, energy, "
        "day_rating, weight_kg FROM daily_log ORDER BY log_date",
        engine,
        parse_dates=["log_date"],
    )
    if not df.empty:
        df["trained_int"] = df["trained"].astype(int)
    return df


def load_transactions_df() -> pd.DataFrame:
    return pd.read_sql(
        "SELECT t.txn_date, t.kind, c.name AS category, t.amount "
        "FROM transaction t JOIN category c ON c.id = t.category_id "
        "ORDER BY t.txn_date",
        engine,
        parse_dates=["txn_date"],
    )


def load_workouts_df() -> pd.DataFrame:
    return pd.read_sql(
        "SELECT s.id AS set_id, s.exercise, s.set_number, s.reps, s.weight_kg, "
        "ws.started_at FROM workout_set s "
        "JOIN workout_session ws ON ws.id = s.session_id "
        "ORDER BY ws.started_at, s.id",
        engine,
        parse_dates=["started_at"],
    )


# --- Стрики ---------------------------------------------------------------

def _streak(dates: set[date], today: date) -> int:
    d = today if today in dates else today - timedelta(days=1)
    count = 0
    while d in dates:
        count += 1
        d -= timedelta(days=1)
    return count


def compute_streaks(daily_df: pd.DataFrame, today: date | None = None) -> dict[str, int]:
    today = today or date.today()
    if daily_df.empty:
        return {"checkin": 0, "training": 0}
    all_dates = {d.date() for d in daily_df["log_date"]}
    train_dates = {
        d.date() for d in daily_df.loc[daily_df["trained"] == True, "log_date"]  # noqa: E712
    }
    return {
        "checkin": _streak(all_dates, today),
        "training": _streak(train_dates, today),
    }


def milestone_label(streak: int) -> str | None:
    for m in (100, 30, 7):
        if streak >= m:
            return f"{m}+ дней 🔥"
    return None


# --- Корреляции -----------------------------------------------------------

def correlation_matrix(daily_df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in DAILY_NUMERIC + ["trained_int"] if c in daily_df.columns]
    sub = daily_df[cols].dropna(how="all")
    if len(sub) < 3:
        return pd.DataFrame()
    corr = sub.corr(numeric_only=True)
    corr = corr.rename(index=DAILY_LABELS, columns=DAILY_LABELS)
    return corr


# --- Недельная сводка -----------------------------------------------------

def weekly_summary(daily_df: pd.DataFrame, txn_df: pd.DataFrame, today: date | None = None) -> dict:
    today = today or date.today()
    week_ago = today - timedelta(days=6)

    d = daily_df.copy()
    if not d.empty:
        d = d[(d["log_date"].dt.date >= week_ago) & (d["log_date"].dt.date <= today)]

    t = txn_df.copy()
    if not t.empty:
        t = t[(t["txn_date"].dt.date >= week_ago) & (t["txn_date"].dt.date <= today)]

    def _mean(col):
        return round(d[col].mean(), 1) if not d.empty and d[col].notna().any() else None

    expense = (
        float(t.loc[t["kind"] == "expense", "amount"].sum()) if not t.empty else 0.0
    )
    return {
        "from": week_ago,
        "to": today,
        "days_logged": int(d["log_date"].nunique()) if not d.empty else 0,
        "avg_sleep": _mean("sleep_hours"),
        "workouts": int(d["trained"].sum()) if not d.empty else 0,
        "work_hours": round(float(d["work_hours"].sum()), 1) if not d.empty else 0.0,
        "avg_mood": _mean("mood"),
        "avg_rating": _mean("day_rating"),
        "expense": expense,
    }


# --- Месячная сводка по финансам (используется в /report) ----------------

def _month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def monthly_finance_summary(session: Session, year: int, month: int) -> dict:
    start, end = _month_range(year, month)

    totals = {k: 0.0 for k in KINDS}
    by_category: dict[str, list[tuple[str, float]]] = {k: [] for k in KINDS}

    rows = session.execute(
        select(Category.kind, Category.name, func.sum(Transaction.amount))
        .join(Category, Transaction.category_id == Category.id)
        .where(Transaction.txn_date >= start, Transaction.txn_date < end)
        .group_by(Category.kind, Category.name)
        .order_by(Category.kind, func.sum(Transaction.amount).desc())
    ).all()

    for kind, name, total in rows:
        amount = float(total or 0)
        totals[kind] += amount
        by_category[kind].append((name, amount))

    net = totals["income"] - totals["expense"]
    return {"totals": totals, "by_category": by_category, "net": net}
