"""Author-selected corpus sources in the existing exact Run-owned Play ledger.

Core owns admission/bytes. This owner binds that read to human input and the
actual Play producer, without borrowing a Build/Plan controller capability.
"""

from __future__ import annotations

import json
from typing import Literal
from pydantic import Field, model_validator

from .authored_graph_references import (
    AuthoredReferencesV2,
    AuthoredSourceReferenceV1,
    validate_selected_source_read,
)
from .native_corpus import (
    NativeCorpusAuthorityV1,
    NativeAuthoredSourceReadV1,
    NativeBodyProviderIncludedV1,
    model_body_frame_records,
    body_frame,
)
from .rules_authority_types import ClosedRulesModel, canonical_sha256


class PlayAuthoredSourceContextV1(ClosedRulesModel):
    schema_: Literal["dmb_play_authored_source_context_v1"] = Field(
        default="dmb_play_authored_source_context_v1", alias="schema"
    )
    authority: NativeCorpusAuthorityV1
    references: AuthoredReferencesV2

    @model_validator(mode="after")
    def exact_source_selections(self):
        if (
            self.schema_ != "dmb_play_authored_source_context_v1"
            or not self.references.references
        ):
            raise ValueError(
                "Play source context requires explicit nonempty source input"
            )
        for ref in self.references.references:
            if not isinstance(ref, AuthoredSourceReferenceV1):
                raise ValueError("Play source context does not admit object references")
            if (ref.managed_world_id, ref.native_world_id, ref.binding_version) != (
                self.authority.managed_world_id,
                self.authority.native_world_id,
                self.authority.binding_version,
            ):
                raise ValueError("Play selected source differs from its World binding")
        return self

    @property
    def authority_sha256(self):
        return canonical_sha256(self.authority)


def context(execution):
    return getattr(execution.policy, "authored_source_context", None)


def reads(execution):
    return tuple(
        e for e in execution.events if isinstance(e, NativeAuthoredSourceReadV1)
    )


def validate_events(execution):
    from . import types as t

    ctx = context(execution)
    relevant = [
        e
        for e in execution.events
        if isinstance(
            e,
            (
                t.BuildAuthoredReferencesCapturedV1,
                NativeAuthoredSourceReadV1,
                NativeBodyProviderIncludedV1,
            ),
        )
    ]
    if ctx is None:
        if relevant:
            raise ValueError(
                "Play reference events require their frozen source capability"
            )
        return
    captures = [
        e for e in relevant if isinstance(e, t.BuildAuthoredReferencesCapturedV1)
    ]
    if not captures:
        if execution.events:
            raise ValueError("Play author input must be captured before activity")
        return
    if len(captures) != 1:
        raise ValueError("Play author input may be captured once")
    capture = captures[0]
    if (
        capture.sequence != 0
        or capture.references != ctx.references
        or capture.read_graph_revision != ctx.authority.revision_id
    ):
        raise ValueError("Play author capture changed its frozen source intent")
    acquired, providers, included, section_inclusions = {}, {}, set(), set()
    for event in execution.events:
        if isinstance(event, NativeAuthoredSourceReadV1):
            if (
                providers
                or event.capture_event_id != capture.event_id
                or event.sequence <= capture.sequence
                or event.reference_index in acquired
                or event.reference_index >= len(ctx.references.references)
            ):
                raise ValueError(
                    "Play source read changed or repeated its captured selection"
                )
            validate_selected_source_read(
                ctx.references.references[event.reference_index],
                event.catalog,
                event.excerpt,
                authority_sha256=ctx.authority_sha256,
            )
            acquired[event.reference_index] = event
        elif isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            if len(acquired) != len(ctx.references.references):
                raise ValueError(
                    "Play provider cannot omit an unresolved selected source"
                )
            providers[event.provider_attempt_id] = event
        elif isinstance(event, t.NativeSourceProviderInclusionV1):
            section_inclusions.add(event.provider_attempt_id)
        elif isinstance(event, NativeBodyProviderIncludedV1):
            provider = providers.get(event.provider_attempt_id)
            if (
                provider is None
                or event.provider_attempt_id in included
                or event.sequence
                != provider.sequence
                + 1
                + int(event.provider_attempt_id in section_inclusions)
                or event.envelope_sha256 != provider.envelope_sha256
                or event.read_event_ids
                != tuple(row.event_id for row in acquired.values())
                or event.frame_sha256
                != canonical_sha256(body_frame(tuple(acquired.values())))
            ):
                raise ValueError(
                    "Play source inclusion changed its exact producer or selected reads"
                )
            included.add(event.provider_attempt_id)
        elif (
            isinstance(event, t.CompletionBindingEventV1)
            and event.provider_attempt_id not in included
        ):
            raise ValueError(
                "Play completion lacks its producing selected-source inclusion"
            )


def validate_binding(receipt, execution):
    ctx = context(execution)
    if ctx != getattr(receipt, "authored_source_context", None):
        raise ValueError("Play source capability differs from its frozen receipt")
    if ctx is None:
        return
    a, graph = ctx.authority, receipt.graph_authority
    if (a.managed_world_id, a.native_world_id, a.binding_version, a.revision_id) != (
        graph.managed_world_id,
        graph.native_world_id,
        graph.binding_version,
        graph.graph_revision,
    ):
        raise ValueError(
            "Play corpus inspection differs from its frozen World/revision"
        )


