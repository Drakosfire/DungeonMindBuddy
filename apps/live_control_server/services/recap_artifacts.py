"""File-backed recap artifact registry for /plan graph projections."""
from __future__ import annotations

import json
import os
import re
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root
from src.live_play.live_store import load_json, write_json

RECAP_ARTIFACTS_ENV = "DUNGEONMIND_RECAP_ARTIFACTS_PATH"
DEFAULT_RECAP_ARTIFACTS_REL = "out/registries/recap_artifacts.json"
REGISTRY_SCHEMA = "dmb_recap_artifacts_registry_v1"
RECORD_SCHEMA = "dmb_recap_artifact_record_v1"
REGISTRY_VERSION = "0.1"

INGEST_RUNS_REL = "evals/graph_memory_layer/runs/live_recap_ingest"
GRAPH_ARTIFACTS_REL = "evals/graph_memory_layer/artifacts/category_graph_model_study"
EVAL_GRAPH_INGEST_RUNS_REL = "evals/graph_memory_layer/artifacts/graph_ingest_runs"
LAST_COHORT_MIRROR_REL = "evals/artifacts/category_graph_model_study/last_cohort_summary.json"

_SAFE_ARTIFACT_ID = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")


class RecapArtifactRegistryError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class GraphRunRef(BaseModel):
    run_uri: str
    model_id: str | None = None
    run_index: int | None = None
    canonical_ir_valid: bool | None = None
    scenario_estimated_cost_usd: float | None = None
    node_recall: float | None = None


class RecapArtifactRecord(BaseModel):
    schema_version: Literal["dmb_recap_artifact_record_v1"] = RECORD_SCHEMA
    artifact_id: str
    campaign_id: str
    session_id: str
    source_artifact_id: str | None = None
    source_recap_path: str
    breadcrumb_seed_path: str | None = None
    session_memory_records_path: str | None = None
    run_bundle_uri: str
    run_manifest_uri: str
    source_span_index_uri: str
    provenance_index_uri: str | None = None
    graph_run_refs: list[GraphRunRef] = Field(default_factory=list)
    default_graph_run_uri: str | None = None
    default_projection_mode: str = "recap_graph"
    source_sha256: str | None = None
    registered_at: str
    updated_at: str
    registry_source: Literal["scan", "explicit"] = "scan"


class RecapArtifactsRegistryDocument(BaseModel):
    schema_version: Literal["dmb_recap_artifacts_registry_v1"] = REGISTRY_SCHEMA
    version: str = REGISTRY_VERSION
    records: list[RecapArtifactRecord] = Field(default_factory=list)


class RecapArtifactsListResponse(BaseModel):
    schema_version: Literal["dmb_recap_artifacts_registry_v1"] = REGISTRY_SCHEMA
    version: str = REGISTRY_VERSION
    records: list[RecapArtifactRecord] = Field(default_factory=list)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _validate_artifact_id(artifact_id: str) -> str:
    cleaned = artifact_id.strip().replace("\\", "/")
    if not cleaned or not _SAFE_ARTIFACT_ID.fullmatch(cleaned):
        raise RecapArtifactRegistryError("unsafe artifact_id", status_code=422)
    if ".." in cleaned or cleaned.startswith("/"):
        raise RecapArtifactRegistryError("unsafe artifact_id", status_code=422)
    return cleaned


def normalize_session_id(session_id: str | int) -> str:
    if isinstance(session_id, int):
        return f"session-{session_id}"
    raw = str(session_id).strip().replace("\\", "/")
    if raw.isdigit():
        return f"session-{raw}"
    if raw.startswith("session-"):
        return raw
    match = re.search(r"(\d+)", raw)
    if match:
        return f"session-{match.group(1)}"
    return raw


def recap_artifacts_path(root: Path) -> Path:
    override = os.environ.get(RECAP_ARTIFACTS_ENV, "").strip()
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = root / candidate
        return candidate
    return root / DEFAULT_RECAP_ARTIFACTS_REL


