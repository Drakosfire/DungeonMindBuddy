"""Existing-world worldbuilding prepare → confirm (CUTOVER D.2B).

Owns the mounted worldbuilding authority boundary. First-world/bootstrap lives
in ``first_world_graph_publication.py``. Product code talks only to
``WorldGraphAuthority``.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import os
import secrets
from dataclasses import asdict, replace
from types import SimpleNamespace
from typing import Any, Mapping

from apps.live_control_server import config as live_config
from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    worldbuilding_authority_operation_id,
)
from apps.live_control_server.models.extract_promote import (
    PRODUCT_CONFIRM_ALLOW_LIVE_WORLD,
    PRODUCT_CONFIRM_DRY_RUN,
    WORLD_BUILDING_WRITE_PLAN_SCHEMA,
    WORLD_BUILDING_WRITE_PLAN_SCHEMA_V1,
    ConfirmAuditStatus,
    WorldbuildingWritePlanConfirmReceipt,
    WorldbuildingWritePlanConfirmRequest,
    WorldbuildingWritePlanPrepareRequest,
    WorldbuildingWritePlanResponse,
    WorldbuildingPublicationBinding,
    WorldbuildingNativeVocabularyBinding,
    WorldbuildingSourceAdmissionBinding,
)
from apps.live_control_server.ports.world_graph_authority import (
    WorldGraphAuthority,
    WorldGraphAuthorityError,
    WorldGraphPublicationReceipt,
    WorldGraphPublishRequest,
)
from apps.live_control_server.ports.world_graph_authority_access import (
    get_world_graph_authority,
)
from apps.live_control_server.services.extract_promote import (
    ExtractPromoteError,
    _diagnostic,
    _load_typed_worldbuilding_preview_for_run,
)
from apps.live_control_server.services.promotable_ingest_run import (
    PromotableIngestRunError,
    resolve_promotable_ingest_run,
)
from graph_memory.worldbuilding_write_plan import (
    WorldbuildingDispositionInput,
    WorldbuildingWritePlanError,
    WorldbuildingWritePlanVerificationContext,
    build_worldbuilding_write_plan,
    materialize_worldbuilding_contribution,
    verify_worldbuilding_write_plan,
)

from apps.live_control_server.services.source_artifact_registry import get_source_artifact, SourceArtifactRegistryError
from apps.live_control_server.services.workspace_document_registry import get_workspace_document, WorkspaceDocumentRegistryError
from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding, WorldGraphProjectionServiceError


def _registered_publication_binding(resolved):
    try:
        return _load_registered_publication_binding(resolved)
    except (SourceArtifactRegistryError, WorkspaceDocumentRegistryError, WorldGraphProjectionServiceError) as exc:
        unavailable = getattr(exc, "status_code", 409) >= 500
        raise ExtractPromoteError(
            "Registered World/source storage is unavailable" if unavailable else "Registered World/source ownership is unavailable",
            code="worldbuilding_source_unavailable" if unavailable else "worldbuilding_source_binding_missing",
            status_code=503 if unavailable else 409,
        ) from exc


def _load_registered_publication_binding(resolved):
    root = live_config.repo_root()
    artifact = get_source_artifact(root, resolved.source_artifact_id)
    if (not artifact.workspace_document_id or not artifact.workspace_document_revision
            or not artifact.world_id or artifact.world_id != resolved.world_id
            or resolved.source_domain != "worldbuilding" or resolved.session_id
            or artifact.content_sha256 != resolved.source_revision_id.removeprefix("sha256:")):
        raise ExtractPromoteError("An exact registered Build source is required",
                                 code="worldbuilding_source_binding_missing", status_code=409)
    document = get_workspace_document(root, artifact.workspace_document_id)
    if (document.kind != "worldbuilding_source" or document.world_id != artifact.world_id
            or document.status != "active"):
        raise ExtractPromoteError("Registered source ownership changed",
                                 code="worldbuilding_source_binding_changed", status_code=409)
    binding = resolve_managed_world_binding(artifact.world_id)
    return WorldbuildingPublicationBinding(
        managed_world_id=binding.managed_world_id, native_world_id=binding.native_world_id,
        binding_version=binding.binding_version, document_id=artifact.workspace_document_id,
        document_revision=artifact.workspace_document_revision,
        source_artifact_id=artifact.source_artifact_id, source_sha256=artifact.content_sha256,
    )


def _world_scoped_preview(preview, binding):
    # Registered Build envelopes carry the managed owner in campaign_id.
    # Compile a native World-scoped view only after registered ownership is proved.
    if preview.campaign_id not in (None, "", binding.managed_world_id):
        raise ExtractPromoteError("Candidate has genuine campaign ownership",
                                 code="worldbuilding_source_binding_changed", status_code=409)
    return replace(preview, campaign_id=None)


def _prepare_source_admission(resolved, binding):
    from apps.live_control_server.ports.world_graph_source_admission import (
        WorldGraphSourceAdmissionRequest, WorldGraphSourceAdmissionError,
    )
    from apps.live_control_server.ports.world_graph_source_admission_access import (
        get_world_graph_source_admission_authority,
    )
    artifact = get_source_artifact(live_config.repo_root(), resolved.source_artifact_id)
    if artifact.campaign_id not in (None, "", binding.managed_world_id):
        raise ExtractPromoteError("Build source has genuine campaign ownership",
                                 code="worldbuilding_source_binding_changed", status_code=409)
    digest = hashlib.sha256(resolved.normalized_recap_path.read_bytes()).hexdigest()
    if digest != binding.source_sha256:
        raise ExtractPromoteError("Frozen source digest changed",
                                 code="worldbuilding_source_binding_changed", status_code=409)
    data = artifact.model_dump()
    data.update(world_id=binding.native_world_id, campaign_id=None)
    # Derived transport only; the registered managed-World artifact is unchanged.
    transport = SimpleNamespace(**data)
    try:
        identity = get_world_graph_source_admission_authority().prove_or_admit(
            WorldGraphSourceAdmissionRequest(
                world_id=binding.native_world_id, campaign_id=None,
                source_artifact=transport, source_revision_token=resolved.source_revision_id,
                source_uri=resolved.sealed_source_uri, verified_input_sha256=digest,
            )
        )
        result = WorldbuildingSourceAdmissionBinding.model_validate(asdict(identity))
    except WorldGraphSourceAdmissionError as exc:
        raise ExtractPromoteError(str(exc), code=exc.code, status_code=409) from exc
    except (ValueError, TypeError) as exc:
        raise ExtractPromoteError("Source proof is not a canonical World-owned identity",
                                 code="worldbuilding_source_binding_changed", status_code=409) from exc
    if (result.source_artifact_id != binding.source_artifact_id
            or result.content_sha256 != digest
            or result.buddy_source_revision_id != resolved.source_revision_id):
        raise ExtractPromoteError("Source admission identity disagrees with frozen input",
                                 code="worldbuilding_source_binding_changed", status_code=409)
    return result


def _reprove_source_admission(plan):
    from apps.live_control_server.ports.world_graph_source_admission import WorldGraphSourceAdmissionError
    from apps.live_control_server.ports.world_graph_source_admission_access import (
        get_world_graph_source_admission_authority,
    )
    sealed = plan.source_admission
    if sealed is None:
        raise _legacy_reprepare_error()
    try:
        actual = get_world_graph_source_admission_authority().prove(
            world_id=plan.world_id, source_artifact_id=sealed.source_artifact_id,
            source_revision_id=sealed.source_revision_id,
            source_revision_token=sealed.buddy_source_revision_id,
        )
        proof = WorldbuildingSourceAdmissionBinding.model_validate(asdict(actual))
    except WorldGraphSourceAdmissionError as exc:
        raise ExtractPromoteError(str(exc), code=exc.code, status_code=409) from exc
    except (ValueError, TypeError) as exc:
        raise ExtractPromoteError("Source proof is not a canonical World-owned identity",
                                 code="worldbuilding_source_binding_changed", status_code=409) from exc
    if proof != sealed:
        raise ExtractPromoteError("Prepared source catalog authority changed",
                                 code="worldbuilding_source_binding_changed", status_code=409)


_PORT_ERROR_MAP: dict[str, tuple[str, int]] = {
    "authority_unavailable": ("authority_unavailable", 503),
    "revision_unavailable": ("world_not_initialized", 409),
    "stale_parent": ("stale_parent_revision", 409),
    "integrity_failure": ("publication_integrity_failure", 409),
    "inexpressible": ("dungeonmind_inexpressible", 409),
    "publication_failed": ("merge_did_not_publish", 409),
}

_PREPARE_BINDING_SCHEMA = "dmb_worldbuilding_prepare_binding_v1"
_PREPARE_BINDING_KEY_ENV = "DMB_WORLDBUILDING_PREPARE_BINDING_KEY"
_PROCESS_PREPARE_BINDING_KEY = secrets.token_bytes(32)


def _promotable_run_error(exc: PromotableIngestRunError) -> ExtractPromoteError:
    from apps.live_control_server.services.extract_promote import (
        _promotable_run_error as mapped,
    )

    return mapped(exc)


def _authority_error(exc: WorldGraphAuthorityError) -> ExtractPromoteError:
    code, status = _PORT_ERROR_MAP.get(exc.code, ("authority_unavailable", 503))
    if exc.code == "stale_parent":
        message = "expected parent revision is not the current World Graph head"
    elif exc.code == "revision_unavailable":
        message = "The World Graph is not initialized."
    else:
        message = str(exc)
    return ExtractPromoteError(
        message,
        code=code,
        status_code=status,
        diagnostics=[_diagnostic(code, message)],
    )


def _write_plan_error(exc: WorldbuildingWritePlanError) -> ExtractPromoteError:
    return ExtractPromoteError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        diagnostics=[_diagnostic(exc.code, str(exc))],
    )


def _legacy_reprepare_error() -> ExtractPromoteError:
    return ExtractPromoteError(
        "worldbuilding v1 plans have no sealed identity authority; re-prepare",
        code="legacy_plan_reprepare_required",
        status_code=409,
        diagnostics=[
            _diagnostic(
                "legacy_plan_reprepare_required",
                "worldbuilding v1 plans have no sealed identity authority; re-prepare",
            )
        ],
    )


def _identity_snapshot_digest(snapshot: Mapping[str, Any]) -> str:
    payload = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _worldbuilding_native_vocabulary_binding() -> dict[str, Any]:
    """Pin the exact additive vocabulary pair used by Build publication."""
    try:
        from dungeonmind_dnd.application.world_object_vocabulary import (
            builtin_world_object_v6_vocabulary_ref,
            load_builtin_world_object_v6_vocabulary,
        )
        from dungeonmind_dnd.application.world_property_vocabulary import (
            builtin_world_property_v4_vocabulary_ref,
        )

        object_vocabulary = builtin_world_object_v6_vocabulary_ref()
        property_vocabulary = builtin_world_property_v4_vocabulary_ref()
        paired_object_vocabulary = property_vocabulary.world_object_vocabulary
        if paired_object_vocabulary != object_vocabulary:
            raise ValueError("world-property-v4 is not paired with world-object-v6")
        predicates = {
            item.term for item in load_builtin_world_object_v6_vocabulary().predicates
        }
        if "dnd5e:governs" not in predicates:
            raise ValueError("world-object-v6 does not define dnd5e:governs")
        return WorldbuildingNativeVocabularyBinding(
            world_object_vocabulary=object_vocabulary.model_dump(mode="json"),
            world_property_vocabulary=property_vocabulary.model_dump(mode="json"),
        ).model_dump(mode="json", by_alias=True)
    except Exception as exc:
        raise ExtractPromoteError(
            "Build publication requires the pinned world-object-v6/world-property-v4 vocabulary pair",
            code="worldbuilding_native_vocabulary_unavailable",
            status_code=503,
            diagnostics=[_diagnostic("worldbuilding_native_vocabulary_unavailable", str(exc))],
        ) from exc


def _qualify_worldbuilding_native_edges(
    *,
    preview: Any,
    effect: Mapping[str, Any],
    native_vocabulary_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate accepted Build relationships and express v6-only terms natively.

    The sealed write plan remains in Buddy vocabulary. This deterministic
    projection runs only after plan verification, and the source predicate and
    exact vocabulary refs stay alongside the native predicate for audit.
    """
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
        CURRENT_WORLD_BUILDING_V6_TARGET,
        edge_endpoint_kind_admission_reason,
        resolve_buddy_predicate_mapping_v4,
    )
    from graph_memory.candidate_graph_to_contribution import kernel_kind_for_node_type

    effect_data = (
        effect.model_dump(mode="json", by_alias=True)
        if callable(getattr(effect, "model_dump", None))
        else dict(effect)
    )
    result = copy.deepcopy(effect_data)
    nodes = {node.node_id: node for node in preview.nodes}
    edges = {edge.edge_id: edge for edge in preview.edges}
    node_id_map = dict(result.get("node_id_map") or {})
    proposals = result.get("accepted_proposals")
    if not isinstance(proposals, list):
        raise ExtractPromoteError(
            "verified worldbuilding plan has no accepted proposal list",
            code="worldbuilding_native_relation_inexpressible",
            status_code=409,
        )

    for assertion in proposals:
        if not isinstance(assertion, dict) or assertion.get("assertion_kind") != "edge":
            continue
        if assertion.get("predicate") != "governs":
            continue
        value = assertion.get("value")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                value = None
        value = dict(value) if isinstance(value, dict) else {}
        edge_id = str(value.get("extract_edge_id") or "").strip()
        edge = edges.get(edge_id)
        if edge is None or edge.relationship_type != "governs":
            raise ExtractPromoteError(
                "accepted governs assertion is not bound to its exact candidate edge",
                code="worldbuilding_native_relation_inexpressible",
                status_code=409,
                diagnostics=[_diagnostic("worldbuilding_native_relation_inexpressible", edge_id or "missing edge id")],
            )
        source = nodes.get(edge.from_node_id)
        target_node = nodes.get(edge.to_node_id)
        if source is None or target_node is None:
            raise ExtractPromoteError(
                "accepted governs edge has a missing candidate endpoint",
                code="worldbuilding_native_relation_inexpressible",
                status_code=409,
            )
        mapping = resolve_buddy_predicate_mapping_v4(
            edge.relationship_type, target=CURRENT_WORLD_BUILDING_V6_TARGET
        )
        reason = edge_endpoint_kind_admission_reason(
            buddy_predicate=edge.relationship_type,
            from_buddy_kind=kernel_kind_for_node_type(source.node_type),
            to_buddy_kind=kernel_kind_for_node_type(target_node.node_type),
            target=CURRENT_WORLD_BUILDING_V6_TARGET,
        )
        reverse = bool(mapping[1]) if mapping is not None else False
        expected_subject = node_id_map.get(edge.to_node_id if reverse else edge.from_node_id)
        expected_target = node_id_map.get(edge.from_node_id if reverse else edge.to_node_id)
        if (
            mapping is None
            or mapping[0] != "dnd5e:governs"
            or reason is not None
            or assertion.get("subject_node_id") != expected_subject
            or assertion.get("target_node_id") != expected_target
        ):
            raise ExtractPromoteError(
                "accepted governs edge is not admitted by the pinned World vocabulary",
                code="worldbuilding_native_relation_inexpressible",
                status_code=409,
                diagnostics=[
                    _diagnostic(
                        "worldbuilding_native_relation_inexpressible",
                        reason or "mapped assertion endpoints or predicate disagree with candidate edge",
                    )
                ],
            )
        assertion["predicate"] = mapping[0]
        if reverse:
            assertion["subject_node_id"], assertion["target_node_id"] = (
                assertion["target_node_id"],
                assertion["subject_node_id"],
            )
        assertion["value"] = {
            **value,
            "buddy_predicate": edge.relationship_type,
            "dm_predicate": mapping[0],
            "native_vocabulary_binding": dict(native_vocabulary_binding),
        }
    return result


