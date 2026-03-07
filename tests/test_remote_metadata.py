import json
import unittest
from pathlib import Path
from unittest.mock import patch

import dekho.remote_metadata as rm


class FetchSunoTrackMetadataTests(unittest.TestCase):
    def setUp(self):
        self.fixture_root = Path(__file__).resolve().parents[1]

    def _build_flight_html(self, decoded_chunks: list[str]) -> str:
        scripts = "".join(
            f"<script>self.__next_f.push([1,{json.dumps(chunk)}])</script>"
            for chunk in decoded_chunks
        )
        return f"<html><body>{scripts}</body></html>"

    def test_extracts_prompt_and_model_fields_from_flight_payload(self):
        html = (self.fixture_root / "temp_suno_example_1.html").read_text(
            encoding="utf-8", errors="replace"
        )
        with patch.object(rm, "_read_html", return_value=html):
            result = rm.fetch_suno_track_metadata(
                "https://suno.com/song/25701027-1be7-4510-a9c4-078c936cd915"
            )

        self.assertEqual(result["major_model_version"], "v5")
        self.assertEqual(result["model_name"], "chirp-crow")
        self.assertIsNotNone(result["tags"])
        self.assertIsNotNone(result["negative_tags"])
        self.assertIsNotNone(result["prompt"])

    def test_resolves_alphanumeric_prompt_reference_from_new_sample(self):
        html = (self.fixture_root / "temp_suno_example_5bfd.html").read_text(
            encoding="utf-8", errors="replace"
        )
        with patch.object(rm, "_read_html", return_value=html):
            result = rm.fetch_suno_track_metadata(
                "https://suno.com/song/31989c2a-f53e-4ef5-9d8e-a4ab4de4fc73"
            )

        self.assertIsNotNone(result["prompt"])
        self.assertFalse(result["prompt"].startswith("$"))
        self.assertIn("[Intro]", result["prompt"])
        self.assertIn("We walked the pier", result["prompt"])

    def test_unresolved_short_prompt_uses_lyrics_like_fallback(self):
        lyric_chunk = (
            "[Intro]\n"
            "We walked the pier until the last of daylight drowned,\n"
            "We found the edge where summer fades.\n\n"
            "[Verse]\n"
            "A hundred lights were stretching down the shore tonight,\n"
            "And every wave returned your name."
        )
        html = self._build_flight_html(
            [
                '0:[{"metadata":{"prompt":"$3e","tags":"acoustic"}}]',
                lyric_chunk,
            ]
        )
        with patch.object(rm, "_read_html", return_value=html):
            result = rm.fetch_suno_track_metadata(
                "https://suno.com/song/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
            )
        self.assertEqual(result["prompt"], lyric_chunk)

    def test_unresolved_prompt_returns_failed_when_no_strong_lyrics_candidate(self):
        html = self._build_flight_html(
            [
                '0:[{"metadata":{"prompt":"$3e","tags":"acoustic"}}]',
                "[instrumental]",
            ]
        )
        with patch.object(rm, "_read_html", return_value=html):
            result = rm.fetch_suno_track_metadata(
                "https://suno.com/song/ffffffff-1111-2222-3333-444444444444"
            )
        self.assertEqual(result["prompt"], "failed")

    def test_non_flight_snapshots_raise_clear_error(self):
        for name in ("temp_back.html", "temp_chasing.html"):
            with self.subTest(name=name):
                html = (self.fixture_root / name).read_text(
                    encoding="utf-8", errors="replace"
                )
                with patch.object(rm, "_read_html", return_value=html):
                    with self.assertRaisesRegex(
                        ValueError, "Suno metadata not found on track page."
                    ):
                        rm.fetch_suno_track_metadata(
                            "https://suno.com/song/00000000-0000-0000-0000-000000000000"
                        )


class ResolvePromptReferenceTests(unittest.TestCase):
    def test_resolves_existing_ref(self):
        self.assertEqual(
            rm._resolve_prompt_reference("$a1", {"a1": "resolved text"}),
            "resolved text",
        )

    def test_unresolved_ref_returns_original(self):
        self.assertEqual(rm._resolve_prompt_reference("$ff", {}), "$ff")

    def test_non_ref_prompt_passes_through(self):
        self.assertEqual(
            rm._resolve_prompt_reference("plain prompt", {"a1": "x"}),
            "plain prompt",
        )

    def test_none_returns_none(self):
        self.assertIsNone(rm._resolve_prompt_reference(None, {"a1": "x"}))


class IsInvalidPromptTests(unittest.TestCase):
    def test_dollar_prefix_is_invalid(self):
        self.assertTrue(rm._is_invalid_prompt("$3e"))

    def test_short_string_is_invalid(self):
        self.assertTrue(rm._is_invalid_prompt("hi"))

    def test_valid_prompt(self):
        self.assertFalse(rm._is_invalid_prompt("This is a real prompt with lyrics"))

    def test_none_is_not_invalid(self):
        self.assertFalse(rm._is_invalid_prompt(None))


class LyricsCandidateScoreTests(unittest.TestCase):
    def test_empty_string_scores_zero(self):
        self.assertEqual(rm._lyrics_candidate_score(""), 0)

    def test_short_text_scores_low(self):
        score = rm._lyrics_candidate_score("just a short line")
        self.assertLess(score, 4)

    def test_lyrics_with_markers_and_newlines_scores_high(self):
        lyrics = (
            "[Verse 1]\n"
            "Line one of the verse goes here\n"
            "Line two of the verse goes here\n\n"
            "[Chorus]\n"
            "Chorus line one that is long enough to matter for scoring\n"
            "Chorus line two that is long enough to matter for scoring\n\n"
            "[Verse 2]\n"
            "Another verse line here"
        )
        score = rm._lyrics_candidate_score(lyrics)
        self.assertGreaterEqual(score, 8)


class GetFirstPresentValueTests(unittest.TestCase):
    def test_finds_value_in_first_node(self):
        nodes = [{"a": 1, "b": 2}, {"a": 10}]
        self.assertEqual(rm._get_first_present_value(nodes, ["a"]), 1)

    def test_finds_value_in_later_node(self):
        nodes = [{"x": 1}, {"a": 42}]
        self.assertEqual(rm._get_first_present_value(nodes, ["a"]), 42)

    def test_tries_keys_in_order(self):
        nodes = [{"fallback": "yes", "primary": "no"}]
        self.assertEqual(
            rm._get_first_present_value(nodes, ["primary", "fallback"]), "no"
        )

    def test_returns_none_when_missing(self):
        self.assertIsNone(rm._get_first_present_value([{"a": 1}], ["z"]))

    def test_skips_none_nodes(self):
        self.assertIsNone(rm._get_first_present_value([None, None], ["a"]))


if __name__ == "__main__":
    unittest.main()
