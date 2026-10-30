"""Typed Plan capability bases; no cross-family revision or authority aliases."""
from __future__ import annotations
from dataclasses import dataclass
from . import types as t
from .native_corpus import NativeCorpusAuthorityV1


@dataclass(frozen=True)
class PlanCapabilityBases:
    receipt: t.PlanWorldGraphContextReceiptV1 | t.PlanSourceContextReceiptV1
    graph: t.PlanWorldGraphContextReceiptV1 | None
    source: NativeCorpusAuthorityV1 | t.NativeCorpusUnavailableV1 | None

    @property
    def plan_basis(self):
        return self.receipt.plan_basis


def capability_bases(receipt):
    if isinstance(receipt, t.PlanSourceContextReceiptV1):
        return PlanCapabilityBases(receipt, receipt.graph_capability, receipt.source_authority)
    if isinstance(receipt, t.PlanWorldGraphContextReceiptV1):
        return PlanCapabilityBases(receipt, receipt, None)
    raise ValueError("Resolved Plan capability receipt required")


def require_graph(receipt):
    graph = capability_bases(receipt).graph
    if graph is None:
        raise ValueError("This Plan turn has no authorized Graph capability")
    return graph


def validate_source_execution_binding(receipt, execution):
    """Bind native source and optional Graph capabilities without cross-family IDs."""
    from .native_corpus import NativeBodySearchAuthorizedV1
    if not isinstance(receipt, t.PlanSourceContextReceiptV1) or not isinstance(execution, t.PlanSourceExecutionV1):
        raise ValueError("Source-capable Plan requires its exact receipt and execution")
    if (execution.context_receipt_sha256 != receipt.context_receipt_sha256
            or execution.policy.source_authority_sha256 != t.canonical_sha256(
                receipt.source_authority.model_dump(mode="json", by_alias=True))):
        raise ValueError("Plan source execution differs from its frozen receipt authority")
    if isinstance(receipt, t.PlanNativeContextReceiptV1):
        from .native_plan_statements import validate_execution
        validate_execution(receipt, execution)
    scope = execution.policy.source_read_scope
    graph = receipt.graph_capability
    if graph is None:
        if scope is not None or execution.policy.allowed_graph_operations:
            raise ValueError("Plan source execution manufactured an absent Graph capability")
    else:
        authority = graph.graph_authority
        if (scope is None or scope.world_id != authority.managed_world_id
                or scope.campaign_id != authority.campaign_id
                or scope.graph_revision != authority.graph_revision):
            raise ValueError("Plan Graph scope differs from its independently frozen authority")
        inputs = t._ask_graph_validation_inputs(graph).model_copy(update={
            "context_receipt_sha256": receipt.context_receipt_sha256})
        t.validate_graph_selected_source_binding(inputs, execution)
        t.validate_graph_related_recap_context_scope(inputs, execution)
    for event in execution.events:
        if isinstance(event, NativeBodySearchAuthorizedV1) and (
                not isinstance(receipt.source_authority, NativeCorpusAuthorityV1)
                or event.authority != receipt.source_authority):
            raise ValueError("Native source search differs from its frozen source-only authority")


def validate_source_provenance(receipt, provenance):
    basis, ref = receipt.plan_basis, provenance.primary_work
    targets = [t.decode_plan_playable_target_reference(row) for row in provenance.supporting_work
        if row.kind == t.PLAN_PLAYABLE_TARGET_REFERENCE_KIND]
    if targets != ([] if receipt.playable_target is None else [receipt.playable_target]):
        raise ValueError("Source-capable Plan target differs from its resolved provenance")
    if (provenance.world_id != basis.world_id
            or provenance.surface_resolution != "resolved"
            or provenance.surface_id != "plan" or not provenance.surface_instance_id
            or provenance.selected_object.resolution != "absent"
            or ref.resolution != "resolved" or ref.kind != "plan"
            or ref.object_id != basis.document_id
            or ref.object_revision != basis.object_revision
            or ref.work_revision_id != basis.work_revision_id
            or ref.revision_n != basis.revision_n
            or ref.content_sha256 != basis.content_sha256):
        raise ValueError("Source-capable Plan receipt differs from its resolved provenance")


def validate_source_submission(submission):
    receipt, execution = submission.graph_context_receipt, submission.graph_context_execution
    intent = submission.submitted_intent_v2
    if (not isinstance(intent, t.SubmittedTurnIntentV2)
            or not isinstance(receipt, t.PlanSourceContextReceiptV1)
            or not isinstance(execution, t.PlanSourceExecutionV1)
            or submission.submitted_intent_v1 is not None
            or submission.play_context_receipt is not None
            or intent.world_id != submission.world_id or intent.message != submission.user_text
            or submission.provenance.surface_instance_id != intent.surface_instance_id):
        raise ValueError("Source-capable Plan requires its exact submitted intent and execution")
    basis, primary = receipt.plan_basis, intent.primary_work
    if (basis.world_id != submission.world_id
            or receipt.plan_context_policy != intent.plan_context_policy
            or basis.document_id != primary.object_id
            or basis.object_revision != primary.expected_revision
            or basis.revision_n != primary.expected_revision_n
            or basis.content_sha256 != primary.expected_content_sha256
            or not t._receipt_target_matches_intent(receipt.playable_target, intent.playable_target)
            or execution.policy.plan_authoring_capture_sha256 != intent.plan_authoring_capture_sha256
            or execution.policy.placement_catalog_sha256 != intent.plan_placement_catalog_sha256):
        raise ValueError("Source-capable Plan receipt differs from its submitted Plan basis or capture")
    if isinstance(receipt, t.PlanNativeContextReceiptV1) and isinstance(receipt.native_query, t.NativePlanQueryV1) and receipt.native_query.question != submission.user_text:
        raise ValueError("Native query differs from unchanged submitted question")
    validate_source_provenance(receipt, submission.provenance)
    validate_source_execution_binding(receipt, execution)
    if execution.events:
        raise ValueError("Accepted source-capable Plan execution must start empty")
    accounting, assembled = execution.policy.provider_input_accounting, receipt.assembled_input
    if (accounting.estimator != assembled.tokenizer_name
            or (accounting.kind == "conservative_upper_bound" and assembled.tokenizer_version != "v1")):
        raise ValueError("Source-capable receipt differs from its frozen provider accounting")


def validate_source_provider_envelope(receipt, execution, event):
    validate_source_execution_binding(receipt, execution)
    graph = receipt.graph_capability
    if graph is None:
        if (event.included_assertion_ids or event.included_relationship_ids
                or event.included_evidence_ref_ids or event.included_graph_event_ids
                or getattr(event, "included_source_read_event_ids", ())
                or getattr(event, "included_source_reuse_event_ids", ())):
            raise ValueError("Source-capable turn cannot include absent Graph evidence")
    else:
        t.validate_graph_provider_evidence(t._ask_graph_validation_inputs(graph), execution, event)
    t.validate_provider_envelope_accounting(receipt.assembled_input, execution, event)
