from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from .db import (
    get_all_tracks_file_data,
    get_track_ids_matching_all_labels,
    get_track_details,
    get_unknown_label_assignments,
    init_db,
    upsert_track_remote_data,
    upsert_track_user_data,
)
from .labels import get_label_catalog, normalize_label_keys
from .remote_metadata import fetch_suno_track_metadata
from .scan import run_scan


def create_app() -> Flask:
    app = Flask(__name__)
    init_db()

    @app.get("/")
    def index() -> str:
        unknown_labels = get_unknown_label_assignments()
        if unknown_labels:
            lines = [
                "ERROR: database contains label assignments that are missing from LABEL_CATALOG.",
                "Fix LABEL_CATALOG or remove/update these assignments:",
            ]
            for row in unknown_labels:
                lines.append(f"- track_id={row['track_id']} label_key={row['label_key']}")
            return ("\n".join(lines), 500, {"Content-Type": "text/plain; charset=utf-8"})

        music_root = Path("./music").resolve()
        label_catalog = get_label_catalog()
        tracks_in_music: list[dict[str, object]] = []

        for row in get_all_tracks_file_data():
            track_id = str(row["track_id"]) if row["track_id"] else ""
            filepath = str(row["filepath"]) if row["filepath"] else ""
            title = str(row["title"]) if row["title"] else ""
            title_new = str(row["title_new"]) if row["title_new"] else ""
            tags = str(row["tags"]) if row["tags"] else ""
            labels = row["labels"] if isinstance(row.get("labels"), list) else []
            label_keys = row["label_keys"] if isinstance(row.get("label_keys"), list) else []
            if not track_id or not filepath:
                continue

            path_in_db = Path(filepath)
            if path_in_db.is_absolute():
                continue
            resolved_path = (music_root / path_in_db).resolve()
            try:
                relative_path = resolved_path.relative_to(music_root)
            except ValueError:
                continue

            tracks_in_music.append(
                {
                    "track_id": track_id,
                    "filepath": relative_path.as_posix(),
                    "display_title": title_new or title or "Unknown",
                    "title": title or "",
                    "tags": tags,
                    "labels": labels,
                    "label_keys": label_keys,
                    "has_remote_tags": bool(tags.strip()),
                }
            )

        return render_template(
            "index.html",
            tracks=tracks_in_music,
            label_catalog=label_catalog,
        )

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

    @app.get("/api/labels")
    def label_catalog():
        return jsonify({"label_catalog": get_label_catalog()})

    @app.get("/api/tracks/<track_id>/audio")
    def track_audio(track_id: str):
        details = get_track_details(track_id)
        if details is None:
            return jsonify({"error": "Track not found"}), 404

        filepath = details.get("filepath")
        if not isinstance(filepath, str) or not filepath:
            return jsonify({"error": "Track filepath is missing."}), 400

        app_root = Path(".").resolve()
        music_root = (app_root / "music").resolve()
        candidate_path = Path(filepath)
        if candidate_path.is_absolute():
            return jsonify({"error": "Track filepath must be relative to app root."}), 400

        # DB filepaths are typically stored relative to ./music.
        resolved_path = (music_root / candidate_path).resolve()
        if not resolved_path.is_file():
            # Backward-compatible fallback for any rows stored relative to app root.
            resolved_path = (app_root / candidate_path).resolve()

        if not resolved_path.is_relative_to(app_root):
            return jsonify({"error": "Track filepath is outside app root."}), 400
        if not resolved_path.is_file():
            return jsonify({"error": "Track audio file not found."}), 404

        return send_file(resolved_path)

    @app.get("/api/tracks/<track_id>/image")
    def track_image(track_id: str):
        normalized_track_id = track_id.strip()
        if not normalized_track_id:
            return jsonify({"error": "Track ID is missing."}), 400

        app_root = Path(".").resolve()
        images_root = (app_root / "images").resolve()
        image_path = (
            images_root
            / normalized_track_id[0]
            / f"{normalized_track_id}.jpg"
        ).resolve()

        if not image_path.is_relative_to(images_root):
            return jsonify({"error": "Track image path is outside images root."}), 400
        if not image_path.is_file():
            return jsonify({"error": "Track image not found."}), 404

        return send_file(image_path)

    @app.get("/api/tracks/<track_id>/spectrogram")
    def track_spectrogram(track_id: str):
        normalized_track_id = track_id.strip()
        if not normalized_track_id:
            return jsonify({"error": "Track ID is missing."}), 400

        app_root = Path(".").resolve()
        spectrograms_root = (app_root / "spectrograms").resolve()
        spectrogram_path = (
            spectrograms_root
            / normalized_track_id[0]
            / f"{normalized_track_id}.png"
        ).resolve()

        if not spectrogram_path.is_relative_to(spectrograms_root):
            return jsonify({"error": "Track spectrogram path is outside spectrograms root."}), 400
        if not spectrogram_path.is_file():
            return jsonify({"error": "Track spectrogram not found."}), 404

        return send_file(spectrogram_path)

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
            prompt=remote_data.get("prompt"),
            tags=remote_data.get("tags"),
            negative_tags=remote_data.get("negative_tags"),
            has_cover_clip_id=bool(remote_data.get("has_cover_clip_id")),
            major_model_version=remote_data.get("major_model_version"),
            model_name=remote_data.get("model_name"),
            persona_name=remote_data.get("persona_name"),
        )

        updated_details = get_track_details(track_id)
        if updated_details is None:
            return jsonify({"error": "Track not found"}), 404
        return jsonify(updated_details)

    @app.post("/api/tracks/<track_id>/user-data")
    def save_track_user_data(track_id: str):
        details = get_track_details(track_id)
        if details is None:
            return jsonify({"error": "Track not found"}), 404

        payload = request.get_json(silent=True)
        if payload is None:
            payload = {}

        title_new = payload.get("title_new", "")
        notes = payload.get("notes", "")
        labels_raw = payload.get("labels", [])

        if not isinstance(title_new, str) or not isinstance(notes, str):
            return jsonify({"error": "title_new and notes must be strings."}), 400
        try:
            labels = normalize_label_keys(labels_raw)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        upsert_track_user_data(
            track_id=track_id,
            title_new=title_new,
            notes=notes,
            labels=labels,
        )

        updated_details = get_track_details(track_id)
        if updated_details is None:
            return jsonify({"error": "Track not found"}), 404
        return jsonify(updated_details)

    @app.post("/api/tracks/filter-by-labels")
    def filter_tracks_by_labels():
        payload = request.get_json(silent=True)
        if payload is None:
            payload = {}

        labels_raw = payload.get("labels", [])
        try:
            labels = normalize_label_keys(labels_raw)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        track_ids = get_track_ids_matching_all_labels(labels)
        return jsonify({"track_ids": track_ids})

    return app
