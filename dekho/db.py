import sqlite3
from pathlib import Path

DB_PATH = Path("dekho.sqlite3")


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tracks (
                track_id TEXT PRIMARY KEY,
                filepath TEXT,
                title TEXT,
                artist TEXT,
                duration REAL,
                url TEXT,
                created TEXT,
                prompt TEXT,
                tags TEXT,
                negative_tags TEXT
            )
            """
        )


def upsert_track(track_id: str, filepath: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO tracks (track_id, filepath)
            VALUES (?, ?)
            ON CONFLICT(track_id) DO UPDATE SET filepath = excluded.filepath
            """,
            (track_id, filepath),
        )