def _prepare_binding_key() -> bytes:
    explicit = os.environ.get(_PREPARE_BINDING_KEY_ENV, "").strip()
    if explicit:
        return hashlib.sha256(
            f"{_PREPARE_BINDING_SCHEMA}:{explicit}".encode("utf-8")
        ).digest()
    return _PROCESS_PREPARE_BINDING_KEY


def _prepare_binding_message(
    *,
    world_id: str,
    parent_revision_id: str,
    plan_id: str,
    plan_digest: str,
    identity_snapshot_digest: str,
    publication_binding: Mapping[str, Any] | None = None,
    source_admission: Mapping[str, Any] | None = None,
    native_vocabulary_binding: Mapping[str, Any] | None = None,
) -> bytes:
    payload = json.dumps(
        {
            "schema": _PREPARE_BINDING_SCHEMA,
            "publication_binding": publication_binding,
            "source_admission": source_admission,
            "native_vocabulary_binding": native_vocabulary_binding,
            "world_id": world_id,
            "parent_revision_id": parent_revision_id,
            "plan_id": plan_id,
            "plan_digest": plan_digest,
            "identity_snapshot_digest": identity_snapshot_digest,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return payload.encode("utf-8")


def _sign_prepare_binding(
    *,
    world_id: str,
    parent_revision_id: str,
    plan_id: str,
    plan_digest: str,
    identity_snapshot_digest: str,
    publication_binding: Mapping[str, Any] | None = None,
    source_admission: Mapping[str, Any] | None = None,
    native_vocabulary_binding: Mapping[str, Any] | None = None,
) -> str:
    digest = hmac.new(
        _prepare_binding_key(),
        _prepare_binding_message(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            plan_id=plan_id,
            plan_digest=plan_digest,
            identity_snapshot_digest=identity_snapshot_digest,
            publication_binding=publication_binding,
            source_admission=source_admission,
            native_vocabulary_binding=native_vocabulary_binding,
        ),
        hashlib.sha256,
    ).hexdigest()
    return f"v1.{digest}"


def _require_prepare_binding(
    plan: WorldbuildingWritePlanResponse,
    snapshot: Mapping[str, Any],
) -> None:
    expected = _sign_prepare_binding(
        world_id=str(plan.world_id),
        parent_revision_id=str(plan.parent_revision_id),
        plan_id=str(plan.plan_id),
        plan_digest=str(plan.plan_digest),
        identity_snapshot_digest=_identity_snapshot_digest(snapshot),
        publication_binding=plan.publication_binding.model_dump(mode="json") if plan.publication_binding else None,
        source_admission=plan.source_admission.model_dump(mode="json") if plan.source_admission else None,
        native_vocabulary_binding=(
            plan.native_vocabulary_binding.model_dump(mode="json", by_alias=True)
            if plan.native_vocabulary_binding else None
        ),
    )
    provided = str(getattr(plan, "prepare_binding", None) or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise ExtractPromoteError(
            "identity snapshot was not sealed by prepare on this server",
            code="identity_snapshot_inexpressible",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "identity_snapshot_inexpressible",
                    "identity snapshot was not sealed by prepare on this server",
                )
            ],
        )


def _relationship_predicate_matches(published: str, expected: str) -> bool:
    """True when the native child edge is the accepted Buddy fact.

    DungeonMind may store a mapped vocabulary term (``linked_to`` →
    ``associated_with``). That is expression, not a dropped assertion.
    """
    if published == expected:
        return True
    published_tail = published.rsplit(":", 1)[-1]
    expected_tail = expected.rsplit(":", 1)[-1]
    if published_tail == expected or published_tail == expected_tail:
        return True
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
        resolve_buddy_predicate_mapping_v4,
    )

    mapping = resolve_buddy_predicate_mapping_v4(expected)
    if mapping is None or not mapping[0]:
        return False
    dm_predicate = mapping[0]
    return published == dm_predicate or published_tail == dm_predicate.rsplit(":", 1)[-1]


