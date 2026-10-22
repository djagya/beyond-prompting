"""Applicability evaluator: statuses, precedence, determinism, supersession, conflicts."""
import copy
import json
import unittest

import applicability
from helpers import fixture_registry, load_inventory, load_seed_registry, status_map

AS_OF = "2026-10-17"


def evaluate(profiles, inventory, as_of=AS_OF):
    loaded = load_seed_registry()
    return applicability.evaluate(loaded, profiles, inventory, as_of)


class Statuses(unittest.TestCase):
    def test_public_surface_conflict_and_baselines(self):
        report = evaluate(["public-surface"], load_inventory("public-gateway.json"))
        statuses = {c: r["status"] for c, r in status_map(report).items()}
        self.assertEqual(statuses, {
            "FMR-001": "required", "FMR-002": "required", "FMR-005": "required",
            "FMR-009": "required", "FMR-010": "needs_decision", "FMR-011": "needs_decision",
            "FMR-012": "required", "FMR-013": "required",
        })
        by_id = status_map(report)
        self.assertEqual(by_id["FMR-010"]["conflicts_with"], ["FMR-011"])
        self.assertEqual(by_id["FMR-011"]["conflicts_with"], ["FMR-010"])
        for cid in ("FMR-010", "FMR-011"):
            sources = {r["source"] for r in by_id[cid]["reasons"]}
            self.assertIn("conflict.control", sources)
        self.assertEqual(report["summary"]["total"], 8)
        self.assertEqual(report["summary"]["needs_decision"], 2)

    def test_workstation_supersession_resolution(self):
        report = evaluate(["workstation"], load_inventory("workstation-minimal.json"))
        self.assertEqual(report["resolution"],
                         [{"profile": "workstation", "requested": "FMR-008", "resolved_to": "FMR-009"}])
        by_id = status_map(report)
        self.assertNotIn("FMR-008", by_id)
        self.assertEqual(by_id["FMR-009"]["status"], "required")
        self.assertEqual(by_id["FMR-009"]["baseline"], True)
        self.assertEqual(by_id["FMR-007"]["status"], "recommended")
        self.assertEqual(by_id["FMR-013"]["status"], "recommended")
        self.assertEqual(by_id["FMR-002"]["status"], "required")

    def test_predicate_false_is_not_applicable(self):
        report = evaluate(["private-server"], load_inventory("workstation-minimal.json"))
        by_id = status_map(report)
        self.assertEqual(by_id["FMR-003"]["status"], "not_applicable")
        sources = {r["source"] for r in by_id["FMR-003"]["reasons"]}
        self.assertEqual(sources, {"predicate.false"})
        # FMR-007 is universal (empty all_of) and baseline in private-server.
        self.assertEqual(by_id["FMR-007"]["status"], "required")

    def test_version_outside_verified_range_is_unsupported(self):
        report = evaluate(["private-server"], load_inventory("old-version-server.json"))
        by_id = status_map(report)
        self.assertEqual(by_id["FMR-003"]["status"], "unsupported")
        self.assertEqual(by_id["FMR-009"]["status"], "unsupported")
        detail = by_id["FMR-003"]["reasons"][0]["detail"]
        self.assertIn("0.7.2", detail)
        self.assertIn("0.8.0", detail)
        # Controls verified down to this version keep applying.
        self.assertEqual(by_id["FMR-001"]["status"], "required")
        self.assertEqual(by_id["FMR-013"]["status"], "recommended")

    def test_version_range_bounds_are_inclusive(self):
        inventory = load_inventory("old-version-server.json")
        inventory["hermes"]["version"] = "0.8.0"  # exact minimum of FMR-003 and FMR-009
        report = evaluate(["private-server"], inventory)
        by_id = status_map(report)
        self.assertEqual(by_id["FMR-003"]["status"], "required")
        self.assertEqual(by_id["FMR-009"]["status"], "required")
        inventory["hermes"]["version"] = "1.2.0"  # exact maximum
        report = evaluate(["private-server"], inventory)
        self.assertEqual(status_map(report)["FMR-003"]["status"], "required")

    def test_version_bounds_edge_outside(self):
        inventory = load_inventory("old-version-server.json")
        inventory["hermes"]["version"] = "0.7.9"  # one below the minimum
        report = evaluate(["private-server"], inventory)
        self.assertEqual(status_map(report)["FMR-003"]["status"], "unsupported")

    def test_missing_hermes_version_yields_needs_decision(self):
        inventory = {"schema": "beyond-prompting/inventory@1",
                     "deployment": {"kind": "workstation", "exposure": "loopback",
                                    "unattended_jobs": False, "owner_model": "individual"}}
        report = evaluate(["workstation"], inventory)
        by_id = status_map(report)
        self.assertEqual(by_id["FMR-007"]["status"], "needs_decision")
        detail = " ".join(r["detail"] for r in by_id["FMR-007"]["reasons"])
        self.assertIn("hermes.version", detail)

    def test_missing_facts_are_never_silently_false(self):
        report = evaluate(["messaging-gateway"], load_inventory("gateway-missing-config.json"))
        by_id = status_map(report)
        self.assertEqual(by_id["FMR-002"]["status"], "needs_decision")
        detail = " ".join(r["detail"] for r in by_id["FMR-002"]["reasons"])
        self.assertIn("config.redact_secrets", detail)
        self.assertEqual(by_id["FMR-009"]["status"], "needs_decision")
        detail = " ".join(r["detail"] for r in by_id["FMR-009"]["reasons"])
        self.assertIn("config.approvals_mode", detail)
        self.assertIn("config.unattended_mode", detail)
        # Present facts still decide other controls.
        self.assertEqual(by_id["FMR-012"]["status"], "required")
        self.assertEqual(by_id["FMR-011"]["status"], "required")
        self.assertEqual(by_id["FMR-005"]["status"], "not_applicable")

    def test_staleness_depends_on_supplied_as_of(self):
        fresh = evaluate(["workstation"], load_inventory("workstation-minimal.json"), "2026-10-17")
        by_id = status_map(fresh)
        self.assertEqual(by_id["FMR-007"]["status"], "recommended")
        self.assertFalse(any(r["source"] == "verification.stale"
                             for result in fresh["results"] for r in result["reasons"]))

        stale = evaluate(["workstation"], load_inventory("workstation-minimal.json"), "2027-12-01")
        by_id = status_map(stale)
        self.assertEqual(by_id["FMR-007"]["status"], "needs_decision")
        sources = {r["source"] for r in by_id["FMR-007"]["reasons"]}
        self.assertIn("verification.stale", sources)
        detail = " ".join(r["detail"] for r in by_id["FMR-007"]["reasons"])
        self.assertIn("as-of 2027-12-01", detail)
        self.assertEqual(stale["as_of"], "2027-12-01")

    def test_numeric_predicate_and_team_composition(self):
        report = evaluate(["team-runtime"], load_inventory("public-gateway.json"))
        by_id = status_map(report)
        self.assertEqual(by_id["FMR-014"]["status"], "required")  # users.count gte 2 is true
        self.assertEqual(by_id["FMR-014"]["profiles"], ["team-runtime"])
        # Inherited private-server baseline controls arrive through extends.
        self.assertEqual(by_id["FMR-003"]["status"], "required")
        self.assertEqual(by_id["FMR-003"]["profiles"], ["private-server"])
        self.assertEqual(by_id["FMR-006"]["status"], "recommended")
        self.assertEqual(report["summary"]["total"], 8)


