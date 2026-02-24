from pathlib import Path

from flask import Flask, jsonify, render_template

from .db import (
    get_all_tracks_file_data,
    get_track_details,
    init_db,
    upsert_track_remote_data,
)
from .remote_metadata import fetch_suno_track_metadata
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

    @app.get("/api/tracks/<track_id>")
    def track_details(track_id: str):
        details = get_track_details(track_id)
        if details is None:
            return jsonify({"error": "Track not found"}), 404
        return jsonify(details)

    @app.post("/api/tracks/<track_id>/remote-data")
    def fetch_track_remote_data(track_id: str):
        details = get_track_details(track_id)
        if details is None:
            return jsonify({"error": "Track not found"}), 404

        track_url = details.get("url")
        if not isinstance(track_url, str) or not track_url:
            return jsonify({"error": "Track URL is missing."}), 400

        try:
            remote_data = fetch_suno_track_metadata(track_url)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except Exception:
            return jsonify({"error": "Failed to fetch data from Suno."}), 502

        upsert_track_remote_data(
            track_id=track_id,
            prompt=remote_data["prompt"],
            tags=remote_data["tags"],
            negative_tags=remote_data["negative_tags"],
        )

        updated_details = get_track_details(track_id)
        if updated_details is None:
            return jsonify({"error": "Track not found"}), 404
        return jsonify(updated_details)

    return app
