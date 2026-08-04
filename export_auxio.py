"""Export playlist-labeled tracks for Auxio.

Usage:
    uv run export_auxio.py
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from collections import OrderedDict
from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1

DB_PATH = Path("dekho.sqlite3")
MUSIC_ROOT = Path("music")
OUTPUT_DIR = Path("export_music")
TRACKS_DIR_NAME = "Tracks"
PLAYLISTS_DIR_NAME = "Playlists"
ARTIST_NAME = "My Recordings"
ALBUM_NAME = "Unpublished Music"
FORBIDDEN_FILENAME_CHARS = str.maketrans("", "", r'/\:*?"<>|')


def normalize_music_relative_path(filepath: str) -> str:
    relative = filepath.lstrip("/")
    if relative.startswith("music/"):
        relative = relative[len("music/") :]
    return relative


def filesystem_safe_name(name: str) -> str:
    cleaned = name.translate(FORBIDDEN_FILENAME_CHARS)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


def allocate_unique_filenames(names: list[str]) -> dict[str, str]:
    """Map original names to unique filesystem-safe stems.

    Duplicate sanitized names get a stable numeric suffix: name, name-2, name-3, ...
    """
    allocated: dict[str, str] = {}
    used_lower: set[str] = set()

    for name in names:
        base = filesystem_safe_name(name) or "playlist"
        candidate = base
        suffix = 2
        while candidate.casefold() in used_lower:
            candidate = f"{base}-{suffix}"
            suffix += 1
        used_lower.add(candidate.casefold())
        allocated[name] = candidate

    return allocated


def stable_track_filename(track_id: str) -> str:
    safe_id = filesystem_safe_name(track_id) or "track"
    return f"{safe_id}.mp3"


def song_display_name(title: str | None, title_new: str | None, track_id: str) -> str:
    title_new_text = title_new.strip() if title_new else ""
    title_text = title.strip() if title else ""
    return title_new_text or title_text or track_id


def fetch_playlist_export_data(
    connection: sqlite3.Connection,
) -> tuple[list[dict[str, object]], OrderedDict[str, list[str]]]:
    """Return (tracks, playlists).

    tracks: unique tracks that have at least one playlist label.
    playlists: playlist label -> ordered unique track_ids.
    """
    rows = connection.execute(
        """
        SELECT
            tfd.track_id,
            tfd.filepath,
            tfd.title,
            tfd.date_created,
            tud.title_new,
            ld.label
        FROM tracks_file_data AS tfd
        JOIN track_user_data_labels AS tul ON tul.track_id = tfd.track_id
        JOIN label_definitions AS ld ON ld.id = tul.label_id
        LEFT JOIN track_user_data AS tud ON tud.track_id = tfd.track_id
        WHERE ld.category = 'playlist'
        ORDER BY
            ld.label COLLATE NOCASE ASC,
            tfd.date_created ASC,
            tfd.filepath COLLATE NOCASE ASC
        """
    ).fetchall()

    tracks_by_id: OrderedDict[str, dict[str, object]] = OrderedDict()
    playlists: OrderedDict[str, list[str]] = OrderedDict()

    for row in rows:
        track_id = str(row[0])
        filepath = str(row[1]) if row[1] else ""
        title = str(row[2]) if row[2] else None
        title_new = str(row[4]) if row[4] else None
        playlist_name = str(row[5])

        if track_id not in tracks_by_id:
            tracks_by_id[track_id] = {
                "track_id": track_id,
                "filepath": filepath,
                "title": song_display_name(title, title_new, track_id),
            }

        playlist_tracks = playlists.setdefault(playlist_name, [])
        if track_id not in playlist_tracks:
            playlist_tracks.append(track_id)

    return list(tracks_by_id.values()), playlists


def write_id3_tags(path: Path, song_name: str) -> None:
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.delall("TIT2")
    tags.delall("TPE1")
    tags.delall("TALB")
    tags.add(TIT2(encoding=3, text=song_name))
    tags.add(TPE1(encoding=3, text=ARTIST_NAME))
    tags.add(TALB(encoding=3, text=ALBUM_NAME))
    tags.update_to_v23()
    tags.save(path, v2_version=3)


def resolve_source_path(filepath: str, music_root: Path) -> Path | None:
    if not filepath:
        return None
    relative = normalize_music_relative_path(filepath)
    source = music_root / relative
    if source.is_file():
        return source
    return None


def build_m3u8_contents(track_ids: list[str]) -> str:
    lines = ["#EXTM3U"]
    for track_id in track_ids:
        lines.append(f"../{TRACKS_DIR_NAME}/{stable_track_filename(track_id)}")
    return "\n".join(lines) + "\n"


def export_tracks(
    tracks: list[dict[str, object]],
    tracks_dir: Path,
    music_root: Path,
) -> tuple[int, list[str]]:
    copied = 0
    missing: list[str] = []

    for track in tracks:
        track_id = str(track["track_id"])
        filepath = str(track.get("filepath") or "")
        source = resolve_source_path(filepath, music_root)
        if source is None:
            missing.append(filepath or track_id)
            continue

        destination = tracks_dir / stable_track_filename(track_id)
        shutil.copy2(source, destination)
        write_id3_tags(destination, str(track["title"]))
        copied += 1

    return copied, missing


def export_playlists(
    playlists: OrderedDict[str, list[str]],
    playlists_dir: Path,
) -> int:
    filename_stems = allocate_unique_filenames(list(playlists.keys()))
    written = 0

    for playlist_name, track_ids in playlists.items():
        stem = filename_stems[playlist_name]
        output_path = playlists_dir / f"{stem}.m3u8"
        output_path.write_text(build_m3u8_contents(track_ids), encoding="utf-8")
        written += 1

    return written


def prepare_output_dirs(output_dir: Path) -> tuple[Path, Path]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    tracks_dir = output_dir / TRACKS_DIR_NAME
    playlists_dir = output_dir / PLAYLISTS_DIR_NAME
    tracks_dir.mkdir(parents=True)
    playlists_dir.mkdir(parents=True)
    return tracks_dir, playlists_dir


def export_auxio(
    db_path: Path = DB_PATH,
    music_root: Path = MUSIC_ROOT,
    output_dir: Path = OUTPUT_DIR,
) -> int:
    if not db_path.exists():
        print(f"Database not found: {db_path.resolve()}", file=sys.stderr)
        return 1

    connection = sqlite3.connect(db_path)
    try:
        tracks, playlists = fetch_playlist_export_data(connection)
    finally:
        connection.close()

    tracks_dir, playlists_dir = prepare_output_dirs(output_dir)
    copied, missing = export_tracks(tracks, tracks_dir, music_root)
    playlist_count = export_playlists(playlists, playlists_dir)

    print(f"Exported to {output_dir.resolve()}")
    print(f"  tracks: {copied}")
    print(f"  playlists: {playlist_count}")

    if missing:
        print(f"Missing {len(missing)} source files:", file=sys.stderr)
        for relative in missing:
            print(f"  {relative}", file=sys.stderr)
        return 1

    return 0


def main() -> None:
    sys.exit(export_auxio())


if __name__ == "__main__":
    main()
