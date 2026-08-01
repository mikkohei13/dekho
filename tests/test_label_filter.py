import unittest

from dekho.label_filter import track_matches_selected_labels


class LabelFilterMatchTests(unittest.TestCase):
    def test_empty_selection_matches_any_track(self):
        self.assertTrue(
            track_matches_selected_labels(["like.like1"], [], match_mode="or")
        )
        self.assertTrue(
            track_matches_selected_labels(["like.like1"], [], match_mode="and")
        )

    def test_or_mode_matches_any_label_within_category(self):
        track_keys = ["like.like2", "playlist.story"]
        selected = ["like.like2", "like.like3"]
        self.assertTrue(
            track_matches_selected_labels(track_keys, selected, match_mode="or")
        )

    def test_or_mode_requires_all_categories(self):
        track_keys = ["like.like2"]
        selected = ["like.like2", "like.like3", "playlist.story"]
        self.assertFalse(
            track_matches_selected_labels(track_keys, selected, match_mode="or")
        )

        track_keys = ["like.like2", "playlist.story"]
        self.assertTrue(
            track_matches_selected_labels(track_keys, selected, match_mode="or")
        )

    def test_and_mode_requires_every_selected_label(self):
        track_keys = ["like.like2", "playlist.story"]
        selected = ["like.like2", "like.like3", "playlist.story"]
        self.assertFalse(
            track_matches_selected_labels(track_keys, selected, match_mode="and")
        )

        track_keys = ["like.like2", "like.like3", "playlist.story"]
        self.assertTrue(
            track_matches_selected_labels(track_keys, selected, match_mode="and")
        )

    def test_default_match_mode_is_or(self):
        track_keys = ["like.like3"]
        selected = ["like.like2", "like.like3"]
        self.assertTrue(track_matches_selected_labels(track_keys, selected))


if __name__ == "__main__":
    unittest.main()
