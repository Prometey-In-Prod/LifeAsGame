import asyncio
import logging

from aiogram import Bot, Dispatcher

from src.bot.handlers import common, daily
from src.bot.scheduler import setup_scheduler
from src.config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(daily.router)
    dp.include_router(common.router)

    scheduler = setup_scheduler(bot)
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
