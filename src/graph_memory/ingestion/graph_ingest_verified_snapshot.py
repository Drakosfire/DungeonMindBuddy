"""Read-once verified snapshot loader for graph-ingest run manifests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from graph_memory.extraction.known_entity_mention_schema import (
    KNOWN_ENTITY_MENTION_SIDECAR_SCHEMA,
    KNOWN_ENTITY_MENTION_SIDECAR_VERSION,
    KnownEntityMention,
    KnownEntityMentionSidecar,
)
from graph_memory.ingestion.extraction_run import normalize_content_digest
from graph_memory.ingestion.graph_ingest_run import (
    GraphIngestArtifactKind,
    GraphIngestRunStatus,
)
from graph_memory.source_span import (
    SourceSpanIndex,
    source_span_index_from_dict,
    validate_source_span_index,
)
from graph_memory.ingestion.graph_ingest_validate import (
    CANDIDATE_READY_STATUSES,
    CANDIDATE_VALIDATION_REPORT_SCHEMA,
    CANDIDATE_VALIDATION_REPORT_VERSION,
    FORBIDDEN_DIAGNOSTIC_FLAGS,
    PREVIEW_UNION_VALIDATION_REPORT_SCHEMA,
    PREVIEW_UNION_VALIDATION_REPORT_VERSION,
    _resolve_manifest_uri,
    assert_requested_session_matches_manifest,
    known_entity_mentions_artifact_declared,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore

PROJECTION_SCHEMA = "dmb_recap_graph_projection_v0"
PROJECTION_DEPENDENCY_CONTRACT_SCHEMA = "dmb_projection_dependency_contract_v1"
PROJECTION_DEPENDENCY_CONTRACT_VERSION = "1.1"
PROJECTION_CONTRACT_VERSION = PROJECTION_DEPENDENCY_CONTRACT_VERSION
REQUIRED_REPORT_LIFECYCLE = {
    "preview_only": True,
    "canon_promotion": False,
    "approved_memory_write": False,
    "corpus_mutation": False,
    "production_retrieval": False,
}
PROJECTION_READY_STATUSES = {
    GraphIngestRunStatus.PREVIEW_UNION_STORE_READY,
    GraphIngestRunStatus.READY_FOR_PROJECTION,
}


def format_digest(hex_or_prefixed: str | None) -> str | None:
    digest = normalize_content_digest(hex_or_prefixed)
    if not digest:
        return None
    return f"sha256:{digest}"


def normalize_authored_overlay_identity(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return "absent"
    if text == "absent" or text.startswith("valid:") or text.startswith("invalid:"):
        return text
    digest = normalize_content_digest(text)
    if digest:
        return f"valid:sha256:{digest}"
    return "absent"


def authored_overlay_identity_from_mapping(raw: Mapping[str, Any]) -> str:
    identity = raw.get("authored_overlay_identity")
    if identity is not None and str(identity).strip():
        return normalize_authored_overlay_identity(str(identity))
    legacy_digest = normalize_content_digest(raw.get("authored_overlay_sha256"))
    if legacy_digest:
        return f"valid:sha256:{legacy_digest}"
    return "absent"


@dataclass(frozen=True)
class ProjectionDependencyContract:
    projection_schema: str
    projection_contract_version: str
    campaign_id: str
    session_id: str
    normalized_recap_sha256: str
    source_span_index_sha256: str
    candidate_graph_sha256: str
    candidate_validation_report_sha256: str
    schema: str = PROJECTION_DEPENDENCY_CONTRACT_SCHEMA
    version: str = PROJECTION_DEPENDENCY_CONTRACT_VERSION
    known_entity_mentions_sha256: str | None = None
    preview_union_store_sha256: str | None = None
    authored_overlay_identity: str = "absent"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "projection_schema": self.projection_schema,
            "projection_contract_version": self.projection_contract_version,
            "campaign_id": self.campaign_id,
            "session_id": self.session_id,
            "normalized_recap_sha256": format_digest(self.normalized_recap_sha256),
            "source_span_index_sha256": format_digest(self.source_span_index_sha256),
            "known_entity_mentions_sha256": format_digest(
                self.known_entity_mentions_sha256
            ),
            "preview_union_store_sha256": format_digest(
                self.preview_union_store_sha256
            ),
            "candidate_graph_sha256": format_digest(self.candidate_graph_sha256),
            "candidate_validation_report_sha256": format_digest(
                self.candidate_validation_report_sha256
            ),
            "authored_overlay_identity": self.authored_overlay_identity,
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ProjectionDependencyContract:
        def _required_digest(key: str) -> str:
            digest = normalize_content_digest(raw.get(key))
            if not digest:
                raise ValueError(f"{key} is required")
            return digest

        def _optional_digest(key: str) -> str | None:
            digest = normalize_content_digest(raw.get(key))
            return digest or None

        campaign_id = str(raw.get("campaign_id") or "").strip()
        session_id = str(raw.get("session_id") or "").strip()
        if not campaign_id:
            raise ValueError("campaign_id is required")
        if not session_id:
            raise ValueError("session_id is required")
        projection_schema = str(raw.get("projection_schema") or "").strip()
        if not projection_schema:
            raise ValueError("projection_schema is required")
        projection_contract_version = str(
            raw.get("projection_contract_version") or ""
        ).strip()
        if not projection_contract_version:
            raise ValueError("projection_contract_version is required")
        contract_schema = str(raw.get("schema") or "").strip()
        if not contract_schema:
            raise ValueError("schema is required")
        contract_version = str(raw.get("version") or "").strip()
        if not contract_version:
            raise ValueError("version is required")
        return cls(
            schema=contract_schema,
            version=contract_version,
            projection_schema=projection_schema,
            projection_contract_version=projection_contract_version,
            campaign_id=campaign_id,
            session_id=session_id,
            normalized_recap_sha256=_required_digest("normalized_recap_sha256"),
            source_span_index_sha256=_required_digest("source_span_index_sha256"),
            known_entity_mentions_sha256=_optional_digest("known_entity_mentions_sha256"),
            preview_union_store_sha256=_optional_digest("preview_union_store_sha256"),
            candidate_graph_sha256=_required_digest("candidate_graph_sha256"),
            candidate_validation_report_sha256=_required_digest(
                "candidate_validation_report_sha256"
            ),
            authored_overlay_identity=authored_overlay_identity_from_mapping(raw),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProjectionDependencyContract):
            return NotImplemented
        return (
            self.schema == other.schema
            and self.version == other.version
            and self.projection_schema == other.projection_schema
            and self.projection_contract_version == other.projection_contract_version
            and self.campaign_id == other.campaign_id
            and self.session_id == other.session_id
            and normalize_content_digest(self.normalized_recap_sha256)
            == normalize_content_digest(other.normalized_recap_sha256)
            and normalize_content_digest(self.source_span_index_sha256)
            == normalize_content_digest(other.source_span_index_sha256)
            and normalize_content_digest(self.known_entity_mentions_sha256)
            == normalize_content_digest(other.known_entity_mentions_sha256)
            and normalize_content_digest(self.preview_union_store_sha256)
            == normalize_content_digest(other.preview_union_store_sha256)
            and normalize_content_digest(self.candidate_graph_sha256)
            == normalize_content_digest(other.candidate_graph_sha256)
            and normalize_content_digest(self.candidate_validation_report_sha256)
            == normalize_content_digest(other.candidate_validation_report_sha256)
            and self.authored_overlay_identity == other.authored_overlay_identity
        )


def projection_dependency_contracts_match(
    a: ProjectionDependencyContract | Mapping[str, Any],
    b: ProjectionDependencyContract | Mapping[str, Any],
) -> bool:
    left = a if isinstance(a, ProjectionDependencyContract) else ProjectionDependencyContract.from_mapping(a)
    right = b if isinstance(b, ProjectionDependencyContract) else ProjectionDependencyContract.from_mapping(b)
    return left == right


@dataclass(frozen=True)
class VerifiedManifestBackedGraphSnapshot:
    manifest_payload: dict[str, Any]
    manifest_sha256: str
    campaign_id: str
    session_id: str
    normalized_recap_text: str
    normalized_recap_sha256: str
    source_span_index: SourceSpanIndex
    source_span_index_sha256: str
    candidate_graph: dict[str, Any]
    candidate_graph_sha256: str
    candidate_validation_report: dict[str, Any]
    candidate_validation_report_sha256: str
    dependency_contract: ProjectionDependencyContract
    known_entity_mentions: dict[str, Any] | None = None
    known_entity_mentions_sha256: str | None = None
    preview_union_store: Any | None = None
    preview_union_store_sha256: str | None = None
    preview_union_validation_report: dict[str, Any] | None = None
    preview_union_validation_report_sha256: str | None = None
    authored_overlay: Any | None = None
    authored_overlay_summary: Any | None = None

    def span_rows(self) -> list[dict[str, Any]]:
        return [asdict(span) for span in self.source_span_index.spans]

    def paragraph_text_by_span_id(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for span in self.source_span_index.spans:
            text = _paragraph_text_for_span(
                recap_text=self.normalized_recap_text,
                start_line=span.start_line,
                end_line=span.end_line,
            )
            if text:
                out[span.source_span_id] = text
        return out


def _paragraph_text_for_span(
    *,
    recap_text: str,
    start_line: int,
    end_line: int,
) -> str:
    lines = recap_text.splitlines()
    if start_line < 1 or end_line < start_line or end_line > len(lines):
        return ""
    return "\n".join(lines[start_line - 1 : end_line])


def _manifest_source(payload: Mapping[str, Any]) -> dict[str, Any]:
    source = payload.get("source")
    if not isinstance(source, dict):
        raise ValueError("manifest source must be an object")
    return source


def _manifest_artifacts(payload: Mapping[str, Any]) -> dict[str, Any]:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("manifest artifacts must be an object")
    return artifacts


def _artifact_ref(payload: Mapping[str, Any], kind: str, *, label: str | None = None) -> dict[str, Any]:
    name = label or kind
    artifacts = _manifest_artifacts(payload)
    artifact = artifacts.get(kind)
    if not isinstance(artifact, dict):
        raise ValueError(f"artifacts.{name} is required")
    uri = artifact.get("uri")
    if not isinstance(uri, str) or not uri.strip():
        raise ValueError(f"artifacts.{name}.uri is required")
    claimed = artifact.get("sha256")
    if not isinstance(claimed, str) or not claimed.strip():
        raise ValueError(f"artifacts.{name}.sha256 is required")
    return artifact


def _read_verified_bytes(
    repo_root: Path,
    uri: str,
    claimed_sha256: str,
    *,
    label: str,
) -> tuple[bytes, str]:
    try:
        path = _resolve_manifest_uri(repo_root, uri)
    except ValueError as exc:
        raise ValueError(f"{label} URI escapes repo root: {exc}") from exc
    if not path.is_file():
        raise ValueError(f"{label} file is missing")
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest().lower()
    if normalize_content_digest(claimed_sha256) != actual:
        raise ValueError(f"{label} sha256 does not match file bytes")
    return raw, actual


def _load_manifest(manifest_path: Path) -> tuple[dict[str, Any], str]:
    if not manifest_path.is_file():
        raise ValueError(f"manifest file is missing: {manifest_path}")
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest().lower()
    try:
        payload = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"manifest is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("manifest payload must be an object")
    campaign_id = str(payload.get("campaign_id") or "").strip()
    session_id = str(payload.get("session_id") or "").strip()
    if not campaign_id:
        raise ValueError("manifest campaign_id is required")
    if not session_id:
        raise ValueError("manifest session_id is required")
    return payload, manifest_sha256


def _parse_status(payload: Mapping[str, Any]) -> GraphIngestRunStatus:
    raw = payload.get("status")
    try:
        return GraphIngestRunStatus(str(raw))
    except ValueError as exc:
        raise ValueError(f"unknown manifest status: {raw!r}") from exc


def _validate_report_lifecycle(
    diagnostics: Any,
    *,
    label: str,
) -> None:
    if not isinstance(diagnostics, dict):
        raise ValueError(f"{label}.diagnostics must be an object")
    preview_only = diagnostics.get("preview_only")
    if preview_only is not True:
        raise ValueError(f"{label}.diagnostics.preview_only must be true")
    for flag in FORBIDDEN_DIAGNOSTIC_FLAGS:
        if diagnostics.get(flag) is not False:
            raise ValueError(f"{label}.diagnostics.{flag} must be false")


def _validate_semantic_validation_report(
    report_payload: Mapping[str, Any],
    *,
    payload: Mapping[str, Any],
    report_label: str,
    expected_schema: str,
    expected_version: str,
    path_field: str,
    expected_path: str,
    digest_field: str,
    expected_digest: str,
) -> None:
    if report_payload.get("schema") != expected_schema:
        raise ValueError(
            f"{report_label}.schema must be {expected_schema}, "
            f"got {report_payload.get('schema')!r}"
        )
    if report_payload.get("version") != expected_version:
        raise ValueError(
            f"{report_label}.version must be {expected_version}, "
            f"got {report_payload.get('version')!r}"
        )
    campaign_id = str(payload.get("campaign_id") or "").strip()
    session_id = str(payload.get("session_id") or "").strip()
    if str(report_payload.get("campaign_id") or "").strip() != campaign_id:
        raise ValueError(f"{report_label}.campaign_id does not match manifest")
    if str(report_payload.get("session_id") or "").strip() != session_id:
        raise ValueError(f"{report_label}.session_id does not match manifest")
    report_path = str(report_payload.get(path_field) or "").strip()
    if not report_path:
        raise ValueError(f"{report_label}.{path_field} is required")
    if report_path != expected_path.strip():
        raise ValueError(f"{report_label}.{path_field} does not match artifacts path")
    if report_payload.get("valid") is not True:
        raise ValueError(f"{report_label}.valid must be true")
    report_errors = report_payload.get("errors")
    if not isinstance(report_errors, list):
        raise ValueError(f"{report_label}.errors must be a list")
    if report_errors:
        raise ValueError(f"{report_label}.errors must be empty")
    claimed = normalize_content_digest(report_payload.get(digest_field))
    if not claimed:
        raise ValueError(f"{report_label}.{digest_field} is required")
    if claimed != expected_digest:
        raise ValueError(f"{report_label}.{digest_field} does not match artifact bytes")
    _validate_report_lifecycle(report_payload.get("diagnostics"), label=report_label)


def _load_normalized_recap(
    repo_root: Path,
    payload: Mapping[str, Any],
) -> tuple[str, str]:
    source = _manifest_source(payload)
    normalized_recap_path = source.get("normalized_recap_path")
    if not isinstance(normalized_recap_path, str) or not normalized_recap_path.strip():
        raise ValueError("source.normalized_recap_path is required")
    claimed_source_digest = normalize_content_digest(source.get("normalized_recap_sha256"))
    if not claimed_source_digest:
        raise ValueError("source.normalized_recap_sha256 is required")

    artifacts = _manifest_artifacts(payload)
    artifact_recap = artifacts.get(GraphIngestArtifactKind.NORMALIZED_RECAP.value)
    claimed_artifact_digest: str | None = None
    if isinstance(artifact_recap, dict):
        claimed_artifact_digest = normalize_content_digest(artifact_recap.get("sha256"))

    raw, actual_digest = _read_verified_bytes(
        repo_root,
        normalized_recap_path,
        claimed_source_digest,
        label="normalized recap",
    )
    if actual_digest != claimed_source_digest:
        raise ValueError("packaged recap bytes do not match source.normalized_recap_sha256")
    if claimed_artifact_digest and claimed_artifact_digest != actual_digest:
        raise ValueError(
            "packaged recap bytes do not match artifacts.normalized_recap.sha256"
        )
    try:
        recap_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"normalized recap is not valid UTF-8: {exc}") from exc
    return recap_text, actual_digest


def _load_source_span_index(
    repo_root: Path,
    payload: Mapping[str, Any],
    *,
    recap_digest: str,
) -> tuple[SourceSpanIndex, str]:
    source = _manifest_source(payload)
    expected_artifact_id = str(source.get("source_artifact_id") or "").strip()
    if not expected_artifact_id:
        raise ValueError("source.source_artifact_id is required for SourceSpanIndex linkage")

    span_ref = _artifact_ref(
        payload,
        GraphIngestArtifactKind.SOURCE_SPAN_INDEX.value,
        label="source_span_index",
    )
    source_span_uri = source.get("source_span_index_uri")
    if not isinstance(source_span_uri, str) or not source_span_uri.strip():
        raise ValueError("source.source_span_index_uri is required")

    artifact_path = _resolve_manifest_uri(repo_root, str(span_ref["uri"]))
    projection_path = _resolve_manifest_uri(repo_root, source_span_uri)
    if not artifact_path.is_file() or not projection_path.is_file():
        raise ValueError("SourceSpanIndex file is missing")
    if artifact_path.resolve() != projection_path.resolve():
        raise ValueError(
            "source.source_span_index_uri must resolve to the same file as "
            "artifacts.source_span_index"
        )

    raw, actual_digest = _read_verified_bytes(
        repo_root,
        str(span_ref["uri"]),
        str(span_ref["sha256"]),
        label="source_span_index",
    )
    try:
        index_payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"SourceSpanIndex is not valid JSON: {exc}") from exc
    if not isinstance(index_payload, dict):
        raise ValueError("SourceSpanIndex payload must be an object")

    index = source_span_index_from_dict(index_payload)
    if normalize_content_digest(index.content_sha256) != recap_digest:
        raise ValueError("SourceSpanIndex.content_sha256 does not match packaged recap bytes")
    validate_source_span_index(
        index,
        source_artifact_id=expected_artifact_id,
        content_sha256=recap_digest,
    )
    return index, actual_digest


def _validate_known_entity_mentions_loaded(
    sidecar_payload: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    index: SourceSpanIndex,
    recap_text: str,
) -> None:
    for key in ("schema", "version", "campaign_id", "session_id"):
        value = sidecar_payload.get(key)
        if key not in sidecar_payload or not isinstance(value, str) or not value.strip():
            raise ValueError(f"known_entity_mentions.{key} is required")
    if "mentions" not in sidecar_payload or not isinstance(
        sidecar_payload.get("mentions"), list
    ):
        raise ValueError("known_entity_mentions.mentions must be a list")
    if "ambiguous_surfaces" not in sidecar_payload or not isinstance(
        sidecar_payload.get("ambiguous_surfaces"), list
    ):
        raise ValueError("known_entity_mentions.ambiguous_surfaces must be a list")

    if sidecar_payload["schema"] != KNOWN_ENTITY_MENTION_SIDECAR_SCHEMA:
        raise ValueError(
            f"known_entity_mentions schema must be {KNOWN_ENTITY_MENTION_SIDECAR_SCHEMA}"
        )
    if sidecar_payload["version"] != KNOWN_ENTITY_MENTION_SIDECAR_VERSION:
        raise ValueError(
            f"known_entity_mentions version must be {KNOWN_ENTITY_MENTION_SIDECAR_VERSION}"
        )

    campaign_id = str(payload.get("campaign_id") or "").strip()
    session_id = str(payload.get("session_id") or "").strip()
    if str(sidecar_payload["campaign_id"]).strip() != campaign_id:
        raise ValueError("known_entity_mentions.campaign_id does not match manifest")
    if str(sidecar_payload["session_id"]).strip() != session_id:
        raise ValueError("known_entity_mentions.session_id does not match manifest")

    try:
        KnownEntityMentionSidecar.from_mapping(sidecar_payload)
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError(f"known_entity_mentions failed schema parse: {exc}") from exc

    spans_by_id = {span.source_span_id: span for span in index.spans}
    for index_row, raw in enumerate(sidecar_payload["mentions"]):
        if not isinstance(raw, Mapping):
            raise ValueError(
                f"known_entity_mentions.mentions[{index_row}] must be an object"
            )
        try:
            mention = KnownEntityMention.from_mapping(raw)
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError(
                f"known_entity_mentions.mentions[{index_row}] invalid: {exc}"
            ) from exc
        span = spans_by_id.get(mention.source_span_ref_id)
        if span is None:
            raise ValueError(
                f"known_entity_mentions.mentions[{index_row}].source_span_ref_id "
                f"is not in SourceSpanIndex: {mention.source_span_ref_id}"
            )
        paragraph = _paragraph_text_for_span(
            recap_text=recap_text,
            start_line=span.start_line,
            end_line=span.end_line,
        )
        if not paragraph:
            raise ValueError(
                f"known_entity_mentions.mentions[{index_row}] span lines are "
                "outside packaged recap bounds"
            )
        if mention.end_offset > len(paragraph):
            raise ValueError(
                f"known_entity_mentions.mentions[{index_row}] offsets exceed "
                "paragraph length"
            )
        slice_text = paragraph[mention.start_offset : mention.end_offset]
        if slice_text != mention.surface_text:
            raise ValueError(
                f"known_entity_mentions.mentions[{index_row}].surface_text does "
                "not match packaged recap at offsets"
            )


def _load_known_entity_mentions(
    repo_root: Path,
    payload: Mapping[str, Any],
    *,
    index: SourceSpanIndex,
    recap_text: str,
) -> tuple[dict[str, Any] | None, str | None]:
    if not known_entity_mentions_artifact_declared(payload):
        return None, None

    artifact = _artifact_ref(
        payload,
        GraphIngestArtifactKind.KNOWN_ENTITY_MENTIONS.value,
        label="known_entity_mentions",
    )
    raw, actual_digest = _read_verified_bytes(
        repo_root,
        str(artifact["uri"]),
        str(artifact["sha256"]),
        label="known_entity_mentions",
    )
    try:
        sidecar_payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"known_entity_mentions is not valid JSON: {exc}") from exc
    if not isinstance(sidecar_payload, dict):
        raise ValueError("known_entity_mentions payload must be an object")

    _validate_known_entity_mentions_loaded(
        sidecar_payload,
        payload,
        index=index,
        recap_text=recap_text,
    )
    return sidecar_payload, actual_digest


def _validate_candidate_identity(
    candidate_graph: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> None:
    campaign_id = str(payload.get("campaign_id") or "").strip()
    session_id = str(payload.get("session_id") or "").strip()
    source = _manifest_source(payload)
    expected_source_artifact_id = str(source.get("source_artifact_id") or "").strip()

    candidate_campaign = candidate_graph.get("campaign_id")
    if not candidate_campaign or not str(candidate_campaign).strip():
        raise ValueError("candidate_graph.campaign_id is required")
    if str(candidate_campaign).strip() != campaign_id:
        raise ValueError("candidate_graph.campaign_id does not match manifest")

    candidate_session = candidate_graph.get("session_id")
    if not candidate_session or not str(candidate_session).strip():
        raise ValueError("candidate_graph.session_id is required")
    if str(candidate_session).strip() != session_id:
        raise ValueError("candidate_graph.session_id does not match manifest")

    bound_ids = candidate_graph.get("source_artifact_ids")
    if not isinstance(bound_ids, list) or not bound_ids:
        raise ValueError("candidate_graph.source_artifact_ids is required")
    normalized = {str(item).strip() for item in bound_ids if str(item).strip()}
    if not expected_source_artifact_id:
        raise ValueError("source.source_artifact_id is required for candidate identity")
    if expected_source_artifact_id not in normalized:
        raise ValueError(
            f"candidate_graph source_artifact_ids {sorted(normalized)!r} "
            f"missing packaged {expected_source_artifact_id!r}"
        )
    if normalized != {expected_source_artifact_id}:
        raise ValueError(
            f"candidate_graph source_artifact_ids {sorted(normalized)!r} "
            f"must equal exactly {[expected_source_artifact_id]!r}"
        )

    diagnostics = candidate_graph.get("diagnostics")
    if isinstance(diagnostics, dict):
        for flag in FORBIDDEN_DIAGNOSTIC_FLAGS:
            if diagnostics.get(flag):
                raise ValueError(f"candidate_graph forbidden lifecycle flag is true: {flag}")


def _load_candidate_graph(
    repo_root: Path,
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    artifact = _artifact_ref(
        payload,
        GraphIngestArtifactKind.CANDIDATE_GRAPH.value,
        label="candidate_graph",
    )
    raw, actual_digest = _read_verified_bytes(
        repo_root,
        str(artifact["uri"]),
        str(artifact["sha256"]),
        label="candidate_graph",
    )
    try:
        candidate_graph = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"candidate_graph is not valid JSON: {exc}") from exc
    if not isinstance(candidate_graph, dict):
        raise ValueError("candidate_graph payload must be an object")
    _validate_candidate_identity(candidate_graph, payload)
    return candidate_graph, actual_digest


def _load_candidate_validation_report(
    repo_root: Path,
    payload: Mapping[str, Any],
    *,
    candidate_digest: str,
    candidate_uri: str,
) -> tuple[dict[str, Any], str]:
    artifact = _artifact_ref(
        payload,
        GraphIngestArtifactKind.CANDIDATE_VALIDATION_REPORT.value,
        label="candidate_validation_report",
    )
    raw, actual_digest = _read_verified_bytes(
        repo_root,
        str(artifact["uri"]),
        str(artifact["sha256"]),
        label="candidate_validation_report",
    )
    try:
        report_payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"candidate_validation_report is not valid JSON: {exc}") from exc
    if not isinstance(report_payload, dict):
        raise ValueError("candidate_validation_report payload must be an object")

    _validate_semantic_validation_report(
        report_payload,
        payload=payload,
        report_label="candidate_validation_report",
        expected_schema=CANDIDATE_VALIDATION_REPORT_SCHEMA,
        expected_version=CANDIDATE_VALIDATION_REPORT_VERSION,
        path_field="candidate_graph_path",
        expected_path=candidate_uri,
        digest_field="candidate_graph_sha256",
        expected_digest=candidate_digest,
    )
    return report_payload, actual_digest


def _is_non_filesystem_uri(uri: str) -> bool:
    """True for scheme URIs (fixture://, https://, …) that are not repo paths."""
    text = str(uri).strip().replace("\\", "/")
    if not text:
        return True
    # Pathlib treats "fixture://…" as a path with a drive-ish quirk on some
    # platforms; scheme presence is the durable signal.
    if "://" in text:
        return True
    return False


def _resolve_repo_contained_path(path: Path, root: Path) -> Path:
    """Reject absolute/escaping paths the same way projection consumers historically did."""
    value = str(path).replace("\\", "/")
    if value.startswith("file:"):
        raise ValueError(f"unsafe repo-contained path: {path}")
    if ".." in Path(value).parts:
        raise ValueError(f"unsafe repo-contained path: {path}")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path is outside repo root: {path}") from exc
    if not resolved.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return resolved


def _assert_store_source_paths_repo_contained(
    store: UnionSupergraphStore,
    *,
    repo_root: Path,
    session_id: str,
) -> None:
    """Fail closed when store source/recap/bundle paths escape the repo root.

    Non-filesystem URIs (e.g. ``fixture://corpus-ref/…``) and worldbuilding
    artifacts are skipped — hub README paths are documentation location only,
    not openable graph sources (including legacy corpus-relative hub URIs).
    """
    root = repo_root.resolve()
    for artifact in store.source_artifacts.values():
        source_domain = getattr(artifact, "source_domain", None)
        uri = getattr(artifact, "uri", None)
        if (
            uri
            and not _is_non_filesystem_uri(str(uri))
            and source_domain != "worldbuilding"
        ):
            _resolve_repo_contained_path(Path(str(uri)), root)
        recap_path = getattr(artifact, "recap_path", None)
        if recap_path and not _is_non_filesystem_uri(str(recap_path)):
            _resolve_repo_contained_path(Path(str(recap_path)), root)
        bundle_uri = getattr(artifact, "ingest_run_bundle_uri", None)
        if not bundle_uri:
            continue
        if _is_non_filesystem_uri(str(bundle_uri)):
            continue
        bundle_path = _resolve_repo_contained_path(Path(str(bundle_uri)), root)
        # Mirror legacy focus-recap markdown loading: probe input_path_record when
        # the focus-session recap artifact has no direct recap_path.
        if (
            getattr(artifact, "source_domain", None) != "recap"
            or getattr(artifact, "session_id", None) != session_id
            or recap_path
        ):
            continue
        try:
            bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            continue
        if not isinstance(bundle_payload, dict):
            continue
        source = bundle_payload.get("source")
        if not isinstance(source, dict):
            continue
        input_path = source.get("input_path_record")
        if input_path:
            _resolve_repo_contained_path(Path(str(input_path)), root)


def _validate_union_store(
    store: UnionSupergraphStore,
    store_payload: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    repo_root: Path,
) -> None:
    campaign_id = str(payload.get("campaign_id") or "").strip()
    session_id = str(payload.get("session_id") or "").strip()
    if store.campaign_id != campaign_id:
        raise ValueError("preview_union_store.campaign_id does not match manifest")
    if store.focus_session_id != session_id:
        raise ValueError("preview_union_store.focus_session_id does not match manifest")

    raw_diagnostics = store_payload.get("diagnostics")
    if not isinstance(raw_diagnostics, dict):
        raise ValueError("preview_union_store.diagnostics must be an object")
    if raw_diagnostics.get("preview_only") is not True:
        raise ValueError("preview_union_store.diagnostics.preview_only must be true")
    for flag in FORBIDDEN_DIAGNOSTIC_FLAGS:
        if raw_diagnostics.get(flag):
            raise ValueError(f"preview_union_store forbidden lifecycle flag is true: {flag}")
    _assert_store_source_paths_repo_contained(
        store, repo_root=repo_root, session_id=session_id
    )


def _load_preview_union_store(
    repo_root: Path,
    payload: Mapping[str, Any],
) -> tuple[UnionSupergraphStore, str]:
    artifact = _artifact_ref(
        payload,
        GraphIngestArtifactKind.PREVIEW_UNION_STORE.value,
        label="preview_union_store",
    )
    raw, actual_digest = _read_verified_bytes(
        repo_root,
        str(artifact["uri"]),
        str(artifact["sha256"]),
        label="preview_union_store",
    )
    try:
        store_payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"preview_union_store is not valid JSON: {exc}") from exc
    if not isinstance(store_payload, dict):
        raise ValueError("preview_union_store payload must be an object")
    store = UnionSupergraphStore.model_validate(store_payload)
    _validate_union_store(store, store_payload, payload, repo_root=repo_root)
    return store, actual_digest