def _rel_posix(root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _breadcrumb_seed_path(source_recap_path: str) -> str | None:
    if "/_normalized/" not in source_recap_path:
        return None
    seed_rel = source_recap_path.replace("/_normalized/", "/_breadcrumbed/").removesuffix(".md")
    return f"{seed_rel}.frontmatter_seed.md"


def _session_memory_path(source_recap_path: str) -> str | None:
    if "/_normalized/" not in source_recap_path:
        return None
    base = source_recap_path.replace("/_normalized/", "/_session_memory/").removesuffix(".md")
    return f"{base}.records_meta.jsonl"


def _session_number(session_id: str) -> int | None:
    marker = "session-"
    if marker not in session_id:
        return int(session_id) if session_id.isdigit() else None
    tail = session_id.split(marker, 1)[1]
    return int(tail) if tail.isdigit() else None


def _campaign_id_from_corpus_path(path: Path) -> str | None:
    parts = path.parts
    for index, part in enumerate(parts):
        if part == "Longmont Campaign" and index + 1 < len(parts):
            match = re.fullmatch(r"Campaign (\d+)", parts[index + 1])
            if match:
                return f"longmont-c{match.group(1)}"
    return None


def _normalized_recap_record_from_path(root: Path, recap_path: Path) -> RecapArtifactRecord | None:
    campaign_id = _campaign_id_from_corpus_path(recap_path)
    session_match = re.match(r"Session\s+(\d+)\b", recap_path.name)
    if campaign_id is None or session_match is None:
        return None
    session_id = normalize_session_id(int(session_match.group(1)))
    source_recap_path = _rel_posix(root, recap_path)
    now = _utc_now_iso()
    return RecapArtifactRecord(
        artifact_id=f"{campaign_id}/{session_id}",
        campaign_id=campaign_id,
        session_id=session_id,
        source_artifact_id=None,
        source_recap_path=source_recap_path,
        breadcrumb_seed_path=_breadcrumb_seed_path(source_recap_path),
        session_memory_records_path=_session_memory_path(source_recap_path),
        run_bundle_uri="",
        run_manifest_uri="",
        source_span_index_uri="",
        provenance_index_uri=None,
        graph_run_refs=[],
        default_graph_run_uri=None,
        source_sha256=f"sha256:{hashlib.sha256(recap_path.read_bytes()).hexdigest()}",
        registered_at=now,
        updated_at=now,
        registry_source="scan",
    )


def _load_registry_document(root: Path) -> RecapArtifactsRegistryDocument:
    path = recap_artifacts_path(root)
    if not path.is_file():
        return RecapArtifactsRegistryDocument()
    payload = load_json(path)
    return RecapArtifactsRegistryDocument.model_validate(payload)


def save_registry_document(root: Path, document: RecapArtifactsRegistryDocument) -> Path:
    path = recap_artifacts_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, document.model_dump(mode="json"))
    return path


def list_recap_artifact_records(
    root: Path | None = None,
    *,
    campaign_id: str | None = None,
) -> list[RecapArtifactRecord]:
    base = root or repo_root()
    records = _load_registry_document(base).records
    if campaign_id:
        records = [r for r in records if r.campaign_id == campaign_id]
    records.sort(key=lambda row: (_session_number(row.session_id) or 0, row.session_id))
    return records


def upsert_recap_artifact_record(
    root: Path,
    record: RecapArtifactRecord,
) -> RecapArtifactRecord:
    record.artifact_id = _validate_artifact_id(record.artifact_id)
    document = _load_registry_document(root)
    now = _utc_now_iso()
    existing = next((r for r in document.records if r.artifact_id == record.artifact_id), None)
    if existing:
        record.registered_at = existing.registered_at
    else:
        record.registered_at = record.registered_at or now
    record.updated_at = now
    document.records = [r for r in document.records if r.artifact_id != record.artifact_id]
    document.records.append(record)
    document.records.sort(key=lambda row: (_session_number(row.session_id) or 0, row.session_id))
    save_registry_document(root, document)
    return record


def resolve_recap_artifact_record(
    root: Path | None = None,
    *,
    artifact_id: str | None = None,
    campaign_id: str | None = None,
    session_id: str | None = None,
) -> RecapArtifactRecord:
    base = root or repo_root()
    records = list_recap_artifact_records(base, campaign_id=campaign_id)
    if not records:
        raise RecapArtifactRegistryError("no recap artifacts registered", status_code=404)

    if artifact_id:
        cleaned = _validate_artifact_id(artifact_id)
        match = next((r for r in records if r.artifact_id == cleaned), None)
        if match is None:
            raise RecapArtifactRegistryError(f"artifact not found: {cleaned}", status_code=404)
        return match

    normalized_session = normalize_session_id(session_id) if session_id is not None else None
    if campaign_id and normalized_session:
        match = next(
            (r for r in records if r.campaign_id == campaign_id and r.session_id == normalized_session),
            None,
        )
        if match is None:
            raise RecapArtifactRegistryError(
                f"artifact not found for {campaign_id}/{normalized_session}",
                status_code=404,
            )
        return match

    if normalized_session:
        match = next((r for r in records if r.session_id == normalized_session), None)
        if match is None:
            raise RecapArtifactRegistryError(f"artifact not found for session {normalized_session}", status_code=404)
        return match

    return records[-1]


