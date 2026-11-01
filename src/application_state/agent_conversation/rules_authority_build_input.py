"""Exact Rules proof for current parent-owned Build carriers, never opaque state.

The Build parent separately proves its complete fresh prepared state/questions
or writer envelope. This APP boundary joins only the explicitly selected Rules
projection to its own ledger; it grants no Graph/saved-source authority.
"""
from __future__ import annotations

import json
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, model_validator

from .rules_authority_events import (
    BuildRulesCarrierV1, RulesBuildProviderAuthorizedV1, RulesBuildProviderIncludedV1,
    RulesBuildToolAuthorizedV1, RulesProviderAuthorizedV1, RulesProviderOutcomeV1,
    RulesQueryObservedV1, ref_map,
)
from .rules_authority_packet import _unique_object, verify_output_proof
from .rules_authority_policy import rules_capability
from .rules_authority_types import ClosedRulesModel, Identity


class RulesBuildOperationV1(ClosedRulesModel):
    operation_id: Identity
    packet_json: Annotated[str, Field(min_length=1, max_length=65536)]


class RulesBuildProjectionV1(ClosedRulesModel):
    schema_: Literal["dmb_build_rules_projection_v1"] = Field(alias="schema")
    authorization_id: UUID
    rules_event_sequence: Annotated[int, Field(ge=0, le=255)]
    role: Literal["controller", "writer"]
    carrier_schema: BuildRulesCarrierV1
    request_id: Identity
    prior_provider_attempt_id: UUID | None
    operations: Annotated[tuple[RulesBuildOperationV1, ...], Field(max_length=6)]

    @model_validator(mode="after")
    def bounded_unique_outputs(self):
        if len({op.operation_id for op in self.operations}) != len(self.operations):
            raise ValueError("Build Rules projection repeats an operation")
        if sum(len(op.packet_json.encode("utf-8")) for op in self.operations) > 65536:
            raise ValueError("Build Rules projection exceeds its packet byte bound")
        return self


