from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from backend.services.balance_service import BalanceService
from backend.services.order_service import OrderService
from backend.services.payment_service import PaymentService
from backend.services.plan_service import PlanService
from backend.services.user_service import UserService
from bot.keyboards.payments import (
    payment_confirmation_keyboard,
    plan_selection_keyboard,
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
            payment_method="card",
        )
        payment = payment_service.create_payment_for_order(
            order_id=order.id,
            provider="cards",
            method="card",
        )

        lines = [
            i18n.t(lang, "orders.created"),
            i18n.t(lang, "orders.number", order_number=order.order_number),
            i18n.t(lang, "orders.plan", plan_name=plan.name),
            i18n.t(lang, "orders.amount", amount=order.amount, currency=order.currency),
            i18n.t(lang, "payments.created"),
            i18n.t(lang, "payments.number", payment_id=payment.id),
            i18n.t(lang, "payments.status", status=payment.status),
        ]

        if callback.message:
            await callback.message.answer(
                "\n".join(lines),
                reply_markup=payment_confirmation_keyboard(payment.id),
            )
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
