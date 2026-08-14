"""Score Hermes small-slice turns against gold packets (no LLM judge)."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _tool_names(tool_events: Sequence[Mapping[str, Any]] | None) -> list[str]:
    names: list[str] = []
    for event in tool_events or []:
        name = event.get("tool_name") or event.get("toolName") or event.get("name")
        if isinstance(name, str) and name:
            names.append(name)
    return names


def _opened_citation_count(result: Mapping[str, Any]) -> int:
    acceptance = result.get("acceptance") or {}
    if isinstance(acceptance, Mapping):
        opened = acceptance.get("source_citations_opened")
        if isinstance(opened, int):
            return opened
        cites = acceptance.get("source_citations") or acceptance.get("sourceCitations") or []
        if isinstance(cites, list):
            return sum(
                1
                for c in cites
                if isinstance(c, Mapping) and (c.get("opened") is True or c.get("status") == "opened")
            )
    trace = result.get("agent_trace") or result.get("agentTrace") or {}
    if isinstance(trace, Mapping):
        opened = trace.get("source_citations_opened")
        if isinstance(opened, int):
            return opened
    return int(result.get("source_citations_opened") or 0)


def _accepted_claim_ids(result: Mapping[str, Any]) -> list[str]:
    acceptance = result.get("acceptance") or {}
    if isinstance(acceptance, Mapping):
        ids = acceptance.get("accepted_claim_ids") or acceptance.get("acceptedClaimIds") or []
        if isinstance(ids, list):
            return [str(x) for x in ids if x]
    ids = result.get("accepted_claim_ids") or []
    return [str(x) for x in ids] if isinstance(ids, list) else []


def _mutations(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = result.get("mutations") or []
    if not isinstance(raw, list):
        return []
    return [m for m in raw if isinstance(m, Mapping)]


def _canvas_proposals(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    out: list[Mapping[str, Any]] = []
    for mut in _mutations(result):
        schema = str(mut.get("schema") or "")
        if "canvas_block_proposal" in schema or mut.get("kind") in {
            "gm-note",
            "read-aloud",
            "rules",
            "warning",
        }:
            out.append(mut)
            continue
        payload = mut.get("proposal") or mut.get("payload") or mut
        if isinstance(payload, Mapping) and (
            payload.get("kind") in {"gm-note", "read-aloud", "rules", "warning"}
            or "canvas" in str(payload.get("schema") or "")
        ):
            out.append(payload if isinstance(payload, Mapping) else mut)
    return out


def score_bucket_hints(answer: str, hints: Sequence[str]) -> bool:
    text = _norm(answer)
    if not hints:
        return False
    hits = sum(1 for h in hints if _norm(str(h)) in text)
    return hits >= max(1, min(2, len(hints) // 3 + 1))


def score_trial(
    *,
    gold: Mapping[str, Any],
    question: Mapping[str, Any],
    answer: str,
    tool_events: Sequence[Mapping[str, Any]] | None,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    tools = _tool_names(tool_events)
    source_reads = sum(1 for t in tools if t == "read_graph_source")
    expands = sum(1 for t in tools if t == "expand_graph_retrieval")
    opened = _opened_citation_count(result)
    claim_ids = _accepted_claim_ids(result)
    proposals = _canvas_proposals(result)
    answer_norm = _norm(answer)

    source_required = bool(question.get("source_read_required"))
    source_ok = (not source_required) or (source_reads >= 1 and opened >= 1) or (
        source_required and source_reads >= 1
    )
    # Prefer opened citations when available; allow tool call alone as structural
    # signal when acceptance projection omits opened count.
    if source_required and source_reads >= 1:
        source_ok = True

    expected_subs = list(gold.get("expected_claim_id_substrings") or [])
    claim_blob = " ".join(claim_ids).lower()
    claims_ok = all(sub.lower() in claim_blob for sub in expected_subs) if expected_subs else True

    forbidden_hits: list[str] = []
    for rule in gold.get("must_not") or []:
        if not isinstance(rule, Mapping):
            continue
        for s in rule.get("forbidden_substrings") or []:
            if _norm(str(s)) and _norm(str(s)) in answer_norm:
                forbidden_hits.append(str(rule.get("id") or s))
                break

    bucket_hints = gold.get("bucket_term_hints") or {}
    bucket_scores: dict[str, bool] = {}
    for bucket in question.get("required_buckets") or []:
        hints = bucket_hints.get(bucket) or []
        bucket_scores[str(bucket)] = score_bucket_hints(answer, hints)
    optional_scores: dict[str, bool] = {}
    for bucket in question.get("optional_buckets") or []:
        hints = bucket_hints.get(bucket) or []
        optional_scores[str(bucket)] = score_bucket_hints(answer, hints)

    required_bucket_pass = all(bucket_scores.values()) if bucket_scores else True

    canvas_ok = True
    canvas_detail: dict[str, Any] = {"expected": bool(question.get("expect_canvas_proposal"))}
    if question.get("expect_canvas_proposal"):
        kind = question.get("expected_canvas_kind") or "gm-note"
        matching = [
            p
            for p in proposals
            if str(p.get("kind") or p.get("blockKind") or "") == kind
            or str((p.get("block") or {}).get("kind") if isinstance(p.get("block"), Mapping) else "")
            == kind
        ]
        canvas_ok = len(matching) >= 1
        canvas_detail["found"] = len(proposals)
        canvas_detail["matching_kind"] = len(matching)
        if matching and question.get("expected_provenance_refs"):
            refs_blob = _norm(str(matching[0].get("provenanceRefs") or matching[0].get("provenance_refs") or ""))
            missing = [
                r
                for r in question["expected_provenance_refs"]
                if _norm(str(r)) not in refs_blob
            ]
            canvas_detail["missing_provenance"] = missing
            # Provenance soft: do not fail structural solely on refs if proposal exists.
    else:
        canvas_detail["found"] = len(proposals)

    # Gate hygiene: authoring must not propose read-aloud that is only about metal leaves.
    gate_hygiene_ok = True
    if question.get("expect_canvas_proposal"):
        for p in proposals:
            kind = str(p.get("kind") or p.get("blockKind") or "")
            body = _norm(str(p.get("markdown") or p.get("text") or p.get("body") or ""))
            if kind == "read-aloud" and "metal" in body and "leaves" in body:
                gate_hygiene_ok = False
                break

    structural_pass = (
        source_ok
        and claims_ok
        and not forbidden_hits
        and canvas_ok
        and gate_hygiene_ok
    )

    return {
        "structural_pass": structural_pass,
        "source_read_required": source_required,
        "source_ok": source_ok,
        "source_reads": source_reads,
        "expands": expands,
        "opened_citations": opened,
        "claims_ok": claims_ok,
        "accepted_claim_ids": claim_ids,
        "forbidden_hits": forbidden_hits,
        "bucket_scores": bucket_scores,
        "optional_bucket_scores": optional_scores,
        "required_bucket_pass": required_bucket_pass,
        "canvas_ok": canvas_ok,
        "canvas_detail": canvas_detail,
        "gate_hygiene_ok": gate_hygiene_ok,
        "tools": tools,
        "expand_ready_candidate": structural_pass and required_bucket_pass,
    }


def aggregate_question_trials(trial_scores: Sequence[Mapping[str, Any]], *, threshold_pass: int = 2) -> dict[str, Any]:
    n = len(trial_scores)
    structural = sum(1 for t in trial_scores if t.get("structural_pass"))
    buckets = sum(1 for t in trial_scores if t.get("required_bucket_pass"))
    expand_ready = sum(1 for t in trial_scores if t.get("expand_ready_candidate"))
    return {
        "trials": n,
        "structural_passes": structural,
        "structural_ok": structural >= min(threshold_pass, n) if n else False,
        "bucket_passes": buckets,
        "expand_ready_passes": expand_ready,
        "expand_ready_ok": expand_ready >= min(threshold_pass, n) if n else False,
    }


__all__ = [
    "aggregate_question_trials",
    "score_bucket_hints",
    "score_trial",
]