def _strict_json(raw):
    return json.loads(raw, object_pairs_hook=_unique_object,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite Build Rules input")))


def verify_build_prepared_input(execution, event, body):
    if not isinstance(event, (RulesBuildProviderAuthorizedV1, RulesBuildProviderIncludedV1)):
        raise ValueError("Typed Build Rules input requires its explicit provider variant")
    cap = rules_capability(graph=True)
    scope = execution.scope
    if (scope.capability_policy_sha256 != cap.policy_sha256 or scope.corpus_sha256 != cap.corpus_sha256
            or scope.ruleset_id != cap.ruleset_id):
        raise ValueError("Rules scope did not select the current typed Build proof policy")
    if event.role == "controller":
        if set(body) != {"model", "state", "questions"} or body["model"] != "jev-1.14.0":
            raise ValueError("Unknown Build Rules controller envelope")
        if not isinstance(body["state"], dict) or not isinstance(body["questions"], dict) or not body["questions"]:
            raise ValueError("Malformed Build Rules controller state/questions")
        carrier = body["state"]
    else:
        if (not isinstance(body.get("model"), str) or not body["model"].strip()
                or body.get("tools") != []
                or not isinstance(body.get("input"), str) or "messages" in body or "state" in body):
            raise ValueError("Unknown Build Rules writer envelope")
        carrier = _strict_json(body["input"])
        if not isinstance(carrier, dict):
            raise ValueError("Build Rules writer input is not an object")
    schema = carrier.get("schema")
    if schema != event.carrier_schema:
        raise ValueError("Build Rules carrier differs from its provider binding")
    controller_policies = {
        "dmb_build_jev_driver_decision_v2": ("policy", "parent_machine_lossless_v1"),
        "dmb_build_jev_driver_continuation_v1": ("input_policy", "receipt_bound_factored_controller_v1"),
        "dmb_build_jev_phase_controller_v1": ("input_policy", "role_separated_controller_inputs_v1"),
    }
    if event.role == "controller":
        if schema not in controller_policies:
            raise ValueError("Writer carrier cannot be used as a controller")
        key, expected = controller_policies[schema]
        if carrier.get(key) != expected:
            raise ValueError("Unknown Build Rules controller input policy")
        if schema == "dmb_build_jev_driver_decision_v2" and carrier.get("initial_packet_codec") != "dmb_build_initial_packet_table_v1":
            raise ValueError("Unknown Build Rules initial packet codec")
    elif schema not in {"dmb_build_source_passage_writer_v1", "dmb_build_primary_context_writer_v1", "dmb_build_primary_context_writer_v2", "dmb_build_jev_writer_packet_v1"}:
        raise ValueError("Controller carrier cannot be used as a writer")
    elif schema in {"dmb_build_source_passage_writer_v1", "dmb_build_primary_context_writer_v1", "dmb_build_primary_context_writer_v2"}:
        if (carrier.get("source_writer_output_policy") != "cited_facts_host_limitations_v1"
                or carrier.get("requested_detail_gap_policy") != "exact_question_phrase_selected_excerpts_v1"):
            raise ValueError("Unknown Build Rules cited-writer policy")
        if schema in {"dmb_build_primary_context_writer_v1", "dmb_build_primary_context_writer_v2"}:
            from .build_primary_context import packet_rows
            if "artifact_under_edit" not in carrier:
                raise ValueError("Primary Build Rules writer lacks authored context lane")
            packet_rows(carrier)
            if schema == "dmb_build_primary_context_writer_v2" and not isinstance(carrier.get("working_draft_context"), dict):
                raise ValueError("Selected primary Build Rules writer lacks its complete draft lane")
    elif carrier.get("input_policy") != "complete_exposed_graph_and_opened_sources_v1":
        raise ValueError("Unknown Build Rules Graph-writer policy")
    try:
        projection = RulesBuildProjectionV1.model_validate_json(json.dumps(carrier["rules_projection"], ensure_ascii=False))
    except (KeyError, TypeError) as exc:
        raise ValueError("Build Rules input lacks its explicit typed projection") from exc
    if projection.authorization_id != scope.authorization_id:
        raise ValueError("Build Rules projection belongs to another logical submission")
    if any(getattr(projection, key) != getattr(event, key) for key in (
            "role", "carrier_schema", "request_id", "prior_provider_attempt_id")):
        raise ValueError("Build Rules projection differs from its provider role/request")
    if isinstance(event, RulesBuildProviderAuthorizedV1):
        auth = event
    else:
        auth = next((e for e in execution.events if isinstance(e, RulesBuildProviderAuthorizedV1)
            and e.provider_attempt_id == event.provider_attempt_id), None)
        if auth is None or auth.request_envelope_sha256 != event.request_envelope_sha256:
            raise ValueError("Build Rules inclusion has no matching authorization")
    if projection.rules_event_sequence != auth.sequence:
        raise ValueError("Build Rules projection uses a stale ledger snapshot")
    previous = [e for e in execution.events if isinstance(e, RulesProviderAuthorizedV1) and e.sequence < auth.sequence]
    prior = previous[-1] if previous else None
    if projection.prior_provider_attempt_id != (prior.provider_attempt_id if prior else None):
        raise ValueError("Build Rules projection differs from its current prior provider")
    if prior is not None:
        outcome = next((e for e in execution.events if isinstance(e, RulesProviderOutcomeV1)
            and e.provider_attempt_id == prior.provider_attempt_id), None)
        if (not isinstance(prior, RulesBuildProviderAuthorizedV1) or outcome is None
                or outcome.status not in {"answered", "tool_calls"}):
            raise ValueError("Build Rules continuation lacks an acknowledged prior provider")
    if event.role == "controller" and projection.operations and (
            schema == "dmb_build_jev_driver_decision_v2"
            or schema == "dmb_build_jev_phase_controller_v1"
            and carrier.get("phase_binding", {}).get("phase") in {"navigate", "coverage", "select"}):
        raise ValueError("Build navigation cannot expose Rules source bodies")
    lookups = {e.call_id: e for e in execution.events if isinstance(e, RulesBuildToolAuthorizedV1)}
    observed = {e.call_id: e for e in execution.events if isinstance(e, RulesQueryObservedV1)}
    outputs, supports = {}, {}
    for operation in projection.operations:
        lookup = lookups.get(operation.operation_id)
        result = observed.get(operation.operation_id)
        if lookup is None or result is None or result.query_id != lookup.query_id:
            raise ValueError("Build Rules projection has no admitted operation/result")
        verify_output_proof(scope, result, execution.supports, operation.packet_json)
        outputs[operation.operation_id] = result.packet_sha256
        refs = ref_map(result.support_refs)
        supports.update({key: refs[key] for key in result.emitted_support_ids})
    declared = {item.call_id: item.packet_sha256 for item in event.matched_outputs}
    if len(declared) != len(event.matched_outputs) or declared != outputs:
        raise ValueError("Build Rules output declarations differ from actual packets")
    declared_refs = event.declared_support_refs if isinstance(event, RulesBuildProviderAuthorizedV1) else event.support_refs
    if ref_map(declared_refs) != supports:
        raise ValueError("Build Rules support declarations differ from actual source bodies")