def _load_preview_union_validation_report(
    repo_root: Path,
    payload: Mapping[str, Any],
    *,
    store_digest: str,
    store_uri: str,
    candidate_digest: str,
    candidate_report_digest: str,
) -> tuple[dict[str, Any], str]:
    artifact = _artifact_ref(
        payload,
        GraphIngestArtifactKind.PREVIEW_UNION_VALIDATION_REPORT.value,
        label="preview_union_validation_report",
    )
    raw, actual_digest = _read_verified_bytes(
        repo_root,
        str(artifact["uri"]),
        str(artifact["sha256"]),
        label="preview_union_validation_report",
    )
    try:
        report_payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"preview_union_validation_report is not valid JSON: {exc}"
        ) from exc
    if not isinstance(report_payload, dict):
        raise ValueError("preview_union_validation_report payload must be an object")

    _validate_semantic_validation_report(
        report_payload,
        payload=payload,
        report_label="preview_union_validation_report",
        expected_schema=PREVIEW_UNION_VALIDATION_REPORT_SCHEMA,
        expected_version=PREVIEW_UNION_VALIDATION_REPORT_VERSION,
        path_field="preview_union_store_path",
        expected_path=store_uri,
        digest_field="preview_union_store_sha256",
        expected_digest=store_digest,
    )

    claimed_candidate = normalize_content_digest(report_payload.get("candidate_graph_sha256"))
    if not claimed_candidate:
        raise ValueError("preview_union_validation_report.candidate_graph_sha256 is required")
    if claimed_candidate != candidate_digest:
        raise ValueError(
            "preview_union_validation_report.candidate_graph_sha256 "
            "does not match verified candidate graph bytes"
        )

    claimed_candidate_report = normalize_content_digest(
        report_payload.get("candidate_validation_report_sha256")
    )
    if not claimed_candidate_report:
        raise ValueError(
            "preview_union_validation_report.candidate_validation_report_sha256 is required"
        )
    if claimed_candidate_report != candidate_report_digest:
        raise ValueError(
            "preview_union_validation_report.candidate_validation_report_sha256 "
            "does not match verified candidate validation report bytes"
        )
    return report_payload, actual_digest


