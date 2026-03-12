# Telegram-бот для отслеживания заявок клиентов

Готовый MVP-пет-проект на Python + aiogram 3 + SQLite.

## Что реализовано

- создание заявок через Telegram-бота;
- пошаговый сбор данных через FSM;
- валидация имени и телефона;
- хранение клиентов, заявок и истории изменений в SQLite;
- смена статусов заявки администратором;
- уведомления клиенту при изменении статуса;
- интеграция с внешним REST API;
- базовая устойчивость к параллельным запросам за счёт `asyncio`, `aiosqlite`, `WAL`-режима SQLite и сериализации операций записи через lock.

## Стек

- Python 3.11+
- aiogram 3
- SQLite
- aiohttp
- aiosqlite

## Структура

```text
app/
  config.py
  db.py
  keyboards.py
  main.py
  handlers/
    user.py
    admin.py
  services/
    validators.py
    external_api.py
```

## Запуск

1. Создай бота через BotFather и получи токен.
2. Скопируй `.env.example` в `.env`.
3. Заполни переменные окружения.
4. Установи зависимости:

```bash
pip install -r requirements.txt
```

5. Запусти бота:

```bash
python -m app.main
```

## Переменные окружения

```env
BOT_TOKEN=...
ADMIN_IDS=123456789
EXTERNAL_API_URL=https://httpbin.org/post
EXTERNAL_API_TIMEOUT=10
DB_PATH=bot.db
```

## Команды

Для пользователя:
- `/start`
- кнопка `📝 Новая заявка`
- кнопка `📂 Мои заявки`

Для администратора:
- `/applications` — показать последние заявки
- inline-кнопки: `В работе`, `Завершить`, `Отменить`, `Обновить`

## Схема БД

### clients
- id
- telegram_user_id
- telegram_username
- full_name
- phone
- created_at
- updated_at

### applications
- id
- client_id
- telegram_user_id
- full_name
- phone
- product
- comment
- status
- created_at
- updated_at

### application_history
- id
- application_id
- old_status
- new_status
- actor_user_id
- note
- payload_json
- created_at

## Идеи для улучшения

- заменить FSM storage на Redis для production;
- добавить FastAPI webhook-режим;
- сделать полноценную RBAC-модель;
- подключить Alembic или отдельный мигратор;
- добавить Docker и docker-compose;
- сделать экспорт заявок в CSV/Excel;
- покрыть репозиторий тестами.

## Почему выбран aiogram

aiogram — асинхронный фреймворк для Telegram Bot API, поддерживает FSM и быстро обновляется под новые версии Bot API. Telegram поддерживает два способа получения обновлений: long polling и webhooks. Для MVP здесь выбран polling, чтобы проект было проще поднять локально. citeturn272448search0turn272448search1turn272448search2turn272448search5
