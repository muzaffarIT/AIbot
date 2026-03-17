from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def plan_selection_keyboard(plans: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"plan:{code}")]
            for code, label in plans
        ]
    )


def payment_confirmation_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить оплату", callback_data=f"confirm_payment:{payment_id}")]
        ]
    )
