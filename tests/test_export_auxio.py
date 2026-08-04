import sqlite3
import tempfile
import unittest
from pathlib import Path

from mutagen.id3 import ID3

import dekho.db as db
import export_auxio


def _write_minimal_mp3(path: Path) -> None:
    # Minimal MPEG frame so mutagen can attach ID3 tags.
    path.write_bytes(bytes.fromhex("fff340c4" + ("00" * 413)))


class FilesystemSafeNameTests(unittest.TestCase):
    def test_replaces_forbidden_characters(self):
        self.assertEqual(export_auxio.filesystem_safe_name("soft p/r"), "soft pr")
        self.assertEqual(
            export_auxio.filesystem_safe_name('a\\b:c*d?e"f<g>h|i'),
            "abcdefghi",
        )

    def test_trims_whitespace(self):
        self.assertEqual(export_auxio.filesystem_safe_name("  Ideas  "), "Ideas")


class AllocateUniqueFilenamesTests(unittest.TestCase):
    def test_appends_stable_suffix_for_duplicates(self):
        allocated = export_auxio.allocate_unique_filenames(["a/b", "ab", "Ideas"])
        self.assertEqual(allocated["a/b"], "ab")
        self.assertEqual(allocated["ab"], "ab-2")
        self.assertEqual(allocated["Ideas"], "Ideas")


class BuildM3u8Tests(unittest.TestCase):
    def test_relative_paths_and_header(self):
        content = export_auxio.build_m3u8_contents(
            ["track-1", "track-2"]
        )
        self.assertEqual(
            content,
            "#EXTM3U\n"
            "../Tracks/track-1.mp3\n"
            "../Tracks/track-2.mp3\n",
        )
        self.assertFalse(content.startswith("\ufeff"))


class FetchPlaylistExportDataTests(unittest.TestCase):
    def setUp(self):
        self._original_db_path = db.DB_PATH
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)
        db.DB_PATH = self.root / "test.sqlite3"
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self._original_db_path
        self._tempdir.cleanup()

    def test_only_includes_playlist_labeled_tracks(self):
        db.upsert_track(track_id="on-playlist", filepath="a.mp3", title="A")
        db.upsert_track(track_id="not-on-playlist", filepath="b.mp3", title="B")
        db.upsert_track_user_data(
            track_id="on-playlist",
            title_new="A renamed",
            notes="",
            remix_of="",
            labels=["playlist.mythical", "like.like1"],
        )
        db.upsert_track_user_data(
            track_id="not-on-playlist",
            title_new="",
            notes="",
            remix_of="",
            labels=["like.like2"],
        )

        connection = sqlite3.connect(db.DB_PATH)
        try:
            tracks, playlists = export_auxio.fetch_playlist_export_data(connection)
        finally:
            connection.close()

        self.assertEqual([t["track_id"] for t in tracks], ["on-playlist"])
        self.assertEqual(tracks[0]["title"], "A renamed")
        self.assertEqual(list(playlists.keys()), ["mythical"])
        self.assertEqual(playlists["mythical"], ["on-playlist"])

    def test_dedupes_track_within_playlist_and_preserves_order(self):
        db.upsert_track(
            track_id="t1",
            filepath="1.mp3",
            title="One",
            date_created="2026-01-01T00:00:00Z",
        )
        db.upsert_track(
            track_id="t2",
            filepath="2.mp3",
            title="Two",
            date_created="2026-02-01T00:00:00Z",
        )
        db.upsert_track_user_data(
            track_id="t1",
            title_new="",
            notes="",
            remix_of="",
            labels=["playlist.retro"],
        )
        db.upsert_track_user_data(
            track_id="t2",
            title_new="",
            notes="",
            remix_of="",
            labels=["playlist.retro", "playlist.western"],
        )

        connection = sqlite3.connect(db.DB_PATH)
        try:
            tracks, playlists = export_auxio.fetch_playlist_export_data(connection)
        finally:
            connection.close()

        self.assertEqual({t["track_id"] for t in tracks}, {"t1", "t2"})
        self.assertEqual(playlists["retro"], ["t1", "t2"])
        self.assertEqual(playlists["western"], ["t2"])


class ExportAuxioIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._original_db_path = db.DB_PATH
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)
        db.DB_PATH = self.root / "test.sqlite3"
        db.init_db()
        self.music_root = self.root / "music"
        self.music_root.mkdir()
        self.output_dir = self.root / "export_music"

    def tearDown(self):
        db.DB_PATH = self._original_db_path
        self._tempdir.cleanup()

    def test_export_writes_tracks_and_playlists(self):
        source = self.music_root / "song.mp3"
        _write_minimal_mp3(source)
        db.upsert_track(
            track_id="abc-123",
            filepath="song.mp3",
            title="Original Title",
            date_created="2026-01-01T00:00:00Z",
        )
        db.upsert_track_user_data(
            track_id="abc-123",
            title_new="Export Title",
            notes="",
            remix_of="",
            labels=["playlist.story", "playlist.other"],
        )

        exit_code = export_auxio.export_auxio(
            db_path=db.DB_PATH,
            music_root=self.music_root,
            output_dir=self.output_dir,
        )
        self.assertEqual(exit_code, 0)

        track_path = self.output_dir / "Tracks" / "abc-123.mp3"
        self.assertTrue(track_path.is_file())

        tags = ID3(track_path)
        self.assertEqual(tags.version, (2, 3, 0))
        self.assertEqual(str(tags["TIT2"]), "Export Title")
        self.assertEqual(str(tags["TPE1"]), "My Recordings")
        self.assertEqual(str(tags["TALB"]), "Unpublished Music")

        soft_pr = self.output_dir / "Playlists" / "soft pr.m3u8"
        other = self.output_dir / "Playlists" / "other.m3u8"
        self.assertTrue(soft_pr.is_file())
        self.assertTrue(other.is_file())
        self.assertEqual(
            soft_pr.read_text(encoding="utf-8"),
            "#EXTM3U\n../Tracks/abc-123.mp3\n",
        )
        self.assertEqual(
            other.read_text(encoding="utf-8"),
            "#EXTM3U\n../Tracks/abc-123.mp3\n",
        )


if __name__ == "__main__":
    unittest.main()
