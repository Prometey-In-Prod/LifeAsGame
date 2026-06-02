from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.filters import OwnerFilter
from src.bot.keyboards import (
    BTN_WORKOUT,
    main_menu,
    workout_after_set_kb,
    workout_start_kb,
)
from src.bot.states import WorkoutFlow
from src.db.database import SessionLocal
from src.db.repo import (
    add_workout_set,
    delete_workout_session,
    finish_workout,
    get_workout_sets,
    start_workout,
)

router = Router()
router.message.filter(OwnerFilter())
router.callback_query.filter(OwnerFilter())


def parse_set(text: str) -> tuple[int, float | None] | None:
    """'12x40' / '12х40' / '12*40' / '12 40' / '12' -> (reps, weight|None)."""
    t = text.strip().lower().replace("х", "x").replace("*", "x").replace(",", ".")
    t = re.sub(r"\s*x\s*", "x", t)
    try:
        if "x" in t:
            reps_s, weight_s = t.split("x", 1)
            reps, weight = int(reps_s), float(weight_s)
        else:
            parts = t.split()
            reps = int(parts[0])
            weight = float(parts[1]) if len(parts) > 1 else None
    except (ValueError, IndexError):
        return None
    if reps <= 0 or (weight is not None and weight < 0):
        return None
    return reps, weight


@router.message(F.text == BTN_WORKOUT)
@router.message(Command("workout"))
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    with SessionLocal() as session:
        ws = start_workout(session)
        session_id = ws.id
    await state.update_data(session_id=session_id)
    await state.set_state(WorkoutFlow.exercise)
    await message.answer(
        "🏋️ Тренировка началась!\n\nНазвание первого упражнения? (например, «Жим лёжа»)",
        reply_markup=workout_start_kb(),
    )


@router.message(WorkoutFlow.exercise)
async def set_exercise(message: Message, state: FSMContext) -> None:
    exercise = (message.text or "").strip()
    if not exercise:
        await message.answer("Введи название упражнения.")
        return
    await state.update_data(exercise=exercise, set_number=0)
    await state.set_state(WorkoutFlow.set_input)
    await message.answer(
        f"<b>{exercise}</b>\nПодход 1 — повторы и вес: «12x40» (или просто «12» без веса).",
        parse_mode="HTML",
    )


@router.message(WorkoutFlow.set_input)
async def add_set(message: Message, state: FSMContext) -> None:
    parsed = parse_set(message.text or "")
    if parsed is None:
        await message.answer("Формат: «12x40» (повторыxвес) или «12». Попробуй ещё раз.")
        return
    reps, weight = parsed
    data = await state.get_data()
    set_number = data.get("set_number", 0) + 1
    await state.update_data(set_number=set_number)
    with SessionLocal() as session:
        add_workout_set(
            session,
            session_id=data["session_id"],
            exercise=data["exercise"],
            set_number=set_number,
            reps=reps,
            weight_kg=weight,
        )
    weight_str = f"{weight:g} кг" if weight is not None else "без веса"
    await message.answer(
        f"✔️ {data['exercise']} — подход {set_number}: {reps} × {weight_str}",
        reply_markup=workout_after_set_kb(),
    )


@router.callback_query(WorkoutFlow.set_input, F.data == "wo:more")
async def more_set(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    next_set = data.get("set_number", 0) + 1
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"<b>{data['exercise']}</b> — подход {next_set}: введи «повторыxвес».",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(WorkoutFlow.set_input, F.data == "wo:next")
async def next_exercise(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(WorkoutFlow.exercise)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Название следующего упражнения?", reply_markup=workout_start_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "wo:finish")
async def finish(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    session_id = data.get("session_id")
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)

    if session_id is None:
        await callback.answer()
        return

    with SessionLocal() as session:
        sets = get_workout_sets(session, session_id)
        if not sets:
            delete_workout_session(session, session_id)
        else:
            finish_workout(session, session_id)

    if not sets:
        await callback.message.answer(
            "Тренировка пустая — не сохраняю.", reply_markup=main_menu()
        )
        await callback.answer()
        return

    by_exercise: dict[str, list] = {}
    total_volume = 0.0
    for s in sets:
        by_exercise.setdefault(s.exercise, []).append(s)
        if s.weight_kg:
            total_volume += s.reps * s.weight_kg

    lines = ["🏁 Тренировка завершена!", ""]
    for exercise, ex_sets in by_exercise.items():
        sets_str = ", ".join(
            f"{s.reps}×{s.weight_kg:g}" if s.weight_kg else f"{s.reps}"
            for s in ex_sets
        )
        lines.append(f"• {exercise}: {sets_str}")
    lines.append("")
    lines.append(f"Всего подходов: {len(sets)}")
    if total_volume:
        lines.append(f"Тоннаж: {total_volume:g} кг")

    await callback.message.answer("\n".join(lines), reply_markup=main_menu())
    await callback.answer()