def _attribute_evidence_ids(assertion: Any, reviewed_contribution_id: str) -> list[str]:
    ids: list[str] = []
    for item in list(getattr(assertion, "evidence_ref_ids", None) or []):
        text = str(item).strip()
        if text:
            ids.append(text)
    subject = str(getattr(assertion, "subject_node_id", "") or "")
    contribution_id = str(reviewed_contribution_id or "").strip()
    if contribution_id and subject:
        fallback = f"evidence:{contribution_id}:{subject}"
        if fallback not in ids:
            ids.append(fallback)
    return ids


def _evidence_id_on_child(present: set[str], expected_id: str) -> bool:
    """True when the child carries the expected evidence id or its DM v1 rewrite.

    DungeonMind adoption/publication may suffix Buddy evidence ids with
    ``:dmv1:<binding sha256>`` (export identity). Exact id match remains valid.
    """
    if expected_id in present:
        return True
    for marker in (":dmv1:", ":dm-extraction-v3:"):
        prefix = expected_id + marker
        for item in present:
            if not item.startswith(prefix):
                continue
            digest = item[len(prefix):]
            if len(digest) == 64 and all(char in "0123456789abcdef" for char in digest):
                return True
    return False


def _identity_snapshot_payload(plan: WorldbuildingWritePlanResponse) -> dict[str, Any]:
    authority = plan.effect.identity_authority
    if authority is None:
        raise _legacy_reprepare_error()
    payload = authority.model_dump(mode="json", by_alias=False)
    schema = payload.pop("schema_", None) or payload.get("schema")
    if schema:
        payload["schema"] = schema
    return payload


