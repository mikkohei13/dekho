from collections.abc import Iterable

LABEL_CATALOG: tuple[dict[str, str | tuple[dict[str, str], ...]], ...] = (
    {
        "category": "playlist",
        "display_name": "playlist",
        "labels": (
            {"key": "playlist.story", "label": "story"},
            {"key": "playlist.mythical", "label": "mythical"},
            {"key": "playlist.doggerland", "label": "doggerland"},
            {"key": "playlist.shadowrun", "label": "shadowrun"},
            {"key": "playlist.retro", "label": "retro"},
            {"key": "playlist.western", "label": "western"},
        ),
    },
    {
        "category": "like",
        "display_name": "like",
        "labels": (
            {"key": "like.like0", "label": "like0"},
            {"key": "like.like1", "label": "like1"},
            {"key": "like.like2", "label": "like2"},
            {"key": "like.like3", "label": "like3"},
        ),
    },
    {
        "category": "setting",
        "display_name": "setting",
        "labels": (
            {"key": "setting.story", "label": "story"},
            {"key": "setting.mythical", "label": "mythical"},
            {"key": "setting.doggerland", "label": "doggerland"},
            {"key": "setting.shadowrun", "label": "shadowrun"},
            {"key": "setting.western", "label": "western"},
        ),
    },
    {
        "category": "type",
        "display_name": "type",
        "labels": (
            {"key": "type.instrumental", "label": "instrumental"},
            {"key": "type.epic", "label": "epic"},
        ),
    },
    {
        "category": "generation",
        "display_name": "generation",
        "labels": (
            {"key": "generation.published_on_suno", "label": "published on Suno"},
            {"key": "generation.own_cover", "label": "own cover"},
            {"key": "generation.other_cover", "label": "other cover"},
            {"key": "generation.ace_cover", "label": "ace-cover"},
        ),
    },
    {
        "category": "persona",
        "display_name": "persona",
        "labels": (
            {"key": "persona.shadowrun", "label": "shadowrun"},
        ),
    },
    {
        "category": "issue",
        "display_name": "issue",
        "labels": (
            {"key": "issue.cut_short", "label": "cut short"},
            {"key": "issue.distortion", "label": "distortion"},
            {"key": "issue.other", "label": "other"},
        ),
    },
)


def get_label_catalog() -> list[dict[str, str | list[dict[str, str]]]]:
    return [
        {
            "category": str(entry["category"]),
            "display_name": str(entry["display_name"]),
            "labels": [
                {"key": str(label["key"]), "label": str(label["label"])}
                for label in entry["labels"]
            ],
        }
        for entry in LABEL_CATALOG
    ]


def get_allowed_label_keys() -> set[str]:
    allowed: set[str] = set()
    for entry in LABEL_CATALOG:
        for label in entry["labels"]:
            allowed.add(str(label["key"]))
    return allowed


def normalize_label_keys(raw_labels: object) -> list[str]:
    if not isinstance(raw_labels, list):
        raise ValueError("labels must be a list.")

    normalized: list[str] = []
    seen: set[str] = set()
    allowed = get_allowed_label_keys()

    for raw_label in raw_labels:
        if not isinstance(raw_label, str):
            raise ValueError("each label must be a string key.")
        if raw_label not in allowed:
            raise ValueError(f"unknown label: {raw_label}")
        if raw_label in seen:
            continue
        seen.add(raw_label)
        normalized.append(raw_label)

    return normalized


def iter_label_definitions() -> Iterable[tuple[str, str, str]]:
    for entry in LABEL_CATALOG:
        category = str(entry["category"])
        for label in entry["labels"]:
            yield str(label["key"]), category, str(label["label"])
