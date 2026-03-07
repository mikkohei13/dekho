import unittest

from dekho.labels import (
    get_allowed_label_keys,
    get_label_catalog,
    iter_label_definitions,
    normalize_label_keys,
)


class NormalizeLabelKeysTests(unittest.TestCase):
    def test_valid_keys_pass_through(self):
        allowed = sorted(get_allowed_label_keys())[:2]
        self.assertEqual(normalize_label_keys(allowed), allowed)

    def test_deduplicates(self):
        key = next(iter(get_allowed_label_keys()))
        self.assertEqual(normalize_label_keys([key, key, key]), [key])

    def test_empty_list(self):
        self.assertEqual(normalize_label_keys([]), [])

    def test_unknown_key_raises(self):
        with self.assertRaises(ValueError, msg="unknown label"):
            normalize_label_keys(["nonexistent.key"])

    def test_non_list_raises(self):
        with self.assertRaises(ValueError, msg="labels must be a list"):
            normalize_label_keys("like.like0")

    def test_non_string_element_raises(self):
        with self.assertRaises(ValueError, msg="each label must be a string"):
            normalize_label_keys([123])


class LabelCatalogConsistencyTests(unittest.TestCase):
    def test_allowed_keys_non_empty(self):
        self.assertGreater(len(get_allowed_label_keys()), 0)

    def test_iter_definitions_matches_allowed_keys(self):
        from_iter = {key for key, _, _ in iter_label_definitions()}
        self.assertEqual(from_iter, get_allowed_label_keys())

    def test_catalog_categories_have_labels(self):
        for entry in get_label_catalog():
            self.assertIn("category", entry)
            self.assertIsInstance(entry["labels"], list)
            self.assertGreater(len(entry["labels"]), 0)

    def test_all_keys_have_dotted_format(self):
        for key in get_allowed_label_keys():
            self.assertIn(".", key, f"label key missing dot separator: {key}")


if __name__ == "__main__":
    unittest.main()
