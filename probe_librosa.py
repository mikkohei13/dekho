"""Probe what audio features librosa can extract for a Dekho track.

Usage:
    uv run probe_librosa.py <track_id>
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import librosa
import numpy as np

DB_PATH = Path("dekho.sqlite3")
MUSIC_ROOT = Path("music")

PITCH_CLASSES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

# Krumhansl-Schmuckler key profiles (tonic at index 0).
MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    dtype=float,
)
MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    dtype=float,
)


def _get_track(track_id: str) -> tuple[str, str]:
    """Return (display_title, filepath) for a track_id."""
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH.resolve()}", file=sys.stderr)
        sys.exit(1)

    connection = sqlite3.connect(DB_PATH)
    try:
        row = connection.execute(
            """
            SELECT
                tfd.title,
                tud.title_new,
                tfd.filepath
            FROM tracks_file_data AS tfd
            LEFT JOIN track_user_data AS tud ON tud.track_id = tfd.track_id
            WHERE tfd.track_id = ?
            """,
            (track_id,),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        print(f"Track not found: {track_id}", file=sys.stderr)
        sys.exit(1)

    title, title_new, filepath = row
    display_title = (title_new or title or "Unknown").strip() or "Unknown"
    if not filepath:
        print(f"Track has no filepath: {track_id}", file=sys.stderr)
        sys.exit(1)
    return display_title, str(filepath)


def _resolve_audio_path(filepath: str) -> Path:
    app_root = Path(".").resolve()
    candidate = Path(filepath)
    if candidate.is_absolute():
        print(f"Track filepath must be relative: {filepath}", file=sys.stderr)
        sys.exit(1)

    resolved = (MUSIC_ROOT / candidate).resolve()
    if not resolved.is_file():
        resolved = (app_root / candidate).resolve()

    if not resolved.is_relative_to(app_root):
        print(f"Track filepath is outside app root: {filepath}", file=sys.stderr)
        sys.exit(1)
    if not resolved.is_file():
        print(f"Track audio file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    return resolved


def estimate_tempo(y: np.ndarray, sr: int) -> tuple[float, float]:
    """Estimate global tempo (BPM) and a 0–1 confidence proxy.

    Librosa has no built-in tempo confidence. Confidence here is the fraction
    of frames whose local tempo estimate is within 5% of the global BPM —
    a stability score for how consistent the tempo reading is across the track.
    """
    hop_length = 512
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    tempo = float(
        np.atleast_1d(
            librosa.feature.tempo(onset_envelope=onset_env, sr=sr, hop_length=hop_length)
        )[0]
    )

    frame_tempos = np.asarray(
        librosa.feature.tempo(
            onset_envelope=onset_env, sr=sr, hop_length=hop_length, aggregate=None
        ),
        dtype=float,
    ).ravel()
    if frame_tempos.size == 0 or tempo <= 0:
        return tempo, 0.0

    relative_error = np.abs(frame_tempos - tempo) / tempo
    confidence = float(np.mean(relative_error <= 0.05))
    return tempo, confidence


def estimate_key(y: np.ndarray, sr: int) -> tuple[str, str]:
    """Estimate musical key and mode via Krumhansl-Schmuckler key finding.

    Uses chroma from the harmonic component, correlated against major/minor
    key profiles for all 12 tonics. Librosa has no built-in key detector.
    """
    y_harmonic, _y_percussive = librosa.effects.hpss(y)
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr)
    chroma_avg = np.mean(chroma, axis=1)

    best_key = "C"
    best_mode = "major"
    best_correlation = float("-inf")

    for tonic_index, pitch_class in enumerate(PITCH_CLASSES):
        # Align chroma so candidate tonic sits at profile index 0.
        aligned = np.roll(chroma_avg, -tonic_index)
        for mode, profile in (("major", MAJOR_PROFILE), ("minor", MINOR_PROFILE)):
            if np.std(aligned) == 0 or np.std(profile) == 0:
                correlation = 0.0
            else:
                correlation = float(np.corrcoef(aligned, profile)[0, 1])
            if correlation > best_correlation:
                best_correlation = correlation
                best_key = pitch_class
                best_mode = mode

    return best_key, best_mode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract exploratory librosa features for a Dekho track."
    )
    parser.add_argument("track_id", help="Track ID from tracks_file_data")
    args = parser.parse_args()

    track_id = args.track_id.strip()
    if not track_id:
        print("track_id must not be empty", file=sys.stderr)
        sys.exit(1)

    song_name, filepath = _get_track(track_id)
    audio_path = _resolve_audio_path(filepath)

    print(f"track_id: {track_id}")
    print(f"song_name: {song_name}")
    print(f"filepath: {audio_path}")
    print("Analyzing with librosa...")

    y, sr = librosa.load(audio_path, sr=22050, mono=True)

    bpm, confidence = estimate_tempo(y, sr)
    print(f"tempo_bpm: {bpm:.2f}")
    print(f"tempo_confidence: {confidence:.4f}")

    key, mode = estimate_key(y, sr)
    print(f"key: {key}")
    print(f"mode: {mode}")


if __name__ == "__main__":
    main()