def _confirm_receipt(
    *,
    outcome: str,
    verified: Mapping[str, Any],
    contribution: Any,
    parent_revision_id: str,
    committed_revision_id: str,
    head_advanced: bool,
    accepted_assertion_ids: list[str],
    rejected_assertion_ids: list[str],
    audit_status: ConfirmAuditStatus,
    warnings: list[str],
) -> WorldbuildingWritePlanConfirmReceipt:
    unresolved_mention_ids = [
        mention.mention_id for mention in contribution.unresolved_mentions
    ]
    return WorldbuildingWritePlanConfirmReceipt(
        outcome=outcome,  # type: ignore[arg-type]
        world_id=str(verified["world_id"]),
        plan_id=str(verified["plan_id"]),
        plan_digest=str(verified["plan_digest"]),
        decision_digest=str(verified["decision_digest"]),
        parent_revision_id=parent_revision_id,
        committed_revision_id=committed_revision_id,
        head_advanced=head_advanced,
        contribution_id=contribution.contribution_id,
        applied_assertion_count=len(accepted_assertion_ids),
        accepted_assertion_ids=list(accepted_assertion_ids),
        rejected_assertion_ids=list(rejected_assertion_ids),
        unresolved_mention_ids=unresolved_mention_ids,
        audit_status=audit_status,
        warnings=list(warnings),
    )


