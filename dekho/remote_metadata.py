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


TEXT_REF_RE = re.compile(r"^(\d+):T[0-9a-fA-F]+,$")
TEXT_REF_INLINE_RE = re.compile(r"^(\d+):T[0-9a-fA-F]+,(.+)$", re.DOTALL)


def _extract_from_decoded_chunk(
    decoded: str, pending_text_ref_id: str | None
) -> tuple[dict[str, Any] | None, dict[str, str], str | None]:
    best_candidate: dict[str, Any] | None = None
    text_refs: dict[str, str] = {}
    next_pending = pending_text_ref_id

    # Next.js Flight can emit text references in two steps:
    #   25:T690,        (declares text ref id)
    #   <next chunk>    (actual text body)
    if next_pending and ":" not in decoded:
        text_refs[next_pending] = decoded
        next_pending = None

    lines = decoded.splitlines()
    for index, line in enumerate(lines):
        inline_match = TEXT_REF_INLINE_RE.match(line.strip())
        if inline_match:
            ref_id = inline_match.group(1)
            first_part = inline_match.group(2)
            remainder = "\n".join(lines[index + 1 :])
            text_value = first_part
            if remainder:
                text_value = f"{text_value}\n{remainder}" if text_value else remainder
            text_refs[ref_id] = text_value
            next_pending = None
            break

        marker_match = TEXT_REF_RE.match(line.strip())
        if marker_match:
            next_pending = marker_match.group(1)
            continue

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
            if not isinstance(node, dict):
                continue
            present_keys = {"prompt", "tags", "negative_tags"}.intersection(node.keys())
            if not present_keys:
                continue

            if best_candidate is None or len(present_keys) > len(
                {"prompt", "tags", "negative_tags"}.intersection(best_candidate.keys())
            ):
                best_candidate = node

    return best_candidate, text_refs, next_pending


def _resolve_prompt_reference(prompt: str | None, text_refs: dict[str, str]) -> str | None:
    if not isinstance(prompt, str):
        return prompt
    if prompt.startswith("$") and prompt[1:].isdigit():
        return text_refs.get(prompt[1:], prompt)
    return prompt


def fetch_suno_track_metadata(track_url: str) -> dict[str, str | None]:
    if not track_url.startswith(("http://", "https://")):
        raise ValueError("Track URL is missing or invalid.")
    if "/song/" not in track_url:
        raise ValueError("Track URL is not a Suno track URL.")

    html = _read_html(track_url)
    text_refs: dict[str, str] = {}
    pending_text_ref_id: str | None = None
    best_candidate: dict[str, Any] | None = None

    for match in PUSH_RE.finditer(html):
        escaped = match.group(1)
        decoded = json.loads(f'"{escaped}"')
        candidate, refs, pending_text_ref_id = _extract_from_decoded_chunk(
            decoded, pending_text_ref_id
        )
        text_refs.update(refs)

        if candidate is not None and (
            best_candidate is None
            or len({"prompt", "tags", "negative_tags"}.intersection(candidate.keys()))
            > len({"prompt", "tags", "negative_tags"}.intersection(best_candidate.keys()))
        ):
            best_candidate = candidate

    if best_candidate is None:
        raise ValueError("Suno metadata not found on track page.")

    prompt = best_candidate.get("prompt")
    tags = best_candidate.get("tags")
    negative_tags = best_candidate.get("negative_tags")

    resolved_prompt = _resolve_prompt_reference(
        str(prompt) if prompt is not None else None, text_refs
    )

    return {
        "prompt": resolved_prompt,
        "tags": str(tags) if tags is not None else None,
        "negative_tags": str(negative_tags) if negative_tags is not None else None,
    }
