import importlib.util
import json
import unittest
from pathlib import Path


def _load_remote_metadata_module():
    module_path = Path(__file__).resolve().parents[1] / "dekho" / "remote_metadata.py"
    spec = importlib.util.spec_from_file_location("remote_metadata", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FetchSunoTrackMetadataTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_remote_metadata_module()
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
        self.module._read_html = lambda _url: html

        result = self.module.fetch_suno_track_metadata(
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
        self.module._read_html = lambda _url: html

        result = self.module.fetch_suno_track_metadata(
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
        self.module._read_html = lambda _url: html

        result = self.module.fetch_suno_track_metadata(
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
        self.module._read_html = lambda _url: html

        result = self.module.fetch_suno_track_metadata(
            "https://suno.com/song/ffffffff-1111-2222-3333-444444444444"
        )
        self.assertEqual(result["prompt"], "failed")

    def test_non_flight_snapshots_raise_clear_error(self):
        for name in ("temp_back.html", "temp_chasing.html"):
            with self.subTest(name=name):
                html = (self.fixture_root / name).read_text(
                    encoding="utf-8", errors="replace"
                )
                self.module._read_html = lambda _url, html=html: html
                with self.assertRaisesRegex(
                    ValueError, "Suno metadata not found on track page."
                ):
                    self.module.fetch_suno_track_metadata(
                        "https://suno.com/song/00000000-0000-0000-0000-000000000000"
                    )


if __name__ == "__main__":
    unittest.main()
