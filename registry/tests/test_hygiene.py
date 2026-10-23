"""Hygiene: keep private identifier patterns out of the registry surface and
confirm the repository's own validator still passes with the registry added."""
import importlib.util
import re
import unittest
from pathlib import Path

from helpers import REPO, REGISTRY_DIR

# Same pattern family the repository validator uses (scripts/validate.py).
PATTERNS = (
    r"/opt/(?:data|vault)/",
    r"-100\d{8,}",
    r"ghp_[A-Za-z0-9]{20,}",
    r"\bsk-[A-Za-z0-9_-]{20,}",
    r"\bt_[0-9a-f]{8}\b",
    r"\b\d{8}_\d{6}_[0-9a-f]{8}\b",
)


class PrivatePatternScan(unittest.TestCase):
    def test_registry_surface_is_free_of_private_patterns(self):
        files = [p for p in REGISTRY_DIR.rglob("*")
                 if p.is_file() and p.suffix in (".json", ".md", ".py")]
        files.append(REPO / "scripts" / "applicability.py")
        findings = []
        for path in files:
            text = path.read_text(encoding="utf-8")
            for pattern in PATTERNS:
                if re.search(pattern, text):
                    findings.append((str(path.relative_to(REPO)), pattern))
        self.assertEqual(findings, [], findings)


class RepositoryValidator(unittest.TestCase):
    def test_existing_validator_passes(self):
        spec = importlib.util.spec_from_file_location("bp_validate", REPO / "scripts" / "validate.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.inspect(REPO)
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
