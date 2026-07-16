"""Structured answer support validator — claim-class authority, not anchor presence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.interaction.claims import GraphClaim, TurnOutcomeState
from graph_memory.interaction.latest_recap import read_admitted_recap_excerpt
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
    "zero_tool_compatibility",
    "claim_ledger_validation",
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
    # S1 only: server support channel (never join into Hermes chat answer_text).
    support_lag_text: str | None = None
    support_excerpt_text: str | None = None
    validator_path: ValidatorPath | None = None


ABSTENTION_ANSWER = (
    "DungeonBuddy’s World Graph does not currently contain enough admitted evidence "
    "to answer this question reliably."
)
HERMES_NO_CHAT_ANSWER = "Hermes did not return a chat answer for this turn."
PARTIAL_SOURCE_WARNING = (
    "Source verification is unavailable or incomplete for one or more supporting anchors."
)


def _latest_recap_change(session: GraphRetrievalSession) -> Mapping[str, Any] | None:
    raw = session.latest_recap_change
    return raw if isinstance(raw, Mapping) else None


def _corpus_root(corpus_root: Path | None) -> Path:
    if corpus_root is not None:
        return corpus_root.resolve()
    from apps.live_control_server.config import repo_root

    return repo_root().resolve()


def _s1_lag_disclosure_text(context: Mapping[str, Any]) -> str:
    """Server-owned lag / boundary disclosure — never invents campaign movement."""
    latest = context.get("latest_recap") if isinstance(context.get("latest_recap"), Mapping) else {}
    boundary = (
        context.get("comparison_boundary")
        if isinstance(context.get("comparison_boundary"), Mapping)
        else {}
    )
    recap_session = str(latest.get("session_id") or boundary.get("recap_session_id") or "").strip()
    graph_latest = str(boundary.get("graph_latest_session_id") or "").strip()
    revision_id = str(boundary.get("graph_revision_id") or "").strip()
    outcome = str(context.get("outcome") or "unknown").strip()
    diagnostic_codes = [
        str(code).strip()
        for code in (context.get("diagnostic_codes") or [])
        if str(code).strip()
    ]

    if not recap_session:
        return (
            "DungeonBuddy could identify a latest-recap comparison request, but the "
            "admitted latest recap is not available in registry metadata for this campaign."
        )

    lines = [
        f"The latest admitted recap is {recap_session}.",
    ]
    if graph_latest or revision_id:
        boundary_bits: list[str] = []
        if graph_latest:
            boundary_bits.append(f"graph head session {graph_latest}")
        if revision_id:
            boundary_bits.append(f"revision {revision_id}")
        lines.append(
            "Comparison boundary: latest admitted recap to "
            + (" and ".join(boundary_bits) + ".")
        )
    else:
        lines.append(
            "Comparison boundary: latest admitted recap to the current graph head "
            "(graph-head session is unavailable)."
        )

    if outcome == "memory_lag" or bool(context.get("memory_lag")):
        lines.append(
            f"{recap_session} is admitted as a recap source, but it is not yet present "
            "in the durable World Graph head. That is memory lag, not a completed "
            "no-change comparison."
        )
    elif outcome == "no_change":
        lines.append(
            "The completed comparison found no later graph session beyond the latest "
            "admitted recap. That is a completed no-change result for the graph-head "
            "boundary, not an unknown retrieval failure."
        )
    elif outcome == "changed":
        lines.append(
            "The graph head appears to contain post-recap session material, but this "
            "turn still lacks admissible matched graph claims to narrate the movement."
        )
    elif outcome == "source_unavailable":
        lines.append(
            "The latest admitted recap source file is unavailable, so the comparison "
            "cannot be completed from source evidence."
        )
    else:
        lines.append(
            "The latest-recap comparison boundary is incomplete or unknown for this "
            "campaign, so I cannot yet describe what changed."
        )

    if diagnostic_codes:
        lines.append("Diagnostics: " + ", ".join(diagnostic_codes) + ".")
    return "\n\n".join(lines)


def _s1_support_fields(
    context: Mapping[str, Any],
    *,
    corpus_root: Path,
) -> tuple[str, str | None, bool]:
    """Lag disclosure + optional admitted-recap excerpt for the support channel.

    Returns ``(lag_text, excerpt_or_status_text, excerpt_readable)``.
    """
    lag = _s1_lag_disclosure_text(context)
    latest = context.get("latest_recap") if isinstance(context.get("latest_recap"), Mapping) else {}
    source_path = str(latest.get("source_recap_path") or "").strip()
    recap_session = str(latest.get("session_id") or "").strip() or "the latest admitted recap"
    memory_lag = bool(context.get("memory_lag")) or str(context.get("outcome") or "") == "memory_lag"
    if not memory_lag or not source_path:
        return lag, None, False

    excerpt = context.get("admitted_recap_excerpt")
    if not isinstance(excerpt, str) or not excerpt.strip():
        excerpt = read_admitted_recap_excerpt(root=corpus_root, source_recap_path=source_path)
    if isinstance(excerpt, str) and excerpt.strip():
        return (
            lag,
            (
                f"From the admitted {recap_session} recap (source evidence; not yet "
                "durable World Graph memory):\n\n"
                f"{excerpt.strip()}"
            ),
            True,
        )
    return (
        lag,
        (
            f"The admitted {recap_session} recap is registered, but its source "
            "file could not be read for this turn."
        ),
        False,
    )


def _s1_admitted_recap_sections(
    context: Mapping[str, Any],
    *,
    corpus_root: Path,
    model_prose: str | None = None,
) -> list[AnswerSection]:
    """Draft sections for S1 named-gap.

    Hermes chat prose (suggestion) stays separate from the lag gap marker.
    Admitted-recap excerpt is never drafted into chat sections — it belongs
    on ValidatedAnswer.support_* after validation.
    """
    _ = corpus_root  # excerpt is built in _s1_support_fields at validate time
    sections: list[AnswerSection] = []
    agent_text = (model_prose or "").strip()
    if agent_text:
        sections.append(
            AnswerSection(
                text=agent_text,
                statement_kind="suggestion",
            )
        )
    sections.append(
        AnswerSection(
            text=_s1_lag_disclosure_text(context),
            statement_kind="gap",
        )
    )
    return sections


# Back-compat alias used by older tests / imports.
def _s1_gap_answer_text(context: Mapping[str, Any]) -> str:
    return _s1_lag_disclosure_text(context)


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
        elif claim.claim_kind == "attribute":
            object_kind = "assertion"
        else:
            object_kind = "claim"
        refs.append(
            GraphReference(
                revision_id=revision_id,
                object_kind=object_kind,
                object_id=claim.claim_id,
                label=claim.value_text or claim.subject_label,
                claim_id=claim.claim_id,
            )
        )
    return refs


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
    corpus_root: Path | None = None,
) -> StructuredAnswerDraft:
    """Build a deterministic answer draft from factual claims when model prose lacks structure."""
    factual = [c for c in session.claims if c.may_state_as_campaign_fact()]
    sections: list[AnswerSection] = []
    if model_prose and model_prose.strip() and factual:
        sections.append(
            AnswerSection(
                text=model_prose.strip(),
                statement_kind="graph_fact",
                supporting_claim_ids=[c.claim_id for c in factual],
            )
        )
    elif factual:
        bullets = []
        for claim in factual[:12]:
            label = claim.subject_label or claim.subject_node_id or claim.claim_id
            predicate = claim.predicate or claim.claim_kind
            value = claim.value_text or ""
            bullets.append(f"- {label}: {predicate} — {value}".strip(" —"))
        sections.append(
            AnswerSection(
                text="Graph-grounded facts for this turn:\n" + "\n".join(bullets),
                statement_kind="graph_fact",
                supporting_claim_ids=[c.claim_id for c in factual],
            )
        )
    unreadable = [
        a.anchor_id for a in session.source_anchors if (not a.readable) and (not a.opened)
    ]
    # Keep source-verification limits in the validator warning/support channel.
    # They are not frontstage answer prose and should not interrupt a co-GM read.
    latest_recap = _latest_recap_change(session)
    if not factual and latest_recap is not None:
        # Prefer Hermes agent prose when present. Admitted-recap excerpt is for
        # the agent packet; do not replace the chat answer with a raw dump.
        sections.extend(
            _s1_admitted_recap_sections(
                latest_recap,
                corpus_root=_corpus_root(corpus_root),
                model_prose=model_prose,
            )
        )
    known = [c.predicate or c.claim_kind for c in factual]
    missing = ["source verification"] if unreadable else []
    if not factual and latest_recap is not None:
        if bool(latest_recap.get("memory_lag")):
            missing.append("latest_recap_in_graph_head")
        coverage_state = "partial_coverage"
    else:
        coverage_state = (
            "partial_coverage" if missing else ("graph_grounded" if factual else "empty")
        )
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
    corpus_root: Path | None = None,
    tool_call_count: int | None = None,
    answer_scope: ExplicitAnswerScope | None = None,
) -> ValidatedAnswer:
    """Validate a Hermes turn's answer against the shared claim ledger.

    ``tool_call_count`` is the number of graph-retrieval tool events Hermes
    emitted *this turn* (graph retrieval tools only — start/completion/error
    all count). It is ``None`` for callers that do not track this (legacy/direct
    unit-test callers), which always preserves the strict abstain-on-no-claims
    behavior below. Only an explicit ``0`` — meaning the agent itself chose
    not to touch the graph, not that we guessed it didn't need to — can route
    into the ``conversation_context`` outcome instead of abstention.

    ``answer_scope`` is set when Hermes completed ``declare_conversation_context``
    without graph retrieval this turn. Explicit ``conversation_context`` preserves
    model prose only when no graph claims, inferences, or latest-recap named-gap
    evidence were accepted.
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
            validator_path="claim_ledger_validation",
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
            corpus_root=corpus_root,
        )

    by_id = _claims_by_id(session)
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
                cid for cid in section.supporting_claim_ids if cid in by_id and by_id[cid].may_state_as_campaign_fact()
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
            claim = by_id.get(claim_id)
            if claim is None or not claim.may_state_as_campaign_fact():
                rejected.append(claim_id)
                continue
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

    named_gap_only = (
        not accepted_unique
        and not inferences
        and "named_gap" in reason_codes
        and _latest_recap_change(session) is not None
    )
    if not accepted_unique and not inferences and not named_gap_only:
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
        if tool_call_count == 0 and model_prose and model_prose.strip():
            # The agent made zero graph-retrieval tool calls this turn and
            # there is nothing already accepted to ground on — trust its own
            # decision that this question didn't need the graph, rather than
            # discarding its answer with the generic abstention text.
            return ValidatedAnswer(
                outcome="conversation_context",
                answer_text=model_prose.strip(),
                rejected_claim_ids=list(dict.fromkeys(rejected)),
                warnings=list(dict.fromkeys(warnings)),
                diagnostic_codes=[],
                reason_codes=["conversation_context_no_tool_calls", *reason_codes],
                validator_path="zero_tool_compatibility",
            )
        return ValidatedAnswer(
            outcome="abstained",
            answer_text=ABSTENTION_ANSWER,
            rejected_claim_ids=list(dict.fromkeys(rejected)),
            warnings=warnings,
            diagnostic_codes=["hermes_insufficient_evidence"],
            reason_codes=["no_admissible_claims", *reason_codes],
            validator_path="claim_ledger_validation",
        )

    if named_gap_only:
        outcome = "partial_coverage"
        reason_codes.append("latest_recap_memory_lag_disclosed")
        context = _latest_recap_change(session)
        lag_text: str | None = None
        excerpt_text: str | None = None
        if context is not None:
            lag_text, excerpt_text, excerpt_readable = _s1_support_fields(
                context,
                corpus_root=_corpus_root(corpus_root),
            )
            if excerpt_readable:
                reason_codes.append("admitted_recap_source_read")
        agent_text = (model_prose or "").strip()
        if agent_text:
            answer_text = agent_text
            reason_codes.append("suggestion_noncanonical")
            reason_codes.append("hermes_agent_answer")
        else:
            answer_text = HERMES_NO_CHAT_ANSWER
        return ValidatedAnswer(
            outcome=outcome,
            answer_text=answer_text,
            accepted_claim_ids=[],
            rejected_claim_ids=list(dict.fromkeys(rejected)),
            graph_references=[],
            source_citations=[],
            inferences=[],
            warnings=list(dict.fromkeys(warnings)),
            diagnostic_codes=list(dict.fromkeys(reason_codes)),
            reason_codes=list(dict.fromkeys(reason_codes)),
            support_lag_text=lag_text,
            support_excerpt_text=excerpt_text,
            validator_path="claim_ledger_validation",
        )
    elif citations and accepted_unique:
        outcome = "source_verified"
    elif unreadable and accepted_unique:
        outcome = "partial_coverage"
    elif inferences and not accepted_unique:
        outcome = "inferred_from_graph"
    else:
        outcome = "graph_grounded"

    answer_text = "\n\n".join(text for text in accepted_texts if text.strip())
    if not answer_text.strip() and model_prose and accepted_unique:
        answer_text = model_prose.strip()
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
        validator_path="claim_ledger_validation",
    )


__all__ = [
    "ABSTENTION_ANSWER",
    "HERMES_NO_CHAT_ANSWER",
    "AnswerSection",
    "StructuredAnswerDraft",
    "ValidatedAnswer",
    "synthesize_draft_from_session",
    "validate_structured_answer",
]
