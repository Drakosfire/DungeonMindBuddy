"""Structured answer support validator — claim-class authority, not anchor presence."""

from __future__ import annotations

import json

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.interaction.claims import GraphClaim, TurnOutcomeState
from graph_memory.interaction.references import (
    GraphReference,
    InferenceReference,
    SourceCitation,
)
from graph_memory.interaction.schema_constants import STRUCTURED_ANSWER_DRAFT_SCHEMA
from graph_memory.interaction.session import GraphRetrievalSession

StatementKind = Literal["graph_fact", "source_detail", "inference", "suggestion", "gap"]
ValidatorPath = Literal[
    "explicit_conversation_context",
    "graph_context_synthesis",
    "claim_ledger_validation",
]
AnswerAuthority = Literal[
    "explicit_conversation_context",
    "graph_context_synthesis",
    "graph_grounded",
    "abstained",
    "execution_error",
]
ExplicitAnswerScope = Literal["conversation_context"]


class AnswerSection(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    text: str
    statement_kind: StatementKind
    supporting_claim_ids: list[str] = Field(default_factory=list)
    source_read_ids: list[str] = Field(default_factory=list)
    inference_id: str | None = None


class StructuredAnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["dmb_structured_answer_draft_v1"] = Field(
        default=STRUCTURED_ANSWER_DRAFT_SCHEMA,
        alias="schema",
    )
    sections: list[AnswerSection] = Field(default_factory=list)
    coverage: dict[str, Any] = Field(default_factory=dict)


class ValidatedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    outcome: TurnOutcomeState
    answer_text: str
    accepted_claim_ids: list[str] = Field(default_factory=list)
    rejected_claim_ids: list[str] = Field(default_factory=list)
    graph_references: list[GraphReference] = Field(default_factory=list)
    source_citations: list[SourceCitation] = Field(default_factory=list)
    inferences: list[InferenceReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    diagnostic_codes: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    # Retained response shape; current validation does not populate legacy support.
    support_lag_text: str | None = None
    support_excerpt_text: str | None = None
    # Natural Hermes prose is frontstage, while this ledger rendering remains
    # available as support until sentence-level response projection exists.
    support_claim_ledger_text: str | None = None
    answer_authority: AnswerAuthority | None = None
    validator_path: ValidatorPath | None = None


ABSTENTION_ANSWER = (
    "DungeonBuddy’s World Graph does not currently contain enough admitted evidence "
    "to answer this question reliably."
)
HERMES_NO_CHAT_ANSWER = "Hermes did not return a chat answer for this turn."
PARTIAL_SOURCE_WARNING = (
    "Source verification is unavailable or incomplete for one or more supporting anchors."
)


def _claims_by_id(session: GraphRetrievalSession) -> dict[str, GraphClaim]:
    return {claim.claim_id: claim for claim in session.claims}


def _graph_refs_for_claims(
    claims: Sequence[GraphClaim],
    *,
    revision_id: str,
) -> list[GraphReference]:
    refs: list[GraphReference] = []
    for claim in claims:
        object_kind: Literal["assertion", "node", "relationship", "claim"]
        if claim.claim_kind == "relationship":
            object_kind = "relationship"
        elif claim.claim_kind == "identity":
            object_kind = "node"
        elif claim.claim_kind in {"attribute", "source_observation"}:
            object_kind = "assertion"
        else:
            object_kind = "claim"
        refs.append(
            GraphReference(
                revision_id=revision_id,
                object_kind=object_kind,
                object_id=claim.source_assertion_id or claim.claim_id,
                label=claim.value_text or claim.subject_label,
                claim_id=claim.claim_id,
            )
        )
    return refs


def _claim_ledger_text(claims: Sequence[GraphClaim]) -> str | None:
    if not claims:
        return None
    bullets: list[str] = []
    for claim in claims[:12]:
        label = claim.subject_label or claim.subject_node_id or claim.claim_id
        predicate = (
            "reviewed source observation"
            if claim.claim_kind == "source_observation"
            else claim.predicate or claim.claim_kind
        )
        value = claim.value_text or ""
        if claim.claim_kind == "source_observation":
            scope = json.dumps(claim.temporal_scope, sort_keys=True) if claim.temporal_scope is not None else "unspecified"
            predicate += (
                f" ({claim.observation_kind}; temporal_scope={scope}; "
                f"epistemic_kind={claim.epistemic_kind or 'unspecified'}; "
                f"source={claim.source_artifact_id or 'unspecified'}; "
                f"source_revision={claim.source_revision_id or 'unspecified'})"
            )
        bullets.append(f"- {label}: {predicate} — {value}".strip(" —"))
    heading = ("Graph-grounded facts and source context for this turn:\n"
               if any(claim.claim_kind == "source_observation" for claim in claims)
               else "Graph-grounded facts for this turn:\n")
    return heading + "\n".join(bullets)


def _source_citations_from_session(session: GraphRetrievalSession) -> list[SourceCitation]:
    citations: list[SourceCitation] = []
    for read in session.source_reads:
        if read.outcome not in {"enough", "partial", "truncated"}:
            continue
        citations.append(
            SourceCitation(
                revision_id=session.snapshot.revision_id,
                anchor_id=read.anchor_id,
                source_artifact_id=read.source_artifact_id,
                content_sha256=read.content_sha256,
                line_start=read.line_start,
                line_end=read.line_end,
                truncated=read.truncated,
                source_read_id=read.source_read_id,
            )
        )
    return citations


def synthesize_draft_from_session(
    session: GraphRetrievalSession,
    *,
    model_prose: str | None = None,
) -> StructuredAnswerDraft:
    """Build a deterministic draft without blessing unstructured model prose.

    The Hermes wire result currently exposes free-form ``final_response`` text,
    not a typed answer draft. Until a producer supplies ``AnswerSection`` rows
    with claim IDs, the fallback must render the accepted ledger directly.
    Attaching every accepted claim to arbitrary prose would turn unrelated
    claims into apparent support for that prose.
    """
    factual = [c for c in session.claims if c.may_state_as_campaign_fact()]
    sections: list[AnswerSection] = []
    if factual and not (model_prose and model_prose.strip()):
        sections.append(
            AnswerSection(
                text=_claim_ledger_text(factual) or "",
                statement_kind="graph_fact",
                supporting_claim_ids=[c.claim_id for c in factual],
            )
        )
    unreadable = [
        a.anchor_id for a in session.source_anchors if (not a.readable) and (not a.opened)
    ]
    # Keep source-verification limits in the validator warning/support channel.
    # They are not frontstage answer prose and should not interrupt a co-GM read.
    known = [c.predicate or c.claim_kind for c in factual]
    missing = ["source verification"] if unreadable else []
    coverage_state = "partial_coverage" if missing else ("graph_grounded" if factual else "empty")
    return StructuredAnswerDraft(
        sections=sections,
        coverage={
            "state": coverage_state,
            "known": known,
            "missing": missing,
        },
    )


def validate_structured_answer(
    session: GraphRetrievalSession,
    draft: StructuredAnswerDraft | Mapping[str, Any] | None,
    *,
    model_prose: str | None = None,
    execution_error: bool = False,
    execution_error_code: str | None = None,
    answer_scope: ExplicitAnswerScope | None = None,
) -> ValidatedAnswer:
    """Validate a Hermes turn's answer against the shared claim ledger.

    ``answer_scope`` is set when Hermes completed ``declare_conversation_context``
    without graph retrieval this turn. That explicit scope wins over deterministic
    preflight candidates: they remain session context, not support for a
    conversation summary.
    """
    if execution_error:
        return ValidatedAnswer(
            outcome="execution_error",
            answer_text=(
                "DungeonBuddy could not complete this World Graph Hermes turn. "
                "No legacy retrieval fallback was used."
            ),
            diagnostic_codes=[execution_error_code or "hermes_graph_agent_error"],
            reason_codes=["execution_error"],
            answer_authority="execution_error",
            validator_path="claim_ledger_validation",
        )

    if answer_scope == "conversation_context":
        if model_prose and model_prose.strip():
            return ValidatedAnswer(
                outcome="conversation_context",
                answer_text=model_prose.strip(),
                reason_codes=["explicit_conversation_context"],
                answer_authority="explicit_conversation_context",
                validator_path="explicit_conversation_context",
            )
        return ValidatedAnswer(
            outcome="abstained",
            answer_text=ABSTENTION_ANSWER,
            diagnostic_codes=["hermes_insufficient_evidence"],
            reason_codes=["explicit_conversation_context", "missing_chat_answer"],
            answer_authority="abstained",
            validator_path="explicit_conversation_context",
        )

    parsed = (
        StructuredAnswerDraft.model_validate(draft)
        if isinstance(draft, Mapping)
        else draft
    )
    if parsed is None or not parsed.sections:
        parsed = synthesize_draft_from_session(
            session,
            model_prose=model_prose,
        )

    by_id = _claims_by_id(session)

    def current_factual_claim(claim_id: str) -> GraphClaim | None:
        claim = by_id.get(claim_id)
        if claim is None:
            return None
        if claim.revision_id != session.snapshot.revision_id:
            rejected.append(claim_id)
            reason_codes.append("claim_revision_mismatch")
            return None
        if not claim.may_state_as_campaign_fact():
            rejected.append(claim_id)
            return None
        return claim

    accepted: list[GraphClaim] = []
    rejected: list[str] = []
    inferences: list[InferenceReference] = []
    warnings: list[str] = []
    reason_codes: list[str] = []
    accepted_texts: list[str] = []
    opened_reads = {
        read.source_read_id
        for read in session.source_reads
        if read.outcome in {"enough", "partial", "truncated"}
    }

    if not parsed.sections and model_prose and model_prose.strip():
        factual = [
            claim
            for claim in session.claims
            if current_factual_claim(claim.claim_id) is not None
        ]
        if factual:
            citations = _source_citations_from_session(session)
            refs = _graph_refs_for_claims(
                factual,
                revision_id=session.snapshot.revision_id,
            )
            unreadable = any(
                (not anchor.readable) and (not anchor.opened)
                for anchor in session.source_anchors
            )
            synthesis_reasons = [
                "graph_context_synthesis",
                "sentence_level_grounding_unvalidated",
                "hermes_agent_answer",
            ]
            if unreadable:
                warnings.append(PARTIAL_SOURCE_WARNING)
                synthesis_reasons.append("source_anchor_unreadable")
            if citations:
                outcome = "source_verified"
            elif unreadable:
                outcome = "partial_coverage"
            else:
                outcome = "graph_grounded"
            return ValidatedAnswer(
                outcome=outcome,
                answer_text=model_prose.strip(),
                accepted_claim_ids=[claim.claim_id for claim in factual],
                rejected_claim_ids=list(dict.fromkeys(rejected)),
                graph_references=refs,
                source_citations=citations,
                warnings=list(dict.fromkeys(warnings)),
                diagnostic_codes=list(dict.fromkeys(synthesis_reasons)),
                reason_codes=list(dict.fromkeys(synthesis_reasons)),
                support_claim_ledger_text=_claim_ledger_text(factual),
                answer_authority="graph_context_synthesis",
                validator_path="graph_context_synthesis",
            )

    for section in parsed.sections:
        if section.statement_kind == "suggestion":
            accepted_texts.append(section.text)
            reason_codes.append("suggestion_noncanonical")
            continue
        if section.statement_kind == "gap":
            accepted_texts.append(section.text)
            reason_codes.append("named_gap")
            continue
        if section.statement_kind == "inference":
            valid_premises = [
                claim.claim_id
                for cid in section.supporting_claim_ids
                if (claim := current_factual_claim(cid)) is not None
            ]
            if not valid_premises:
                rejected.extend(section.supporting_claim_ids)
                reason_codes.append("inference_missing_premises")
                continue
            inference_id = section.inference_id or f"turn-local:{len(inferences) + 1}"
            inferences.append(
                InferenceReference(
                    inference_id=inference_id,
                    text=section.text,
                    supporting_claim_ids=valid_premises,
                )
            )
            accepted_texts.append(f"[Hermes inference] {section.text}")
            continue

        # graph_fact / source_detail
        section_claims: list[GraphClaim] = []
        for claim_id in section.supporting_claim_ids:
            claim = current_factual_claim(claim_id)
            if claim is not None:
                section_claims.append(claim)
        if section.statement_kind == "source_detail":
            if not any(rid in opened_reads for rid in section.source_read_ids):
                warnings.append(PARTIAL_SOURCE_WARNING)
                reason_codes.append("source_detail_without_open_read")
                # Keep graph paraphrase if claims exist; do not cite source.
            elif not section_claims:
                rejected.extend(section.supporting_claim_ids)
                continue
        if not section_claims and section.statement_kind == "graph_fact":
            reason_codes.append("unsupported_graph_fact_removed")
            continue
        accepted.extend(section_claims)
        accepted_texts.append(section.text)
        for claim in section_claims:
            claim.used_in_answer = True

    accepted_unique = list({c.claim_id: c for c in accepted}.values())
    citations = _source_citations_from_session(session)
    refs = _graph_refs_for_claims(
        accepted_unique,
        revision_id=session.snapshot.revision_id,
    )

    unreadable = any(
        (not a.readable) and (not a.opened) for a in session.source_anchors
    )
    if accepted_unique and unreadable:
        warnings.append(PARTIAL_SOURCE_WARNING)
        reason_codes.append("source_anchor_unreadable")

    if not accepted_unique and not inferences:
        if (
            answer_scope == "conversation_context"
            and model_prose
            and model_prose.strip()
        ):
            return ValidatedAnswer(
                outcome="conversation_context",
                answer_text=model_prose.strip(),
                rejected_claim_ids=list(dict.fromkeys(rejected)),
                warnings=list(dict.fromkeys(warnings)),
                diagnostic_codes=[],
                reason_codes=["explicit_conversation_context", *reason_codes],
                validator_path="explicit_conversation_context",
            )
        return ValidatedAnswer(
            outcome="abstained",
            answer_text=ABSTENTION_ANSWER,
            rejected_claim_ids=list(dict.fromkeys(rejected)),
            warnings=warnings,
            diagnostic_codes=["hermes_insufficient_evidence"],
            reason_codes=["no_admissible_claims", *reason_codes],
            answer_authority="abstained",
            validator_path="claim_ledger_validation",
        )

    if citations and accepted_unique:
        outcome = "source_verified"
    elif unreadable and accepted_unique:
        outcome = "partial_coverage"
    elif inferences and not accepted_unique:
        outcome = "inferred_from_graph"
    else:
        outcome = "graph_grounded"

    answer_text = "\n\n".join(text for text in accepted_texts if text.strip())
    if not answer_text.strip() and accepted_unique:
        answer_text = _claim_ledger_text(accepted_unique) or ""
    if model_prose and model_prose.strip() in accepted_texts:
        reason_codes.append("hermes_agent_answer")

    return ValidatedAnswer(
        outcome=outcome,
        answer_text=answer_text,
        accepted_claim_ids=[c.claim_id for c in accepted_unique],
        rejected_claim_ids=list(dict.fromkeys(rejected)),
        graph_references=refs,
        source_citations=citations,
        inferences=inferences,
        warnings=list(dict.fromkeys(warnings)),
        diagnostic_codes=list(dict.fromkeys(reason_codes)),
        reason_codes=list(dict.fromkeys(reason_codes)),
        support_claim_ledger_text=_claim_ledger_text(accepted_unique),
        answer_authority="graph_grounded",
        validator_path="claim_ledger_validation",
    )


__all__ = [
    "ABSTENTION_ANSWER",
    "AnswerAuthority",
    "HERMES_NO_CHAT_ANSWER",
    "AnswerSection",
    "StructuredAnswerDraft",
    "ValidatedAnswer",
    "synthesize_draft_from_session",
    "validate_structured_answer",
]
