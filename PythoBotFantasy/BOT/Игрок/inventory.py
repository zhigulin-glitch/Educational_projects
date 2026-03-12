import sqlite3
from typing import Optional

from BOT.Игрок.user_stats import (
    DB_PLAYERS_NAME,
    get_player_by_tg_id,
    update_player,
    RACES,  # чтобы знать базовый max_hp и max_energy по расе
)
from BOT.Предметы.db import get_item_by_id  # из твоего db.py с items


def connect():
    """
    Подключение к базе players.db (там же, где таблица players).
    В ЭТОЙ базе будут храниться инвентарь и экипировка.
    """
    return sqlite3.connect(DB_PLAYERS_NAME)




# ===================== СОЗДАНИЕ ТАБЛИЦ =====================

def create_inventory_tables():
    """
       Создаёт таблицы:
         - inventory        (главный инвентарь в хижине)
         - temp_inventory   (временный лут из локаций)
         - equipment        (основная экипировка)
         - temp_equipment   (текущая экипировка в локации)
    """
    db = connect()
    cursor = db.cursor()

    # Главный инвентарь (то, что уже "привезли" в хижину)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER,        -- к какому игроку относится
        item_id INTEGER,      -- id предмета из таблицы items
        quantity INTEGER      -- сколько таких предметов
    )
    """)

    # ВРЕМЕННЫЙ инвентарь (лут в локации, ещё не доставлен в хижину)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS temp_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER,        -- к какому игроку относится
        item_id INTEGER,      -- id предмета из таблицы items
        quantity INTEGER      -- сколько таких предметов
    )
    """)

    # Таблица экипировки
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER,
        slot TEXT,
        item_id INTEGER
    )
    """)

    # 🔹 НОВОЕ: таблица текущей (временной) экипировки
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            slot TEXT,
            item_id INTEGER
        )
        """)

    db.commit()
    db.close()




# ===================== ИНВЕНТАРЬ =====================

def add_item_to_inventory(tg_id: int, item_id: int, quantity: int = 1): # функция для добавления вещи в сумку. # tg_id — кому. # item_id — какой предмет (id из таблицы items). quantity: int = 1 — сколько штук добавить, по умолчанию 1.
    """
    Добавить предмет в инвентарь игрока.
    Если предмет уже есть — увеличивает количество.
    """
    if quantity <= 0: # Если quantity <= 0 — не делаем ничего (return).
        return

    db = connect() # Подключаемся к БД
    cursor = db.cursor() # берём курсор.

#----------- Ищем, есть ли уже запись для такого игрока и этого предмета. _____ ? — плейсхолдеры, значения подставляем (tg_id, item_id). ________ row = cursor.fetchone() — берём одну строку (или None).
    cursor.execute("""
    SELECT id, quantity FROM inventory
    WHERE tg_id = ? AND item_id = ?
    """, (tg_id, item_id))
    row = cursor.fetchone()

    if row is None:                 # Если строки нет (row is None) — у игрока ещё нет такого предмета. # Делаем INSERT — создаём новую запись.
        cursor.execute("""
        INSERT INTO inventory (tg_id, item_id, quantity)
        VALUES (?, ?, ?)
        """, (tg_id, item_id, quantity))
    else:                                               # Если строка есть — распаковываем row: # inv_id — id записи в таблице inventory. old_qty — сколько уже было.
        inv_id, old_qty = row
        new_qty = old_qty + quantity                    # new_qty = old_qty + quantity — новое количество.
        cursor.execute("""
        UPDATE inventory
        SET quantity = ?
        WHERE id = ?
        """, (new_qty, inv_id))

    db.commit() # сохраняем изменения в базу.
    db.close() # закрываем подключение.

