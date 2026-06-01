from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models import Category, Vitamin

BTN_DAY = "📋 Заполнить день"
BTN_FINANCE = "💰 Финансы"
BTN_WORKOUT = "🏋️ Тренировка"

KIND_LABELS = {
    "income": "💰 Доход",
    "expense": "💸 Расход",
    "saving": "🐷 Сбережение",
    "debt": "💳 Долг/кредит",
}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DAY)],
            [KeyboardButton(text=BTN_FINANCE), KeyboardButton(text=BTN_WORKOUT)],
        ],
        resize_keyboard=True,
    )


def yes_no() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data="yn:yes"),
                InlineKeyboardButton(text="Нет", callback_data="yn:no"),
            ]
        ]
    )


def scale_1_10() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for n in range(1, 11):
        builder.button(text=str(n), callback_data=f"scale:{n}")
    builder.adjust(5, 5)
    return builder.as_markup()


def skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip")]]
    )


def finance_kind_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for kind, label in KIND_LABELS.items():
        builder.button(text=label, callback_data=f"fin_kind:{kind}")
    builder.adjust(2)
    return builder.as_markup()


def finance_categories_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in categories:
        builder.button(text=c.name, callback_data=f"fin_cat:{c.id}")
    builder.adjust(2)
    return builder.as_markup()


def vitamins_kb(vitamins: list[Vitamin], selected: set[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for v in vitamins:
        mark = "✅ " if v.id in selected else "▫️ "
        builder.button(text=f"{mark}{v.name}", callback_data=f"vit:{v.id}")
    builder.button(text="Готово ✓", callback_data="vit_done")
    builder.adjust(2)
    return builder.as_markup()
