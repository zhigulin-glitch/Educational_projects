from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

STATUSES = {
    "new": "Новая",
    "in_progress": "В работе",
    "done": "Завершена",
    "cancelled": "Отменена",
}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Новая заявка")],
            [KeyboardButton(text="📂 Мои заявки")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def status_keyboard(application_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟡 В работе",
                    callback_data=f"status:{application_id}:in_progress",
                ),
                InlineKeyboardButton(
                    text="✅ Завершить",
                    callback_data=f"status:{application_id}:done",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⛔ Отменить",
                    callback_data=f"status:{application_id}:cancelled",
                ),
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data=f"refresh:{application_id}",
                ),
            ],
        ]
    )