def _load_verified_snapshot(
    repo_root: Path,
    manifest_path: Path,
    *,
    allowed_statuses: set[GraphIngestRunStatus],
    session_id: str | None = None,
    authored_overlay_identity: str = "absent",
    include_union: bool,
) -> VerifiedManifestBackedGraphSnapshot:
    manifest_payload, manifest_sha256 = _load_manifest(manifest_path)
    status = _parse_status(manifest_payload)
    if status not in allowed_statuses:
        raise ValueError(
            f"manifest status {status.value!r} is not allowed for this loader; "
            f"expected one of {sorted(s.value for s in allowed_statuses)!r}"
        )
    if session_id is not None:
        assert_requested_session_matches_manifest(manifest_payload, session_id=session_id)

    recap_text, recap_digest = _load_normalized_recap(repo_root, manifest_payload)
    index, index_digest = _load_source_span_index(
        repo_root,
        manifest_payload,
        recap_digest=recap_digest,
    )
    known_entity_mentions, known_entity_digest = _load_known_entity_mentions(
        repo_root,
        manifest_payload,
        index=index,
        recap_text=recap_text,
    )

    candidate_artifact = _artifact_ref(
        manifest_payload,
        GraphIngestArtifactKind.CANDIDATE_GRAPH.value,
        label="candidate_graph",
    )
    candidate_graph, candidate_digest = _load_candidate_graph(repo_root, manifest_payload)
    candidate_report, candidate_report_digest = _load_candidate_validation_report(
        repo_root,
        manifest_payload,
        candidate_digest=candidate_digest,
        candidate_uri=str(candidate_artifact["uri"]),
    )

    preview_union_store = None
    preview_union_store_sha256 = None
    preview_union_validation_report = None
    preview_union_validation_report_sha256 = None

    if include_union:
        store_artifact = _artifact_ref(
            manifest_payload,
            GraphIngestArtifactKind.PREVIEW_UNION_STORE.value,
            label="preview_union_store",
        )
        preview_union_store, preview_union_store_sha256 = _load_preview_union_store(
            repo_root, manifest_payload
        )
        preview_union_validation_report, preview_union_validation_report_sha256 = (
            _load_preview_union_validation_report(
                repo_root,
                manifest_payload,
                store_digest=preview_union_store_sha256,
                store_uri=str(store_artifact["uri"]),
                candidate_digest=candidate_digest,
                candidate_report_digest=candidate_report_digest,
            )
        )

    dependency_contract = ProjectionDependencyContract(
        projection_schema=PROJECTION_SCHEMA,
        projection_contract_version=PROJECTION_CONTRACT_VERSION,
        campaign_id=str(manifest_payload["campaign_id"]),
        session_id=str(manifest_payload["session_id"]),
        normalized_recap_sha256=recap_digest,
        source_span_index_sha256=index_digest,
        known_entity_mentions_sha256=known_entity_digest,
        preview_union_store_sha256=preview_union_store_sha256,
        candidate_graph_sha256=candidate_digest,
        candidate_validation_report_sha256=candidate_report_digest,
        authored_overlay_identity=normalize_authored_overlay_identity(
            authored_overlay_identity
        ),
    )

    return VerifiedManifestBackedGraphSnapshot(
        manifest_payload=manifest_payload,
        manifest_sha256=manifest_sha256,
        campaign_id=str(manifest_payload["campaign_id"]),
        session_id=str(manifest_payload["session_id"]),
        normalized_recap_text=recap_text,
        normalized_recap_sha256=recap_digest,
        source_span_index=index,
        source_span_index_sha256=index_digest,
        known_entity_mentions=known_entity_mentions,
        known_entity_mentions_sha256=known_entity_digest,
        candidate_graph=candidate_graph,
        candidate_graph_sha256=candidate_digest,
        candidate_validation_report=candidate_report,
        candidate_validation_report_sha256=candidate_report_digest,
        preview_union_store=preview_union_store,
        preview_union_store_sha256=preview_union_store_sha256,
        preview_union_validation_report=preview_union_validation_report,
        preview_union_validation_report_sha256=preview_union_validation_report_sha256,
        dependency_contract=dependency_contract,
    )


