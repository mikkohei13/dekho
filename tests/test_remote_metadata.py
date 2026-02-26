import importlib.util
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

    def test_extracts_prompt_and_model_fields_from_flight_payload(self):
        html = (self.fixture_root / "temp_suno.html").read_text(
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
