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


if __name__ == "__main__":
    unittest.main()
