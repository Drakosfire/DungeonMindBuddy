"""Deterministic, read-only Eldyrwild C2 acceptance-corpus inventory."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

MANIFEST_SCHEMA = "dmb_world_acceptance_inventory_manifest_v1"
MANIFEST_VERSION = "1.0"
REPORT_SCHEMA = "dmb_world_acceptance_inventory_v1"
REPORT_VERSION = "1.0"
_MANIFEST_KEYS = frozenset(
    {"schema", "version", "world_id", "campaign_id", "corpus_root", "families"}
)
_FAMILY_KEYS = frozenset({"family_id", "required", "reason", "selection"})
_SELECTION_KEYS = frozenset(
    {"files", "roots", "glob", "minimum_per_root", "exclude_files"}
)


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
            "families": [dict(x) for x in self.families],
            "sources": [asdict(x) for x in self.sources],
            "diagnostics": [asdict(x) for x in self.diagnostics],
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fail(msg: str) -> None:
    raise AcceptanceInventoryError(msg)


def _reject_unknown(data: Mapping[str, Any], allowed: frozenset[str], label: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        _fail(f"{label} has unknown keys: {unknown}")


def _req_map(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{label} must be an object")
    return value


def _req_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label} must be a non-empty string")
    return value


def _req_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{label} must be a boolean")
    return value


def _req_str_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(i, str) for i in value):
        _fail(f"{label} must be a list of strings")
    return tuple(value)


def _posix_rel(path: str, label: str) -> str:
    text = _req_str(path, label).replace("\\", "/")
    pure = PurePosixPath(text)
    if text.startswith("/") or pure.is_absolute():
        _fail(f"{label} must be relative: {path!r}")
    if ".." in pure.parts:
        _fail(f"{label} must not contain '..': {path!r}")
    return text


def _validate_glob(glob: str, label: str) -> str:
    if not isinstance(glob, str) or not glob.strip():
        _fail(f"{label} must be a non-empty string")
    text = glob.replace("\\", "/")
    pure = PurePosixPath(text)
    if text.startswith("/") or pure.is_absolute():
        _fail(f"{label} must be relative: {glob!r}")
    if ".." in pure.parts:
        _fail(f"{label} must not contain '..': {glob!r}")
    return glob


def _parse_selection(raw: Mapping[str, Any], family_id: str) -> FamilySelection:
    _reject_unknown(raw, _SELECTION_KEYS, f"{family_id}.selection")
    files = _req_str_list(raw.get("files", []), f"{family_id}.selection.files")
    roots = _req_str_list(raw.get("roots", []), f"{family_id}.selection.roots")
    exclude = _req_str_list(
        raw.get("exclude_files", []), f"{family_id}.selection.exclude_files"
    )
    glob = _validate_glob(raw.get("glob", "**/*.md"), f"{family_id}.selection.glob")
    minimum = raw.get("minimum_per_root", 0)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
        _fail(f"{family_id}.selection.minimum_per_root must be a non-negative int")
    if not files and not roots:
        _fail(f"{family_id}.selection must include files and/or roots")
    files_t = tuple(_posix_rel(i, f"{family_id}.selection.files") for i in files)
    excl_t = tuple(_posix_rel(i, f"{family_id}.selection.exclude_files") for i in exclude)
    overlap = sorted(set(files_t) & set(excl_t))
    if overlap:
        _fail(f"{family_id}.selection files/exclude_files overlap: {overlap}")
    return FamilySelection(
        files=files_t,
        roots=tuple(_posix_rel(i, f"{family_id}.selection.roots") for i in roots),
        glob=glob,
        minimum_per_root=minimum,
        exclude_files=excl_t,
    )


def load_acceptance_manifest(path: Path) -> AcceptanceInventoryManifest:
    try:
        raw_text = path.read_bytes()
        payload = json.loads(raw_text.decode("utf-8"))
    except OSError as exc:
        raise AcceptanceInventoryError(f"manifest unreadable: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AcceptanceInventoryError(f"invalid manifest JSON: {path}") from exc
    data = _req_map(payload, "manifest")
    _reject_unknown(data, _MANIFEST_KEYS, "manifest")
    schema = _req_str(data.get("schema"), "schema")
    if schema != MANIFEST_SCHEMA:
        _fail(f"unsupported manifest schema: {schema!r}")
    version = _req_str(data.get("version"), "version")
    if version != MANIFEST_VERSION:
        _fail(f"unsupported manifest version: {version!r}")
    families_raw = data.get("families")
    if not isinstance(families_raw, list) or not families_raw:
        _fail("families must be a non-empty list")
    families: list[ManifestFamily] = []
    seen: set[str] = set()
    for index, item in enumerate(families_raw):
        fam = _req_map(item, f"families[{index}]")
        _reject_unknown(fam, _FAMILY_KEYS, f"families[{index}]")
        family_id = _req_str(fam.get("family_id"), f"families[{index}].family_id")
        if family_id in seen:
            _fail(f"duplicate family_id: {family_id}")
        seen.add(family_id)
        families.append(
            ManifestFamily(
                family_id=family_id,
                required=_req_bool(fam.get("required"), f"{family_id}.required"),
                reason=_req_str(fam.get("reason"), f"{family_id}.reason"),
                selection=_parse_selection(
                    _req_map(fam.get("selection"), f"{family_id}.selection"), family_id
                ),
            )
        )
    return AcceptanceInventoryManifest(
        schema=schema,
        version=version,
        world_id=_req_str(data.get("world_id"), "world_id"),
        campaign_id=_req_str(data.get("campaign_id"), "campaign_id"),
        corpus_root=_posix_rel(_req_str(data.get("corpus_root"), "corpus_root"), "corpus_root"),
        families=tuple(families),
        manifest_path=path.resolve(),
        manifest_sha256=_sha256_bytes(raw_text),
    )


def _no_symlink_components(base: Path, rel: str) -> Path:
    cursor = base
    for part in PurePosixPath(rel).parts:
        cursor = cursor / part
        try:
            if cursor.is_symlink():
                _fail(f"symlinks are not allowed: {rel!r}")
        except OSError as exc:
            raise AcceptanceInventoryError(f"path unreadable: {rel!r}") from exc
    return cursor


def _confined(corpus_root: Path, rel: str) -> Path:
    unresolved = _no_symlink_components(corpus_root, rel)
    try:
        candidate = unresolved.resolve(strict=False)
        candidate.relative_to(corpus_root.resolve())
    except ValueError as exc:
        raise AcceptanceInventoryError(f"path escapes corpus root: {rel!r}") from exc
    return candidate


def _phys(path: Path) -> str:
    st = path.stat()
    return f"{st.st_dev}:{st.st_ino}"


def _claim(
    claimed_rel: dict[str, str],
    claimed_phys: dict[str, str],
    rel: str,
    phys: str,
    family_id: str,
) -> None:
    if rel in claimed_rel:
        _fail(f"duplicate selection for {rel!r}: {claimed_rel[rel]} and {family_id}")
    if phys in claimed_phys:
        _fail(
            f"duplicate physical source for {rel!r}: "
            f"{claimed_phys[phys]} and {family_id}"
        )
    claimed_rel[rel] = family_id
    claimed_phys[phys] = family_id


def _expand_family(
    *,
    repo_root: Path,
    corpus_root: Path,
    family: ManifestFamily,
    claimed_rel: dict[str, str],
    claimed_phys: dict[str, str],
    diagnostics: list[InventoryDiagnostic],
) -> list[InventorySource]:
    sel = family.selection
    exclude = set(sel.exclude_files)
    selected: list[str] = []
    corpus_res = corpus_root.resolve()
    fid = family.family_id

    for rel in sel.files:
        abs_path = _confined(corpus_root, rel)
        if not abs_path.is_file():
            code = "required_file_missing" if family.required else "optional_file_missing"
            diagnostics.append(
                InventoryDiagnostic(code, f"selected file missing: {rel}", fid, rel)
            )
            if family.required:
                _fail(f"required file missing for {fid}: {rel}")
            continue
        selected.append(rel)

    for root_rel in sel.roots:
        root_abs = _confined(corpus_root, root_rel)
        if not root_abs.exists():
            code = "required_root_missing" if family.required else "optional_root_missing"
            diagnostics.append(
                InventoryDiagnostic(code, f"selected root missing: {root_rel}", fid, root_rel)
            )
            if family.required:
                _fail(f"required root missing for {fid}: {root_rel}")
            continue
        if not root_abs.is_dir():
            _fail(f"selection root is not a directory: {root_rel}")
        root_res = root_abs.resolve()
        root_rels: list[str] = []
        for path in sorted(p for p in root_abs.glob(sel.glob) if p.is_file()):
            under = path.relative_to(root_abs).as_posix()
            _no_symlink_components(root_abs, under)
            try:
                resolved = path.resolve()
                resolved.relative_to(root_res)
                rel = resolved.relative_to(corpus_res).as_posix()
            except ValueError as exc:
                raise AcceptanceInventoryError(
                    f"glob match escapes selection root or corpus under {root_rel}"
                ) from exc
            if rel not in exclude:
                root_rels.append(rel)
        if family.required and len(root_rels) < sel.minimum_per_root:
            diagnostics.append(
                InventoryDiagnostic(
                    "required_root_below_minimum",
                    f"root {root_rel} matched {len(root_rels)}; "
                    f"minimum_per_root={sel.minimum_per_root}",
                    fid,
                    root_rel,
                )
            )
            _fail(f"required root below minimum for {fid}: {root_rel}")
        if not family.required and not root_rels:
            diagnostics.append(
                InventoryDiagnostic(
                    "optional_root_empty",
                    f"optional root empty or unmatched: {root_rel}",
                    fid,
                    root_rel,
                )
            )
        selected.extend(root_rels)

    sources: list[InventorySource] = []
    for rel in selected:
        abs_path = _confined(corpus_root, rel)
        data = abs_path.read_bytes()
        _claim(claimed_rel, claimed_phys, rel, _phys(abs_path), fid)
        sources.append(
            InventorySource(
                path=abs_path.resolve().relative_to(repo_root.resolve()).as_posix(),
                family_id=fid,
                required=family.required,
                selection_reason=family.reason,
                sha256=_sha256_bytes(data),
                size_bytes=len(data),
            )
        )
    sources.sort(key=lambda s: s.path)
    return sources


def build_acceptance_inventory(
    repo_root: Path, manifest: AcceptanceInventoryManifest
) -> AcceptanceInventoryReport:
    repo_root = repo_root.resolve()
    corpus_root = _confined(repo_root, manifest.corpus_root)
    if not corpus_root.is_dir():
        _fail(f"corpus_root is not a directory: {manifest.corpus_root}")
    diagnostics: list[InventoryDiagnostic] = []
    claimed_rel: dict[str, str] = {}
    claimed_phys: dict[str, str] = {}
    all_sources: list[InventorySource] = []
    family_summaries: list[dict[str, Any]] = []
    for family in manifest.families:
        fam_sources = _expand_family(
            repo_root=repo_root,
            corpus_root=corpus_root,
            family=family,
            claimed_rel=claimed_rel,
            claimed_phys=claimed_phys,
            diagnostics=diagnostics,
        )
        all_sources.extend(fam_sources)
        family_summaries.append(
            {
                "family_id": family.family_id,
                "required": family.required,
                "reason": family.reason,
                "source_count": len(fam_sources),
            }
        )
    all_sources.sort(key=lambda s: s.path)
    summary = {
        "source_count": len(all_sources),
        "required_source_count": sum(1 for s in all_sources if s.required),
        "optional_source_count": sum(1 for s in all_sources if not s.required),
        "required_missing_count": sum(
            1 for d in diagnostics if d.code.startswith("required_")
        ),
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
