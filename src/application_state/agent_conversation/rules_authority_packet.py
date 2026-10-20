"""Verify internal, ephemeral Rules output proof before sealing an observation.

The raw packet is never persisted by this module. ApplicationState's locked
append operation must invoke this verifier; HTTP/model inputs are not receipts.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .rules_authority_events import (
    RulesQueryObservedV1,
    RulesStoredSupportV1,
    normalized_question,
    query_identity,
    ref_map,
)
from .rules_authority_types import (
    ClosedRulesModel,
    Digest,
    Identity,
    RulesScopeV1,
    RulesSupportRefV1,
    RulesSupportV1,
    canonical_sha256,
)


class RulesPacketV1(ClosedRulesModel):
    schema_: Literal["dmb_rules_packet_v1"] = Field(alias="schema")
    call_id: Identity
    query_id: Digest
    normalized_question: Annotated[str, Field(min_length=1, max_length=14400)]
    corpus_sha256: Digest
    ruleset_id: Annotated[str, Field(pattern=r"^[a-z0-9_]{1,80}$")]
    status: Literal["evidence", "no_evidence", "unavailable", "denied", "over_budget"]
    support_refs: Annotated[tuple[RulesSupportRefV1, ...], Field(max_length=4)]
    emitted_support_ids: Annotated[tuple[UUID, ...], Field(max_length=4)]
    previous_support_ids: Annotated[tuple[UUID, ...], Field(max_length=4)]
    support_capsules: Annotated[tuple[RulesSupportV1, ...], Field(max_length=4)]
    diagnostic: (
        Literal["corpus_unavailable", "unsupported_ruleset", "rules_budget_exhausted"]
        | None
    )

    @model_validator(mode="after")
    def exact_partition(self):
        refs = ref_map(self.support_refs)
        emitted = set(self.emitted_support_ids)
        previous = set(self.previous_support_ids)
        if self.normalized_question != normalized_question(self.normalized_question):
            raise ValueError("Rules packet question is not normalized")
        if len(emitted) != len(self.emitted_support_ids) or len(previous) != len(
            self.previous_support_ids
        ):
            raise ValueError("Rules packet repeats a support identity")
        if emitted & previous or emitted | previous != set(refs):
            raise ValueError("Rules packet must partition exact result supports")
        capsules = {
            unit.support_id: canonical_sha256(unit) for unit in self.support_capsules
        }
        if len(capsules) != len(self.support_capsules) or set(capsules) != emitted:
            raise ValueError("Rules packet capsules differ from emitted identities")
        if any(refs[key] != digest for key, digest in capsules.items()):
            raise ValueError("Rules packet capsule digest differs from its reference")
        if (self.status == "evidence") != bool(refs):
            raise ValueError("Only evidence packets carry source support")
        expected_diagnostic = {
            "unavailable": "corpus_unavailable",
            "denied": "unsupported_ruleset",
            "over_budget": "rules_budget_exhausted",
        }.get(self.status)
        if self.diagnostic != expected_diagnostic:
            raise ValueError("Rules packet diagnostic differs from status")
        return self


class RulesBudgetDiagnosticV1(ClosedRulesModel):
    schema_: Literal["dmb_rules_budget_diagnostic_v1"] = Field(alias="schema")
    execution_id: UUID
    call_id: Identity
    code: Literal["rules_budget_exhausted"]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Rules output contains duplicate JSON keys")
        result[key] = value
    return result


def verify_output_proof(
    scope: RulesScopeV1,
    observation: RulesQueryObservedV1,
    supports: dict[UUID, RulesStoredSupportV1],
    raw_output: str,
) -> None:
    """Match exact output bytes and admitted capsules, without storing a second copy."""
    raw = raw_output.encode("utf-8")
    if (
        len(raw) > 65536
        or observation.presentation_utf8 != len(raw)
        or observation.packet_sha256 != sha256(raw).hexdigest()
    ):
        raise ValueError(
            "Rules output byte length or raw digest differs from observation"
        )
    if observation.execution_id != scope.execution_id:
        raise ValueError("Rules output belongs to another execution")
    # Duplicate keys are rejected before Pydantic; do not silently select a value.
    json.loads(raw_output, object_pairs_hook=_unique_object)
    if observation.status == "over_budget":
        if (
            len(raw) > 1024
            or observation.support_refs
            or observation.emitted_support_ids
        ):
            raise ValueError("Rules budget diagnostic exceeds its reserved envelope")
        diagnostic = RulesBudgetDiagnosticV1.model_validate_json(raw_output)
        if (
            diagnostic.execution_id != scope.execution_id
            or diagnostic.call_id != observation.call_id
        ):
            raise ValueError("Rules budget diagnostic belongs to another call")
        return
    packet = RulesPacketV1.model_validate_json(raw_output)
    if (
        packet.call_id != observation.call_id
        or packet.query_id != observation.query_id
        or packet.query_id != query_identity(scope, packet.normalized_question)
        or packet.corpus_sha256 != scope.corpus_sha256
        or packet.ruleset_id != scope.ruleset_id
        or packet.status != observation.status
        or packet.support_refs != observation.support_refs
        or packet.emitted_support_ids != observation.emitted_support_ids
    ):
        raise ValueError(
            "Rules raw packet differs from its frozen observation or source scope"
        )
    for ref in packet.support_refs:
        stored = supports.get(ref.support_id)
        if (
            stored is None
            or stored.support_sha256 != ref.support_sha256
            or stored.support.corpus_sha256 != scope.corpus_sha256
            or stored.support.ruleset_id != scope.ruleset_id
        ):
            raise ValueError("Rules packet refers to an unadmitted source capsule")
    for capsule in packet.support_capsules:
        if capsule != supports[capsule.support_id].support:
            raise ValueError("Rules emitted capsule differs from admitted source text")


def append_observed_output(
    execution,
    observation: RulesQueryObservedV1,
    raw_output: str,
    new_supports: tuple[RulesSupportV1, ...] = (),
):
    """Pure validated append; the SQL owner supplies current claim/CAS fencing.

    Exact event replay is a no-op. New equivalent calls are separate observations
    and consume presentation bytes, while source bodies retain one identity.
    """
    from .rules_authority_events import RulesExecutionV1

    if execution.state != "active":
        raise ValueError("Rules execution no longer accepts output")
    support_map = dict(execution.supports)
    for support in new_supports:
        if support.support_id not in observation.emitted_support_ids:
            raise ValueError("New Rules source was not emitted by this observation")
        stored = RulesStoredSupportV1(
            support=support, support_sha256=canonical_sha256(support)
        )
        previous = support_map.get(support.support_id)
        if previous is not None and previous != stored:
            raise ValueError("Rules source identity was reused for different text")
        support_map[support.support_id] = stored
    verify_output_proof(execution.scope, observation, support_map, raw_output)
    previous = next(
        (item for item in execution.events if item.event_id == observation.event_id),
        None,
    )
    if previous is not None:
        if previous != observation or support_map != execution.supports:
            raise ValueError("Rules observation replay differs from sealed event")
        return execution
    data = execution.model_dump(mode="json", by_alias=True)
    data["supports"] = {
        str(key): value.model_dump(mode="json", by_alias=True)
        for key, value in support_map.items()
    }
    data["events"].append(observation.model_dump(mode="json", by_alias=True))
    data["budget_use"]["presentation_utf8"] += observation.presentation_utf8
    data["budget_use"]["novel_excerpt_utf8"] = sum(
        len(item.support.excerpt_text.encode("utf-8")) for item in support_map.values()
    )
    # Whole-ledger validation derives all counters again and checks prior call,
    # sequence, scope, result identity, capsule reuse and retirement thresholds.
    return RulesExecutionV1.model_validate_json(json.dumps(data, ensure_ascii=False))
