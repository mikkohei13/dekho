import sqlite3
from pathlib import Path

DB_PATH = Path("dekho.sqlite3")


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tracks_file_data (
                track_id TEXT PRIMARY KEY,
                filepath TEXT,
                title TEXT,
                artist TEXT,
                duration REAL,
                url TEXT,
                date_created TEXT,
                date_added TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS track_remote_data (
                track_id TEXT PRIMARY KEY,
                prompt TEXT,
                tags TEXT,
                negative_tags TEXT,
                FOREIGN KEY (track_id) REFERENCES tracks_file_data(track_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS track_user_data (
                track_id TEXT PRIMARY KEY,
                notes TEXT,
                title_new TEXT,
                FOREIGN KEY (track_id) REFERENCES tracks_file_data(track_id)
            )
            """
        )


def upsert_track(track_id: str, filepath: str) -> None:
    # Ensures DB/tables are recreated if file was deleted while server is running.
    init_db()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO tracks_file_data (track_id, filepath)
            VALUES (?, ?)
            ON CONFLICT(track_id) DO UPDATE SET filepath = excluded.filepath
            """,
            (track_id, filepath),
        )


def get_all_tracks_file_data() -> list[dict[str, str | None]]:
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT track_id, filepath
            FROM tracks_file_data
            """
        ).fetchall()

    return [{"track_id": row[0], "filepath": row[1]} for row in rows]
