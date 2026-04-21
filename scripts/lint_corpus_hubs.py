"""Read-only compliance linter for corpus subject hubs.

Walks `corpus/eldyrwild-markdown/` (or `--corpus PATH`), discovers candidate hub
folders by path pattern (NPC, PC, Location), parses each `README.md`'s YAML
frontmatter, and reports per-hub OK / ISSUE lines.

The lint is informational by default (exit 0). Pass `--strict` to exit 1 when
any hub has at least one ISSUE.

Conventions enforced (see `Docs/CONVENTION-Corpus-Subject-Schemas.md`):

- `subject_class` is present and in the closed vocabulary.
- `subject_doc_kind == "hub_index"` on the README.
- `document_class` is in the existing closed vocabulary.
- Per-class satellite hints (PC: timeline if dossier exists; NPC: cross-link
  pointer paragraph; Location: README presence on §2.1 / §2.3 shapes).

The script never modifies files. It only reads.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml


SUBJECT_CLASS_VOCAB: frozenset[str] = frozenset(
    {"npc", "pc", "location", "faction", "item", "event", "world", "null"}
)

SUBJECT_DOC_KIND_VOCAB: frozenset[str] = frozenset(
    {
        "hub_index",
        "timeline",
        "dossier",
        "statblock",
        "seed",
        "recap",
        "prep",
        "world_primer",
        "location_dossier",
        "item_card",
        "faction_brief",
        "notes_aggregate",
        "null",
    }
)

DOCUMENT_CLASS_VOCAB: frozenset[str] = frozenset(
    {"play", "reference", "world", "planning"}
)


# --------------------------------------------------------------------------- #
# Hub discovery
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class HubCandidate:
    path: Path  # the hub folder
    expected_subject_class: str  # what subject_class we expect on the README
    shape: str  # "npc", "pc", "location_top", "location_dossiers", "location_region"


def _is_npc_hub(folder: Path) -> bool:
    """A folder under a `NPCs/` parent that contains a slug-style child folder."""
    return folder.parent.name == "NPCs" and folder.is_dir() and not _looks_like_legacy(folder)


def _is_pc_hub(folder: Path) -> bool:
    return folder.parent.name == "PCs" and folder.is_dir()


def _looks_like_legacy(folder: Path) -> bool:
    """Folders with a single forward-pointer README (e.g. legacy Torbin Jove)."""
    readme = folder / "README.md"
    if not readme.is_file():
        return False
    head = readme.read_text(encoding="utf-8", errors="replace")[:400].lower()
    return "deprecated folder" in head or "moved" in head[:80]


def _is_location_top_hub(folder: Path) -> bool:
    """A child of `Cities and Towns/` (or similar typed parent) that has at least
    one sub-folder besides `NPCs/`. We use the presence of any non-NPC subfolder
    or a `*_Map_Key_*` / `The City of *.md` file as the signal."""
    if not folder.is_dir():
        return False
    parent = folder.parent.name
    if parent not in {"Cities and Towns"}:
        return False
    children = list(folder.iterdir())
    has_world_primer = any(
        c.is_file()
        and c.suffix == ".md"
        and (
            re.search(r"_Map_Key", c.name, flags=re.IGNORECASE)
            or c.name.lower().startswith("the city of")
        )
        for c in children
    )
    has_sub_folders = any(c.is_dir() and c.name != "NPCs" for c in children)
    return has_world_primer or has_sub_folders


def _is_location_dossiers_collection(folder: Path) -> bool:
    return folder.is_dir() and folder.name.endswith("_Location_Dossiers")


def _is_location_region_hub(folder: Path) -> bool:
    """Heterogeneous region directory — `Migrating Forest/Branchbound/` shape.

    Heuristic: a directory that contains a mix of `*_culture_*.md`,
    encounter / loot files, and at least one named-entity file, but is not
    itself a `NPCs/` or `Cities and Towns/...` child.
    """
    if not folder.is_dir():
        return False
    parent_chain = {p.name for p in folder.parents}
    if "NPCs" in parent_chain or "PCs" in parent_chain:
        return False
    if folder.parent.name in {"Cities and Towns", "NPCs", "PCs"}:
        return False
    md_files = [c for c in folder.iterdir() if c.is_file() and c.suffix == ".md"]
    if len(md_files) < 3:
        return False
    has_culture_or_encounter = any(
        re.search(r"(culture|encounter|witness|knows)", f.stem, flags=re.IGNORECASE)
        for f in md_files
    )
    return has_culture_or_encounter


def discover_hubs(corpus_root: Path) -> list[HubCandidate]:
    candidates: list[HubCandidate] = []
    for folder in sorted(corpus_root.rglob("*")):
        if not folder.is_dir():
            continue
        if folder.name.startswith("."):
            continue
        if _is_npc_hub(folder):
            candidates.append(
                HubCandidate(
                    path=folder, expected_subject_class="npc", shape="npc"
                )
            )
        elif _is_pc_hub(folder):
            candidates.append(
                HubCandidate(path=folder, expected_subject_class="pc", shape="pc")
            )
        elif _is_location_top_hub(folder):
            candidates.append(
                HubCandidate(
                    path=folder,
                    expected_subject_class="location",
                    shape="location_top",
                )
            )
        elif _is_location_dossiers_collection(folder):
            candidates.append(
                HubCandidate(
                    path=folder,
                    expected_subject_class="location",
                    shape="location_dossiers",
                )
            )
        elif _is_location_region_hub(folder):
            candidates.append(
                HubCandidate(
                    path=folder,
                    expected_subject_class="location",
                    shape="location_region",
                )
            )
    return candidates


# --------------------------------------------------------------------------- #
# Frontmatter parsing
# --------------------------------------------------------------------------- #


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*(?:\n|$)", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, object] | None:
    """Return parsed frontmatter dict, or None if no frontmatter block."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    raw = m.group(1)
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


