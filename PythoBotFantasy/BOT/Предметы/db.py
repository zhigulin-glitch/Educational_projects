import sqlite3
DB_NAME = 'test.db'

def connect():   # Каждый раз, когда ты хочешь поработать с базой (создать таблицу, добавить предмет, прочитать предметы), ты вызываешь connect().
    #Подключение к базе данных.
    return sqlite3.connect(DB_NAME)

def create_tables():
        # Создание таблицы предметов, если её ещё нет.
    db = connect()
    cursor = db.cursor()
                #id INTEGER PRIMARY KEY AUTOINCREMENT                                                    name TEXT NOT NULL  и  type TEXT NOT NULL                                                  type — тип предмета:
                # Ниже в таблице:                                                               name — название предмета, например "Ржавый клинок".       "weapon" — оружие  "armor" — броня "book" — магическая книга "potion" — зелье "artifact" — артефакт
                # id — уникальный номер предмета.                                               TEXT — строка.
                # INTEGER — тип данных: целое число.                                            NOT NULL — поле обязательно, нельзя оставить пустым.
                # PRIMARY KEY — главный ключ (уникальный идентификатор строки).
                # AUTOINCREMENT — значение увеличивается автоматически: 1, 2, 3, 4…
                # Тебе не нужно вручную задавать id при добавлении предмета.

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        -- Основная информация
        name TEXT NOT NULL,      -- Название предмета
        type TEXT NOT NULL,      -- weapon, armor, book, potion, artifact
        rarity TEXT,             -- common, rare, epic (может быть NULL)
        price INTEGER NOT NULL,  -- Цена в золоте

        -- Оружие и боевые книги
        damage_min INTEGER,      -- Минимальный урон
        damage_max INTEGER,      -- Максимальный урон

        -- Броня
        phys_armor_min INTEGER,  -- Физ. броня (минимум)
        phys_armor_max INTEGER,  -- Физ. броня (максимум)
        magic_def_min INTEGER,   -- Маг. защита (минимум)
        magic_def_max INTEGER,   -- Маг. защита (максимум)

        -- Зелья (лечат сразу)
        heal_min INTEGER,        -- Лечение минимум (в HP)
        heal_max INTEGER,        -- Лечение максимум (в HP)

        -- Книги (умения, например "лечит 20% HP")
        heal_percent INTEGER,    -- На сколько % лечит (для Книги света и т.п.)

        -- Артефакты (постоянные бонусы)
        bonus_hp INTEGER,            -- +HP навсегда
        bonus_energy INTEGER,        -- +энергия навсегда
        bonus_strength INTEGER,      -- +сила
        bonus_intellect INTEGER,     -- +интеллект
        bonus_phys_armor INTEGER,    -- +физ. броня
        bonus_magic_resist INTEGER   -- +маг. сопротивление
    )
    """)

    db.commit()
    db.close()

def add_item(
    name,
    type_,
    price,
    rarity=None,
    damage_min=None, damage_max=None,
    phys_armor_min=None, phys_armor_max=None,
    magic_def_min=None, magic_def_max=None,
    heal_min=None, heal_max=None,
    heal_percent=None,
    bonus_hp=None,
    bonus_energy=None,
    bonus_strength=None,
    bonus_intellect=None,
    bonus_phys_armor=None,
    bonus_magic_resist=None
):

    db = connect() #Подключаемся к базе.
    cursor = db.cursor() #Создаём курсор. #Это значения, которые встанут на место ? по порядку.

                                    # INSERT INTO items - Мы говорим базе: "Добавь новую строку в таблицу items".   Вопросительные знаки ? — плейсхолдеры (места для значений). Они защищают от SQL-инъекций и удобны для подстановки переменных.
    cursor.execute("""
        INSERT INTO items (
            name, type, rarity, price,
            damage_min, damage_max,
            phys_armor_min, phys_armor_max,
            magic_def_min, magic_def_max,
            heal_min, heal_max,
            heal_percent,
            bonus_hp, bonus_energy, bonus_strength,
            bonus_intellect, bonus_phys_armor, bonus_magic_resist
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
        name, type_, rarity, price,
        damage_min, damage_max,                                    #Это значения, которые встанут на место ? по порядку.
        phys_armor_min, phys_armor_max,
        magic_def_min, magic_def_max,
        heal_min, heal_max,
        heal_percent,
        bonus_hp, bonus_energy, bonus_strength,
        bonus_intellect, bonus_phys_armor, bonus_magic_resist
    ))

    db.commit() # сохраняет изменения в базу
    db.close() # закрывает подключение. всегда закрывать базу после работы, чтобы не висели лишние подключения и не было блокировок файла.

def get_all_items():

    #Вернуть список всех предметов.
    #Возвращает список кортежей.
    #Каждый кортеж = одна строка таблицы items.

    db = connect() #db = connect() — вызываем нашу функцию connect() (из db.py), чтобы подключиться к game.db.  db — объект соединения с базой данных.
    cursor = db.cursor() # это объект, через который мы выполняем SQL-команды (SELECT, INSERT, UPDATE, и т.д.).

    cursor.execute("SELECT * FROM items") # cursor.execute(...) — выполнить SQL-запрос. SELECT — команда чтения данных. * — означает «все поля». FROM items — из таблицы items.
    items = cursor.fetchall() #— забирает все результаты последнего SELECT.

    db.close() # закрываем соединение с базой.
    return items # возвращаем список предметов в то место, где вызвали get_all_items().


def get_items_by_type(type_):

    #Вернуть все предметы определённого типа.
    #type_: 'weapon', 'armor', 'book', 'potion', 'artifact'

    db = connect()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM items WHERE type = ?", (type_,))
    items = cursor.fetchall()

    db.close()
    return items


def get_item_by_id(item_id):

    #Вернуть один предмет по его id.
    #Удобно, когда игрок выбирает предмет из списка.

    db = connect()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,)) # SELECT * FROM items — берём всё. WHERE id = ? — фильтр: id должен быть равен тому, что мы передали. (item_id,) — снова кортеж из одного элемента.
    item = cursor.fetchone()

    db.close()
    return item