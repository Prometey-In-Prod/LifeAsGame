from __future__ import annotations

import re
from datetime import date, time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.filters import OwnerFilter
from src.bot.keyboards import BTN_DAY, main_menu, scale_1_10, skip_kb, vitamins_kb, yes_no
from src.bot.states import DailyCheckin
from src.db.database import SessionLocal
from src.db.repo import compute_sleep_hours, get_active_vitamins, upsert_daily_log

router = Router()
router.message.filter(OwnerFilter())
router.callback_query.filter(OwnerFilter())


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


@router.message(F.text == BTN_DAY)
@router.message(Command("day"))
async def start_checkin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(DailyCheckin.bedtime)
    await message.answer(
        "📋 Чек-ин дня.\n\nВо сколько ты лёг спать? (например, 23:30)"
    )


@router.callback_query(F.data == "start_day")
async def start_checkin_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(DailyCheckin.bedtime)
    await callback.message.answer(
        "📋 Чек-ин дня.\n\nВо сколько ты лёг спать? (например, 23:30)"
    )
    await callback.answer()


@router.message(DailyCheckin.bedtime)
async def set_bedtime(message: Message, state: FSMContext) -> None:
    parsed = parse_time(message.text or "")
    if parsed is None:
        await message.answer("Не понял время. Введи в формате ЧЧ:ММ, например 23:30.")
        return
    await state.update_data(bedtime=parsed.isoformat())
    await state.set_state(DailyCheckin.wakeup)
    await message.answer("Во сколько ты проснулся? (например, 7:15)")


@router.message(DailyCheckin.wakeup)
async def set_wakeup(message: Message, state: FSMContext) -> None:
    parsed = parse_time(message.text or "")
    if parsed is None:
        await message.answer("Не понял время. Введи в формате ЧЧ:ММ, например 7:15.")
        return
    data = await state.get_data()
    bedtime = time.fromisoformat(data["bedtime"])
    sleep_hours = compute_sleep_hours(bedtime, parsed)
    await state.update_data(wakeup=parsed.isoformat())
    await state.set_state(DailyCheckin.trained)
    await message.answer(
        f"Сон: {sleep_hours} ч 😴\n\nБыла тренировка сегодня?", reply_markup=yes_no()
    )


@router.callback_query(DailyCheckin.trained, F.data.startswith("yn:"))
async def set_trained(callback: CallbackQuery, state: FSMContext) -> None:
    trained = callback.data == "yn:yes"
    await state.update_data(trained=trained)
    await state.set_state(DailyCheckin.work_hours)
    await callback.message.edit_text(
        f"Тренировка: {'да 💪' if trained else 'нет'}"
    )
    await callback.message.answer("Сколько часов интенсивно работал? (например, 4.5)")
    await callback.answer()


@router.message(DailyCheckin.work_hours)
async def set_work_hours(message: Message, state: FSMContext) -> None:
    value = parse_float(message.text or "")
    if value is None:
        await message.answer("Введи число часов, например 4.5.")
        return
    await state.update_data(work_hours=value, vitamin_ids=[])
    await state.set_state(DailyCheckin.vitamins)
    with SessionLocal() as session:
        vitamins = get_active_vitamins(session)
    await message.answer(
        "Какие витамины принял? Отмечай и жми «Готово».",
        reply_markup=vitamins_kb(vitamins, set()),
    )


@router.callback_query(DailyCheckin.vitamins, F.data.startswith("vit:"))
async def toggle_vitamin(callback: CallbackQuery, state: FSMContext) -> None:
    vid = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = set(data.get("vitamin_ids", []))
    selected.symmetric_difference_update({vid})
    await state.update_data(vitamin_ids=list(selected))
    with SessionLocal() as session:
        vitamins = get_active_vitamins(session)
    await callback.message.edit_reply_markup(
        reply_markup=vitamins_kb(vitamins, selected)
    )
    await callback.answer()


