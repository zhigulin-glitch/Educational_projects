import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import aiosqlite

UTC = timezone.utc


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ApplicationRow:
    id: int
    telegram_user_id: int
    telegram_username: str | None
    full_name: str
    phone: str
    product: str
    comment: str | None
    status: str
    created_at: str
    updated_at: str


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute('PRAGMA journal_mode=WAL;')
        await self.conn.execute('PRAGMA foreign_keys=ON;')
        await self.conn.execute('PRAGMA synchronous=NORMAL;')
        await self._init_schema()

    async def close(self) -> None:
        if self.conn is not None:
            await self.conn.close()

    async def _init_schema(self) -> None:
        assert self.conn is not None
        async with self._write_lock:
            await self.conn.executescript(
                '''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL UNIQUE,
                    telegram_username TEXT,
                    full_name TEXT,
                    phone TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    telegram_user_id INTEGER NOT NULL,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    product TEXT NOT NULL,
                    comment TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS application_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER NOT NULL,
                    old_status TEXT,
                    new_status TEXT NOT NULL,
                    actor_user_id INTEGER NOT NULL,
                    note TEXT,
                    payload_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
                CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(telegram_user_id);
                CREATE INDEX IF NOT EXISTS idx_history_application ON application_history(application_id);
                '''
            )
            await self.conn.commit()

    async def fetchone(self, query: str, params: Iterable[Any] = ()) -> aiosqlite.Row | None:
        assert self.conn is not None
        async with self.conn.execute(query, params) as cur:
            return await cur.fetchone()

    async def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[aiosqlite.Row]:
        assert self.conn is not None
        async with self.conn.execute(query, params) as cur:
            return await cur.fetchall()

    async def execute(self, query: str, params: Iterable[Any] = ()) -> int:
        assert self.conn is not None
        async with self._write_lock:
            cur = await self.conn.execute(query, params)
            await self.conn.commit()
            return cur.lastrowid

    async def execute_many(self, statements: list[tuple[str, tuple[Any, ...]]]) -> None:
        assert self.conn is not None
        async with self._write_lock:
            for query, params in statements:
                await self.conn.execute(query, params)
            await self.conn.commit()

    async def upsert_client(
        self,
        telegram_user_id: int,
        telegram_username: str | None,
        full_name: str,
        phone: str,
    ) -> int:
        ts = now_iso()
        existing = await self.fetchone(
            'SELECT id FROM clients WHERE telegram_user_id = ?',
            (telegram_user_id,),
        )
        if existing:
            await self.execute(
                '''
                UPDATE clients
                SET telegram_username = ?, full_name = ?, phone = ?, updated_at = ?
                WHERE telegram_user_id = ?
                ''',
                (telegram_username, full_name, phone, ts, telegram_user_id),
            )
            return int(existing['id'])

        return await self.execute(
            '''
            INSERT INTO clients (telegram_user_id, telegram_username, full_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (telegram_user_id, telegram_username, full_name, phone, ts, ts),
        )

    async def create_application(
        self,
        telegram_user_id: int,
        telegram_username: str | None,
        full_name: str,
        phone: str,
        product: str,
        comment: str | None,
    ) -> int:
        client_id = await self.upsert_client(telegram_user_id, telegram_username, full_name, phone)
        ts = now_iso()
        application_id = await self.execute(
            '''
            INSERT INTO applications (
                client_id, telegram_user_id, full_name, phone, product, comment, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?)
            ''',
            (client_id, telegram_user_id, full_name, phone, product, comment, ts, ts),
        )
        await self.add_history(
            application_id=application_id,
            old_status=None,
            new_status='new',
            actor_user_id=telegram_user_id,
            note='Заявка создана',
            payload={'product': product, 'comment': comment},
        )
        return application_id

    async def add_history(
        self,
        application_id: int,
        old_status: str | None,
        new_status: str,
        actor_user_id: int,
        note: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self.execute(
            '''
            INSERT INTO application_history (
                application_id, old_status, new_status, actor_user_id, note, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                application_id,
                old_status,
                new_status,
                actor_user_id,
                note,
                json.dumps(payload or {}, ensure_ascii=False),
                now_iso(),
            ),
        )

    async def update_status(self, application_id: int, new_status: str, actor_user_id: int, note: str | None = None) -> bool:
        row = await self.fetchone('SELECT status FROM applications WHERE id = ?', (application_id,))
        if row is None:
            return False
        old_status = row['status']
        await self.execute_many([
            (
                'UPDATE applications SET status = ?, updated_at = ? WHERE id = ?',
                (new_status, now_iso(), application_id),
            ),
            (
                '''
                INSERT INTO application_history (
                    application_id, old_status, new_status, actor_user_id, note, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (application_id, old_status, new_status, actor_user_id, note, json.dumps({}, ensure_ascii=False), now_iso()),
            ),
        ])
        return True

    async def get_application(self, application_id: int) -> ApplicationRow | None:
        row = await self.fetchone('SELECT * FROM applications WHERE id = ?', (application_id,))
        if row is None:
            return None
        return ApplicationRow(**dict(row))

    async def list_applications(self, limit: int = 20, status: str | None = None) -> list[ApplicationRow]:
        if status:
            rows = await self.fetchall(
                'SELECT * FROM applications WHERE status = ? ORDER BY id DESC LIMIT ?',
                (status, limit),
            )
        else:
            rows = await self.fetchall('SELECT * FROM applications ORDER BY id DESC LIMIT ?', (limit,))
        return [ApplicationRow(**dict(row)) for row in rows]

    async def get_history(self, application_id: int) -> list[aiosqlite.Row]:
        return await self.fetchall(
            'SELECT * FROM application_history WHERE application_id = ? ORDER BY id ASC',
            (application_id,),
        )
