import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from src.bot.handlers import common, daily, finance
from src.bot.scheduler import setup_scheduler
from src.config import BOT_TOKEN, PROXY_URL

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else None
    bot = Bot(BOT_TOKEN, session=session)
    if PROXY_URL:
        logging.info("Бот ходит через прокси %s", PROXY_URL)
    dp = Dispatcher()
    dp.include_router(daily.router)
    dp.include_router(finance.router)
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