# --------------------------------------------------------------------------- #
# Per-hub validation
# --------------------------------------------------------------------------- #


@dataclass
class HubReport:
    candidate: HubCandidate
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def _check_value(name: str, value: object, vocab: Iterable[str]) -> str | None:
    if value is None:
        return f"{name} — required vs missing"
    if not isinstance(value, str):
        return f"{name} — string vs {type(value).__name__}"
    if value not in vocab:
        return f"{name} — one of {{{', '.join(sorted(vocab))}}} vs '{value}'"
    return None


def _has_satellite(hub: Path, suffix: str) -> bool:
    return any(p.is_file() and p.name.endswith(suffix) for p in hub.iterdir())


def validate_hub(candidate: HubCandidate) -> HubReport:
    report = HubReport(candidate=candidate)
    readme = candidate.path / "README.md"

    # For location-dossier collections, README is recommended but optional.
    readme_optional = candidate.shape == "location_dossiers"

    if not readme.is_file():
        if not readme_optional:
            report.issues.append("README.md — required vs missing")
        return report

    text = readme.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    if fm is None:
        report.issues.append("frontmatter — YAML block vs missing/unparseable")
        return report

    subject_class = fm.get("subject_class")
    issue = _check_value("subject_class", subject_class, SUBJECT_CLASS_VOCAB)
    if issue:
        report.issues.append(issue)
    elif (
        isinstance(subject_class, str)
        and subject_class != candidate.expected_subject_class
    ):
        report.issues.append(
            f"subject_class — '{candidate.expected_subject_class}' (from path) "
            f"vs '{subject_class}'"
        )

    subject_doc_kind = fm.get("subject_doc_kind")
    issue = _check_value("subject_doc_kind", subject_doc_kind, SUBJECT_DOC_KIND_VOCAB)
    if issue:
        report.issues.append(issue)
    elif subject_doc_kind != "hub_index":
        report.issues.append(
            f"subject_doc_kind — 'hub_index' vs '{subject_doc_kind}'"
        )

    document_class = fm.get("document_class")
    issue = _check_value("document_class", document_class, DOCUMENT_CLASS_VOCAB)
    if issue:
        report.issues.append(issue)

    # Per-class satellite hints.
    has_dossier = _has_satellite(candidate.path, "_character_dossier.md")
    has_timeline = (candidate.path / "timeline.md").is_file()

    if candidate.shape == "npc":
        # NPCs may stay seed-only; only expect a timeline once a dossier exists.
        if has_dossier and not has_timeline:
            report.issues.append(
                "timeline.md — recommended (dossier present, no timeline) vs missing"
            )
    elif candidate.shape == "pc":
        # PC hubs: per CONVENTION-PC-Hub.md §3 / §9, dossier and timeline are
        # required at PC inception (i.e. as soon as the README exists).
        if not has_timeline:
            report.issues.append(
                "timeline.md — required at PC inception vs missing"
            )
        if not has_dossier:
            report.issues.append(
                "{slug}_character_dossier.md — required at PC inception vs missing"
            )

    return report


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _default_corpus_root() -> Path:
    return Path(__file__).resolve().parents[1] / "corpus" / "eldyrwild-markdown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint corpus subject-hub README frontmatter."
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=_default_corpus_root(),
        help="Corpus root to walk (default: corpus/eldyrwild-markdown).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any hub has at least one ISSUE.",
    )
    args = parser.parse_args(argv)

    corpus_root: Path = args.corpus
    if not corpus_root.is_dir():
        print(f"ERROR: corpus root not found: {corpus_root}", file=sys.stderr)
        return 2

    candidates = discover_hubs(corpus_root)
    reports = [validate_hub(c) for c in candidates]

    ok_count = sum(1 for r in reports if r.ok)
    issue_count = len(reports) - ok_count

    for report in reports:
        rel = report.candidate.path.relative_to(corpus_root)
        if report.ok:
            print(f"OK    [{report.candidate.shape}] {rel}")
        else:
            for issue in report.issues:
                print(f"ISSUE [{report.candidate.shape}] {rel}: {issue}")

    print()
    print(
        f"Summary: {len(reports)} hubs scanned, {ok_count} OK, {issue_count} with issues."
    )

    if args.strict and issue_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