def _verify_worldbuilding_child(
    authority: WorldGraphAuthority,
    *,
    receipt: WorldGraphPublicationReceipt,
    contribution: Any,
    verified: Mapping[str, Any],
    parent: str,
    materialized_accepted: list[str],
) -> tuple[str, list[str]]:
    """Prove accepted worldbuilding facts and receipt bindings on the child."""
    codes: list[str] = []
    if receipt.world_id != str(verified["world_id"]):
        codes.append("receipt_world_mismatch")
    if receipt.parent_revision_id != parent:
        codes.append("receipt_parent_mismatch")
    if tuple(receipt.accepted_assertion_ids) != tuple(materialized_accepted):
        codes.append("accepted_assertion_ids_mismatch")
    if not str(receipt.reviewed_contribution_id or "").strip():
        codes.append("reviewed_contribution_unbound")
    try:
        child = authority.read_revision(receipt.world_id, receipt.published_revision_id)
    except WorldGraphAuthorityError as exc:
        if exc.code == "authority_unavailable":
            if codes:
                return "failed", codes
            return "degraded", [f"child_verification_unavailable:{exc.code}"]
        raise
    if (
        child.parent_revision_id
        and child.parent_revision_id != receipt.parent_revision_id
    ):
        codes.append("child_parent_mismatch")
    objects = child.objects
    relationships = list(child.relationships.values())
    for assertion in list(getattr(contribution, "accepted_assertions", None) or []):
        kind = str(getattr(assertion, "assertion_kind", "") or "")
        subject = str(getattr(assertion, "subject_node_id", "") or "")
        target = str(getattr(assertion, "target_node_id", "") or "")
        predicate = str(getattr(assertion, "predicate", "") or "")
        value = getattr(assertion, "value", None) or {}
        if not isinstance(value, dict):
            value = {}
        if kind == "node" and subject and subject not in objects:
            codes.append(f"missing_object:{subject}")
        elif kind == "attribute":
            if subject and subject not in objects:
                codes.append(f"missing_attribute_subject:{subject}")
            elif subject:
                expected = _attribute_evidence_ids(
                    assertion, str(receipt.reviewed_contribution_id or "")
                )
                present_evidence = set(getattr(child, "evidence_refs", {}) or {})
                supported = getattr(child, "supported_assertion_ids", frozenset()) or frozenset()
                assertion_id = str(getattr(assertion, "assertion_id", "") or "")
                terms = tuple(getattr(objects[subject], "property_terms", ()) or ())
                evidence_ok = any(
                    _evidence_id_on_child(present_evidence, item) for item in expected
                ) or (assertion_id in supported)
                terms_ok = bool(
                    predicate
                    and terms
                    and any(
                        _relationship_predicate_matches(term, predicate) for term in terms
                    )
                )
                if predicate and terms and not terms_ok:
                    codes.append(f"missing_attribute:{subject}:{predicate}")
                elif not evidence_ok and not terms_ok:
                    codes.append(
                        f"missing_attribute_evidence:{subject}:{predicate or assertion_id}"
                    )
        elif kind == "alias":
            if subject and subject not in objects:
                codes.append(f"missing_alias_subject:{subject}")
            elif subject:
                alias = str(value.get("alias") or getattr(assertion, "label", "") or "")
                aliases = tuple(getattr(objects[subject], "aliases", ()) or ())
                if alias and alias not in aliases:
                    codes.append(f"missing_alias:{subject}:{alias}")
        elif kind == "edge":
            if subject and subject not in objects:
                codes.append(f"missing_edge_subject:{subject}")
            if target and target not in objects:
                codes.append(f"missing_edge_target:{target}")
            if subject and target and predicate:
                matched = any(
                    rel.subject_object_id == subject
                    and rel.target_object_id == target
                    and _relationship_predicate_matches(rel.predicate, predicate)
                    for rel in relationships
                )
                if not matched:
                    codes.append(f"missing_relationship:{subject}:{predicate}:{target}")
    if codes:
        return "failed", codes
    return "passed", []


