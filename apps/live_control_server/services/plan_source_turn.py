"""Trusted Plan source composition; the existing Jev harness owns execution.

This module creates no request runner and opens no document body. Its output is
host-only authority for the existing claim/authorization and navigation owners.
"""
from hashlib import sha256
import json

from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_source_context import validate_source_execution_binding
from ..integrations.dungeonmind.native_corpus_source import prepare_native_source_context


def prepare(managed_world_id, principal, *, revision_id=None, repository=None, resolve_identity=None):
    """Resolve source ownership before optional Graph bootstrap, without body IO.

    Absence of a head is an explicit unavailable capability. Authorization,
    descriptor, binding and integrity failures are not empty search results.
    """
    if principal is None or principal.role != "gm":
        raise ValueError("GM authority is required for Plan source inspection")
    if resolve_identity is None:
        from .managed_world_graph_projection import resolve_managed_source_identity
        resolve_identity = resolve_managed_source_identity
    bound = resolve_identity(managed_world_id)
    if bound.managed_world_id != managed_world_id:
        raise ValueError("Plan source identity differs from requested World")
    if repository is None:
        from ..integrations.dungeonmind.native_registry_source import repository as native_repository
        repository = native_repository()
    head = repository.get_head(bound.native_world_id) if revision_id is None else None
    if revision_id is None and head is None:
        return None, t.NativeCorpusUnavailableV1(managed_world_id=managed_world_id,
            failure_code="native_source_head_unavailable")
    context = prepare_native_source_context(managed_world_id=managed_world_id,
        principal=principal, revision_id=revision_id or head.head_revision_id,
        repository=repository, resolve_identity=resolve_identity)
    if context.binding != bound:
        raise ValueError("Plan source ownership changed during composition")
    return context, context.authority


def freeze(request, work, playable_target, view, budget, *, authority, graph_receipt=None,
           graph_policy=None, included_history=(), plan_jev_request=None):
    """Freeze the actual first Jev wire under independent source/Graph bases."""
    from .agent_turn_service import _json_node_count
    from .plan_jev_dispatch import verify_initial_input
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    verify_initial_input(view, request, work, plan_jev_request)
    basis = work.content_basis
    if (request.surface.surface_id != "plan" or request.plan_context_policy is None
            or basis is None or authority.managed_world_id != basis.world_id):
        raise ValueError("Plan source composition requires its exact committed Plan World")
    if (graph_receipt is None) != (graph_policy is None):
        raise ValueError("A genuine Graph capability requires its own receipt and policy")
    if graph_receipt is not None and (not isinstance(graph_receipt, t.PlanWorldGraphContextReceiptV1)
            or not isinstance(graph_policy, t.PlanPlacementAuthoringPolicyV1)):
        raise ValueError("Plan source composition cannot manufacture a Graph capability")
    raw = view["payloadJson"].encode()
    if len(raw) != view["payloadUtf8Bytes"] or sha256(raw).hexdigest() != view["payloadSha256"]:
        raise ValueError("Plan source first provider bytes differ from their actual witness")
    body = json.loads(raw)
    count = len(raw) + 64 * (1 + _json_node_count(body))
    assembled = t.PlanSourceProviderInputV1(provider_model_name=view["model"],
        provider_model_version=view["model"], tokenizer_name=budget["estimator"],
        tokenizer_version="v1", provider_envelope_input_tokens=count,
        output_token_reserve=budget["outputReserveTokens"], context_window_limit=budget["contextLimitTokens"],
        included_history=[t.PlanWorldGraphHistoryPinV1(turn_id=turn_id,
            answer_sha256=sha256(text.encode()).hexdigest()) for turn_id, text in included_history
            if text and _contains_text(body, text)], assembled_input_sha256=view["payloadSha256"])
    plan_basis = t.PlanAskContextBasis(world_id=basis.world_id, document_id=basis.document_id,
        object_revision=basis.object_revision, work_revision_id=basis.work_revision_id,
        revision_n=basis.revision_n, content_sha256=basis.content_sha256)
    provisional = t.PlanSourceContextReceiptV1.model_construct(
        receipt_serializer_version="canonical-json-utf8-v1", context_receipt_sha256="0" * 64,
        plan_context_policy=request.plan_context_policy, plan_basis=plan_basis,
        playable_target=playable_target, source_authority=authority,
        graph_capability=graph_receipt, assembled_input=assembled)
    payload = provisional.model_dump(mode="json", by_alias=True, exclude={"context_receipt_sha256"})
    receipt = t.PlanSourceContextReceiptV1.model_validate(payload | {"context_receipt_sha256": canonical_sha256(payload)})
    fields = dict(allowed_graph_operations=[], max_provider_attempts=None, max_graph_operations=None,
        max_results_per_operation=0, max_total_provider_input_tokens=None,
        max_total_provider_output_tokens=None, provider_input_accounting={
            "kind": "conservative_upper_bound", "estimator": budget["estimator"]},
        source_opened=False, source_read_scope=None, max_source_read_chars=96000,
        max_chars_per_source_read=12000, source_read_accounting="settled_receipts_v1",
        provider_roles=budget["providerRoles"], native_source_section_policy="exact_native_source_sections_v1",
        requested_work_policy="semantic_plan_placement_v1",
        placement_catalog_sha256=request.plan_placement_catalog.sha256 if request.plan_placement_catalog is not None else None,
        plan_authoring_capture_sha256=request.plan_authoring_capture.sha256 if request.plan_authoring_capture is not None else None,
        source_authority_sha256=canonical_sha256(authority.model_dump(mode="json", by_alias=True)))
    if graph_policy is not None:
        for key in ("allowed_graph_operations", "max_results_per_operation", "source_read_scope",
                    "max_source_read_chars", "max_chars_per_source_read"):
            fields[key] = getattr(graph_policy, key)
    policy = t.PlanSourceExecutionPolicyV1(**fields)
    execution_payload = dict(schema="dmb_plan_source_execution_v1",
        context_receipt_sha256=receipt.context_receipt_sha256,
        policy=policy.model_dump(mode="json", by_alias=True))
    execution = t.PlanSourceExecutionV1.model_validate(execution_payload | {
        "execution_policy_sha256": canonical_sha256(execution_payload), "events": []})
    validate_source_execution_binding(receipt, execution)
    return receipt, execution, ([], [], [])


def _contains_text(value, text):
    if isinstance(value, str):
        return value == text
    if isinstance(value, list):
        return any(_contains_text(item, text) for item in value)
    if isinstance(value, dict):
        return any(_contains_text(item, text) for item in value.values())
    return False
