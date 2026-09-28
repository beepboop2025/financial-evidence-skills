"""A responsive service is not proof that the intended revision is deployed."""

import os
import unittest
from unittest.mock import patch

from financial_evidence.release import release_identity


class ReleaseTests(unittest.TestCase):
    def test_unknown_revision_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            result = release_identity()
        self.assertIsNone(result["source_commit"])
        self.assertEqual(result["release_id"], "unversioned-local")

    def test_full_revision_is_preserved_and_invalid_config_fails(self):
        revision = "a" * 40
        with patch.dict(os.environ, {"FINANCIAL_EVIDENCE_SOURCE_COMMIT": revision}):
            result = release_identity()
        self.assertEqual(result["source_commit"], revision)
        self.assertTrue(result["release_id"].endswith("+" + revision[:12]))
        for invalid in ("main", "abcdef", "A" * 40, "a" * 40 + "\n"):
            with (
                self.subTest(invalid=invalid),
                patch.dict(os.environ, {"FINANCIAL_EVIDENCE_SOURCE_COMMIT": invalid}),
                self.assertRaises(ValueError),
            ):
                release_identity()
