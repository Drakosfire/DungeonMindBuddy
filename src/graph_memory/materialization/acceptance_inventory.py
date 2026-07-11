"""Deterministic, read-only Eldyrwild C2 acceptance-corpus inventory.

Selects and hashes source artifacts. Does not extract, contribute, or publish.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

MANIFEST_SCHEMA = "dmb_world_acceptance_inventory_manifest_v1"
REPORT_SCHEMA = "dmb_world_acceptance_inventory_v1"
REPORT_VERSION = "1.0"


class AcceptanceInventoryError(ValueError):
    """Manifest, path-confinement, or required-selection failure."""


@dataclass(frozen=True, slots=True)
class FamilySelection:
    files: tuple[str, ...] = ()
    roots: tuple[str, ...] = ()
    glob: str = "**/*.md"
    minimum_per_root: int = 0
    exclude_files: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ManifestFamily:
    family_id: str
    required: bool
    reason: str
    selection: FamilySelection


@dataclass(frozen=True, slots=True)
class AcceptanceInventoryManifest:
    schema: str
    version: str
    world_id: str
    campaign_id: str
    corpus_root: str
    families: tuple[ManifestFamily, ...]
    manifest_path: Path
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class InventorySource:
    path: str
    family_id: str
    required: bool
    selection_reason: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class InventoryDiagnostic:
    code: str
    message: str
    family_id: str | None = None
    path: str | None = None


@dataclass(frozen=True, slots=True)
class AcceptanceInventoryReport:
    schema: str
    version: str
    world_id: str
    campaign_id: str
    corpus_root: str
    manifest_sha256: str
    summary: Mapping[str, int]
    families: Sequence[Mapping[str, Any]]
    sources: Sequence[InventorySource]
    diagnostics: Sequence[InventoryDiagnostic]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "world_id": self.world_id,
            "campaign_id": self.campaign_id,
            "corpus_root": self.corpus_root,
            "manifest_sha256": self.manifest_sha256,
            "summary": dict(self.summary),
            "families": [dict(item) for item in self.families],
            "sources": [asdict(item) for item in self.sources],
            "diagnostics": [asdict(item) for item in self.diagnostics],
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return _sha256_bytes(data), len(data)


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AcceptanceInventoryError(f"{label} must be an object")
    return value


def _require_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AcceptanceInventoryError(f"{label} must be a non-empty string")
    return value


def _require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AcceptanceInventoryError(f"{label} must be a boolean")
    return value


def _require_str_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AcceptanceInventoryError(f"{label} must be a list of strings")
    return tuple(value)


def _posix_rel(path: str, label: str) -> str:
    text = _require_str(path, label).replace("\\", "/")
    if text.startswith("/") or PurePosixPath(text).is_absolute():
        raise AcceptanceInventoryError(f"{label} must be relative: {path!r}")
    if ".." in PurePosixPath(text).parts:
        raise AcceptanceInventoryError(f"{label} must not contain '..': {path!r}")
    return text


def _parse_selection(raw: Mapping[str, Any], family_id: str) -> FamilySelection:
    files = _require_str_list(raw.get("files", []), f"{family_id}.selection.files")
    roots = _require_str_list(raw.get("roots", []), f"{family_id}.selection.roots")
    exclude_files = _require_str_list(
        raw.get("exclude_files", []), f"{family_id}.selection.exclude_files"
    )
    glob = raw.get("glob", "**/*.md")
    if not isinstance(glob, str) or not glob:
        raise AcceptanceInventoryError(f"{family_id}.selection.glob must be a string")
    minimum = raw.get("minimum_per_root", 0)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
        raise AcceptanceInventoryError(
            f"{family_id}.selection.minimum_per_root must be a non-negative int"
        )
    if not files and not roots:
        raise AcceptanceInventoryError(
            f"{family_id}.selection must include files and/or roots"
        )
    return FamilySelection(
        files=tuple(_posix_rel(item, f"{family_id}.selection.files") for item in files),
        roots=tuple(_posix_rel(item, f"{family_id}.selection.roots") for item in roots),
        glob=glob,
        minimum_per_root=minimum,
        exclude_files=tuple(
            _posix_rel(item, f"{family_id}.selection.exclude_files")
            for item in exclude_files
        ),
    )


def load_acceptance_manifest(path: Path) -> AcceptanceInventoryManifest:
    raw_text = path.read_bytes()
    try:
        payload = json.loads(raw_text.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AcceptanceInventoryError(f"invalid manifest JSON: {path}") from exc
    data = _require_mapping(payload, "manifest")
    schema = _require_str(data.get("schema"), "schema")
    if schema != MANIFEST_SCHEMA:
        raise AcceptanceInventoryError(f"unsupported manifest schema: {schema!r}")
    families_raw = data.get("families")
    if not isinstance(families_raw, list) or not families_raw:
        raise AcceptanceInventoryError("families must be a non-empty list")
    families: list[ManifestFamily] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(families_raw):
        fam = _require_mapping(item, f"families[{index}]")
        family_id = _require_str(fam.get("family_id"), f"families[{index}].family_id")
        if family_id in seen_ids:
            raise AcceptanceInventoryError(f"duplicate family_id: {family_id}")
        seen_ids.add(family_id)
        selection = _parse_selection(
            _require_mapping(fam.get("selection"), f"{family_id}.selection"),
            family_id,
        )
        families.append(
            ManifestFamily(
                family_id=family_id,
                required=_require_bool(fam.get("required"), f"{family_id}.required"),
                reason=_require_str(fam.get("reason"), f"{family_id}.reason"),
                selection=selection,
            )
        )
    return AcceptanceInventoryManifest(
        schema=schema,
        version=_require_str(data.get("version"), "version"),
        world_id=_require_str(data.get("world_id"), "world_id"),
        campaign_id=_require_str(data.get("campaign_id"), "campaign_id"),
        corpus_root=_posix_rel(
            _require_str(data.get("corpus_root"), "corpus_root"), "corpus_root"
        ),
        families=tuple(families),
        manifest_path=path.resolve(),
        manifest_sha256=_sha256_bytes(raw_text),
    )


def _confined_path(corpus_root: Path, rel: str) -> Path:
    candidate = (corpus_root / rel).resolve()
    try:
        candidate.relative_to(corpus_root.resolve())
    except ValueError as exc:
        raise AcceptanceInventoryError(
            f"path escapes corpus root: {rel!r}"
        ) from exc
    if candidate.is_symlink():
        raise AcceptanceInventoryError(f"symlinks are not allowed: {rel!r}")
    return candidate


def _repo_rel(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _expand_family(
    *,
    repo_root: Path,
    corpus_root: Path,
    family: ManifestFamily,
    claimed: dict[str, str],
    diagnostics: list[InventoryDiagnostic],
) -> list[InventorySource]:
    selection = family.selection
    exclude = set(selection.exclude_files)
    selected_rels: list[str] = []

    for rel in selection.files:
        if rel in exclude:
            continue
        abs_path = _confined_path(corpus_root, rel)
        if not abs_path.is_file():
            diagnostics.append(
                InventoryDiagnostic(
                    code="required_file_missing"
                    if family.required
                    else "optional_file_missing",
                    message=f"selected file missing: {rel}",
                    family_id=family.family_id,
                    path=rel,
                )
            )
            if family.required:
                raise AcceptanceInventoryError(
                    f"required file missing for {family.family_id}: {rel}"
                )
            continue
        selected_rels.append(rel)

    for root_rel in selection.roots:
        root_abs = _confined_path(corpus_root, root_rel)
        if not root_abs.exists():
            diagnostics.append(
                InventoryDiagnostic(
                    code="required_root_missing"
                    if family.required
                    else "optional_root_missing",
                    message=f"selected root missing: {root_rel}",
                    family_id=family.family_id,
                    path=root_rel,
                )
            )
            if family.required:
                raise AcceptanceInventoryError(
                    f"required root missing for {family.family_id}: {root_rel}"
                )
            continue
        if not root_abs.is_dir():
            raise AcceptanceInventoryError(
                f"selection root is not a directory: {root_rel}"
            )
        matched = sorted(
            path
            for path in root_abs.glob(selection.glob)
            if path.is_file() and not path.is_symlink()
        )
        root_rels: list[str] = []
        for path in matched:
            try:
                rel = path.resolve().relative_to(corpus_root.resolve()).as_posix()
            except ValueError as exc:
                raise AcceptanceInventoryError(
                    f"glob match escapes corpus root under {root_rel}"
                ) from exc
            if rel in exclude:
                continue
            root_rels.append(rel)
        if family.required and len(root_rels) < selection.minimum_per_root:
            diagnostics.append(
                InventoryDiagnostic(
                    code="required_root_below_minimum",
                    message=(
                        f"root {root_rel} matched {len(root_rels)} files; "
                        f"minimum_per_root={selection.minimum_per_root}"
                    ),
                    family_id=family.family_id,
                    path=root_rel,
                )
            )
            raise AcceptanceInventoryError(
                f"required root below minimum for {family.family_id}: {root_rel}"
            )
        if not family.required and not root_rels:
            diagnostics.append(
                InventoryDiagnostic(
                    code="optional_root_empty",
                    message=f"optional root empty or unmatched: {root_rel}",
                    family_id=family.family_id,
                    path=root_rel,
                )
            )
        selected_rels.extend(root_rels)

    sources: list[InventorySource] = []
    for rel in selected_rels:
        if rel in claimed:
            raise AcceptanceInventoryError(
                f"duplicate selection for {rel!r}: "
                f"{claimed[rel]} and {family.family_id}"
            )
        abs_path = _confined_path(corpus_root, rel)
        digest, size = _sha256_file(abs_path)
        repo_path = _repo_rel(repo_root, abs_path)
        claimed[rel] = family.family_id
        sources.append(
            InventorySource(
                path=repo_path,
                family_id=family.family_id,
                required=family.required,
                selection_reason=family.reason,
                sha256=digest,
                size_bytes=size,
            )
        )
    sources.sort(key=lambda item: item.path)
    return sources


def build_acceptance_inventory(
    repo_root: Path,
    manifest: AcceptanceInventoryManifest,
) -> AcceptanceInventoryReport:
    repo_root = repo_root.resolve()
    corpus_root = _confined_path(repo_root, manifest.corpus_root)
    if not corpus_root.is_dir():
        raise AcceptanceInventoryError(
            f"corpus_root is not a directory: {manifest.corpus_root}"
        )

    diagnostics: list[InventoryDiagnostic] = []
    claimed: dict[str, str] = {}
    all_sources: list[InventorySource] = []
    family_summaries: list[dict[str, Any]] = []

    for family in manifest.families:
        family_sources = _expand_family(
            repo_root=repo_root,
            corpus_root=corpus_root,
            family=family,
            claimed=claimed,
            diagnostics=diagnostics,
        )
        all_sources.extend(family_sources)
        family_summaries.append(
            {
                "family_id": family.family_id,
                "required": family.required,
                "reason": family.reason,
                "source_count": len(family_sources),
            }
        )

    all_sources.sort(key=lambda item: item.path)
    required_missing = sum(
        1 for item in diagnostics if item.code.startswith("required_")
    )
    summary = {
        "source_count": len(all_sources),
        "required_source_count": sum(1 for item in all_sources if item.required),
        "optional_source_count": sum(1 for item in all_sources if not item.required),
        "required_missing_count": required_missing,
        "diagnostic_count": len(diagnostics),
    }
    return AcceptanceInventoryReport(
        schema=REPORT_SCHEMA,
        version=REPORT_VERSION,
        world_id=manifest.world_id,
        campaign_id=manifest.campaign_id,
        corpus_root=manifest.corpus_root,
        manifest_sha256=manifest.manifest_sha256,
        summary=summary,
        families=family_summaries,
        sources=tuple(all_sources),
        diagnostics=tuple(diagnostics),
    )


def write_acceptance_inventory(
    report: AcceptanceInventoryReport, output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report.to_dict(), indent=2, sort_keys=False, ensure_ascii=True)
    # Stable trailing newline for byte-identical repeats.
    output_path.write_text(payload + "\n", encoding="utf-8")


__all__ = [
    "AcceptanceInventoryError",
    "AcceptanceInventoryManifest",
    "AcceptanceInventoryReport",
    "InventoryDiagnostic",
    "InventorySource",
    "build_acceptance_inventory",
    "load_acceptance_manifest",
    "write_acceptance_inventory",
]
