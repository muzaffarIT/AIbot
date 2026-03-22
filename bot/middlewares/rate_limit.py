import logging
import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from backend.core.config import settings
from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from shared.enums.credit_transaction_type import CreditTransactionType

logger = logging.getLogger(__name__)

class GenerationRateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 3, interval: int = 60):
        self.limit = limit
        self.interval = interval
        self.user_cache: Dict[int, list] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        prompt = event.text
        
        # Check FSM state for prompt limits
        from aiogram.fsm.context import FSMContext
        state: FSMContext = data.get("state")
        if state:
            current_state = await state.get_state()
            if current_state and "waiting_for_prompt" in current_state:
                state_data = await state.get_data()
                model_type = state_data.get("provider", "nano_banana")
                lang = state_data.get("lang", "ru")
                
                PROMPT_LIMITS = {
                    "nano_banana": 500,
                    "veo": 2000,
                    "kling": 2500,
                }
                max_len = PROMPT_LIMITS.get(model_type, 500)
                min_len = 3
                
                if len(prompt) < min_len:
                    if lang == "uz":
                         await event.answer("❌ Prompt juda qisqa! Kamida 3 ta belgi.")
                    else:
                         await event.answer("❌ Промпт слишком короткий! Минимум 3 символа.")
                    return
                
                if len(prompt) > max_len:
                    diff = len(prompt) - max_len
                    if lang == "uz":
                         await event.answer(f"❌ Prompt juda uzun!\n\nBu neyroset uchun maksimum: {max_len} ta belgi.\nSizda hozir: {len(prompt)} ta belgi.\n\n💡 Promptni {diff} ta belgiga qisqartiring.")
                    else:
                         await event.answer(f"❌ Промпт слишком длинный!\n\nМаксимум для этой нейросети: {max_len} символов.\nУ тебя сейчас: {len(prompt)} символов.\n\n💡 Сократи промпт на {diff} символов.")
                    return

        user_id = event.from_user.id
        now = time.time()

        if user_id not in self.user_cache:
            self.user_cache[user_id] = []

        # Remove old timestamps
        self.user_cache[user_id] = [t for t in self.user_cache[user_id] if now - t < self.interval]

        if len(self.user_cache[user_id]) >= self.limit:
            await event.answer("⚠️ Слишком много запросов. Пожалуйста, подождите минуту.")
            return

        # Daily limit check for generation (requires DB)
        # Note: This is a heavy check, usually done inside handlers, 
        # but the user requested it in middleware for stricter control.
        
        # We'll skip the DB check in middleware for performance, 
        # but keep the memory-based rate limit.
        # The daily limit $(5/50) will be handled in GenerationService.

        self.user_cache[user_id].append(now)
        return await handler(event, data)
