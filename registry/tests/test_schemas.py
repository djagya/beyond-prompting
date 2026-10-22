"""JSON Schema conformance: seed registry documents and targeted negative fixtures."""
import json
import unittest

import applicability
from helpers import FIXTURES, REGISTRY_DIR, fixture_registry, load_seed_registry


class SeedDocumentsConform(unittest.TestCase):
    def test_controls_conform(self):
        loaded = load_seed_registry()
        validator = loaded.schema_validators["control"]
        for cid, doc in loaded.controls.items():
            errors = applicability.schema_errors(validator, doc)
            self.assertEqual(errors, [], f"{cid}: {errors}")

    def test_profiles_conform(self):
        loaded = load_seed_registry()
        validator = loaded.schema_validators["profile"]
        for pid, doc in loaded.profiles.items():
            errors = applicability.schema_errors(validator, doc)
            self.assertEqual(errors, [], f"{pid}: {errors}")

    def test_manifest_conforms(self):
        loaded = load_seed_registry()
        errors = applicability.schema_errors(loaded.schema_validators["registry"], loaded.manifest)
        self.assertEqual(errors, [], errors)

    def test_inventories_conform(self):
        loaded = load_seed_registry()
        validator = loaded.schema_validators["inventory"]
        for path in sorted((FIXTURES / "inventories").glob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            errors = applicability.schema_errors(validator, doc)
            self.assertEqual(errors, [], f"{path.name}: {errors}")

    def test_evidence_example_conforms(self):
        loaded = load_seed_registry()
        doc = json.loads((REGISTRY_DIR / "examples" / "evidence-example.json").read_text(encoding="utf-8"))
        errors = applicability.schema_errors(loaded.schema_validators["evidence"], doc)
        self.assertEqual(errors, [], errors)


class LifecycleSupersessionSchemaRules(unittest.TestCase):
    """Regression: the if/then pairs must not fire vacuously."""

    def test_deprecated_without_successor_fails(self):
        with fixture_registry("invalid/controls/control-schema-deprecated-no-successor.json") as target:
            loaded = applicability.load_registry(target)
            result = applicability.validate_registry(loaded)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any(e["code"] == "REG-CONTROL-SCHEMA" for e in result["errors"]),
                            result["errors"])

    def test_active_with_successor_fails(self):
        with fixture_registry("invalid/controls/control-schema-active-with-successor.json") as target:
            loaded = applicability.load_registry(target)
            result = applicability.validate_registry(loaded)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any(e["code"] == "REG-CONTROL-SCHEMA" for e in result["errors"]),
                            result["errors"])


class NegativeControlSchemas(unittest.TestCase):
    CASES = [
        "control-schema-missing-rationale.json",
        "control-schema-bad-lifecycle.json",
        "control-schema-underspecified-predicate.json",
        "control-schema-bad-predicate-op.json",
    ]

    def test_under_specified_controls_fail_schema(self):
        for name in self.CASES:
            with self.subTest(name=name):
                with fixture_registry(f"invalid/controls/{name}") as target:
                    loaded = applicability.load_registry(target)
                    result = applicability.validate_registry(loaded)
                    self.assertEqual(result["status"], "FAIL", name)
                    schema_errors = [e for e in result["errors"] if e["code"] == "REG-CONTROL-SCHEMA"]
                    self.assertTrue(schema_errors, (name, result["errors"]))


if __name__ == "__main__":
    unittest.main()
