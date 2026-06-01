from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import Category, Transaction

KINDS = ("income", "expense", "saving", "debt")


def _month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def monthly_finance_summary(session: Session, year: int, month: int) -> dict:
    """Сводка за месяц: суммы по типам и разбивка по категориям.

    Возвращает: {totals: {kind: sum}, by_category: {kind: [(name, sum), ...]}, net}.
    """
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
