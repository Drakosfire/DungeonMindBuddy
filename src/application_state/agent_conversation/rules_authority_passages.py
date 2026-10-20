"""One cited historical Rules capsule, resolved from accepted storage only.

The caller must verify current operator/World admission before this private SQL
boundary. No current catalog or remote source participates in historical reads.
"""

from __future__ import annotations

import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.errors import (
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
)
from .rules_authority_events import RulesStoredSupportV1
from .rules_authority_types import (
    ClosedRulesModel,
    Digest,
    RulesAcceptedBindingV1,
    RulesScopeV1,
    RulesSupportV1,
    canonical_bytes,
    canonical_sha256,
)


class RulesHistoricalPassageRequestV1(ClosedRulesModel):
    world_id: Annotated[str, Field(min_length=1, max_length=256)]
    conversation_id: UUID
    turn_id: UUID
    attempt: Annotated[int, Field(ge=1)]
    support_id: UUID
    support_sha256: Digest


class RulesHistoricalPassageV1(ClosedRulesModel):
    schema_: Literal["dmb_rules_historical_passage_v1"] = Field(alias="schema")
    world_id: str
    conversation_id: UUID
    turn_id: UUID
    accepted_attempt: Annotated[int, Field(ge=1)]
    support: RulesSupportV1
    support_sha256: Digest

    @model_validator(mode="after")
    def exact_bounded_capsule(self):
        if (
            canonical_sha256(self.support) != self.support_sha256
            or len(canonical_bytes(self)) > 32768
        ):
            raise ValueError(
                "Historical Rules capsule differs from its digest or response bound"
            )
        return self


def read_historical_rules_passage(
    conn, request: RulesHistoricalPassageRequestV1
) -> RulesHistoricalPassageV1:
    capsule = "(r.payload->'supports'->%(support_id)s)"
    cited = "(r.accepted_binding->'support_table' @> %(wanted)s)"
    admitted = """(t.status='completed' AND t.answer_composition_kind='rules_mixed_v1'
        AND t.attempt=%(attempt)s AND r.payload->>'state'='accepted'
        AND octet_length(r.accepted_binding::text)<=40960)"""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""SELECT t.status,t.answer_composition_kind,t.revision,t.attempt,
            r.payload->>'state' AS rules_state,
            CASE WHEN octet_length((r.payload->'scope')::text)<=4096 THEN r.payload->'scope' ELSE NULL END AS scope,
            CASE WHEN octet_length(r.accepted_binding::text)<=40960 THEN r.accepted_binding ELSE NULL END AS binding,
            r.accepted_binding_sha256 AS seal,
            COALESCE({cited},FALSE) AS cited,
            COALESCE({admitted} AND {cited} AND octet_length({capsule}::text)>40960,FALSE) AS capsule_oversized,
            CASE WHEN {admitted} AND {cited} AND octet_length({capsule}::text)<=40960 THEN {capsule} ELSE NULL END AS capsule
            FROM agent.turn t LEFT JOIN agent.turn_rules_execution r ON r.turn_id=t.turn_id AND r.product_attempt=t.attempt
            WHERE t.world_id=%(world)s AND t.conversation_id=%(conversation)s AND t.turn_id=%(turn)s""",
            dict(
                world=request.world_id,
                conversation=request.conversation_id,
                turn=request.turn_id,
                attempt=request.attempt,
                support_id=str(request.support_id),
                wanted=Jsonb(
                    [
                        dict(
                            support_id=str(request.support_id),
                            support_sha256=request.support_sha256,
                        )
                    ]
                ),
            ),
        )
        row = cur.fetchone()
    if row is None or row["attempt"] != request.attempt:
        raise ApplicationStateNotFoundError(
            "Historical Rules passage not found in verified World conversation and attempt"
        )
    if (
        row["status"] != "completed"
        or row["answer_composition_kind"] != "rules_mixed_v1"
    ):
        raise ApplicationStateNotFoundError("Turn has no completed mixed Rules answer")
    if (
        row["rules_state"] != "accepted"
        or row["binding"] is None
        or row["scope"] is None
    ):
        raise ApplicationStateIntegrityError(
            "Historical Rules answer has no bounded accepted authority"
        )
    try:
        binding = RulesAcceptedBindingV1.model_validate_json(
            json.dumps(row["binding"], ensure_ascii=False)
        )
        scope = RulesScopeV1.model_validate_json(
            json.dumps(row["scope"], ensure_ascii=False)
        )
        if canonical_sha256(binding) != row["seal"]:
            raise ValueError("Historical Rules summary seal differs")
        owner = (
            request.world_id,
            request.conversation_id,
            request.turn_id,
            request.attempt,
        )
        if (
            binding.world_id,
            binding.conversation_id,
            binding.turn_id,
            binding.product_attempt,
        ) != owner or binding.accepted_turn_revision != row["revision"]:
            raise ValueError("Historical Rules binding differs from its accepted owner")
        if (
            scope.world_id,
            scope.conversation_id,
            scope.turn_id,
            scope.product_attempt,
        ) != owner or (scope.execution_id, scope.corpus_sha256, scope.ruleset_id) != (
            binding.execution_id,
            binding.corpus_sha256,
            binding.ruleset_id,
        ):
            raise ValueError(
                "Historical Rules frozen scope differs from accepted authority"
            )
    except (ValueError, TypeError, KeyError) as exc:
        raise ApplicationStateIntegrityError(
            "Historical Rules authority failed strict validation"
        ) from exc
    if not row["cited"]:
        raise ApplicationStateNotFoundError(
            "Rules support is not cited by this accepted answer"
        )
    if row["capsule"] is None or row["capsule_oversized"]:
        raise ApplicationStateIntegrityError(
            "Cited Rules source capsule is missing or exceeds transfer bound"
        )
    try:
        stored = RulesStoredSupportV1.model_validate_json(
            json.dumps(row["capsule"], ensure_ascii=False)
        )
        support = stored.support
        if (
            support.support_id,
            stored.support_sha256,
            support.corpus_sha256,
            support.ruleset_id,
        ) != (
            request.support_id,
            request.support_sha256,
            binding.corpus_sha256,
            binding.ruleset_id,
        ):
            raise ValueError("Historical source identity differs from cited support")
        return RulesHistoricalPassageV1(
            schema="dmb_rules_historical_passage_v1",
            world_id=request.world_id,
            conversation_id=request.conversation_id,
            turn_id=request.turn_id,
            accepted_attempt=request.attempt,
            support=support,
            support_sha256=stored.support_sha256,
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise ApplicationStateIntegrityError(
            "Historical Rules source capsule failed strict validation"
        ) from exc
