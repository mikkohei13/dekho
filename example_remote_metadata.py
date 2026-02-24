# Example script to fetch track metadata from Suno.

import json
import re
from pathlib import Path
from urllib.request import Request, urlopen
from typing import Any

PUSH_RE = re.compile(
    r'self\.__next_f\.push\(\[\d+,\s*"((?:\\.|[^"\\])*)"\]\)</script>',
    re.DOTALL,
)

def walk(node: Any):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)

def _read_html(source: str) -> str:
    if source.startswith(("http://", "https://")):
        req = Request(source, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req) as res:
            return res.read().decode("utf-8", errors="replace")

    return Path(source).read_text(encoding="utf-8")


def extract_track_metadata(source: str) -> dict:
    text = _read_html(source)

    for m in PUSH_RE.finditer(text):
        escaped = m.group(1)

        # Decode JS/JSON string literal from self.__next_f.push second arg
        decoded = json.loads(f'"{escaped}"')  # handles \" and \n safely

        # One decoded chunk may contain multiple lines like "12:[...]" / "17:[...]"
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

            for d in walk(obj):
                if {"prompt", "tags", "negative_tags"}.issubset(d.keys()):
                    return {
                        "prompt": d["prompt"],
                        "tags": d["tags"],
                        "negative_tags": d["negative_tags"],
                    }

    raise ValueError("Track metadata not found")

track_id = "fe9019aa-debb-4c72-859d-589a38b44835"
url = f"https://suno.com/song/{track_id}"

meta = extract_track_metadata(url)
print(meta["tags"][:2048])
print(meta["negative_tags"][:2048])
print(meta["prompt"][:8192])
