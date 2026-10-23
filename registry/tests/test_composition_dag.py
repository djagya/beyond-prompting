"""Paired DAG-composition regressions.

A shared ancestor reached through two children is inheritance, not a cycle:
a valid diamond composes deterministically with each ancestor contributing
exactly once. True cycles, missing ancestors and explicit duplicate or
opposing-baseline declarations are still rejected, and repeated selection
of the same profile is idempotent.
"""
import json
import unittest

import applicability
from helpers import fixture_registry, load_inventory, load_seed_registry

AS_OF = "2026-10-17"

DIAMOND = [
    "valid/profiles/diamond-base.json",
    "valid/profiles/diamond-left.json",
    "valid/profiles/diamond-right.json",
    "valid/profiles/diamond-top.json",
]

OPPOSING = [
    "invalid/profiles/oppose-base.json",
    "invalid/profiles/oppose-left.json",
    "invalid/profiles/oppose-right.json",
    "invalid/profiles/oppose-top.json",
]


def codes(result):
    return {e["code"] for e in result["errors"]}


class ValidDiamond(unittest.TestCase):
    def test_diamond_validates_without_false_cycle_or_duplicate(self):
        with fixture_registry(*DIAMOND) as target:
            result = applicability.validate_registry(applicability.load_registry(target))
        self.assertEqual(result["status"], "PASS", result["errors"])

    def test_shared_ancestor_visited_once_in_first_visit_order(self):
        with fixture_registry(*DIAMOND) as target:
            loaded = applicability.load_registry(target)
            refs = applicability.flatten_profile(loaded.profiles, "diamond-top")
        self.assertEqual([owner for owner, _ in refs],
                         ["diamond-base", "diamond-left", "diamond-right", "diamond-top"])
        self.assertEqual([ref["control"] for _, ref in refs],
                         ["FMR-001", "FMR-002", "FMR-003", "FMR-004"])

    def test_diamond_evaluate_is_complete_and_deterministic(self):
        inventory = load_inventory("workstation-minimal.json")
        with fixture_registry(*DIAMOND) as target:
            loaded = applicability.load_registry(target)
            first = applicability.evaluate(loaded, ["diamond-top"], inventory, AS_OF)
            second = applicability.evaluate(loaded, ["diamond-top"], inventory, AS_OF)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(first["profiles"], ["diamond-top"])
        self.assertEqual(first["summary"]["total"], 4)
        attribution = {r["control"]: r["profiles"] for r in first["results"]}
        self.assertEqual(attribution, {
            "FMR-001": ["diamond-base"],
            "FMR-002": ["diamond-left"],
            "FMR-003": ["diamond-right"],
            "FMR-004": ["diamond-top"],
        })


class RejectionsPreserved(unittest.TestCase):
    def test_true_cycle_is_rejected_as_cycle_not_duplicate(self):
        with fixture_registry("invalid/profiles/fixture-cycle-a.json",
                              "invalid/profiles/fixture-cycle-b.json") as target:
            result = applicability.validate_registry(applicability.load_registry(target))
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("REG-PROFILE-CYCLE", codes(result))
        self.assertNotIn("REG-PROFILE-DUP", codes(result))

    def test_missing_ancestor_is_rejected_without_false_cycle(self):
        with fixture_registry("invalid/profiles/fixture-unknown-extends.json") as target:
            result = applicability.validate_registry(applicability.load_registry(target))
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("REG-PROFILE-REF", codes(result))
        self.assertNotIn("REG-PROFILE-CYCLE", codes(result))

    def test_opposing_baseline_in_independent_parents_is_rejected(self):
        """The same control declared with opposing baselines by two parents
        of one composition is a meaningful disagreement: it must be rejected
        with both declarations named, never silently merged away."""
        with fixture_registry(*OPPOSING) as target:
            result = applicability.validate_registry(applicability.load_registry(target))
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("REG-PROFILE-DUP", codes(result))
        self.assertNotIn("REG-PROFILE-CYCLE", codes(result))
        dupes = [e for e in result["errors"] if e["code"] == "REG-PROFILE-DUP"]
        self.assertTrue(any(
            e["target"] == "profiles/oppose-top.json"
            and "FMR-002" in e["detail"]
            and "oppose-left baseline=true" in e["detail"]
            and "oppose-right baseline=false" in e["detail"]
            for e in dupes), dupes)

    def test_flatten_profile_raises_distinct_cycle_error(self):
        with fixture_registry(*DIAMOND) as target:
            loaded = applicability.load_registry(target)
        chained = dict(loaded.profiles)
        # Direct self-extend.
        chained["diamond-top"] = dict(loaded.profiles["diamond-top"], extends=["diamond-top"])
        with self.assertRaises(applicability.ProfileCycleError):
            applicability.flatten_profile(chained, "diamond-top")
        # A self-extend listed next to an already-finished shared ancestor.
        chained["diamond-top"] = dict(loaded.profiles["diamond-top"])
        chained["diamond-left"] = dict(loaded.profiles["diamond-left"],
                                       extends=["diamond-base", "diamond-left"])
        with self.assertRaises(applicability.ProfileCycleError):
            applicability.flatten_profile(chained, "diamond-top")

    def test_missing_ancestor_raises_plain_registry_error(self):
        with fixture_registry(*DIAMOND) as target:
            loaded = applicability.load_registry(target)
        chained = dict(loaded.profiles)
        chained["diamond-top"] = dict(loaded.profiles["diamond-top"], extends=["diamond-ghost"])
        with self.assertRaises(applicability.RegistryError) as ctx:
            applicability.flatten_profile(chained, "diamond-top")
        self.assertNotIsInstance(ctx.exception, applicability.ProfileCycleError)


class RepeatedSelection(unittest.TestCase):
    def test_seed_repeated_profile_selection_is_idempotent(self):
        loaded = load_seed_registry()
        inventory = load_inventory("workstation-minimal.json")
        once = applicability.evaluate(loaded, ["workstation"], inventory, AS_OF)
        twice = applicability.evaluate(loaded, ["workstation", "workstation"], inventory, AS_OF)
        self.assertEqual(json.dumps(once, sort_keys=True), json.dumps(twice, sort_keys=True))

    def test_diamond_repeated_selection_is_idempotent(self):
        inventory = load_inventory("workstation-minimal.json")
        with fixture_registry(*DIAMOND) as target:
            loaded = applicability.load_registry(target)
            once = applicability.evaluate(loaded, ["diamond-top"], inventory, AS_OF)
            twice = applicability.evaluate(loaded, ["diamond-top", "diamond-top"],
                                           inventory, AS_OF)
            # Selecting an already-inherited ancestor adds no controls; only
            # the recorded selection itself differs.
            with_ancestor = applicability.evaluate(loaded, ["diamond-top", "diamond-base", "diamond-top"],
                                                   inventory, AS_OF)
        self.assertEqual(json.dumps(once, sort_keys=True), json.dumps(twice, sort_keys=True))
        self.assertEqual(with_ancestor["profiles"], ["diamond-base", "diamond-top"])
        once_results = json.dumps(once["results"], sort_keys=True)
        self.assertEqual(once_results, json.dumps(with_ancestor["results"], sort_keys=True))
        self.assertEqual(once["resolution"], with_ancestor["resolution"])
        self.assertEqual(once["summary"], with_ancestor["summary"])


if __name__ == "__main__":
    unittest.main()
