import sqlite3

# Имя файла базы данных с игроками
DB_PLAYERS_NAME = "players.db"

# Описание рас и их стартовых характеристик
RACES = {                                           #RACES — словарь с 4 расами.
    "human": {                                      #Ключи ("human", "orc", "animal", "raven_man") — то, что реально хранится в БД в поле race.
        "name": "Человек",                          #Значения — словари со стартовыми статами:
        "max_hp": 8,
        "max_energy": 100,
        "base_strength": 1,
        "base_intelligence": 2,
        "base_armor": 0,
        "base_magic_resist": 0,
    },
    "orc": {
        "name": "Орк",
        "max_hp": 10,
        "max_energy": 90,
        "base_strength": 2,
        "base_intelligence": 0,
        "base_armor": 2,
        "base_magic_resist": 0,
    },
    "animal": {
        "name": "Животное",
        "max_hp": 15,
        "max_energy": 90,
        "base_strength": 1,
        "base_intelligence": 0,
        "base_armor": 0,
        "base_magic_resist": 0,
    },
    "raven_man": {
        "name": "Равэн",
        "max_hp": 8,
        "max_energy": 110,
        "base_strength": 0,
        "base_intelligence": 2,
        "base_armor": 0,
        "base_magic_resist": 2,
    },
}


def get_exp_to_next_for_level(level: int) -> int:
    """
    Возвращает, сколько опыта нужно до следующего уровня
    для данного уровня.
    В table зашита твоя шкала:
    1 → 25 опыта до 2-го уровня
    2 → 50 до 3-го
    и т.д.

    Если уровень выше, чем в словаре (например 10), возвращает 0 — значит дальше не качаем (на будущее).
    Эта функция нужна:
    при создании игрока (add_player);
    при прокачке (add_exp).
    """
    table = {
        1: 25,
        2: 50,
        3: 100,
        4: 150,
        5: 200,
        6: 250,
        7: 300,
        8: 400,
        9: 550,
    }
    return table.get(level, 0)


def connect():
    """
    Подключение к базе данных игроков.
    Возвращает объект соединения sqlite3.Connection.
    """
    return sqlite3.connect(DB_PLAYERS_NAME)


def create_tables():
    """
    Создание таблицы players, если её ещё нет.
    """
    db = connect()
    cursor = db.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        tg_id INTEGER UNIQUE,          -- уникальный Telegram ID
        username TEXT,                 -- ник игрока
        race TEXT,                     -- раса игрока (human, orc, animal, raven_man)

        level INTEGER DEFAULT 1,       -- уровень
        exp INTEGER DEFAULT 0,         -- текущий опыт
        exp_to_next INTEGER DEFAULT 25, -- опыт до следующего уровня (для 1 уровня 25)

        hp INTEGER,                    -- текущее здоровье
        max_hp INTEGER,                -- максимальное здоровье

        energy INTEGER,                -- текущая энергия
        max_energy INTEGER,            -- максимальная энергия

        base_strength INTEGER,         -- базовая сила (без предметов)
        base_intelligence INTEGER,     -- базовый интеллект (без предметов)

        base_armor INTEGER,            -- базовая броня
        base_magic_resist INTEGER,     -- базовое маг. сопротивление

        armor INTEGER,                 -- итоговая броня (с учётом предметов)
        magic_resist INTEGER,          -- итоговое маг. сопротивление

        free_points INTEGER DEFAULT 3, -- свободные очки характеристик
        cookies INTEGER DEFAULT 0,     -- печеньки
        rating INTEGER DEFAULT 0,      -- рейтинг для арены
        coins INTEGER DEFAULT 0         -- монеты
    )
    """)

    db.commit()
    db.close()


def add_player(tg_id: int, username: str | None = None):
    """
    Добавить нового игрока в базу, если его ещё нет.

    На этом этапе раса ещё не выбрана, поэтому статы временные.
    Потом при выборе расы они будут пересчитаны.
    """
    db = connect()
    cursor = db.cursor()

    # Проверяем, есть ли уже такой игрок
    cursor.execute("SELECT id FROM players WHERE tg_id = ?", (tg_id,))
    existing = cursor.fetchone()

    if existing is not None:
        db.close()
        return

    # Базовые стартовые значения прогресса
    level = 1
    exp = 0
    exp_to_next = get_exp_to_next_for_level(level)

    # ВРЕМЕННЫЕ статы до выбора расы
    max_hp = 0
    hp = max_hp

    max_energy = 0
    energy = max_energy

    base_strength = 0
    base_intelligence = 0

    base_armor = 0
    base_magic_resist = 0

    armor = base_armor
    magic_resist = base_magic_resist

    free_points = 3
    cookies = 0
    race = None  # раса пока не выбрана
    rating = 0
    coins = 0

    cursor.execute("""
    INSERT INTO players (
        tg_id, username, race,
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
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tg_id, username, race,
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
    ))

    db.commit()
    db.close()


