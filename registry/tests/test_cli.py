"""CLI end-to-end: the real user surface, exercised through a subprocess."""
import json

import tempfile
import unittest
from pathlib import Path

from helpers import FIXTURES, REPO, run_cli

INVENTORY = str(FIXTURES / "inventories" / "public-gateway.json")
WORKSTATION = str(FIXTURES / "inventories" / "workstation-minimal.json")


class ValidateRegistryCommand(unittest.TestCase):
    def test_seed_registry_exits_zero(self):
        proc = run_cli("validate-registry")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["counts"]["controls"], 22)


class EvaluateCommand(unittest.TestCase):
    def test_evaluate_public_surface(self):
        proc = run_cli("evaluate", "--profile", "public-surface",
                       "--inventory", INVENTORY, "--as-of", "2026-10-17")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["as_of"], "2026-10-17")
        self.assertEqual(report["summary"]["needs_decision"], 2)
        self.assertEqual(report["summary"]["required"], 8)
        self.assertEqual(report["summary"]["total"], 10)

    def test_deterministic_stdout(self):
        first = run_cli("evaluate", "--profile", "public-surface",
                        "--inventory", INVENTORY, "--as-of", "2026-10-17")
        second = run_cli("evaluate", "--profile", "public-surface",
                         "--inventory", INVENTORY, "--as-of", "2026-10-17")
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)

    def test_out_file_matches_stdout(self):
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            out = Path(tmp) / "report.json"
            proc = run_cli("evaluate", "--profile", "public-surface",
                           "--inventory", INVENTORY, "--as-of", "2026-10-17",
                           "--out", str(out))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(out.read_text(encoding="utf-8"), proc.stdout)

    def test_multiple_profiles(self):
        proc = run_cli("evaluate", "--profile", "workstation", "--profile", "privileged-operator",
                       "--inventory", WORKSTATION, "--as-of", "2026-10-17")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["profiles"], ["privileged-operator", "workstation"])

    def test_supersession_resolution_via_cli(self):
        proc = run_cli("evaluate", "--profile", "workstation",
                       "--inventory", WORKSTATION, "--as-of", "2026-10-17")
        report = json.loads(proc.stdout)
        self.assertEqual(report["resolution"],
                         [{"profile": "workstation", "requested": "FMR-008", "resolved_to": "FMR-009"}])


class FailurePaths(unittest.TestCase):
    def test_invalid_inventory_exits_one(self):
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            bad = Path(tmp) / "bad-inventory.json"
            bad.write_text(json.dumps({"schema": "beyond-prompting/inventory@1",
                                       "secret_token": "x"}), encoding="utf-8")
            proc = run_cli("evaluate", "--profile", "workstation",
                           "--inventory", str(bad), "--as-of", "2026-10-17")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "FAIL")
        self.assertIn("inventory fails schema validation", payload["errors"][0]["detail"])

    def test_unknown_profile_exits_one(self):
        proc = run_cli("evaluate", "--profile", "no-such-profile",
                       "--inventory", INVENTORY, "--as-of", "2026-10-17")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("unknown profile", proc.stdout)

    def test_missing_as_of_is_usage_error(self):
        proc = run_cli("evaluate", "--profile", "workstation", "--inventory", INVENTORY)
        self.assertEqual(proc.returncode, 2)

    def test_malformed_as_of_is_usage_error(self):
        proc = run_cli("evaluate", "--profile", "workstation",
                       "--inventory", INVENTORY, "--as-of", "2026-13-99")
        self.assertEqual(proc.returncode, 2)

    def test_invalid_registry_exits_one_for_evaluate(self):
        import shutil
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            registry = Path(tmp) / "registry"
            registry.mkdir()
            for part in ("controls", "profiles", "schemas"):
                shutil.copytree(REPO / "registry" / part, registry / part)
            shutil.copy2(REPO / "registry" / "registry.json", registry / "registry.json")
            stale = json.loads((FIXTURES / "invalid" / "controls" / "fmr-810.json").read_text())
            (registry / "controls" / "fmr-810.json").write_text(json.dumps(stale), encoding="utf-8")
            proc = run_cli("--registry", str(registry), "evaluate", "--profile", "workstation",
                           "--inventory", INVENTORY, "--as-of", "2026-10-17")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("registry fails validation", proc.stdout)
            check = run_cli("--registry", str(registry), "validate-registry")
            self.assertEqual(check.returncode, 1)
            result = json.loads(check.stdout)
            self.assertTrue(any(e["code"] == "REG-VERIFICATION-STALE" for e in result["errors"]))


class ExportFormat(unittest.TestCase):
    def test_markdown_export_is_deterministic_and_complete(self):
        argv = ("evaluate", "--profile", "public-surface",
                "--inventory", INVENTORY, "--as-of", "2026-10-17", "--format", "markdown")
        first = run_cli(*argv)
        second = run_cli(*argv)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        text = first.stdout
        self.assertIn("# Applicability report", text)
        self.assertIn("## Summary", text)
        self.assertIn("| required | 8 |", text)
        self.assertIn("## needs_decision (2)", text)
        self.assertIn("version basis: illustrative", text)
        self.assertIn("`hermes_version.basis`", text)

    def test_markdown_out_file_matches_stdout(self):
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            out = Path(tmp) / "report.md"
            proc = run_cli("evaluate", "--profile", "public-surface",
                           "--inventory", INVENTORY, "--as-of", "2026-10-17",
                           "--format", "markdown", "--out", str(out))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(out.read_text(encoding="utf-8"), proc.stdout)

    def test_markdown_escapes_special_characters(self):
        from helpers import applicability
        loaded_report = json.loads(run_cli("evaluate", "--profile", "public-surface",
                                           "--inventory", INVENTORY,
                                           "--as-of", "2026-10-17").stdout)
        loaded_report["results"][0]["title"] = "a|b`c*d_e[f]g\\h"
        text = applicability.render_report_markdown(loaded_report)
        self.assertIn(r"a\|b\`c\*d\_e\[f\]g\\h", text)

    def test_json_export_is_byte_stable(self):
        argv = ("evaluate", "--profile", "public-surface",
                "--inventory", INVENTORY, "--as-of", "2026-10-17")
        self.assertEqual(run_cli(*argv).stdout, run_cli(*argv).stdout)


