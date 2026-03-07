import tempfile
import unittest
from pathlib import Path

import dekho.db as db
from dekho.scan import run_scan


class ScanEdgeCaseTests(unittest.TestCase):
    def setUp(self):
        self._original_db_path = db.DB_PATH
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)
        db.DB_PATH = self.root / "test.sqlite3"
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self._original_db_path
        self._tempdir.cleanup()

    def test_run_scan_reports_db_rows_missing_from_music_folder(self):
        db.upsert_track(
            track_id="missing-track",
            filepath="missing-folder/missing.mp3",
            title="Missing Track",
        )
        music_dir = self.root / "music"
        music_dir.mkdir(parents=True, exist_ok=True)

        result = run_scan(music_dir)
        self.assertEqual(result["scanned"], 0)
        self.assertEqual(result["stored"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(len(result["warnings_missing_from_folder"]), 1)
        warning = result["warnings_missing_from_folder"][0]
        self.assertEqual(warning["track_id"], "missing-track")
        self.assertEqual(warning["missing_identifier"], "yes")
        self.assertEqual(warning["missing_path"], "yes")


if __name__ == "__main__":
    unittest.main()
