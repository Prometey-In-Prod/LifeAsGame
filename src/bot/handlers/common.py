from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.filters import OwnerFilter
from src.bot.keyboards import main_menu

router = Router()
router.message.filter(OwnerFilter())
router.callback_query.filter(OwnerFilter())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Это твоя система LifeAsGame.\n\n"
        "📋 Заполнить день — ежедневный чек-ин\n"
        "💰 Финансы — учёт доходов/расходов\n"
        "🏋️ Тренировка — лог тренировки\n\n"
        "Выбери действие на клавиатуре ниже.",
        reply_markup=main_menu(),
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu())
