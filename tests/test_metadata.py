import unittest

from dekho.metadata import _stringify_tag_value, _track_id_from_url


class TrackIdFromUrlTests(unittest.TestCase):
    def test_full_suno_url(self):
        url = "https://suno.com/song/25701027-1be7-4510-a9c4-078c936cd915"
        self.assertEqual(
            _track_id_from_url(url), "25701027-1be7-4510-a9c4-078c936cd915"
        )

    def test_alternate_domain_with_song_path(self):
        url = "https://other.example.com/song/abc-123"
        self.assertEqual(_track_id_from_url(url), "abc-123")

    def test_url_without_song_path_returns_whole_url(self):
        url = "https://example.com/track/abc-123"
        self.assertEqual(_track_id_from_url(url), url)


class StringifyTagValueTests(unittest.TestCase):
    def test_string_passthrough(self):
        self.assertEqual(_stringify_tag_value("hello"), "hello")

    def test_list_joined(self):
        self.assertEqual(_stringify_tag_value(["a", "b", "c"]), "a, b, c")

    def test_tuple_joined(self):
        self.assertEqual(_stringify_tag_value(("x", "y")), "x, y")

    def test_non_string_converted(self):
        self.assertEqual(_stringify_tag_value(42), "42")


if __name__ == "__main__":
    unittest.main()
