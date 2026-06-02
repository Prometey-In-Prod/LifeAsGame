from __future__ import annotations

import re
from datetime import date, time

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.filters import OwnerFilter
from src.bot.keyboards import (
    BTN_DAY,
    day_nav_kb,
    main_menu,
    scale_1_10,
    vitamins_kb,
    yes_no,
)
from src.bot.states import DailyCheckin
from src.db.database import SessionLocal
from src.db.repo import get_active_vitamins, get_daily_log, upsert_daily_log

router = Router()
router.message.filter(OwnerFilter())
router.callback_query.filter(OwnerFilter())

# Порядок шагов чек-ина
ORDER = [
    DailyCheckin.bedtime,
    DailyCheckin.wakeup,
    DailyCheckin.trained,
    DailyCheckin.work_hours,
    DailyCheckin.vitamins,
    DailyCheckin.mood,
    DailyCheckin.energy,
    DailyCheckin.day_rating,
    DailyCheckin.weight,
    DailyCheckin.note,
]
ORDER_NAMES = [s.state for s in ORDER]

SCALE_FIELD = {
    DailyCheckin.mood.state: "mood",
    DailyCheckin.energy.state: "energy",
    DailyCheckin.day_rating.state: "day_rating",
}


def parse_time(text: str) -> time | None:
    text = text.strip().replace(".", ":").replace("-", ":")
    m = re.fullmatch(r"(\d{1,2})(?::(\d{1,2}))?", text)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2) or 0)
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return time(hh, mm)


def parse_float(text: str) -> float | None:
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        return None
    return value if value >= 0 else None


def _save_field(**fields) -> None:
    with SessionLocal() as session:
        upsert_daily_log(session, date.today(), **fields)


async def send_step(message: Message, state: FSMContext, step) -> None:
    """Задать вопрос для шага step (step — State из DailyCheckin)."""
    await state.set_state(step)

    if step == DailyCheckin.bedtime:
        await message.answer(
            "🛌 Во сколько лёг спать? (например, 23:30)", reply_markup=day_nav_kb()
        )
    elif step == DailyCheckin.wakeup:
        await message.answer(
            "☀️ Во сколько проснулся? (например, 7:15)", reply_markup=day_nav_kb()
        )
    elif step == DailyCheckin.trained:
        await message.answer("🏋️ Была тренировка сегодня?", reply_markup=yes_no())
    elif step == DailyCheckin.work_hours:
        await message.answer(
            "💼 Сколько часов интенсивно работал? (например, 4.5)",
            reply_markup=day_nav_kb(),
        )
    elif step == DailyCheckin.vitamins:
        with SessionLocal() as session:
            vitamins = get_active_vitamins(session)
            log = get_daily_log(session, date.today())
            selected = {v.id for v in log.vitamins} if log else set()
        await state.update_data(vitamin_ids=list(selected))
        await message.answer(
            "💊 Какие витамины принял? Отмечай и жми «Готово».",
            reply_markup=vitamins_kb(vitamins, selected),
        )
    elif step == DailyCheckin.mood:
        await message.answer("🙂 Настроение (1–10)?", reply_markup=scale_1_10())
    elif step == DailyCheckin.energy:
        await message.answer("⚡ Энергия (1–10)?", reply_markup=scale_1_10())
    elif step == DailyCheckin.day_rating:
        await message.answer("⭐ Оценка дня (1–10)?", reply_markup=scale_1_10())
    elif step == DailyCheckin.weight:
        await message.answer("⚖️ Вес сегодня (кг)?", reply_markup=day_nav_kb())
    elif step == DailyCheckin.note:
        await message.answer("📝 Заметка о дне?", reply_markup=day_nav_kb())


async def advance(message: Message, state: FSMContext) -> None:
    """Перейти к следующему шагу или завершить, если шаги кончились."""
    current = await state.get_state()
    idx = ORDER_NAMES.index(current) if current in ORDER_NAMES else -1
    if idx == -1 or idx + 1 >= len(ORDER):
        await finish(message, state)
    else:
        await send_step(message, state, ORDER[idx + 1])


async def finish(message: Message, state: FSMContext) -> None:
    await state.clear()
    with SessionLocal() as session:
        log = get_daily_log(session, date.today())
        vit_count = len(log.vitamins) if log else 0

    if log is None:
        await message.answer("Ничего не сохранил за сегодня.", reply_markup=main_menu())
        return

    lines = ["✅ День сохранён!"]
    if log.sleep_hours is not None:
        lines.append(f"Сон: {log.sleep_hours} ч")
    elif log.bedtime or log.wakeup:
        lines.append(
            f"Сон: лёг {log.bedtime or '—'}, встал {log.wakeup or '—'} (неполно)"
        )
    lines.append(f"Тренировка: {'да' if log.trained else 'нет'}")
    if log.work_hours is not None:
        lines.append(f"Работа: {log.work_hours} ч")
    if vit_count:
        lines.append(f"Витамины: {vit_count}")
    rating_parts = [
        ("Настроение", log.mood),
        ("Энергия", log.energy),
        ("Оценка дня", log.day_rating),
    ]
    rating_str = ", ".join(f"{name} {val}" for name, val in rating_parts if val is not None)
    if rating_str:
        lines.append(rating_str)
    if log.weight_kg is not None:
        lines.append(f"Вес: {log.weight_kg} кг")

    lines.append("\nМожешь зайти снова в течение дня — допишешь остальное.")
    await message.answer("\n".join(lines), reply_markup=main_menu())


