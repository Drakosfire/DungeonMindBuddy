#!/usr/bin/env python3
"""Run a live-query pipeline and emit step-by-step telemetry JSON.

Reuses query enhancement (step 1) from a prior telemetry artifact when
``--enhancement-from`` is set; otherwise runs retrieval + grounding on the
raw question only.

Example::

  uv run python -m evals.c2_live_prep.run_live_query_telemetry_trace \\
    --enhancement-from evals/c2_live_prep/artifacts/runs/2026-06-01/live_query_trace_session22_fresh_ingested_lexical.json \\
    --output evals/c2_live_prep/artifacts/runs/2026-06-01/live_query_trace_session22_tuned_telemetry.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.synthesis import _load_api_key  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402
from src.live_play.live_query_context import (  # noqa: E402
    _build_citations,
    _default_query_config,
    _extract_answer_text,
    assign_evidence_ids,
    render_grounded_prompt,
)
from src.live_play.manifest_context_query import (  # noqa: E402
    QueryRequest,
    build_context_packet,
    infer_session_numbers,
    load_manifest,
)

_DEFAULT_MANIFEST = "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"
_DEFAULT_ENHANCEMENT = (
    "evals/c2_live_prep/artifacts/runs/2026-06-01/"
    "live_query_trace_session22_fresh_ingested_lexical.json"
)
_DEFAULT_QUESTION = "what was the last thing that happened in Session 22"
_DOGFOOD_DEFAULTS_ENV = "DMB_C2S23_DOGFOOD_DEFAULTS"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compact_admitted(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": row.get("evidence_id"),
        "path": row.get("path"),
        "source_role": row.get("source_role"),
        "authority": row.get("authority"),
        "line_start": row.get("line_start"),
        "line_end": row.get("line_end"),
        "text_excerpt": row.get("text_excerpt"),
    }


def _compact_rejected(row: dict[str, Any]) -> dict[str, Any]:
    ev = dict(row.get("evidence") or {})
    return {
        "evidence_id": ev.get("evidence_id"),
        "reason_code": row.get("reason_code"),
        "source_role": ev.get("source_role"),
        "authority": ev.get("authority"),
        "path": ev.get("path"),
    }


def _aliases_from_step1(step1: dict[str, Any]) -> list[str]:
    for diag in list((step1.get("result") or {}).get("diagnostics") or []):
        if isinstance(diag, dict) and diag.get("aliases"):
            return [str(a) for a in diag["aliases"]]
    return []


def _scoped_retrieval_question(question: str, session: int | None) -> str:
    q = question.strip()
    if session is None:
        return q
    if session in infer_session_numbers(q):
        return q
    return f"Session {session} canon play recap: {q}"


def _retrieval_question(
    step1: dict[str, Any] | None,
    *,
    fallback: str,
    session: int | None,
) -> tuple[str, str]:
    if not step1:
        scoped = _scoped_retrieval_question(fallback, session)
        return scoped, scoped
    result = step1.get("result") if isinstance(step1.get("result"), dict) else {}
    base = str(result.get("effective_question") or fallback).strip()
    if "aliases:" in base.lower():
        return base, base
    aliases = _aliases_from_step1(step1)
    if aliases:
        with_aliases = f"{base} Aliases: {', '.join(aliases)}."
        return base, with_aliases
    return base, base


def _render_grounded_prompt_with_citation_rule(question: str, packet: dict[str, Any]) -> str:
    prompt = render_grounded_prompt(question, packet)
    extra = "Every factual campaign claim in your answer must include at least one admitted evidence citation."
    if extra not in prompt:
        prompt = prompt.replace(
            "Rules:\n- ",
            f"Rules:\n- {extra}\n- ",
            1,
        )
    return prompt


def _run_llm_step(
    *,
    question: str,
    packet: dict[str, Any],
    llm_config: dict[str, Any],
) -> dict[str, Any]:
    model = str(llm_config.get("model") or "gpt-5.4-mini").strip()
    temperature = float(llm_config.get("temperature") or 0.2)
    max_output_tokens = int(llm_config.get("max_output_tokens") or 600)
    prompt = _render_grounded_prompt_with_citation_rule(question, packet)

    request_payload = {
        "model": model,
        "input": prompt,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        return {
            "request": request_payload,
            "response_output_text": "",
            "result": {
                "answer": None,
                "source": "none",
                "warnings": ["llm_api_key_missing"],
                "diagnostics": [{"code": "llm_api_key_missing"}],
            },
            "rendered_prompt": prompt,
        }

    from openai import OpenAI

    try:
        client = OpenAI()
        response = client.responses.create(
            model=model,
            input=prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
    except Exception as exc:
        return {
            "request": request_payload,
            "response_output_text": "",
            "result": {
                "answer": None,
                "source": "none",
                "warnings": ["llm_grounding_call_failed"],
                "diagnostics": [{"code": "llm_grounding_call_failed", "error_type": type(exc).__name__}],
            },
            "rendered_prompt": prompt,
        }

    answer = _extract_answer_text(response)
    output_text = answer or ""
    if not answer:
        return {
            "request": request_payload,
            "response_output_text": output_text,
            "result": {
                "answer": None,
                "source": "none",
                "warnings": ["llm_empty_answer_fallback_used"],
                "diagnostics": [{"code": "llm_empty_answer_fallback_used"}],
            },
            "rendered_prompt": prompt,
        }

    return {
        "request": request_payload,
        "response_output_text": output_text,
        "result": {
            "answer": answer,
            "source": "llm",
            "warnings": [],
            "diagnostics": [],
        },
        "rendered_prompt": prompt,
    }


def _citation_diagnostics(answer: str, packet: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    from src.live_play.live_query_context import _extract_cited_evidence_ids

    cited = _extract_cited_evidence_ids(answer)
    admitted_by_id = {
        str(row.get("evidence_id") or ""): row
        for row in list(packet.get("admitted_evidence") or [])
        if row.get("evidence_id")
    }
    rejected_ids = {
        str(row.get("evidence", {}).get("evidence_id") or "")
        for row in list(packet.get("rejected_evidence") or [])
        if row.get("evidence", {}).get("evidence_id")
    }
    citations, citation_warnings = _build_citations(answer, packet)
    unknown_ids = sorted(eid for eid in cited if eid not in admitted_by_id and eid not in rejected_ids)
    cited_rejected_ids = sorted(eid for eid in cited if eid in rejected_ids)
    diagnostics = {
        "cited_evidence_ids": cited,
        "admitted_citation_ids": [c["evidence_id"] for c in citations],
        "unknown_citation_ids": unknown_ids,
        "rejected_citation_ids": cited_rejected_ids,
    }
    return citations, citation_warnings, diagnostics


def _build_step4(
    *,
    answer: str,
    answer_source: str,
    citations: list[dict[str, Any]],
    citation_warnings: list[str],
    citation_diagnostics: dict[str, Any],
    llm_warnings: list[str],
) -> dict[str, Any]:
    llm_citation_failure = bool(
        [w for w in (llm_warnings + citation_warnings) if w.startswith("llm_") or w == "ungrounded_answer_missing_citations"]
    )
    status = "ok" if answer_source == "llm" and not llm_citation_failure else "llm_grounding_failed"
    if answer_source == "llm" and not llm_citation_failure:
        decision = "accept_answer"
    else:
        decision = "reject_or_fallback"

    return {
        "warnings": llm_warnings + citation_warnings,
        "decision_steps": [
            {
                "step": "citation_validation",
                "llm_citation_failure": llm_citation_failure,
                "citation_warnings": citation_warnings,
                "citation_diagnostics": citation_diagnostics,
            },
            {
                "step": "acceptance_gate",
                "decision": decision,
                "status": status if decision != "accept_answer" else "ok",
                "answer_source": answer_source,
            },
        ],
        "citation_validation": {
            "citations": citations,
            "warnings": citation_warnings,
            "diagnostics": citation_diagnostics,
        },
        "final": {
            "status": "ok" if decision == "accept_answer" else status,
            "grounding_answer_source": answer_source,
            "answer": answer,
        },
    }


def run_telemetry_trace(
    *,
    question: str,
    manifest_path: Path,
    root: Path,
    enhancement_artifact: dict[str, Any] | None,
    llm_config: dict[str, Any],
    target_session: int | None = None,
) -> dict[str, Any]:
    os.environ[_DOGFOOD_DEFAULTS_ENV] = "1"
    step1 = None
    if enhancement_artifact:
        raw_step1 = enhancement_artifact.get("step_1_query_enhancement")
        if isinstance(raw_step1, dict):
            step1 = raw_step1

    _, retrieval_query = _retrieval_question(step1, fallback=question, session=target_session)
    query_id = f"live-query-{uuid.uuid4().hex[:12]}"
    manifest = load_manifest(manifest_path)
    query_request = QueryRequest(question_id=query_id, question=retrieval_query, category=None)
    context_packet = build_context_packet(
        query_request,
        manifest,
        root=root,
        config=_default_query_config(),
    )
    context_packet = assign_evidence_ids(context_packet)

    admitted = list(context_packet.get("admitted_evidence") or [])
    rejected = list(context_packet.get("rejected_evidence") or [])
    step2 = {
        "retrieval_query": retrieval_query,
        "effective_question": retrieval_query,
        "admitted_count": len(admitted),
        "rejected_count": len(rejected),
        "top_admitted": [_compact_admitted(r) for r in admitted[:5]],
        "top_rejected": [_compact_rejected(r) for r in rejected[:5]],
    }

    step3 = _run_llm_step(question=question, packet=context_packet, llm_config=llm_config)
    step3_result = step3.get("result") if isinstance(step3.get("result"), dict) else {}
    answer = str(step3_result.get("answer") or "")
    answer_source = str(step3_result.get("source") or "none")
    llm_warnings = list(step3_result.get("warnings") or [])

    if not answer:
        from src.live_play.live_query_context import build_fallback_grounded_answer

        answer = build_fallback_grounded_answer(question, context_packet)
        answer_source = "fallback"
        llm_warnings = llm_warnings + ["llm_empty_answer_fallback_used"]

    citations, citation_warnings, citation_diagnostics = _citation_diagnostics(answer, context_packet)
    step4 = _build_step4(
        answer=answer,
        answer_source=answer_source,
        citations=citations,
        citation_warnings=citation_warnings,
        citation_diagnostics=citation_diagnostics,
        llm_warnings=llm_warnings,
    )

    out: dict[str, Any] = {
        "question": question,
        "target_session": target_session,
        "manifest_path": str(manifest_path.relative_to(root)),
        "llm_config": llm_config,
        "generated_at": _utc_now_z(),
        "step_2_context_packet": step2,
        "step_3_answer_llm": step3,
        "step_4_validation_and_decision": step4,
    }
    if step1 is not None:
        out["step_1_query_enhancement"] = step1
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", type=str, default=_DEFAULT_QUESTION)
    parser.add_argument(
        "--session",
        type=int,
        default=None,
        help="Scope retrieval to this session when the question omits an explicit session number.",
    )
    parser.add_argument("--manifest-path", type=str, default=_DEFAULT_MANIFEST)
    parser.add_argument("--enhancement-from", type=Path, default=Path(_DEFAULT_ENHANCEMENT))
    parser.add_argument(
        "--no-enhancement",
        action="store_true",
        help="Skip step-1 reuse; run retrieval on the raw question only.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evals/c2_live_prep/artifacts/runs" / str(date.today()) / "live_query_trace_session22_tuned_telemetry.json",
    )
    args = parser.parse_args()

    enhancement_artifact: dict[str, Any] | None = None
    llm_config: dict[str, Any] = {
        "provider": "openai",
        "model": "gpt-5.4-mini",
        "require_llm": True,
        "max_output_tokens": 600,
        "temperature": 0.2,
    }
    if not args.no_enhancement and args.enhancement_from.is_file():
        enhancement_artifact = json.loads(args.enhancement_from.read_text(encoding="utf-8"))
        if isinstance(enhancement_artifact.get("llm_config"), dict):
            llm_config = dict(enhancement_artifact["llm_config"])

    manifest_path = (ROOT / args.manifest_path).resolve()
    trace = run_telemetry_trace(
        question=args.question.strip(),
        manifest_path=manifest_path,
        root=ROOT,
        enhancement_artifact=enhancement_artifact,
        llm_config=llm_config,
        target_session=args.session,
    )

    out_path = args.output.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8")

    step4 = trace.get("step_4_validation_and_decision") or {}
    final = step4.get("final") if isinstance(step4.get("final"), dict) else {}
    step2 = trace.get("step_2_context_packet") if isinstance(trace.get("step_2_context_packet"), dict) else {}
    print(
        json.dumps(
            {
                "ok": final.get("status") == "ok",
                "output": str(out_path.relative_to(ROOT)),
                "admitted_count": step2.get("admitted_count"),
                "rejected_count": step2.get("rejected_count"),
                "warnings": step4.get("warnings"),
                "answer_preview": str(final.get("answer") or "")[:240],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if final.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
