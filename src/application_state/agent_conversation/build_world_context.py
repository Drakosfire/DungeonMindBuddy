"""Build turn scope and per-origin acquired context; never publication authority."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from .types import BuildSourceContextBasisV1, Digest, StrictModel

POLICY = "build_world_opened_source_context_v1"


class _Frozen(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FrozenBuildBasis(BuildSourceContextBasisV1):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BuildContextScope(_Frozen):
    kind: Literal["build_world_context"] = "build_world_context"
    policy: Literal["build_world_opened_source_context_v1"] = POLICY
    managed_world_id: str = Field(min_length=1)
    world_id: str = Field(min_length=1)
    binding_version: int = Field(strict=True, ge=1)
    graph_revision: str = Field(min_length=1)
    primary_basis: FrozenBuildBasis
    client_thread_id: str = Field(min_length=1)
    client_turn_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def primary_belongs_to_world(self):
        if self.primary_basis.world_id != self.managed_world_id:
            raise ValueError("Primary Build basis belongs to another managed World")
        return self


class PrimarySectionOrigin(_Frozen):
    kind: Literal["primary_saved_section"] = "primary_saved_section"
    source_basis: FrozenBuildBasis
    section_event_id: UUID
    read_id: UUID


class PrimaryObservationOrigin(_Frozen):
    kind: Literal["primary_reviewed_observation"] = "primary_reviewed_observation"
    source_basis: FrozenBuildBasis
    operation_event_ids: tuple[UUID, ...] = Field(min_length=1)
    assertion_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    source_revision_id: str = Field(min_length=1)
    evidence_ref_ids: tuple[str, ...] = Field(min_length=1)


class WorldPassageOrigin(_Frozen):
    kind: Literal["world_opened_passage"] = "world_opened_passage"
    operation_event_id: UUID
    source_read_event_id: UUID
    source_read_id: str = Field(min_length=1)
    anchor_id: str = Field(min_length=1)
    evidence_ref_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    source_revision_id: str = Field(min_length=1)
    content_sha256: Digest
    line_start: int | None = Field(default=None, strict=True, ge=1)
    line_end: int | None = Field(default=None, strict=True, ge=1)

    @model_validator(mode="after")
    def ordered_lines(self):
        if (self.line_start is None) != (self.line_end is None) or (
            self.line_start is not None and self.line_end < self.line_start
        ):
            raise ValueError("World passage line range is reversed")
        return self


SourceOrigin = PrimarySectionOrigin | PrimaryObservationOrigin | WorldPassageOrigin


def scope_digest(turn):
    from . import types as t

    if (
        not isinstance(turn.graph_context_receipt, t.BuildGraphContextReceiptV1)
        or getattr(turn.graph_context_execution.policy, "world_context_policy", None)
        != POLICY
        or turn.provenance.surface_id != "build"
    ):
        raise ValueError(
            "World context requires its exact Build receipt and capability"
        )
    return t.canonical_sha256(
        {
            "world_id": turn.world_id,
            "turn_id": str(turn.turn_id),
            "conversation_id": str(turn.conversation_id),
            "attempt": turn.attempt,
            "context_receipt_sha256": turn.graph_context_receipt.context_receipt_sha256,
            "execution_policy_sha256": turn.graph_context_execution.execution_policy_sha256,
        }
    )


def request_arguments(turn, target):
    arguments = {
        "retrievalSessionId": turn.graph_context_execution.policy.source_read_scope.retrieval_session_id,
        "operation": target.operation,
    }
    if target.operation == "search":
        if target.node_id is not None or target.action_id != "world-search":
            raise ValueError("World search target changed")
        arguments["queryText"] = turn.user_text
    else:
        if not target.node_id or target.action_id != "world-object:" + target.node_id:
            raise ValueError("World object target changed")
        arguments["targets"] = [{"kind": "node", "id": target.node_id}]
    return arguments


def verify_world_selection(turn, event, proof, trace):
    """Join actual Build controller bytes/choices to the World action, never prose."""
    from hashlib import sha256
    from generationengine.types import DecisionResult
    from . import types as t
    from .source_writer_output import strict_json

    execution = turn.graph_context_execution
    expected_scope = scope_digest(turn)
    if (
        not isinstance(proof, dict)
        or set(proof) != {"request_json", "response_json"}
        or not isinstance(event, t.BuildWorldReadSelectionV1)
    ):
        raise ValueError("World action requires exact controller request/result proof")
    auths = [
        e for e in execution.events if isinstance(e, t.ProviderAttemptAuthorizedEventV3)
    ]
    auth = auths[-1] if auths else None
    if (
        auth is None
        or auth.provider_attempt_id != event.controller_attempt_id
        or (auth.provider, auth.model, auth.api_mode)
        != execution.policy.provider_roles.controller.identity()
        or sha256(proof["request_json"].encode()).hexdigest() != auth.envelope_sha256
        or auth.envelope_sha256 != event.controller_envelope_sha256
        or event.scope_sha256 != expected_scope
        or event.context_receipt_sha256 != execution.context_receipt_sha256
        or event.execution_policy_sha256 != execution.execution_policy_sha256
        or sha256(proof["response_json"].encode()).hexdigest()
        != event.controller_response_sha256
    ):
        raise ValueError(
            "World action differs from its actual current Build controller"
        )
    if (
        trace.get("world_id") != turn.world_id
        or trace.get("turn_id") != str(turn.turn_id)
        or trace.get("conversation_id") != str(turn.conversation_id)
        or trace.get("attempt") != turn.attempt
        or trace.get("capture_status") != "recording"
    ):
        raise ValueError("World action result capture belongs to another turn")
    identity = f"unvalidated-controller-decision:{auth.provider_attempt_id}:{execution.context_receipt_sha256}"
    outputs = [
        m
        for o in trace.get("observations", [])
        if o.get("kind") == "context_snapshot"
        for m in o.get("materials", [])
        if m.get("item_id") == identity
    ]
    if len(outputs) != 1 or outputs[0].get("text") != proof["response_json"]:
        raise ValueError("World action lacks its exact protected controller result")
    request = strict_json(proof["request_json"])
    result = DecisionResult.model_validate(strict_json(proof["response_json"]))
    state = request["state"]
    decision = state["decision"]
    if (
        result.observation.provider != "typesafe"
        or result.observation.resolved_model != auth.model
        or result.observation.response_model != auth.model
        or request.get("model") != auth.model
        or decision.get("request_id") != event.machine_request_id
        or decision.get("phase") not in {"navigate", "coverage"}
        or state.get("schema") != "dmb_build_jev_phase_controller_v1"
        or state.get("historical_initial", {}).get("turn_id") != str(turn.turn_id)
        or state["historical_initial"].get("execution_policy_sha256")
        != execution.execution_policy_sha256
    ):
        raise ValueError("World action was not offered in current Build navigation")
    catalog = decision["state"]["action_catalog"]
    if catalog.get("columns") != ["id", "kind", "hint", "hint_truncated"]:
        raise ValueError("World action lacks its exact current action catalog")
    rows = catalog["rows"]
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError("World action catalog repeats an identity")
    offered = {
        row[0]: row[1] for row in rows if row[1] in {"world_search", "world_object"}
    }
    if decision["phase"] == "navigate":
        selected = result.answers["next"].selected
        choices = {selected} & set(offered)
    else:
        choices = {
            row[0]
            for i, row in enumerate(rows)
            if row[0] in offered
            and result.answers[f"use_{i}"].selected in {"useful", "unknown"}
        }
    if choices != {a.action_id for a in event.actions} or len(choices) != len(
        event.actions
    ):
        raise ValueError("World action differs from actual selected offered choices")
    for action in event.actions:
        if (
            offered[action.action_id] != "world_" + action.operation
            or action.request_arguments_sha256
            != t.canonical_sha256(request_arguments(turn, action))
        ):
            raise ValueError(
                "World action executable target differs from the admitted choice"
            )


def validate_world_events(execution):
    from . import types as t

    enabled = getattr(execution.policy, "world_context_policy", None) == POLICY
    seen, provider, outcome = set(), None, None
    for event in execution.events:
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            provider, outcome = event, None
        elif (
            isinstance(event, t.ProviderOutcomeEventV1)
            and provider is not None
            and event.provider_attempt_id == provider.provider_attempt_id
        ):
            outcome = event.outcome
        elif isinstance(event, t.BuildWorldReadSelectionV1):
            if (
                not enabled
                or provider is None
                or outcome != "response_received"
                or (provider.provider, provider.model, provider.api_mode)
                != execution.policy.provider_roles.controller.identity()
                or provider.provider_attempt_id != event.controller_attempt_id
                or provider.envelope_sha256 != event.controller_envelope_sha256
                or event.context_receipt_sha256 != execution.context_receipt_sha256
                or event.execution_policy_sha256 != execution.execution_policy_sha256
            ):
                raise ValueError(
                    "World action lacks its current acknowledged controller"
                )
            for action in event.actions:
                if action.action_id in seen:
                    raise ValueError(
                        "World acquisition cannot repeat an attempted target"
                    )
                seen.add(action.action_id)


def opened_world_passages(
    execution, operation_ids, read_ids, graph_payloads, source_payloads
):
    """Reconstruct each origin from actual selected operations and real V2 reads."""
    from hashlib import sha256
    from . import types as t
    from .source_writer_output import strict_json

    events = {str(e.event_id): e for e in execution.events}
    pins, donor_for = {}, {}
    for identity in operation_ids:
        operation = events.get(str(identity))
        permitted = {
            a.request_arguments_sha256
            for e in execution.events
            if isinstance(e, t.BuildWorldReadSelectionV1)
            and e.sequence < getattr(operation, "sequence", -1)
            for a in e.actions
        }
        if (
            not isinstance(operation, t.ValidatedGraphOperationEventV3)
            or operation.request_arguments_sha256 not in permitted
            or operation.graph_revision
            != execution.policy.source_read_scope.graph_revision
        ):
            raise ValueError(
                "World passage lacks its selected current object operation"
            )
        raw = strict_json(graph_payloads[operation.event_id])
        native = {
            k: v
            for k, v in raw.items()
            if k not in {"retrievalSessionId", "addedClaimIds", "claimLedger"}
        }
        if t.canonical_sha256(native) != operation.result_packet_sha256:
            raise ValueError("World object body differs from its committed operation")
        for pin in operation.returned_source_pins:
            if execution.effective_source_pins().get(pin.anchor_id) != pin:
                raise ValueError("World source pin differs from current admitted scope")
            if pin.anchor_id in pins and pins[pin.anchor_id] != pin:
                raise ValueError("World source pin changed between selected objects")
            pins[pin.anchor_id] = pin
            donor_for[pin.anchor_id] = operation.event_id
    result = []
    for identity in read_ids:
        event = events.get(str(identity))
        if not isinstance(event, t.ValidatedSourceReadEventV2):
            raise ValueError("World source is not an actual V2 read")
        raw = strict_json(source_payloads[event.event_id])
        rows = raw.get("reads", [raw])
        if len(rows) != len(event.receipts):
            raise ValueError("World source bodies differ from receipt count")
        for body, receipt in zip(rows, event.receipts, strict=True):
            pin = pins.get(receipt.anchor_id)
            if pin is None:
                continue  # Other selected units must represent whole batch siblings.
            if (
                receipt.evidence_ref_id != pin.evidence_ref_id
                or receipt.source_artifact_id != pin.source_artifact_id
                or receipt.source_revision_id != pin.source_revision_id
                or receipt.outcome != "enough"
                or receipt.truncated
                or receipt.evidence_sufficiency_status != "sufficient"
                or body.get("outcome") != receipt.outcome
                or body.get("truncated", False)
                or body.get("anchorId") != receipt.anchor_id
                or body.get("evidenceRefId") != receipt.evidence_ref_id
                or body.get("sourceArtifactId") != receipt.source_artifact_id
                or body.get("lineStart") != receipt.line_start
                or body.get("lineEnd") != receipt.line_end
                or not isinstance(body.get("content"), str)
                or len(body["content"]) != receipt.returned_chars
                or sha256(body["content"].encode()).hexdigest()
                != receipt.content_sha256
            ):
                raise ValueError(
                    "World passage differs from exact selected pin/read bytes"
                )
            name = body.get("sourceName")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("World passage lacks its host-provided source name")
            origin = WorldPassageOrigin(
                operation_event_id=donor_for[pin.anchor_id],
                source_read_event_id=event.event_id,
                source_read_id=receipt.source_read_id,
                anchor_id=pin.anchor_id,
                evidence_ref_id=pin.evidence_ref_id,
                source_artifact_id=pin.source_artifact_id,
                source_revision_id=pin.source_revision_id,
                content_sha256=receipt.content_sha256,
                line_start=receipt.line_start,
                line_end=receipt.line_end,
            )
            result.append((origin, body["content"], name.strip()))
    return result


def scope_presentation(scope):
    if isinstance(scope, BuildContextScope):
        return {
            "kind": "primary_authored_page_and_opened_world_sources",
            "primary_role": "authored_reference_not_played_truth",
            "world_role": "opened_source_evidence_not_graph_truth",
        }
    return scope.model_dump(mode="json")


def verify_named_input(packet, turn, trace):
    """Display names come from protected read captures, never writer or caller text."""
    execution = turn.graph_context_execution
    if packet.get("world_context_policy") != getattr(
        execution.policy, "world_context_policy", None
    ):
        raise ValueError("Named source capability differs from frozen execution")
    if getattr(execution.policy, "world_context_policy", None) != POLICY:
        return
    captured = {}
    for row in trace.get("observations", []):
        if row.get("kind") not in {"source_passage", "source_passage_reuse"}:
            continue
        key = (
            row.get("source_artifact_id"),
            row.get("source_revision_id"),
            row.get("line_start"),
            row.get("line_end"),
            row.get("text"),
        )
        if key in captured and captured[key] != row.get("source_name"):
            raise ValueError("Ambiguous captured source owner name")
        captured[key] = row.get("source_name")
    for passage in packet.get("opened_passages", []):
        key = (
            passage.get("source_artifact_id"),
            passage.get("source_revision_id"),
            passage.get("line_start"),
            passage.get("line_end"),
            passage.get("text"),
        )
        if key not in captured or passage.get("source_name") != captured[key]:
            raise ValueError("Writer source name differs from protected source read")
