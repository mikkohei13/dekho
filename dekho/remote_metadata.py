import json
import re
from typing import Any
from urllib.request import Request, urlopen

PUSH_RE = re.compile(
    r'self\.__next_f\.push\(\[\d+,\s*"((?:\\.|[^"\\])*)"\]\)</script>',
    re.DOTALL,
)


def _walk(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def _read_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_suno_track_metadata(track_url: str) -> dict[str, str]:
    if not track_url.startswith(("http://", "https://")):
        raise ValueError("Track URL is missing or invalid.")
    if "/song/" not in track_url:
        raise ValueError("Track URL is not a Suno track URL.")

    html = _read_html(track_url)

    for match in PUSH_RE.finditer(html):
        escaped = match.group(1)
        decoded = json.loads(f'"{escaped}"')

        for line in decoded.splitlines():
            if ":" not in line:
                continue
            _, payload = line.split(":", 1)
            payload = payload.strip()
            if not payload or payload[0] not in "[{":
                continue

            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue

            for node in _walk(obj):
                if {"prompt", "tags", "negative_tags"}.issubset(node.keys()):
                    return {
                        "prompt": str(node["prompt"]),
                        "tags": str(node["tags"]),
                        "negative_tags": str(node["negative_tags"]),
                    }

    raise ValueError("Suno metadata not found on track page.")