def prepare_worldbuilding(
    request: WorldbuildingWritePlanPrepareRequest,
) -> WorldbuildingWritePlanResponse:
    """Prepare a plan and admit exact source provenance, never graph facts."""
    try:
        resolved = resolve_promotable_ingest_run(request.run_id, root=live_config.repo_root())
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc

    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(
        resolved
    )
    publication_binding = _registered_publication_binding(resolved)
    native_vocabulary_binding = _worldbuilding_native_vocabulary_binding()
    typed_preview = _world_scoped_preview(typed_preview, publication_binding)
    native_world_id = publication_binding.native_world_id
    authority = get_world_graph_authority()
    try:
        mutation_context = authority.mutation_context(
            native_world_id, request.expected_parent_revision_id
        )
    except WorldGraphAuthorityError as exc:
        if exc.code == "revision_unavailable":
            try:
                head = authority.current_head(native_world_id)
            except WorldGraphAuthorityError:
                raise _authority_error(exc) from exc
            if head.revision_id != request.expected_parent_revision_id:
                raise ExtractPromoteError(
                    "expected parent revision is not the current World Graph head",
                    code="stale_parent_revision",
                    status_code=409,
                    diagnostics=[
                        _diagnostic(
                            "stale_parent_revision",
                            "expected parent revision is not the current World Graph head",
                        )
                    ],
                ) from exc
        raise _authority_error(exc) from exc

    try:
        plan = build_worldbuilding_write_plan(
            preview=typed_preview,
            mutation_context=mutation_context,
            world_id=native_world_id,
            expected_parent_revision_id=request.expected_parent_revision_id,
            run_id=resolved.run_id,
            source_artifact_id=resolved.source_artifact_id,
            source_revision_id=resolved.source_revision_id,
            source_uri=resolved.sealed_source_uri,
            extraction_profile=expected_profile,
            campaign_scope=None,
            dispositions=[
                WorldbuildingDispositionInput(
                    assertion_id=item.assertion_id,
                    decision=item.decision,
                    target_node_id=item.target_node_id,
                )
                for item in request.dispositions
            ],
        )
    except WorldbuildingWritePlanError as exc:
        raise _write_plan_error(exc) from exc

    # Reject accepted relationships that the sealed native vocabulary cannot
    # express before returning a plan the operator might review.
    _qualify_worldbuilding_native_edges(
        preview=typed_preview,
        effect=plan.effect,
        native_vocabulary_binding=native_vocabulary_binding,
    )

    try:
        head = authority.current_head(native_world_id)
    except WorldGraphAuthorityError as exc:
        raise _authority_error(exc) from exc
    if head.revision_id != request.expected_parent_revision_id:
        raise ExtractPromoteError(
            "expected parent revision is not the current World Graph head",
            code="stale_parent_revision",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "stale_parent_revision",
                    "expected parent revision is not the current World Graph head",
                )
            ],
        )

    response = WorldbuildingWritePlanResponse(
        schema=WORLD_BUILDING_WRITE_PLAN_SCHEMA,
        version=2,
        publication_binding=publication_binding,
        plan_id=plan.plan_id,
        plan_digest=plan.plan_digest,
        decision_digest=plan.decision_digest,
        world_id=plan.world_id,
        parent_revision_id=plan.parent_revision_id,
        run_id=plan.run_id,
        source_artifact_id=plan.source_artifact_id,
        source_revision_id=plan.source_revision_id,
        extraction_profile=plan.extraction_profile,  # type: ignore[arg-type]
        candidate_preview_id=plan.candidate_preview_id,
        candidate_schema=plan.candidate_schema,
        candidate_version=plan.candidate_version,
        effect=plan.effect,
        summary=plan.summary,
        diagnostics=plan.diagnostics,
        native_vocabulary_binding=native_vocabulary_binding,
    )
    try:
        verify_worldbuilding_write_plan(
            response.model_dump(mode="json", by_alias=True),
            preview=typed_preview,
            mutation_context=mutation_context,
            context=WorldbuildingWritePlanVerificationContext(
                world_id=native_world_id,
                parent_revision_id=request.expected_parent_revision_id,
                run_id=resolved.run_id,
                source_artifact_id=resolved.source_artifact_id,
                source_revision_id=resolved.source_revision_id,
                source_uri=resolved.sealed_source_uri,
                extraction_profile=expected_profile,
                campaign_scope=None,
            ),
            require_current_head=False,
        )
    except WorldbuildingWritePlanError as exc:
        if exc.code == "stale_parent_revision":
            raise _write_plan_error(exc) from exc
        raise ExtractPromoteError(
            "worldbuilding write plan failed self-verification",
            code="plan_verification_failed",
            status_code=500,
            diagnostics=[_diagnostic("plan_verification_failed", str(exc))],
        ) from exc
    admitted = _prepare_source_admission(resolved, publication_binding)
    if _registered_publication_binding(resolved) != publication_binding:
        raise ExtractPromoteError("World binding changed after source admission",
                                 code="worldbuilding_source_binding_changed", status_code=409)
    try:
        admitted_head = authority.current_head(native_world_id)
    except WorldGraphAuthorityError as exc:
        raise _authority_error(exc) from exc
    if admitted_head.revision_id != request.expected_parent_revision_id:
        raise ExtractPromoteError("Parent changed after source admission",
                                 code="stale_parent_revision", status_code=409)
    response = response.model_copy(update={"source_admission": admitted})
    snapshot = _identity_snapshot_payload(response)
    return response.model_copy(
        update={
            "prepare_binding": _sign_prepare_binding(
                world_id=native_world_id,
                parent_revision_id=response.parent_revision_id,
                plan_id=response.plan_id,
                plan_digest=response.plan_digest,
                identity_snapshot_digest=_identity_snapshot_digest(snapshot),
                publication_binding=publication_binding.model_dump(mode="json"),
                source_admission=admitted.model_dump(mode="json"),
                native_vocabulary_binding=native_vocabulary_binding,
            )
        }
    )


