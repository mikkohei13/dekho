import tempfile
import unittest
from pathlib import Path

import dekho.db as db


class DbLabelQueryTests(unittest.TestCase):
    def setUp(self):
        self._original_db_path = db.DB_PATH
        self._tempdir = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self._tempdir.name) / "test.sqlite3"
        db.init_db()
        db.upsert_track(track_id="a-track", filepath="music/a.mp3", title="A")
        db.upsert_track(track_id="b-track", filepath="music/b.mp3", title="B")

    def tearDown(self):
        db.DB_PATH = self._original_db_path
        self._tempdir.cleanup()

    def test_matching_all_labels_ignores_duplicates_in_filter(self):
        db.upsert_track_user_data(
            track_id="a-track",
            title_new="A",
            notes="",
            labels=["like.like1", "playlist.story"],
        )
        db.upsert_track_user_data(
            track_id="b-track",
            title_new="B",
            notes="",
            labels=["like.like1"],
        )

        match_ids = db.get_track_ids_matching_all_labels(
            ["like.like1", "playlist.story", "playlist.story"]
        )
        self.assertEqual(match_ids, ["a-track"])

    def test_replace_track_labels_rejects_unknown_label_key(self):
        with db.get_connection() as connection:
            with self.assertRaisesRegex(ValueError, "Unknown label key"):
                db.replace_track_labels(
                    connection=connection,
                    track_id="a-track",
                    labels=["not.a.real.label"],
                )


if __name__ == "__main__":
    unittest.main()
