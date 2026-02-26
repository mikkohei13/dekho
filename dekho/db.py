import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .labels import get_allowed_label_keys, get_label_catalog, iter_label_definitions

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
                has_cover_clip_id INTEGER NOT NULL DEFAULT 0,
                major_model_version TEXT,
                model_name TEXT,
                persona_name TEXT,
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS label_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                label TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS track_user_data_labels (
                track_id TEXT NOT NULL,
                label_id INTEGER NOT NULL,
                PRIMARY KEY (track_id, label_id),
                FOREIGN KEY (track_id) REFERENCES track_user_data(track_id),
                FOREIGN KEY (label_id) REFERENCES label_definitions(id)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_track_user_data_labels_label_id_track_id
            ON track_user_data_labels (label_id, track_id)
            """
        )
        _seed_label_definitions(connection)


def _seed_label_definitions(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT INTO label_definitions (key, category, label)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            category = excluded.category,
            label = excluded.label
        """,
        list(iter_label_definitions()),
    )


def _get_label_ids_for_keys(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT id, key
        FROM label_definitions
        """
    ).fetchall()
    return {str(row[1]): int(row[0]) for row in rows}


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


def get_all_tracks_file_data() -> list[dict[str, object]]:
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT tfd.track_id, tfd.filepath, tfd.title, tud.title_new, trd.tags
            FROM tracks_file_data AS tfd
            LEFT JOIN track_user_data AS tud ON tud.track_id = tfd.track_id
            LEFT JOIN track_remote_data AS trd ON trd.track_id = tfd.track_id
            ORDER BY tfd.date_created DESC, tfd.filepath COLLATE NOCASE ASC
            """
        ).fetchall()
        label_rows = connection.execute(
            """
            SELECT tul.track_id, ld.key, ld.label
            FROM track_user_data_labels AS tul
            JOIN label_definitions AS ld ON ld.id = tul.label_id
            ORDER BY ld.category, ld.label
            """
        ).fetchall()

    labels_by_track_id: dict[str, list[str]] = {}
    label_keys_by_track_id: dict[str, list[str]] = {}
    for label_row in label_rows:
        track_id = str(label_row[0])
        label_key = str(label_row[1])
        label = str(label_row[2])
        label_keys_by_track_id.setdefault(track_id, []).append(label_key)
        labels_by_track_id.setdefault(track_id, []).append(label)

    return [
        {
            "track_id": row[0],
            "filepath": row[1],
            "title": row[2],
            "title_new": row[3],
            "tags": row[4],
            "label_keys": label_keys_by_track_id.get(str(row[0]), []),
            "labels": labels_by_track_id.get(str(row[0]), []),
        }
        for row in rows
    ]


def get_track_details(track_id: str) -> dict[str, object] | None:
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
                trd.has_cover_clip_id,
                trd.major_model_version,
                trd.model_name,
                trd.persona_name,
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
        "has_cover_clip_id": bool(row[9]),
        "major_model_version": row[10],
        "model_name": row[11],
        "persona_name": row[12],
        "title_new": row[13],
        "notes": row[14],
        "labels": get_track_label_keys(track_id),
        "label_catalog": get_label_catalog(),
    }


def get_track_remote_data(track_id: str) -> dict[str, str | bool | None] | None:
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                track_id,
                prompt,
                tags,
                negative_tags,
                has_cover_clip_id,
                major_model_version,
                model_name,
                persona_name
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
        "has_cover_clip_id": bool(row[4]),
        "major_model_version": row[5],
        "model_name": row[6],
        "persona_name": row[7],
    }


def upsert_track_remote_data(
    track_id: str,
    prompt: str | None,
    tags: str | None,
    negative_tags: str | None,
    has_cover_clip_id: bool | None,
    major_model_version: str | None,
    model_name: str | None,
    persona_name: str | None,
) -> None:
    init_db()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO track_remote_data (
                track_id,
                prompt,
                tags,
                negative_tags,
                has_cover_clip_id,
                major_model_version,
                model_name,
                persona_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(track_id) DO UPDATE SET
                prompt = excluded.prompt,
                tags = excluded.tags,
                negative_tags = excluded.negative_tags,
                has_cover_clip_id = excluded.has_cover_clip_id,
                major_model_version = excluded.major_model_version,
                model_name = excluded.model_name,
                persona_name = excluded.persona_name
            """,
            (
                track_id,
                prompt,
                tags,
                negative_tags,
                1 if has_cover_clip_id else 0,
                major_model_version,
                model_name,
                persona_name,
            ),
        )


def upsert_track_user_data(
    track_id: str,
    title_new: str,
    notes: str,
    labels: list[str] | None = None,
) -> None:
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
        if labels is not None:
            replace_track_labels(connection=connection, track_id=track_id, labels=labels)


def get_track_label_keys(track_id: str) -> list[str]:
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT ld.key
            FROM track_user_data_labels AS tul
            JOIN label_definitions AS ld ON ld.id = tul.label_id
            WHERE tul.track_id = ?
            ORDER BY ld.key
            """,
            (track_id,),
        ).fetchall()
    return [str(row[0]) for row in rows]


def replace_track_labels(
    connection: sqlite3.Connection,
    track_id: str,
    labels: list[str],
) -> None:
    connection.execute(
        """
        DELETE FROM track_user_data_labels
        WHERE track_id = ?
        """,
        (track_id,),
    )
    if not labels:
        return

    label_ids_by_key = _get_label_ids_for_keys(connection)
    rows_to_insert: list[tuple[str, int]] = []
    for label in labels:
        label_id = label_ids_by_key.get(label)
        if label_id is None:
            raise ValueError(f"Unknown label key: {label}")
        rows_to_insert.append((track_id, label_id))

    connection.executemany(
        """
        INSERT INTO track_user_data_labels (track_id, label_id)
        VALUES (?, ?)
        """,
        rows_to_insert,
    )


def get_track_ids_matching_all_labels(labels: list[str]) -> list[str]:
    init_db()
    normalized_labels = list(dict.fromkeys(labels))
    if not normalized_labels:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT track_id
                FROM tracks_file_data
                ORDER BY filepath
                """
            ).fetchall()
        return [str(row[0]) for row in rows]

    where_conditions = ", ".join(["?"] * len(normalized_labels))
    params: list[str | int] = [*normalized_labels]
    params.append(len(normalized_labels))

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT tfd.track_id
            FROM tracks_file_data AS tfd
            JOIN track_user_data_labels AS tul ON tul.track_id = tfd.track_id
            JOIN label_definitions AS ld ON ld.id = tul.label_id
            WHERE ld.key IN ({where_conditions})
            GROUP BY tfd.track_id
            HAVING COUNT(DISTINCT ld.id) = ?
            ORDER BY tfd.filepath
            """,
            params,
        ).fetchall()
    return [str(row[0]) for row in rows]


def get_unknown_label_assignments() -> list[dict[str, str]]:
    init_db()
    allowed = get_allowed_label_keys()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT tul.track_id, ld.key
            FROM track_user_data_labels AS tul
            JOIN label_definitions AS ld ON ld.id = tul.label_id
            ORDER BY tul.track_id, ld.key
            """
        ).fetchall()
    return [
        {"track_id": str(row[0]), "label_key": str(row[1])}
        for row in rows
        if str(row[1]) not in allowed
    ]
