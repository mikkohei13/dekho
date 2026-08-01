"""Label filter match rules used by the track list UI.

The frontend mirrors this logic in
`dekho/static/scripts/index/render-track-list.js` (`trackMatchesSelectedLabels`).
"""

from collections.abc import Iterable


def _label_category(label_key: str) -> str:
    return label_key.split(".", 1)[0] if label_key else ""


def track_matches_selected_labels(
    track_label_keys: Iterable[str],
    selected_label_keys: Iterable[str],
    match_mode: str = "or",
) -> bool:
    """Return whether a track matches selected label keys.

    - ``and``: track must have every selected key.
    - ``or`` (default): within each category, any selected key matches;
      across categories, all category groups must match.
    """
    selected = list(dict.fromkeys(selected_label_keys))
    if not selected:
        return True

    track_keys = set(track_label_keys)
    if match_mode == "and":
        return all(label_key in track_keys for label_key in selected)

    selected_by_category: dict[str, list[str]] = {}
    for label_key in selected:
        category = _label_category(label_key)
        if not category:
            continue
        selected_by_category.setdefault(category, []).append(label_key)

    for keys in selected_by_category.values():
        if not any(label_key in track_keys for label_key in keys):
            return False
    return True