class CompareCommand(unittest.TestCase):
    def _report(self, directory, name, as_of):
        out = Path(directory) / name
        proc = run_cli("evaluate", "--profile", "public-surface",
                       "--inventory", INVENTORY, "--as-of", as_of, "--out", str(out))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return str(out)

    def test_identical_reports_same_context_no_changes(self):
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            a = self._report(tmp, "a.json", "2026-10-17")
            proc = run_cli("compare", a, a)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            diff = json.loads(proc.stdout)
            self.assertTrue(diff["same_context"])
            self.assertEqual(diff["changes"], [])
            self.assertNotIn("warning", diff)
            self.assertEqual(diff["summary"]["unchanged"], diff["summary"]["total_controls"])

    def test_different_as_of_is_context_bound_with_warning(self):
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            a = self._report(tmp, "a.json", "2026-10-17")
            b = self._report(tmp, "b.json", "2027-12-01")
            proc = run_cli("compare", a, b)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            diff = json.loads(proc.stdout)
            self.assertFalse(diff["same_context"])
            self.assertFalse(diff["context"]["as_of"]["equal"])
            self.assertTrue(diff["context"]["registry_digest"]["equal"])
            self.assertIn("not, by themselves", diff["warning"])
            modified = [c for c in diff["changes"] if c["change"] == "modified"]
            transitions = {(e["status"]["from"], e["status"]["to"]) for e in modified}
            # The eight decided controls go stale; the two conflicted controls
            # were already needs_decision and only gain the stale reason.
            self.assertEqual(transitions, {("required", "needs_decision"),
                                           ("needs_decision", "needs_decision")})
            for entry in modified:
                added_sources = {r["source"] for r in entry["reasons_added"]}
                self.assertIn("verification.stale", added_sources)

    def test_compare_markdown_and_determinism(self):
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            a = self._report(tmp, "a.json", "2026-10-17")
            b = self._report(tmp, "b.json", "2027-12-01")
            first = run_cli("compare", a, b, "--format", "markdown")
            second = run_cli("compare", a, b, "--format", "markdown")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertIn("# Applicability report comparison", first.stdout)
            self.assertIn("## Input context", first.stdout)
            self.assertIn("**Warning:**", first.stdout)
            self.assertIn("| as_of | 2026-10-17 | 2027-12-01 | no |", first.stdout)

    def test_malformed_report_exits_one(self):
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("not json", encoding="utf-8")
            good = self._report(tmp, "good.json", "2026-10-17")
            proc = run_cli("compare", str(bad), good)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("REPORT-LOAD", proc.stdout)

    def test_schema_violating_report_exits_one(self):
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            good = self._report(tmp, "good.json", "2026-10-17")
            bogus = Path(tmp) / "bogus.json"
            doc = json.loads(Path(good).read_text(encoding="utf-8"))
            doc["results"][0]["status"] = "bogus-status"
            bogus.write_text(json.dumps(doc), encoding="utf-8")
            proc = run_cli("compare", str(bogus), good)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("REPORT-SCHEMA", proc.stdout)

    def test_missing_report_file_exits_one(self):
        proc = run_cli("compare", "/nonexistent/a.json", "/nonexistent/b.json")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("REPORT-LOAD", proc.stdout)


class InputHardening(unittest.TestCase):
    def test_duplicate_keys_are_rejected_as_contradictory(self):
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            bad = Path(tmp) / "dup.json"
            bad.write_text(
                '{"schema": "beyond-prompting/inventory@1",'
                ' "deployment": {"kind": "workstation", "exposure": "loopback",'
                ' "unattended_jobs": true, "owner_model": "individual"},'
                ' "deployment": {"kind": "workstation", "exposure": "loopback",'
                ' "unattended_jobs": false, "owner_model": "individual"}}',
                encoding="utf-8")
            proc = run_cli("evaluate", "--profile", "workstation",
                           "--inventory", str(bad), "--as-of", "2026-10-17")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("duplicate key", proc.stdout)

    def test_oversized_inventory_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            big = Path(tmp) / "big.json"
            big.write_text('{"schema": "beyond-prompting/inventory@1", "pad": "'
                           + "x" * (5 * 1024 * 1024) + '"}', encoding="utf-8")
            proc = run_cli("evaluate", "--profile", "workstation",
                           "--inventory", str(big), "--as-of", "2026-10-17")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("limit", proc.stdout)

    def test_pathological_nesting_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="fmr-cli-") as tmp:
            deep = Path(tmp) / "deep.json"
            deep.write_text("[" * 100000 + "]" * 100000, encoding="utf-8")
            proc = run_cli("evaluate", "--profile", "workstation",
                           "--inventory", str(deep), "--as-of", "2026-10-17")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("nested too deeply", proc.stdout)


if __name__ == "__main__":
    unittest.main()