def _graph_run_from_cohort_entry(entry: Mapping[str, Any]) -> GraphRunRef | None:
    run_uri = str(entry.get("run_dir") or "").strip().replace("\\", "/")
    if not run_uri:
        return None
    return GraphRunRef(
        run_uri=run_uri,
        model_id=str(entry.get("model_id") or "") or None,
        run_index=int(entry["run_index"]) if entry.get("run_index") is not None else None,
        canonical_ir_valid=bool(entry.get("canonical_ir_valid"))
        if entry.get("canonical_ir_valid") is not None
        else None,
        scenario_estimated_cost_usd=float(entry["scenario_estimated_cost_usd"])
        if entry.get("scenario_estimated_cost_usd") is not None
        else None,
        node_recall=float(entry.get("node_recall")) if entry.get("node_recall") is not None else None,
    )


def _record_from_eval_graph_ingest_manifest(
    root: Path, manifest_path: Path
) -> RecapArtifactRecord | None:
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if str(payload.get("status") or "") != "preview_union_store_ready":
        return None
    campaign_id = str(payload.get("campaign_id") or "").strip()
    session_id = normalize_session_id(str(payload.get("session_id") or ""))
    if not campaign_id or not session_id:
        return None
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    source_recap_path = str(source.get("normalized_recap_path") or "").replace("\\", "/")
    if not source_recap_path:
        return None
    run_uri = _rel_posix(root, manifest_path.parent)
    manifest_uri = _rel_posix(root, manifest_path)
    source_span_index_uri = str(source.get("source_span_index_uri") or "").replace("\\", "/")
    if not source_span_index_uri:
        source_span_index_uri = f"{run_uri}/source_span_index.json"
    health = payload.get("health") if isinstance(payload.get("health"), dict) else {}
    now = _utc_now_iso()
    return RecapArtifactRecord(
        artifact_id=f"{campaign_id}/{session_id}",
        campaign_id=campaign_id,
        session_id=session_id,
        source_artifact_id=str(source.get("source_artifact_id") or "") or None,
        source_recap_path=source_recap_path,
        breadcrumb_seed_path=_breadcrumb_seed_path(source_recap_path),
        session_memory_records_path=_session_memory_path(source_recap_path),
        run_bundle_uri=run_uri,
        run_manifest_uri=manifest_uri,
        source_span_index_uri=source_span_index_uri,
        provenance_index_uri=None,
        graph_run_refs=[
            GraphRunRef(
                run_uri=run_uri,
                model_id=str(health.get("model_id") or "") or None,
                canonical_ir_valid=bool(health.get("preview_union_store_valid"))
                if health.get("preview_union_store_valid") is not None
                else None,
            )
        ],
        default_graph_run_uri=run_uri,
        source_sha256=str(source.get("normalized_recap_sha256") or "") or None,
        registered_at=now,
        updated_at=now,
        registry_source="explicit",
    )


def _merge_eval_dogfood_record(
    existing: RecapArtifactRecord, incoming: RecapArtifactRecord
) -> RecapArtifactRecord:
    merged_refs = list(existing.graph_run_refs)
    seen = {ref.run_uri for ref in merged_refs}
    for ref in incoming.graph_run_refs:
        if ref.run_uri in seen:
            continue
        seen.add(ref.run_uri)
        merged_refs.append(ref)
    return existing.model_copy(
        update={
            "run_bundle_uri": incoming.run_bundle_uri or existing.run_bundle_uri,
            "run_manifest_uri": incoming.run_manifest_uri or existing.run_manifest_uri,
            "source_span_index_uri": incoming.source_span_index_uri or existing.source_span_index_uri,
            "graph_run_refs": merged_refs,
            "default_graph_run_uri": incoming.default_graph_run_uri or existing.default_graph_run_uri,
            "source_sha256": incoming.source_sha256 or existing.source_sha256,
            "updated_at": incoming.updated_at,
        }
    )


def _record_from_run_bundle(root: Path, bundle_dir: Path) -> RecapArtifactRecord | None:
    manifest_path = bundle_dir / "run_manifest.json"
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    campaign_id = str(manifest.get("campaign_id") or "").strip()
    session_id = normalize_session_id(str(manifest.get("session_id") or ""))
    if not campaign_id or not session_id:
        return None

    source = manifest.get("source") or {}
    source_recap_path = str(source.get("input_path_record") or "").replace("\\", "/")
    if not source_recap_path:
        return None

    bundle_uri = _rel_posix(root, bundle_dir)
    now = _utc_now_iso()
    source_artifact_path = bundle_dir / "source_artifact.json"
    source_artifact_id = None
    if source_artifact_path.is_file():
        source_artifact_id = str(json.loads(source_artifact_path.read_text(encoding="utf-8")).get("source_artifact_id") or "") or None

    return RecapArtifactRecord(
        artifact_id=f"{campaign_id}/{session_id}",
        campaign_id=campaign_id,
        session_id=session_id,
        source_artifact_id=source_artifact_id,
        source_recap_path=source_recap_path,
        breadcrumb_seed_path=_breadcrumb_seed_path(source_recap_path),
        session_memory_records_path=_session_memory_path(source_recap_path),
        run_bundle_uri=bundle_uri,
        run_manifest_uri=f"{bundle_uri}/run_manifest.json",
        source_span_index_uri=f"{bundle_uri}/source_span_index.json",
        provenance_index_uri=f"{bundle_uri}/provenance_index.json",
        graph_run_refs=[],
        default_graph_run_uri=None,
        source_sha256=str(source.get("input_sha256") or "") or None,
        registered_at=now,
        updated_at=now,
        registry_source="scan",
    )