def confirm_worldbuilding(
    request: WorldbuildingWritePlanConfirmRequest,
) -> WorldbuildingWritePlanConfirmReceipt:
    """Rebuild-verify a v2 plan and publish or recover one DungeonMind child."""
    plan = request.plan
    if (
        plan.schema_ == WORLD_BUILDING_WRITE_PLAN_SCHEMA_V1
        or plan.version == 1
        or plan.effect.identity_authority is None
    ):
        raise _legacy_reprepare_error()

    world_root = live_config.world_graph_root()
    if (
        world_root.resolve() == live_config.live_world_graph_root().resolve()
        and not PRODUCT_CONFIRM_ALLOW_LIVE_WORLD
    ):
        raise ExtractPromoteError(
            "refusing to mutate live world root without allow_live_world",
            code="live_world_refused",
            status_code=403,
            diagnostics=[_diagnostic("live_world_refused", "live world refused")],
        )

    try:
        resolved = resolve_promotable_ingest_run(plan.run_id, root=live_config.repo_root())
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc

    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(
        resolved
    )
    publication_binding = _registered_publication_binding(resolved)
    native_vocabulary_binding = _worldbuilding_native_vocabulary_binding()
    typed_preview = _world_scoped_preview(typed_preview, publication_binding)
    native_world_id = publication_binding.native_world_id
    if plan.publication_binding is None or plan.publication_binding != publication_binding:
        raise ExtractPromoteError("World/source binding changed; prepare again",
                                 code="worldbuilding_source_binding_changed", status_code=409)
    if (
        plan.native_vocabulary_binding is None
        or plan.native_vocabulary_binding.model_dump(mode="json", by_alias=True)
        != native_vocabulary_binding
    ):
        raise ExtractPromoteError(
            "Worldbuilding vocabulary changed; prepare again",
            code="worldbuilding_native_vocabulary_changed",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "worldbuilding_native_vocabulary_changed",
                    "prepared World vocabulary refs do not match the current pinned pair",
                )
            ],
        )
    verify_context = WorldbuildingWritePlanVerificationContext(
        world_id=native_world_id,
        parent_revision_id=plan.parent_revision_id,
        run_id=resolved.run_id,
        source_artifact_id=resolved.source_artifact_id,
        source_revision_id=resolved.source_revision_id,
        source_uri=resolved.sealed_source_uri,
        extraction_profile=expected_profile,
        campaign_scope=None,
    )
    authority = get_world_graph_authority()
    snapshot = _identity_snapshot_payload(plan)
    _require_prepare_binding(plan, snapshot)
    _reprove_source_admission(plan)
    try:
        mutation_context = authority.mutation_context(
            native_world_id,
            plan.parent_revision_id,
            sealed_identity_snapshot=snapshot,
        )
    except WorldGraphAuthorityError as exc:
        raise _authority_error(exc) from exc

    try:
        verified = verify_worldbuilding_write_plan(
            plan.model_dump(mode="json", by_alias=True),
            preview=typed_preview,
            mutation_context=mutation_context,
            context=verify_context,
            require_current_head=False,
        )
        native_effect = _qualify_worldbuilding_native_edges(
            preview=typed_preview,
            effect=verified["effect"],
            native_vocabulary_binding=native_vocabulary_binding,
        )
        contribution = materialize_worldbuilding_contribution(
            world_id=verified["world_id"],
            plan_digest=verified["plan_digest"],
            effect=native_effect,
        )
    except WorldbuildingWritePlanError as exc:
        raise _write_plan_error(exc) from exc

    if PRODUCT_CONFIRM_DRY_RUN:
        raise ExtractPromoteError(
            "worldbuilding confirm dry_run is not supported",
            code="invalid_request",
            status_code=422,
            diagnostics=[_diagnostic("invalid_request", "dry_run not supported")],
        )

    materialized_accepted = [
        assertion.assertion_id for assertion in contribution.accepted_assertions
    ]
    materialized_rejected = [
        assertion.assertion_id for assertion in contribution.rejected_assertions
    ]
    parent = str(verified["parent_revision_id"])
    operation_id = worldbuilding_authority_operation_id(
        world_id=str(verified["world_id"]),
        plan_id=str(verified["plan_id"]),
        plan_digest=str(verified["plan_digest"]),
    )
    actor = str(plan.run_id)
    recovered: WorldGraphPublicationReceipt | None
    try:
        recovered = authority.recover(
            str(verified["world_id"]),
            operation_id,
            expected_parent_revision_id=parent,
            contribution=contribution,
            actor=actor,
            operation_namespace="worldbuilding",
        )
    except WorldGraphAuthorityError as exc:
        raise _authority_error(exc) from exc

    if recovered is not None:
        return _receipt_from_publication(
            receipt=recovered,
            verified=verified,
            resolved=resolved, publication_binding=publication_binding,
            contribution=contribution,
            parent=parent,
            materialized_accepted=materialized_accepted,
            materialized_rejected=materialized_rejected,
            authority=authority,
            outcome="already_applied",
        )

    try:
        head = authority.current_head(str(verified["world_id"]))
    except WorldGraphAuthorityError as exc:
        raise _authority_error(exc) from exc
    if head.revision_id != parent:
        raise ExtractPromoteError(
            "expected parent revision is not the current World Graph head",
            code="stale_parent_revision",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "stale_parent_revision",
                    "expected parent revision is not the current World Graph head",
                )
            ],
        )

    publish_request = WorldGraphPublishRequest(
        world_id=str(verified["world_id"]),
        expected_parent_revision_id=parent,
        authority_operation_id=operation_id,
        actor=actor,
        contribution=contribution,
        accepted_assertion_ids=tuple(materialized_accepted),
        operation_namespace="worldbuilding",
    )
    if _registered_publication_binding(resolved) != publication_binding:
        raise ExtractPromoteError("World/source binding changed before publication",
                                 code="worldbuilding_source_binding_changed", status_code=409)
    try:
        receipt = authority.publish(publish_request)
    except WorldGraphAuthorityError as exc:
        if exc.code == "stale_parent":
            raise _authority_error(exc) from exc
        try:
            recovered = authority.recover(
                str(verified["world_id"]),
                operation_id,
                expected_parent_revision_id=parent,
                contribution=contribution,
                actor=actor,
                operation_namespace="worldbuilding",
            )
        except WorldGraphAuthorityError as recover_exc:
            raise _authority_error(recover_exc) from recover_exc
        if recovered is not None:
            return _receipt_from_publication(
                receipt=recovered,
                verified=verified,
            resolved=resolved, publication_binding=publication_binding,
                contribution=contribution,
                parent=parent,
                materialized_accepted=materialized_accepted,
                materialized_rejected=materialized_rejected,
                authority=authority,
                outcome="already_applied",
                extra_warnings=[f"publish_uncertain:{exc.code}"],
            )
        raise _authority_error(exc) from exc

    return _receipt_from_publication(
        receipt=receipt,
        verified=verified,
            resolved=resolved, publication_binding=publication_binding,
        contribution=contribution,
        parent=parent,
        materialized_accepted=materialized_accepted,
        materialized_rejected=materialized_rejected,
        authority=authority,
        outcome="already_applied" if receipt.outcome == "already_applied" else "committed",
    )


