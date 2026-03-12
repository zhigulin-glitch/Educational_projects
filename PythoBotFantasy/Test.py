import os
import telebot
import random
from telebot import types

from BOT.Предметы.db import get_item_by_id, get_items_by_type

from BOT.Игрок.inventory import (
    create_inventory_tables,
    get_inventory,
    get_temp_inventory,
    get_equipped_item,
    move_temp_to_main_inventory,
    add_item_to_inventory,
    add_item_to_temp_inventory,
    equip_item,
    unequip_slot,
    remove_item_from_inventory,
    remove_item_from_temp_inventory
)
from BOT.Игрок.user_stats import (
    create_tables as create_players_tables,
    add_player,
    set_race_for_player,
    get_player_by_tg_id,
    update_player,
    get_random_opponent,
    RACES,
    connect
)
# Глобальное состояние для арены:
# для каждого игрока храним множество уже показанных противников
ARENA_SEEN_OPPONENTS: dict[int, set[int]] = {}
ARENA_LAST = {}  # {tg_id: opponent_tg_id}
# Активные бои: для каждого игрока хранится состояние боя
BATTLES: dict[int, dict] = {}
# Состояние боёв на арене: {tg_id: {"current_opponent": tg_id_противника}}
arena_state: dict[int, dict] = {}


BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

def give_temp_random_common_weapon(tg_id: int, chat_id: int):
    """
    Выдаёт игроку рандомное Обычное оружие (rarity='common')
    из таблицы items и кладёт в основной инвентарь.
    """
    # Берём все оружия из БД предметов
    weapons = get_items_by_type("weapon")  # список строк из таблицы items

    # Оставляем только обычные
    common_weapons = [w for w in weapons if w[3] == "common"]
    # w[3] — это rarity, т.к. структура примерно:
    # (id, name, type, rarity, price, ...)

    if not common_weapons:
        bot.send_message(chat_id, "⚠ В базе нет обычного оружия (rarity='common').")
        return

    # Случайно выбираем одно
    item_row = random.choice(common_weapons)
    item_id = item_row[0]
    item_name = item_row[1]

    # Кладём в инвентарь
    add_item_to_temp_inventory(tg_id, item_id, 1)

    # Сообщаем игроку
    bot.send_message(chat_id, f"🎁 Ты получил оружие: *{item_name}* (обычное).", parse_mode="Markdown")

def give_random_common_weapon(tg_id: int, chat_id: int):
    """
    Выдаёт игроку рандомное Обычное оружие (rarity='common')
    из таблицы items и кладёт в основной инвентарь.
    """
    # Берём все оружия из БД предметов
    weapons = get_items_by_type("weapon")  # список строк из таблицы items

    # Оставляем только обычные
    common_weapons = [w for w in weapons if w[3] == "common"]
    # w[3] — это rarity, т.к. структура примерно:
    # (id, name, type, rarity, price, ...)

    if not common_weapons:
        bot.send_message(chat_id, "⚠ В базе нет обычного оружия (rarity='common').")
        return

    # Случайно выбираем одно
    item_row = random.choice(common_weapons)
    item_id = item_row[0]
    item_name = item_row[1]

    # Кладём в инвентарь
    add_item_to_inventory(tg_id, item_id, 1)

    # Сообщаем игроку
    bot.send_message(chat_id, f"🎁 Ты получил оружие: *{item_name}* (обычное).", parse_mode="Markdown")

def give_random_common_armor(tg_id: int, chat_id: int):
    """
    Выдаёт игроку рандомную Обычную броню (rarity='common')
    из таблицы items и кладёт в основной инвентарь.
    """
    # Берём всю броню из БД предметов
    armors = get_items_by_type("armor")  # список строк из таблицы items

    # Оставляем только обычную броню
    common_armors = [a for a in armors if a[3] == "common"]
    # a[3] — это rarity
    # структура: (id, name, type, rarity, price, ...)

    if not common_armors:
        bot.send_message(chat_id, "⚠ В базе нет обычной брони (rarity='common').")
        return

    # Случайно выбираем одну броню
    item_row = random.choice(common_armors)
    item_id = item_row[0]
    item_name = item_row[1]

    # Кладём в инвентарь
    add_item_to_inventory(tg_id, item_id, 1)

    # Сообщаем игроку
    bot.send_message(
        chat_id,
        f"🛡 Ты получил броню: *{item_name}* (обычная).",
        parse_mode="Markdown"
    )

def give_cookies(tg_id: int, chat_id: int, amount: int = 1):
    """
    Выдаёт игроку печеньки (увеличивает значение cookies в таблице players).
    amount — сколько печенек добавить.
    """
    if amount <= 0:
        bot.send_message(chat_id, "Количество печенек должно быть больше нуля.")
        return

    player = get_player_by_tg_id(tg_id)
    if player is None:
        bot.send_message(chat_id, "Ты ещё не создан в системе. Попробуй /start.")
        return

    (
        player_id, p_tg_id, username, race,
        level, exp, exp_to_next,
        hp, max_hp,
        energy, max_energy,
        base_strength, base_intelligence,
        base_armor, base_magic_resist,
        armor, magic_resist,
        free_points,
        cookies,
        rating,
        coins
    ) = player

    new_cookies = (cookies or 0) + amount

    # Обновляем только поле cookies
    update_player(tg_id, cookies=new_cookies)

    if amount == 1:
        got_text = "Ты получил 🍪 1 печеньку."
    else:
        got_text = f"Ты получил 🍪 x{amount}."

    bot.send_message(
        chat_id,
        f"{got_text}\nТеперь у тебя всего: 🍪 {new_cookies}."
    )

# -------------------- Меню хижины: INLINE под изображением -----------------------------


def get_hut_menu_inline():
    """
    Inline-меню хижины: кнопки под сообщением/изображением.
    """
    markup = types.InlineKeyboardMarkup()

    btn_stats = types.InlineKeyboardButton("📊 Статы", callback_data="hut_stats")
    btn_inventory = types.InlineKeyboardButton("🎒 Инвентарь", callback_data="hut_inventory")
    button_city = types.InlineKeyboardButton('Отправиться в город', callback_data="hut_city")
    button_book = types.InlineKeyboardButton('Книга историй', callback_data="hut_book")
    btn_exit = types.InlineKeyboardButton("Путешествия", callback_data="hut_exit")


    markup.row(btn_stats, btn_inventory)
    markup.row(button_city)
    markup.row(button_book)
    markup.row(btn_exit)

    return markup


def send_hut_view(chat_id: int):
    """
    Отправляет сообщение с изображением хижины, текстом
    и INLINE-меню под изображением.
    """
    # ВАЖНО: поменяй "hut.jpg" на свой путь к картинке хижины.
    with open("BOT/Хижина.jpg", "rb") as photo:
        bot.send_photo(
            chat_id,
            photo,
            caption=(
                "Ты находишься в своей хижине.\n"
                "Здесь ты можешь перевести дух, проверить свои статы, "
                "заглянуть в инвентарь или выйти наружу навстречу приключениям."
            ),
            reply_markup=get_hut_menu_inline()
        )


# ------------ Хижина: обработчики inline-кнопок под изображением -----------------


@bot.callback_query_handler(func=lambda c: c.data == "hut_stats")
def hut_stats_cb(call: types.CallbackQuery):
    # Переиспользуем handle_stats
    msg = call.message
    msg.from_user = call.from_user
    handle_stats(msg)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "hut_inventory")
def hut_inventory_cb(call: types.CallbackQuery):
    msg = call.message
    msg.from_user = call.from_user
    handle_inventory(msg)
    bot.answer_callback_query(call.id)

# ===== КНИГА ИСТОРИЙ =====

@bot.callback_query_handler(func=lambda c: c.data == "hut_book")
def hut_book_cb(call: types.CallbackQuery):
    """
    Книга историй — пока в разработке.
    Под сообщением одна кнопка 'Вернуться', которая просто удаляет это сообщение.
    """
    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("⬅ Вернуться", callback_data="book_back")
    markup.add(btn_back)

    bot.send_message(
        call.message.chat.id,
        "📖 Книга историй пока в разработке...\n"
        "Скоро здесь появятся легенды, мифы и истории этого мира.",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data == "book_back")
def book_back_cb(call: types.CallbackQuery):
    """
    Закрыть сообщение книги (удалить).
    """
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)


# Универсальная функция выхода из хижины (по chat_id)


def exit_hut(chat_id: int):
    bot.send_message(
        chat_id,
        "Ты выходишь из хижины. Холодный воздух обдаёт лицо, а вокруг открывается незнакомый мир..."
    )

    bot.send_message(
        chat_id,
        "Куда направишься?",
        reply_markup=get_location_choice_menu()
    )