def add_item_to_temp_inventory(tg_id: int, item_id: int, quantity: int = 1):
    """
    Добавить предмет во ВРЕМЕННЫЙ инвентарь (лут в локации).
    Аналог add_item_to_inventory, только в таблицу temp_inventory.
    """
    if quantity <= 0:
        return

    db = connect()
    cursor = db.cursor()

    cursor.execute("""
    SELECT id, quantity FROM temp_inventory
    WHERE tg_id = ? AND item_id = ?
    """, (tg_id, item_id))
    row = cursor.fetchone()

    if row is None:
        cursor.execute("""
        INSERT INTO temp_inventory (tg_id, item_id, quantity)
        VALUES (?, ?, ?)
        """, (tg_id, item_id, quantity))
    else:
        inv_id, old_qty = row
        new_qty = old_qty + quantity
        cursor.execute("""
        UPDATE temp_inventory
        SET quantity = ?
        WHERE id = ?
        """, (new_qty, inv_id))

    db.commit()
    db.close()


def remove_item_from_inventory(tg_id: int, item_id: int, quantity: int = 1) -> bool:
    """
    Убрать предмет из инвентаря.
    Возвращает True, если получилось убрать, False — если предмета не хватает.
    """
    if quantity <= 0:
        return False

    db = connect()
    cursor = db.cursor()

    cursor.execute("""
    SELECT id, quantity FROM inventory
    WHERE tg_id = ? AND item_id = ?
    """, (tg_id, item_id))
    row = cursor.fetchone()

    if row is None:
        db.close()
        return False

    inv_id, old_qty = row
    if old_qty < quantity:
        db.close()
        return False

    new_qty = old_qty - quantity
    if new_qty == 0:
        cursor.execute("DELETE FROM inventory WHERE id = ?", (inv_id,))
    else:
        cursor.execute("""
        UPDATE inventory
        SET quantity = ?
        WHERE id = ?
        """, (new_qty, inv_id))

    db.commit()
    db.close()
    return True


