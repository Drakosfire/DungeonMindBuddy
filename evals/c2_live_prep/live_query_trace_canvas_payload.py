"""Normalize live-query trace JSON artifacts into a compact canvas payload."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_CLIP = 420
_PROMPT_CLIP = 900
_EXCERPT_CLIP = 280


def _clip(text: str, limit: int = _CLIP) -> str:
    s = (text or "").strip()
    if len(s) <= limit:
        return s
    return s[: limit - 1] + "…"


def _basename(path: str) -> str:
    return Path(path.replace("\\", "/")).name


def _session_from_path(path: str) -> int | None:
    m = re.search(r"Session\s+(\d+)", path, flags=re.I)
    return int(m.group(1)) if m else None


def _compact_evidence(row: dict[str, Any]) -> dict[str, Any]:
    path = str(row.get("path") or "")
    return {
        "evidence_id": str(row.get("evidence_id") or ""),
        "path": path,
        "path_basename": _basename(path),
        "session": _session_from_path(path),
        "source_role": str(row.get("source_role") or ""),
        "authority": str(row.get("authority") or ""),
        "line_start": row.get("line_start"),
        "line_end": row.get("line_end"),
        "final_score": row.get("final_score") or row.get("score"),
        "text_excerpt": _clip(str(row.get("text_excerpt") or ""), _EXCERPT_CLIP),
        "reason_code": str(row.get("reason_code") or row.get("admission_reason") or ""),
    }


def _compact_manifest_entry(row: dict[str, Any]) -> dict[str, Any]:
    path = str(row.get("route") or row.get("path") or "")
    comps = row.get("score_components") if isinstance(row.get("score_components"), dict) else {}
    return {
        "route_basename": _basename(path),
        "source_role": str(row.get("source_role") or ""),
        "session_scope": list(row.get("session_scope") or []),
        "final_score": row.get("final_score"),
        "session_scope_score": comps.get("session_scope_score"),
        "source_role_score": comps.get("source_role_score"),
        "exact_title_match_score": comps.get("exact_title_match_score"),
    }


def _compact_span_or_unit(row: dict[str, Any]) -> dict[str, Any]:
    path = str(row.get("path") or "")
    return {
        "path_basename": _basename(path),
        "source_role": str(row.get("source_role") or ""),
        "session": _session_from_path(path),
        "line_start": row.get("line_start"),
        "line_end": row.get("line_end"),
        "unit_id": str(row.get("unit_id") or "") or None,
        "final_score": row.get("final_score"),
        "text_excerpt": _clip(str(row.get("text_excerpt") or ""), _EXCERPT_CLIP),
    }


def assess_session22_quality(*, question: str, answer: str, citations: list[dict[str, Any]]) -> dict[str, Any]:
    q = (question or "").lower()
    a = (answer or "").lower()
    if "session 22" not in q and "s22" not in q:
        return {"label": "unknown", "session22_closing_beat_signal": False, "conical_hill_drift_signal": False}

    closing_tokens = ("lysandro", "lysandra", "lieutenant lysandra", "met her father")
    drift_tokens = ("conical hill", "giant bowl", "drake nest")
    closing_hit = any(tok in a for tok in closing_tokens)
    drift_hit = any(tok in a for tok in drift_tokens)

    cited_sessions = {_session_from_path(str(c.get("path") or "")) for c in citations}
    cited_sessions.discard(None)
    cites_s21 = 21 in cited_sessions
    cites_s22 = 22 in cited_sessions

    if closing_hit and (cites_s22 or not cites_s21):
        label = "aligned"
    elif drift_hit or (cites_s21 and not cites_s22):
        label = "drift"
    else:
        label = "unknown"

    return {
        "label": label,
        "session22_closing_beat_signal": closing_hit,
        "conical_hill_drift_signal": drift_hit or (cites_s21 and not cites_s22),
        "cited_sessions": sorted(cited_sessions),
    }


def _is_telemetry_trace(raw: dict[str, Any]) -> bool:
    return isinstance(raw.get("step_2_context_packet"), dict)


def _from_telemetry(raw: dict[str, Any], *, artifact_path: Path | str) -> dict[str, Any]:
    step1 = raw.get("step_1_query_enhancement") if isinstance(raw.get("step_1_query_enhancement"), dict) else {}
    step1_result = step1.get("result") if isinstance(step1.get("result"), dict) else {}
    step2 = raw.get("step_2_context_packet") if isinstance(raw.get("step_2_context_packet"), dict) else {}
    step3 = raw.get("step_3_answer_llm") if isinstance(raw.get("step_3_answer_llm"), dict) else {}
    step4 = raw.get("step_4_validation_and_decision") if isinstance(raw.get("step_4_validation_and_decision"), dict) else {}
    step4_final = step4.get("final") if isinstance(step4.get("final"), dict) else {}

    llm_cfg = raw.get("llm_config") if isinstance(raw.get("llm_config"), dict) else {}
    citations = list((step4.get("citation_validation") or {}).get("citations") or [])

    answer = str(step4_final.get("answer") or step3.get("response_output_text") or "")
    question = str(raw.get("question") or step1_result.get("original_question") or "")

    top_admitted = [_compact_evidence(x) for x in list(step2.get("top_admitted") or [])[:8]]
    top_rejected = [_compact_evidence(x) for x in list(step2.get("top_rejected") or [])[:8]]

    req = step1.get("request") if isinstance(step1.get("request"), dict) else {}
    prompt_excerpt = _clip(str(req.get("input") or ""), _PROMPT_CLIP)
    ans_req = step3.get("request") if isinstance(step3.get("request"), dict) else {}
    answer_prompt_excerpt = _clip(str(ans_req.get("input") or step3.get("rendered_prompt") or ""), _PROMPT_CLIP)

    return {
        "artifact_path": str(Path(artifact_path).as_posix()),
        "artifact_basename": Path(artifact_path).name,
        "format": "telemetry",
        "question": question,
        "target_session": raw.get("target_session"),
        "manifest_path": str(raw.get("manifest_path") or ""),
        "llm_model": str(llm_cfg.get("model") or req.get("model") or ""),
        "status": str(step4_final.get("status") or "unknown"),
        "grounding_answer_source": str(step4_final.get("grounding_answer_source") or ""),
        "warnings": list(step4.get("warnings") or []),
        "quality": assess_session22_quality(question=question, answer=answer, citations=citations),
        "enhancement": {
            "source": str(step1_result.get("source") or step1.get("source") or ""),
            "effective_question": str(step1_result.get("effective_question") or step2.get("retrieval_query") or ""),
            "response_output_text": _clip(str(step1.get("response_output_text") or ""), _PROMPT_CLIP),
            "prompt_excerpt": prompt_excerpt,
        },
        "retrieval": {
            "retrieval_query": str(step2.get("retrieval_query") or ""),
            "admitted_count": int(step2.get("admitted_count") or len(top_admitted)),
            "rejected_count": int(step2.get("rejected_count") or len(top_rejected)),
            "top_admitted": top_admitted,
            "top_rejected": top_rejected,
            "retrieval_trace_summary": None,
        },
        "answer": {
            "text": answer,
            "prompt_excerpt": answer_prompt_excerpt,
            "response_output_text": _clip(str(step3.get("response_output_text") or ""), _PROMPT_CLIP),
        },
        "citations": [_compact_evidence(c) for c in citations],
        "cited_evidence_ids": [str(c.get("evidence_id") or "") for c in citations if c.get("evidence_id")],
    }


def _from_response_trace(raw: dict[str, Any], *, artifact_path: Path | str) -> dict[str, Any]:
    packet = raw.get("context_packet") if isinstance(raw.get("context_packet"), dict) else {}
    trace = packet.get("retrieval_trace") if isinstance(packet.get("retrieval_trace"), dict) else {}

    citations = list(raw.get("citations") or [])
    answer = str(raw.get("answer") or "")
    question = str(raw.get("question") or trace.get("question") or "")

    admitted = [_compact_evidence(x) for x in list(packet.get("admitted_evidence") or [])[:10]]
    rejected = [_compact_evidence(x) for x in list(packet.get("rejected_evidence") or [])[:8]]

    trace_summary = {
        "asks_for_last_or_final": bool(trace.get("asks_for_last_or_final")),
        "asks_for_play_event": bool(trace.get("asks_for_play_event")),
        "session_numbers": list(trace.get("session_numbers") or []),
        "top_manifest_entries": [
            _compact_manifest_entry(x) for x in list(trace.get("top_manifest_entries") or [])[:8]
        ],
        "top_markdown_spans": [_compact_span_or_unit(x) for x in list(trace.get("top_markdown_spans") or [])[:6]],
        "top_session_memory_units": [
            _compact_span_or_unit(x) for x in list(trace.get("top_session_memory_units") or [])[:6]
        ],
        "admitted_ranked": [_compact_evidence(x) for x in list(trace.get("admitted_evidence") or [])[:10]],
        "rejected_ranked": [_compact_evidence(x) for x in list(trace.get("rejected_evidence") or [])[:8]],
    }

    return {
        "artifact_path": str(Path(artifact_path).as_posix()),
        "artifact_basename": Path(artifact_path).name,
        "format": "response_trace",
        "question": question,
        "manifest_path": "",
        "llm_model": "",
        "status": "ok" if answer.strip() else "empty",
        "grounding_answer_source": "unknown",
        "warnings": list(raw.get("warnings") or []),
        "quality": assess_session22_quality(question=question, answer=answer, citations=citations),
        "enhancement": {
            "source": "",
            "effective_question": "",
            "response_output_text": "",
            "prompt_excerpt": "",
        },
        "retrieval": {
            "retrieval_query": str(trace.get("question") or question),
            "admitted_count": len(packet.get("admitted_evidence") or []),
            "rejected_count": len(packet.get("rejected_evidence") or []),
            "top_admitted": admitted[:8],
            "top_rejected": rejected[:8],
            "retrieval_trace_summary": trace_summary,
        },
        "answer": {
            "text": answer,
            "prompt_excerpt": "",
            "response_output_text": "",
        },
        "citations": [_compact_evidence(c) for c in citations],
        "cited_evidence_ids": [str(c.get("evidence_id") or "") for c in citations if c.get("evidence_id")],
    }


def build_payload(raw: dict[str, Any], *, artifact_path: Path | str) -> dict[str, Any]:
    if _is_telemetry_trace(raw):
        payload = _from_telemetry(raw, artifact_path=artifact_path)
    else:
        payload = _from_response_trace(raw, artifact_path=artifact_path)

    payload["transition_rows"] = _transition_rows(payload)
    return payload


def build_query_summary(detail: dict[str, Any]) -> dict[str, Any]:
    ret = detail.get("retrieval") if isinstance(detail.get("retrieval"), dict) else {}
    enh = detail.get("enhancement") if isinstance(detail.get("enhancement"), dict) else {}
    ans = detail.get("answer") if isinstance(detail.get("answer"), dict) else {}
    quality = detail.get("quality") if isinstance(detail.get("quality"), dict) else {}
    answer_text = str(ans.get("text") or "")
    return {
        "question": str(detail.get("question") or ""),
        "target_session": detail.get("target_session"),
        "artifact_path": str(detail.get("artifact_path") or ""),
        "artifact_basename": str(detail.get("artifact_basename") or ""),
        "format": str(detail.get("format") or ""),
        "status": str(detail.get("status") or ""),
        "quality_label": str(quality.get("label") or "unknown"),
        "admitted_count": int(ret.get("admitted_count") or 0),
        "rejected_count": int(ret.get("rejected_count") or 0),
        "citation_count": len(list(detail.get("citations") or [])),
        "answer_preview": _clip(answer_text, 220),
        "warnings": list(detail.get("warnings") or []),
        "has_enhancement": bool(str(enh.get("source") or "").strip()),
        "llm_model": str(detail.get("llm_model") or ""),
    }


def build_multi_query_canvas_payload(
    entries: list[tuple[dict[str, Any], bool]],
) -> dict[str, Any]:
    """Build canvas payload. Tuple bool is ``default_expanded`` for accordion rows."""
    queries: list[dict[str, Any]] = []
    for idx, (detail, default_expanded) in enumerate(entries):
        summary = build_query_summary(detail)
        slug = re.sub(r"[^a-z0-9]+", "-", summary["question"].lower()).strip("-")[:48] or f"query-{idx + 1}"
        queries.append(
            {
                "query_id": slug,
                "default_expanded": default_expanded,
                "summary": summary,
                "detail": detail,
            }
        )
    return {"queries": queries}


def _transition_rows(payload: dict[str, Any]) -> list[list[str]]:
    enh = payload.get("enhancement") if isinstance(payload.get("enhancement"), dict) else {}
    ret = payload.get("retrieval") if isinstance(payload.get("retrieval"), dict) else {}
    ans = payload.get("answer") if isinstance(payload.get("answer"), dict) else {}
    rows = [
        ["0. Input", payload.get("question") or "", "process_live_query", "question"],
        [
            "1. Query enhancement",
            _clip(str(enh.get("prompt_excerpt") or ""), 180),
            "query_enhancement_llm",
            f"source={enh.get('source') or 'n/a'}",
        ],
        [
            "2. Retrieval",
            _clip(str(ret.get("retrieval_query") or ""), 180),
            "build_context_packet",
            f"admitted={ret.get('admitted_count')}, rejected={ret.get('rejected_count')}",
        ],
        [
            "3. Grounded answer",
            _clip(str(ans.get("prompt_excerpt") or ans.get("text") or ""), 180),
            "llm_grounded_answer",
            f"format={payload.get('format')}",
        ],
        [
            "4. Citations + gate",
            ", ".join(payload.get("cited_evidence_ids") or []) or "none",
            "citation_validation",
            f"status={payload.get('status')}, quality={payload.get('quality', {}).get('label')}",
        ],
    ]
    return rows


def load_trace_payload(path: Path | str) -> dict[str, Any]:
    artifact_path = Path(path)
    raw = __import__("json").loads(artifact_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"trace artifact must be a JSON object: {artifact_path}")
    return build_payload(raw, artifact_path=artifact_path)
