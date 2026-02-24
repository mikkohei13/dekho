from pathlib import Path

import mutagen

SUNO_SONG_URL_PREFIX = "https://suno.com/song/"


def extract_track_id(file_path: Path) -> str | None:
    audio = mutagen.File(file_path)
    if audio is None or not audio.tags:
        return None

    for key, value in audio.tags.items():
        if not str(key).startswith("WOAS"):
            continue

        raw_value = str(value).strip()
        if not raw_value:
            return None

        if raw_value.startswith(SUNO_SONG_URL_PREFIX):
            return raw_value.removeprefix(SUNO_SONG_URL_PREFIX)

        if "/song/" in raw_value:
            return raw_value.rsplit("/", 1)[-1]

        return raw_value

    return None
