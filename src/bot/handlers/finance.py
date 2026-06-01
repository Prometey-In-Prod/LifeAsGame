from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.filters import OwnerFilter
from src.bot.keyboards import (
    BTN_FINANCE,
    KIND_LABELS,
    finance_categories_kb,
    finance_kind_kb,
    main_menu,
    skip_kb,
)
from src.bot.reports import build_current_month_report
from src.bot.states import FinanceEntry
from src.db.database import SessionLocal
from src.db.repo import add_transaction, get_categories

router = Router()
router.message.filter(OwnerFilter())
router.callback_query.filter(OwnerFilter())


def parse_amount(text: str) -> float | None:
    try:
        value = float(text.strip().replace(",", ".").replace(" ", ""))
    except ValueError:
        return None
    return value if value > 0 else None


@router.message(F.text == BTN_FINANCE)
@router.message(Command("money"))
async def start_finance(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(FinanceEntry.kind)
    await message.answer("💰 Что записываем?", reply_markup=finance_kind_kb())


@router.message(Command("report"))
async def cmd_report(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(build_current_month_report())


@router.callback_query(FinanceEntry.kind, F.data.startswith("fin_kind:"))
async def set_kind(callback: CallbackQuery, state: FSMContext) -> None:
    kind = callback.data.split(":")[1]
    await state.update_data(kind=kind)
    with SessionLocal() as session:
        categories = get_categories(session, kind)
    if not categories:
        await callback.message.edit_text("Нет категорий для этого типа.")
        await state.clear()
        await callback.answer()
        return
    await state.set_state(FinanceEntry.category)
    await callback.message.edit_text(
        f"{KIND_LABELS[kind]} — выбери категорию:",
        reply_markup=finance_categories_kb(categories),
    )
    await callback.answer()


@router.callback_query(FinanceEntry.category, F.data.startswith("fin_cat:"))
async def set_category(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id)
    await state.set_state(FinanceEntry.amount)
    await callback.message.edit_text("Сумма (₽)?")
    await callback.answer()


@router.message(FinanceEntry.amount)
async def set_amount(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text or "")
    if amount is None:
        await message.answer("Введи сумму числом больше нуля, например 1500.")
        return
    await state.update_data(amount=amount)
    await state.set_state(FinanceEntry.note)
    await message.answer("Комментарий? Можно пропустить.", reply_markup=skip_kb())


@router.message(FinanceEntry.note)
async def set_note(message: Message, state: FSMContext) -> None:
    await _save(message, state, note=(message.text or "").strip() or None)


@router.callback_query(FinanceEntry.note, F.data == "skip")
async def skip_note(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Без комментария.")
    await _save(callback.message, state, note=None)
    await callback.answer()


async def _save(message: Message, state: FSMContext, note: str | None) -> None:
    data = await state.get_data()
    await state.clear()
    with SessionLocal() as session:
        add_transaction(
            session,
            txn_date=date.today(),
            kind=data["kind"],
            category_id=data["category_id"],
            amount=data["amount"],
            note=note,
        )
        category = next(
            c for c in get_categories(session, data["kind"]) if c.id == data["category_id"]
        )
    summary = (
        f"✅ Записано!\n"
        f"{KIND_LABELS[data['kind']]} · {category.name}\n"
        f"Сумма: {data['amount']:.2f} ₽"
    )
    if note:
        summary += f"\nКомментарий: {note}"
    await message.answer(summary, reply_markup=main_menu())
