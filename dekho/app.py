from pathlib import Path

from flask import Flask, render_template

from .db import init_db, upsert_track
from .metadata import extract_track_id


def create_app() -> Flask:
    app = Flask(__name__)
    init_db()

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/scan")
    def scan() -> str:
        music_dir = Path("./music")
        scanned = 0
        stored = 0
        skipped = 0
        tracks = []

        if music_dir.exists():
            for file_path in sorted(music_dir.rglob("*.mp3")):
                scanned += 1
                track_id = extract_track_id(file_path)
                if not track_id:
                    skipped += 1
                    continue

                upsert_track(track_id=track_id, filepath=str(file_path.resolve()))
                stored += 1
                tracks.append({"track_id": track_id, "filepath": str(file_path)})

        return render_template(
            "scan_result.html",
            scanned=scanned,
            stored=stored,
            skipped=skipped,
            tracks=tracks,
        )

    return app
