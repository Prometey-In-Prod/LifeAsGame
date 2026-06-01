from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bot.reports import build_monthly_finance_report
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


async def send_monthly_report(bot: Bot) -> None:
    today = date.today()
    # 1-го числа отчитываемся за предыдущий месяц
    year = today.year - 1 if today.month == 1 else today.year
    month = 12 if today.month == 1 else today.month - 1
    await bot.send_message(OWNER_CHAT_ID, build_monthly_finance_report(year, month))


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
    scheduler.add_job(
        send_monthly_report,
        CronTrigger(day=1, hour=10, minute=0, timezone=tz),
        args=[bot],
        id="monthly_report",
        replace_existing=True,
    )
    return scheduler
