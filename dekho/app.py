from pathlib import Path

from flask import Flask, render_template

from .db import get_all_tracks_file_data, init_db
from .scan import run_scan


def create_app() -> Flask:
    app = Flask(__name__)
    init_db()

    @app.get("/")
    def index() -> str:
        music_root = Path("./music").resolve()
        tracks_in_music: list[dict[str, str]] = []

        for row in get_all_tracks_file_data():
            track_id = str(row["track_id"]) if row["track_id"] else ""
            filepath = str(row["filepath"]) if row["filepath"] else ""
            if not track_id or not filepath:
                continue

            resolved_path = Path(filepath).resolve()
            try:
                relative_path = resolved_path.relative_to(music_root)
            except ValueError:
                continue

            tracks_in_music.append(
                {
                    "track_id": track_id,
                    "filepath": relative_path.as_posix(),
                }
            )

        tracks_in_music.sort(key=lambda track: track["filepath"].casefold())
        return render_template("index.html", tracks=tracks_in_music)

    @app.get("/scan")
    def scan() -> str:
        scan_result = run_scan(Path("./music"))
        return render_template("scan_result.html", **scan_result)

    return app
