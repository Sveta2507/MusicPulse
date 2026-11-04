"""Низькорівнева робота з SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Database:
    """Створює з'єднання і структуру локальної бази даних."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Відкриває з'єднання, підтверджує або відкочує транзакцію."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Створює таблиці виконавців, жанрів, зв'язків та метаданих."""
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS artists (
                    qid TEXT PRIMARY KEY,
                    name_uk TEXT NOT NULL,
                    name_en TEXT NOT NULL,
                    description TEXT NOT NULL,
                    artist_type TEXT NOT NULL CHECK (artist_type IN ('group', 'person')),
                    start_year INTEGER,
                    website TEXT,
                    image_url TEXT,
                    image_local TEXT,
                    wikidata_url TEXT NOT NULL,
                    spotify_url TEXT,
                    youtube_url TEXT,
                    retrieved_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS genres (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS artist_genres (
                    artist_qid TEXT NOT NULL REFERENCES artists(qid) ON DELETE CASCADE,
                    genre_id TEXT NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
                    PRIMARY KEY (artist_qid, genre_id)
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