def _collect_cohort_summaries(root: Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    mirror = root / LAST_COHORT_MIRROR_REL
    if mirror.is_file():
        summaries.append(json.loads(mirror.read_text(encoding="utf-8")))
    artifacts = root / GRAPH_ARTIFACTS_REL
    if artifacts.is_dir():
        for cohort_path in sorted(artifacts.rglob("cohort_summary.json")):
            summaries.append(json.loads(cohort_path.read_text(encoding="utf-8")))
    return summaries


def _preferred_bundle_dir(bundle_dirs: list[Path]) -> Path:
    for bundle_dir in bundle_dirs:
        if "category_study" in bundle_dir.name:
            return bundle_dir
    return sorted(bundle_dirs, key=lambda path: path.name)[-1]


def sync_recap_artifacts_registry(root: Path | None = None) -> RecapArtifactsRegistryDocument:
    base = root or repo_root()
    ingest_root = base / INGEST_RUNS_REL
    bundles_by_session: dict[tuple[str, str], list[Path]] = {}

    if ingest_root.is_dir():
        for bundle_dir in sorted(ingest_root.iterdir()):
            if not bundle_dir.is_dir():
                continue
            manifest_path = bundle_dir / "run_manifest.json"
            if not manifest_path.is_file():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            campaign_id = str(manifest.get("campaign_id") or "").strip()
            session_id = normalize_session_id(str(manifest.get("session_id") or ""))
            if not campaign_id or not session_id:
                continue
            bundles_by_session.setdefault((campaign_id, session_id), []).append(bundle_dir)

    records_by_id: dict[str, RecapArtifactRecord] = {}
    for (campaign_id, session_id), bundle_dirs in bundles_by_session.items():
        record = _record_from_run_bundle(base, _preferred_bundle_dir(bundle_dirs))
        if record is not None:
            records_by_id[record.artifact_id] = record

    corpus_root = base / "corpus/eldyrwild-markdown"
    if corpus_root.is_dir():
        for recap_path in sorted(corpus_root.glob("Longmont Campaign/Campaign */Session Recaps/_normalized/Session *.md")):
            record = _normalized_recap_record_from_path(base, recap_path)
            if record is not None:
                records_by_id.setdefault(record.artifact_id, record)

    eval_ingest_root = base / EVAL_GRAPH_INGEST_RUNS_REL
    if eval_ingest_root.is_dir():
        for manifest_path in sorted(eval_ingest_root.rglob("graph_ingest_run_manifest.json")):
            record = _record_from_eval_graph_ingest_manifest(base, manifest_path)
            if record is None:
                continue
            existing = records_by_id.get(record.artifact_id)
            if existing is None:
                records_by_id[record.artifact_id] = record
            else:
                records_by_id[record.artifact_id] = _merge_eval_dogfood_record(existing, record)

    for cohort in _collect_cohort_summaries(base):
        session_number = cohort.get("session")
        if session_number is None:
            continue
        session_id = normalize_session_id(int(session_number))
        matches = [r for r in records_by_id.values() if r.session_id == session_id]
        if not matches:
            continue
        graph_runs: list[GraphRunRef] = []
        seen: set[str] = set()
        for entry in cohort.get("runs") or []:
            if not isinstance(entry, Mapping):
                continue
            ref = _graph_run_from_cohort_entry(entry)
            if ref is None or ref.run_uri in seen:
                continue
            seen.add(ref.run_uri)
            graph_runs.append(ref)
        for record in matches:
            merged_seen = {ref.run_uri for ref in record.graph_run_refs}
            for ref in graph_runs:
                if ref.run_uri in merged_seen:
                    continue
                merged_seen.add(ref.run_uri)
                record.graph_run_refs.append(ref)
            record.default_graph_run_uri = None

    existing = _load_registry_document(base)
    for old in existing.records:
        if old.artifact_id not in records_by_id and old.registry_source == "explicit":
            records_by_id[old.artifact_id] = old

    document = RecapArtifactsRegistryDocument(
        records=sorted(
            records_by_id.values(),
            key=lambda row: (_session_number(row.session_id) or 0, row.session_id),
        )
    )
    save_registry_document(base, document)
    return document


def ensure_recap_artifacts_registry(root: Path | None = None) -> RecapArtifactsRegistryDocument:
    base = root or repo_root()
    return sync_recap_artifacts_registry(base)
