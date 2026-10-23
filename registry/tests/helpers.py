"""Shared helpers for the hardening registry test suite."""
import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REGISTRY_DIR = TESTS_DIR.parent
REPO = REGISTRY_DIR.parent
SCRIPTS = REPO / "scripts"
FIXTURES = TESTS_DIR / "fixtures"
INVALID = FIXTURES / "invalid"

sys.path.insert(0, str(SCRIPTS))

import applicability  # noqa: E402


@contextmanager
def fixture_registry(*inject):
    """Copy the seed registry into a temp dir and inject fixture files.

    Each inject argument is a path relative to registry/tests/fixtures;
    controls land in controls/, profiles in profiles/ by their schema marker.
    """
    with tempfile.TemporaryDirectory(prefix="fmr-test-registry-") as tmp:
        target = Path(tmp)
        (target / "controls").mkdir()
        (target / "profiles").mkdir()
        shutil.copytree(REGISTRY_DIR / "schemas", target / "schemas")
        shutil.copy2(REGISTRY_DIR / "registry.json", target / "registry.json")
        for path in (REGISTRY_DIR / "controls").glob("*.json"):
            shutil.copy2(path, target / "controls" / path.name)
        for path in (REGISTRY_DIR / "profiles").glob("*.json"):
            shutil.copy2(path, target / "profiles" / path.name)
        for rel in inject:
            src = FIXTURES / rel
            doc = json.loads(src.read_text(encoding="utf-8"))
            sub = "profiles" if src.parent.name == "profiles" else "controls"
            shutil.copy2(src, target / sub / src.name)
        yield target


def load_seed_registry():
    return applicability.load_registry(REGISTRY_DIR)


def load_inventory(name):
    return json.loads((FIXTURES / "inventories" / name).read_text(encoding="utf-8"))


def run_cli(*argv):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "applicability.py"), *argv],
        capture_output=True, text=True, cwd=str(REPO),
    )


def status_map(report):
    return {result["control"]: result for result in report["results"]}
