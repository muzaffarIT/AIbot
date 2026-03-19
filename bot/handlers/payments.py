import json
from aiogram import F, Router, Bot
from aiogram.types import Message, PreCheckoutQuery
from backend.services.user_service import UserService
from bot.services.db_session import get_db_session
from bot.services.payment_service import BotPaymentService

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
        print(f"Error parse web_app_data: {e}")

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message) -> None:
    payload = message.successful_payment.invoice_payload
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(message.from_user.id)
        if not user:
            # Fallback if user doesn't exist yet
            user = user_service.get_or_create_user(
                telegram_user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            
        credited_amount = BotPaymentService.process_successful_payment(user.id, payload)
        if credited_amount > 0:
            await message.answer(f"✅ Оплата успешна! Вам начислено {credited_amount} кредитов.\nСпасибо за покупку.")
        else:
            await message.answer("⚠️ Оплата прошла, но возникла ошибка при начислении кредитов. Обратитесь в поддержку.")
    finally:
        db.close()

