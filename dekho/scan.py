from __future__ import annotations

import os
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import mutagen

from .db import DB_PATH, get_all_tracks_file_data, upsert_track
from .metadata import extract_file_metadata


@dataclass(frozen=True)
class TrackFile:
    track_id: str
    filepath: Path
    filepath_resolved: Path
    filepath_compare_key: str


def normalize_compare_key(path: Path | str, base_dir: Path | None = None) -> str:
    candidate_path = Path(path)
    if not candidate_path.is_absolute() and base_dir is not None:
        candidate_path = base_dir / candidate_path
    normalized = os.path.normpath(str(candidate_path.resolve()))
    return os.path.normcase(normalized).casefold()


def to_storage_filepath(path: Path, music_root: Path) -> str:
    return path.resolve().relative_to(music_root).as_posix()


def move_to_duplicates_folder(source_path: Path, duplicates_dir: Path) -> Path:
    duplicates_dir.mkdir(parents=True, exist_ok=True)

    base_name = source_path.name
    destination = duplicates_dir / base_name
    suffix = 1
    while destination.exists():
        destination = duplicates_dir / f"{source_path.stem}_{suffix}{source_path.suffix}"
        suffix += 1

    source_path.rename(destination)
    return destination


def _pick_canonical_file(
    track_files: list[TrackFile], db_filepath: str | None, music_root: Path
) -> TrackFile:
    if db_filepath:
        db_compare_key = normalize_compare_key(db_filepath, base_dir=music_root)
        for candidate in track_files:
            if candidate.filepath_compare_key == db_compare_key:
                return candidate
    return track_files[0]


def backup_database_if_exists() -> str | None:
    source_db = DB_PATH
    if not source_db.exists():
        return None

    backups_dir = Path("./database_backups")
    backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = backups_dir / f"{source_db.stem}_{timestamp}{source_db.suffix}"

    shutil.copy2(source_db, destination)
    return str(destination)


def export_track_cover_image(track_id: str, file_path: Path) -> None:
    if not track_id:
        return

    try:
        audio = mutagen.File(file_path)
    except Exception:
        return

    if audio is None or not audio.tags:
        return

    cover_bytes: bytes | None = None
    for key, value in audio.tags.items():
        if not str(key).startswith("APIC"):
            continue

        mime = getattr(value, "mime", "")
        if not isinstance(mime, str) or mime.casefold() != "image/jpeg":
            continue

        data = getattr(value, "data", None)
        if isinstance(data, (bytes, bytearray)) and data:
            cover_bytes = bytes(data)
            break

    if not cover_bytes:
        return

    cover_subdir = Path("./images") / track_id[0]
    cover_subdir.mkdir(parents=True, exist_ok=True)
    (cover_subdir / f"{track_id}.jpg").write_bytes(cover_bytes)


def run_scan(music_dir: Path) -> dict[str, object]:
    database_backup_path = backup_database_if_exists()
    music_root = music_dir.resolve()
    duplicates_dir = Path("./music_duplicates")
    all_mp3_files: list[Path] = []
    if music_dir.exists():
        all_mp3_files = sorted(
            file_path
            for file_path in music_dir.rglob("*")
            if file_path.is_file() and file_path.suffix.casefold() == ".mp3"
        )

    grouped_track_files: dict[str, list[TrackFile]] = defaultdict(list)
    scanned_tracks: list[dict[str, str]] = []
    missing_identifier_files: list[dict[str, str]] = []
    all_music_path_keys = {normalize_compare_key(path) for path in all_mp3_files}

    for file_path in all_mp3_files:
        file_metadata = extract_file_metadata(file_path)
        track_id = file_metadata.get("track_id")
        if not track_id:
            missing_identifier_files.append(
                {"filepath": to_storage_filepath(file_path, music_root)}
            )
            continue

        resolved = file_path.resolve()
        grouped_track_files[track_id].append(
            TrackFile(
                track_id=track_id,
                filepath=file_path,
                filepath_resolved=resolved,
                filepath_compare_key=normalize_compare_key(resolved),
            )
        )

    db_rows = get_all_tracks_file_data()
    db_by_id = {str(row["track_id"]): row for row in db_rows if row["track_id"]}

    duplicate_warnings: list[dict[str, str]] = []
    renamed_path_updates: list[dict[str, str]] = []
    missing_from_folder: list[dict[str, str]] = []

    scanned_track_ids: set[str] = set()

    for track_id in sorted(grouped_track_files):
        candidates = grouped_track_files[track_id]
        db_filepath = db_by_id.get(track_id, {}).get("filepath")
        canonical_file = _pick_canonical_file(candidates, db_filepath, music_root)
        scanned_track_ids.add(track_id)

        for candidate in candidates:
            if candidate == canonical_file:
                continue
            moved_to = move_to_duplicates_folder(candidate.filepath, duplicates_dir)
            duplicate_warnings.append(
                {
                    "track_id": track_id,
                    "kept_filepath": str(canonical_file.filepath),
                    "duplicate_filepath": str(candidate.filepath),
                    "moved_to": str(moved_to),
                }
            )

        if (
            db_filepath
            and normalize_compare_key(db_filepath, base_dir=music_root)
            != canonical_file.filepath_compare_key
        ):
            renamed_path_updates.append(
                {
                    "track_id": track_id,
                    "old_filepath": str(db_filepath),
                    "new_filepath": to_storage_filepath(
                        canonical_file.filepath_resolved, music_root
                    ),
                }
            )

        canonical_metadata = extract_file_metadata(canonical_file.filepath_resolved)
        upsert_track(
            track_id=track_id,
            filepath=to_storage_filepath(canonical_file.filepath_resolved, music_root),
            title=canonical_metadata.get("title"),
            artist=canonical_metadata.get("artist"),
            duration=canonical_metadata.get("duration"),
            url=canonical_metadata.get("url"),
            date_created=canonical_metadata.get("date_created"),
        )
        try:
            export_track_cover_image(track_id, canonical_file.filepath_resolved)
        except Exception:
            # Cover extraction should not break the scan pipeline.
            pass
        scanned_tracks.append(
            {
                "track_id": track_id,
                "filepath": to_storage_filepath(canonical_file.filepath, music_root),
                "scan_time_utc": datetime.now(UTC).isoformat(),
            }
        )

    db_rows_after_scan = get_all_tracks_file_data()
    for row in db_rows_after_scan:
        row_track_id = str(row["track_id"]) if row["track_id"] else ""
        row_filepath = str(row["filepath"]) if row["filepath"] else ""
        if not row_track_id:
            continue

        row_path_key = (
            normalize_compare_key(row_filepath, base_dir=music_root)
            if row_filepath
            else None
        )
        has_id_in_scan = row_track_id in scanned_track_ids
        has_path_in_scan = bool(row_path_key and row_path_key in all_music_path_keys)

        if has_id_in_scan and has_path_in_scan:
            continue

        missing_from_folder.append(
            {
                "track_id": row_track_id,
                "filepath": row_filepath,
                "missing_identifier": "yes" if not has_id_in_scan else "no",
                "missing_path": "yes" if not has_path_in_scan else "no",
            }
        )

    return {
        "database_backup_path": database_backup_path,
        "scanned": len(all_mp3_files),
        "stored": len(scanned_tracks),
        "skipped": len(missing_identifier_files),
        "tracks": scanned_tracks,
        "warnings_duplicates": duplicate_warnings,
        "warnings_renamed_path": renamed_path_updates,
        "warnings_missing_from_folder": missing_from_folder,
        "warnings_missing_identifier": missing_identifier_files,
    }