class ProfileComposition(unittest.TestCase):
    def test_multi_profile_union_merges_baselines(self):
        report = evaluate(["workstation", "privileged-operator"], load_inventory("workstation-minimal.json"))
        by_id = status_map(report)
        fmr_007 = by_id["FMR-007"]
        self.assertEqual(fmr_007["baseline"], True)  # privileged-operator marks it baseline
        self.assertEqual(fmr_007["profiles"], ["privileged-operator", "workstation"])
        self.assertEqual(by_id["FMR-013"]["baseline"], True)
        self.assertEqual(by_id["FMR-002"]["profiles"], ["privileged-operator", "workstation"])

    def test_profile_order_does_not_change_report(self):
        inventory = load_inventory("workstation-minimal.json")
        first = evaluate(["workstation", "privileged-operator"], inventory)
        second = evaluate(["privileged-operator", "workstation"], inventory)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_no_control_bodies_in_profiles(self):
        loaded = load_seed_registry()
        for pid, profile in loaded.profiles.items():
            for ref in profile["controls"]:
                self.assertEqual(sorted(ref.keys()), sorted(["control", "baseline"]) + (
                    ["note"] if "note" in ref else []), pid)


class Determinism(unittest.TestCase):
    def test_same_inputs_identical_report(self):
        inventory = load_inventory("public-gateway.json")
        first = evaluate(["public-surface"], copy.deepcopy(inventory))
        second = evaluate(["public-surface"], copy.deepcopy(inventory))
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_registry_digest_tracks_content(self):
        with fixture_registry() as base_dir:
            base = applicability.load_registry(base_dir)
        with fixture_registry() as other_dir:
            path = other_dir / "controls" / "fmr-001.json"
            doc = json.loads(path.read_text(encoding="utf-8"))
            doc["title"] = "tampered title"
            path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            other = applicability.load_registry(other_dir)
        self.assertNotEqual(base.digest, other.digest)

    def test_registry_digest_stable_across_loads(self):
        with fixture_registry() as first_dir:
            first = applicability.load_registry(first_dir)
        second = load_seed_registry()
        self.assertEqual(first.digest, second.digest)

    def test_inventory_digest_tracks_content(self):
        loaded = load_seed_registry()
        a = load_inventory("public-gateway.json")
        b = copy.deepcopy(a)
        b["users"]["count"] = 4
        ra = applicability.evaluate(loaded, ["public-surface"], a, AS_OF)
        rb = applicability.evaluate(loaded, ["public-surface"], b, AS_OF)
        self.assertNotEqual(ra["inventory_digest"], rb["inventory_digest"])

    def test_report_validates_against_report_schema(self):
        loaded = load_seed_registry()
        report = applicability.evaluate(loaded, ["public-surface"], load_inventory("public-gateway.json"), AS_OF)
        errors = applicability.schema_errors(loaded.schema_validators["report"], report)
        self.assertEqual(errors, [], errors)


