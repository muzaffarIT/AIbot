from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from backend.services.generation_service import GenerationService
from backend.services.user_service import UserService
from bot.services.db_session import get_db_session
from bot.states.kling_states import KlingStates
from shared.enums.providers import AIProvider
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()

TRIGGERS = {
    i18n.t("ru", "menu.animate_image"),
    i18n.t("uz", "menu.animate_image"),
}


@router.message(F.text.in_(TRIGGERS))
async def ask_for_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(KlingStates.waiting_for_prompt)
    await message.answer("Отправьте prompt для анимации через Kling Motion.")


@router.message(KlingStates.waiting_for_prompt)
async def create_kling_job(message: Message, state: FSMContext) -> None:
    db = get_db_session()
    try:
        user = UserService(db).get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        job = GenerationService(db).create_job_for_user(
            telegram_user_id=user.telegram_user_id,
            provider=AIProvider.KLING,
            prompt=message.text or "",
        )

        lines = [
            "Задача на Kling Motion создана.",
            f"Job ID: {job.id}",
            f"Статус: {job.status}",
            f"Списано кредитов: {job.credits_reserved}",
        ]
        if job.result_url:
            lines.append(f"Результат: {job.result_url}")

        await message.answer("\n".join(lines))
    except ValueError as exc:
        await message.answer(str(exc))
    finally:
        await state.clear()
        db.close()
