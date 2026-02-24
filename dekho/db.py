import sqlite3
from datetime import UTC, datetime
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


def upsert_track(
    track_id: str,
    filepath: str,
    title: str | None = None,
    artist: str | None = None,
    duration: float | None = None,
    url: str | None = None,
    date_created: str | None = None,
) -> None:
    # Ensures DB/tables are recreated if file was deleted while server is running.
    init_db()
    date_added = datetime.now(UTC).isoformat()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO tracks_file_data (
                track_id, filepath, title, artist, duration, url, date_created, date_added
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(track_id) DO UPDATE SET
                filepath = excluded.filepath,
                title = excluded.title,
                artist = excluded.artist,
                duration = excluded.duration,
                url = excluded.url,
                date_created = excluded.date_created
            """,
            (track_id, filepath, title, artist, duration, url, date_created, date_added),
        )


def get_all_tracks_file_data() -> list[dict[str, str | None]]:
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT tfd.track_id, tfd.filepath, tfd.title, tud.title_new
            FROM tracks_file_data AS tfd
            LEFT JOIN track_user_data AS tud ON tud.track_id = tfd.track_id
            """
        ).fetchall()

    return [
        {
            "track_id": row[0],
            "filepath": row[1],
            "title": row[2],
            "title_new": row[3],
        }
        for row in rows
    ]


def get_track_details(track_id: str) -> dict[str, str | float | None] | None:
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                tfd.track_id,
                tfd.title,
                tfd.url,
                tfd.filepath,
                tfd.duration,
                tfd.date_created,
                trd.prompt,
                trd.tags,
                trd.negative_tags,
                tud.title_new,
                tud.notes
            FROM tracks_file_data AS tfd
            LEFT JOIN track_remote_data AS trd ON trd.track_id = tfd.track_id
            LEFT JOIN track_user_data AS tud ON tud.track_id = tfd.track_id
            WHERE tfd.track_id = ?
            """,
            (track_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "track_id": row[0],
        "title": row[1],
        "url": row[2],
        "filepath": row[3],
        "duration": row[4],
        "date_created": row[5],
        "prompt": row[6],
        "tags": row[7],
        "negative_tags": row[8],
        "title_new": row[9],
        "notes": row[10],
    }


def get_track_remote_data(track_id: str) -> dict[str, str | None] | None:
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT track_id, prompt, tags, negative_tags
            FROM track_remote_data
            WHERE track_id = ?
            """,
            (track_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "track_id": row[0],
        "prompt": row[1],
        "tags": row[2],
        "negative_tags": row[3],
    }


def upsert_track_remote_data(
    track_id: str, prompt: str, tags: str, negative_tags: str
) -> None:
    init_db()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO track_remote_data (track_id, prompt, tags, negative_tags)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(track_id) DO UPDATE SET
                prompt = excluded.prompt,
                tags = excluded.tags,
                negative_tags = excluded.negative_tags
            """,
            (track_id, prompt, tags, negative_tags),
        )


def upsert_track_user_data(track_id: str, title_new: str, notes: str) -> None:
    init_db()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO track_user_data (track_id, title_new, notes)
            VALUES (?, ?, ?)
            ON CONFLICT(track_id) DO UPDATE SET
                title_new = excluded.title_new,
                notes = excluded.notes
            """,
            (track_id, title_new, notes),
        )
