import json
import re
from typing import Any
from urllib.request import Request, urlopen

PUSH_RE = re.compile(
    r'self\.__next_f\.push\(\[\d+,\s*"((?:\\.|[^"\\])*)"\]\)</script>',
    re.DOTALL,
)

# React Flight text blob: "<id>:T<hex-length>,<payload>"
TEXT_REF_HEAD_RE = re.compile(r"^([0-9A-Za-z]+):T([0-9a-fA-F]+),")
PROMPT_REF_RE = re.compile(r"^\$([0-9A-Za-z]+)$")
STANZA_MARKER_RE = re.compile(r"(?:\[[^\]\n]{1,40}\]|\([^\)\n]{1,40}\))")
FLIGHT_PREFIX_RE = re.compile(r"^[0-9A-Za-z]+:")
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


def _looks_like_flight_control_chunk(decoded: str) -> bool:
    for line in decoded.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        return FLIGHT_PREFIX_RE.match(stripped) is not None
    return False


def _is_usable_content_node(node: dict[str, Any]) -> bool:
    present = CONTENT_SIGNAL_KEYS.intersection(node.keys())
    if not present:
        return False
    # Ignore i18n/UI dicts that only expose a short label like {"prompt":"Prompt"}.
    if present == {"prompt"}:
        prompt = node.get("prompt")
        if not isinstance(prompt, str):
            return False
        stripped = prompt.strip()
        if stripped.startswith("$"):
            return True
        return "\n" in stripped or len(stripped) >= 40
    return True


