from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from src.config import OWNER_CHAT_ID


class OwnerFilter(BaseFilter):
    """Пропускает только владельца — данные личные."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return user is not None and user.id == OWNER_CHAT_ID
