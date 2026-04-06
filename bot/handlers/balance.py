from aiogram import F, Router
from aiogram.types import Message

from backend.services.balance_service import BalanceService
from backend.services.user_service import UserService
from bot.services.db_session import get_db_session
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()

BALANCE_TRIGGERS = {
    i18n.t("ru", "menu.balance"),
    i18n.t("uz", "menu.balance"),
}


def _format_transaction_line(transaction) -> str:
    sign = "+" if transaction.amount >= 0 else ""
    label = transaction.comment or transaction.transaction_type
    return f"{sign}{transaction.amount} -> {label}"


@router.message(F.text.in_(BALANCE_TRIGGERS))
async def show_balance(message: Message) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        user = user_service.get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        lang = user.language_code
        credits = balance_service.get_balance_value(user.id)
        transactions = balance_service.get_last_transactions(user.id, limit=5)

        lines = [i18n.t(lang, "balance.current", credits=credits)]
        if transactions:
            lines.extend(
                [
                    "",
                    i18n.t(lang, "balance.history.title"),
                    *[_format_transaction_line(item) for item in transactions],
                ]
            )
        else:
            lines.extend(["", i18n.t(lang, "balance.history.empty")])

        await message.answer("\n".join(lines))
    finally:
        db.close()