def remove_item_from_temp_inventory(tg_id: int, item_id: int, quantity: int = 1) -> bool:
    """
    Удаляет предмет из ВРЕМЕННОГО инвентаря (таблица temp_inventory).
    Если quantity >= текущего количества — строка удаляется полностью.
    Возвращает True, если что-то реально удалили.
    """
    if quantity <= 0:
        return False

    db = connect()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, quantity FROM temp_inventory
        WHERE tg_id = ? AND item_id = ?
    """, (tg_id, item_id))
    row = cursor.fetchone()

    if row is None:
        db.close()
        return False

    inv_id, current_qty = row

    if current_qty <= quantity:
        cursor.execute("DELETE FROM temp_inventory WHERE id = ?", (inv_id,))
    else:
        cursor.execute("""
            UPDATE temp_inventory
            SET quantity = ?
            WHERE id = ?
        """, (current_qty - quantity, inv_id))

    db.commit()
    db.close()
    return True


def get_inventory(tg_id: int):
    """
    Вернуть список всех предметов в инвентаре игрока.
    Список кортежей (id, tg_id, item_id, quantity).
    """
    db = connect()
    cursor = db.cursor()

    cursor.execute("""
    SELECT id, tg_id, item_id, quantity
    FROM inventory
    WHERE tg_id = ?
    """, (tg_id,))
    rows = cursor.fetchall()

    db.close()
    return rows             # Закрываем базу и возвращаем список.


# ===================== ВРЕМЕННЫЙ ИНВЕНТАРЬ (ЛУТ ИЗ ЛОКАЦИИ) =====================

def add_temp_item(tg_id: int, item_id: int, quantity: int = 1):
    """
    Добавить предмет во ВРЕМЕННЫЙ инвентарь (лут из локации).
    Работает так же, как add_item_to_inventory, но пишет в temp_inventory.
    """
    if quantity <= 0:
        return

    db = connect()
    cursor = db.cursor()

    cursor.execute("""
    SELECT id, quantity FROM temp_inventory
    WHERE tg_id = ? AND item_id = ?
    """, (tg_id, item_id))
    row = cursor.fetchone()

    if row is None:
        cursor.execute("""
        INSERT INTO temp_inventory (tg_id, item_id, quantity)
        VALUES (?, ?, ?)
        """, (tg_id, item_id, quantity))
    else:
        inv_id, old_qty = row
        new_qty = old_qty + quantity
        cursor.execute("""
        UPDATE temp_inventory
        SET quantity = ?
        WHERE id = ?
        """, (new_qty, inv_id))

    db.commit()
    db.close()


def get_temp_inventory(tg_id: int):
    """
    Вернуть список всех предметов во ВРЕМЕННОМ инвентаре игрока.
    Список кортежей (id, tg_id, item_id, quantity).
    """
    db = connect()
    cursor = db.cursor()

    cursor.execute("""
    SELECT id, tg_id, item_id, quantity
    FROM temp_inventory
    WHERE tg_id = ?
    """, (tg_id,))
    rows = cursor.fetchall()

    db.close()
    return rows


def clear_temp_inventory(tg_id: int):
    """
    Полностью очистить временный инвентарь игрока.
    (используем после того, как лут перенесли в основной)
    """
    db = connect()
    cursor = db.cursor()

    cursor.execute("""
    DELETE FROM temp_inventory
    WHERE tg_id = ?
    """, (tg_id,))

    db.commit()
    db.close()

def move_temp_to_main_inventory(tg_id: int):
    """
    Перенести весь лут из временного инвентаря (temp_inventory)
    в основной (inventory).

    Логика:
      - читаем все строки из temp_inventory
      - для каждой: добавляем в обычный inventory (add_item_to_inventory)
      - после этого очищаем temp_inventory для этого игрока
    """
    rows = get_temp_inventory(tg_id)
    if not rows:
        return  # нечего переносить

    for inv_id, p_tg_id, item_id, qty in rows:
        add_item_to_inventory(tg_id, item_id, qty)

    clear_temp_inventory(tg_id)



# ===================== ЭКИПИРОВКА =====================

def get_equipment(tg_id: int):
    """
    Вернуть всю экипировку игрока.
    Список кортежей (id, tg_id, slot, item_id).
    """
    db = connect()
    cursor = db.cursor()

    cursor.execute("""
    SELECT id, tg_id, slot, item_id
    FROM equipment
    WHERE tg_id = ?
    """, (tg_id,))
    rows = cursor.fetchall()

    db.close()
    return rows


def get_equipped_item(tg_id: int, slot: str, use_temp: bool = False) -> Optional[int]:
    """
    Вернуть id предмета в слоте.
    use_temp=False -> основная экипировка (equipment)
    use_temp=True  -> текущая экипировка (temp_equipment)
    """
    table = "temp_equipment" if use_temp else "equipment"

    db = connect()
    cursor = db.cursor()

    cursor.execute(f"""
        SELECT item_id FROM {table}
        WHERE tg_id = ? AND slot = ?
    """, (tg_id, slot))
    row = cursor.fetchone()

    db.close()

    if row is None:
        return None
    return row[0]


def equip_item(tg_id: int, item_id: int, slot: str, use_temp: bool = False) -> bool:
    """
    Надеть предмет в указанный слот.

    Если use_temp = False  -> пишем в таблицу equipment (основная экипировка).
    Если use_temp = True   -> пишем в таблицу temp_equipment (текущая экипировка).
    """
    db = connect()
    cursor = db.cursor()

    # --- проверяем, есть ли предмет у игрока (в любом инвентаре) ---
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0)
        FROM inventory
        WHERE tg_id = ? AND item_id = ?
    """, (tg_id, item_id))
    row = cursor.fetchone()
    inv_qty = row[0] if row is not None else 0

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0)
        FROM temp_inventory
        WHERE tg_id = ? AND item_id = ?
    """, (tg_id, item_id))
    row = cursor.fetchone()
    temp_qty = row[0] if row is not None else 0

    total_qty = (inv_qty or 0) + (temp_qty or 0)
    if total_qty <= 0:
        db.close()
        return False

    # --- выбираем таблицу экипировки ---
    table = "temp_equipment" if use_temp else "equipment"

    # Проверяем, есть ли уже запись для этого слота
    cursor.execute(f"""
        SELECT id FROM {table}
        WHERE tg_id = ? AND slot = ?
    """, (tg_id, slot))
    eq_row = cursor.fetchone()

    if eq_row is None:
        cursor.execute(f"""
            INSERT INTO {table} (tg_id, slot, item_id)
            VALUES (?, ?, ?)
        """, (tg_id, slot, item_id))
    else:
        eq_id = eq_row[0]
        cursor.execute(f"""
            UPDATE {table}
            SET item_id = ?
            WHERE id = ?
        """, (item_id, eq_id))

    db.commit()
    db.close()

    # ⚠ ВАЖНО:
    # Пока для простоты пересчитываем статы только из "основной" экипировки,
    # как и раньше. Т. е. temp_equipment влияет только на "текущую" логику,
    # когда ты сам её будешь использовать.
    if not use_temp:
        recalc_player_stats_from_equipment(tg_id)

    return True




def unequip_slot(tg_id: int, slot: str, use_temp: bool = False):
    """
    Снять предмет из указанного слота.
    use_temp=False -> из основной экипировки
    use_temp=True  -> из текущей экипировки
    """
    table = "temp_equipment" if use_temp else "equipment"

    db = connect()
    cursor = db.cursor()

    cursor.execute(f"""
        DELETE FROM {table}
        WHERE tg_id = ? AND slot = ?
    """, (tg_id, slot))

    db.commit()
    db.close()

    if not use_temp:
        recalc_player_stats_from_equipment(tg_id)





# ===================== ПЕРЕСЧЁТ СТАТОВ =====================

def recalc_player_stats_from_equipment(tg_id: int):
    """
    Пересчитывает статы игрока с учётом экипированных предметов.

    ВАЖНО:
      - базовые статы берём из таблицы players (base_armor, base_magic_resist)
        и из RACES по race (max_hp, max_energy).
      - бонусы считаем на основе полей bonus_* в items.

    Что учитываем:
      - armor = base_armor + суммарный bonus_phys_armor
      - magic_resist = base_magic_resist + суммарный bonus_magic_resist
      - max_hp = базовый HP по расе + суммарный bonus_hp
      - max_energy = базовая энергия по расе + суммарный bonus_energy

    Текущее hp/energy обрезаем, если они больше нового максимума.
    """
    player = get_player_by_tg_id(tg_id)
    if player is None:
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

    # --- Базовые значения HP и энергии по расе ---
    # Если раса не выбрана или нет в RACES — используем текущее max_hp/max_energy как базу.
    race_data = RACES.get(race) if race is not None else None
    if race_data is not None:
        base_hp_race = race_data.get("max_hp", max_hp)
        base_energy_race = race_data.get("max_energy", max_energy)
    else:
        base_hp_race = max_hp
        base_energy_race = max_energy

    # Суммарные бонусы от экипированных предметов
    bonus_hp = 0
    bonus_energy = 0
    bonus_strength = 0
    bonus_intellect = 0
    bonus_phys_armor = 0
    bonus_magic_resist = 0

    db = connect()
    cursor = db.cursor()

    cursor.execute("""
    SELECT slot, item_id FROM equipment
    WHERE tg_id = ?
    """, (tg_id,))
    equipped_rows = cursor.fetchall()

    db.close()

    for slot, equipped_item_id in equipped_rows:
        item = get_item_by_id(equipped_item_id)
        if item is None:
            continue

        # Порядок полей соответствует твоему CREATE TABLE items:
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
            i_bonus_hp,
            i_bonus_energy,
            i_bonus_strength,
            i_bonus_intellect,
            i_bonus_phys_armor,
            i_bonus_magic_resist,
        ) = item

        bonus_hp += i_bonus_hp or 0
        bonus_energy += i_bonus_energy or 0
        bonus_strength += i_bonus_strength or 0
        bonus_intellect += i_bonus_intellect or 0
        bonus_phys_armor += i_bonus_phys_armor or 0
        bonus_magic_resist += i_bonus_magic_resist or 0

    # Итоговые значения
    new_armor = base_armor + bonus_phys_armor
    new_magic_resist = base_magic_resist + bonus_magic_resist

    new_max_hp = base_hp_race + bonus_hp
    new_max_energy = base_energy_race + bonus_energy

    # Текущее здоровье/энергия не может быть больше максимума
    new_hp = min(hp, new_max_hp)
    new_energy = min(energy, new_max_energy)

    update_player(
        tg_id,
        armor=new_armor,
        magic_resist=new_magic_resist,
        hp=new_hp,
        max_hp=new_max_hp,
        energy=new_energy,
        max_energy=new_max_energy
    )

