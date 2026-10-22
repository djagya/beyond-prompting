"""Semantic registry validation: every negative fixture fails with its own error code."""
import unittest

import applicability
from helpers import fixture_registry, load_seed_registry


class SeedRegistryPasses(unittest.TestCase):
    def test_seed_registry_passes(self):
        result = applicability.validate_registry(load_seed_registry())
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["counts"]["controls"], 14)
        self.assertEqual(result["counts"]["profiles"], 7)
        self.assertEqual(result["counts"]["deprecated"], 1)


class NegativeFixtures(unittest.TestCase):
    CASES = [
        ("invalid/controls/fmr-810.json", "REG-VERIFICATION-STALE"),
        ("invalid/controls/fmr-811.json", "REG-VERIFICATION-FUTURE"),
        ("invalid/controls/fmr-812.json", "REG-VERSION-RANGE"),
        ("invalid/controls/fmr-813.json", "REG-CONFLICT-ASYM"),
        ("invalid/controls/fmr-814.json", "REG-CONTROL-REF"),
        ("invalid/controls/fmr-815.json", "REG-CONFLICT-SELF"),
        ("invalid/controls/fmr-816.json", "REG-CONTROL-REF"),
        ("invalid/controls/fmr-818.json", "REG-SUPERSESSION-MISMATCH"),
        ("invalid/controls/control-stem-mismatch.json", "REG-CONTROL-STEM"),
        ("invalid/profiles/fixture-unknown-control.json", "REG-CONTROL-REF"),
        ("invalid/profiles/fixture-unknown-extends.json", "REG-PROFILE-REF"),
        ("invalid/profiles/fixture-duplicate-resolved.json", "REG-PROFILE-DUP"),
        ("invalid/profiles/profile-stem-mismatch.json", "REG-PROFILE-STEM"),
    ]

    def test_targeted_failure_codes(self):
        for fixture, code in self.CASES:
            with self.subTest(fixture=fixture):
                with fixture_registry(fixture) as target:
                    loaded = applicability.load_registry(target)
                    result = applicability.validate_registry(loaded)
                    self.assertEqual(result["status"], "FAIL", fixture)
                    matches = [e for e in result["errors"] if e["code"] == code]
                    self.assertTrue(matches, (fixture, code, result["errors"]))

    def test_superseded_by_retired_control_fails(self):
        with fixture_registry("invalid/controls/fmr-880.json",
                              "invalid/controls/fmr-817.json") as target:
            result = applicability.validate_registry(applicability.load_registry(target))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(e["code"] == "REG-SUPERSEDED-BY-LIFECYCLE" for e in result["errors"]),
                        result["errors"])

    def test_supersession_cycle_fails(self):
        with fixture_registry("invalid/controls/fmr-819.json",
                              "invalid/controls/fmr-820.json") as target:
            result = applicability.validate_registry(applicability.load_registry(target))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(e["code"] == "REG-SUPERSESSION-CYCLE" for e in result["errors"]),
                        result["errors"])

    def test_profile_extend_cycle_fails(self):
        with fixture_registry("invalid/profiles/fixture-cycle-a.json",
                              "invalid/profiles/fixture-cycle-b.json") as target:
            result = applicability.validate_registry(applicability.load_registry(target))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(e["code"] == "REG-PROFILE-CYCLE" for e in result["errors"]),
                        result["errors"])

    def test_profile_reference_to_retired_control_fails(self):
        with fixture_registry("invalid/controls/fmr-880.json",
                              "invalid/profiles/fixture-retired-ref.json") as target:
            result = applicability.validate_registry(applicability.load_registry(target))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(e["code"] == "REG-PROFILE-REF-LIFECYCLE" for e in result["errors"]),
                        result["errors"])

    def test_unreferenced_retired_control_alone_is_legal(self):
        """Retirement is a terminal lifecycle state, not itself a defect."""
        with fixture_registry("invalid/controls/fmr-880.json") as target:
            result = applicability.validate_registry(applicability.load_registry(target))
        self.assertEqual(result["status"], "PASS", result["errors"])

    def test_duplicate_control_id_fails_at_load(self):
        with fixture_registry("invalid/controls/fmr-821.json",
                              "invalid/controls/fmr-821b.json") as target:
            with self.assertRaises(applicability.RegistryError) as ctx:
                applicability.load_registry(target)
        self.assertIn("duplicate control id", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