def load_verified_candidate_ready_snapshot(
    repo_root: Path,
    manifest_path: Path,
) -> VerifiedManifestBackedGraphSnapshot:
    """Load candidate-ready snapshot (union fields None). Status must be in CANDIDATE_READY_STATUSES."""
    return _load_verified_snapshot(
        repo_root,
        manifest_path,
        allowed_statuses=CANDIDATE_READY_STATUSES,
        include_union=False,
    )


def load_verified_projection_ready_snapshot(
    repo_root: Path,
    manifest_path: Path,
    *,
    session_id: str,
    authored_overlay_identity: str = "absent",
) -> VerifiedManifestBackedGraphSnapshot:
    """Load projection-ready snapshot including union store. Status must be PREVIEW_UNION_STORE_READY or READY_FOR_PROJECTION."""
    return _load_verified_snapshot(
        repo_root,
        manifest_path,
        allowed_statuses=PROJECTION_READY_STATUSES,
        session_id=session_id,
        authored_overlay_identity=authored_overlay_identity,
        include_union=True,
    )


def build_projection_dependency_contract_from_snapshot(
    snapshot: VerifiedManifestBackedGraphSnapshot,
    *,
    authored_overlay_identity: str = "absent",
) -> ProjectionDependencyContract:
    overlay_identity = normalize_authored_overlay_identity(authored_overlay_identity)
    return ProjectionDependencyContract(
        projection_schema=PROJECTION_SCHEMA,
        projection_contract_version=PROJECTION_CONTRACT_VERSION,
        campaign_id=snapshot.campaign_id,
        session_id=snapshot.session_id,
        normalized_recap_sha256=snapshot.normalized_recap_sha256,
        source_span_index_sha256=snapshot.source_span_index_sha256,
        known_entity_mentions_sha256=snapshot.known_entity_mentions_sha256,
        preview_union_store_sha256=snapshot.preview_union_store_sha256,
        candidate_graph_sha256=snapshot.candidate_graph_sha256,
        candidate_validation_report_sha256=snapshot.candidate_validation_report_sha256,
        authored_overlay_identity=overlay_identity,
    )


