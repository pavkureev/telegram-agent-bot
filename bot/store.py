from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContextItem:
    title: str
    content: str


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_state (
                    chat_id INTEGER PRIMARY KEY,
                    agent TEXT NOT NULL DEFAULT 'researcher'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS context_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get_agent(self, chat_id: int) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT agent FROM chat_state WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
            if row:
                return str(row["agent"])
            conn.execute(
                "INSERT INTO chat_state(chat_id, agent) VALUES(?, 'researcher')",
                (chat_id,),
            )
            return "researcher"

    def set_agent(self, chat_id: int, agent: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_state(chat_id, agent)
                VALUES(?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET agent = excluded.agent
                """,
                (chat_id, agent),
            )

    def add_context(self, chat_id: int, title: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO context_items(chat_id, title, content) VALUES(?, ?, ?)",
                (chat_id, title, content),
            )

    def get_context(self, chat_id: int) -> list[ContextItem]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT title, content
                FROM context_items
                WHERE chat_id = ?
                ORDER BY id ASC
                """,
                (chat_id,),
            ).fetchall()
        return [ContextItem(title=str(row["title"]), content=str(row["content"])) for row in rows]

    def clear_context(self, chat_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM context_items WHERE chat_id = ?", (chat_id,))

    def reset_chat(self, chat_id: int) -> None:
        self.clear_context(chat_id)
