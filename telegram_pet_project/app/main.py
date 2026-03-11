import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings
from app.db import Database
from app.handlers.admin import router as admin_router
from app.handlers.user import router as user_router
from app.keyboards import status_keyboard
from app.services.external_api import ExternalAPIClient


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    settings = get_settings()

    db = Database(settings.db_path)
    await db.connect()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=MemoryStorage())

    dp["db"] = db
    dp["settings"] = settings
    dp["external_api"] = ExternalAPIClient(
        settings.external_api_url,
        settings.external_api_timeout
    )
    dp["status_keyboard"] = status_keyboard

    dp.include_router(user_router)
    dp.include_router(admin_router)

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
