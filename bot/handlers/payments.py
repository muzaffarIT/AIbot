import json
import logging
from aiogram import F, Router, Bot
from aiogram.types import Message, PreCheckoutQuery
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from bot.services.db_session import get_db_session
from bot.services.payment_service import BotPaymentService
from bot.keyboards.main_menu import main_inline_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.web_app_data)
async def web_app_data_handler(message: Message, bot: Bot) -> None:
    data = message.web_app_data.data
    try:
        parsed = json.loads(data)
        if parsed.get("action") == "buy_plan":
            package_id = parsed.get("package_id")
            if package_id:
                await BotPaymentService.send_invoice(bot, message.chat.id, package_id)
    except Exception as e:
        logger.error(f"Error parsing web_app_data: {e}")


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot) -> None:
    payload = message.successful_payment.invoice_payload
    db = get_db_session()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        user = user_service.get_user_by_telegram_id(message.from_user.id)
        if not user:
            user = user_service.get_or_create_user(
                telegram_user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )

        credited_amount = BotPaymentService.process_successful_payment(user.id, payload)
        balance = balance_service.get_balance_value(user.id)

        if credited_amount > 0:
            logger.info(f"Payment success: user={user.telegram_user_id}, credited={credited_amount}")

            # Trigger referral bonus if user was referred
            if user.referred_by_telegram_id and not user.referral_bonus_paid:
                from bot.handlers.referral import notify_referrer_on_purchase
                import asyncio
                asyncio.create_task(
                    notify_referrer_on_purchase(bot, user.id)
                )

            await message.answer(
                f"✅ <b>Оплата прошла успешно!</b>\n\n"
                f"💰 Начислено: <b>{credited_amount}</b> кредитов\n"
                f"💳 Текущий баланс: <b>{balance}</b> кредитов\n\n"
                f"Спасибо за покупку! Теперь создавай нейроарт 🎨",
                parse_mode="HTML",
                reply_markup=main_inline_keyboard(),
            )
        else:
            logger.error(f"Payment credited 0 for user={user.telegram_user_id}, payload={payload}")
            await message.answer(
                "⚠️ Оплата прошла, но возникла ошибка при начислении кредитов.\n"
                "Обратитесь в поддержку: @khaetov_000"
            )
    finally:
        db.close()