@router.callback_query(DailyCheckin.vitamins, F.data == "vit_done")
async def vitamins_done(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DailyCheckin.mood)
    await callback.message.edit_text("Витамины записал.")
    await callback.message.answer("Настроение (1–10)?", reply_markup=scale_1_10())
    await callback.answer()


@router.callback_query(DailyCheckin.mood, F.data.startswith("scale:"))
async def set_mood(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(mood=int(callback.data.split(":")[1]))
    await state.set_state(DailyCheckin.energy)
    await callback.message.edit_text(f"Настроение: {callback.data.split(':')[1]}/10")
    await callback.message.answer("Энергия (1–10)?", reply_markup=scale_1_10())
    await callback.answer()


@router.callback_query(DailyCheckin.energy, F.data.startswith("scale:"))
async def set_energy(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(energy=int(callback.data.split(":")[1]))
    await state.set_state(DailyCheckin.day_rating)
    await callback.message.edit_text(f"Энергия: {callback.data.split(':')[1]}/10")
    await callback.message.answer("Оценка дня (1–10)?", reply_markup=scale_1_10())
    await callback.answer()


@router.callback_query(DailyCheckin.day_rating, F.data.startswith("scale:"))
async def set_day_rating(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(day_rating=int(callback.data.split(":")[1]))
    await state.set_state(DailyCheckin.weight)
    await callback.message.edit_text(f"Оценка дня: {callback.data.split(':')[1]}/10")
    await callback.message.answer(
        "Вес сегодня (кг)? Можно пропустить.", reply_markup=skip_kb()
    )
    await callback.answer()


@router.message(DailyCheckin.weight)
async def set_weight(message: Message, state: FSMContext) -> None:
    value = parse_float(message.text or "")
    if value is None:
        await message.answer("Введи вес числом, например 78.5, или нажми «Пропустить».")
        return
    await state.update_data(weight_kg=value)
    await _ask_note(message, state)


@router.callback_query(DailyCheckin.weight, F.data == "skip")
async def skip_weight(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Вес пропущен.")
    await _ask_note(callback.message, state)
    await callback.answer()


async def _ask_note(message: Message, state: FSMContext) -> None:
    await state.set_state(DailyCheckin.note)
    await message.answer(
        "Заметка о дне? Можно пропустить.", reply_markup=skip_kb()
    )


@router.message(DailyCheckin.note)
async def set_note(message: Message, state: FSMContext) -> None:
    await state.update_data(note=(message.text or "").strip())
    await _finish(message, state)


@router.callback_query(DailyCheckin.note, F.data == "skip")
async def skip_note(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Заметка пропущена.")
    await _finish(callback.message, state)
    await callback.answer()


async def _finish(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()

    with SessionLocal() as session:
        log = upsert_daily_log(
            session,
            log_date=date.today(),
            bedtime=time.fromisoformat(data["bedtime"]),
            wakeup=time.fromisoformat(data["wakeup"]),
            trained=data["trained"],
            work_hours=data["work_hours"],
            vitamin_ids=data.get("vitamin_ids", []),
            mood=data["mood"],
            energy=data["energy"],
            day_rating=data["day_rating"],
            weight_kg=data.get("weight_kg"),
            note=data.get("note") or None,
        )
        sleep_hours = log.sleep_hours
        vit_count = len(data.get("vitamin_ids", []))

    summary = (
        "✅ День записан!\n"
        f"Сон: {sleep_hours} ч\n"
        f"Тренировка: {'да' if data['trained'] else 'нет'}\n"
        f"Работа: {data['work_hours']} ч\n"
        f"Витамины: {vit_count}\n"
        f"Настроение/энергия/день: {data['mood']}/{data['energy']}/{data['day_rating']}"
    )
    if data.get("weight_kg"):
        summary += f"\nВес: {data['weight_kg']} кг"
    await message.answer(summary, reply_markup=main_menu())
