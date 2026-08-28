"""DungeonMind production adapter for the World Graph authority port (D.2A).

Owns database URL resolution, repository construction, and mapping between
Buddy contribution values and DungeonMind governed publication. Product
services must not import this module's PostgreSQL types.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import copy as shallow_copy
from typing import Any

from graph_memory.world_graph_mutation_context import wire_kind

from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    WorldGraphWriteError,
    _assert_publication_replay_identity,
    _direct_services,
    _prove_existing_publication_matches_request,
    _receipt_ids_from_reviewed_contribution,
    _require_database_url,
    derive_authority_review_operation_id,
    load_authority_mutation_context,
    publish_contribution_via_dungeonmind,
)
from apps.live_control_server.ports.world_graph_authority import (
    AuthorityEvidenceRef,
    AuthorityObject,
    AuthorityRelationship,
    WorldGraphAuthorityError,
    WorldGraphExpectedChildFacts,
    WorldGraphHead,
    WorldGraphPublicationReceipt,
    WorldGraphPublishRequest,
    WorldGraphRevisionView,
    WorldGraphVerificationResult,
)

_WRITE_TO_PORT = {
    "authority_unavailable": "authority_unavailable",
    "authority_head_missing": "authority_unavailable",
    "authority_receipt_missing": "authority_unavailable",
    "authority_integrity": "integrity_failure",
    "revision_not_bridged": "revision_unavailable",
    "governed_write_stale_parent": "stale_parent",
    "governed_write_inexpressible": "inexpressible",
    "governed_write_materialization_failed": "inexpressible",
    "governed_write_legacy_package": "inexpressible",
    "governed_write_idempotency_conflict": "integrity_failure",
    "governed_write_failed": "publication_failed",
    "invalid_request": "inexpressible",
}

_MECHANICS_KINDS = frozenset({"external_resource"})
_MECHANICS_PREDICATES = frozenset({"uses_statblock"})
_MECHANICS_VALUE_KEYS = frozenset({"threat_statblock_binding", "statblock_binding"})


def _raise_port(exc: WorldGraphWriteError) -> None:
    raise WorldGraphAuthorityError(
        str(exc),
        code=_WRITE_TO_PORT.get(exc.code, "publication_failed"),  # type: ignore[arg-type]
        details=dict(exc.details),
    ) from exc


def _alias_values(raw: Any) -> tuple[str, ...]:
    if not raw:
        return ()
    values: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            values.append(item)
        elif isinstance(item, dict):
            text = str(item.get("value") or item.get("alias") or "").strip()
            if text:
                values.append(text)
    return tuple(values)


def _object_from_payload(raw: Mapping[str, Any]) -> AuthorityObject | None:
    object_id = str(raw.get("object_id") or "").strip()
    if not object_id:
        return None
    kind = wire_kind(str(raw.get("kind") or ""))
    meta = raw.get("assertion_metadata") or raw.get("existence_assertion_metadata") or {}
    campaign_scope = None
    if isinstance(meta, dict):
        campaign_scope = meta.get("campaign_scope")
        if campaign_scope is not None:
            campaign_scope = str(campaign_scope)
    external = None
    property_terms: list[str] = []
    for prop in raw.get("properties") or []:
        if not isinstance(prop, dict):
            continue
        term = str(prop.get("property_term") or prop.get("predicate") or "")
        if term.strip():
            property_terms.append(term)
        if term.rsplit(":", 1)[-1] == "external_resource":
            value = prop.get("value")
            if isinstance(value, dict):
                external = value
    return AuthorityObject(
        object_id=object_id,
        label=str(raw.get("label") or ""),
        kind=kind,
        role=kind,
        aliases=_alias_values(raw.get("aliases")),
        source_domains=(),
        campaign_scope=campaign_scope,
        summary=str(raw.get("summary") or "") or None,
        external_resource=external,
        property_terms=tuple(property_terms),
    )


def _relationship_from_payload(raw: Mapping[str, Any]) -> AuthorityRelationship | None:
    relationship_id = str(raw.get("relationship_id") or "").strip()
    subject = str(raw.get("source_object_id") or raw.get("subject_object_id") or "").strip()
    target = str(raw.get("target_object_id") or raw.get("object_object_id") or "").strip()
    predicate = wire_kind(str(raw.get("predicate") or ""))
    if not relationship_id or not subject or not target or not predicate:
        return None
    return AuthorityRelationship(
        relationship_id=relationship_id,
        subject_object_id=subject,
        target_object_id=target,
        predicate=predicate,
        direction="outbound",
        source_domains=(),
        threat_statblock_binding=None,
    )


def _evidence_from_payload(raw: Mapping[str, Any]) -> AuthorityEvidenceRef | None:
    evidence_ref_id = str(raw.get("evidence_ref_id") or "").strip()
    if not evidence_ref_id:
        return None
    role = raw.get("evidence_role")
    if role is not None and not isinstance(role, str):
        role = str(getattr(role, "value", role) or "")
    locator = raw.get("locator")
    return AuthorityEvidenceRef(
        evidence_ref_id=evidence_ref_id,
        evidence_role=str(role or "").strip(),
        locator=str(locator).strip() if locator else None,
    )


def _view_from_stored(*, world_id: str, stored: Any) -> WorldGraphRevisionView:
    payload = dict(getattr(stored, "graph_payload", None) or {})
    envelope = getattr(stored, "revision", None)
    revision_id = str(getattr(envelope, "revision_id", "") or "")
    parent_revision_id = getattr(envelope, "parent_revision_id", None)
    objects: dict[str, AuthorityObject] = {}
    for raw in list(payload.get("objects") or []):
        if not isinstance(raw, dict):
            continue
        obj = _object_from_payload(raw)
        if obj is not None:
            objects[obj.object_id] = obj
    relationships: dict[str, AuthorityRelationship] = {}
    for raw in list(payload.get("relationships") or []):
        if not isinstance(raw, dict):
            continue
        rel = _relationship_from_payload(raw)
        if rel is not None:
            relationships[rel.relationship_id] = rel
    evidence_refs: dict[str, AuthorityEvidenceRef] = {}
    for raw in list(payload.get("evidence_refs") or []):
        if not isinstance(raw, dict):
            continue
        evidence = _evidence_from_payload(raw)
        if evidence is not None:
            evidence_refs[evidence.evidence_ref_id] = evidence
    return WorldGraphRevisionView(
        world_id=world_id,
        revision_id=revision_id,
        parent_revision_id=str(parent_revision_id) if parent_revision_id else None,
        objects=objects,
        relationships=relationships,
        evidence_refs=evidence_refs,
    )


def _assertion_value(assertion: Any) -> dict[str, Any]:
    value = getattr(assertion, "value", None) or {}
    if isinstance(value, str):
        import json

        try:
            parsed = json.loads(value)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return dict(value) if isinstance(value, dict) else {}


def _is_mechanics_assertion(assertion: Any) -> bool:
    kind = str(_assertion_value(assertion).get("kind") or "")
    if wire_kind(kind) in _MECHANICS_KINDS:
        return True
    predicate = str(getattr(assertion, "predicate", None) or "")
    if predicate.rsplit(":", 1)[-1] in _MECHANICS_PREDICATES:
        return True
    value = _assertion_value(assertion)
    return any(key in value for key in _MECHANICS_VALUE_KEYS)


def _world_graph_expressible(contribution: Any) -> Any:
    accepted = [
        item
        for item in list(getattr(contribution, "accepted_assertions", None) or [])
        if not _is_mechanics_assertion(item)
    ]
    model_copy = getattr(contribution, "model_copy", None)
    if callable(model_copy):
        return model_copy(update={"accepted_assertions": accepted})
    try:
        cloned = shallow_copy(contribution)
        cloned.accepted_assertions = accepted
        return cloned
    except Exception:
        return contribution


_WORLDBUILDING_IDENTITY_OUTCOMES = {
    "created_new": "created_new",
    "human_override": "resolved_existing",
    "resolved_existing": "resolved_existing",
    "rejected_by_operator": "rejected",
    "rejected": "rejected",
    "accepted_by_operator": None,
    "deferred_by_operator": None,
    "": None,
}


def _remap_worldbuilding_identity_outcome(assertion: Any) -> Any:
    raw = str(getattr(assertion, "identity_resolution_outcome", "") or "")
    if raw not in _WORLDBUILDING_IDENTITY_OUTCOMES:
        raise WorldGraphAuthorityError(
            "worldbuilding assertion identity outcome cannot be expressed in DungeonMind",
            code="inexpressible",
            details={"identity_resolution_outcome": raw},
        )
    mapped = _WORLDBUILDING_IDENTITY_OUTCOMES[raw]
    if mapped == (raw or None):
        return assertion
    model_copy = getattr(assertion, "model_copy", None)
    if callable(model_copy):
        return model_copy(update={"identity_resolution_outcome": mapped})
    cloned = shallow_copy(assertion)
    cloned.identity_resolution_outcome = mapped
    return cloned


def _worldbuilding_expressible(contribution: Any) -> Any:
    """Map worldbuilding identity vocabulary onto DungeonMind without dropping facts."""
    updates = {}
    for field in (
        "accepted_assertions",
        "rejected_assertions",
        "candidate_assertions",
    ):
        items = list(getattr(contribution, field, None) or [])
        if items:
            updates[field] = [_remap_worldbuilding_identity_outcome(item) for item in items]
    if not updates:
        return contribution
    model_copy = getattr(contribution, "model_copy", None)
    if callable(model_copy):
        return model_copy(update=updates)
    cloned = shallow_copy(contribution)
    for field, value in updates.items():
        setattr(cloned, field, value)
    return cloned


class DungeonMindWorldGraphAuthorityAdapter:
    """Production World Graph authority. PostgreSQL stays inside this class."""

    def __init__(self, *, database_url: str | None = None) -> None:
        self._database_url = database_url

    def _services(self, world_id: str) -> Any:
        try:
            dsn = _require_database_url(self._database_url)
            return _direct_services(dsn, world_id)
        except WorldGraphWriteError as exc:
            _raise_port(exc)
            raise

    def current_head(self, world_id: str) -> WorldGraphHead:
        services = self._services(world_id)
        try:
            head = services.bundle.world_graph.get_head(world_id)
        except Exception as exc:
            raise WorldGraphAuthorityError(
                "DungeonMind authority is unavailable",
                code="authority_unavailable",
                details={"world_id": world_id, "reason": type(exc).__name__},
            ) from exc
        if head is None or not str(getattr(head, "head_revision_id", "") or "").strip():
            raise WorldGraphAuthorityError(
                "DungeonMind authority has no published head",
                code="revision_unavailable",
                details={"world_id": world_id},
            )
        return WorldGraphHead(world_id=world_id, revision_id=str(head.head_revision_id))

    def read_revision(self, world_id: str, revision_id: str) -> WorldGraphRevisionView:
        services = self._services(world_id)
        try:
            stored = services.bundle.world_graph.get_revision(world_id, revision_id)
        except Exception as exc:
            raise WorldGraphAuthorityError(
                "DungeonMind authority is unavailable",
                code="authority_unavailable",
                details={"world_id": world_id, "reason": type(exc).__name__},
            ) from exc
        if stored is None:
            raise WorldGraphAuthorityError(
                "DungeonMind revision is unavailable",
                code="revision_unavailable",
                details={"world_id": world_id, "revision_id": revision_id},
            )
        return _view_from_stored(world_id=world_id, stored=stored)

    def mutation_context(
        self,
        world_id: str,
        revision_id: str,
        *,
        sealed_identity_snapshot: Mapping[str, Any] | None = None,
    ):
        try:
            return load_authority_mutation_context(
                world_id,
                revision_id,
                sealed_identity_snapshot=sealed_identity_snapshot,
                database_url=self._database_url,
            )
        except WorldGraphWriteError as exc:
            _raise_port(exc)
            raise

    def publish(self, request: WorldGraphPublishRequest) -> WorldGraphPublicationReceipt:
        namespace = request.operation_namespace or "threat"
        if namespace == "threat":
            expressible = _world_graph_expressible(request.contribution)
        elif namespace == "worldbuilding":
            expressible = _worldbuilding_expressible(request.contribution)
        else:
            expressible = request.contribution
        accepted = list(getattr(expressible, "accepted_assertions", None) or [])
        if not accepted:
            raise WorldGraphAuthorityError(
                "contribution has no DungeonMind-representable World Graph facts",
                code="inexpressible",
                details={
                    "world_id": request.world_id,
                    "authority_operation_id": request.authority_operation_id,
                    "decision": request.decision,
                    "operation_namespace": namespace,
                },
            )
        dm_operation_id = derive_authority_review_operation_id(
            world_id=request.world_id,
            authority_operation_id=request.authority_operation_id,
            operation_namespace=namespace,
        )
        try:
            payload = publish_contribution_via_dungeonmind(
                world_id=request.world_id,
                expected_parent_revision_id=request.expected_parent_revision_id,
                operation_id=dm_operation_id,
                actor=request.actor,
                contribution=expressible,
                database_url=self._database_url,
                publication_family=namespace,
            )
        except WorldGraphWriteError as exc:
            _raise_port(exc)
            raise
        return WorldGraphPublicationReceipt(
            world_id=str(payload["world_id"]),
            authority_operation_id=request.authority_operation_id,
            parent_revision_id=str(payload["parent_revision_id"]),
            published_revision_id=str(payload["committed_revision_id"]),
            reviewed_contribution_id=str(payload["contribution_id"]),
            accepted_assertion_ids=tuple(payload.get("accepted_assertion_ids") or ()),
            published=True,
            outcome="published" if payload.get("outcome") == "published" else "already_applied",
            reviewed_contribution_sha256=payload.get("reviewed_contribution_sha256"),
        )

    def recover(
        self,
        world_id: str,
        authority_operation_id: str,
        *,
        expected_parent_revision_id: str | None = None,
        contribution: Any | None = None,
        actor: str | None = None,
        operation_namespace: str = "threat",
    ) -> WorldGraphPublicationReceipt | None:
        services = self._services(world_id)
        dm_operation_id = derive_authority_review_operation_id(
            world_id=world_id,
            authority_operation_id=authority_operation_id,
            operation_namespace=operation_namespace or "threat",
        )
        try:
            existing = services.bundle.finalized_review_publications.get(
                world_id, dm_operation_id
            )
        except Exception as exc:
            raise WorldGraphAuthorityError(
                "DungeonMind authority is unavailable",
                code="authority_unavailable",
                details={"world_id": world_id, "reason": type(exc).__name__},
            ) from exc
        if existing is None:
            return None
        if expected_parent_revision_id is not None and contribution is not None and actor:
            replay_contribution = contribution
            if (operation_namespace or "threat") == "threat":
                replay_contribution = _world_graph_expressible(contribution)
            elif (operation_namespace or "threat") == "worldbuilding":
                replay_contribution = _worldbuilding_expressible(contribution)
            try:
                _prove_existing_publication_matches_request(
                    bundle=services.bundle,
                    existing=existing,
                    world_id=world_id,
                    expected_parent_revision_id=expected_parent_revision_id,
                    operation_id=dm_operation_id,
                    actor=actor,
                    contribution=replay_contribution,
                    publication_family=operation_namespace or "threat",
                )
            except WorldGraphWriteError as exc:
                _raise_port(exc)
                raise
        elif expected_parent_revision_id is not None:
            try:
                _assert_publication_replay_identity(
                    existing=existing,
                    expected_parent_revision_id=expected_parent_revision_id,
                )
            except WorldGraphWriteError as exc:
                _raise_port(exc)
                raise
        try:
            accepted_ids, _affected = _receipt_ids_from_reviewed_contribution(
                bundle=services.bundle,
                world_id=world_id,
                publication=existing,
            )
        except WorldGraphWriteError as exc:
            _raise_port(exc)
            raise
        return WorldGraphPublicationReceipt(
            world_id=world_id,
            authority_operation_id=authority_operation_id,
            parent_revision_id=str(existing.expected_parent_revision_id),
            published_revision_id=str(existing.published_revision_id),
            reviewed_contribution_id=str(existing.reviewed_contribution_id),
            accepted_assertion_ids=tuple(accepted_ids),
            published=True,
            outcome="already_applied",
            reviewed_contribution_sha256=getattr(
                existing, "reviewed_contribution_sha256", None
            ),
        )

    def verify_child(
        self,
        *,
        receipt: WorldGraphPublicationReceipt,
        expected: WorldGraphExpectedChildFacts,
    ) -> WorldGraphVerificationResult:
        codes: list[str] = []
        child = self.read_revision(receipt.world_id, receipt.published_revision_id)
        if (
            child.parent_revision_id
            and child.parent_revision_id != receipt.parent_revision_id
        ):
            codes.append("child_parent_mismatch")
        threat = child.objects.get(expected.threat_node_id)
        if threat is None:
            codes.append("missing_threat_object")
        elif expected.expected_object_kind:
            actual_kind = wire_kind(threat.kind).casefold()
            if actual_kind != expected.expected_object_kind.casefold():
                codes.append("threat_kind_mismatch")
        # Resource/binding are accepted-mechanics facts (R.3 field class D /
        # DungeonMind v6 mechanics screen), not World Graph authored material.
        # Native verification therefore proves the Threat object, not
        # resource/binding payloads. File-mode still verifies those on the
        # Buddy graph. Owning compatibility evidence is proposal construction
        # from accepted-mechanics plus exact-parent preflight if those facts
        # appear on a revision view.
        status = "failed" if codes else "passed"
        return WorldGraphVerificationResult(status=status, codes=tuple(codes))
