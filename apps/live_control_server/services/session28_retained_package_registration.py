"""Preview and explicitly register the retained Session 28 review package.

This adapter imports already-produced artifacts. It never runs extraction, and
its preview path does not write to the repository or AppState.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from apps.live_control_server.services.promotable_ingest_run import (
    ingest_run_registry_roots,
    is_under_ingest_runs,
    is_under_world_store,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunDiagnostics,
    ExtractionRunStatus,
)

IMPORT_DERIVATION = "retained_recap_package_import_v1"
IMPORTER_VERSION = "session28-retained-package-registration-v1"
PINNED_INVENTORY_SHA256 = "b45f3d80f75262c3cef1802bc382a96e8d159e1d57d39aef41ce7a24d9927fae"
PINNED_MANIFEST_SHA256 = "13de71e0f0b493a98535230fd66296e863efa7f746333f1f311b0655e2375342"
PINNED_SOURCE_SHA256 = "d19e72c07e5aa5b584f7820c4d30a00df3e7706d5ec7bf7a45b19dce2f67b6eb"
PINNED_CANDIDATE_SHA256 = "2112fa630647154534cf9edc0437b367493cb6ae4d7597509915299a4592e1cd"
PINNED_VALIDATION_REPORT_SHA256 = "7ec537e690924df2244fb7130326041d8d374a03adb59f2dcc66aba347f985f1"
PINNED_KNOWN_ENTITY_MENTIONS_SHA256 = "aa8d39cb2d26dfcdb820fa7342d6e350f394598809187de587a2b5a7ad308dfd"
PINNED_PROVENANCE_INDEX_SHA256 = "8330e0debe95d3259c3152b499df9357910bd3418002b037f470967a417fcb9a"
PINNED_SPAN_INDEX_SHA256 = "d22fc2ea3d21c3491cde4c2a83878668b2a8c9285911dea264643db013b36e80"
PINNED_REVIEW_SNAPSHOT_SHA256 = "750513c15269f5cf3a81bb593e2c0054e3ec2b2db17062d51ebcd5301dd78dbe"
HISTORICAL_REVIEW_RUN_ID = "bcf698ee-45ba-4376-8780-3b56185302c8"
LEGACY_GRAPH_INGEST_RUN_ID = (
    "graph-ingest:longmont-c2:session-28:20261001T194854Z"
)
SOURCE_ARTIFACT_ID = "artifact:recap:longmont-c2:session-28:d19e72c07e5a"
CAMPAIGN_ID = "longmont-c2"
SESSION_ID = "session-28"
PROFILE_ID = "recap_category_v1@1.0"
EXPECTED_ASSERTION_COUNT = 61
EXPECTED_INVALID_EVIDENCE_COUNT = 1
EXPECTED_MANIFEST_PREFIX = "out/graph_memory/runs/longmont-c2/session-28/20261001T194758Z/"

# URI-to-file bindings are explicit. Import never guesses from a basename.
_URI_TO_PACKAGE_PATH = {
    f"{EXPECTED_MANIFEST_PREFIX}normalized_recap_source.md": "normalized_recap_source.md",
    f"{EXPECTED_MANIFEST_PREFIX}candidate_graph.json": "candidate_graph.json",
    f"{EXPECTED_MANIFEST_PREFIX}candidate_validation_report.json": "candidate_validation_report.json",
    f"{EXPECTED_MANIFEST_PREFIX}known_entity_mentions.json": "known_entity_mentions.json",
    f"{EXPECTED_MANIFEST_PREFIX}provenance_index.json": "provenance_index.json",
    f"{EXPECTED_MANIFEST_PREFIX}source_span_index.json": "source_span_index.json",
    f"{EXPECTED_MANIFEST_PREFIX}source_spans": "source_spans",
}


class RetainedPackageRegistrationError(ValueError):
    """Pinned retained package is invalid or conflicts with existing state."""


@dataclass(frozen=True)
class PackageFilePin:
    path: str
    sha256: str


@dataclass(frozen=True)
class VerifiedRetainedPackage:
    package_root: Path
    inventory_sha256: str
    files: tuple[PackageFilePin, ...]
    manifest: dict[str, Any]
    review_snapshot: dict[str, Any]
    source_sha256: str
    candidate_sha256: str
    span_index_sha256: str
    source_artifact_id: str
    uri_relocations: tuple[dict[str, str], ...]
    run_id: str
    preview_fingerprint: str

    def as_preview(self) -> dict[str, Any]:
        return {
            "schema": "dmb_session28_retained_package_preview_v1",
            "importer_version": IMPORTER_VERSION,
            "package_inventory_sha256": self.inventory_sha256,
            "preview_fingerprint": self.preview_fingerprint,
            "canonical_import_run_id": self.run_id,
            "historical_review_run_id": HISTORICAL_REVIEW_RUN_ID,
            "legacy_graph_ingest_run_id": LEGACY_GRAPH_INGEST_RUN_ID,
            "source_artifact_id": self.source_artifact_id,
            "source_sha256": self.source_sha256,
            "campaign_id": CAMPAIGN_ID,
            "session_id": SESSION_ID,
            "profile_id": PROFILE_ID,
            "package_file_count": len(self.files),
            "package_files": [
                {"path": item.path, "sha256": item.sha256} for item in self.files
            ],
            "uri_relocations": list(self.uri_relocations),
            "review_snapshot": {
                "sha256": PINNED_REVIEW_SNAPSHOT_SHA256,
                "assertion_count": EXPECTED_ASSERTION_COUNT,
                "inspection_status": "invalid_evidence",
                "invalid_evidence_count": EXPECTED_INVALID_EVIDENCE_COUNT,
                "promotable": False,
                "world_id": None,
            },
            "mode": "preview",
        }


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_inventory_sha256(files: tuple[PackageFilePin, ...]) -> str:
    """Hash sorted `relative-path<TAB>sha256` records with a final newline."""
    payload = "".join(
        f"{item.path}\t{item.sha256}\n" for item in sorted(files, key=lambda x: x.path)
    )
    return _sha256_bytes(payload.encode("utf-8"))


def _safe_relative_path(raw: Any) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw or "\x00" in raw:
        raise RetainedPackageRegistrationError("inventory contains an unsafe file path")
    rel = PurePosixPath(raw)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise RetainedPackageRegistrationError("inventory contains an unsafe file path")
    if rel.as_posix() != raw:
        raise RetainedPackageRegistrationError("inventory paths must be canonical POSIX paths")
    return raw


def _reject_symlinks(path: Path, *, root: Path) -> None:
    try:
        rel = path.relative_to(root)
    except ValueError as exc:
        raise RetainedPackageRegistrationError("package path escapes its pinned root") from exc
    cursor = root
    if root.is_symlink():
        raise RetainedPackageRegistrationError("package root must not be a symlink")
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise RetainedPackageRegistrationError("package contains a symlink")


def _read_verified_inventory(
    package_root: Path,
    inventory_path: Path,
    *,
    expected_inventory_sha256: str,
) -> tuple[tuple[PackageFilePin, ...], str]:
    raw_root = package_root.expanduser()
    raw_inventory = inventory_path.expanduser()
    if raw_root.is_symlink() or raw_inventory.is_symlink():
        raise RetainedPackageRegistrationError("package root and inventory must not be symlinks")
    root = raw_root.resolve(strict=True)
    inventory = raw_inventory.resolve(strict=True)
    if not root.is_dir():
        raise RetainedPackageRegistrationError("package root must be a real directory")
    if inventory.is_relative_to(root):
        raise RetainedPackageRegistrationError("hash inventory must be outside the package root")
    try:
        payload = json.loads(inventory.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RetainedPackageRegistrationError("package hash inventory is unreadable") from exc
    if not isinstance(payload, dict) or set(payload) != {"package_root", "files"}:
        raise RetainedPackageRegistrationError("package hash inventory has an unsupported shape")
    recorded_root = payload.get("package_root")
    if not isinstance(recorded_root, str) or Path(recorded_root).expanduser().resolve() != root:
        raise RetainedPackageRegistrationError("package root differs from its pinned inventory")
    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise RetainedPackageRegistrationError("package inventory has no file pins")

    pins: list[PackageFilePin] = []
    seen: set[str] = set()
    for row in raw_files:
        if not isinstance(row, dict) or set(row) - {"path", "sha256", "size", "bytes"}:
            raise RetainedPackageRegistrationError("package inventory entry is malformed")
        rel = _safe_relative_path(row.get("path"))
        digest = row.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(
            ch not in "0123456789abcdef" for ch in digest
        ):
            raise RetainedPackageRegistrationError("package inventory digest is malformed")
        if rel in seen:
            raise RetainedPackageRegistrationError("package inventory repeats a path")
        seen.add(rel)
        path = root.joinpath(*PurePosixPath(rel).parts)
        _reject_symlinks(path, root=root)
        if not path.is_file():
            raise RetainedPackageRegistrationError(f"pinned package file is missing: {rel}")
        recorded_size = row.get("size", row.get("bytes"))
        if recorded_size is not None and (
            isinstance(recorded_size, bool)
            or not isinstance(recorded_size, int)
            or recorded_size != path.stat().st_size
        ):
            raise RetainedPackageRegistrationError(f"package file size mismatch: {rel}")
        actual = _sha256_file(path)
        if actual != digest:
            raise RetainedPackageRegistrationError(f"package file hash mismatch: {rel}")
        pins.append(PackageFilePin(path=rel, sha256=digest))

    actual_files: set[str] = set()
    for current, dirs, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in dirs:
            entry = current_path / name
            if entry.is_symlink():
                raise RetainedPackageRegistrationError("package contains a symlink")
        for name in names:
            entry = current_path / name
            _reject_symlinks(entry, root=root)
            if not entry.is_file():
                raise RetainedPackageRegistrationError("package contains a non-file artifact")
            actual_files.add(entry.relative_to(root).as_posix())
    if actual_files != seen:
        raise RetainedPackageRegistrationError("package files differ from the complete pinned inventory")

    ordered = tuple(sorted(pins, key=lambda x: x.path))
    fingerprint = canonical_inventory_sha256(ordered)
    if fingerprint != expected_inventory_sha256:
        raise RetainedPackageRegistrationError("canonical package inventory fingerprint is not approved")
    return ordered, fingerprint


def _read_pinned_json(root: Path, files: tuple[PackageFilePin, ...], path: str) -> dict[str, Any]:
    pin = next((item for item in files if item.path == path), None)
    if pin is None:
        raise RetainedPackageRegistrationError(f"required package file is not pinned: {path}")
    try:
        value = json.loads((root / path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RetainedPackageRegistrationError(f"pinned JSON file is invalid: {path}") from exc
    if not isinstance(value, dict):
        raise RetainedPackageRegistrationError(f"pinned JSON root must be an object: {path}")
    return value


def _verify_manifest_and_review(
    root: Path, files: tuple[PackageFilePin, ...]
) -> tuple[dict[str, Any], dict[str, Any], tuple[dict[str, str], ...]]:
    manifest = _read_pinned_json(root, files, "graph_ingest_run_manifest.json")
    review = _read_pinned_json(root, files, "exact_run_review_package.json")
    digest_by_path = {item.path: item.sha256 for item in files}
    if digest_by_path.get("graph_ingest_run_manifest.json") != PINNED_MANIFEST_SHA256:
        raise RetainedPackageRegistrationError("retained manifest pin differs from authority")
    if digest_by_path.get("exact_run_review_package.json") != PINNED_REVIEW_SNAPSHOT_SHA256:
        raise RetainedPackageRegistrationError("retained review snapshot pin differs from authority")
    if digest_by_path.get("normalized_recap_source.md") != PINNED_SOURCE_SHA256:
        raise RetainedPackageRegistrationError("normalized source pin differs from authority")
    if digest_by_path.get("candidate_graph.json") != PINNED_CANDIDATE_SHA256:
        raise RetainedPackageRegistrationError("candidate graph pin differs from authority")
    if digest_by_path.get("source_span_index.json") != PINNED_SPAN_INDEX_SHA256:
        raise RetainedPackageRegistrationError("source span index pin differs from authority")
    if digest_by_path.get("candidate_validation_report.json") != PINNED_VALIDATION_REPORT_SHA256:
        raise RetainedPackageRegistrationError("candidate validation report pin differs from authority")
    if digest_by_path.get("known_entity_mentions.json") != PINNED_KNOWN_ENTITY_MENTIONS_SHA256:
        raise RetainedPackageRegistrationError("known entity mentions pin differs from authority")
    if digest_by_path.get("provenance_index.json") != PINNED_PROVENANCE_INDEX_SHA256:
        raise RetainedPackageRegistrationError("provenance index pin differs from authority")

    source = manifest.get("source")
    artifacts = manifest.get("artifacts")
    if (
        manifest.get("schema") != "dmb_graph_ingest_run_manifest_v0"
        or manifest.get("run_id") != LEGACY_GRAPH_INGEST_RUN_ID
        or not isinstance(manifest.get("diagnostics"), dict)
        or manifest["diagnostics"].get("extraction_run_id") != HISTORICAL_REVIEW_RUN_ID
        or manifest.get("campaign_id") != CAMPAIGN_ID
        or manifest.get("session_id") != SESSION_ID
        or not isinstance(source, dict)
        or not isinstance(artifacts, dict)
    ):
        raise RetainedPackageRegistrationError("retained run manifest identity differs from authority")
    if (
        source.get("source_artifact_id") != SOURCE_ARTIFACT_ID
        or source.get("source_domain") != "recap"
        or source.get("normalized_recap_sha256") != f"sha256:{PINNED_SOURCE_SHA256}"
        or source.get("normalized_recap_path")
        != f"{EXPECTED_MANIFEST_PREFIX}normalized_recap_source.md"
    ):
        raise RetainedPackageRegistrationError("retained source identity differs from authority")

    expected_artifacts = {
        "candidate_graph": ("candidate_graph.json", PINNED_CANDIDATE_SHA256),
        "candidate_validation_report": (
            "candidate_validation_report.json",
            PINNED_VALIDATION_REPORT_SHA256,
        ),
        "known_entity_mentions": (
            "known_entity_mentions.json",
            PINNED_KNOWN_ENTITY_MENTIONS_SHA256,
        ),
        "normalized_recap": ("normalized_recap_source.md", PINNED_SOURCE_SHA256),
        "provenance_index": (
            "provenance_index.json",
            None,
        ),
        "source_span_bundle": ("source_spans", None),
        "source_span_index": ("source_span_index.json", PINNED_SPAN_INDEX_SHA256),
    }
    if set(artifacts) != set(expected_artifacts):
        raise RetainedPackageRegistrationError("manifest artifact set differs from the verified package")
    old_uris: set[str] = set()
    for kind, (relative_path, expected_digest) in expected_artifacts.items():
        item = artifacts.get(kind)
        if not isinstance(item, dict):
            raise RetainedPackageRegistrationError(f"manifest artifact is malformed: {kind}")
        expected_uri = f"{EXPECTED_MANIFEST_PREFIX}{relative_path}"
        if item.get("uri") != expected_uri or item.get("exists") is not True:
            raise RetainedPackageRegistrationError(f"manifest artifact URI differs from authority: {kind}")
        if expected_digest is not None:
            manifest_digest = str(item.get("sha256") or "").removeprefix("sha256:")
            if manifest_digest != expected_digest:
                raise RetainedPackageRegistrationError(f"manifest artifact digest differs from authority: {kind}")
        if _URI_TO_PACKAGE_PATH.get(expected_uri) != relative_path:
            raise RetainedPackageRegistrationError(f"no explicit package relocation exists for {kind}")
        old_uris.add(expected_uri)
    for key in (
        "normalized_recap_path",
        "source_span_index_uri",
        "provenance_index_uri",
        "source_span_bundle_uri",
    ):
        uri = source.get(key)
        if not isinstance(uri, str) or _URI_TO_PACKAGE_PATH.get(uri) is None:
            raise RetainedPackageRegistrationError(f"manifest source URI has no exact relocation: {key}")
        old_uris.add(uri)

    if (
        review.get("schema") != "dmb_extract_promote_exact_run_review_v1"
        or review.get("runId") != HISTORICAL_REVIEW_RUN_ID
        or review.get("derivedFromRunId") is not None
        or review.get("sourceArtifactId") != SOURCE_ARTIFACT_ID
        or review.get("sourceRevisionId") != f"sha256:{PINNED_SOURCE_SHA256}"
        or review.get("campaignId") != CAMPAIGN_ID
        or review.get("sessionId") != SESSION_ID
        or review.get("worldId") is not None
        or review.get("inspectionStatus") != "invalid_evidence"
        or review.get("invalidEvidenceCount") != EXPECTED_INVALID_EVIDENCE_COUNT
        or review.get("promotable") is not False
        or review.get("firstWorldPublishEligible") is not False
        or not isinstance(review.get("assertions"), list)
        or len(review["assertions"]) != EXPECTED_ASSERTION_COUNT
    ):
        raise RetainedPackageRegistrationError("retained exact-review snapshot differs from authority")

    relocations = tuple(
        {
            "historical_uri": uri,
            "package_relative_path": _URI_TO_PACKAGE_PATH[uri],
        }
        for uri in sorted(old_uris)
    )
    return manifest, review, relocations


def _canonical_import_run_id(inventory_sha256: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"dmb:{IMPORT_DERIVATION}:{inventory_sha256}"))


def _preview_fingerprint(
    *,
    inventory_sha256: str,
    run_id: str,
    relocations: tuple[dict[str, str], ...],
    files: tuple[PackageFilePin, ...],
) -> str:
    payload = {
        "schema": "dmb_session28_retained_package_preview_v1",
        "importer_version": IMPORTER_VERSION,
        "inventory_sha256": inventory_sha256,
        "run_id": run_id,
        "historical_review_run_id": HISTORICAL_REVIEW_RUN_ID,
        "legacy_graph_ingest_run_id": LEGACY_GRAPH_INGEST_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_sha256": PINNED_SOURCE_SHA256,
        "campaign_id": CAMPAIGN_ID,
        "session_id": SESSION_ID,
        "profile_id": PROFILE_ID,
        "files": [{"path": f.path, "sha256": f.sha256} for f in files],
        "uri_relocations": list(relocations),
    }
    return _sha256_bytes(_canonical_json(payload))


def preview_retained_package(
    *,
    package_root: Path,
    inventory_path: Path,
    expected_inventory_sha256: str = PINNED_INVENTORY_SHA256,
) -> VerifiedRetainedPackage:
    root = package_root.expanduser().resolve(strict=True)
    files, inventory_sha = _read_verified_inventory(
        root,
        inventory_path,
        expected_inventory_sha256=expected_inventory_sha256,
    )
    manifest, review, relocations = _verify_manifest_and_review(root, files)
    run_id = _canonical_import_run_id(inventory_sha)
    if run_id in {HISTORICAL_REVIEW_RUN_ID, LEGACY_GRAPH_INGEST_RUN_ID}:
        raise RetainedPackageRegistrationError("new import identity aliases a historical run")
    fingerprint = _preview_fingerprint(
        inventory_sha256=inventory_sha,
        run_id=run_id,
        relocations=relocations,
        files=files,
    )
    return VerifiedRetainedPackage(
        package_root=root,
        inventory_sha256=inventory_sha,
        files=files,
        manifest=manifest,
        review_snapshot=review,
        source_sha256=PINNED_SOURCE_SHA256,
        candidate_sha256=PINNED_CANDIDATE_SHA256,
        span_index_sha256=PINNED_SPAN_INDEX_SHA256,
        source_artifact_id=SOURCE_ARTIFACT_ID,
        uri_relocations=relocations,
        run_id=run_id,
        preview_fingerprint=fingerprint,
    )


def _staged_package_path(root: Path, run_id: str) -> Path:
    roots = ingest_run_registry_roots(root)
    repo = root.resolve()
    candidates = [candidate.resolve() for candidate in roots]
    registry_root = next(
        (candidate for candidate in candidates if candidate.is_relative_to(repo)), None
    )
    if registry_root is None:
        raise RetainedPackageRegistrationError("configured ingest registry is outside the repository")
    path = registry_root / "retained_package_imports" / run_id / "package"
    _reject_symlinks(path, root=registry_root)
    if not path.resolve().is_relative_to(registry_root):
        raise RetainedPackageRegistrationError("staged package path escapes ingest registry")
    if is_under_world_store(path, root=root) or not is_under_ingest_runs(path, root=root):
        raise RetainedPackageRegistrationError("staged package path is outside the ingest registry")
    return path


def _verify_existing_stage(target: Path, pins: tuple[PackageFilePin, ...]) -> None:
    if not target.is_dir() or target.is_symlink():
        raise RetainedPackageRegistrationError("existing staged package path is not a real directory")
    expected = {pin.path: pin.sha256 for pin in pins}
    actual: set[str] = set()
    for current, dirs, names in os.walk(target, followlinks=False):
        base = Path(current)
        if any((base / item).is_symlink() for item in dirs):
            raise RetainedPackageRegistrationError("existing staged package contains a symlink")
        for name in names:
            path = base / name
            if path.is_symlink() or not path.is_file():
                raise RetainedPackageRegistrationError("existing staged package contains an unsafe entry")
            rel = path.relative_to(target).as_posix()
            actual.add(rel)
            if expected.get(rel) != _sha256_file(path):
                raise RetainedPackageRegistrationError("existing staged package conflicts with verified pins")
    if actual != set(expected):
        raise RetainedPackageRegistrationError("existing staged package is incomplete or has extra files")


def _stage_verified_package(
    verified: VerifiedRetainedPackage,
    *,
    repo_root: Path,
) -> Path:
    target = _staged_package_path(repo_root, verified.run_id)
    target_parent = target.parent
    target_parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        _verify_existing_stage(target, verified.files)
        return target

    created = False
    try:
        target.mkdir(exist_ok=False)
        created = True
        for pin in verified.files:
            source = verified.package_root / pin.path
            _reject_symlinks(source, root=verified.package_root)
            if _sha256_file(source) != pin.sha256:
                raise RetainedPackageRegistrationError(f"package changed during staging: {pin.path}")
            destination = target.joinpath(*PurePosixPath(pin.path).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() or destination.is_symlink():
                raise RetainedPackageRegistrationError("staging refuses to overwrite an existing file")
            with source.open("rb") as reader, destination.open("xb") as writer:
                shutil.copyfileobj(reader, writer)
            if _sha256_file(destination) != pin.sha256:
                raise RetainedPackageRegistrationError(f"staged file hash mismatch: {pin.path}")
        _verify_existing_stage(target, verified.files)
        return target
    except Exception:
        if created and target.exists():
            shutil.rmtree(target)
        raise


def _repo_uri(repo_root: Path, path: Path) -> str:
    resolved_root = repo_root.resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise RetainedPackageRegistrationError("component URI escapes repository root")
    return f"repo://{resolved_path.relative_to(resolved_root).as_posix()}"


def _component_refs(
    *,
    repo_root: Path,
    package_dir: Path,
    artifact_uri: str,
) -> dict[str, ExtractionRunComponentRef]:
    pins = {
        "source_span_index": ("source_span_index.json", PINNED_SPAN_INDEX_SHA256),
        "candidate_graph": ("candidate_graph.json", PINNED_CANDIDATE_SHA256),
        "validation_report": (
            "candidate_validation_report.json",
            PINNED_VALIDATION_REPORT_SHA256,
        ),
        "provenance_index": (
            "provenance_index.json",
            PINNED_PROVENANCE_INDEX_SHA256,
        ),
    }
    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=artifact_uri,
            sha256=PINNED_SOURCE_SHA256,
            exists=True,
        )
    }
    for name, (relative, digest) in pins.items():
        path = package_dir / relative
        if _sha256_file(path) != digest:
            raise RetainedPackageRegistrationError(f"staged component changed: {relative}")
        kind = ExtractionRunComponentKind(name)
        components[name] = ExtractionRunComponentRef(
            kind=kind,
            uri=_repo_uri(repo_root, path),
            sha256=digest,
            exists=True,
        )
    return components


def _lineage_for_import(verified: VerifiedRetainedPackage, staged_dir: Path, root: Path) -> dict[str, Any]:
    relocations = []
    for row in verified.uri_relocations:
        staged_path = staged_dir / row["package_relative_path"]
        relocations.append(
            {
                **row,
                "staged_repo_uri": _repo_uri(root, staged_path),
            }
        )
    return {
        "derivation": IMPORT_DERIVATION,
        "importer_version": IMPORTER_VERSION,
        "import_fingerprint": verified.preview_fingerprint,
        "package_inventory_sha256": verified.inventory_sha256,
        "historical_review_run_id": HISTORICAL_REVIEW_RUN_ID,
        "legacy_graph_ingest_run_id": LEGACY_GRAPH_INGEST_RUN_ID,
        "historical_input_path_record": verified.manifest["source"]["input_path_record"],
        "uri_relocations": relocations,
        "package_file_sha256": [
            {"path": item.path, "sha256": item.sha256} for item in verified.files
        ],
    }


def _assert_source_artifact_matches(artifact: Any, verified: VerifiedRetainedPackage) -> None:
    if (
        artifact.source_artifact_id != verified.source_artifact_id
        or str(artifact.source_domain) != "recap"
        or artifact.campaign_id != CAMPAIGN_ID
        or artifact.session_id != SESSION_ID
        or (artifact.content_sha256 or "").removeprefix("sha256:") != verified.source_sha256
        or artifact.world_id is not None
    ):
        raise RetainedPackageRegistrationError("existing SourceArtifact conflicts with package identity")


def _assert_existing_run_matches(
    run: ExtractionRun,
    verified: VerifiedRetainedPackage,
    *,
    components: dict[str, ExtractionRunComponentRef],
    lineage: dict[str, Any],
) -> None:
    stored_components = {
        key: (value.kind, value.uri, value.sha256, value.exists)
        for key, value in run.components.items()
    }
    expected_components = {
        key: (value.kind, value.uri, value.sha256, value.exists)
        for key, value in components.items()
    }
    if (
        run.run_id != verified.run_id
        or run.source_artifact_id != verified.source_artifact_id
        or run.source_domain != "recap"
        or run.campaign_id != CAMPAIGN_ID
        or run.session_id != SESSION_ID
        or run.profile_id != PROFILE_ID
        or run.status != ExtractionRunStatus.REVIEWABLE
        or run.lineage.get("derivation") != IMPORT_DERIVATION
        or run.lineage.get("import_fingerprint") != verified.preview_fingerprint
        or run.lineage != lineage
        or stored_components != expected_components
    ):
        raise RetainedPackageRegistrationError("canonical import run ID is occupied by different data")


def _assert_review_result(review: Any, *, expected_run_id: str) -> None:
    if (
        getattr(review, "run_id", None) != expected_run_id
        or getattr(review, "derived_from_run_id", None) is not None
        or getattr(review, "campaign_id", None) != CAMPAIGN_ID
        or getattr(review, "session_id", None) != SESSION_ID
        or getattr(review, "source_artifact_id", None) != SOURCE_ARTIFACT_ID
        or getattr(review, "source_revision_id", None) != f"sha256:{PINNED_SOURCE_SHA256}"
        or getattr(review, "world_id", None) is not None
        or getattr(review, "inspection_status", None) != "invalid_evidence"
        or getattr(review, "invalid_evidence_count", None) != EXPECTED_INVALID_EVIDENCE_COUNT
        or getattr(review, "promotable", None) is not False
        or getattr(review, "first_world_publish_eligible", None) is not False
        or len(getattr(review, "assertions", [])) != EXPECTED_ASSERTION_COUNT
    ):
        raise RetainedPackageRegistrationError("exact review result differs from retained snapshot contract")


def register_retained_package(
    *,
    package_root: Path,
    inventory_path: Path,
    repo_root: Path,
    expected_preview_fingerprint: str,
    expected_inventory_sha256: str = PINNED_INVENTORY_SHA256,
) -> dict[str, Any]:
    """Apply a preview only when its exact fingerprint is supplied.

    This function is intentionally not called by the CLI unless the operator
    passes ``--apply`` and the matching preview fingerprint. It is never used
    by tests against an operator database.
    """
    verified = preview_retained_package(
        package_root=package_root,
        inventory_path=inventory_path,
        expected_inventory_sha256=expected_inventory_sha256,
    )
    if expected_preview_fingerprint != verified.preview_fingerprint:
        raise RetainedPackageRegistrationError("apply fingerprint differs from current preview")

    root = repo_root.expanduser().resolve(strict=True)
    package_dir = _stage_verified_package(verified, repo_root=root)
    lineage = _lineage_for_import(verified, package_dir, root)

    from apps.live_control_server.services import graph_run_registry as runs
    from apps.live_control_server.services import source_artifact_registry as sources
    from apps.live_control_server.services.extract_promote import get_exact_run_review_package

    try:
        artifact = sources.get_source_artifact(root, verified.source_artifact_id)
    except sources.SourceArtifactRegistryError as exc:
        if exc.status_code != 404:
            raise RetainedPackageRegistrationError("existing SourceArtifact could not be verified") from exc
        source_text = (verified.package_root / "normalized_recap_source.md").read_text(
            encoding="utf-8"
        )
        artifact = sources.create_recap_source_artifact(
            root,
            campaign_id=CAMPAIGN_ID,
            session_id=SESSION_ID,
            recap_text=source_text,
            expected_content_sha256=verified.source_sha256,
        )
    _assert_source_artifact_matches(artifact, verified)

    components = _component_refs(
        repo_root=root,
        package_dir=package_dir,
        artifact_uri=artifact.uri,
    )
    try:
        existing = runs.get_extraction_run(root, verified.run_id)
    except runs.GraphRunRegistryError as exc:
        if exc.status_code != 404:
            raise RetainedPackageRegistrationError("existing import run could not be verified") from exc
        existing = None
    if existing is not None:
        _assert_existing_run_matches(
            existing,
            verified,
            components=components,
            lineage=lineage,
        )
        result = existing
        idempotent = True
    else:
        run = ExtractionRun(
            run_id=verified.run_id,
            source_artifact_id=verified.source_artifact_id,
            source_domain="recap",
            status=ExtractionRunStatus.REVIEWABLE,
            revision=1,
            campaign_id=CAMPAIGN_ID,
            session_id=SESSION_ID,
            profile_id=PROFILE_ID,
            # The facade sets created_at/updated_at to current import time.
            components=components,
            diagnostics=ExtractionRunDiagnostics(
                messages=["Imported from a complete, hash-verified retained recap package."]
            ),
            lineage=lineage,
        )
        try:
            result = runs.create_extraction_run(
                root,
                run_id=run.run_id,
                source_artifact_id=run.source_artifact_id,
                source_domain=run.source_domain,
                campaign_id=run.campaign_id,
                session_id=run.session_id,
                profile_id=run.profile_id,
                components=run.components,
                status=run.status,
                diagnostics=run.diagnostics,
                lineage=run.lineage,
            )
            idempotent = False
        except runs.GraphRunRegistryError as exc:
            # A concurrent identical import may win the deterministic-ID race.
            try:
                existing = runs.get_extraction_run(root, verified.run_id)
            except runs.GraphRunRegistryError:
                raise RetainedPackageRegistrationError("canonical import run creation failed") from exc
            _assert_existing_run_matches(
                existing,
                verified,
                components=components,
                lineage=lineage,
            )
            result = existing
            idempotent = True

    review = get_exact_run_review_package(result.run_id)
    _assert_review_result(review, expected_run_id=verified.run_id)
    preview = verified.as_preview()
    preview["mode"] = "applied"
    preview["canonical_import_run_id"] = result.run_id
    preview["created_at"] = result.created_at
    preview["idempotent_replay"] = idempotent
    preview["exact_review"] = {
        "assertion_count": len(review.assertions),
        "inspection_status": review.inspection_status,
        "invalid_evidence_count": review.invalid_evidence_count,
        "promotable": review.promotable,
        "world_id": review.world_id,
        "first_world_publish_eligible": review.first_world_publish_eligible,
    }
    return preview
