"""Visualization routes (Blueprint), decoupled from the main app logic.

Serves standalone pages and data APIs for track analytics.
"""

import math
from itertools import combinations

from flask import Blueprint, jsonify, render_template

from .db import get_connection, init_db

viz_bp = Blueprint("viz", __name__, url_prefix="/viz")

LIKE_WEIGHTS = {
    "like.like3": 4,
    "like.like2": 3,
    "like.like1": 2,
    "like.like0": 1,
    "like.not_like": 0,
}
DEFAULT_WEIGHT = 1


def _query_tracks_with_tags_and_likes() -> list[dict]:
    """Return tracks that have tags, along with their like label (if any)."""
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                trd.track_id,
                trd.tags,
                ld.key AS like_key
            FROM track_remote_data AS trd
            LEFT JOIN track_user_data_labels AS tul
                ON tul.track_id = trd.track_id
            LEFT JOIN label_definitions AS ld
                ON ld.id = tul.label_id AND ld.category = 'like'
            WHERE trd.tags IS NOT NULL AND TRIM(trd.tags) != ''
            """
        ).fetchall()
    tracks: dict[str, dict] = {}
    for row in rows:
        tid = str(row[0])
        if tid not in tracks:
            tracks[tid] = {
                "track_id": tid,
                "tags": str(row[1]),
                "like_key": str(row[2]) if row[2] else None,
            }
        elif row[2] is not None:
            tracks[tid]["like_key"] = str(row[2])
    return list(tracks.values())


def _parse_tags(raw: str) -> list[str]:
    return [t.strip().lower() for t in raw.split(",") if t.strip()]


def _build_cooccurrence_data() -> dict:
    tracks = _query_tracks_with_tags_and_likes()

    tag_freq: dict[str, float] = {}
    tag_count: dict[str, int] = {}
    pair_weight: dict[tuple[str, str], float] = {}
    pair_count: dict[tuple[str, str], int] = {}
    total_weight = 0.0
    total_tracks = 0

    for track in tracks:
        tags = _parse_tags(track["tags"])
        if len(tags) < 2:
            continue
        tags = sorted(set(tags))
        weight = LIKE_WEIGHTS.get(track["like_key"], DEFAULT_WEIGHT) if track["like_key"] else DEFAULT_WEIGHT

        total_weight += weight
        total_tracks += 1
        for tag in tags:
            tag_freq[tag] = tag_freq.get(tag, 0.0) + weight
            tag_count[tag] = tag_count.get(tag, 0) + 1
        for a, b in combinations(tags, 2):
            key = (a, b)
            pair_weight[key] = pair_weight.get(key, 0.0) + weight
            pair_count[key] = pair_count.get(key, 0) + 1

    min_occurrences = 2
    frequent_tags = sorted(
        [t for t, c in tag_count.items() if c >= min_occurrences],
        key=lambda t: -tag_freq[t],
    )

    max_tags = 50
    if len(frequent_tags) > max_tags:
        frequent_tags = frequent_tags[:max_tags]

    tag_set = set(frequent_tags)
    n = len(frequent_tags)
    tag_index = {t: i for i, t in enumerate(frequent_tags)}

    matrix = [[0.0] * n for _ in range(n)]
    raw_counts = [[0] * n for _ in range(n)]
    surprise = [[0.0] * n for _ in range(n)]

    for (a, b), w in pair_weight.items():
        if a not in tag_set or b not in tag_set:
            continue
        i, j = tag_index[a], tag_index[b]
        matrix[i][j] = w
        matrix[j][i] = w
        c = pair_count[(a, b)]
        raw_counts[i][j] = c
        raw_counts[j][i] = c

    for i in range(n):
        matrix[i][i] = tag_freq.get(frequent_tags[i], 0.0)
        raw_counts[i][i] = tag_count.get(frequent_tags[i], 0)

    if total_weight > 0:
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                ti, tj = frequent_tags[i], frequent_tags[j]
                expected = (tag_freq.get(ti, 0) * tag_freq.get(tj, 0)) / total_weight
                actual = matrix[i][j]
                if expected > 0 and actual > 0:
                    surprise[i][j] = round(math.log2(actual / expected), 3)

    like_dist = {}
    for track in tracks:
        tags = _parse_tags(track["tags"])
        if len(tags) < 2:
            continue
        lk = track["like_key"] or "unrated"
        like_dist[lk] = like_dist.get(lk, 0) + 1

    return {
        "tags": frequent_tags,
        "matrix": matrix,
        "raw_counts": raw_counts,
        "surprise": surprise,
        "total_tracks": total_tracks,
        "like_distribution": like_dist,
    }


@viz_bp.get("/tag-heatmap")
def tag_heatmap():
    return render_template("viz_tag_heatmap.html")


@viz_bp.get("/api/tag-cooccurrence")
def tag_cooccurrence_api():
    return jsonify(_build_cooccurrence_data())