def get_player_by_tg_id(tg_id: int):
    """
    Получить данные игрока по его Telegram ID.

    Возвращает кортеж со всеми полями таблицы players или None, если игрока нет.
    """
    db = connect()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM players WHERE tg_id = ?", (tg_id,))
    player = cursor.fetchone()

    db.close()
    return player


def get_random_opponent(exclude_tg_id: int | None = None):
    """
    Вернуть случайного игрока для битвы.

    exclude_tg_id — кого исключить из выборки (обычно текущего игрока).
    Возвращает одну строку из таблицы players (кортеж) или None, если никого нет.
    """
    db = connect()
    cursor = db.cursor()

    if exclude_tg_id is None:
        cursor.execute("""
            SELECT * FROM players
            ORDER BY RANDOM()
            LIMIT 1
        """)
    else:
        cursor.execute("""
            SELECT * FROM players
            WHERE tg_id != ?
            ORDER BY RANDOM()
            LIMIT 1
        """, (exclude_tg_id,))

    row = cursor.fetchone()
    db.close()
    return row


def update_player(tg_id: int, **fields):
    """
    Универсальная функция для обновления полей игрока.

    Пример использования:
        update_player(123456789, hp=40, energy=10)
        update_player(123456789, level=2, free_points=5)
    """
    if not fields:
        return

    db = connect()
    cursor = db.cursor()

    set_parts = []
    values = []
    for column, value in fields.items():
        set_parts.append(f"{column} = ?")
        values.append(value)

    set_clause = ", ".join(set_parts)
    values.append(tg_id)

    query = f"UPDATE players SET {set_clause} WHERE tg_id = ?"
    cursor.execute(query, tuple(values))

    db.commit()
    db.close()


def set_race_for_player(tg_id: int, race_key: str) -> bool:
    """
    Установить расу игроку и задать стартовые статы согласно расе.

    race_key должен быть ключом из словаря RACES: "human", "orc", "animal", "raven_man".

    Возвращает:
        True  - если раса успешно установлена
        False - если такой расы нет или игрок не найден
    """
    race_data = RACES.get(race_key)
    if race_data is None:
        return False

    player = get_player_by_tg_id(tg_id)
    if player is None:
        return False

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

    max_hp = race_data["max_hp"]
    hp = max_hp

    max_energy = race_data["max_energy"]
    energy = max_energy

    base_strength = race_data["base_strength"]
    base_intelligence = race_data["base_intelligence"]

    base_armor = race_data["base_armor"]
    base_magic_resist = race_data["base_magic_resist"]

    armor = base_armor
    magic_resist = base_magic_resist

    update_player(
        tg_id,
        race=race_key,
        hp=hp,
        max_hp=max_hp,
        energy=energy,
        max_energy=max_energy,
        base_strength=base_strength,
        base_intelligence=base_intelligence,
        base_armor=base_armor,
        base_magic_resist=base_magic_resist,
        armor=armor,
        magic_resist=magic_resist,
    )

    return True


def add_exp(tg_id: int, amount: int) -> int:
    """
    Добавить игроку amount опыта и, если нужно, поднять уровень.
    Возвращает количество поднятых уровней.
    """
    if amount <= 0:
        return 0

    player = get_player_by_tg_id(tg_id)
    if player is None:
        return 0

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

    exp += amount
    max_level = 9
    level_ups = 0

    # Авто-левелап, пока хватает опыта
    while level < max_level and exp_to_next > 0 and exp >= exp_to_next:
        exp -= exp_to_next
        level += 1
        level_ups += 1

        # новая планка опыта
        exp_to_next = get_exp_to_next_for_level(level)

        # за уровень даём свободные очки, например, 3
        free_points += 3


    if level >= max_level:
        exp_to_next = 0  # дальше качаться нельзя (пока)

    update_player(
        tg_id,
        level=level,
        exp=exp,
        exp_to_next=exp_to_next,
        free_points=free_points
    )

    return level_ups


if __name__ == "__main__":
    # Тест: создаём таблицу, игрока, даём опыт, ставим расу
    create_tables()
    add_player(123456789, "TestPlayer")

    print("До выбора расы:", get_player_by_tg_id(123456789))
    set_race_for_player(123456789, "human")
    print("После выбора расы:", get_player_by_tg_id(123456789))

    ups = add_exp(123456789, 80)
    print("Поднято уровней:", ups)
    print("После опыта:", get_player_by_tg_id(123456789))


