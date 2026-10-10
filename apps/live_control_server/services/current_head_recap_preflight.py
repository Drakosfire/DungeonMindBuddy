"""Read-only planning preflight for the accepted current-corpus recap cohort.

This module reports source identity and graph-evidence observations at one
observed World head. It never prepares or confirms Candidate Graph Admission,
and it is not proof of admission, semantic correctness, or corpus completeness.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

ACCEPTED_MANIFEST_SCHEMA = "dmb_current_corpus_admission_manifest_v1"
ACCEPTED_MANIFEST_COUNT = 44
ACCEPTED_MANIFEST_DIGEST = (
    "d21477c395f7093540491ca17c109a83bdf7e8a4e9f04517f5ef91f5d3d30e5c"
)
DEFAULT_ACCEPTED_ARTIFACT_ROOT = Path(
    "out/graph_memory/current_corpus_admission_acceptance_v1/"
    "execute-2026-09-16T020204Z-6e3b812a"
)
DEFAULT_WORLD_ID = "eldyrwild"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PreflightInputError(ValueError):
    """The accepted manifest or its source ledger is not the pinned cohort."""


@dataclass(frozen=True)
class ExpectedSource:
    ordinal: int
    campaign_id: str
    session_id: str
    session: int
    source_artifact_id: str
    source_revision_id: str
    content_sha256: str
    original_path: str
    normalized_sha256: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.campaign_id, self.session_id)


@dataclass(frozen=True)
class NativeSource:
    source_artifact_id: str
    source_revision_id: str
    content_sha256: str | None
    campaign_id: str | None = None
    session_id: str | None = None
    source_domain: str | None = None


@dataclass(frozen=True)
class GraphEvidence:
    source_artifact_id: str
    source_revision_id: str
    evidence_ref_id: str
    anchor_id: str
    graph_revision: str


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_accepted_sources(
    manifest_path: Path,
    ledger_path: Path,
    *,
    expected_count: int = ACCEPTED_MANIFEST_COUNT,
    expected_digest: str = ACCEPTED_MANIFEST_DIGEST,
) -> tuple[ExpectedSource, ...]:
    """Load only the frozen source identities; candidate JSON is not read."""

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PreflightInputError("accepted manifest or ledger is unavailable") from exc

    schema = str(manifest.get("schema") or "")
    entries = list(manifest.get("entries") or [])
    if schema != ACCEPTED_MANIFEST_SCHEMA:
        raise PreflightInputError("accepted manifest schema mismatch")
    if (
        int(manifest.get("count") or 0) != expected_count
        or len(entries) != expected_count
    ):
        raise PreflightInputError("accepted manifest count mismatch")

    manifest_rows: list[dict[str, Any]] = []
    required = (
        "ordinal",
        "campaign_id",
        "campaign_number",
        "session",
        "session_id",
        "normalized_path",
        "normalized_sha256",
        "original_path",
        "original_sha256",
        "source_artifact_id",
    )
    for raw in entries:
        if not isinstance(raw, Mapping) or any(key not in raw for key in required):
            raise PreflightInputError("accepted manifest entry is incomplete")
        manifest_rows.append({key: raw[key] for key in required})
    computed_digest = _canonical_sha256({"schema": schema, "entries": manifest_rows})
    if manifest.get("digest") != expected_digest or computed_digest != expected_digest:
        raise PreflightInputError("accepted manifest digest mismatch")
    if [row["ordinal"] for row in manifest_rows] != list(range(1, expected_count + 1)):
        raise PreflightInputError("accepted manifest order is not canonical")

    sessions = list(ledger.get("sessions") or [])
    if len(sessions) != expected_count:
        raise PreflightInputError("accepted session ledger count mismatch")

    expected: list[ExpectedSource] = []
    seen: set[tuple[str, str]] = set()
    for row, source in zip(manifest_rows, sessions, strict=True):
        if not isinstance(source, Mapping):
            raise PreflightInputError("accepted session ledger row is malformed")
        campaign_id = str(row["campaign_id"])
        session_id = str(row["session_id"])
        key = (campaign_id, session_id)
        if key in seen:
            raise PreflightInputError("accepted manifest contains duplicate sessions")
        seen.add(key)
        if (
            source.get("ordinal") != row["ordinal"]
            or source.get("campaign_id") != campaign_id
            or source.get("session_id") != session_id
            or source.get("source_artifact_id") != row["source_artifact_id"]
            or source.get("original_path") != row["original_path"]
            or source.get("original_sha256") != row["original_sha256"]
            or source.get("normalized_sha256") != row["normalized_sha256"]
        ):
            raise PreflightInputError("accepted ledger disagrees with manifest")
        original_sha = str(row["original_sha256"])
        normalized_sha = str(row["normalized_sha256"])
        source_revision_id = str(source.get("source_revision_id") or "")
        if not _SHA256_RE.fullmatch(original_sha) or not _SHA256_RE.fullmatch(
            normalized_sha
        ):
            raise PreflightInputError("accepted manifest contains an invalid digest")
        if source_revision_id != f"sha256:{original_sha}":
            raise PreflightInputError("accepted native source revision is not exact")
        expected.append(
            ExpectedSource(
                ordinal=int(row["ordinal"]),
                campaign_id=campaign_id,
                session_id=session_id,
                session=int(row["session"]),
                source_artifact_id=str(row["source_artifact_id"]),
                source_revision_id=source_revision_id,
                content_sha256=original_sha,
                original_path=str(row["original_path"]),
                normalized_sha256=normalized_sha,
            )
        )

    if any(
        source.campaign_id == "longmont-c2" and source.session == 29
        for source in expected
    ):
        raise PreflightInputError("Session 29 is outside the accepted 44-source cohort")
    return tuple(expected)


def _source_identity(source: NativeSource) -> dict[str, Any]:
    return asdict(source)


def _classify_source(
    expected: ExpectedSource,
    native_sources: Sequence[NativeSource],
    graph_evidence: Sequence[GraphEvidence],
    *,
    pinned_head: str,
    graph_index_complete: bool,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pair_rows = [
        source
        for source in native_sources
        if source.source_artifact_id == expected.source_artifact_id
        and source.source_revision_id == expected.source_revision_id
    ]
    exact_identity = [
        source
        for source in pair_rows
        if source.content_sha256 == expected.content_sha256
    ]
    conflicting_pair = [
        source
        for source in pair_rows
        if source.content_sha256 != expected.content_sha256
    ]
    nearby = [
        source
        for source in native_sources
        if source.campaign_id == expected.campaign_id
        and source.session_id == expected.session_id
    ]
    observed_evidence = [
        item
        for item in graph_evidence
        if item.source_artifact_id == expected.source_artifact_id
        and item.source_revision_id == expected.source_revision_id
    ]
    evidence_at_head = [
        item for item in observed_evidence if item.graph_revision == pinned_head
    ]
    observed_evidence_payload = [asdict(item) for item in observed_evidence]
    pinned_evidence_payload = [asdict(item) for item in evidence_at_head]

    if conflicting_pair:
        return (
            "digest_conflict",
            [_source_identity(row) for row in nearby],
            observed_evidence_payload,
            pinned_evidence_payload,
        )
    if not pair_rows:
        return (
            "missing_source_pair",
            [_source_identity(row) for row in nearby],
            observed_evidence_payload,
            pinned_evidence_payload,
        )
    if not exact_identity:
        return (
            "digest_conflict",
            [_source_identity(row) for row in nearby],
            observed_evidence_payload,
            pinned_evidence_payload,
        )
    if not graph_index_complete:
        return (
            "graph_evidence_unavailable",
            [_source_identity(row) for row in nearby],
            observed_evidence_payload,
            pinned_evidence_payload,
        )
    if not evidence_at_head:
        return (
            "graph_evidence_absent",
            [_source_identity(row) for row in nearby],
            observed_evidence_payload,
            pinned_evidence_payload,
        )
    return (
        "exact_match",
        [_source_identity(row) for row in nearby],
        observed_evidence_payload,
        pinned_evidence_payload,
    )


_NEXT_ACTION = {
    "exact_match": "review exact source and graph evidence tuple; no admission implied",
    "missing_source_pair": "locate the exact native artifact/revision pair; do not substitute another session artifact",
    "digest_conflict": "resolve the exact artifact/revision digest conflict without overwriting source bytes",
    "graph_evidence_absent": "inspect evidence binding at the pinned head before proposing any admission",
    "parent_head_drift": "discard this plan and rerun against a newly observed head",
    "graph_evidence_unavailable": "obtain a complete pinned-head evidence index before review",
    "authority_unavailable": "identify and authorize a read-only native authority before review",
}


def build_preflight_plan(
    expected_sources: Sequence[ExpectedSource],
    *,
    world_id: str,
    manifest_digest: str,
    pinned_head: str | None,
    head_after: str | None,
    native_sources: Sequence[NativeSource] = (),
    graph_evidence: Sequence[GraphEvidence] = (),
    source_inventory_complete: bool = True,
    graph_index_complete: bool = True,
    authority_error: str | None = None,
) -> dict[str, Any]:
    """Build a review plan from read observations, never an admission decision."""

    head_drift = bool(pinned_head and head_after and pinned_head != head_after)
    rows: list[dict[str, Any]] = []
    for expected in expected_sources:
        if (
            authority_error
            or not pinned_head
            or not head_after
            or not source_inventory_complete
        ):
            observation = "authority_unavailable"
            nearby: list[dict[str, Any]] = []
            observed_evidence_payload: list[dict[str, Any]] = []
            pinned_evidence_payload: list[dict[str, Any]] = []
        else:
            (
                observation,
                nearby,
                observed_evidence_payload,
                pinned_evidence_payload,
            ) = _classify_source(
                expected,
                native_sources,
                graph_evidence,
                pinned_head=pinned_head,
                graph_index_complete=graph_index_complete,
            )
        disposition = "parent_head_drift" if head_drift else observation
        rows.append(
            {
                "ordinal": expected.ordinal,
                "campaign_id": expected.campaign_id,
                "session_id": expected.session_id,
                "source": {
                    "path": expected.original_path,
                    "source_artifact_id": expected.source_artifact_id,
                    "source_revision_id": expected.source_revision_id,
                    "content_sha256": expected.content_sha256,
                    "normalized_sha256": expected.normalized_sha256,
                },
                "pinned_head_disposition": observation,
                "disposition": disposition,
                "observed_native_sources": nearby,
                "observed_graph_evidence": observed_evidence_payload,
                "pinned_graph_evidence": pinned_evidence_payload,
                "next_action": _NEXT_ACTION[disposition],
                "mutation_proposed": False,
            }
        )
    return {
        "schema": "dmb_current_head_recap_preflight_v1",
        "world_id": world_id,
        "manifest": {
            "schema": ACCEPTED_MANIFEST_SCHEMA,
            "count": len(expected_sources),
            "digest": manifest_digest,
            "session_29_included": any(
                row.campaign_id == "longmont-c2" and row.session == 29
                for row in expected_sources
            ),
        },
        "pinned_head": pinned_head,
        "head_after_reads": head_after,
        "head_drift": head_drift,
        "status": "review_required",
        "authority_error": authority_error,
        "source_inventory_complete": source_inventory_complete,
        "graph_index_complete": graph_index_complete,
        "planning_only": True,
        "admission_proof": False,
        "completeness_proof": False,
        "writes_performed": False,
        "review_plan": {
            "requires_human_review": True,
            "automatic_mutations": [],
            "actions": [
                {
                    "ordinal": row["ordinal"],
                    "disposition": row["disposition"],
                    "action": row["next_action"],
                }
                for row in rows
            ],
        },
        "sources": rows,
    }


def _native_source_inventory(bundle: Any, world_id: str) -> tuple[NativeSource, ...]:
    sources = bundle.sources
    list_artifacts = getattr(sources, "list_artifacts_for_world", None)
    list_revisions = getattr(sources, "list_revisions", None)
    if not callable(list_artifacts) or not callable(list_revisions):
        raise RuntimeError("source_inventory_unavailable")
    rows: list[NativeSource] = []
    for artifact in list_artifacts(world_id):
        domain = getattr(artifact, "source_domain", None)
        domain_key = getattr(artifact, "source_domain_key", None)
        if domain is not None and hasattr(domain, "value"):
            source_domain = str(domain.value)
        else:
            source_domain = str(domain_key or domain or "").strip() or None
        for revision in list_revisions(artifact.source_artifact_id):
            digest = getattr(revision, "content_sha256", None)
            rows.append(
                NativeSource(
                    source_artifact_id=str(artifact.source_artifact_id),
                    source_revision_id=str(
                        getattr(revision, "source_revision_id", "") or ""
                    ),
                    content_sha256=str(digest).strip().lower() if digest else None,
                    campaign_id=getattr(artifact, "campaign_id", None),
                    session_id=getattr(artifact, "session_id", None),
                    source_domain=source_domain,
                )
            )
    return tuple(rows)


def read_current_head_observations(
    *,
    world_id: str = DEFAULT_WORLD_ID,
) -> tuple[str, str, tuple[NativeSource, ...], tuple[GraphEvidence, ...], bool]:
    """Read source inventory and graph anchors under one pinned Buddy read bundle."""

    if world_id != DEFAULT_WORLD_ID:
        raise RuntimeError("world_id_must_be_eldyrwild")

    # These imports stay lazy so pure planner tests do not require a live
    # DungeonMind installation or open a database connection.
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        direct_services_from_bundle,
        list_source_anchor_index_direct_v2,
    )
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase,
        PostgresRepositoryBundle,
    )
    from graph_memory.retrieval.models import WorldGraphSearchRequest

    database_url = config.world_graph_authority_database_url()
    if not database_url:
        raise RuntimeError("authority_unavailable")
    bundle = PostgresRepositoryBundle(PostgresDatabase(database_url))
    services = direct_services_from_bundle(bundle, world_id)
    pinned_head = services.binding.dungeonmind_head_revision_id
    if not pinned_head:
        raise RuntimeError("current_head_unavailable")
    native_sources = _native_source_inventory(bundle, world_id)
    request = WorldGraphSearchRequest.model_validate(
        {
            "schema": "dmb_world_graph_search_request_v1",
            "worldId": world_id,
            "campaignId": "longmont-c2",
            "focus": {"kind": "none", "sessionId": None, "campaignId": None},
            "admissibility": "gm",
            "revisionPin": pinned_head,
            "scopeMode": "world",
            "queryText": "recap-source-preflight",
            "seedNodeIds": [],
            "bounds": {
                "maxNodes": 1,
                "maxRelationships": 1,
                "maxAttributes": 1,
                "maxSourceAnchors": 1,
            },
        }
    )
    index = list_source_anchor_index_direct_v2(
        services, request, revision_id=pinned_head
    )
    if index.status == "complete":
        evidence = tuple(
            GraphEvidence(
                source_artifact_id=pin.source_artifact_id,
                source_revision_id=pin.source_revision_id,
                evidence_ref_id=pin.evidence_ref_id,
                anchor_id=pin.anchor_id,
                graph_revision=pin.graph_revision,
            )
            for pin in index.source_pins
        )
        graph_index_complete = True
    elif index.status == "overflow":
        evidence = ()
        graph_index_complete = False
    else:
        raise RuntimeError("graph_evidence_unavailable")

    current_head = bundle.world_graph.get_head(world_id)
    head_after = str(getattr(current_head, "head_revision_id", "") or "")
    return pinned_head, head_after, native_sources, evidence, graph_index_complete


def run_current_head_preflight(
    *,
    manifest_path: Path = DEFAULT_ACCEPTED_ARTIFACT_ROOT / "manifest.json",
    ledger_path: Path = DEFAULT_ACCEPTED_ARTIFACT_ROOT / "session_ledger.json",
    world_id: str = DEFAULT_WORLD_ID,
) -> dict[str, Any]:
    if world_id != DEFAULT_WORLD_ID:
        raise PreflightInputError("preflight is pinned to the existing Elderwyld World")
    expected = load_accepted_sources(manifest_path, ledger_path)
    try:
        head, head_after, native_sources, graph_evidence, graph_complete = (
            read_current_head_observations(world_id=world_id)
        )
        return build_preflight_plan(
            expected,
            world_id=world_id,
            manifest_digest=ACCEPTED_MANIFEST_DIGEST,
            pinned_head=head,
            head_after=head_after,
            native_sources=native_sources,
            graph_evidence=graph_evidence,
            graph_index_complete=graph_complete,
        )
    except Exception as exc:  # fail closed; do not leak connection/source content
        code = str(getattr(exc, "code", "") or "")
        if not code and isinstance(exc, RuntimeError):
            code = str(exc)
        return build_preflight_plan(
            expected,
            world_id=world_id,
            manifest_digest=ACCEPTED_MANIFEST_DIGEST,
            pinned_head=None,
            head_after=None,
            authority_error=code or "authority_unavailable",
            source_inventory_complete=False,
            graph_index_complete=False,
        )
