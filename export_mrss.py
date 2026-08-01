"""Generate a Media RSS (MRSS) feed of tracks that have playlist labels.

Usage:
    uv run export_mrss.py
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote
from xml.etree.ElementTree import Element, ElementTree, SubElement, indent, register_namespace

DB_PATH = Path("dekho.sqlite3")
MUSIC_ROOT = Path("music")
OUTPUT_DIR = Path("export_music")
OUTPUT_FILE = OUTPUT_DIR / "dekho.rss"
OUTPUT_MUSIC_DIR = OUTPUT_DIR / "music"
MEDIA_URL_PREFIX = "https://www.biomi.org/dekho/"
MRSS_NS = "http://search.yahoo.com/mrss/"
CHANNEL_TITLE = "Dekho Music Library"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def format_pub_date(date_created: str | None, date_added: str | None = None) -> str:
    parsed = _parse_datetime(date_created) or _parse_datetime(date_added)
    if parsed is None:
        parsed = datetime(1970, 1, 1, tzinfo=UTC)
    return format_datetime(parsed, usegmt=True)


def normalize_music_relative_path(filepath: str) -> str:
    relative = filepath.lstrip("/")
    if relative.startswith("music/"):
        relative = relative[len("music/") :]
    return relative


def media_content_url(filepath: str) -> str:
    relative = normalize_music_relative_path(filepath)
    encoded = quote(relative, safe="/")
    return f"{MEDIA_URL_PREFIX}music/{encoded}"


def mime_type_for_filepath(filepath: str) -> str:
    suffix = Path(filepath).suffix.lower()
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix == ".m4a":
        return "audio/mp4"
    if suffix == ".wav":
        return "audio/wav"
    if suffix == ".flac":
        return "audio/flac"
    if suffix == ".ogg":
        return "audio/ogg"
    return "application/octet-stream"


def fetch_playlist_tracks(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            tfd.track_id,
            tfd.filepath,
            tfd.title,
            tfd.duration,
            tfd.date_created,
            tfd.date_added,
            tud.title_new,
            ld.label
        FROM tracks_file_data AS tfd
        JOIN track_user_data_labels AS tul ON tul.track_id = tfd.track_id
        JOIN label_definitions AS ld ON ld.id = tul.label_id
        LEFT JOIN track_user_data AS tud ON tud.track_id = tfd.track_id
        WHERE ld.category = 'playlist'
        ORDER BY tfd.date_created DESC, tfd.filepath COLLATE NOCASE ASC, ld.label ASC
        """
    ).fetchall()

    tracks_by_id: dict[str, dict[str, object]] = {}
    for row in rows:
        track_id = str(row[0])
        track = tracks_by_id.get(track_id)
        if track is None:
            title_new = str(row[6]).strip() if row[6] else ""
            title = str(row[2]).strip() if row[2] else ""
            track = {
                "track_id": track_id,
                "filepath": str(row[1]) if row[1] else "",
                "title": title_new or title or track_id,
                "duration": row[3],
                "date_created": row[4],
                "date_added": row[5],
                "playlist_labels": [],
            }
            tracks_by_id[track_id] = track
        labels = track["playlist_labels"]
        assert isinstance(labels, list)
        label = str(row[7])
        if label not in labels:
            labels.append(label)

    return list(tracks_by_id.values())


def build_mrss(tracks: list[dict[str, object]]) -> Element:
    register_namespace("media", MRSS_NS)
    rss = Element("rss")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = CHANNEL_TITLE

    for track in tracks:
        filepath = str(track.get("filepath") or "")
        if not filepath:
            continue

        item = SubElement(channel, "item")
        SubElement(item, "title").text = str(track.get("title") or track["track_id"])
        SubElement(item, "guid").text = str(track["track_id"])
        SubElement(item, "pubDate").text = format_pub_date(
            str(track["date_created"]) if track.get("date_created") else None,
            str(track["date_added"]) if track.get("date_added") else None,
        )

        duration_raw = track.get("duration")
        duration_seconds = 0
        if isinstance(duration_raw, (int, float)):
            duration_seconds = max(0, int(round(float(duration_raw))))

        content = SubElement(item, f"{{{MRSS_NS}}}content")
        content.set("url", media_content_url(filepath))
        content.set("type", mime_type_for_filepath(filepath))
        content.set("duration", str(duration_seconds))

        playlist_labels = track.get("playlist_labels")
        if isinstance(playlist_labels, list):
            for label in playlist_labels:
                category = SubElement(item, f"{{{MRSS_NS}}}category")
                category.text = str(label)

    return rss


def write_mrss(output_path: Path, tracks: list[dict[str, object]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    root = build_mrss(tracks)
    tree = ElementTree(root)
    indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def copy_track_files(
    tracks: list[dict[str, object]],
    music_root: Path = MUSIC_ROOT,
    output_music_dir: Path = OUTPUT_MUSIC_DIR,
) -> tuple[int, list[str]]:
    """Copy included tracks into output_music_dir, preserving subfolders.

    Returns (copied_count, missing_relative_paths).
    """
    copied = 0
    missing: list[str] = []

    for track in tracks:
        filepath = str(track.get("filepath") or "")
        if not filepath:
            continue

        relative = normalize_music_relative_path(filepath)
        source = music_root / relative
        destination = output_music_dir / relative

        if not source.is_file():
            missing.append(relative)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1

    return copied, missing


def main() -> None:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH.resolve()}", file=sys.stderr)
        sys.exit(1)

    connection = sqlite3.connect(DB_PATH)
    try:
        tracks = fetch_playlist_tracks(connection)
    finally:
        connection.close()

    write_mrss(OUTPUT_FILE, tracks)
    print(f"Wrote {len(tracks)} tracks to {OUTPUT_FILE.resolve()}")

    copied, missing = copy_track_files(tracks)
    print(f"Copied {copied} files to {OUTPUT_MUSIC_DIR.resolve()}")
    if missing:
        print(f"Missing {len(missing)} source files:", file=sys.stderr)
        for relative in missing:
            print(f"  {relative}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
