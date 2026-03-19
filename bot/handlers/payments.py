from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, LabeledPrice, PreCheckoutQuery
from backend.core.config import settings
import base64

from backend.services.balance_service import BalanceService
from backend.services.order_service import OrderService
from backend.services.payment_service import PaymentService
from backend.services.plan_service import PlanService
from backend.services.user_service import UserService
from bot.keyboards.payments import (
    payment_confirmation_keyboard,
    plan_selection_keyboard,
    payment_methods_keyboard,
    payment_url_keyboard,
)
from bot.services.db_session import get_db_session
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()

PLAN_TRIGGERS = {
    "/plans",
    i18n.t("ru", "menu.buy"),
    i18n.t("uz", "menu.buy"),
}


def _build_plan_label(plan) -> str:
    return f"{plan.name} | {plan.credits_amount} credits | {plan.price} {plan.currency}"


@router.message(F.text.in_(PLAN_TRIGGERS))
async def show_plans(message: Message) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        plan_service = PlanService(db)

        user = user_service.get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        lang = user.language_code
        plans = plan_service.get_active_plans()

        if not plans:
            await message.answer(i18n.t(lang, "plans.empty"))
            return

        lines = [i18n.t(lang, "orders.choose_plan"), ""]
        for plan in plans:
            lines.append(
                f"{plan.name}: {plan.credits_amount} credits, {plan.price} {plan.currency}"
            )

        keyboard = plan_selection_keyboard(
            [(plan.code, _build_plan_label(plan)) for plan in plans]
        )
        await message.answer("\n".join(lines), reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data.startswith("plan:"))
async def create_order_and_payment(callback: CallbackQuery) -> None:
    plan_code = callback.data.split(":", maxsplit=1)[1]
    db = get_db_session()
    try:
        user_service = UserService(db)
        plan_service = PlanService(db)
        order_service = OrderService(db)
        payment_service = PaymentService(db)

        user = user_service.get_or_create_user(
            telegram_user_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
        )
        lang = user.language_code
        plan = plan_service.get_plan_by_code(plan_code)

        if not plan or not plan.is_active:
            await callback.answer(i18n.t(lang, "plans.empty"), show_alert=True)
            return

        order = order_service.create_order_for_plan(
            user_id=user.id,
            plan_code=plan.code,
            payment_method="online",
        )

        lines = [
            i18n.t(lang, "orders.created"),
            i18n.t(lang, "orders.number", order_number=order.order_number),
            i18n.t(lang, "orders.plan", plan_name=plan.name),
            i18n.t(lang, "orders.amount", amount=order.amount, currency=order.currency),
            "Выберите удобный способ оплаты:",
        ]

        if callback.message:
            await callback.message.answer(
                "\n".join(lines),
                reply_markup=payment_methods_keyboard(order.id),
            )
        await callback.answer()
    finally:
        db.close()

@router.callback_query(F.data.startswith("pay:"))
async def process_payment_selection(callback: CallbackQuery) -> None:
    _, provider, order_id_str = callback.data.split(":", maxsplit=2)
    order_id = int(order_id_str)
    db = get_db_session()
    try:
        user_service = UserService(db)
        payment_service = PaymentService(db)
        order_service = OrderService(db)

        user = user_service.get_or_create_user(
            telegram_user_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
        )
        lang = user.language_code

        order = order_service.repo.get_by_id(order_id)
        if not order:
            await callback.answer(i18n.t(lang, "orders.empty"), show_alert=True)
            return

        payment = payment_service.create_payment_for_order(
            order_id=order.id,
            provider=provider,
            method="online",
        )

        usd_to_uzs = 12500
        if provider == "payme":
            amount_tiyins = int(payment.amount * usd_to_uzs * 100)
            payload = f"m={settings.payme_merchant_id};ac.order_id={payment.id};a={amount_tiyins}"
            encoded = base64.b64encode(payload.encode("utf-8")).decode("utf-8")
            url = f"https://checkout.paycom.uz/{encoded}"
            
            await callback.message.edit_text(
                f"К оплате: {payment.amount} USD (~{int(payment.amount * usd_to_uzs)} UZS)\nНажмите кнопку ниже, чтобы перейти в Payme.",
                reply_markup=payment_url_keyboard(url)
            )
        elif provider == "click":
            amount_uzs = int(payment.amount * usd_to_uzs)
            url = (
                f"https://my.click.uz/services/pay?service_id={settings.click_service_id}"
                f"&merchant_id={settings.click_merchant_id}&amount={amount_uzs}&transaction_param={payment.id}"
            )
            
            await callback.message.edit_text(
                f"К оплате: {payment.amount} USD (~{amount_uzs} UZS)\nНажмите кнопку ниже, чтобы перейти в Click.",
                reply_markup=payment_url_keyboard(url)
            )
        elif provider == "cards":
            amount_cents = int(payment.amount * 100)
            prices = [LabeledPrice(label=f"Оплата заказа #{order.order_number}", amount=amount_cents)]
            
            await callback.message.answer_invoice(
                title=f"Заказ #{order.order_number}",
                description=f"Оплата заказа на {payment.amount} USD",
                payload=str(payment.id),
                provider_token=settings.cards_provider_key,
                currency="USD",
                prices=prices,
                start_parameter="payment",
            )
            await callback.message.delete()
        
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data.startswith("confirm_payment:"))
async def confirm_payment(callback: CallbackQuery) -> None:
    payment_id = int(callback.data.split(":", maxsplit=1)[1])
    db = get_db_session()
    try:
        user_service = UserService(db)
        payment_service = PaymentService(db)
        balance_service = BalanceService(db)

        user = user_service.get_or_create_user(
            telegram_user_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
        )
        lang = user.language_code
        payment = payment_service.confirm_payment(payment_id)
        order = payment_service.order_repo.get_by_id(payment.order_id)
        plan = payment_service.plan_repo.get_by_id(order.plan_id) if order else None
        credits = balance_service.get_balance_value(user.id)

        lines = [
            i18n.t(lang, "payments.confirmed"),
            i18n.t(lang, "orders.paid"),
        ]
        if plan:
            lines.append(
                i18n.t(lang, "payments.credits_added", credits=plan.credits_amount)
            )
        lines.append(i18n.t(lang, "balance.current", credits=credits))

        if callback.message:
            await callback.message.answer("\n".join(lines))
        await callback.answer()
    finally:
        db.close()

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message) -> None:
    payment_id_str = message.successful_payment.invoice_payload
    if not payment_id_str.isdigit():
        return
        
    payment_id = int(payment_id_str)
    db = get_db_session()
    try:
        user_service = UserService(db)
        payment_service = PaymentService(db)
        
        user = user_service.get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        lang = user.language_code
        
        payment = payment_service.confirm_payment(payment_id)
        
        lines = [
            i18n.t(lang, "payments.confirmed"),
            i18n.t(lang, "orders.paid"),
        ]
        await message.answer("\n".join(lines))
    finally:
        db.close()
