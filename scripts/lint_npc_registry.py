"""Read-only validator for per-campaign NPC registry artifacts.

The NPC registry (``<campaign>/_npc_registry.json``) is the canonical
GM-curated lookup for known NPCs in a campaign. This script:

1. Parses the registry as JSON.
2. Validates it against ``schemas/v0.1/npc_registry.schema.json``.
3. Cross-checks every record's ``slug`` against an actual folder under either
   ``hub_path`` or ``setting_hub_path`` (relative to the corpus root).
4. Reports duplicate slugs.
5. Flags ``tracked`` / ``background`` / ``dormant`` records with
   ``hub_path: null`` (only ``candidate`` may have a null hub).
6. Flags records where ``first_session > last_session``.

Output mirrors ``scripts/lint_corpus_hubs.py``: per-issue lines plus a
summary. Exits 0 on a clean run, 1 if any record has an issue.

The script never modifies files. It only reads.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


# --------------------------------------------------------------------------- #
# Defaults
# --------------------------------------------------------------------------- #


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_corpus_root() -> Path:
    return _repo_root() / "corpus" / "eldyrwild-markdown"


def _default_registry_path() -> Path:
    return (
        _default_corpus_root()
        / "Longmont Campaign"
        / "Campaign 2"
        / "_npc_registry.json"
    )


def _default_schema_path() -> Path:
    return _repo_root() / "schemas" / "v0.1" / "npc_registry.schema.json"


# --------------------------------------------------------------------------- #
# Per-record validation
# --------------------------------------------------------------------------- #


@dataclass
class RecordReport:
    index: int
    slug: str
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def _resolve_hub(corpus_root: Path, hub_rel: str | None) -> Path | None:
    if not hub_rel:
        return None
    return corpus_root / hub_rel.rstrip("/")


def _validate_record(
    index: int,
    record: dict,
    *,
    corpus_root: Path,
    duplicate_slugs: set[str],
) -> RecordReport:
    slug = str(record.get("slug") or f"<missing-slug-at-index-{index}>")
    report = RecordReport(index=index, slug=slug)

    status = record.get("status")
    hub_path = record.get("hub_path")
    setting_hub_path = record.get("setting_hub_path")

    if slug in duplicate_slugs:
        report.issues.append(f"slug — duplicate slug '{slug}' in registry")

    first_session = record.get("first_session")
    last_session = record.get("last_session")
    if (
        isinstance(first_session, int)
        and isinstance(last_session, int)
        and first_session > last_session
    ):
        report.issues.append(
            f"sessions — first_session ({first_session}) > last_session ({last_session})"
        )

    if status in {"tracked", "background", "dormant"} and hub_path is None:
        report.issues.append(
            f"hub_path — required for status='{status}' vs null"
        )

    if status == "candidate" and hub_path is not None:
        # Not strictly an error, but a smell — surface it as a soft note.
        # Keep as ISSUE for now so the GM is reminded to promote status.
        report.issues.append(
            "hub_path — set on a 'candidate' record; promote status to "
            "'tracked' or 'background' once the hub is curated"
        )

    # Cross-ref: at least one of hub_path / setting_hub_path must resolve to a
    # directory whose folder name matches the slug.
    hub_dir = _resolve_hub(corpus_root, hub_path)
    setting_dir = _resolve_hub(corpus_root, setting_hub_path)

    candidate_dirs = [d for d in (hub_dir, setting_dir) if d is not None]
    resolved_dir: Path | None = None
    for candidate in candidate_dirs:
        if candidate.is_dir():
            if candidate.name == slug:
                resolved_dir = candidate
                break
            else:
                report.issues.append(
                    f"slug — folder name '{candidate.name}' does not match "
                    f"slug '{slug}' at {candidate}"
                )
        else:
            label = "hub_path" if candidate is hub_dir else "setting_hub_path"
            report.issues.append(
                f"{label} — directory does not exist: {candidate}"
            )

    if status != "candidate" and resolved_dir is None and not candidate_dirs:
        report.issues.append(
            f"hub_path — no folder configured for status='{status}'"
        )

    return report


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #


def _load_schema(schema_path: Path) -> dict:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _validate_schema(records_payload: object, schema: dict) -> list[str]:
    """Return formatted JSON-Schema errors (empty list = OK)."""
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(records_payload), key=lambda e: list(e.path)):
        path = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"schema — {path}: {err.message}")
    return errors


def lint_registry(
    *,
    registry_path: Path,
    corpus_root: Path,
    schema_path: Path,
) -> tuple[int, int, list[str]]:
    """Lint a single registry file.

    Returns
    -------
    (record_count, ok_count, lines)
        Lines are pre-formatted output lines (per-record OK/ISSUE plus any
        top-level ERROR lines); the caller prints them in order.
    """
    lines: list[str] = []

    if not registry_path.is_file():
        lines.append(f"ERROR: registry not found: {registry_path}")
        return 0, 0, lines

    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        lines.append(f"ERROR: invalid JSON in {registry_path}: {exc}")
        return 0, 0, lines

    schema = _load_schema(schema_path)
    schema_errors = _validate_schema(raw, schema)
    if schema_errors:
        for msg in schema_errors:
            lines.append(f"ISSUE [schema] {registry_path.name}: {msg}")
        # Keep going only if it's an array; otherwise we cannot iterate.
        if not isinstance(raw, list):
            return 0, 0, lines

    if not isinstance(raw, list):
        lines.append(
            f"ERROR: top-level value in {registry_path} must be an array, "
            f"got {type(raw).__name__}"
        )
        return 0, 0, lines

    slug_counts: Counter[str] = Counter()
    for record in raw:
        if isinstance(record, dict) and isinstance(record.get("slug"), str):
            slug_counts[record["slug"]] += 1
    duplicate_slugs = {slug for slug, count in slug_counts.items() if count > 1}

    reports: list[RecordReport] = []
    for index, record in enumerate(raw):
        if not isinstance(record, dict):
            reports.append(
                RecordReport(
                    index=index,
                    slug=f"<non-object-at-{index}>",
                    issues=[f"record — must be a JSON object, got {type(record).__name__}"],
                )
            )
            continue
        reports.append(
            _validate_record(
                index,
                record,
                corpus_root=corpus_root,
                duplicate_slugs=duplicate_slugs,
            )
        )

    ok_count = sum(1 for r in reports if r.ok)
    for report in reports:
        if report.ok:
            lines.append(f"OK    [{report.index:02d}] {report.slug}")
        else:
            for issue in report.issues:
                lines.append(f"ISSUE [{report.index:02d}] {report.slug}: {issue}")

    # Surface schema errors that didn't already increment record-level issues.
    if schema_errors and ok_count == len(reports):
        # All records individually OK but schema-level errors above; treat as
        # a registry-level issue so exit code reflects the failure.
        ok_count = max(0, ok_count - 1)

    return len(reports), ok_count, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint a per-campaign NPC registry JSON file."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=_default_registry_path(),
        help="Registry JSON file to lint (default: Campaign 2 registry).",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=_default_corpus_root(),
        help="Corpus root that hub_path / setting_hub_path are relative to.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=_default_schema_path(),
        help="Path to npc_registry.schema.json (default: schemas/v0.1/...).",
    )
    args = parser.parse_args(argv)

    record_count, ok_count, lines = lint_registry(
        registry_path=args.path,
        corpus_root=args.corpus_root,
        schema_path=args.schema,
    )

    for line in lines:
        print(line)

    issue_count = record_count - ok_count
    print()
    print(
        f"Summary: {record_count} records, {ok_count} OK, {issue_count} with issues."
    )

    if issue_count > 0 or any(line.startswith("ERROR") for line in lines):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
