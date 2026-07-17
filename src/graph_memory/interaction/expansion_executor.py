"""Bounded retrieval-plan executor over a shared GraphRetrievalSession."""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.live_control_server.services import world_graph_retrieval as retrieval_service
from apps.live_control_server.services.world_graph_retrieval import (
    WorldGraphRetrievalServiceError,
)
from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
from graph_memory.interaction.schema_constants import (
    EXPAND_GRAPH_RETRIEVAL_SCHEMA,
    READ_GRAPH_SOURCE_SCHEMA,
)
from graph_memory.interaction.session import (
    OperationName,
    RetrievalOperationEvent,
    SourceAnchorState,
    SourceReadEntry,
)
from graph_memory.interaction.session_store import get_session, replace_session
from graph_memory.retrieval.models import (
    RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
    RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
    RETRIEVAL_OBJECT_REQUEST_SCHEMA,
    RETRIEVAL_SEARCH_REQUEST_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
    WorldGraphEvidenceRequest,
    WorldGraphEvidenceTarget,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalFocus,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
)

ExpansionOperation = Literal[
    "object",
    "neighborhood",
    "search",
    "support",
]

# Shared cap for search/neighborhood seed lists. object/support allow at most one.
_MAX_EXPAND_TARGETS = 8


class ExpandTarget(BaseModel):
    """Node-only targets until edge/assertion expand semantics exist."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    kind: Literal["node"] = "node"
    id: str = Field(min_length=1)


class ExpandGraphRetrievalRequest(BaseModel):
    """Model-visible expand request.

    Only fields the executor actually honors are admitted. Filtering
    (relationFamilies / claimPredicates) and client-supplied bounds are
    omitted until they have distinct tested semantics.

    Target cardinality (enforced in the executor after session seed resolution):
    - object / support: exactly one effective node
    - neighborhood: 1–8 effective seeds (no silent search fallback)
    - search: 0–8 seed nodes
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["dmb_expand_graph_retrieval_request_v1"] = Field(
        alias="schema",
        default=EXPAND_GRAPH_RETRIEVAL_SCHEMA,
    )
    retrieval_session_id: str = Field(min_length=1, alias="retrievalSessionId")
    operation: ExpansionOperation
    targets: list[ExpandTarget] = Field(
        default_factory=list,
        max_length=_MAX_EXPAND_TARGETS,
    )
    query_text: str | None = Field(default=None, alias="queryText")
    depth: Literal[1, 2] = 1
    historical_revision_id: str | None = Field(
        default=None,
        alias="historicalRevisionId",
    )


class ReadGraphSourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["dmb_read_graph_source_request_v1"] = Field(
        alias="schema",
        default=READ_GRAPH_SOURCE_SCHEMA,
    )
    retrieval_session_id: str = Field(min_length=1, alias="retrievalSessionId")
    anchor_ids: list[str] = Field(
        min_length=1,
        max_length=8,
        alias="anchorIds",
    )
    max_chars: int = Field(default=4000, ge=1, le=12000, alias="maxChars")


_SCOPE_WIRE_KEYS = frozenset(
    {
        "worldId",
        "campaignId",
        "focus",
        "admissibility",
        "revisionPin",
        "world_id",
        "campaign_id",
        "revision_pin",
    }
)


