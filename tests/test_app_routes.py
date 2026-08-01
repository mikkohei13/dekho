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
                "labels": ["like.like2", "playlist.story"],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["title_new"], "Renamed Track")
        self.assertEqual(payload["notes"], "Needs review")
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

    def test_filter_by_labels_returns_matching_track_ids(self):
        db.upsert_track(
            track_id="track-2",
            filepath="music/track-2.mp3",
            title="Track Two",
        )
        db.upsert_track_user_data(
            track_id="track-1",
            title_new="Track One",
            notes="",
            labels=["like.like1", "playlist.story"],
        )
        db.upsert_track_user_data(
            track_id="track-2",
            title_new="Track Two",
            notes="",
            labels=["like.like1"],
        )

        response = self.client.post(
            "/api/tracks/filter-by-labels",
            json={"labels": ["like.like1", "playlist.story"]},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["track_ids"], ["track-1"])


if __name__ == "__main__":
    unittest.main()
