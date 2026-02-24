from pathlib import Path
import re

import mutagen

SUNO_SONG_URL_PREFIX = "https://suno.com/song/"
CREATED_AT_PATTERN = re.compile(r"(?:^|[;\s])created=([^;]+)")


def _stringify_tag_value(value: object) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(map(str, value))
    return str(value)


def extract_track_id(file_path: Path) -> str | None:
    metadata = extract_file_metadata(file_path)
    track_id = metadata.get("track_id")
    return track_id if isinstance(track_id, str) and track_id else None


def extract_file_metadata(file_path: Path) -> dict[str, str | float | None]:
    audio = mutagen.File(file_path)
    if audio is None:
        return {
            "track_id": None,
            "title": None,
            "artist": None,
            "url": None,
            "date_created": None,
            "duration": None,
        }

    tags = audio.tags or {}

    track_id: str | None = None
    url: str | None = None
    title: str | None = None
    artist: str | None = None
    date_created: str | None = None

    title_value = tags.get("TIT2")
    if title_value:
        title = _stringify_tag_value(title_value).strip() or None

    artist_value = tags.get("TPE1")
    if artist_value:
        artist = _stringify_tag_value(artist_value).strip() or None

    for key, value in tags.items():
        key_str = str(key)
        raw_value = _stringify_tag_value(value).strip()
        if not raw_value:
            continue

        if key_str.startswith("WOAS") and url is None:
            url = raw_value
            if raw_value.startswith(SUNO_SONG_URL_PREFIX):
                track_id = raw_value.removeprefix(SUNO_SONG_URL_PREFIX)
            elif "/song/" in raw_value:
                track_id = raw_value.rsplit("/", 1)[-1]
            else:
                track_id = raw_value
            continue

        if key_str.startswith("COMM"):
            match = CREATED_AT_PATTERN.search(raw_value)
            if match:
                date_created = match.group(1).strip() or None

    duration: float | None = None
    if getattr(audio, "info", None) is not None and hasattr(audio.info, "length"):
        duration = float(audio.info.length)

    return {
        "track_id": track_id,
        "title": title,
        "artist": artist,
        "url": url,
        "date_created": date_created,
        "duration": duration,
    }