def capture_input(turn, *, event_id):
    from . import types as t

    receipt, execution = turn.graph_context_receipt, turn.graph_context_execution
    if not isinstance(receipt, t.PlayWorldGraphContextReceiptV1) or not isinstance(
        execution, t.PlayWorldGraphExecutionV1
    ):
        raise ValueError("Play reference capture requires its actual Run-owned turn")
    validate_binding(receipt, execution)
    ctx = context(execution)
    if ctx is None:
        raise ValueError("Play reference capture has no source selections")
    return t.BuildAuthoredReferencesCapturedV1(
        kind="build_authored_references_captured_v1",
        event_id=event_id,
        sequence=len(execution.events),
        references=ctx.references,
        read_graph_revision=ctx.authority.revision_id,
        turn_id=turn.turn_id,
        conversation_id=turn.conversation_id,
        attempt=turn.attempt,
        submitted_intent_fingerprint=turn.submitted_intent_fingerprint_v2,
    )


def observe_source(turn, *, event_id, reference_index, materialize):
    from .authored_graph_references import capture

    execution = turn.graph_context_execution
    validate_binding(turn.graph_context_receipt, execution)
    ctx = context(execution)
    if ctx is None or not 0 <= reference_index < len(ctx.references.references):
        raise ValueError("Play source read has no exact selected input")
    catalog, excerpt = materialize(ctx.references.references[reference_index])
    validate_selected_source_read(
        ctx.references.references[reference_index],
        catalog,
        excerpt,
        authority_sha256=ctx.authority_sha256,
    )
    return NativeAuthoredSourceReadV1(
        event_id=event_id,
        sequence=len(execution.events),
        capture_event_id=capture(execution).event_id,
        reference_index=reference_index,
        catalog=catalog,
        excerpt=excerpt,
    )


def model_frame(execution):
    ctx = context(execution)
    if ctx is None:
        return None
    return model_body_frame_records(
        ctx.authority, execution, lambda row: "r" + str(row.reference_index)
    )


def prove_input(turn, authorization, raw, *, sequence, event_id):
    """Derive selected-source inclusion from the actual current Play SDK request."""
    from hashlib import sha256
    from . import types as t
    from .play_graph_input import NativePlayInputV6, _user_texts, MAX_REQUEST_BYTES
    from .source_writer_output import strict_json

    receipt, execution = turn.graph_context_receipt, turn.graph_context_execution
    if (
        not isinstance(receipt, t.PlayWorldGraphContextReceiptV1)
        or not isinstance(execution, t.PlayWorldGraphExecutionV1)
        or not isinstance(authorization, t.ProviderAttemptAuthorizedEventV3)
        or isinstance(authorization, t.PlanJevProviderAuthorizedV1)
        or context(execution) is None
        or sequence
        != authorization.sequence
        + 1
        + int(
            any(
                isinstance(row, t.NativeSourceSectionObservedV1)
                and row.outcome == "complete"
                for row in execution.events
            )
        )
        or not isinstance(raw, str)
        or len(raw.encode()) > MAX_REQUEST_BYTES
        or sha256(raw.encode()).hexdigest() != authorization.envelope_sha256
    ):
        raise ValueError(
            "Play selected sources lack their exact prepared provider input"
        )
    validate_binding(receipt, execution)
    selected = reads(execution)
    if len(selected) != len(context(execution).references.references):
        raise ValueError("Play selected sources must be read before provider admission")
    body = strict_json(raw)
    if not isinstance(body, dict) or body.get("model") != authorization.model:
        raise ValueError("Play selected sources changed their producing model")
    carriers = []
    for text in _user_texts(body, authorization.api_mode):
        try:
            candidate = strict_json(text)
        except (ValueError, TypeError):
            continue
        if (
            not isinstance(candidate, dict)
            or candidate.get("schema") != "dmb_native_play_input_v6"
        ):
            continue
        carrier = NativePlayInputV6.model_validate_json(
            json.dumps(candidate, ensure_ascii=False)
        )
        if carrier.submission_id == turn.idempotency_key:
            carriers.append(carrier)
    if (
        len(carriers) != 1
        or carriers[0].message != turn.user_text
        or carriers[0].native_body_evidence != model_frame(execution)
    ):
        raise ValueError(
            "Play selected sources changed their exact current-submission bytes"
        )
    return NativeBodyProviderIncludedV1(
        event_id=event_id,
        sequence=sequence,
        provider_attempt_id=authorization.provider_attempt_id,
        envelope_sha256=authorization.envelope_sha256,
        read_event_ids=tuple(row.event_id for row in selected),
        frame_sha256=canonical_sha256(body_frame(selected)),
    )


def producing_bodies(turn, authorization, raw):
    """Reuse the shared citation support after checking the actual Play producer."""
    from .native_corpus import NativeBodySupport

    execution = turn.graph_context_execution
    witnesses = [
        e
        for e in execution.events
        if isinstance(e, NativeBodyProviderIncludedV1)
        and e.provider_attempt_id == authorization.provider_attempt_id
    ]
    if len(witnesses) != 1:
        raise ValueError(
            "Play answer lacks its unique selected-source producing inclusion"
        )
    witness = witnesses[0]
    if (
        prove_input(
            turn,
            authorization,
            raw,
            sequence=witness.sequence,
            event_id=witness.event_id,
        )
        != witness
    ):
        raise ValueError(
            "Play selected sources differ from their actual producing bytes"
        )
    return tuple(
        NativeBodySupport("r" + str(row.reference_index), row, row.catalog)
        for row in reads(execution)
        if row.event_id in witness.read_event_ids
    )
