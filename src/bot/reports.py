from __future__ import annotations

from datetime import date

from src.analysis.metrics import monthly_finance_summary
from src.db.database import SessionLocal

MONTHS_RU = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]


def _fmt(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ")


def build_monthly_finance_report(year: int, month: int) -> str:
    with SessionLocal() as session:
        data = monthly_finance_summary(session, year, month)

    totals = data["totals"]
    by_cat = data["by_category"]

    lines = [f"📊 Финансы — {MONTHS_RU[month - 1]} {year}", ""]
    lines.append(f"💰 Доходы: {_fmt(totals['income'])} ₽")
    lines.append(f"💸 Расходы: {_fmt(totals['expense'])} ₽")
    lines.append(f"🐷 Сбережения: {_fmt(totals['saving'])} ₽")
    if totals["debt"]:
        lines.append(f"💳 Выплаты по долгам: {_fmt(totals['debt'])} ₽")

    net = data["net"]
    sign = "📈" if net >= 0 else "📉"
    lines.append("")
    lines.append(f"{sign} Баланс (доход − расход): {_fmt(net)} ₽")

    expense_cats = by_cat["expense"]
    if expense_cats:
        lines.append("")
        lines.append("Топ расходов:")
        for name, amount in expense_cats[:5]:
            lines.append(f"  • {name}: {_fmt(amount)} ₽")

    if not any(totals.values()):
        return f"📊 За {MONTHS_RU[month - 1]} {year} ещё нет записей."

    return "\n".join(lines)


def build_current_month_report() -> str:
    today = date.today()
    return build_monthly_finance_report(today.year, today.month)
