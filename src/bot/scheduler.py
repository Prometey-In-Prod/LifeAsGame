from __future__ import annotations

from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import OWNER_CHAT_ID, TZ


async def send_daily_reminder(bot: Bot) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Заполнить день", callback_data="start_day")]
        ]
    )
    await bot.send_message(
        OWNER_CHAT_ID, "Пора подвести итоги дня 🌙", reply_markup=kb
    )


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    tz = ZoneInfo(TZ)
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(
        send_daily_reminder,
        CronTrigger(hour=21, minute=0, timezone=tz),
        args=[bot],
        id="daily_reminder",
        replace_existing=True,
    )
    return scheduler
