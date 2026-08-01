import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import export_mrss


class ExportMrssTests(unittest.TestCase):
    def test_media_content_url_includes_music_prefix(self):
        url = export_mrss.media_content_url("2025-11/Break the Silence.mp3")
        self.assertEqual(
            url,
            "https://www.biomi.org/dekho/music/2025-11/Break%20the%20Silence.mp3",
        )

    def test_build_mrss_includes_playlist_categories(self):
        tracks = [
            {
                "track_id": "track-1",
                "filepath": "2025-11/Break the Silence.mp3",
                "title": "Break the Silence",
                "duration": 215.4,
                "date_created": "2025-08-01T00:00:00Z",
                "date_added": None,
                "playlist_labels": ["soft p/r", "mythical"],
            }
        ]

        root = export_mrss.build_mrss(tracks)
        xml = ET.tostring(root, encoding="unicode")

        self.assertIn("<title>Dekho Music Library</title>", xml)
        self.assertIn("<title>Break the Silence</title>", xml)
        self.assertIn("<guid>track-1</guid>", xml)
        self.assertIn('duration="215"', xml)
        self.assertIn("media:category", xml)
        self.assertIn("soft p/r", xml)
        self.assertIn("mythical", xml)
        self.assertIn(
            "https://www.biomi.org/dekho/music/2025-11/Break%20the%20Silence.mp3",
            xml,
        )

    def test_write_mrss_creates_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "dekho.rss"
            export_mrss.write_mrss(
                output_path,
                [
                    {
                        "track_id": "track-1",
                        "filepath": "2026-02/Song.mp3",
                        "title": "Song",
                        "duration": 100,
                        "date_created": "2026-02-01T12:00:00Z",
                        "date_added": None,
                        "playlist_labels": ["other"],
                    }
                ],
            )
            self.assertTrue(output_path.exists())
            content = output_path.read_text(encoding="utf-8")
            self.assertIn('<?xml version=', content)
            self.assertIn("<rss", content)

    def test_copy_track_files_preserves_subfolders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            music_root = root / "music"
            output_music_dir = root / "export_music" / "music"
            source = music_root / "2025-11" / "Break the Silence.mp3"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"fake-mp3")

            copied, missing = export_mrss.copy_track_files(
                [
                    {
                        "track_id": "track-1",
                        "filepath": "2025-11/Break the Silence.mp3",
                    }
                ],
                music_root=music_root,
                output_music_dir=output_music_dir,
            )

            destination = output_music_dir / "2025-11" / "Break the Silence.mp3"
            self.assertEqual(copied, 1)
            self.assertEqual(missing, [])
            self.assertTrue(destination.is_file())
            self.assertEqual(destination.read_bytes(), b"fake-mp3")


if __name__ == "__main__":
    unittest.main()