class PredicateLogic(unittest.TestCase):
    INVENTORY = {
        "schema": "beyond-prompting/inventory@1",
        "deployment": {"kind": "messaging-gateway", "exposure": "vpn",
                       "unattended_jobs": True, "owner_model": "team"},
        "users": {"count": 3, "admins": 1},
        "inputs": {"untrusted_content": False, "channels": ["messaging"]},
    }

    def ev(self, predicate):
        return applicability.evaluate_predicate(predicate, self.INVENTORY)

    def test_kleene_any_of_false_and_unknown_is_unknown(self):
        verdict, issues = self.ev({"any_of": [
            {"fact": "deployment.unattended_jobs", "op": "equals", "value": False},
            {"fact": "config.unattended_mode", "op": "equals", "value": "deny"},
        ]})
        self.assertIsNone(verdict)
        self.assertTrue(any("config.unattended_mode" in i for i in issues))

    def test_kleene_any_of_true_dominates(self):
        verdict, _ = self.ev({"any_of": [
            {"fact": "deployment.unattended_jobs", "op": "equals", "value": False},
            {"fact": "users.count", "op": "gte", "value": 2},
        ]})
        self.assertIs(verdict, True)

    def test_kleene_all_of_true_and_unknown_is_unknown(self):
        verdict, _ = self.ev({"all_of": [
            {"fact": "users.count", "op": "gte", "value": 2},
            {"fact": "messaging.connected", "op": "equals", "value": True},
        ]})
        self.assertIsNone(verdict)

    def test_kleene_all_of_false_dominates(self):
        verdict, _ = self.ev({"all_of": [
            {"fact": "users.count", "op": "gte", "value": 2},
            {"fact": "deployment.exposure", "op": "equals", "value": "public"},
        ]})
        self.assertIs(verdict, False)

    def test_not_preserves_unknown(self):
        verdict, _ = self.ev({"not": {"fact": "messaging.connected", "op": "equals", "value": True}})
        self.assertIsNone(verdict)

    def test_empty_all_of_is_vacuously_true(self):
        verdict, issues = self.ev({"all_of": []})
        self.assertIs(verdict, True)
        self.assertEqual(issues, [])

    def test_contains_requires_list_fact(self):
        verdict, issues = self.ev({"fact": "users.count", "op": "contains", "value": 3})
        self.assertIsNone(verdict)
        self.assertTrue(any("type mismatch" in i for i in issues))

    def test_contains_on_list(self):
        verdict, _ = self.ev({"fact": "inputs.channels", "op": "contains", "value": "messaging"})
        self.assertIs(verdict, True)

    def test_numeric_compare_rejects_non_numbers(self):
        verdict, issues = self.ev({"fact": "deployment.exposure", "op": "gt", "value": 1})
        self.assertIsNone(verdict)
        self.assertTrue(any("type mismatch" in i for i in issues))

    def test_missing_section_is_unknown_not_false(self):
        verdict, issues = self.ev({"fact": "config.redact_secrets", "op": "equals", "value": True})
        self.assertIsNone(verdict)
        self.assertIn("fact not present in inventory: config.redact_secrets", issues)

    def test_exists(self):
        verdict, _ = self.ev({"fact": "users.count", "op": "exists"})
        self.assertIs(verdict, True)
        verdict, _ = self.ev({"fact": "browser.enabled", "op": "exists"})
        self.assertIsNone(verdict)

    def test_not_equals_scalar(self):
        verdict, _ = self.ev({"fact": "deployment.exposure", "op": "not_equals", "value": "public"})
        self.assertIs(verdict, True)


if __name__ == "__main__":
    unittest.main()