def _receipt_from_publication(
    *,
    receipt: WorldGraphPublicationReceipt,
    resolved,
    publication_binding,
    verified: Mapping[str, Any],
    contribution: Any,
    parent: str,
    materialized_accepted: list[str],
    materialized_rejected: list[str],
    authority: WorldGraphAuthority,
    outcome: str,
    extra_warnings: list[str] | None = None,
) -> WorldbuildingWritePlanConfirmReceipt:
    warnings = list(extra_warnings or [])
    status, codes = _verify_worldbuilding_child(
        authority,
        receipt=receipt,
        contribution=contribution,
        verified=verified,
        parent=parent,
        materialized_accepted=materialized_accepted,
    )
    if status == "failed":
        raise ExtractPromoteError(
            "published worldbuilding child failed native verification",
            code="publication_integrity_failure",
            status_code=409,
            diagnostics=[_diagnostic("publication_integrity_failure", ",".join(codes))],
        )
    audit_status: ConfirmAuditStatus = "ok"
    if status == "degraded":
        audit_status = "degraded"
        outcome = "published_audit_degraded"
        warnings.extend(codes)
    accepted = list(materialized_accepted)
    if _registered_publication_binding(resolved) != publication_binding:
        raise ExtractPromoteError(
            "World/source binding changed; completed publication remains in the original native World",
            code="worldbuilding_source_binding_changed", status_code=409,
        )
    return _confirm_receipt(
        outcome=outcome,
        verified=verified,
        contribution=contribution,
        parent_revision_id=parent,
        committed_revision_id=receipt.published_revision_id,
        head_advanced=receipt.published_revision_id != parent,
        accepted_assertion_ids=accepted,
        rejected_assertion_ids=materialized_rejected,
        audit_status=audit_status,
        warnings=warnings,
    )


__all__ = ["confirm_worldbuilding", "prepare_worldbuilding"]
