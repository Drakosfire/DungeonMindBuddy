"""Deterministic, read-only Eldyrwild C2 acceptance-corpus inventory."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

MANIFEST_SCHEMA = "dmb_world_acceptance_inventory_manifest_v2"
MANIFEST_VERSION = "2.0"
REPORT_SCHEMA = "dmb_world_acceptance_inventory_v2"
REPORT_VERSION = "2.0"
_MANIFEST_KEYS = frozenset(
    {
        "schema",
        "version",
        "world_id",
        "campaign_id",
        "corpus_root",
        "source_kind",
        "extraction_profile",
        "expected",
        "families",
    }
)
_FAMILY_KEYS = frozenset(
    {
        "family_id",
        "required",
        "reason",
        "canon_layer",
        "campaign_scope",
        "source_authority",
        "selection",
    }
)
_SELECTION_KEYS = frozenset({"files"})
_EXPECTED_KEYS = frozenset(
    {"source_count", "path_set_sha256", "content_set_sha256"}
)


class AcceptanceInventoryError(ValueError):
    """Manifest, path-confinement, or required-selection failure."""


@dataclass(frozen=True, slots=True)
class FamilySelection:
    files: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ManifestFamily:
    family_id: str
    required: bool
    reason: str
    canon_layer: str
    campaign_scope: str | None
    source_authority: str
    selection: FamilySelection


@dataclass(frozen=True, slots=True)
class AcceptanceInventoryManifest:
    schema: str
    version: str
    world_id: str
    campaign_id: str
    corpus_root: str
    source_kind: str
    extraction_profile: str
    expected_source_count: int
    expected_path_set_sha256: str
    expected_content_set_sha256: str
    families: tuple[ManifestFamily, ...]
    manifest_path: Path
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class InventorySource:
    path: str
    source_artifact_id: str
    source_revision_id: str
    family_id: str
    required: bool
    selection_reason: str
    canon_layer: str
    campaign_scope: str | None
    source_authority: str
    source_kind: str
    extraction_profile: str
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
    manifest_path: Path
    corpus_root_path: Path
    source_kind: str
    extraction_profile: str
    summary: Mapping[str, int]
    contract: Mapping[str, Any]
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
            "source_kind": self.source_kind,
            "extraction_profile": self.extraction_profile,
            "summary": dict(self.summary),
            "contract": dict(self.contract),
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


def _parse_selection(raw: Mapping[str, Any], family_id: str) -> FamilySelection:
    _reject_unknown(raw, _SELECTION_KEYS, f"{family_id}.selection")
    files = _req_str_list(raw.get("files", []), f"{family_id}.selection.files")
    if not files:
        _fail(f"{family_id}.selection.files must be a non-empty list")
    files_t = tuple(_posix_rel(i, f"{family_id}.selection.files") for i in files)
    if len(files_t) != len(set(files_t)):
        _fail(f"{family_id}.selection.files contains duplicates")
    return FamilySelection(files=files_t)


def _digest_lines(lines: Sequence[str]) -> str:
    return _sha256_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def _req_sha256(value: Any, label: str) -> str:
    text = _req_str(value, label)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        _fail(f"{label} must be a lowercase SHA-256 digest")
    return text


def _parse_family(raw: Mapping[str, Any], index: int, campaign_id: str) -> ManifestFamily:
    _reject_unknown(raw, _FAMILY_KEYS, f"families[{index}]")
    family_id = _req_str(raw.get("family_id"), f"families[{index}].family_id")
    canon_layer = _req_str(raw.get("canon_layer"), f"{family_id}.canon_layer")
    campaign_scope = raw.get("campaign_scope")
    if canon_layer == "world":
        if campaign_scope is not None:
            _fail(f"{family_id}.campaign_scope must be null for world sources")
    elif canon_layer == "campaign":
        if campaign_scope != campaign_id:
            _fail(f"{family_id}.campaign_scope must equal {campaign_id!r}")
    else:
        _fail(f"{family_id}.canon_layer must be 'world' or 'campaign'")
    return ManifestFamily(
        family_id=family_id,
        required=_req_bool(raw.get("required"), f"{family_id}.required"),
        reason=_req_str(raw.get("reason"), f"{family_id}.reason"),
        canon_layer=canon_layer,
        campaign_scope=campaign_scope,
        source_authority=_req_str(
            raw.get("source_authority"), f"{family_id}.source_authority"
        ),
        selection=_parse_selection(
            _req_map(raw.get("selection"), f"{family_id}.selection"), family_id
        ),
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
    campaign_id = _req_str(data.get("campaign_id"), "campaign_id")
    source_kind = _req_str(data.get("source_kind"), "source_kind")
    if source_kind != "source_extraction":
        _fail(f"unsupported source_kind: {source_kind!r}")
    extraction_profile = _req_str(data.get("extraction_profile"), "extraction_profile")
    expected = _req_map(data.get("expected"), "expected")
    _reject_unknown(expected, _EXPECTED_KEYS, "expected")
    expected_source_count = expected.get("source_count")
    if (
        not isinstance(expected_source_count, int)
        or isinstance(expected_source_count, bool)
        or expected_source_count < 1
    ):
        _fail("expected.source_count must be a positive int")
    families_raw = data.get("families")
    if not isinstance(families_raw, list) or not families_raw:
        _fail("families must be a non-empty list")
    families: list[ManifestFamily] = []
    seen: set[str] = set()
    for index, item in enumerate(families_raw):
        family = _parse_family(
            _req_map(item, f"families[{index}]"), index, campaign_id
        )
        if family.family_id in seen:
            _fail(f"duplicate family_id: {family.family_id}")
        seen.add(family.family_id)
        families.append(family)
    return AcceptanceInventoryManifest(
        schema=schema,
        version=version,
        world_id=_req_str(data.get("world_id"), "world_id"),
        campaign_id=campaign_id,
        corpus_root=_posix_rel(_req_str(data.get("corpus_root"), "corpus_root"), "corpus_root"),
        source_kind=source_kind,
        extraction_profile=extraction_profile,
        expected_source_count=expected_source_count,
        expected_path_set_sha256=_req_sha256(
            expected.get("path_set_sha256"), "expected.path_set_sha256"
        ),
        expected_content_set_sha256=_req_sha256(
            expected.get("content_set_sha256"), "expected.content_set_sha256"
        ),
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
    source_kind: str,
    extraction_profile: str,
) -> list[InventorySource]:
    fid = family.family_id
    sources: list[InventorySource] = []
    for rel in family.selection.files:
        abs_path = _confined(corpus_root, rel)
        if not abs_path.is_file():
            code = "required_file_missing" if family.required else "optional_file_missing"
            diagnostics.append(
                InventoryDiagnostic(code, f"selected file missing: {rel}", fid, rel)
            )
            if family.required:
                _fail(f"required file missing for {fid}: {rel}")
            continue
        data = abs_path.read_bytes()
        _claim(claimed_rel, claimed_phys, rel, _phys(abs_path), fid)
        sources.append(
            InventorySource(
                path=abs_path.resolve().relative_to(repo_root.resolve()).as_posix(),
                source_artifact_id=rel,
                source_revision_id=f"sha256:{_sha256_bytes(data)}",
                family_id=fid,
                required=family.required,
                selection_reason=family.reason,
                canon_layer=family.canon_layer,
                campaign_scope=family.campaign_scope,
                source_authority=family.source_authority,
                source_kind=source_kind,
                extraction_profile=extraction_profile,
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
            source_kind=manifest.source_kind,
            extraction_profile=manifest.extraction_profile,
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
    path_set_sha256 = _digest_lines(
        [source.source_artifact_id for source in all_sources]
    )
    content_set_sha256 = _digest_lines(
        [
            f"{source.source_artifact_id}\t{source.sha256}"
            for source in all_sources
        ]
    )
    if len(all_sources) != manifest.expected_source_count:
        _fail(
            "acceptance source count drift: "
            f"expected {manifest.expected_source_count}, got {len(all_sources)}"
        )
    if path_set_sha256 != manifest.expected_path_set_sha256:
        _fail("acceptance path-set digest drift")
    if content_set_sha256 != manifest.expected_content_set_sha256:
        _fail("acceptance content-set digest drift")
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
        manifest_path=manifest.manifest_path,
        corpus_root_path=corpus_root,
        source_kind=manifest.source_kind,
        extraction_profile=manifest.extraction_profile,
        summary=summary,
        contract={
            "source_count": len(all_sources),
            "path_set_sha256": path_set_sha256,
            "content_set_sha256": content_set_sha256,
        },
        families=family_summaries,
        sources=tuple(all_sources),
        diagnostics=tuple(diagnostics),
    )


def write_acceptance_inventory(
    report: AcceptanceInventoryReport, output_path: Path
) -> None:
    output_path = output_path.resolve()
    if output_path == report.manifest_path.resolve():
        _fail("output path must not overwrite the manifest")
    try:
        output_path.relative_to(report.corpus_root_path.resolve())
    except ValueError:
        pass
    else:
        _fail("output path must not be inside the corpus root")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report.to_dict(), indent=2, sort_keys=False, ensure_ascii=True)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload + "\n")
            temp_path = Path(handle.name)
        os.replace(temp_path, output_path)
    except OSError as exc:
        raise AcceptanceInventoryError(f"cannot write inventory: {output_path}") from exc


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
