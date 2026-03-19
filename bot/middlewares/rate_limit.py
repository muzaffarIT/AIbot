import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from shared.utils.i18n import I18n

class GenerationRateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 3, interval: int = 60):
        self.limit = limit
        self.interval = interval
        self.users: dict[int, list[float]] = {}
        self.i18n = I18n()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        
        text = event.text
        if text:
            triggers = {
                self.i18n.t("ru", "menu.generate_image"),
                self.i18n.t("uz", "menu.generate_image"),
                self.i18n.t("ru", "menu.create_video"),
                self.i18n.t("uz", "menu.create_video"),
                self.i18n.t("ru", "menu.animate_image"),
                self.i18n.t("uz", "menu.animate_image"),
            }
            if text in triggers:
                user_id = event.from_user.id
                now = time.time()
                
                if user_id in self.users:
                    self.users[user_id] = [t for t in self.users[user_id] if now - t < self.interval]
                else:
                    self.users[user_id] = []
                    
                if len(self.users[user_id]) >= self.limit:
                    lang = data.get("lang", "ru")
                    msg = self.i18n.t(lang, "errors.rate_limit") if self.i18n.t(lang, "errors.rate_limit") != "errors.rate_limit" else f"⏳ Пожалуйста, подождите. Разрешено не более {self.limit} запросов в {self.interval} секунд."
                    await event.answer(msg)
                    return
                else:
                    self.users[user_id].append(now)
                    
        return await handler(event, data)