def _normalize_interaction_arguments(arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Prefer camelCase wire keys; drop scope injects expand/read models forbid."""
    payload = {key: value for key, value in dict(arguments).items() if key not in _SCOPE_WIRE_KEYS}
    # Dual inject (alias + field name) is forbidden under extra=forbid once aliased.
    if "retrievalSessionId" in payload and "retrieval_session_id" in payload:
        payload.pop("retrieval_session_id", None)
    if "queryText" in payload and "query_text" in payload:
        payload.pop("query_text", None)
    if "anchorIds" in payload and "anchor_ids" in payload:
        payload.pop("anchor_ids", None)
    if "maxChars" in payload and "max_chars" in payload:
        payload.pop("max_chars", None)
    if "historicalRevisionId" in payload and "historical_revision_id" in payload:
        payload.pop("historical_revision_id", None)
    return payload


def _focus_for_request(focus: Mapping[str, Any]) -> WorldGraphRetrievalFocus:
    kind = str(focus.get("kind") or "none")
    session_id = focus.get("session_id")
    payload: dict[str, Any] = {"kind": kind, "sessionId": session_id}
    return WorldGraphRetrievalFocus.model_validate(payload)


def _request_context_payload(session, focus: WorldGraphRetrievalFocus) -> dict[str, Any]:
    """Alias-only wire payload for PR010A request models (populate_by_name=False)."""
    return {
        "worldId": session.snapshot.world_id,
        "campaignId": session.snapshot.campaign_id,
        "focus": focus.model_dump(mode="json", by_alias=True),
        "admissibility": session.snapshot.admissibility,
        "revisionPin": session.snapshot.revision_id,
    }


def _session_or_raise(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise ValueError(f"unknown retrieval session: {session_id}")
    return session


def _target_node_ids(request: ExpandGraphRetrievalRequest, session) -> list[str]:
    if request.targets:
        # Schema admits node targets only; every target id is a node id.
        return [t.id for t in request.targets]
    selected = session.selected_referent_ids()
    if selected:
        return selected
    return list(session.preflight_candidate_ids)


def _target_cardinality_error(
    *,
    operation: ExpansionOperation,
    requested_count: int,
    effective_ids: list[str],
) -> dict[str, Any] | None:
    """Reject requests whose effective targets would be silently truncated."""
    effective_count = len(effective_ids)
    if operation in {"object", "support"}:
        if requested_count > 1:
            return {
                "schema": "dmb_world_graph_retrieval_error_v1",
                "code": "too_many_targets",
                "message": f"{operation} expansion accepts at most one target node",
                "statusCode": 422,
                "diagnostics": [
                    {
                        "code": "too_many_targets",
                        "message": f"requested {requested_count} targets; {operation} allows 1",
                        "severity": "error",
                    }
                ],
            }
        if effective_count == 0:
            return {
                "schema": "dmb_world_graph_retrieval_error_v1",
                "code": "ambiguous_target",
                "message": f"{operation} expansion requires a target node",
                "statusCode": 422,
                "diagnostics": [],
            }
        if effective_count > 1:
            return {
                "schema": "dmb_world_graph_retrieval_error_v1",
                "code": "ambiguous_target",
                "message": (
                    f"{operation} expansion requires exactly one target node; "
                    f"session resolved {effective_count} seeds"
                ),
                "statusCode": 422,
                "diagnostics": [
                    {
                        "code": "ambiguous_target",
                        "message": f"effective seed count {effective_count} exceeds 1",
                        "severity": "error",
                    }
                ],
            }
        return None

    if operation == "neighborhood":
        if effective_count == 0:
            return {
                "schema": "dmb_world_graph_retrieval_error_v1",
                "code": "ambiguous_target",
                "message": (
                    "neighborhood expansion requires at least one seed node; "
                    "use search when no targets or session seeds are available"
                ),
                "statusCode": 422,
                "diagnostics": [],
            }
        if effective_count > _MAX_EXPAND_TARGETS:
            return {
                "schema": "dmb_world_graph_retrieval_error_v1",
                "code": "too_many_targets",
                "message": (
                    f"neighborhood expansion accepts at most {_MAX_EXPAND_TARGETS} seed nodes"
                ),
                "statusCode": 422,
                "diagnostics": [
                    {
                        "code": "too_many_targets",
                        "message": (
                            f"effective seed count {effective_count} exceeds "
                            f"{_MAX_EXPAND_TARGETS}"
                        ),
                        "severity": "error",
                    }
                ],
            }
        return None

    # search: zero seeds is valid (query-only); more than the cap is not.
    if effective_count > _MAX_EXPAND_TARGETS:
        return {
            "schema": "dmb_world_graph_retrieval_error_v1",
            "code": "too_many_targets",
            "message": f"search expansion accepts at most {_MAX_EXPAND_TARGETS} seed nodes",
            "statusCode": 422,
            "diagnostics": [
                {
                    "code": "too_many_targets",
                    "message": (
                        f"effective seed count {effective_count} exceeds {_MAX_EXPAND_TARGETS}"
                    ),
                    "severity": "error",
                }
            ],
        }
    return None


def _dispatch_expansion(
    *,
    request: ExpandGraphRetrievalRequest,
    session,
    ctx: dict[str, Any],
    focus: WorldGraphRetrievalFocus,
    node_ids: list[str],
    root: Path | None,
):
    del focus  # focus already embedded in ctx
    if request.operation == "object":
        obj_req = WorldGraphObjectRequest.model_validate(
            {
                **ctx,
                "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
                "nodeId": node_ids[0],
            }
        )
        return retrieval_service.get_campaign_object(obj_req, root=root)
    if request.operation == "neighborhood":
        neigh_req = WorldGraphNeighborhoodRequest.model_validate(
            {
                **ctx,
                "schema": RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
                "seedNodeIds": node_ids,
                "maxDepth": request.depth,
            }
        )
        return retrieval_service.get_object_neighborhood(neigh_req, root=root)
    if request.operation == "support":
        evidence_req = WorldGraphEvidenceRequest.model_validate(
            {
                **ctx,
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "target": {"kind": "node", "id": node_ids[0]},
            }
        )
        return retrieval_service.get_object_evidence(evidence_req, root=root)
    search_req = WorldGraphSearchRequest.model_validate(
        {
            **ctx,
            "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
            "queryText": request.query_text or session.question,
            "seedNodeIds": node_ids,
        }
    )
    return retrieval_service.search_campaign_graph(search_req, root=root)


def execute_expand_graph_retrieval(
    arguments: Mapping[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    try:
        request = ExpandGraphRetrievalRequest.model_validate(
            _normalize_interaction_arguments(arguments)
        )
    except ValidationError as exc:
        return {
            "schema": "dmb_world_graph_retrieval_error_v1",
            "code": "invalid_arguments",
            "message": "Invalid expand_graph_retrieval arguments",
            "statusCode": 422,
            "diagnostics": [{"code": "invalid_arguments", "message": str(exc), "severity": "error"}],
        }

    session = _session_or_raise(request.retrieval_session_id)
    if (
        request.historical_revision_id
        and request.historical_revision_id != session.snapshot.revision_id
    ):
        return {
            "schema": "dmb_world_graph_retrieval_error_v1",
            "code": "revision_conflict",
            "message": "Expansion historical revision does not match session revision.",
            "statusCode": 409,
            "diagnostics": [
                {
                    "code": "revision_conflict",
                    "message": "historical_revision_id must equal session revision",
                    "severity": "error",
                }
            ],
        }

    started = time.perf_counter()
    focus = _focus_for_request(session.snapshot.focus)
    ctx = _request_context_payload(session, focus)
    node_ids = _target_node_ids(request, session)
    cardinality_error = _target_cardinality_error(
        operation=request.operation,
        requested_count=len(request.targets),
        effective_ids=node_ids,
    )
    if cardinality_error is not None:
        return {**cardinality_error, "retrievalSessionId": session.id}
    operation: OperationName = request.operation  # type: ignore[assignment]

    try:
        result = _dispatch_expansion(
            request=request,
            session=session,
            ctx=ctx,
            focus=focus,
            node_ids=node_ids,
            root=root,
        )
    except WorldGraphRetrievalServiceError as exc:
        return {
            "schema": "dmb_world_graph_retrieval_error_v1",
            "code": getattr(exc, "code", None) or "world_graph_retrieval_error",
            "message": str(exc),
            "statusCode": getattr(exc, "status_code", None) or 500,
            "diagnostics": [
                {
                    "code": getattr(exc, "code", None) or "world_graph_retrieval_error",
                    "message": str(exc),
                    "severity": "error",
                }
            ],
            "retrievalSessionId": session.id,
        }
    if isinstance(result, dict) and result.get("schema") == "dmb_world_graph_retrieval_error_v1":
        return {**result, "retrievalSessionId": session.id}

    result_dict = result.model_dump(mode="json", by_alias=True)
    new_claims = claims_from_retrieval_result(
        result_dict,
        revision_id=session.snapshot.revision_id,
    )
    added = session.upsert_claims(new_claims)

    for anchor in result_dict.get("sourceAnchors") or []:
        if not isinstance(anchor, Mapping):
            continue
        anchor_id = str(anchor.get("anchorId") or "")
        if not anchor_id:
            continue
        if any(existing.anchor_id == anchor_id for existing in session.source_anchors):
            continue
        session.source_anchors.append(
            SourceAnchorState(
                anchor_id=anchor_id,
                readable=bool(anchor.get("readable") is True),
                opened=False,
                locator_kind=(
                    None if anchor.get("locatorKind") is None else str(anchor.get("locatorKind"))
                ),
                supporting_claim_ids=[
                    str(x)
                    for x in (
                        anchor.get("supportingAssertionIds")
                        or anchor.get("supportingGraphObjectIds")
                        or []
                    )
                ],
            )
        )

    duration_ms = (time.perf_counter() - started) * 1000.0
    status = "completed"
    outcome = str(result_dict.get("outcome") or "")
    if outcome in {"partial", "truncated"}:
        status = "partial"
    elif outcome in {"empty", "denied", "unavailable"}:
        status = "failed"

    session.operations.append(
        RetrievalOperationEvent(
            operation_id=f"op:{uuid.uuid4().hex[:12]}",
            requested_by="hermes",
            operation=operation,
            inputs={
                "targets": [t.model_dump(mode="json") for t in request.targets],
                "effective_targets": [{"kind": "node", "id": nid} for nid in node_ids],
                "query_text": request.query_text,
            },
            status=status,  # type: ignore[arg-type]
            added_claim_ids=added,
            added_anchor_ids=[a.anchor_id for a in session.source_anchors][-16:],
            diagnostic_codes=[
                str(d.get("code"))
                for d in (result_dict.get("diagnostics") or [])
                if isinstance(d, Mapping) and d.get("code")
            ],
            duration_ms=duration_ms,
        )
    )
    replace_session(session)
    return {
        **result_dict,
        "retrievalSessionId": session.id,
        "addedClaimIds": added,
        "claimLedger": [c.model_dump(mode="json", by_alias=True) for c in session.claims],
    }


def execute_read_graph_source(
    arguments: Mapping[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    try:
        request = ReadGraphSourceRequest.model_validate(
            _normalize_interaction_arguments(arguments)
        )
    except ValidationError as exc:
        return {
            "schema": "dmb_world_graph_retrieval_error_v1",
            "code": "invalid_arguments",
            "message": "Invalid read_graph_source arguments",
            "statusCode": 422,
            "diagnostics": [{"code": "invalid_arguments", "message": str(exc), "severity": "error"}],
        }

    session = _session_or_raise(request.retrieval_session_id)
    admitted = {anchor.anchor_id: anchor for anchor in session.source_anchors}
    focus = _focus_for_request(session.snapshot.focus)
    reads: list[dict[str, Any]] = []
    for anchor_id in request.anchor_ids:
        if admitted and anchor_id not in admitted:
            reads.append(
                {
                    "schema": "dmb_world_graph_source_anchor_read_v1",
                    "outcome": "denied",
                    "anchorId": anchor_id,
                    "diagnostics": [
                        {
                            "code": "anchor_not_in_session",
                            "message": "Anchor is not admitted in the retrieval session",
                            "severity": "error",
                        }
                    ],
                }
            )
            continue
        try:
            read_req = WorldGraphSourceAnchorReadRequest.model_validate(
                {
                    **_request_context_payload(session, focus),
                    "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                    "anchorId": anchor_id,
                    "maxChars": request.max_chars,
                }
            )
            result = retrieval_service.read_source_anchor(read_req, root=root)
        except WorldGraphRetrievalServiceError as exc:
            reads.append(
                {
                    "schema": "dmb_world_graph_retrieval_error_v1",
                    "code": getattr(exc, "code", None) or "world_graph_retrieval_error",
                    "message": str(exc),
                    "statusCode": getattr(exc, "status_code", None) or 500,
                    "anchorId": anchor_id,
                    "diagnostics": [
                        {
                            "code": getattr(exc, "code", None)
                            or "world_graph_retrieval_error",
                            "message": str(exc),
                            "severity": "error",
                        }
                    ],
                }
            )
            continue
        result_dict = result.model_dump(mode="json", by_alias=True)
        reads.append(result_dict)
        source_read_id = f"source-read:{uuid.uuid4().hex[:12]}"
        opened = result_dict.get("outcome") in {"enough", "partial", "truncated"} and (
            result_dict.get("content") is not None
        )
        session.source_reads.append(
            SourceReadEntry(
                source_read_id=source_read_id,
                anchor_id=anchor_id,
                outcome=str(result_dict.get("outcome") or "unavailable"),
                content_sha256=(
                    None
                    if result_dict.get("contentSha256") is None
                    else str(result_dict.get("contentSha256"))
                ),
                line_start=result_dict.get("lineStart"),
                line_end=result_dict.get("lineEnd"),
                truncated=bool(result_dict.get("truncated")),
                source_artifact_id=(
                    None
                    if result_dict.get("sourceArtifactId") is None
                    else str(result_dict.get("sourceArtifactId"))
                ),
            )
        )
        for anchor in session.source_anchors:
            if anchor.anchor_id == anchor_id:
                anchor.opened = opened
                if opened:
                    anchor.readable = True
        session.operations.append(
            RetrievalOperationEvent(
                operation_id=f"op:{uuid.uuid4().hex[:12]}",
                requested_by="hermes",
                operation="source_read",
                inputs={"anchor_id": anchor_id},
                status="completed" if opened else "failed",
                added_anchor_ids=[anchor_id],
                diagnostic_codes=[
                    str(d.get("code"))
                    for d in (result_dict.get("diagnostics") or [])
                    if isinstance(d, Mapping) and d.get("code")
                ],
            )
        )

    replace_session(session)
    if len(reads) == 1:
        return {**reads[0], "retrievalSessionId": session.id}
    return {
        "schema": "dmb_read_graph_source_batch_v1",
        "retrievalSessionId": session.id,
        "reads": reads,
    }


__all__ = [
    "ExpandGraphRetrievalRequest",
    "ReadGraphSourceRequest",
    "execute_expand_graph_retrieval",
    "execute_read_graph_source",
]