def load_reusable_projection_from_snapshot(
    snapshot: VerifiedManifestBackedGraphSnapshot,
    repo_root: Path,
) -> dict[str, Any] | None:
    """Return cached projection JSON when artifact bytes and dependency contract match."""
    payload = snapshot.manifest_payload
    artifacts = _manifest_artifacts(payload)
    artifact = artifacts.get(GraphIngestArtifactKind.PROJECTION_PAYLOAD.value)
    if not isinstance(artifact, dict):
        return None

    uri = artifact.get("uri")
    claimed = artifact.get("sha256")
    if not isinstance(uri, str) or not uri.strip():
        return None
    if not isinstance(claimed, str) or not claimed.strip():
        return None

    try:
        raw, _actual = _read_verified_bytes(
            repo_root,
            uri,
            claimed,
            label="projection_payload",
        )
    except ValueError:
        return None

    try:
        projection_payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(projection_payload, dict):
        return None

    if str(projection_payload.get("campaign_id") or "").strip() != snapshot.campaign_id:
        return None
    if str(projection_payload.get("session_id") or "").strip() != snapshot.session_id:
        return None

    stored_deps = artifact.get("depends_on")
    if not isinstance(stored_deps, Mapping):
        stored_deps = projection_payload.get("projection_depends_on")
    if not isinstance(stored_deps, Mapping):
        return None

    try:
        stored_contract = ProjectionDependencyContract.from_mapping(stored_deps)
    except ValueError:
        return None

    if not projection_dependency_contracts_match(
        stored_contract, snapshot.dependency_contract
    ):
        return None

    if snapshot.known_entity_mentions_sha256 is None:
        if projection_payload.get("known_entity_mentions_contract") is True:
            return None
    else:
        if projection_payload.get("known_entity_mentions_contract") is not True:
            return None
        if (
            normalize_content_digest(projection_payload.get("known_entity_mentions_sha256"))
            != snapshot.known_entity_mentions_sha256
        ):
            return None

    return projection_payload
