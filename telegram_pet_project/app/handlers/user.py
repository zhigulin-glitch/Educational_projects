from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.keyboards import STATUSES, main_menu
from app.services.validators import normalize_phone, validate_phone

router = Router(name="user")


class ApplicationForm(StatesGroup):
    full_name = State()
    phone = State()
    product = State()
    comment = State()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Я бот для приёма и отслеживания заявок. Выбери действие в меню ниже.",
        reply_markup=main_menu(),
    )


@router.message(F.text == "ℹ️ Помощь")
async def help_handler(message: Message) -> None:
    await message.answer(
        "Что умеет бот:\n"
        "• принимает заявку в несколько шагов;\n"
        "• сохраняет контакты и историю изменений;\n"
        "• показывает статус заявки;\n"
        "• уведомляет администратора о новых заявках."
    )


@router.message(F.text == "📝 Новая заявка")
async def new_application(message: Message, state: FSMContext) -> None:
    await state.set_state(ApplicationForm.full_name)
    await message.answer("Введите имя и фамилию:")


@router.message(ApplicationForm.full_name)
async def form_full_name(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if len(text) < 3:
        await message.answer("Имя слишком короткое. Введите корректное ФИО.")
        return

    await state.update_data(full_name=text)
    await state.set_state(ApplicationForm.phone)
    await message.answer("Введите телефон в формате +79990001122:")


@router.message(ApplicationForm.phone)
async def form_phone(message: Message, state: FSMContext) -> None:
    phone = normalize_phone(message.text or "")

    if not validate_phone(phone):
        await message.answer("Телефон выглядит некорректно. Попробуйте ещё раз.")
        return

    await state.update_data(phone=phone)
    await state.set_state(ApplicationForm.product)
    await message.answer("Какой товар или услуга интересует?")


@router.message(ApplicationForm.product)
async def form_product(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if len(text) < 2:
        await message.answer("Опишите товар или услугу подробнее.")
        return

    await state.update_data(product=text)
    await state.set_state(ApplicationForm.comment)
    await message.answer("Добавьте комментарий или напишите '-' чтобы пропустить.")


@router.message(ApplicationForm.comment)
async def form_comment(
    message: Message,
    state: FSMContext,
    db,
    external_api,
    settings,
    status_keyboard,
) -> None:

    data = await state.get_data()

    comment = (message.text or "").strip()
    if comment == "-":
        comment = None

    application_id = await db.create_application(
        telegram_user_id=message.from_user.id,
        telegram_username=message.from_user.username,
        full_name=data["full_name"],
        phone=data["phone"],
        product=data["product"],
        comment=comment,
    )

    payload = {
        "application_id": application_id,
        "telegram_user_id": message.from_user.id,
        "username": message.from_user.username,
        "full_name": data["full_name"],
        "phone": data["phone"],
        "product": data["product"],
        "comment": comment,
        "status": "new",
    }

    ok, external_response = await external_api.send_application(payload)

    if not ok:
        await db.add_history(
            application_id=application_id,
            old_status="new",
            new_status="new",
            actor_user_id=message.from_user.id,
            note="Ошибка отправки во внешний REST API",
            payload={"details": external_response},
        )

    await state.clear()

    await message.answer(
        f"✅ Заявка #{application_id} создана. Текущий статус: {STATUSES['new']}.",
        reply_markup=main_menu(),
    )

    admin_text = (
        f"📥 Новая заявка #{application_id}\n"
        f"Клиент: {data['full_name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Товар/услуга: {data['product']}\n"
        f"Комментарий: {comment or '—'}\n"
        f"Внешний API: {'OK' if ok else 'ERROR'}"
    )

    for admin_id in settings.admin_ids:
        await message.bot.send_message(
            admin_id,
            admin_text,
            reply_markup=status_keyboard(application_id),
        )


@router.message(F.text == "📂 Мои заявки")
async def my_applications(message: Message, db) -> None:
    rows = await db.fetchall(
        "SELECT * FROM applications WHERE telegram_user_id = ? ORDER BY id DESC LIMIT 10",
        (message.from_user.id,),
    )

    if not rows:
        await message.answer("У вас пока нет заявок.")
        return

    lines = ["Ваши последние заявки:"]

    for row in rows:
        lines.append(
            f"• #{row['id']} — {row['product']} — "
            f"{STATUSES.get(row['status'], row['status'])}"
        )

    await message.answer("\n".join(lines))
