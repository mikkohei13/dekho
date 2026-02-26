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
CONTENT_SIGNAL_KEYS = {
    "prompt",
    "tags",
    "negative_tags",
    "cover_clip_id",
    "persona",
}
MODEL_SIGNAL_KEYS = {
    "major_model_version",
    "model_name",
}


def _extract_from_decoded_chunk(
    decoded: str, pending_text_ref_id: str | None
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, str], str | None]:
    best_content_candidate: dict[str, Any] | None = None
    best_model_candidate: dict[str, Any] | None = None
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
            present_content_keys = CONTENT_SIGNAL_KEYS.intersection(node.keys())
            if present_content_keys and (
                best_content_candidate is None
                or len(present_content_keys)
                > len(CONTENT_SIGNAL_KEYS.intersection(best_content_candidate.keys()))
            ):
                best_content_candidate = node

            present_model_keys = MODEL_SIGNAL_KEYS.intersection(node.keys())
            if present_model_keys and (
                best_model_candidate is None
                or len(present_model_keys)
                > len(MODEL_SIGNAL_KEYS.intersection(best_model_candidate.keys()))
            ):
                best_model_candidate = node

    return best_content_candidate, best_model_candidate, text_refs, next_pending


def _resolve_prompt_reference(prompt: str | None, text_refs: dict[str, str]) -> str | None:
    if not isinstance(prompt, str):
        return prompt
    if prompt.startswith("$") and prompt[1:].isdigit():
        return text_refs.get(prompt[1:], prompt)
    return prompt


def _get_first_present_value(
    nodes: list[dict[str, Any] | None], keys: list[str]
) -> Any | None:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        for key in keys:
            value = node.get(key)
            if value is not None:
                return value
    return None


def fetch_suno_track_metadata(track_url: str) -> dict[str, str | bool | None]:
    if not track_url.startswith(("http://", "https://")):
        raise ValueError("Track URL is missing or invalid.")
    if "/song/" not in track_url:
        raise ValueError("Track URL is not a Suno track URL.")

    html = _read_html(track_url)
    text_refs: dict[str, str] = {}
    pending_text_ref_id: str | None = None
    best_content_candidate: dict[str, Any] | None = None
    best_model_candidate: dict[str, Any] | None = None

    for match in PUSH_RE.finditer(html):
        escaped = match.group(1)
        decoded = json.loads(f'"{escaped}"')
        content_candidate, model_candidate, refs, pending_text_ref_id = _extract_from_decoded_chunk(
            decoded, pending_text_ref_id
        )
        text_refs.update(refs)

        if content_candidate is not None and (
            best_content_candidate is None
            or len(CONTENT_SIGNAL_KEYS.intersection(content_candidate.keys()))
            > len(CONTENT_SIGNAL_KEYS.intersection(best_content_candidate.keys()))
        ):
            best_content_candidate = content_candidate

        if model_candidate is not None and (
            best_model_candidate is None
            or len(MODEL_SIGNAL_KEYS.intersection(model_candidate.keys()))
            > len(MODEL_SIGNAL_KEYS.intersection(best_model_candidate.keys()))
        ):
            best_model_candidate = model_candidate

    if best_content_candidate is None and best_model_candidate is None:
        raise ValueError("Suno metadata not found on track page.")

    primary_candidate = best_content_candidate or best_model_candidate or {}
    metadata = primary_candidate.get("metadata")
    metadata_node = metadata if isinstance(metadata, dict) else {}

    prompt = primary_candidate.get("prompt", metadata_node.get("prompt"))
    tags = primary_candidate.get("tags", metadata_node.get("tags"))
    negative_tags = primary_candidate.get(
        "negative_tags", metadata_node.get("negative_tags")
    )

    persona_name: Any = primary_candidate.get("persona_name")
    if persona_name is None:
        persona = primary_candidate.get("persona")
        if isinstance(persona, dict):
            persona_name = persona.get("name")

    resolved_prompt = _resolve_prompt_reference(
        str(prompt) if prompt is not None else None, text_refs
    )
    has_cover_clip_id = (
        "cover_clip_id" in metadata_node or "cover_clip_id" in primary_candidate
    )
    model_lookup_nodes = [best_model_candidate, primary_candidate, metadata_node]
    major_model_version = _get_first_present_value(
        model_lookup_nodes,
        [
            "major_model_version",
            "majorModelVersion",
            "model_version",
            "modelVersion",
        ],
    )
    model_name = _get_first_present_value(
        model_lookup_nodes,
        ["model_name", "modelName", "model"],
    )

    return {
        "prompt": resolved_prompt,
        "tags": str(tags) if tags is not None else None,
        "negative_tags": str(negative_tags) if negative_tags is not None else None,
        "has_cover_clip_id": has_cover_clip_id,
        "major_model_version": (
            str(major_model_version) if major_model_version is not None else None
        ),
        "model_name": str(model_name) if model_name is not None else None,
        "persona_name": str(persona_name) if persona_name is not None else None,
    }