@bot.callback_query_handler(func=lambda c: c.data == "hut_exit")
def hut_exit_cb(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    exit_hut(call.message.chat.id)


# -------------------- Статы и инвентарь -----------------------------
def render_inventory(tg_id: int, chat_id: int, message_id: int | None = None, edit: bool = False):
    rows = get_inventory(tg_id)

    # 🔹 соберём id надетых предметов
    equipped_ids = set()
    for slot_code in ("weapon", "armor", "book", "artifact"):
        eq_id = get_equipped_item(tg_id, slot_code)
        if eq_id is not None:
            equipped_ids.add(eq_id)

    if not rows:
        text = "📦 Твой *основной* инвентарь пуст.\nИспользуй 🍪"
        markup = types.InlineKeyboardMarkup()
        btn_close = types.InlineKeyboardButton("❌ Закрыть", callback_data="close_inventory")
        markup.add(btn_close)

        if edit and message_id:
            bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
        return

    lines = ["📦 *Твой основной инвентарь:*", ""]
    markup = types.InlineKeyboardMarkup()

    for inv_id, p_tg_id, item_id, qty in rows:
        item = get_item_by_id(item_id)
        if item is None:
            continue

        i_id, name, type_, rarity, price, *rest = item

        type_text = {
            "weapon": "оружие",
            "armor": "броня",
            "book": "книга",
            "potion": "зелье",
            "artifact": "артефакт"
        }.get(type_, type_)

        equipped_mark = " ✅ " if item_id in equipped_ids else ""

        lines.append(f"- {name} x{qty} ({type_text}) {equipped_mark}")

        # 🔹 кнопка "Надеть" — только если этот тип экипируемый И сейчас не надет
        if type_ in ("weapon", "armor", "book", "artifact") and item_id not in equipped_ids:
            btn_wear = types.InlineKeyboardButton(
                f"👕 Надеть: {name}",
                callback_data=f"inv_wear_{item_id}"
            )


        # 🔹 "Выкинуть" можно всегда (если хочешь — тоже можно запретить для надетых)
        if item_id not in equipped_ids:
            btn_drop = types.InlineKeyboardButton(
                f"🗑 Выкинуть: {name}",
                callback_data=f"inv_drop_{item_id}"
            )
            markup.row(btn_wear, btn_drop)

    # кнопка Экипировка
    btn_equipment = types.InlineKeyboardButton("🛡 Экипировка", callback_data="show_equipment")
    markup.row(btn_equipment)

    # кнопка Закрыть
    btn_close = types.InlineKeyboardButton("❌ Закрыть", callback_data="close_inventory")
    markup.row(btn_close)

    text = "\n".join(lines)

    if edit and message_id:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
# Рендер выбора предметов для локации
def render_location_pick_inventory(
    tg_id: int,
    chat_id: int,
    message_id: int | None = None,
    edit: bool = False
):
    """
    Показывает основной инвентарь с возможностью выбрать,
    что взять с собой в локацию.

    При выборе предмет:
      - удаляется из inventory (remove_item_from_inventory)
      - добавляется в temp_inventory (add_item_to_temp_inventory)
    """
    rows = get_inventory(tg_id)

    markup = types.InlineKeyboardMarkup()

    if not rows:
        text = (
            "📦 В твоём *основном* инвентаре ничего нет.\n"
            "Тебе нечего взять с собой в путь."
        )
        btn_done = types.InlineKeyboardButton("✅ Готово", callback_data="forest_enter_done")
        markup.add(btn_done)

        if edit and message_id:
            bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
        return

    lines = [
        "🌲 Ты стоишь у входа в локацию.",
        "Выбери, что взять с собой из хижины:",
        "",
        "📦 *Твой основной инвентарь:*",
        ""
    ]

    for inv_id, p_tg_id, item_id, qty in rows:
        item = get_item_by_id(item_id)
        if item is None:
            continue

        i_id, name, type_, rarity, price, *rest = item

        type_text = {
            "weapon": "оружие",
            "armor": "броня",
            "book": "книга",
            "potion": "зелье",
            "artifact": "артефакт"
        }.get(type_, type_)

        lines.append(f"- {name} x{qty} ({type_text})")

        # Кнопка "Взять 1 шт." — можно нажимать несколько раз
        if qty > 0:
            btn_take = types.InlineKeyboardButton(
                f"🎒 Взять: {name}",
                callback_data=f"loc_take_{item_id}"
            )
            markup.add(btn_take)

    # Кнопка "Готово"
    btn_done = types.InlineKeyboardButton("✅ Готово, войти в локацию", callback_data="forest_enter_done")
    markup.add(btn_done)

    text = "\n".join(lines)

    if edit and message_id:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
# Callback: взять предмет с собой (из основного → в текущий)
@bot.callback_query_handler(func=lambda c: c.data.startswith("loc_take_"))
def location_take_item_cb(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    try:
        item_id = int(call.data.split("loc_take_", 1)[1])
    except (ValueError, IndexError):
        bot.answer_callback_query(call.id, "Ошибка предмета.")
        return

    item = get_item_by_id(item_id)
    if item is None:
        bot.answer_callback_query(call.id, "Такого предмета нет.")
        return

    name = item[1]

    # 1) Пытаемся убрать 1 шт. из основного инвентаря
    ok = remove_item_from_inventory(tg_id, item_id, quantity=1)
    if not ok:
        bot.answer_callback_query(call.id, "В основном инвентаре не осталось этого предмета.")
        # Всё равно перерисуем, чтобы обновился список
        render_location_pick_inventory(
            tg_id,
            chat_id,
            message_id=call.message.message_id,
            edit=True
        )
        return

    # 2) Кладём 1 шт. в текущий (temp_inventory)
    add_item_to_temp_inventory(tg_id, item_id, 1)

    bot.answer_callback_query(call.id, f"Ты берёшь с собой: {name}")

    # 3) Перерисовываем сообщение выбора с обновлённым количеством
    render_location_pick_inventory(
        tg_id,
        chat_id,
        message_id=call.message.message_id,
        edit=True
    )

# Callback: «Готово, войти в локацию»
@bot.callback_query_handler(func=lambda c: c.data == "forest_enter_done")
def forest_enter_done_cb(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id)

    # Удаляем сообщение с выбором предметов
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception:
        pass

    # Теперь игрок считается «в локации» — показываем описание и меню
    bot.send_message(
        chat_id,
        "🌲 Ты входишь в Древний лес. Деревья здесь высоки и молчаливы, а тени между ними шевелятся...",
        reply_markup=get_location_actions_menu()
    )


@bot.message_handler(func=lambda m: m.text == "📊 Статы")
def handle_stats(message: types.Message):
    """
    Кнопка 'Статы' — показываем текущие характеристики игрока.
    Используется и из reply-клавиатуры, и из inline-меню.
    """
    tg_id = message.from_user.id
    chat_id = message.chat.id

    player = get_player_by_tg_id(tg_id)
    if player is None:
        bot.send_message(chat_id, "Ты ещё не создан в системе. Попробуй /start.")
        return

    (
        player_id, p_tg_id, username, race,
        level, exp, exp_to_next,
        hp, max_hp,
        energy, max_energy,
        base_strength, base_intelligence,
        base_armor, base_magic_resist,
        armor, magic_resist,
        free_points,
        cookies,
        rating,
        coins
    ) = player

    if race == 'human':
        race_stats = 'Человек'
    elif race == 'orc':
        race_stats = 'Орк'
    elif race == 'animal':
        race_stats = 'Животное'
    elif race == 'raven_man':
        race_stats = 'Равен'
    else:
        race_stats = 'Неизвестно'

    text = f"""Твои статы:

🧬 Раса: {race_stats}
🪙 Монеты: {coins}

🔢 Уровень: {level}
🎯 Опыт: {exp} / {exp_to_next}
✨ Свободных очков: {free_points}

❤️ Здоровье: {max_hp}
💪 Сила: {base_strength}
📚 Интеллект: {base_intelligence}

🛡 Броня: {base_armor}
✨ Маг. сопротивление: {base_magic_resist}

⚡ Энергия: {max_energy}

"""
    markup = types.InlineKeyboardMarkup()
    button_close = types.InlineKeyboardButton('❌ Закрыть', callback_data='close_stats')
    markup.add(button_close)

    bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "close_stats")
def close_stats(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)


@bot.message_handler(func=lambda m: m.text == "🎒 Инвентарь")
def handle_inventory(message: types.Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id
    render_inventory(tg_id, chat_id)

@bot.callback_query_handler(func=lambda c: c.data == "show_equipment")
def show_equipment(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id)

    slots = {
        "weapon": "⚔️ Оружие",
        "armor": "🛡 Броня",
        "book": "📘 Книга",
        "artifact": "🔮 Артефакт"
    }

    lines = ["*🛡 Твоя основная экипировка:*", ""]
    markup = types.InlineKeyboardMarkup()

    for slot_key, slot_name in slots.items():
        item_id = get_equipped_item(tg_id, slot_key)

        if item_id is None:
            lines.append(f"{slot_name}: — пусто —")
            continue

        item = get_item_by_id(item_id)
        if item is None:
            lines.append(f"{slot_name}: — ошибка предмета —")
            continue

        (
            i_id,
            name,
            type_,
            rarity,
            price,
            damage_min,
            damage_max,
            phys_armor_min,
            phys_armor_max,
            magic_def_min,
            magic_def_max,
            heal_min,
            heal_max,
            heal_percent,
            bonus_hp,
            bonus_energy,
            bonus_strength,
            bonus_intellect,
            bonus_phys_armor,
            bonus_magic_resist,
        ) = item

        # 🔹 собираем статы
        stats = []

        if damage_min or damage_max:
            stats.append(f"Урон: {damage_min}-{damage_max}")
        if phys_armor_min or phys_armor_max:
            stats.append(f"Физ. броня: {phys_armor_min}-{phys_armor_max}")
        if magic_def_min or magic_def_max:
            stats.append(f"Маг. защита: {magic_def_min}-{magic_def_max}")
        if heal_min or heal_max:
            stats.append(f"Лечение: {heal_min}-{heal_max}")
        if heal_percent:
            stats.append(f"Лечение %: {heal_percent}%")
        if bonus_hp:
            stats.append(f"❤️ +{bonus_hp} HP")
        if bonus_energy:
            stats.append(f"🔋 +{bonus_energy} Энергия")
        if bonus_strength:
            stats.append(f"💪 +{bonus_strength} Сила")
        if bonus_intellect:
            stats.append(f"📚 +{bonus_intellect} Интеллект")
        if bonus_phys_armor:
            stats.append(f"🛡 +{bonus_phys_armor} Броня")
        if bonus_magic_resist:
            stats.append(f"✨ +{bonus_magic_resist} Маг. резист")

        stats_text = "\n    ".join(stats) if stats else "Без бонусов"

        lines.append(
            f"{slot_name}: *{name}*\n"
            f"    ➤ {stats_text}\n"
        )

        # 🔹 Кнопка "Снять" для этого слота
        btn_takeoff = types.InlineKeyboardButton(
            f"❎ Снять: {name}",
            callback_data=f"unequip_{slot_key}"

        )
        markup.add(btn_takeoff)

    # Кнопка Назад
    btn_back = types.InlineKeyboardButton("⬅ Назад", callback_data="back_to_inventory")
    markup.add(btn_back)

    text = "\n".join(lines)

    bot.edit_message_text(
        text,
        chat_id=chat_id,
        message_id=call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("unequip_"))
def unequip_item_handler(call: types.CallbackQuery):
    tg_id = call.from_user.id
    slot = call.data.split("unequip_", 1)[1]  # weapon / armor / book / artifact

    bot.answer_callback_query(call.id)

    unequip_slot(tg_id, slot)

    # Обновляем ту же страницу экипировки
    show_equipment(call)


@bot.callback_query_handler(func=lambda c: c.data.startswith("inv_wear_")) # надеть
def inventory_wear_item(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    try:
        item_id = int(call.data.split("inv_wear_", 1)[1])
    except (ValueError, IndexError):
        bot.answer_callback_query(call.id, "Ошибка предмета.")
        return

    item = get_item_by_id(item_id)
    if item is None:
        bot.answer_callback_query(call.id, "Такого предмета нет.")
        return

    # определить слот по type_
    _, name, type_, *_ = item
    if type_ == "weapon":
        slot = "weapon"
    elif type_ == "armor":
        slot = "armor"
    elif type_ == "book":
        slot = "book"
    elif type_ == "artifact":
        slot = "artifact"
    else:
        bot.answer_callback_query(call.id, "Этот предмет нельзя надеть.")
        return

    ok = equip_item(tg_id, item_id, slot)
    if not ok:
        bot.answer_callback_query(call.id, "У тебя нет этого предмета.")
        return

    bot.answer_callback_query(call.id, f"Ты надел(а): {name}")

    # 🔹 ПЕРЕРИСОВЫВАЕМ ЭТО ЖЕ СООБЩЕНИЕ
    render_inventory(tg_id, chat_id, message_id=call.message.message_id, edit=True)


@bot.callback_query_handler(func=lambda c: c.data.startswith("inv_drop_")) # выкинуть
def inventory_drop_item(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    try:
        item_id = int(call.data.split("inv_drop_", 1)[1])
    except (ValueError, IndexError):
        bot.answer_callback_query(call.id, "Ошибка предмета.")
        return

    item = get_item_by_id(item_id)
    if item is None:
        bot.answer_callback_query(call.id, "Такого предмета нет.")
        return

    name = item[1]

    ok = remove_item_from_inventory(tg_id, item_id, quantity=1)
    if not ok:
        bot.answer_callback_query(call.id, "У тебя нет этого предмета.")
        return

    bot.answer_callback_query(call.id, f"Ты выкинул(а): {name}")

    # 🔹 снова перерисовываем этот же инвентарь
    render_inventory(tg_id, chat_id, message_id=call.message.message_id, edit=True)


@bot.callback_query_handler(func=lambda c: c.data == "back_to_inventory")
def back_to_inventory(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)

    render_inventory(tg_id, chat_id, message_id=call.message.message_id, edit=True)




@bot.callback_query_handler(func=lambda c: c.data == "close_inventory")
def close_inventory(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ================== ГОРОД ==================
def send_city_view(chat_id: int):
    """
    Показывает меню города (как hut_city), но без привязки к callback.
    """
    markup = types.InlineKeyboardMarkup()
    button_tavern = types.InlineKeyboardButton('Таверна: "Ржавый клинок"', callback_data="city_tavern")
    button_arena = types.InlineKeyboardButton('Арена', callback_data="city_arena")
    button_back_hut = types.InlineKeyboardButton('🏠 Вернуться в хижину', callback_data="city_back_hut")

    markup.row(button_tavern)
    markup.row(button_arena)
    markup.row(button_back_hut)

    bot.send_message(
        chat_id,
        '🏙 Ты входишь в город. Вокруг шум, голоса, запахи еды и дыма из труб.\n'
        'Куда направишься?',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data == "hut_city")
def hut_city(call: types.CallbackQuery):
    """
    Переход в город из хижины.
    Появляется сообщение с тремя кнопками: Таверна, Арена, Вернуться в хижину.
    """
    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup()
    button_tavern = types.InlineKeyboardButton('Таверна: "Ржавый клинок"', callback_data="city_tavern")
    button_arena = types.InlineKeyboardButton('Арена', callback_data="city_arena")
    button_back_hut = types.InlineKeyboardButton('🏠 Вернуться в хижину', callback_data="city_back_hut")

    markup.row(button_tavern)
    markup.row(button_arena)
    markup.row(button_back_hut)

    bot.send_message(
        call.message.chat.id,
        '🏙 Ты входишь в город. Вокруг шум, голоса, запахи еды и дыма из труб.\n'
        'Куда направишься?',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data == "city_back_hut")
def city_back_hut(call: types.CallbackQuery):
    """
    Возврат из города в хижину:
    удаляем сообщение с городом и показываем хижину.
    """
    bot.answer_callback_query(call.id)
    # Удаляем сообщение с меню города
    bot.delete_message(call.message.chat.id, call.message.message_id)
    # Показываем хижину
    send_hut_view(call.message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == "city_tavern")
def city_tavern(call: types.CallbackQuery):
    """
    Переход в таверну из города.
    Пока там пусто, но есть кнопка 'Вернуться в город'.
    """
    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup()
    btn_back_city = types.InlineKeyboardButton("⬅ Вернуться в город", callback_data="tavern_back_city")
    markup.add(btn_back_city)

    bot.send_message(
        call.message.chat.id,
        '🍺 Ты заходишь в таверну "Ржавый клинок".\n'
        'Здесь пока ничего не происходит, но вскоре появятся посетители, задания и слухи.',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data == "tavern_back_city")
def tavern_back_city(call: types.CallbackQuery):
    """
    Возврат из таверны в город: удаляем сообщение таверны, снова показываем меню города.
    """
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda c: c.data == "city_arena")
def arena_enter(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)

    chat_id = call.message.chat.id
    tg_id = call.from_user.id

    # Берём игрока из БД
    player = get_player_by_tg_id(tg_id)
    if player is None:
        bot.send_message(chat_id, "Ты ещё не создан в системе. Попробуй /start.")
        return

    (
        player_id, p_tg_id, username, race,
        level, exp, exp_to_next,
        hp, max_hp,
        energy, max_energy,
        base_strength, base_intelligence,
        base_armor, base_magic_resist,
        armor, magic_resist,
        free_points,
        cookies,
        rating,
        coins
    ) = player

    if race == 'human':
        race_stats = 'Человек'
    elif race == 'orc':
        race_stats = 'Орк'
    elif race == 'animal':
        race_stats = 'Животное'
    elif race == 'raven_man':
        race_stats = 'Равен'
    else:
        race_stats = 'Неизвестно'

    text = f"""🏟 Ты заходишь на арену.

Вокруг — шум зрителей, звон металла и запах пыли, поднятой десятками боёв.

Твои текущие параметры для боя:

___ 🏆 Рейтинг:{rating} ___

🧬 Раса: {race_stats}
🔢 Уровень: {level}
🎯 Опыт: {exp} / {exp_to_next}

❤️ Здоровье: {max_hp}
💪 Сила: {base_strength}
📚 Интеллект: {base_intelligence}

🛡 Броня: {base_armor}
✨ Маг. сопротивление: {base_magic_resist}
"""

    # Кнопки под сообщением арены
    markup = types.InlineKeyboardMarkup()
    btn_search = types.InlineKeyboardButton("🔍 Поиск противника", callback_data="arena_search")
    btn_back = types.InlineKeyboardButton("↩️ Вернуться в город", callback_data="arena_back_city")
    btn_inventory = types.InlineKeyboardButton("🎒 Инвентарь", callback_data="hut_inventory")

    markup.row(btn_inventory)
    markup.row(btn_search)
    markup.row(btn_back)

    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "arena_back_city")
def arena_back_to_city(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)

    chat_id = call.message.chat.id
    tg_id = call.from_user.id

    # очищаем арену/бой
    ARENA_SEEN_OPPONENTS.pop(tg_id, None)
    ARENA_LAST.pop(tg_id, None)
    BATTLES.pop(tg_id, None)   # 🔥 важно: закрыть бой, если был

    # удаляем текущее сообщение (меню арены/бой/послебой)
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception:
        pass

    # ✅ показываем город
    send_city_view(chat_id)




# ------------------ Меню, когда игрок вне хижины и выбирает локацию ------------------------


def get_location_choice_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_loc1 = types.KeyboardButton("Локация в разработке")
    btn_loc2 = types.KeyboardButton("Локация в разработке")
    btn_forest = types.KeyboardButton("Древний лес")
    btn_back_hut = types.KeyboardButton("🏠 Вернуться в хижину")

    kb.row(btn_loc1, btn_loc2, btn_forest)
    kb.row(btn_back_hut)

    return kb


@bot.message_handler(func=lambda m: m.text == "Локация в разработке")
def handle_location_wip(message: types.Message):
    chat_id = message.chat.id
    bot.send_message(
        chat_id,
        "🏗 Эта локация ещё в разработке. Скоро здесь появится что-то интересное!"
    )


@bot.message_handler(func=lambda m: m.text == "Древний лес")
def handle_forest(message: types.Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id

    # Показываем выбор, что взять с собой
    render_location_pick_inventory(tg_id, chat_id)



@bot.message_handler(func=lambda m: m.text == "🏠 Вернуться в хижину")
def handle_back_to_hut_message(message: types.Message):
    """
    Возврат в хижину из локации:
    - весь лут из temp_inventory переносим в основной инвентарь,
    - убираем reply-клавиатуру,
    - показываем хижину.
    """
    tg_id = message.from_user.id
    chat_id = message.chat.id

    # 🔥 Забираем весь лут с собой: temp_inventory -> inventory
    move_temp_to_main_inventory(tg_id)

    bot.send_message(
        chat_id,
        "Ты возвращаешься в знакомую хижину. Здесь безопаснее, чем снаружи... вроде бы.",
        reply_markup=types.ReplyKeyboardRemove()
    )

    send_hut_view(chat_id)


# ---------------------- Меню, когда игрок уже в локации ------------------------

def temp_inventory(tg_id: int, chat_id: int, message_id: int | None = None, edit: bool = False):
    rows = get_temp_inventory(tg_id)

    # 🔹 соберём id надетых предметов
    equipped_ids = set()
    for slot_code in ("weapon", "armor", "book", "artifact"):
        eq_id = get_equipped_item(tg_id, slot_code, use_temp=True)
        if eq_id is not None:
            equipped_ids.add(eq_id)

    if not rows:
        text = "📦 Твой инвентарь пуст.\nИспользуй 🍪"
        markup = types.InlineKeyboardMarkup()
        btn_close = types.InlineKeyboardButton("❌ Закрыть", callback_data="close_inventory_2")
        markup.add(btn_close)

        if edit and message_id:
            bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
        return

    lines = ["📦 *Твой инвентарь:*", ""]
    markup = types.InlineKeyboardMarkup()

    for inv_id, p_tg_id, item_id, qty in rows:
        item = get_item_by_id(item_id)
        if item is None:
            continue

        i_id, name, type_, rarity, price, *rest = item

        type_text = {
            "weapon": "оружие",
            "armor": "броня",
            "book": "книга",
            "potion": "зелье",
            "artifact": "артефакт"
        }.get(type_, type_)

        equipped_mark = " ✅ " if item_id in equipped_ids else ""

        lines.append(f"- {name} x{qty} ({type_text}) {equipped_mark}")

        # 🔹 кнопка "Надеть" — только если этот тип экипируемый И сейчас не надет
        if type_ in ("weapon", "armor", "book", "artifact") and item_id not in equipped_ids:
            btn_wear = types.InlineKeyboardButton(
                f"👕 Надеть: {name}",
                callback_data=f"temp_wear_{item_id}"
            )


        # 🔹 "Выкинуть" можно всегда (если хочешь — тоже можно запретить для надетых)
        if item_id not in equipped_ids:
            btn_drop = types.InlineKeyboardButton(
                f"🗑 Выкинуть: {name}",
                callback_data=f"temp_drop_{item_id}"
            )
            markup.row(btn_wear, btn_drop)

    # кнопка Экипировка
    btn_equipment = types.InlineKeyboardButton("🛡 Экипировка", callback_data="temp_show_equipment")
    markup.row(btn_equipment)

    # кнопка Закрыть
    btn_close = types.InlineKeyboardButton("❌ Закрыть", callback_data="close_inventory")
    markup.row(btn_close)

    text = "\n".join(lines)

    if edit and message_id:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def get_location_actions_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    btn_stats = types.KeyboardButton("📊 Текущие статы")
    btn_inventory = types.KeyboardButton("🎒 Текущий инвентарь")
    btn_cookie = types.KeyboardButton("🍪 Съесть печеньку")
    btn_back_hut = types.KeyboardButton("🏠 Вернуться в хижину")

    kb.row(btn_stats, btn_inventory)
    kb.row(btn_cookie, btn_back_hut)

    return kb


@bot.message_handler(func=lambda m: m.text == "📊 Текущие статы")
def handle_current_stats(message: types.Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id

    player = get_player_by_tg_id(tg_id)
    if player is None:
        bot.send_message(chat_id, "Ты ещё не создан в системе. Попробуй /start.")
        return

    (
        player_id, p_tg_id, username, race,
        level, exp, exp_to_next,
        hp, max_hp,
        energy, max_energy,
        base_strength, base_intelligence,
        base_armor, base_magic_resist,
        armor, magic_resist,
        free_points,
        cookies,
        rating,
        coins
    ) = player

    if race == 'human':
        race_stats = 'Человек'
    elif race == 'orc':
        race_stats = 'Орк'
    elif race == 'animal':
        race_stats = 'Животное'
    elif race == 'raven_man':
        race_stats = 'Равен'
    else:
        race_stats = 'Неизвестно'

    text = f"""Твои текущие статы:

🧬 Раса: {race_stats}

🔢 Уровень: {level}
🎯 Опыт: {exp} / {exp_to_next}
✨ Свободных очков: {free_points}

❤️ Здоровье: {hp} / {max_hp}
💪 Сила: {base_strength}
📚 Интеллект: {base_intelligence}

🛡 Броня: {base_armor}
✨ Маг. сопротивление: {base_magic_resist}

⚡ Энергия: {energy} / {max_energy}

🍪 Печенек: {cookies}    🪙 Монеты: {coins}
"""
    markup = types.InlineKeyboardMarkup()
    button_close = types.InlineKeyboardButton('❌ Закрыть', callback_data='close_stats_2')
    markup.add(button_close)

    bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "close_stats_2")
def close_stats_2(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)


@bot.message_handler(func=lambda m: m.text == "🎒 Текущий инвентарь")
def handle_temp_inventory(message: types.Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id
    temp_inventory(tg_id, chat_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("temp_wear_"))
def temp_inventory_wear_item(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    try:
        item_id = int(call.data.split("temp_wear_", 1)[1])
    except (ValueError, IndexError):
        bot.answer_callback_query(call.id, "Ошибка предмета.")
        return

    item = get_item_by_id(item_id)
    if item is None:
        bot.answer_callback_query(call.id, "Такого предмета нет.")
        return

    _, name, type_, *_ = item

    if type_ == "weapon":
        slot = "weapon"
    elif type_ == "armor":
        slot = "armor"
    elif type_ == "book":
        slot = "book"
    elif type_ == "artifact":
        slot = "artifact"
    else:
        bot.answer_callback_query(call.id, "Этот предмет нельзя надеть.")
        return

    # 🔹 ВАЖНО: экипируем в ТЕКУЩУЮ экипировку
    ok = equip_item(tg_id, item_id, slot, use_temp=True)
    if not ok:
        bot.answer_callback_query(call.id, "У тебя нет этого предмета.")
        return

    bot.answer_callback_query(call.id, f"Ты надел(а): {name}")

    # Перерисовываем ТЕКУЩИЙ инвентарь
    temp_inventory(tg_id, chat_id, message_id=call.message.message_id, edit=True)


@bot.callback_query_handler(func=lambda c: c.data == "temp_show_equipment")
def temp_show_equipment(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id)

    slots = {
        "weapon": "⚔️ Оружие",
        "armor": "🛡 Броня",
        "book": "📘 Книга",
        "artifact": "🔮 Артефакт"
    }

    lines = ["*🛡 Твоя текущая экипировка:*", ""]
    markup = types.InlineKeyboardMarkup()

    for slot_key, slot_name in slots.items():
        item_id = get_equipped_item(tg_id, slot_key, use_temp=True)

        if item_id is None:
            lines.append(f"{slot_name}: — пусто —")
            continue

        item = get_item_by_id(item_id)
        if item is None:
            lines.append(f"{slot_name}: — ошибка предмета —")
            continue

        (
            i_id,
            name,
            type_,
            rarity,
            price,
            damage_min,
            damage_max,
            phys_armor_min,
            phys_armor_max,
            magic_def_min,
            magic_def_max,
            heal_min,
            heal_max,
            heal_percent,
            bonus_hp,
            bonus_energy,
            bonus_strength,
            bonus_intellect,
            bonus_phys_armor,
            bonus_magic_resist,
        ) = item

        # 🔹 собираем статы
        stats = []

        if damage_min or damage_max:
            stats.append(f"Урон: {damage_min}-{damage_max}")
        if phys_armor_min or phys_armor_max:
            stats.append(f"Физ. броня: {phys_armor_min}-{phys_armor_max}")
        if magic_def_min or magic_def_max:
            stats.append(f"Маг. защита: {magic_def_min}-{magic_def_max}")
        if heal_min or heal_max:
            stats.append(f"Лечение: {heal_min}-{heal_max}")
        if heal_percent:
            stats.append(f"Лечение %: {heal_percent}%")
        if bonus_hp:
            stats.append(f"❤️ +{bonus_hp} HP")
        if bonus_energy:
            stats.append(f"🔋 +{bonus_energy} Энергия")
        if bonus_strength:
            stats.append(f"💪 +{bonus_strength} Сила")
        if bonus_intellect:
            stats.append(f"📚 +{bonus_intellect} Интеллект")
        if bonus_phys_armor:
            stats.append(f"🛡 +{bonus_phys_armor} Броня")
        if bonus_magic_resist:
            stats.append(f"✨ +{bonus_magic_resist} Маг. резист")

        stats_text = "\n    ".join(stats) if stats else "Без бонусов"

        lines.append(
            f"{slot_name}: *{name}*\n"
            f"    ➤ {stats_text}\n"
        )

        # 🔹 Кнопка "Снять" для этого слота
        btn_takeoff = types.InlineKeyboardButton(
            f"❎ Снять: {name}",
            callback_data=f"temp_unequip_{slot_key}"

        )
        markup.add(btn_takeoff)

    # Кнопка Назад
    btn_back = types.InlineKeyboardButton("⬅ Назад", callback_data="back_to_inventory_temp")
    markup.add(btn_back)

    text = "\n".join(lines)

    bot.edit_message_text(
        text,
        chat_id=chat_id,
        message_id=call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("temp_unequip_"))
def temp_unequip_item_handler(call: types.CallbackQuery):
    tg_id = call.from_user.id

    # "temp_unequip_weapon" -> ["temp_", "weapon"]
    slot = call.data.split("temp_unequip_", 1)[1]

    bot.answer_callback_query(call.id)

    unequip_slot(tg_id, slot, use_temp=True)

    # Обновляем текущую экипировку
    temp_show_equipment(call)


@bot.callback_query_handler(func=lambda c: c.data.startswith("temp_drop_")) # выкинуть
def inventory_temp_drop_item(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    try:
        item_id = int(call.data.split("temp_drop_", 1)[1])
    except (ValueError, IndexError):
        bot.answer_callback_query(call.id, "Ошибка предмета.")
        return

    item = get_item_by_id(item_id)
    if item is None:
        bot.answer_callback_query(call.id, "Такого предмета нет.")
        return

    name = item[1]

    ok = remove_item_from_temp_inventory(tg_id, item_id, quantity=1)
    if not ok:
        bot.answer_callback_query(call.id, "У тебя нет этого предмета.")
        return

    bot.answer_callback_query(call.id, f"Ты выкинул(а): {name}")

    # 🔹 снова перерисовываем этот же инвентарь
    temp_inventory(tg_id, chat_id, message_id=call.message.message_id, edit=True)

@bot.callback_query_handler(func=lambda c: c.data == "back_to_inventory_temp")
def back_to_inventory(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)

    temp_inventory(tg_id, chat_id, message_id=call.message.message_id, edit=True)

@bot.callback_query_handler(func=lambda c: c.data == "close_inventory_2")
def close_inventory_2(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "🍪 Съесть печеньку")
def handle_eat_cookie(message: types.Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id

    markup = types.InlineKeyboardMarkup()
    btn_close = types.InlineKeyboardButton("❌ Закрыть", callback_data="close_cookies")
    markup.add(btn_close)

    player = get_player_by_tg_id(tg_id)
    if player is None:
        bot.send_message(chat_id, "Ты ещё не создан в системе. Попробуй /start.")
        return

    (
        player_id, p_tg_id, username, race,
        level, exp, exp_to_next,
        hp, max_hp,
        energy, max_energy,
        base_strength, base_intelligence,
        base_armor, base_magic_resist,
        armor, magic_resist,
        free_points,
        cookies,
        rating,
        coins
    ) = player

    if cookies <= 0:
        bot.send_message(chat_id, "🍪 У тебя нет печенек, чтобы забрать лут из этой локации.", parse_mode="Markdown", reply_markup=markup)
        return

    # Переносим лут
    move_temp_to_main_inventory(tg_id)

    # Отнимаем 1 печеньку
    update_player(tg_id, cookies=cookies - 1)

    bot.send_message(
        chat_id,
        "🍪 Ты съел печеньку.\n"
        "✨ Всё, что ты нашёл в этой локации, было аккуратно перенесено в твой основной инвентарь в хижине!", parse_mode="Markdown", reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data == "close_cookies")
def close_cookies(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)

# --------------------------------- Хэндлер команды /start ---------------------------
@bot.message_handler(commands = ['start']) # Если пользователь вводит /start — вызываем функцию handle_start
def handle_start(message):

    tg_id = message.from_user.id
    username = message.from_user.username
    add_player(tg_id, username)

    markup = types.InlineKeyboardMarkup()                                                   # Создаём объект inline-клавиатуры
    button_start = types.InlineKeyboardButton('Вперёд', callback_data="enter_one")     # Создаём кнопку # Текст кнопки # callback_data — то, что бот получает при нажатии
    markup.add(button_start)                                                                # Добавляем кнопку на клавиатуру

    bot.send_message(message.chat.id,                                                         # Кому отправляем — ID чата пользователя
'''Сейчас ты погрузишься в уникальный фэнтэзи мир, полный тайн и загадок, рыцарей и магов, чудовищ и героев.
Исследуй территории, выполняй квесты, сражайся с монстрами, экипируй себя разным орудием и доспехами!
———
Механика самой игры очень проста, подробности можно уточнить далее в главном меню. 
———
Если ты готов, нажимай на кнопку и она перенесёт тебя в нашу вселенную.
''', reply_markup=markup)                                                                       # Прикрепляем клавиатуру с кнопкой
# ---------- Хэндлер нажатия на кнопку "Вперёд" ----------
@bot.callback_query_handler(func=lambda c: c.data == 'enter_one')
# Эта строка говорит: вызывать функцию enter1 только если callback_data == 'enter_one'
def enter1(call: types.CallbackQuery):

    markup = types.InlineKeyboardMarkup()
    button_start2 = types.InlineKeyboardButton('Наблюдать', callback_data="enter_two")
    markup.add(button_start2)

    bot.answer_callback_query(call.id,  text="Отлично!")                                                 # ID действия нажатия # Всплывающее уведомление (toast)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)      # Чат # Сообщение, у которого убираем клавиатуру # Удаляем старую клавиатуру
    # Отправляем новое сообщение
    bot.send_message(call.message.chat.id,
'''~Ты выходишь из портала и видишь перед собой старого волшебника~

🧙🏻‍♂️ - о, вовремя я! Приветствую тебя… Меня зовут {Придумать имя}, я встречаю и направляю таких же новичков как и ты.
Прости, больше о себе ничего не расскажу! Нам пора идти…

~ маг достаёт какую то склянку и бросает её на землю. Из неё начинает обильно выделяться голубоватый дымок~''' , reply_markup=markup) # Прикрепляем новую кнопку

    #Timer(5,send_second_message, args=[call.message.chat.id]).start()
@bot.callback_query_handler(func=lambda c: c.data == 'enter_two')
def send_second_message(call: types.CallbackQuery):

    markup = types.InlineKeyboardMarkup()
    button_start3 = types.InlineKeyboardButton('Не сопротивляться', callback_data="enter_three")
    markup.add(button_start3)

    bot.answer_callback_query(call.id, text ='Вау...')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(call.message.chat.id,
    ''' ~дым рассеялся, а на месте склянки возник небольшой портал~ 

🧙🏻‍♂️ - прыгай, у нас мало времени! 

~ маг берёт вас за шкирку и толкает в портал…~''', reply_markup=markup)

    #Timer(5, send_second_message2, args=[chat_id]).start()

@bot.callback_query_handler(func=lambda c: c.data == 'enter_three')
def send_second_message2(call: types.CallbackQuery):

    markup = types.InlineKeyboardMarkup()
    button_start4 = types.InlineKeyboardButton('Слушать дальше', callback_data="enter_four")
    markup.add(button_start4)

    bot.answer_callback_query(call.id, text='Чёрт')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(call.message.chat.id,
    '''~ через мгновение вы оказываетесь в  совершенно глухой местности. Яркое солнце слегка пробивается через густые ветви деревьев, пение птиц ласкает уши. Наконец ты вдали от городского шума и вечной суеты ~

🧙🏻‍♂️ - Добро пожаловать, странник! Отсюда ты начнёшь своё путешествие. Отныне это твоё пристанище 

~ маг указывает рукой на хижину, которая стоит неподалёку прямо среди густых деревьев и кустов. Старое одноэтажное деревянное здание с маленькими окошками и слегка покосившейся треугольной крышей. От самой хижины петляет множество тропинок. Куда? Неизвестно. Видимо это тебе и предстоит разузнать. Маг замечает твой вопросительный взгляд и продолжает монолог ~''', reply_markup=markup)

    #Timer(10, send_second_message3, args=[chat_id]).start()

@bot.callback_query_handler(func=lambda c: c.data == 'enter_four')
def send_second_message3(call: types.CallbackQuery):

    markup = types.InlineKeyboardMarkup()
    button_see = types.InlineKeyboardButton('Осмотреться', callback_data="see")
    markup.add(button_see)

    bot.answer_callback_query(call.id, text='Внимательно')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(call.message.chat.id,
    '''🧙🏻‍♂️ - тебя ждёт множество путешествий и загадок, мой дорогой друг! Этому миру нужна твоя помощь. Но помни, ты можешь вернуться сюда в любое время, чтобы перевести дух и восстановить силы. Ты всегда можешь обратиться ко мне, если, конечно, найдёшь. Удачи! 

~ маг моментально испаряется, оставляя на своём месте лишь белый дым. Теперь ты один наедине со своими мыслями и полным непониманием что же делать дальше…~  

💭 - Кто это был? Куда он торопился? Где мне теперь искать ответы на эти вопросы…''', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == 'see')
def handle_see(call: types.CallbackQuery):

    bot.answer_callback_query(call.id, text = 'Глядим...')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    markup = types.InlineKeyboardMarkup()
    button_house = types.InlineKeyboardButton('Войти в хижину', callback_data="house")
    markup.add(button_house)

    bot.send_message(call.message.chat.id,
    '''~ Ты поворачиваешь голову и замечаешь, что из хижины в неизвестном направлении ведёт множество тропинок. А рядом стоит старый деревянный указатель, на котором неаккуратным почерком выцарапаны буквы. Ты подходишь ближе, чтобы наконец узнать, куда тебя могут привести эти неведомые дорожки ~

💭 - После таких загадочных перемещений по всяким порталам идти уже никуда не хочется. Лучше пойти в хижину и передохнуть немного''', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == 'house')
def handle_house(call: types.CallbackQuery):

    bot.answer_callback_query(call.id, text='Открываем дверь...')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    markup = types.InlineKeyboardMarkup()
    button_drop = types.InlineKeyboardButton('Посмотреть что там', callback_data="house_drop")
    markup.add(button_drop)

    bot.send_message(call.message.chat.id,
    '''~ Ты подходишь к хижине и поднимаешься на крыльцо по скрипящим под ногами деревянным ступенькам. Тяжёлая дверь с пронзающим звуком открывается, не успев ты даже до неё дотронуться ~

💭 - Видимо, эта развалюха сама зовёт меня в гости

~ Текст про предмет в углу ~''', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == 'house_drop')
def handle_house_drop(call: types.CallbackQuery):

    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id, text='Осматриваемся...')
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

    # 🎁 ВЫДАЁМ ОРУЖИЕ
    give_random_common_weapon(tg_id, chat_id)

    # Кнопка продолжения
    markup = types.InlineKeyboardMarkup()
    button_letter = types.InlineKeyboardButton(
        'Прочитать записку',
        callback_data="letter"
    )
    markup.add(button_letter)

    # Продолжение истории (ВСЁ КАК БЫЛО)
    bot.send_message(
        chat_id,
        '''~ Переступив порог, ты ощущаешь запах старого дерева. Но не противный, а скорее приятный, добавляющий этому месту ещё больше антуража.

Перед твоим взором предстаёт довольно уютное помещение. На полу расстелен тяжёлый ковёр с замысловатыми узорами.  
В углу стоит небольшая железная кровать с аккуратно заправленным покрывалом.

На покрывале ты замечаешь потёртую бумажку. Похоже, это записка... ~''',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data == 'letter')
def handle_letter(call: types.CallbackQuery):

    markup = types.InlineKeyboardMarkup()
    button_put = types.InlineKeyboardButton('Отложить записку', callback_data="put")
    markup.add(button_put)

    bot.answer_callback_query(call.id, text='Смотрим записи...')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    bot.send_message(call.message.chat.id,
    '''📝 - Приветствую тебя, странник! Ты наверняка задаёшься вопросом, что это за место? Не переживай, я всё объясню. 

Это - твоя хижина, откуда ты начнёшь своё путешествие. Что-то вроде главного меню. Здесь находится всё необходимое для комфортного прохождения квестов.[объясняем правила]''', reply_markup= markup)

@bot.callback_query_handler(func=lambda c: c.data == 'put')
def handle_put(call: types.CallbackQuery):

    markup = types.InlineKeyboardMarkup()
    button_mirror = types.InlineKeyboardButton('Подойти к зеркалу', callback_data="mirror")
    markup.add(button_mirror)

    bot.answer_callback_query(call.id, 'Кладём')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    bot.send_message(call.message.chat.id,'''Вы видите зеркало''', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == 'mirror')
def handle_mirror(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, 'Иду к зеркалу...')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    # Убираем inline-клавиатуру у сообщения, где была кнопка "зеркало".
    # call.message.chat.id      — ID чата, где было сообщение.
    # call.message.message_id   — ID конкретного сообщения.
    # reply_markup=None         — «удалить» клавиатуру у сообщения.
    chat_id = call.message.chat.id #Для удобства сохраняем chat_id в отдельную переменную. Этот id будем использовать, когда отправляем новые сообщения.

    # 1) Общая сценка про зеркало
    intro_text = (
        "~ Ты подходишь к запылённому зеркалу. Отражение сначала кажется обычным, "
        "но через миг поверхность стекла начинает искажаться, как вода от брошенного в неё камня... ~\n\n"
        "В отражении одно за другим проявляются четыре силуэта — четыре возможных пути."
    )
    bot.send_message(chat_id, intro_text)

    # 2) Отдельные сообщения по каждой расе с их характеристиками
    #   Ключи должны совпадать с RACES из user_stats.py
    race_order = ["human", "orc", "animal", "raven_man"]
    races_block_parts = []  # сюда сложим куски текста по каждой расе

    for key in race_order:
        race = RACES[key]
        name = race["name"]
        max_hp = race["max_hp"]
        max_energy = race["max_energy"]
        base_strength = race["base_strength"]
        base_intelligence = race["base_intelligence"]
        base_armor = race["base_armor"]
        base_magic_resist = race["base_magic_resist"]

        if key == "human":

            emoji = "🧍 Человек"
        elif key == "orc":

            emoji = "💚 Орк"
        elif key == "animal":

            emoji = "🐾 Животное"
        elif key == "raven_man":

            emoji = "🪶 Равэн"
        else:

            emoji = name

        race_text = f"""
____________________

{emoji}


❤️ Здоровье: {max_hp}
💪 Сила: {base_strength}
📚 Интеллект: {base_intelligence}

🛡 Броня: {base_armor}
✨ Маг. сопротивление: {base_magic_resist}

⚡ Энергия: {max_energy}
"""
        races_block_parts.append(race_text)
        races_block = "\n".join(races_block_parts)
        full_text = races_block

    # 3) Сообщение с кнопками выбора расы
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_human = types.KeyboardButton('Человек')
    btn_orc = types.KeyboardButton('Орк')
    btn_animal = types.KeyboardButton('Животное')
    btn_raven = types.KeyboardButton('Равэн')

    markup.row(btn_human, btn_orc)
    markup.row(btn_animal, btn_raven)

    bot.send_message(chat_id, full_text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['Человек', 'Орк', 'Животное', 'Равэн'])
def handle_race_choice_message(message: types.Message):
    tg_id = message.from_user.id # tg_id – уникальный ID пользователя в Telegram
    chat_id = message.chat.id # chat_id – ID чата (сюда отправляем сообщения)
    text = message.text # text – выбранный текст (название расы)

    # Прячем клавиатуру после выбора
    remove_kb = types.ReplyKeyboardRemove() # специальный объект, чтобы убрать Reply-клавиатуру

    # Преобразуем текст в ключ расы
    if text == 'Человек':
        race_key = 'human'
    elif text == 'Орк':
        race_key = 'orc'
    elif text == 'Животное':
        race_key = 'animal'
    elif text == 'Равэн':
        race_key = 'raven_man'
    else:
        bot.send_message(chat_id, "Не понял, какую расу ты выбрал...", reply_markup=remove_kb)
        return

    if race_key not in RACES:
        bot.send_message(chat_id, "Такая раса не найдена...", reply_markup=remove_kb)
        return

    success = set_race_for_player(tg_id, race_key)
    if not success:
        bot.send_message(chat_id, "Не удалось сохранить выбор расы :(", reply_markup=remove_kb)
        return

    race_name = RACES[race_key]["name"]

    player = get_player_by_tg_id(tg_id)
    if player is None:
        bot.send_message(chat_id, f"Ты выбрал расу: {race_name}.", reply_markup=remove_kb)
        return

    (
        player_id, p_tg_id, username, race,
        level, exp, exp_to_next,
        hp, max_hp,
        energy, max_energy,
        base_strength, base_intelligence,
        base_armor, base_magic_resist,
        armor, magic_resist,
        free_points,
        cookies,
        rating,
        coins
    ) = player

    text_stats = f"""Ты смотришь в зеркало и видишь своё истинное отражение.

Раса: {race_name}
Уровень: {level}
Опыт: {exp} / {exp_to_next}

❤️ Здоровье: {max_hp}
💪 Сила: {base_strength}
📚 Интеллект: {base_intelligence}

🛡 Броня: {base_armor}
✨ Маг. сопротивление: {base_magic_resist}

⚡ Энергия: {max_energy}

Свободных очков: {free_points}

~ Теперь ты готов к своему первому настоящему приключению ~
"""
    bot.send_message(chat_id, text_stats, reply_markup=remove_kb)

    # Сразу показываем хижину с картинкой и inline-меню
    send_hut_view(chat_id)

@bot.message_handler(func=lambda m: m.text == "ТЕСТ ОРУЖИЕ ЛОКО")
def handle_temp_test_weapon(message: types.Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id
    give_temp_random_common_weapon(tg_id, chat_id)

@bot.message_handler(func=lambda m: m.text == "ТЕСТ ОРУЖИЕ")
def handle_test_weapon(message: types.Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id
    give_random_common_weapon(tg_id, chat_id)

@bot.message_handler(func=lambda m: m.text == "ТЕСТ БРОНЯ")
def handle_test_armor(message: types.Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id
    give_random_common_armor(tg_id, chat_id)

@bot.message_handler(func=lambda m: m.text == "ТЕСТ ПЕЧЕНКА")
def handle_test_cookie(message: types.Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id
    give_cookies(tg_id, chat_id, amount=1)

#=================================АРЕНА====================================
def get_unique_random_opponent_for_player(tg_id: int):
    """
    Вернуть случайного противника, которого ещё не показывали этому игроку
    в текущей «сессии поиска».

    Если подходящих противников нет — вернуть None.
    Опирается на get_random_opponent(...) из user_stats.py
    и глобальный словарь ARENA_SEEN_OPPONENTS.
    """
    # Множество уже показанных противников для этого игрока
    seen = ARENA_SEEN_OPPONENTS.get(tg_id, set())

    # Чтобы не попасть в вечный цикл, ограничим число попыток
    max_attempts = 10
    attempts = 0

    while attempts < max_attempts:
        attempts += 1

        opponent = get_random_opponent(exclude_tg_id=tg_id)
        if opponent is None:
            return None  # вообще нет других игроков

        o_tg_id = opponent[1]  # tg_id противника во второй колонке (после id)

        if o_tg_id in seen:
            # Уже показывали этого противника — пробуем ещё
            continue

        # Нашли нового противника
        seen.add(o_tg_id)
        ARENA_SEEN_OPPONENTS[tg_id] = seen
        return opponent

    # Если сюда дошли — скорее всего всех уже показали
    return None

def get_next_opponent_for_player(tg_id: int):
    """
    Возвращает противника случайно, но не совпадающего с последним.
    Если в игре всего 1 противник — вернём его.
    """

    last = ARENA_LAST.get(tg_id)
    max_attempts = 10
    attempts = 0

    while attempts < max_attempts:
        attempts += 1
        opponent = get_random_opponent(exclude_tg_id=tg_id)
        if opponent is None:
            return None  # других игроков нет вообще

        o_tg_id = opponent[1]

        if o_tg_id != last:
            ARENA_LAST[tg_id] = o_tg_id  # сохраняем нового
            return opponent

    # Если все попытки не дали нового — вернём того же
    opponent = get_random_opponent(exclude_tg_id=tg_id)
    if opponent:
        ARENA_LAST[tg_id] = opponent[1]
    return opponent


@bot.callback_query_handler(func=lambda c: c.data == "arena_search")
def arena_search_enemy(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)

    chat_id = call.message.chat.id
    tg_id = call.from_user.id

    # Начинаем новую сессию поиска — очищаем список показанных enemy
    ARENA_SEEN_OPPONENTS[tg_id] = set()

    # Пытаемся найти уникального противника
    opponent = get_next_opponent_for_player(tg_id)

    try:
        # Можно удалить сообщение "описание арены", чтобы не засорять чат
        bot.delete_message(chat_id, call.message.message_id)
    except Exception:
        pass

    if opponent is None:
        bot.send_message(chat_id, "Пока ты один на арене. Других игроков ещё нет ⚠️")
        return

    (
        o_id, o_tg_id, o_username, o_race,
        o_level, o_exp, o_exp_to_next,
        o_hp, o_max_hp,
        o_energy, o_max_energy,
        o_base_strength, o_base_intelligence,
        o_base_armor, o_base_magic_resist,
        o_armor, o_magic_resist,
        o_free_points,
        o_cookies,
        o_rating,
        o_coins
    ) = opponent

    if o_race == 'human':
        o_race_name = 'Человек'
    elif o_race == 'orc':
        o_race_name = 'Орк'
    elif o_race == 'animal':
        o_race_name = 'Животное'
    elif o_race == 'raven_man':
        o_race_name = 'Равен'
    else:
        o_race_name = 'Неизвестно'

    # Красиво показываем имя противника
    display_name = o_username if o_username else f"Игрок #{o_id}"

    text = f"""🏟 Ты осматриваешь арену и находишь противника!

___👤 Противник: {display_name}___
    🏆Рейтинг:{o_rating}  🪙 Монеты: {o_coins}
            
🧬 Раса: {o_race_name}
🔢 Уровень: {o_level}

❤️ Здоровье: {o_max_hp}
💪 Сила: {o_base_strength}
📚 Интеллект: {o_base_intelligence}

🛡 Броня: {o_base_armor}
✨ Маг. сопротивление: {o_base_magic_resist}

Что будешь делать?
"""

    markup = types.InlineKeyboardMarkup()

    # В callback_data зашиваем tg_id противника
    btn_fight = types.InlineKeyboardButton(
        "⚔ Вступить в бой", callback_data=f"arena_fight_{o_tg_id}"
    )
    btn_next = types.InlineKeyboardButton(
        "➡ Следующий", callback_data="arena_next"
    )
    btn_back = types.InlineKeyboardButton(
        "↩ Назад", callback_data="arena_back_city"
    )

    markup.row(btn_fight)
    markup.row(btn_next)
    markup.row(btn_back)

    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "arena_next")
def arena_next_enemy(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)

    chat_id = call.message.chat.id
    tg_id = call.from_user.id

    opponent = get_next_opponent_for_player(tg_id)

    if opponent is None:
        # Все противники уже были показаны
        bot.edit_message_text(
            "Ты уже встретил всех доступных сейчас бойцов на арене.\n"
            "Возвращайся позже, когда появятся новые соперники.",
            chat_id,
            call.message.message_id
        )
        return

    (
        o_id, o_tg_id, o_username, o_race,
        o_level, o_exp, o_exp_to_next,
        o_hp, o_max_hp,
        o_energy, o_max_energy,
        o_base_strength, o_base_intelligence,
        o_base_armor, o_base_magic_resist,
        o_armor, o_magic_resist,
        o_free_points,
        o_cookies,
        o_rating,
        o_coins
    ) = opponent

    if o_race == 'human':
        o_race_name = 'Человек'
    elif o_race == 'orc':
        o_race_name = 'Орк'
    elif o_race == 'animal':
        o_race_name = 'Животное'
    elif o_race == 'raven_man':
        o_race_name = 'Равен'
    else:
        o_race_name = 'Неизвестно'

    display_name = o_username if o_username else f"Игрок #{o_id}"

    text = f"""🏟 Ты продолжаешь поиск...

___👤 Противник: {display_name}___
    🏆Рейтинг:{o_rating}  🪙 Монеты: {o_coins}

🧬 Раса: {o_race_name}
🔢 Уровень: {o_level}

❤️ Здоровье: {o_max_hp}
💪 Сила: {o_base_strength}
📚 Интеллект: {o_base_intelligence}

🛡 Броня: {o_base_armor}
✨ Маг. сопротивление: {o_base_magic_resist}

Выбери действие:
"""

    markup = types.InlineKeyboardMarkup()
    btn_fight = types.InlineKeyboardButton(
        "⚔ Вступить в бой", callback_data=f"arena_fight_{o_tg_id}"
    )
    btn_next = types.InlineKeyboardButton(
        "➡ Следующий", callback_data="arena_next"
    )
    btn_back = types.InlineKeyboardButton(
        "↩ Назад", callback_data="arena_back_city"
    )

    markup.row(btn_fight)
    markup.row(btn_next)
    markup.row(btn_back)

    bot.edit_message_text(
        text,
        chat_id,
        call.message.message_id,
        reply_markup=markup
    )

def get_race_name(race_key: str) -> str:
    """
    Короткий помощник для красивого имени расы.
    """
    if race_key == 'human':
        return 'Человек'
    elif race_key == 'orc':
        return 'Орк'
    elif race_key == 'animal':
        return 'Животное'
    elif race_key == 'raven_man':
        return 'Равэн'
    return 'Неизвестно'


def get_equipped_item_text(tg_id: int, slot: str) -> str:
    """
    slot: 'weapon' | 'armor' | 'book'
    Возвращает красивый текст экипированного предмета.
    """
    item_id = get_equipped_item(tg_id, slot)
    if not item_id:
        return "— пусто —"

    item = get_item_by_id(item_id)
    if not item:
        return "— неизвестно —"

    (
        i_id,
        name,
        type_,
        rarity,
        price,
        damage_min,
        damage_max,
        phys_armor_min,
        phys_armor_max,
        magic_def_min,
        magic_def_max,
        heal_min,
        heal_max,
        heal_percent,
        bonus_hp,
        bonus_energy,
        bonus_strength,
        bonus_intellect,
        bonus_phys_armor,
        bonus_magic_resist,
    ) = item

    # ⚔️ ОРУЖИЕ
    if slot == "weapon" and damage_min is not None and damage_max is not None:
        return f"{name} ({damage_min}-{damage_max})"

    # 🛡 БРОНЯ
    if slot == "armor":
        parts = []
        if phys_armor_min is not None and phys_armor_max is not None:
            parts.append(f"🛡 {phys_armor_min}-{phys_armor_max}")
        if magic_def_min is not None and magic_def_max is not None:
            parts.append(f"✨ {magic_def_min}-{magic_def_max}")
        stats = " | ".join(parts)
        return f"{name} ({stats})" if stats else name

    # 📘 КНИГА
    if slot == "book":
        if damage_min is not None and damage_max is not None:
            return f"{name} ({damage_min}-{damage_max})"
        if heal_percent:
            return f"{name} (+{heal_percent}%)"
        return name

    return name


def format_fighter_stats_block(player_row, title: str) -> str:
    """
    player_row — строка из таблицы players (SELECT * FROM players ...)
    title — заголовок блока (например 'Твои статы' или 'Статы противника').
    """
    (
        player_id, tg_id, username, race,
        level, exp, exp_to_next,
        hp, max_hp,
        energy, max_energy,
        base_strength, base_intelligence,
        base_armor, base_magic_resist,
        armor, magic_resist,
        free_points,
        cookies,
        rating,
        coins
    ) = player_row

    race_name = get_race_name(race)
    nick = f"@{username}" if username else f"id:{tg_id}"

    weapon_text = get_equipped_item_text(tg_id, "weapon")
    armor_text = get_equipped_item_text(tg_id, "armor")
    book_text = get_equipped_item_text(tg_id, "book")

    text = f"""🔹 {title}
    
👤 {nick}
🧬 Раса: {race_name}     ❤️ {hp}/{max_hp}
🔢 Уровень: {level}
🏆 Рейтинг:{rating}

⚔ Оружие: {weapon_text}
🛡 Броня: {armor_text}
📘 Книга: {book_text}

💪 {base_strength}       📚 {base_intelligence}       🛡 {armor}       ✨ {magic_resist}
"""
    return text


@bot.callback_query_handler(func=lambda c: c.data.startswith("arena_fight_"))
def arena_fight_cb(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    try:
        opponent_tg = int(call.data.split("arena_fight_", 1)[1])
    except (IndexError, ValueError):
        bot.answer_callback_query(call.id, "Ошибка данных противника.")
        return

    my_row = get_player_by_tg_id(tg_id)
    enemy_row = get_player_by_tg_id(opponent_tg)

    if my_row is None or enemy_row is None:
        bot.answer_callback_query(call.id, "Ошибка при загрузке бойцов.")
        return

    my_row_list = list(my_row)
    enemy_row_list = list(enemy_row)

    my_phys, my_magic = _compute_initial_shields(my_row_list)
    en_phys, en_magic = _compute_initial_shields(enemy_row_list)

    # Создаём состояние боя (message_id заполним после отправки)
    BATTLES[tg_id] = {
        "player": {"row": my_row_list, "phys": my_phys, "magic": my_magic, "phys_max": my_phys, "magic_max": my_magic},
        "enemy": {"row": enemy_row_list, "phys": en_phys, "magic": en_magic, "phys_max": en_phys,
                  "magic_max": en_magic},
        "chat_id": chat_id,
        "message_id": None
    }

    my_block = format_fighter_stats_block_in_battle(BATTLES[tg_id]["player"], "Твои статы")
    enemy_block = format_fighter_stats_block_in_battle(BATTLES[tg_id]["enemy"], "Статы противника")

    text = f"""{my_block}
   ======================
                    ⚔️  VS  ⚔️
   ======================      
{enemy_block}
Выбери своё действие:
"""

    # Отправляем НОВОЕ сообщение боя (а не edit)
    msg = bot.send_message(chat_id, text, reply_markup=_arena_battle_keyboard())

    # Сохраняем message_id этого сообщения, чтобы потом удалять
    BATTLES[tg_id]["message_id"] = msg.message_id

    bot.answer_callback_query(call.id)

    # Можно удалить сообщение с карточкой противника (где была кнопка "вступить в бой")
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception:
        pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("arena_action_"))
def arena_action_cb(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    action = call.data.split("arena_action_", 1)[1]  # attack / defend / magic / run

    state = BATTLES.get(tg_id)
    if not state:
        bot.answer_callback_query(call.id, "Бой не найден.")
        return

    player = state["player"]   # {"row":[...], "phys":int, "magic":int, "phys_max":int, "magic_max":int}
    enemy = state["enemy"]
    p_row = player["row"]
    e_row = enemy["row"]

    # 1) Удаляем текущее сообщение со статами (то, где были кнопки действий)
    old_stats_msg_id = state.get("message_id")
    if old_stats_msg_id:
        try:
            bot.delete_message(chat_id, old_stats_msg_id)
        except Exception:
            pass
        state["message_id"] = None

    # ================== ПОБЕГ (со штрафом рейтинга) ==================
    if action == "run":
        # штраф рейтинга как при поражении
        p_level = int(p_row[4] or 0)
        e_level = int(e_row[4] or 0)
        p_rating = int(p_row[19] or 0)
        e_rating = int(e_row[19] or 0)

        delta = _calc_rating_delta(p_rating, p_level, e_rating, e_level)
        new_rating = max(0, p_rating - delta)
        update_player(tg_id, rating=new_rating)

        BATTLES.pop(tg_id, None)

        bot.send_message(
            chat_id,
            f"🏃 Герой сбежал с арены.\n📉 Рейтинг: -{delta} (теперь {new_rating})",
            reply_markup=_arena_after_battle_keyboard()
        )
        bot.answer_callback_query(call.id)
        return

    # ================== ДЕЙСТВИЕ ПРОТИВНИКА ==================
    enemy_action = random.choice(["attack", "attack", "defend", "magic"])

    log_parts: list[str] = ["📜 Ход:"]

    # стойки защиты (один раз)
    if action == "defend":
        log_parts.append("🛡 Твой герой уходит в защиту, выжидая момент.")
    if enemy_action == "defend":
        log_parts.append("🛡 Противник уходит в защиту.")

    # ================== ХОД ГЕРОЯ ==================
    if action == "attack":
        dmg_info = _compute_raw_damage(p_row, use_magic=False)
        roll = int(dmg_info["roll"])
        total_dmg = int(dmg_info["total"])

        # стартовые щиты цели ДО удара
        enemy_primary_start = int(enemy["phys"])              # phys — основной щит от физ. урона
        enemy_secondary_start = int(enemy["magic"]) if enemy_action == "defend" else 0  # в защите урон может уйти во 2-й щит

        res = _apply_damage_to_defender(
            enemy,
            total_dmg,
            "phys",
            defender_is_defending=(enemy_action == "defend")
        )

        tool_name = _weapon_name_for_attack(tg_id, use_magic=False)  # оружие

        log_parts.append(
            _render_hit_story(
                attacker_name="Твой герой",
                tool_name=tool_name,
                roll=roll,
                total_dmg=total_dmg,
                dmg_type="phys",
                result=res,
                defender_defending=(enemy_action == "defend"),
                defender_primary_start=enemy_primary_start,
                defender_secondary_start=enemy_secondary_start
            )
        )

    elif action == "magic":
        dmg_info = _compute_raw_damage(p_row, use_magic=True)
        roll = int(dmg_info["roll"])
        total_dmg = int(dmg_info["total"])

        # для магии основной щит = magic
        enemy_primary_start = int(enemy["magic"])
        enemy_secondary_start = int(enemy["phys"]) if enemy_action == "defend" else 0

        res = _apply_damage_to_defender(
            enemy,
            total_dmg,
            "magic",
            defender_is_defending=(enemy_action == "defend")
        )

        tool_name = _weapon_name_for_attack(tg_id, use_magic=True)  # книга (или — пусто —)

        log_parts.append(
            _render_hit_story(
                attacker_name="Твой герой",
                tool_name=tool_name,
                roll=roll,
                total_dmg=total_dmg,
                dmg_type="magic",
                result=res,
                defender_defending=(enemy_action == "defend"),
                defender_primary_start=enemy_primary_start,
                defender_secondary_start=enemy_secondary_start
            )
        )

    elif action == "defend":
        pass
    else:
        bot.answer_callback_query(call.id, "Неизвестное действие.")
        return

    # ================== ХОД ПРОТИВНИКА ==================
    if e_row[7] > 0:
        enemy_tg_id = int(e_row[1])

        if enemy_action == "attack":
            dmg_info = _compute_raw_damage(e_row, use_magic=False)
            roll = int(dmg_info["roll"])
            total_dmg = int(dmg_info["total"])

            player_primary_start = int(player["phys"])
            player_secondary_start = int(player["magic"]) if action == "defend" else 0

            res = _apply_damage_to_defender(
                player,
                total_dmg,
                "phys",
                defender_is_defending=(action == "defend")
            )

            tool_name = _weapon_name_for_attack(enemy_tg_id, use_magic=False)

            log_parts.append(
                _render_hit_story(
                    attacker_name="Противник",
                    tool_name=tool_name,
                    roll=roll,
                    total_dmg=total_dmg,
                    dmg_type="phys",
                    result=res,
                    defender_defending=(action == "defend"),
                    defender_primary_start=player_primary_start,
                    defender_secondary_start=player_secondary_start
                )
            )

        elif enemy_action == "magic":
            dmg_info = _compute_raw_damage(e_row, use_magic=True)
            roll = int(dmg_info["roll"])
            total_dmg = int(dmg_info["total"])

            player_primary_start = int(player["magic"])
            player_secondary_start = int(player["phys"]) if action == "defend" else 0

            res = _apply_damage_to_defender(
                player,
                total_dmg,
                "magic",
                defender_is_defending=(action == "defend")
            )

            tool_name = _weapon_name_for_attack(enemy_tg_id, use_magic=True)

            log_parts.append(
                _render_hit_story(
                    attacker_name="Противник",
                    tool_name=tool_name,
                    roll=roll,
                    total_dmg=total_dmg,
                    dmg_type="magic",
                    result=res,
                    defender_defending=(action == "defend"),
                    defender_primary_start=player_primary_start,
                    defender_secondary_start=player_secondary_start
                )
            )

        elif enemy_action == "defend":
            pass

    # ================== ПРОВЕРКА КОНЦА БОЯ ==================
    ended = False
    final_text = None

    if p_row[7] <= 0 and e_row[7] <= 0:
        ended = True
        final_text = "🤝 Оба бойца падают без сил. Ничья!"
    elif e_row[7] <= 0:
        ended = True
        final_text = "🏆 Твой герой одержал победу на арене!"
    elif p_row[7] <= 0:
        ended = True
        final_text = "💀 Твой герой пал в бою на арене..."

    # ================== ОТПРАВКА ЛОГА ==================
    markup = types.InlineKeyboardMarkup()
    btn_next = types.InlineKeyboardButton("➡ Следующий ход", callback_data="arena_next_turn")
    markup.add(btn_next)

    bot.send_message(
        chat_id,
        "\n\n".join(log_parts),
        parse_mode="Markdown",
        reply_markup=markup
    )

    # если бой закончился — результат покажем на "Следующий ход"
    if ended:
        state["ended"] = True
        state["final_text"] = final_text
    else:
        state["ended"] = False
        state.pop("final_text", None)

    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "arena_next_turn")
def arena_next_turn_cb(call: types.CallbackQuery):
    tg_id = call.from_user.id
    chat_id = call.message.chat.id

    state = BATTLES.get(tg_id)
    if not state:
        bot.answer_callback_query(call.id, "Бой не найден.")
        return

    # Если бой завершён — здесь показываем финал + начисления/штрафы
    if state.get("ended"):
        # убрать кнопку у лога, чтобы не нажимали повторно
        try:
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass

        player = state["player"]
        enemy = state["enemy"]
        p_row = player["row"]
        e_row = enemy["row"]

        # индексы в players row:
        # level = 4, rating = 19
        p_level = int(p_row[4] or 0)
        e_level = int(e_row[4] or 0)
        p_rating = int(p_row[19] or 0)
        e_rating = int(e_row[19] or 0)

        result_text = state.get("final_text", "Бой завершён.")

        # --- НИЧЬЯ ---
        if "ничья" in result_text.lower():
            bot.send_message(chat_id, result_text, reply_markup=_arena_after_battle_keyboard())
            BATTLES.pop(tg_id, None)
            bot.answer_callback_query(call.id)
            return

        # --- ПОБЕДА ---
        if "побед" in result_text.lower():
            delta = _calc_rating_delta(p_rating, p_level, e_rating, e_level)
            new_rating = max(0, p_rating + delta)
            update_player(tg_id, rating=new_rating)

            bot.send_message(chat_id, f"📈 Рейтинг: +{delta} (теперь {new_rating})")
            _try_give_common_loot(tg_id, chat_id)

            bot.send_message(chat_id, result_text, reply_markup=_arena_after_battle_keyboard())
            BATTLES.pop(tg_id, None)
            bot.answer_callback_query(call.id)
            return

        # --- ПОРАЖЕНИЕ ---
        delta = _calc_rating_delta(p_rating, p_level, e_rating, e_level)
        new_rating = max(0, p_rating - delta)
        update_player(tg_id, rating=new_rating)

        bot.send_message(chat_id, f"📉 Рейтинг: -{delta} (теперь {new_rating})")
        bot.send_message(chat_id, result_text, reply_markup=_arena_after_battle_keyboard())

        BATTLES.pop(tg_id, None)
        bot.answer_callback_query(call.id)
        return

    # Если бой НЕ завершён — просто показать новые статы и кнопки действий
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except Exception:
        pass

    player = state["player"]
    enemy = state["enemy"]

    my_block = format_fighter_stats_block_in_battle(player, "Статы героя")
    enemy_block = format_fighter_stats_block_in_battle(enemy, "Статы противника")

    text = f"""{my_block}
   ======================
                    ⚔️  VS  ⚔️
   ======================
{enemy_block}
Выбери действие:
"""

    msg = bot.send_message(chat_id, text, reply_markup=_arena_battle_keyboard())
    state["message_id"] = msg.message_id

    bot.answer_callback_query(call.id)


def _arena_battle_keyboard():
    """
    Клавиатура во время боя.
    """
    markup = types.InlineKeyboardMarkup()
    btn_attack = types.InlineKeyboardButton("🗡 Атака", callback_data="arena_action_attack")
    btn_defend = types.InlineKeyboardButton("🛡 Защита", callback_data="arena_action_defend")
    btn_magic = types.InlineKeyboardButton("✨ Магия", callback_data="arena_action_magic")
    btn_run = types.InlineKeyboardButton("🏃 Бежать", callback_data="arena_action_run")

    markup.row(btn_attack, btn_defend)
    markup.row(btn_magic, btn_run)
    return markup

def _roll_item_range(val_min, val_max) -> int:
    if val_min is None or val_max is None:
        return 0
    try:
        return random.randint(int(val_min), int(val_max))
    except Exception:
        return 0


def _compute_initial_shields(fighter_row_list: list) -> tuple[int, int]:
    """
    Возвращает (phys_shield, magic_shield) на старте боя.

    Берём:
      - totals из players: armor (индекс 15), magic_resist (индекс 16)
      - + бонусы от экипировки:
         weapon + armor:
           phys_armor_min/max (индексы 7/8)
           magic_def_min/max  (индексы 9/10)
    """
    tg_id = fighter_row_list[1]

    base_phys = int(fighter_row_list[15] or 0)
    base_magic = int(fighter_row_list[16] or 0)

    phys_bonus = 0
    magic_bonus = 0

    # weapon
    w_id = get_equipped_item(tg_id, "weapon")
    if w_id:
        item = get_item_by_id(w_id)
        if item:
            phys_bonus += _roll_item_range(item[7], item[8])
            magic_bonus += _roll_item_range(item[9], item[10])

    # armor
    a_id = get_equipped_item(tg_id, "armor")
    if a_id:
        item = get_item_by_id(a_id)
        if item:
            phys_bonus += _roll_item_range(item[7], item[8])
            magic_bonus += _roll_item_range(item[9], item[10])

    return base_phys + phys_bonus, base_magic + magic_bonus


def _apply_damage_to_defender(defender: dict, dmg: int, dmg_type: str, defender_is_defending: bool):
    """
    Наносит урон defender'у и возвращает детали удара:
    {
      "dmg": int,
      "to_primary": int,
      "to_secondary": int,
      "to_hp": int,
      "primary_left": int,
      "secondary_left": int,
      "hp_left": int,
      "primary_broken": bool,
      "secondary_broken": bool
    }
    """
    if dmg <= 0:
        row = defender["row"]
        return {
            "dmg": 0,
            "to_primary": 0,
            "to_secondary": 0,
            "to_hp": 0,
            "primary_left": defender["phys"] if dmg_type == "phys" else defender["magic"],
            "secondary_left": defender["magic"] if dmg_type == "phys" else defender["phys"],
            "hp_left": int(row[7]),
            "primary_broken": False,
            "secondary_broken": False
        }

    row = defender["row"]

    if dmg_type == "phys":
        primary = "phys"
        secondary = "magic" if defender_is_defending else None
    else:
        primary = "magic"
        secondary = "phys" if defender_is_defending else None

    start_primary = defender[primary]
    start_secondary = defender[secondary] if secondary else 0

    to_primary = 0
    to_secondary = 0
    to_hp = 0

    # 1) основной щит
    take = min(defender[primary], dmg)
    defender[primary] -= take
    dmg -= take
    to_primary += take

    primary_broken = (start_primary > 0 and defender[primary] == 0)

    # 2) вторичный щит (если защита)
    secondary_broken = False
    if dmg > 0 and secondary:
        take2 = min(defender[secondary], dmg)
        defender[secondary] -= take2
        dmg -= take2
        to_secondary += take2
        secondary_broken = (start_secondary > 0 and defender[secondary] == 0)

    # 3) HP
    if dmg > 0:
        before_hp = int(row[7] or 0)
        row[7] = max(0, before_hp - dmg)
        to_hp = before_hp - int(row[7])

    return {
        "dmg": to_primary + to_secondary + to_hp,
        "to_primary": to_primary,
        "to_secondary": to_secondary,
        "to_hp": to_hp,
        "primary_left": defender[primary],
        "secondary_left": defender[secondary] if secondary else None,
        "hp_left": int(row[7]),
        "primary_broken": primary_broken,
        "secondary_broken": secondary_broken
    }


def _compute_raw_damage(attacker_row: list, use_magic: bool) -> dict:
    """
    Возвращает:
    {
      "roll": выпавшее число предмета (оружие/книга),
      "total": итоговый урон = base + roll
    }
    """
    attacker_tg = attacker_row[1]

    strength = int(attacker_row[11] or 0)
    intellect = int(attacker_row[12] or 0)
    base = intellect if use_magic else strength

    roll = 0
    if use_magic:
        item_id = get_equipped_item(attacker_tg, "book")
    else:
        item_id = get_equipped_item(attacker_tg, "weapon")

    if item_id:
        item = get_item_by_id(item_id)
        if item:
            roll = _roll_item_range(item[5], item[6])

    total = max(0, base + roll)
    return {"roll": roll, "total": total}


def format_fighter_stats_block_in_battle(fighter: dict, title: str) -> str:
    """
    Показывает блок статов + текущие щиты (броня/маг.щит) из боя.
    fighter = {"row":[...], "phys":int, "magic":int}
    """
    row = fighter["row"]
    (
        player_id, tg_id, username, race,
        level, exp, exp_to_next,
        hp, max_hp,
        energy, max_energy,
        base_strength, base_intelligence,
        base_armor, base_magic_resist,
        armor, magic_resist,
        free_points,
        cookies,
        rating,
        coins
    ) = row

    race_name = get_race_name(race)
    nick = f"@{username}" if username else f"id:{tg_id}"

    phys_shield = fighter["phys"]
    magic_shield = fighter["magic"]

    phys_max = fighter.get("phys_max", phys_shield)
    magic_max = fighter.get("magic_max", magic_shield)

    weapon_text = get_equipped_item_text(tg_id, "weapon")
    armor_text = get_equipped_item_text(tg_id, "armor")
    book_text = get_equipped_item_text(tg_id, "book")

    text = f"""🔹 {title}

👤 {nick}
🧬 Раса: {race_name}     
🔢 Уровень: {level}      
🏆 Рейтинг:{rating}
----------------------
Оружие: {weapon_text}
Броня: {armor_text}
Книга: {book_text}
----------------------
💪 {base_strength}    📚 {base_intelligence}
----------------------
❤️ {hp}/{max_hp}    🛡 {phys_shield}/{phys_max}    ✨ {magic_shield}/{magic_max}
----------------------
"""
    return text

def _weapon_name_for_attack(tg_id: int, use_magic: bool) -> str:
    if use_magic:
        # книга нужна для магии — если её нет, ниже в логе уже будет "пытается что-то наколдовать"
        return get_equipped_item_text(tg_id, "book")

    # физ атака: если оружия нет — бьёт кулаками
    w = get_equipped_item_text(tg_id, "weapon")
    if not w or w.strip() == "— пусто —":
        return "Кулаки"
    return w


def _ru_uron(n: int) -> str:
    # 1 урон, 2-4 урона, 5+ урона (нам достаточно простого варианта)
    return "урон" if n == 1 else "урона"

def _render_hit_story(
    attacker_name: str,
    tool_name: str,
    roll: int,
    total_dmg: int,
    dmg_type: str,                   # "phys" | "magic"
    result: dict,
    defender_defending: bool,
    defender_primary_start: int,
    defender_secondary_start: int
) -> str:
    icon = "🗡" if dmg_type == "phys" else "✨"

    lines = []

    # если магия без книги — другой текст
    if dmg_type == "magic" and (not tool_name or tool_name.strip() == "— пусто —"):
        lines.append(f"{icon} {attacker_name} пытается что-то наколдовать…")
    else:
        lines.append(f"{icon} {attacker_name} атакует, используя *{tool_name}*.")

    # 🎲 + Итоговый урон (как ты хочешь)
    lines.append(f"🎲 Выпало: {roll}  Итоговый урон: {total_dmg}")

    # Состав защиты и сколько поглотили — ТОЛЬКО суммой
    if defender_defending:
        defense_sum = int(defender_primary_start) + int(defender_secondary_start)
        lines.append(f"🛡 Защита цели: {defense_sum}")
    else:
        defense_sum = int(defender_primary_start)
        lines.append(f"🛡 Защита цели: {defense_sum}")

    absorbed_sum = int(result.get("to_primary", 0)) + int(result.get("to_secondary", 0))
    lines.append(f"➤ Щиты поглотили: {absorbed_sum}.")

    if result.get("secondary_broken"):
        lines.append("💥 Дополнительная защита не выдержала!")
    if result.get("primary_broken"):
        lines.append("💥 Щит трескается и разрушается!")

    if result.get("to_hp", 0) > 0:
        hp_dmg = int(result["to_hp"])
        lines.append(f"➤ {hp_dmg} {_ru_uron(hp_dmg)} проходит в здоровье.")
    else:
        lines.append("➤ Урон не смог пробить здоровье.")

    return "\n".join(lines)


def _calc_rating_delta(my_rating: int, my_level: int, enemy_rating: int, enemy_level: int) -> int:
    """
    Базово: +1
    +1 за каждый уровень противника (как ты попросил: "за каждый уровень")
    +бонус за победу над более рейтинговым (чем больше разница — тем больше бонус)
    """
    my_rating = int(my_rating or 0)
    enemy_rating = int(enemy_rating or 0)
    enemy_level = int(enemy_level or 0)

    rating_bonus = max(0, (enemy_rating - my_rating) // 10)  # шаг 10 рейтинга = +1 бонус
    return 1 + enemy_level + rating_bonus


def _try_give_common_loot(winner_tg_id: int, chat_id: int) -> bool:
    """
    Шанс 1/100 выдать любой обычный предмет (rarity='common').
    Возвращает True, если выдал.
    """
    if random.randint(1, 100) != 1:
        return False

    all_items = []
    for t in ("weapon", "armor", "book"):
        rows = get_items_by_type(t)  # строки из items
        for it in rows:
            # структура: (id, name, type, rarity, price, ...)
            if len(it) > 3 and it[3] == "common":
                all_items.append(it)

    if not all_items:
        return False

    item_row = random.choice(all_items)
    item_id = item_row[0]
    item_name = item_row[1]

    add_item_to_inventory(winner_tg_id, item_id, 1)
    bot.send_message(chat_id, f"🎁 Удача на твоей стороне! Ты получил обычный предмет: *{item_name}*", parse_mode="Markdown")
    return True


def _arena_after_battle_keyboard():
    """
    Клавиатура после окончания боя.
    """
    markup = types.InlineKeyboardMarkup()
    btn_search = types.InlineKeyboardButton("🔍 Искать нового противника", callback_data="arena_search")
    btn_back = types.InlineKeyboardButton("↩ Вернуться в город", callback_data="arena_back_city")
    markup.row(btn_search)
    markup.row(btn_back)
    return markup








create_inventory_tables() # создаём таблицы инвентаря при старте скрипта
create_players_tables() # создаём таблицу игроков при старте скрипта
bot.polling()

# мне нужно добавить объяснения практически на каждую строчку из чата гпт!!!