from BOT.Предметы.db import create_tables, add_item

def fill_items(): # объявление функции, которая будет заниматься заполнением предметов.
    # Создаём таблицы (если ещё нет)
    create_tables() # создаёт таблицу items, если её нет. если таблица уже есть — ничего страшного, команда CREATE TABLE IF NOT EXISTS просто проигнорирует создание.

    # ==========================
    #  ОРУЖИЕ — ОБЫЧНОЕ
    # ==========================
    add_item("Ржавый клинок", "weapon", price=6, rarity="common",
             damage_min=1, damage_max=4)

    add_item("Двуручный меч", "weapon", price=12, rarity="common",
             damage_min=4, damage_max=8)

    add_item("Дрын", "weapon", price=5, rarity="common",
             damage_min=1, damage_max=6)

    add_item("Вилы", "weapon", price=7, rarity="common",
             damage_min=2, damage_max=7)

    add_item("Боевые кулаки", "weapon", price=3, rarity="common",
             damage_min=2, damage_max=3)

    add_item("Копьё охотника", "weapon", price=10, rarity="common",
             damage_min=3, damage_max=6)

    add_item("Лук лесника", "weapon", price=8, rarity="common",
             damage_min=1, damage_max=6)

    add_item("Топорики", "weapon", price=12, rarity="common",
             damage_min=2, damage_max=8)

    add_item("Топор дровосека", "weapon", price=10, rarity="common",
             damage_min=4, damage_max=7)

    add_item("Гладиус", "weapon", price=8, rarity="common",
             damage_min=3, damage_max=5)

    add_item("Олений рог", "weapon", price=6, rarity="common",
             damage_min=2, damage_max=5)

    add_item("Связка дротиков", "weapon", price=6, rarity="common",
             damage_min=1, damage_max=5)

    add_item("Каменный нож", "weapon", price=5, rarity="common",
             damage_min=1, damage_max=5)

    add_item("Кость", "weapon", price=5, rarity="common",
             damage_min=2, damage_max=5)

    add_item("Серп", "weapon", price=6, rarity="common",
             damage_min=1, damage_max=8)

    add_item("Кривой кинжал", "weapon", price=10, rarity="common",
             damage_min=3, damage_max=6)

    add_item("Сломанная алебарда", "weapon", price=9, rarity="common",
             damage_min=3, damage_max=7)

    # ==========================
    #  ОРУЖИЕ — РЕДКОЕ
    # ==========================
    add_item("Моргенштерн", "weapon", price=25, rarity="rare",
             damage_min=7, damage_max=11)

    add_item("Цепь наказанного", "weapon", price=22, rarity="rare",
             damage_min=4, damage_max=12)

    add_item("Двойной клинок", "weapon", price=30, rarity="rare",
             damage_min=8, damage_max=12)

    add_item("Трезубец", "weapon", price=35, rarity="rare",
             damage_min=9, damage_max=13)

    add_item("Арбалет", "weapon", price=40, rarity="rare",
             damage_min=5, damage_max=14)

    add_item("Двуручный боевой топор", "weapon", price=45, rarity="rare",
             damage_min=10, damage_max=14)

    add_item("Алебарда", "weapon", price=32, rarity="rare",
             damage_min=8, damage_max=14)

    add_item("Секира", "weapon", price=36, rarity="rare",
             damage_min=9, damage_max=15)

    add_item("Древний молот", "weapon", price=40, rarity="rare",
             damage_min=11, damage_max=13)

    add_item("Дубина огра", "weapon", price=38, rarity="rare",
             damage_min=5, damage_max=16)

    add_item("Булава", "weapon", price=34, rarity="rare",
             damage_min=7, damage_max=13)

    add_item("Вампирский кинжал", "weapon", price=30, rarity="rare",
             damage_min=6, damage_max=11)

    add_item("Шипованные кулаки", "weapon", price=33, rarity="rare",
             damage_min=8, damage_max=13)

    # ==========================
    #  ОРУЖИЕ — ЭПИЧЕСКОЕ
    # ==========================
    add_item("Рубила Waaagh", "weapon", price=120, rarity="epic",
             damage_min=15, damage_max=21)

    add_item("Кольемёт", "weapon", price=80, rarity="epic",
             damage_min=12, damage_max=17)

    add_item("Костяной тамогавк", "weapon", price=90, rarity="epic",
             damage_min=14, damage_max=19)

    add_item("Эльфийский меч", "weapon", price=100, rarity="epic",
             damage_min=13, damage_max=18)

    add_item("Рука короля скелетов", "weapon", price=110, rarity="epic",
             damage_min=16, damage_max=20)

    add_item("Молот Судьи", "weapon", price=115, rarity="epic",
             damage_min=14, damage_max=22)

    add_item("Алый рассекатель", "weapon", price=95, rarity="epic",
             damage_min=16, damage_max=18)

    # ==========================
    #  БРОНЯ — ОБЫЧНАЯ
    # ==========================
    add_item("Рваные тряпки", "armor", price=3, rarity="common",
             phys_armor_min=0, phys_armor_max=1,
             magic_def_min=0, magic_def_max=0)

    add_item("Кожанка", "armor", price=8, rarity="common",
             phys_armor_min=1, phys_armor_max=2,
             magic_def_min=0, magic_def_max=0)

    add_item("Бочка", "armor", price=10, rarity="common",
             phys_armor_min=1, phys_armor_max=3,
             magic_def_min=0, magic_def_max=0)

    # ==========================
    #  БРОНЯ — РЕДКАЯ
    # ==========================
    add_item("Ржавая кираса", "armor", price=20, rarity="rare",
             phys_armor_min=2, phys_armor_max=4,
             magic_def_min=0, magic_def_max=0)

    add_item("Бронзовый доспех", "armor", price=30, rarity="rare",
             phys_armor_min=3, phys_armor_max=5,
             magic_def_min=1, magic_def_max=2)

    add_item("Кольчуга", "armor", price=28, rarity="rare",
             phys_armor_min=3, phys_armor_max=4,
             magic_def_min=0, magic_def_max=0)

    add_item("Балахон", "armor", price=22, rarity="rare",
             phys_armor_min=0, phys_armor_max=1,
             magic_def_min=3, magic_def_max=4)

    # ==========================
    #  БРОНЯ — ЭПИЧЕСКАЯ
    # ==========================
    add_item("Балахон оракула", "armor", price=55, rarity="epic",
             phys_armor_min=2, phys_armor_max=4,
             magic_def_min=6, magic_def_max=8)

    add_item("Титановый доспех", "armor", price=90, rarity="epic",
             phys_armor_min=8, phys_armor_max=11,
             magic_def_min=0, magic_def_max=0)

    add_item("Мантия скверны", "armor", price=80, rarity="epic",
             phys_armor_min=3, phys_armor_max=4,
             magic_def_min=5, magic_def_max=6)

    add_item("Бочка из морёного дуба", "armor", price=60, rarity="epic",
             phys_armor_min=7, phys_armor_max=9,
             magic_def_min=1, magic_def_max=2)

    # ==========================
    #  МАГИЧЕСКИЕ КНИГИ
    # ==========================

    # Боевые книги (урон)
    add_item("Книга тьмы", "book", price=80,
             damage_min=9, damage_max=15)

    # Лечащие книги (проценты)
    add_item("Книга света", "book", price=70,
             heal_percent=20)

    # ==========================
    #  ЗЕЛЬЯ ИСЦЕЛЕНИЯ
    # ==========================
    add_item("Ампула здоровья", "potion", price=3,
             heal_min=2, heal_max=3)

    add_item("Склянка исцеления", "potion", price=6,
             heal_min=5, heal_max=10)

    add_item("Бутылка снадобья", "potion", price=20,
             heal_percent=50)

    # ==========================
    #  АРТЕФАКТЫ (постоянные бонусы)
    # ==========================
    add_item("Глаз провидца", "artifact", price=150,
             bonus_hp=3)

    add_item("Черепушка короля скелетов", "artifact", price=180,
             bonus_phys_armor=5)

    add_item("Вино хоббитов", "artifact", price=200,
             bonus_strength=4)

    add_item("Книга древних", "artifact", price=220,
             bonus_intellect=3)

    add_item("Дама крести", "artifact", price=250,
             bonus_magic_resist=5)

    add_item("Амулет неуязвимости", "artifact", price=400,
             bonus_magic_resist=5, bonus_phys_armor=5)

    add_item("Сердце Ветрокрыла", "artifact", price=350,
             bonus_energy=20)


if __name__ == "__main__": # означает: «если этот файл запущен напрямую, а не импортирован как модуль».   если ты сделаешь python fill_items.py → условие выполнится, и код внутри запустится. если ты где-то в другом файле напишешь: import fill_items — то fill_items() не запустится сам, только функции будут доступны.
    fill_items()
    print("База предметов успешно заполнена!")