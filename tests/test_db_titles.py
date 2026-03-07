import tempfile
import unittest
from pathlib import Path

import dekho.db as db


class ScanTitleSyncTests(unittest.TestCase):
    def setUp(self):
        self._original_db_path = db.DB_PATH
        self._tempdir = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self._tempdir.name) / "test.sqlite3"
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self._original_db_path
        self._tempdir.cleanup()

    def test_scan_upsert_sets_file_title_and_user_title_new(self):
        db.upsert_track(
            track_id="track-1",
            filepath="a/track-1.mp3",
            title="From MP3",
        )

        details = db.get_track_details("track-1")
        self.assertIsNotNone(details)
        self.assertEqual(details["title"], "From MP3")
        self.assertEqual(details["title_new"], "From MP3")

    def test_scan_upsert_does_not_overwrite_existing_title_new(self):
        db.upsert_track(
            track_id="track-2",
            filepath="a/track-2.mp3",
            title="Initial MP3 Title",
        )
        db.upsert_track_user_data(
            track_id="track-2",
            title_new="Custom User Title",
            notes="",
        )

        db.upsert_track(
            track_id="track-2",
            filepath="a/track-2-renamed.mp3",
            title="Updated MP3 Title",
        )

        details = db.get_track_details("track-2")
        self.assertIsNotNone(details)
        self.assertEqual(details["title"], "Updated MP3 Title")
        self.assertEqual(details["title_new"], "Custom User Title")

    def test_scan_upsert_fills_title_new_when_existing_value_is_empty(self):
        db.upsert_track(
            track_id="track-3",
            filepath="a/track-3.mp3",
            title="Initial MP3 Title",
        )
        db.upsert_track_user_data(
            track_id="track-3",
            title_new="",
            notes="",
        )

        db.upsert_track(
            track_id="track-3",
            filepath="a/track-3.mp3",
            title="Rescanned MP3 Title",
        )

        details = db.get_track_details("track-3")
        self.assertIsNotNone(details)
        self.assertEqual(details["title"], "Rescanned MP3 Title")
        self.assertEqual(details["title_new"], "Rescanned MP3 Title")


if __name__ == "__main__":
    unittest.main()