def _consider_candidates(
    obj: Any,
    best_content_candidate: dict[str, Any] | None,
    best_model_candidate: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    for node in _walk(obj):
        if not isinstance(node, dict):
            continue
        present_content_keys = CONTENT_SIGNAL_KEYS.intersection(node.keys())
        if (
            present_content_keys
            and _is_usable_content_node(node)
            and (
                best_content_candidate is None
                or len(present_content_keys)
                > len(CONTENT_SIGNAL_KEYS.intersection(best_content_candidate.keys()))
            )
        ):
            best_content_candidate = node

        present_model_keys = MODEL_SIGNAL_KEYS.intersection(node.keys())
        if present_model_keys and (
            best_model_candidate is None
            or len(present_model_keys)
            > len(MODEL_SIGNAL_KEYS.intersection(best_model_candidate.keys()))
        ):
            best_model_candidate = node
    return best_content_candidate, best_model_candidate


def _parse_flight_json_line(
    line: str,
    best_content_candidate: dict[str, Any] | None,
    best_model_candidate: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if ":" not in line:
        return best_content_candidate, best_model_candidate
    _, payload = line.split(":", 1)
    payload = payload.strip()
    if not payload or payload[0] not in "[{":
        return best_content_candidate, best_model_candidate
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return best_content_candidate, best_model_candidate
    return _consider_candidates(obj, best_content_candidate, best_model_candidate)


def _split_utf8_prefix(text: str, byte_len: int) -> tuple[str, str] | None:
    """Split off the first ``byte_len`` UTF-8 bytes of ``text``.

    React Flight ``T<hex>`` lengths are UTF-8 byte counts, not Unicode code points.
    Returns None when ``text`` does not contain enough bytes.
    """
    encoded = text.encode("utf-8")
    if len(encoded) < byte_len:
        return None
    prefix = encoded[:byte_len].decode("utf-8")
    return prefix, text[len(prefix) :]


def _extract_from_decoded_chunk(
    decoded: str, pending_text_ref_id: str | None
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, str], str | None]:
    best_content_candidate: dict[str, Any] | None = None
    best_model_candidate: dict[str, Any] | None = None
    text_refs: dict[str, str] = {}
    next_pending = pending_text_ref_id

    # Marker-only refs arrive as: previous chunk ended with "25:T690,"
    # and the next non-control chunk is the full text body.
    if next_pending and not _looks_like_flight_control_chunk(decoded):
        text_refs[next_pending] = decoded
        return best_content_candidate, best_model_candidate, text_refs, None

    cursor = 0
    length = len(decoded)
    while cursor < length:
        next_nl = decoded.find("\n", cursor)
        line_end = length if next_nl < 0 else next_nl
        line = decoded[cursor:line_end]

        head = TEXT_REF_HEAD_RE.match(line)
        if head:
            ref_id = head.group(1)
            byte_len = int(head.group(2), 16)
            content_start = cursor + head.end()
            split = _split_utf8_prefix(decoded[content_start:], byte_len)
            if split is not None:
                # Length-prefixed payload in this chunk; more Flight data may follow.
                text_value, _remainder = split
                text_refs[ref_id] = text_value
                cursor = content_start + len(text_value)
                next_pending = None
                continue

            # Declared length does not fit: treat as marker for the next text chunk.
            next_pending = ref_id
            break

        best_content_candidate, best_model_candidate = _parse_flight_json_line(
            line, best_content_candidate, best_model_candidate
        )
        cursor = line_end + 1 if next_nl >= 0 else length

    return best_content_candidate, best_model_candidate, text_refs, next_pending


def _resolve_prompt_reference(prompt: str | None, text_refs: dict[str, str]) -> str | None:
    if not isinstance(prompt, str):
        return prompt
    match = PROMPT_REF_RE.match(prompt.strip())
    if match:
        return text_refs.get(match.group(1), prompt)
    return prompt


def _is_invalid_prompt(prompt: str | None) -> bool:
    if not isinstance(prompt, str):
        return False
    stripped = prompt.strip()
    return stripped.startswith("$") or len(stripped) < 5


def _lyrics_candidate_score(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    markers = len(STANZA_MARKER_RE.findall(stripped))
    newlines = stripped.count("\n")
    length = len(stripped)
    score = 0
    if markers >= 2:
        score += 5
    elif markers == 1:
        score += 2
    if newlines >= 4:
        score += 4
    elif newlines >= 2:
        score += 2
    if length >= 250:
        score += 4
    elif length >= 120:
        score += 2
    elif length >= 60:
        score += 1
    return score


def _find_lyrics_like_text(
    decoded_chunks: list[str], text_refs: dict[str, str]
) -> str | None:
    candidates: list[str] = []
    seen: set[str] = set()
    for value in text_refs.values():
        stripped = value.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            candidates.append(stripped)
    for chunk in decoded_chunks:
        stripped = chunk.strip()
        if (
            stripped
            and stripped not in seen
            and not stripped.startswith("self.__next_f.push")
            and not _looks_like_flight_control_chunk(chunk)
        ):
            seen.add(stripped)
            candidates.append(stripped)

    best_text: str | None = None
    best_score = -1
    for candidate in candidates:
        score = _lyrics_candidate_score(candidate)
        if score > best_score:
            best_score = score
            best_text = candidate

    if best_text is None:
        return None

    best_markers = len(STANZA_MARKER_RE.findall(best_text))
    best_newlines = best_text.count("\n")
    best_length = len(best_text)
    # Keep this intentionally conservative to avoid false positives.
    if best_score >= 8 and best_newlines >= 2 and best_length >= 80 and best_markers >= 1:
        return best_text
    return None


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


def _extract_persona_name(nodes: list[dict[str, Any] | None]) -> str | None:
    direct = _get_first_present_value(nodes, ["persona_name"])
    if direct is not None:
        return str(direct)
    for node in nodes:
        if not isinstance(node, dict):
            continue
        persona = node.get("persona")
        if isinstance(persona, dict):
            name = persona.get("name")
            if name is not None:
                return str(name)
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
    decoded_chunks: list[str] = []

    for match in PUSH_RE.finditer(html):
        escaped = match.group(1)
        decoded = json.loads(f'"{escaped}"')
        decoded_chunks.append(decoded)
        content_candidate, model_candidate, refs, pending_text_ref_id = (
            _extract_from_decoded_chunk(decoded, pending_text_ref_id)
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
    model_metadata = (
        best_model_candidate.get("metadata")
        if isinstance(best_model_candidate, dict)
        else None
    )
    model_metadata_node = model_metadata if isinstance(model_metadata, dict) else {}

    lookup_nodes = [
        primary_candidate,
        metadata_node,
        best_model_candidate,
        model_metadata_node,
    ]
    prompt = _get_first_present_value(lookup_nodes, ["prompt"])
    tags = _get_first_present_value(lookup_nodes, ["tags"])
    negative_tags = _get_first_present_value(lookup_nodes, ["negative_tags"])
    persona_name = _extract_persona_name(lookup_nodes)

    resolved_prompt = _resolve_prompt_reference(
        str(prompt) if prompt is not None else None, text_refs
    )
    if _is_invalid_prompt(resolved_prompt):
        fallback_prompt = _find_lyrics_like_text(decoded_chunks, text_refs)
        resolved_prompt = fallback_prompt if fallback_prompt is not None else "failed"
    has_cover_clip_id = any(
        isinstance(node, dict) and "cover_clip_id" in node for node in lookup_nodes
    )
    major_model_version = _get_first_present_value(
        lookup_nodes,
        [
            "major_model_version",
            "majorModelVersion",
            "model_version",
            "modelVersion",
        ],
    )
    model_name = _get_first_present_value(
        lookup_nodes,
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
        "persona_name": persona_name,
    }