# --- Запуск чек-ина -------------------------------------------------------

@router.message(F.text == BTN_DAY)
@router.message(Command("day"))
async def start_checkin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "📋 Чек-ин дня. На любом шаге: «⏭ Пропустить» или «✅ Завершить» — "
        "ответы сохраняются сразу, можно вернуться позже."
    )
    await send_step(message, state, DailyCheckin.bedtime)


@router.callback_query(F.data == "start_day")
async def start_checkin_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(
        "📋 Чек-ин дня. На любом шаге: «⏭ Пропустить» или «✅ Завершить»."
    )
    await send_step(callback.message, state, DailyCheckin.bedtime)
    await callback.answer()


# --- Навигация ------------------------------------------------------------

@router.callback_query(StateFilter(*ORDER), F.data == "day_skip")
async def on_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await advance(callback.message, state)
    await callback.answer("Пропущено")


@router.callback_query(StateFilter(*ORDER), F.data == "day_finish")
async def on_finish(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await finish(callback.message, state)
    await callback.answer()


# --- Шаги -----------------------------------------------------------------

@router.message(DailyCheckin.bedtime)
async def set_bedtime(message: Message, state: FSMContext) -> None:
    parsed = parse_time(message.text or "")
    if parsed is None:
        await message.answer("Не понял время. Формат ЧЧ:ММ, например 23:30.")
        return
    _save_field(bedtime=parsed)
    await advance(message, state)


@router.message(DailyCheckin.wakeup)
async def set_wakeup(message: Message, state: FSMContext) -> None:
    parsed = parse_time(message.text or "")
    if parsed is None:
        await message.answer("Не понял время. Формат ЧЧ:ММ, например 7:15.")
        return
    _save_field(wakeup=parsed)
    with SessionLocal() as session:
        log = get_daily_log(session, date.today())
        if log and log.sleep_hours is not None:
            await message.answer(f"Сон: {log.sleep_hours} ч 😴")
    await advance(message, state)


@router.callback_query(DailyCheckin.trained, F.data.startswith("yn:"))
async def set_trained(callback: CallbackQuery, state: FSMContext) -> None:
    trained = callback.data == "yn:yes"
    _save_field(trained=trained)
    await callback.message.edit_text(f"Тренировка: {'да 💪' if trained else 'нет'}")
    await advance(callback.message, state)
    await callback.answer()


@router.message(DailyCheckin.work_hours)
async def set_work_hours(message: Message, state: FSMContext) -> None:
    value = parse_float(message.text or "")
    if value is None:
        await message.answer("Введи число часов, например 4.5.")
        return
    _save_field(work_hours=value)
    await advance(message, state)


@router.callback_query(DailyCheckin.vitamins, F.data.startswith("vit:"))
async def toggle_vitamin(callback: CallbackQuery, state: FSMContext) -> None:
    vid = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = set(data.get("vitamin_ids", []))
    selected.symmetric_difference_update({vid})
    await state.update_data(vitamin_ids=list(selected))
    with SessionLocal() as session:
        vitamins = get_active_vitamins(session)
    await callback.message.edit_reply_markup(reply_markup=vitamins_kb(vitamins, selected))
    await callback.answer()


@router.callback_query(DailyCheckin.vitamins, F.data == "vit_done")
async def vitamins_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    _save_field(vitamin_ids=data.get("vitamin_ids", []))
    await callback.message.edit_text("Витамины записал.")
    await advance(callback.message, state)
    await callback.answer()


@router.callback_query(StateFilter(*SCALE_FIELD.keys()), F.data.startswith("scale:"))
async def set_scale(callback: CallbackQuery, state: FSMContext) -> None:
    field = SCALE_FIELD[await state.get_state()]
    value = int(callback.data.split(":")[1])
    _save_field(**{field: value})
    await callback.message.edit_text(f"{value}/10")
    await advance(callback.message, state)
    await callback.answer()


@router.message(DailyCheckin.weight)
async def set_weight(message: Message, state: FSMContext) -> None:
    value = parse_float(message.text or "")
    if value is None:
        await message.answer("Введи вес числом, например 78.5, или «⏭ Пропустить».")
        return
    _save_field(weight_kg=value)
    await advance(message, state)


@router.message(DailyCheckin.note)
async def set_note(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text:
        _save_field(note=text)
    await finish(message, state)
