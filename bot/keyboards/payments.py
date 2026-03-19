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

def payment_methods_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Payme", callback_data=f"pay:payme:{order_id}"),
                InlineKeyboardButton(text="💳 Click", callback_data=f"pay:click:{order_id}")
            ],
            [
                InlineKeyboardButton(text="💳 Картой (Cards)", callback_data=f"pay:cards:{order_id}")
            ]
        ]
    )

def payment_url_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить 💸", url=url)]
        ]
    )
