from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.keyboards import STATUSES, status_keyboard

router = Router(name="admin")


def is_admin(user_id: int, admin_ids: list[int]) -> bool:
    return user_id in admin_ids


@router.message(F.text.startswith("/applications"))
async def applications_list(message: Message, db, settings) -> None:
    if not is_admin(message.from_user.id, settings.admin_ids):
        await message.answer("Недостаточно прав.")
        return

    items = await db.list_applications(limit=10)

    if not items:
        await message.answer("Заявок пока нет.")
        return

    for item in items:
        await message.answer(
            f"#{item.id} | {item.full_name}\n"
            f"Телефон: {item.phone}\n"
            f"Продукт: {item.product}\n"
            f"Статус: {STATUSES.get(item.status, item.status)}",
            reply_markup=status_keyboard(item.id),
        )


@router.callback_query(F.data.startswith("status:"))
async def status_change(callback: CallbackQuery, db, settings) -> None:
    if not is_admin(callback.from_user.id, settings.admin_ids):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    _, application_id_str, new_status = callback.data.split(":", 2)
    application_id = int(application_id_str)

    ok = await db.update_status(
        application_id,
        new_status,
        callback.from_user.id,
        note="Статус изменён администратором",
    )

    if not ok:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    application = await db.get_application(application_id)

    await callback.message.edit_text(
        f"#{application.id} | {application.full_name}\n"
        f"Телефон: {application.phone}\n"
        f"Продукт: {application.product}\n"
        f"Статус: {STATUSES.get(application.status, application.status)}",
        reply_markup=status_keyboard(application.id),
    )

    await callback.answer("Статус обновлён")

    await callback.bot.send_message(
        application.telegram_user_id,
        f"ℹ️ Статус заявки #{application.id} обновлён: "
        f"{STATUSES.get(application.status, application.status)}",
    )


@router.callback_query(F.data.startswith("refresh:"))
async def refresh_card(callback: CallbackQuery, db, settings) -> None:
    if not is_admin(callback.from_user.id, settings.admin_ids):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    _, application_id_str = callback.data.split(":", 1)

    application = await db.get_application(int(application_id_str))

    if application is None:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    await callback.message.edit_text(
        f"#{application.id} | {application.full_name}\n"
        f"Телефон: {application.phone}\n"
        f"Продукт: {application.product}\n"
        f"Статус: {STATUSES.get(application.status, application.status)}\n"
        f"Обновлено: {application.updated_at}",
        reply_markup=status_keyboard(application.id),
    )

    await callback.answer("Карточка обновлена")