import sqlite3


def ensure_schema(connection: sqlite3.Connection) -> None:
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
