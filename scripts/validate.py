"""Read-only structural checks for Beyond Prompting; not runtime acceptance."""
from pathlib import Path
import json
import re
import sys

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is unavailable. Do not auto-install; use an authorized environment.")

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = (
    r"/opt/(?:data|vault)/",
    r"-100\d{8,}",
    r"ghp_[A-Za-z0-9]{20,}",
    r"\bsk-[A-Za-z0-9_-]{20,}",
    r"\bt_[0-9a-f]{8}\b",
    r"\b\d{8}_\d{6}_[0-9a-f]{8}\b",
)


def headings(path):
    """Count Markdown headings outside fenced code blocks."""
    count, fenced = 0, False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"#{1,6} ", line):
            count += 1
    return count


def inspect(root):
    errors = []
    docs = sorted(p for p in root.rglob("*.md") if ".git" not in p.parts)
    for path in docs:
        text = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(root))
        if text.count("```") % 2:
            errors.append({"file": rel, "kind": "unbalanced_code_fence"})
        for target in re.findall(r"\]\(([^\s)]+)\)", text):
            if target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            resolved = (path.parent / target.split("#")[0]).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                errors.append({"file": rel, "kind": "relative_link", "target": target})
            if path.name == "SKILL.md" and not resolved.is_relative_to(path.parent.resolve()):
                errors.append({"file": rel, "kind": "skill_bundle_dependency", "target": target})
        for pattern in PATTERNS:
            if re.search(pattern, text):
                errors.append({"file": rel, "kind": "private_identifier_pattern", "pattern": pattern})
        if path.name == "SKILL.md":
            try:
                lines = text.splitlines()
                if not lines or lines[0] != "---":
                    raise ValueError("Missing opening frontmatter delimiter")
                end = lines.index("---", 1)
                metadata = yaml.safe_load("\n".join(lines[1:end]))
                if not isinstance(metadata, dict):
                    raise ValueError("Frontmatter must be a mapping")
                name = metadata.get("name")
                description = metadata.get("description")
                if not isinstance(name, str) or name != path.parent.name:
                    raise ValueError("Invalid skill name")
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
                    raise ValueError("Invalid skill name format")
                if not isinstance(description, str) or not description.strip():
                    raise ValueError("Missing description")
            except (KeyError, ValueError, yaml.YAMLError):
                errors.append({"file": rel, "kind": "skill_frontmatter"})
    for en in sorted(root.glob("*/*.en.md")):
        ru = en.with_name(en.name[: -len(".en.md")] + ".ru.md")
        rel = str(en.relative_to(root))
        if not ru.exists():
            errors.append({"file": rel, "kind": "missing_translation", "target": ru.name})
            continue
        en_count, ru_count = headings(en), headings(ru)
        if en_count != ru_count:
            errors.append({"file": rel, "kind": "translation_heading_mismatch", "en": en_count, "ru": ru_count})
    return {"markdown_files": len(docs), "skill_count": sum(p.name == "SKILL.md" for p in docs),
            "errors": errors, "status": "PASS" if not errors else "FAIL",
            "scope": "structural_and_selected_text_patterns_only"}


if __name__ == "__main__":
    result = inspect(ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(bool(result["errors"]))
