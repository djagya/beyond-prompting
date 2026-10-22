#!/usr/bin/env python3
"""Hardening registry: registry validation and deterministic applicability evaluation.

Reads a registry directory (manifest, controls/, profiles/, schemas/) and a
metadata-safe inventory, and answers one question per control: is it required,
recommended, not_applicable, needs_decision or unsupported for this deployment?

Contract:
- Deterministic: the report is a pure function of the registry bytes, the
  selected profiles, the inventory bytes and the supplied as-of date. No
  wall-clock time, no randomness, no host or runtime inspection, no writes.
- Missing facts never evaluate to false: a predicate over absent or
  type-mismatched inventory facts yields UNKNOWN and the control surfaces as
  needs_decision naming the undecidable facts.
- A Hermes version outside every verified range of a control yields
  unsupported, never a silent pass.
- The evaluator never applies a control; applying is a separate, authorized act.

Requires the jsonschema package (validated offline against local schema
documents; no network retrieval ever happens).

Exit codes: 0 success, 1 validation or evaluation failure, 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry as SchemaRegistry, Resource
    from referencing.jsonschema import DRAFT202012
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        f"Dependency gap: {exc}. This tool needs the 'jsonschema' package "
        "(with 'referencing'). Do not auto-install; use an authorized environment."
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_BASE = "https://beyond-prompting.example/registry/schemas/"
STATUS_VALUES = ("required", "recommended", "not_applicable", "needs_decision", "unsupported")


class RegistryError(Exception):
    """Raised when a structurally valid registry is semantically unusable."""


class ProfileCycleError(RegistryError):
    """Raised when a profile reaches itself through extends (a true cycle).

    A shared ancestor reached through two different children is normal DAG
    inheritance, not a cycle, and never raises this.
    """


@dataclass
class LoadedRegistry:
    manifest: dict
    controls: dict            # control id -> control document
    profiles: dict            # profile id -> profile document
    control_files: dict       # control id -> file name inside controls/
    profile_files: dict       # profile id -> file name inside profiles/
    digest: str
    schema_validators: dict = field(default_factory=dict)


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest_of(obj) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def load_schema_validators(registry_dir: Path) -> dict:
    """Build offline validators for every schema document in registry_dir/schemas."""
    schema_dir = registry_dir / "schemas"
    if not schema_dir.is_dir():
        raise RegistryError(f"schemas directory not found: {schema_dir}")
    resources = []
    for path in sorted(schema_dir.glob("*.schema.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RegistryError(f"schema file is not valid JSON: {path.name}: {exc}") from exc
        if "$id" not in doc:
            raise RegistryError(f"schema file missing $id: {path.name}")
        resources.append((doc["$id"], Resource.from_contents(doc, default_specification=DRAFT202012)))
    resource_map = SchemaRegistry().with_resources(resources)
    format_checker = Draft202012Validator.FORMAT_CHECKER
    validators = {}
    for name in ("control", "profile", "inventory", "report", "evidence", "registry"):
        ref = {"$ref": SCHEMA_BASE + name + ".schema.json"}
        validators[name] = Draft202012Validator(ref, registry=resource_map, format_checker=format_checker)
    return validators


def schema_errors(validator, instance) -> list:
    errors = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: (list(e.absolute_path), e.message)):
        location = "$" + "".join(f"[{part!r}]" if isinstance(part, str) else f"[{part}]" for part in err.absolute_path)
        errors.append(f"{location}: {err.message}")
    return errors


def load_registry(registry_dir: Path) -> LoadedRegistry:
    registry_dir = Path(registry_dir)
    manifest_path = registry_dir / "registry.json"
    if not manifest_path.is_file():
        raise RegistryError(f"registry manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RegistryError(f"registry manifest is not valid JSON: {exc}") from exc

    controls = {}
    control_files = {}
    for path in sorted((registry_dir / "controls").glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RegistryError(f"control file is not valid JSON: {path.name}: {exc}") from exc
        cid = doc.get("id") if isinstance(doc, dict) else None
        if not isinstance(cid, str):
            raise RegistryError(f"control file has no id: {path.name}")
        if cid in controls:
            raise RegistryError(f"duplicate control id {cid} (files {control_files[cid]} and {path.name})")
        controls[cid] = doc
        control_files[cid] = path.name

    profiles = {}
    profile_files = {}
    for path in sorted((registry_dir / "profiles").glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RegistryError(f"profile file is not valid JSON: {path.name}: {exc}") from exc
        pid = doc.get("id") if isinstance(doc, dict) else None
        if not isinstance(pid, str):
            raise RegistryError(f"profile file has no id: {path.name}")
        if pid in profiles:
            raise RegistryError(f"duplicate profile id {pid}")
        profiles[pid] = doc
        profile_files[pid] = path.name

    digest_payload = {
        "manifest": manifest,
        "controls": [controls[k] for k in sorted(controls)],
        "profiles": [profiles[k] for k in sorted(profiles)],
    }
    return LoadedRegistry(
        manifest=manifest,
        controls=controls,
        profiles=profiles,
        control_files=control_files,
        profile_files=profile_files,
        digest=digest_of(digest_payload),
        schema_validators=load_schema_validators(registry_dir),
    )


def _parse_version(value: str):
    return tuple(int(part) for part in value.split("."))


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


# ---------------------------------------------------------------------------
# Semantic registry validation
# ---------------------------------------------------------------------------

def validate_registry(loaded: LoadedRegistry) -> dict:
    """Full validation: JSON Schema per document plus referential semantics.

    Invalid, stale, contradictory or under-specified content fails here with a
    stable error code per finding.
    """
    errors = []

    def add(code, target, detail):
        errors.append({"code": code, "target": target, "detail": detail})

    manifest = loaded.manifest
    merrors = schema_errors(loaded.schema_validators["registry"], manifest)
    for msg in merrors:
        add("REG-MANIFEST-SCHEMA", "registry.json", msg)
    if merrors:
        return {"status": "FAIL", "errors": errors,
                "counts": {"controls": len(loaded.controls), "profiles": len(loaded.profiles)}}

    registry_as_of = _parse_date(manifest["as_of"])
    max_age = manifest["policy"]["max_verification_age_days"]

    for cid in sorted(loaded.controls):
        control = loaded.controls[cid]
        fname = loaded.control_files.get(cid, f"{cid.lower()}.json")
        target = f"controls/{fname}"
        for msg in schema_errors(loaded.schema_validators["control"], control):
            add("REG-CONTROL-SCHEMA", target, msg)
        if Path(fname).stem != cid.lower():
            add("REG-CONTROL-STEM", target,
                f"id {cid} does not match file stem {Path(fname).stem!r}")
        for rng in control.get("hermes_versions", {}).get("verified", []):
            if _parse_version(rng["minimum"]) > _parse_version(rng["maximum"]):
                add("REG-VERSION-RANGE", target,
                    f"inverted range {rng['minimum']}..{rng['maximum']}")
        lv = control.get("last_verification", {})
        if isinstance(lv.get("date"), str):
            try:
                lv_date = _parse_date(lv["date"])
            except ValueError:
                add("REG-VERIFICATION-DATE", target, f"unparseable date {lv['date']!r}")
            else:
                if lv_date > registry_as_of:
                    add("REG-VERIFICATION-FUTURE", target,
                        f"last verification {lv_date} is after registry as-of {registry_as_of}")
                elif (registry_as_of - lv_date).days > max_age:
                    add("REG-VERIFICATION-STALE", target,
                        f"last verification {lv_date} is {(registry_as_of - lv_date).days} days old; "
                        f"policy allows {max_age}")

    for pid in sorted(loaded.profiles):
        profile = loaded.profiles[pid]
        fname = loaded.profile_files.get(pid, f"{pid}.json")
        target = f"profiles/{fname}"
        for msg in schema_errors(loaded.schema_validators["profile"], profile):
            add("REG-PROFILE-SCHEMA", target, msg)
        if Path(fname).stem != pid:
            add("REG-PROFILE-STEM", target,
                f"id {pid} does not match file stem {Path(fname).stem!r}")

    controls = loaded.controls
    profiles = loaded.profiles

    for cid in sorted(controls):
        control = controls[cid]
        target = f"controls/{cid.lower()}.json"
        for entry in control.get("conflicts", []):
            other = entry["control"]
            if other == cid:
                add("REG-CONFLICT-SELF", target, "control lists itself as a conflict")
            elif other not in controls:
                add("REG-CONTROL-REF", target, f"conflict references unknown control {other}")
            else:
                back = [c["control"] for c in controls[other].get("conflicts", [])]
                if cid not in back:
                    add("REG-CONFLICT-ASYM", target,
                        f"conflict with {other} is not declared by {other}")
        sup = control.get("supersession", {})
        for other in sup.get("supersedes", []):
            if other not in controls:
                add("REG-CONTROL-REF", target, f"supersedes unknown control {other}")
            elif controls[other].get("supersession", {}).get("superseded_by") != cid:
                add("REG-SUPERSESSION-MISMATCH", target,
                    f"supersedes {other} but {other} does not name {cid} as successor")
        successor = sup.get("superseded_by")
        if successor is not None:
            if successor not in controls:
                add("REG-CONTROL-REF", target, f"superseded_by references unknown control {successor}")
            elif controls[successor].get("lifecycle") != "active":
                add("REG-SUPERSEDED-BY-LIFECYCLE", target,
                    f"successor {successor} has lifecycle {controls[successor].get('lifecycle')!r}, must be active")
            elif cid not in controls[successor].get("supersession", {}).get("supersedes", []):
                add("REG-SUPERSESSION-MISMATCH", target,
                    f"superseded_by {successor} but {successor} does not list {cid} in supersedes")

    # Supersession acyclicity: follow every deprecated chain once.
    for cid in sorted(controls):
        target = f"controls/{cid.lower()}.json"
        seen = set()
        current = cid
        while current in controls and controls[current].get("lifecycle") == "deprecated":
            if current in seen:
                add("REG-SUPERSESSION-CYCLE", target, f"supersession cycle reached {current} twice")
                break
            seen.add(current)
            nxt = controls[current].get("supersession", {}).get("superseded_by")
            if nxt is None:
                break  # schema already flags deprecated-without-successor
            current = nxt

    for pid in sorted(profiles):
        profile = profiles[pid]
        target = f"profiles/{pid}.json"
        for parent in profile.get("extends", []):
            if parent not in profiles:
                add("REG-PROFILE-REF", target, f"extends unknown profile {parent}")
        for ref in profile.get("controls", []):
            cid = ref["control"]
            if cid not in controls:
                add("REG-CONTROL-REF", target, f"references unknown control {cid}")
            elif controls[cid].get("lifecycle") in ("draft", "retired"):
                add("REG-PROFILE-REF-LIFECYCLE", target,
                    f"references {cid} with lifecycle {controls[cid].get('lifecycle')!r}")

    # Profile composition: extends must form a DAG. flatten_profile visits
    # each ancestor exactly once (first-visit order), so a shared ancestor
    # reached through two children is accepted, and only a profile that
    # reaches itself through extends is a cycle. The duplicate check then
    # fires only when a resolved control is explicitly declared more than
    # once inside one composition — including the same control declared by
    # independent parents with opposing baselines, which is a meaningful
    # disagreement the registry must reject, never silently discard.
    for pid in sorted(profiles):
        target = f"profiles/{loaded.profile_files.get(pid, pid + '.json')}"
        try:
            refs = flatten_profile(profiles, pid)
            declarations = [
                (owner, ref["baseline"], resolve_control(controls, ref["control"]))
                for owner, ref in refs
            ]
        except ProfileCycleError as exc:
            add("REG-PROFILE-CYCLE", target, str(exc))
            continue
        except RegistryError as exc:
            add("REG-PROFILE-REF", target, str(exc))
            continue
        declared_by = {}
        for owner, baseline, resolved in declarations:
            declared_by.setdefault(resolved, []).append((owner, baseline))
        for cid in sorted(cid for cid, owners in declared_by.items() if len(owners) > 1):
            who = "; ".join(
                f"{owner} baseline={'true' if baseline else 'false'}"
                for owner, baseline in sorted(declared_by[cid])
            )
            add("REG-PROFILE-DUP", target,
                f"control {cid} is declared more than once in this composition "
                f"({who}); explicit disagreement must be resolved, not merged")

    errors.sort(key=lambda e: (e["code"], e["target"], e["detail"]))
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "counts": {
            "controls": len(controls),
            "profiles": len(profiles),
            "deprecated": sum(1 for c in controls.values() if c.get("lifecycle") == "deprecated"),
            "retired": sum(1 for c in controls.values() if c.get("lifecycle") == "retired"),
        },
    }


# ---------------------------------------------------------------------------
# Profile composition
# ---------------------------------------------------------------------------

def flatten_profile(profiles: dict, slug: str) -> list:
    """Ordered (owning profile, control reference) pairs for a profile and its extends.

    The extends graph is a DAG: a shared ancestor reached through two
    different children contributes exactly once, in first-visit order
    (ancestors before the profiles that extend them), so a diamond
    composition never repeats the common ancestor's controls. Only a
    profile that reaches itself through extends raises ProfileCycleError.
    """
    ordered = []
    finished = set()

    def visit(current, on_path):
        if current in on_path:
            raise ProfileCycleError(f"extends cycle through {current}")
        if current in finished:
            return
        profile = profiles[current]
        for parent in profile.get("extends", []):
            if parent not in profiles:
                raise RegistryError(f"extends unknown profile {parent}")
            visit(parent, on_path | {current})
        ordered.extend((current, ref) for ref in profile["controls"])
        finished.add(current)

    if slug not in profiles:
        raise RegistryError(f"unknown profile {slug}")
    visit(slug, frozenset())
    return ordered


def resolve_control(controls: dict, cid: str) -> str:
    """Follow a supersession chain to the first non-deprecated control."""
    seen = set()
    current = cid
    while current in controls and controls[current].get("lifecycle") == "deprecated":
        if current in seen:
            raise RegistryError(f"supersession cycle at {current}")
        seen.add(current)
        nxt = controls[current].get("supersession", {}).get("superseded_by")
        if nxt is None or nxt not in controls:
            raise RegistryError(f"deprecated control {current} has no usable successor")
        current = nxt
    if current not in controls:
        raise RegistryError(f"unknown control {cid}")
    if controls[current].get("lifecycle") in ("draft", "retired"):
        raise RegistryError(f"control {current} resolves to lifecycle {controls[current]['lifecycle']!r}")
    return current


# ---------------------------------------------------------------------------
# Predicate evaluation (Kleene three-valued logic)
# ---------------------------------------------------------------------------

def lookup_fact(inventory: dict, path: str):
    node = inventory
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def evaluate_predicate(predicate, inventory: dict):
    """Return (verdict, issues) where verdict is True, False or None (unknown)."""
    if "fact" in predicate:
        return _evaluate_condition(predicate, inventory)
    if "all_of" in predicate:
        verdict, issues = True, []
        for sub in predicate["all_of"]:
            sub_verdict, sub_issues = evaluate_predicate(sub, inventory)
            issues.extend(sub_issues)
            if sub_verdict is False:
                verdict = False
            elif sub_verdict is None and verdict is not False:
                verdict = None
        return verdict, issues
    if "any_of" in predicate:
        verdict, issues = False, []
        for sub in predicate["any_of"]:
            sub_verdict, sub_issues = evaluate_predicate(sub, inventory)
            issues.extend(sub_issues)
            if sub_verdict is True:
                verdict = True
            elif sub_verdict is None and verdict is not True:
                verdict = None
        return verdict, issues
    if "not" in predicate:
        sub_verdict, sub_issues = evaluate_predicate(predicate["not"], inventory)
        if sub_verdict is None:
            return None, sub_issues
        return (not sub_verdict), sub_issues
    raise RegistryError(f"malformed predicate node: {sorted(predicate)}")


def _evaluate_condition(condition, inventory: dict):
    path, op = condition["fact"], condition["op"]
    present, value = lookup_fact(inventory, path)
    issues = []

    if op == "exists":
        return (True if present else None), ([] if present else [f"fact not present in inventory: {path}"])
    if op == "not_exists":
        return (False if present else True), []
    if not present:
        return None, [f"fact not present in inventory: {path}"]
    if op == "contains":
        if not isinstance(value, list):
            return None, [f"fact type mismatch: {path} is not a list for contains"]
        return (condition["value"] in value), []
    if op in ("gt", "gte", "lt", "lte"):
        expected = condition["value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or isinstance(expected, bool) or not isinstance(expected, (int, float)):
            return None, [f"fact type mismatch: {path} does not compare numerically for {op}"]
        if op == "gt":
            return value > expected, []
        if op == "gte":
            return value >= expected, []
        if op == "lt":
            return value < expected, []
        return value <= expected, []
    if op in ("in", "not_in"):
        if not isinstance(condition["value"], list):
            return None, [f"predicate type mismatch: {op} needs a list value"]
        inside = value in condition["value"]
        return (inside if op == "in" else not inside), []
    if op in ("equals", "not_equals"):
        if isinstance(value, (dict, list)) or isinstance(condition["value"], (dict, list)):
            return None, [f"fact type mismatch: {path} is not scalar for {op}"]
        equal = value == condition["value"]
        return (equal if op == "equals" else not equal), []
    raise RegistryError(f"unknown operator {op!r}")


# ---------------------------------------------------------------------------
# Applicability evaluation
# ---------------------------------------------------------------------------

def _version_in_ranges(version: str, ranges: list) -> bool:
    parsed = _parse_version(version)
    return any(_parse_version(r["minimum"]) <= parsed <= _parse_version(r["maximum"]) for r in ranges)


def evaluate(loaded: LoadedRegistry, profile_slugs: list, inventory: dict, as_of: str) -> dict:
    """Evaluate the composed control set of one or more profiles against an inventory.

    Deterministic: depends only on the loaded registry, the profile selection,
    the inventory document and as_of. The result is validated against the
    report schema before it is returned.
    """
    report_problems = validate_registry(loaded)
    if report_problems["status"] != "PASS":
        raise RegistryError("registry fails validation: " + json.dumps(report_problems["errors"][:3]))

    inventory_problems = schema_errors(loaded.schema_validators["inventory"], inventory)
    if inventory_problems:
        raise RegistryError("inventory fails schema validation: " + "; ".join(inventory_problems[:5]))

    as_of_date = _parse_date(as_of)
    max_age = loaded.manifest["policy"]["max_verification_age_days"]

    merged = {}
    resolutions = []
    # Repeated selection of the same profile is idempotent: each selected
    # profile is composed exactly once, so the report is byte-identical to
    # selecting it a single time.
    for slug in dict.fromkeys(profile_slugs):
        if slug not in loaded.profiles:
            raise RegistryError(f"unknown profile {slug}")
        for owner, ref in flatten_profile(loaded.profiles, slug):
            cid = ref["control"]
            try:
                resolved = resolve_control(loaded.controls, cid)
            except RegistryError as exc:
                raise RegistryError(f"profile {owner}: {exc}") from exc
            if resolved != cid:
                resolutions.append({"profile": owner, "requested": cid, "resolved_to": resolved})
            slot = merged.setdefault(resolved, {"profiles": [], "baseline": False})
            if owner not in slot["profiles"]:
                slot["profiles"].append(owner)
            slot["baseline"] = slot["baseline"] or ref["baseline"]

    control_ids = sorted(merged)

    # Pass 1: per-control dimensions that do not depend on other controls.
    dimensions = {}
    for cid in control_ids:
        control = loaded.controls[cid]
        verdict, issues = evaluate_predicate(control["predicate"], inventory)
        hermes_section = inventory.get("hermes", {})
        if isinstance(hermes_section, dict) and isinstance(hermes_section.get("version"), str):
            version = hermes_section["version"]
            in_range = _version_in_ranges(version, control["hermes_versions"]["verified"])
            version_state = "IN_RANGE" if in_range else "OUT_OF_RANGE"
        else:
            version, version_state = None, "MISSING"
        lv_date = _parse_date(control["last_verification"]["date"])
        stale = (as_of_date - lv_date).days > max_age
        dimensions[cid] = {"verdict": verdict, "issues": issues, "version": version,
                           "version_state": version_state, "stale": stale}

    # Pass 2: conflicts fire only when both sides evaluate predicate-true.
    conflicts = {cid: [] for cid in control_ids}
    for cid in control_ids:
        if dimensions[cid]["verdict"] is not True:
            continue
        for entry in loaded.controls[cid].get("conflicts", []):
            other = entry["control"]
            if other in dimensions and dimensions[other]["verdict"] is True:
                conflicts[cid].append(other)

    results = []
    for cid in control_ids:
        control = loaded.controls[cid]
        dim = dimensions[cid]
        slot = merged[cid]
        result = {
            "control": cid,
            "title": control["title"],
            "baseline": slot["baseline"],
            "profiles": sorted(slot["profiles"]),
            "reasons": [],
        }
        if dim["verdict"] is False:
            result["status"] = "not_applicable"
            result["reasons"].append({
                "source": "predicate.false",
                "detail": "applicability predicate is demonstrably false for this inventory"})
        elif dim["version_state"] == "OUT_OF_RANGE":
            result["status"] = "unsupported"
            ranges = "; ".join(
                f"{r['minimum']}..{r['maximum']}" for r in control["hermes_versions"]["verified"])
            result["reasons"].append({
                "source": "hermes_version.range",
                "detail": f"hermes version {dim['version']} is outside every verified range ({ranges})"})
        else:
            decision_reasons = []
            if dim["version_state"] == "MISSING":
                decision_reasons.append({
                    "source": "hermes_version.range",
                    "detail": "hermes.version is not present in the inventory; verified-range membership is unknown"})
            if dim["verdict"] is None:
                decision_reasons.append({
                    "source": "predicate.fact_missing",
                    "detail": "undecidable facts: " + "; ".join(sorted(set(dim["issues"])))})
            if dim["stale"]:
                decision_reasons.append({
                    "source": "verification.stale",
                    "detail": (f"last verification {control['last_verification']['date']} is older than "
                               f"{max_age} days before as-of {as_of}")})
            if conflicts[cid]:
                decision_reasons.append({
                    "source": "conflict.control",
                    "detail": "conflicts with " + ", ".join(sorted(conflicts[cid])) +
                              "; both designs apply and the operator must choose one"})
                result["conflicts_with"] = sorted(conflicts[cid])
            if decision_reasons:
                result["status"] = "needs_decision"
                result["reasons"] = decision_reasons
            else:
                result["status"] = "required" if slot["baseline"] else "recommended"
                result["reasons"].append({
                    "source": "profile.baseline" if slot["baseline"] else "profile.discretion",
                    "detail": ("omission violates the declared baseline of profile(s): "
                               + ", ".join(sorted(slot["profiles"]))
                               if slot["baseline"] else
                               "meaningful risk reduction; operator choice remains in profile(s): "
                               + ", ".join(sorted(slot["profiles"])))})
        results.append(result)

    summary = {status: 0 for status in STATUS_VALUES}
    for result in results:
        summary[result["status"]] += 1
    summary["total"] = len(results)

    report = {
        "schema": "beyond-prompting/report@1",
        "registry_version": loaded.manifest["registry_version"],
        "registry_as_of": loaded.manifest["as_of"],
        "as_of": as_of,
        "profiles": sorted(set(profile_slugs)),
        "inventory_digest": {"algorithm": "sha256", "value": digest_of(inventory)},
        "registry_digest": {"algorithm": "sha256", "value": loaded.digest},
        "policy": {"max_verification_age_days": max_age},
        "resolution": sorted(resolutions, key=lambda r: (r["profile"], r["requested"])),
        "results": results,
        "summary": summary,
    }
    report_problems = schema_errors(loaded.schema_validators["report"], report)
    if report_problems:
        raise RegistryError("generated report fails its own schema: " + "; ".join(report_problems[:5]))
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _fail(errors: list) -> int:
    print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False, indent=2))
    return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=("Hardening registry: registry validation and "
                                                  "deterministic applicability evaluation."))
    parser.add_argument("--registry", default=str(ROOT / "registry"), help="registry directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate-registry", help="validate a registry directory and exit")

    ev = sub.add_parser("evaluate", help="evaluate profiles against an inventory")
    ev.add_argument("--profile", action="append", required=True, metavar="SLUG")
    ev.add_argument("--inventory", required=True, help="path to a metadata-safe inventory JSON file")
    ev.add_argument("--as-of", required=True, metavar="YYYY-MM-DD",
                    help="evaluation date; staleness is judged against it")
    ev.add_argument("--out", help="optional path to write the report to")

    args = parser.parse_args(argv)
    registry_dir = Path(args.registry)

    try:
        loaded = load_registry(registry_dir)
    except (RegistryError, OSError) as exc:
        return _fail([{"code": "REG-LOAD", "detail": str(exc)}])

    if args.command == "validate-registry":
        result = validate_registry(loaded)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "PASS" else 1

    try:
        inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail([{"code": "INVENTORY-LOAD", "detail": str(exc)}])
    try:
        report = evaluate(loaded, args.profile, inventory, args.as_of)
    except RegistryError as exc:
        return _fail([{"code": "EVALUATE", "detail": str(exc)}])
    except ValueError as exc:
        print(json.dumps({"status": "FAIL", "errors": [{"code": "USAGE", "detail": str(exc)}]}), file=sys.stderr)
        return 2

    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
