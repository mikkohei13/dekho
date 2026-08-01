import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import dekho.db as db
from dekho.app import create_app


class AppRouteContractTests(unittest.TestCase):
    def setUp(self):
        self._original_db_path = db.DB_PATH
        self._tempdir = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self._tempdir.name) / "test.sqlite3"
        db.init_db()
        db.upsert_track(
            track_id="track-1",
            filepath="music/track-1.mp3",
            title="Track One",
            url="https://suno.com/song/track-1",
        )
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        db.DB_PATH = self._original_db_path
        self._tempdir.cleanup()

    def test_get_track_details_includes_label_catalog_contract(self):
        response = self.client.get("/api/tracks/track-1")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["track_id"], "track-1")
        self.assertIn("labels", payload)
        self.assertIn("label_catalog", payload)
        self.assertIsInstance(payload["label_catalog"], list)

    def test_save_user_data_updates_payload_fields(self):
        response = self.client.post(
            "/api/tracks/track-1/user-data",
            json={
                "title_new": "Renamed Track",
                "notes": "Needs review",
                "remix_of": "fe9019aa-debb-4c72-859d-589a38b44835",
                "labels": ["like.like2", "playlist.story"],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["title_new"], "Renamed Track")
        self.assertEqual(payload["notes"], "Needs review")
        self.assertEqual(
            payload["remix_of"],
            "fe9019aa-debb-4c72-859d-589a38b44835",
        )
        self.assertEqual(payload["labels"], ["like.like2", "playlist.story"])
        self.assertIn("label_catalog", payload)

    def test_fetch_remote_data_merges_remote_fields(self):
        remote_payload = {
            "prompt": "A lyrical prompt",
            "tags": "ambient",
            "negative_tags": "harsh",
            "has_cover_clip_id": True,
            "major_model_version": "v5",
            "model_name": "chirp-crow",
            "persona_name": "default",
        }
        with patch("dekho.app.fetch_suno_track_metadata", return_value=remote_payload):
            response = self.client.post("/api/tracks/track-1/remote-data")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["track_id"], "track-1")
        self.assertEqual(payload["tags"], "ambient")
        self.assertEqual(payload["model_name"], "chirp-crow")
        self.assertIn("label_catalog", payload)

    def test_overview_page_renders_feature_icons(self):
        db.upsert_track_user_data(
            track_id="track-1",
            title_new="Track One",
            notes="some notes",
            remix_of="fe9019aa-debb-4c72-859d-589a38b44835",
            labels=["like.like2", "playlist.story", "type.instrumental"],
        )
        db.upsert_track_remote_data(
            track_id="track-1",
            prompt="lyrics",
            tags="ambient",
            negative_tags=None,
            has_cover_clip_id=False,
            major_model_version=None,
            model_name=None,
            persona_name=None,
        )

        response = self.client.get("/overview")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Track One", html)
        self.assertIn("✎", html)
        self.assertIn("↻", html)
        self.assertIn("≣", html)
        self.assertIn("◈", html)
        self.assertIn("✦", html)
        self.assertIn("★★", html)
        self.assertIn("♪", html)
        self.assertIn('class="col-icon stars like"', html)


if __name__ == "__main__":
    unittest.main()
