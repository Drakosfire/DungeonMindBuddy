from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from src.agent.synthesis import _load_api_key
from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.live_play.classify_live_turn import TurnClassification
from src.live_play.manifest_context_query import (
    QueryConfig,
    QueryRequest,
    build_context_packet,
    load_manifest,
)

_DEFAULT_MANIFEST_PATH = Path("evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json")
_DEFAULT_PRECONDITION_PATHS: dict[str, str] = {
    "canonical_recap_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/"
        "Session 22 - Mireward Road and Lysandro.md"
    ),
    "normalized_recap_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/"
        "Session 22 - Mireward Road and Lysandro.md"
    ),
    "breadcrumb_recap_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/"
        "Session 22 - Mireward Road and Lysandro.breadcrumbed.md"
    ),
    "session_memory_jsonl_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/"
        "Session 22 - Mireward Road and Lysandro.records_meta.jsonl"
    ),
    "session_memory_meta_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/"
        "Session 22 - Mireward Road and Lysandro.records_meta.json"
    ),
    "live_workspace_s23_packet": "evals/c2_live_prep/live/session_23/live_packet.json",
    "activated_manifest": "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json",
}
_DOGFOOD_DEFAULTS_ENV = "DMB_C2S23_DOGFOOD_DEFAULTS"
_DEBUG_GROUNDED_PROMPT_ENV = "DMB_LIVE_QUERY_INCLUDE_GROUNDED_PROMPT"
_REQUIRE_LLM_ENV = "DMB_LIVE_QUERY_REQUIRE_LLM"
_LIVE_QUERY_MODEL_ENV = "DMB_LIVE_QUERY_MODEL"
_LIVE_QUERY_TEMP_ENV = "DMB_LIVE_QUERY_TEMPERATURE"
_LIVE_QUERY_MAX_TOKENS_ENV = "DMB_LIVE_QUERY_MAX_OUTPUT_TOKENS"
_LIVE_QUERY_PROVIDER_ENV = "DMB_LIVE_QUERY_PROVIDER"


@dataclass(frozen=True)
class ContextLookupResult:
    response: dict[str, Any]
    events_to_write: list[dict[str, object]]
    jobs_to_queue: list[dict[str, object]]


@dataclass(frozen=True)
class LiveQueryLLMConfig:
    provider: str
    model: str
    require_llm: bool
    max_output_tokens: int = 600
    temperature: float = 0.2


@dataclass(frozen=True)
class GroundedAnswerResult:
    answer: str | None
    source: Literal["llm", "stub", "fallback", "none"]
    warnings: list[str]
    diagnostics: list[dict[str, Any]]


@dataclass(frozen=True)
class CitationValidationResult:
    citations: list[dict[str, Any]]
    warnings: list[str]
    diagnostics: dict[str, Any]


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_model_policy(root: Path) -> dict[str, Any]:
    candidates = [
        root / "MODEL_POLICY.json",
        root.parent / "MODEL_POLICY.json",
    ]
    for path in candidates:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
    return {}


def _live_query_model(root: Path) -> str:
    policy = _load_model_policy(root)
    models = dict(policy.get("models") or {})
    actions = dict(policy.get("actions") or {})
    role = str(actions.get("ruleslawyer_response_synthesis") or "retrieval_synthesis").strip()
    candidate = str(models.get(role) or models.get("retrieval_synthesis") or "gpt-5.3-chat-latest").strip()
    return candidate or "gpt-5.3-chat-latest"


def _env_flag_enabled(name: str) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_text(name: str) -> str | None:
    raw = str(os.getenv(name, "")).strip()
    return raw or None


def _env_int(name: str, default: int) -> int:
    raw = _env_text(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _env_float(name: str, default: float) -> float:
    raw = _env_text(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _dedupe_strs(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _grounding_prompt_policy() -> dict[str, bool]:
    return {
        "uses_admitted_evidence": True,
        "forbids_rejected_support": True,
        "requires_evidence_id_citations": True,
        "read_only": True,
    }


def resolve_live_query_llm_config(
    root: Path,
    *,
    override: LiveQueryLLMConfig | None = None,
    model_override: str | None = None,
    require_llm_override: bool | None = None,
) -> LiveQueryLLMConfig:
    if override is not None:
        return override

    provider = _env_text(_LIVE_QUERY_PROVIDER_ENV) or "openai"
    model = (
        (model_override or "").strip()
        or (_env_text(_LIVE_QUERY_MODEL_ENV) or "").strip()
        or _live_query_model(root)
    )
    require_llm = require_llm_override if require_llm_override is not None else _env_flag_enabled(_REQUIRE_LLM_ENV)
    max_output_tokens = _env_int(_LIVE_QUERY_MAX_TOKENS_ENV, 600)
    temperature = _env_float(_LIVE_QUERY_TEMP_ENV, 0.2)
    return LiveQueryLLMConfig(
        provider=provider,
        model=model,
        require_llm=bool(require_llm),
        max_output_tokens=max_output_tokens,
        temperature=temperature,
    )


def resolve_manifest_path(
    *,
    request_manifest_path: str | None,
    packet: dict[str, Any],
    root: Path,
) -> Path | None:
    def _resolve_in_repo(candidate: str) -> Path | None:
        path = Path(candidate)
        resolved = (path if path.is_absolute() else (root / path)).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            return None
        if resolved.is_file():
            return resolved
        return None

    if request_manifest_path and request_manifest_path.strip():
        # Explicit caller override is authoritative: if provided but invalid/missing,
        # fail truthfully instead of silently falling back.
        return _resolve_in_repo(request_manifest_path.strip())

    candidates: list[str] = []
    for key in (
        "planning_manifest_path",
        "active_manifest_path",
        "manifest_path",
    ):
        raw = packet.get(key)
        if isinstance(raw, str) and raw.strip():
            candidates.append(raw.strip())
    if _env_flag_enabled(_DOGFOOD_DEFAULTS_ENV):
        candidates.append(str(_DEFAULT_MANIFEST_PATH))

    for candidate in candidates:
        resolved = _resolve_in_repo(candidate)
        if resolved is not None:
            return resolved
    return None


def _default_query_config() -> QueryConfig:
    if not _env_flag_enabled(_DOGFOOD_DEFAULTS_ENV):
        return QueryConfig()
    return QueryConfig(
        precondition_paths=_DEFAULT_PRECONDITION_PATHS,
        virtual_precondition_path="virtual://c2s23/corpus_preconditions/session_22",
        virtual_precondition_session_scope=(22,),
    )


def assign_evidence_ids(packet: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(packet))

    admitted = list(out.get("admitted_evidence") or [])
    for row in admitted:
        seed = "|".join(
            str(row.get(k) or "")
            for k in ("path", "unit_id", "line_start", "line_end", "text_excerpt")
        )
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
        row["evidence_id"] = f"ev-{digest}"

    rejected = list(out.get("rejected_evidence") or [])
    for idx, row in enumerate(rejected, start=1):
        evidence = dict(row.get("evidence") or {})
        if not evidence.get("evidence_id"):
            seed = "|".join(
                str(evidence.get(k) or "")
                for k in ("path", "unit_id", "line_start", "line_end", "text_excerpt")
            )
            digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
            evidence["evidence_id"] = f"ev-{digest}"
            row["evidence"] = evidence
        row["rejection_id"] = f"rej-{idx:03d}"

    out["admitted_evidence"] = admitted
    out["rejected_evidence"] = rejected
    return out


def render_grounded_prompt(question: str, packet: dict[str, Any]) -> str:
    admitted_rows: list[str] = []
    for row in list(packet.get("admitted_evidence") or []):
        admitted_rows.append(
            "\n".join(
                [
                    f"[{row.get('evidence_id', 'ev-unknown')}]",
                    f"role: {row.get('source_role', '')}",
                    f"authority: {row.get('authority', '')}",
                    f"path: {row.get('path', '')}",
                    f"line_range: {row.get('line_start', '')}-{row.get('line_end', '')}",
                    f"unit_id: {row.get('unit_id', '')}",
                    f"excerpt: {str(row.get('text_excerpt') or '').strip()}",
                ]
            )
        )
    rejected_rows: list[str] = []
    for row in list(packet.get("rejected_evidence") or []):
        ev = dict(row.get("evidence") or {})
        rejected_rows.append(
            "\n".join(
                [
                    f"[{row.get('rejection_id', 'rej-unknown')}]",
                    f"reason_code: {row.get('reason_code', '')}",
                    f"evidence_id: {ev.get('evidence_id', '')}",
                    f"role: {ev.get('source_role', '')}",
                    f"authority: {ev.get('authority', '')}",
                    f"path: {ev.get('path', '')}",
                    f"excerpt: {str(ev.get('text_excerpt') or '').strip()}",
                ]
            )
        )

    rules = [
        "Use admitted evidence for factual claims.",
        "Do not use rejected evidence as support.",
        "Cite admitted evidence IDs inline as [ev-...].",
        "Distinguish play facts from planning suggestions.",
        "Never claim write capability in this response path; it is read-only.",
        "If asked to mutate artifacts, explicitly refuse mutation and stay read-only.",
        "Every factual campaign claim in your answer must include at least one admitted evidence citation.",
    ]
    return "\n\n".join(
        [
            "You are answering a live planning question for a TTRPG campaign.",
            "Rules:\n- " + "\n- ".join(rules),
            f"Question:\n{question}",
            "ADMITTED EVIDENCE:\n" + ("\n\n".join(admitted_rows) if admitted_rows else "(none)"),
            "REJECTED EVIDENCE:\n" + ("\n\n".join(rejected_rows) if rejected_rows else "(none)"),
        ]
    )


def _extract_answer_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    return ""


def _extract_cited_evidence_ids(answer: str) -> list[str]:
    found = re.findall(r"\[(ev-[a-z0-9]+)\]", answer.lower())
    seen: set[str] = set()
    out: list[str] = []
    for eid in found:
        if eid in seen:
            continue
        seen.add(eid)
        out.append(eid)
    return out


def _answer_requires_read_only_refusal(question: str) -> bool:
    lowered = question.lower()
    return any(
        token in lowered
        for token in (
            "create ",
            "write ",
            "patch ",
            "register ",
            "update ",
            "append ",
            "edit ",
            "mutate ",
        )
    )


def build_fallback_grounded_answer(question: str, packet: dict[str, Any]) -> str:
    admitted = list(packet.get("admitted_evidence") or [])
    rejected = list(packet.get("rejected_evidence") or [])
    if not admitted:
        return (
            "I do not have enough admitted evidence to answer this confidently. "
            "Please provide additional canon recap/session-memory context."
        )
    snippets: list[str] = []
    for row in admitted[:3]:
        eid = str(row.get("evidence_id") or "ev-unknown")
        excerpt = str(row.get("text_excerpt") or "").strip()
        if not excerpt:
            continue
        snippets.append(f"{excerpt} [{eid}]")

    answer = " ".join(snippets).strip()
    if rejected:
        r = rejected[0]
        reason = str(r.get("reason_code") or "rejected")
        rid = str(r.get("rejection_id") or "rej-unknown")
        answer += f"\n\nRejected evidence remains audit-visible ({rid}: {reason})."
    if _answer_requires_read_only_refusal(question):
        answer += "\n\nThis live query path is read-only and cannot write, patch, create, or register artifacts."
    return answer


def _run_llm_grounded_answer(
    *,
    question: str,
    packet: dict[str, Any],
    llm_config: LiveQueryLLMConfig,
    client_factory: Callable[[], Any] | None = None,
) -> GroundedAnswerResult:
    diagnostics: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not llm_config.model.strip():
        code = "llm_model_config_missing"
        warnings.append(code)
        diagnostics.append({"code": code})
        return GroundedAnswerResult(answer=None, source="none", warnings=warnings, diagnostics=diagnostics)

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        code = "llm_api_key_missing"
        warnings.append(code)
        diagnostics.append({"code": code})
        return GroundedAnswerResult(answer=None, source="none", warnings=warnings, diagnostics=diagnostics)

    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:
        code = "llm_client_unavailable"
        warnings.append(code)
        diagnostics.append({"code": code, "error_type": type(exc).__name__})
        return GroundedAnswerResult(answer=None, source="none", warnings=warnings, diagnostics=diagnostics)

    prompt = render_grounded_prompt(question, packet)
    try:
        client = client_factory() if client_factory is not None else OpenAI()
    except Exception as exc:
        code = "llm_client_unavailable"
        warnings.append(code)
        diagnostics.append({"code": code, "error_type": type(exc).__name__})
        return GroundedAnswerResult(answer=None, source="none", warnings=warnings, diagnostics=diagnostics)

    try:
        response = client.responses.create(
            model=llm_config.model,
            input=prompt,
            temperature=llm_config.temperature,
            max_output_tokens=llm_config.max_output_tokens,
        )
    except Exception as exc:
        code = "llm_request_failed"
        warnings.append(code)
        diagnostics.append({"code": code, "error_type": type(exc).__name__})
        return GroundedAnswerResult(answer=None, source="none", warnings=warnings, diagnostics=diagnostics)

    answer = _extract_answer_text(response)
    if not answer:
        code = "llm_empty_answer"
        warnings.append(code)
        diagnostics.append({"code": code})
        return GroundedAnswerResult(answer=None, source="none", warnings=warnings, diagnostics=diagnostics)

    return GroundedAnswerResult(answer=answer, source="llm", warnings=warnings, diagnostics=diagnostics)


def _build_citations(answer: str, packet: dict[str, Any]) -> CitationValidationResult:
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

    citations: list[dict[str, Any]] = []
    for eid in cited:
        row = admitted_by_id.get(eid)
        if row is None:
            continue
        citations.append(
            {
                "evidence_id": eid,
                "path": row.get("path"),
                "line_start": row.get("line_start"),
                "line_end": row.get("line_end"),
                "source_role": row.get("source_role"),
                "authority": row.get("authority"),
            }
        )

    warnings: list[str] = []
    if not cited:
        warnings.append("llm_answer_missing_citations")
    unknown_ids = sorted([eid for eid in cited if eid not in admitted_by_id and eid not in rejected_ids])
    cited_rejected_ids = sorted([eid for eid in cited if eid in rejected_ids])
    if unknown_ids or cited_rejected_ids:
        warnings.append("llm_answer_cited_rejected_or_unknown_evidence")
    if cited and not citations:
        warnings.append("llm_answer_missing_citations")

    diagnostics = {
        "cited_evidence_ids": cited,
        "admitted_citation_ids": [c["evidence_id"] for c in citations],
        "unknown_citation_ids": unknown_ids,
        "rejected_citation_ids": cited_rejected_ids,
    }
    return CitationValidationResult(
        citations=citations,
        warnings=_dedupe_strs(warnings),
        diagnostics=diagnostics,
    )


def _classify_llm_failure_status(warnings: list[str]) -> str:
    unavailable_codes = {
        "llm_api_key_missing",
        "llm_client_unavailable",
        "llm_model_config_missing",
    }
    if any(code in unavailable_codes for code in warnings):
        return "llm_unavailable"
    return "llm_grounding_failed"


def _base_response(
    *,
    query_id: str,
    session: int,
    classification: TurnClassification,
    mode: str,
    status: str,
) -> dict[str, Any]:
    return {
        "schema": "dmb_live_query_response_v1",
        "query_id": query_id,
        "session": session,
        "mode": mode,
        "status": status,
        "classification": {
            "latency_mode": classification.latency_mode,
            "event_type": classification.event_type,
            "intent": classification.intent,
            "table_id": classification.table_id,
            "roll": classification.roll,
            "skill_check": classification.skill_check,
            "confidence": classification.confidence,
        },
        "events_written": [],
        "jobs_queued": [],
        "next_suggestions": [],
        "diagnostics": [],
        "mutations": [],
    }


def run_context_lookup_turn(
    *,
    question: str,
    classification: TurnClassification,
    packet: dict[str, Any],
    root: Path,
    session: int,
    request_manifest_path: str | None = None,
    llm_config_override: LiveQueryLLMConfig | None = None,
    llm_model_override: str | None = None,
    require_llm_override: bool | None = None,
    llm_client_factory: Callable[[], Any] | None = None,
) -> ContextLookupResult:
    query_id = f"live-query-{uuid.uuid4().hex[:12]}"
    manifest_path = resolve_manifest_path(
        request_manifest_path=request_manifest_path,
        packet=packet,
        root=root,
    )
    if manifest_path is None:
        response = _base_response(
            query_id=query_id,
            session=session,
            classification=classification,
            mode="context_lookup",
            status="missing_context_manifest",
        )
        response.update(
            {
                "answer": "I cannot ground this answer because no activated planning corpus manifest is configured.",
                "diagnostics": ["missing_context_manifest"],
                "provenance": {
                    "mode": "context_lookup",
                    "grounding_answer_source": "none",
                    "grounding_prompt_policy": _grounding_prompt_policy(),
                },
                "citations": [],
                "context_packet": None,
                "warnings": [],
            }
        )
        return ContextLookupResult(response=response, events_to_write=[], jobs_to_queue=[])

    llm_config = resolve_live_query_llm_config(
        root,
        override=llm_config_override,
        model_override=llm_model_override,
        require_llm_override=require_llm_override,
    )
    manifest = load_manifest(manifest_path)
    query_request = QueryRequest(question_id=query_id, question=question, category=None)
    context_packet = build_context_packet(query_request, manifest, root=root, config=_default_query_config())
    context_packet = assign_evidence_ids(context_packet)

    llm_result = _run_llm_grounded_answer(
        question=question,
        packet=context_packet,
        llm_config=llm_config,
        client_factory=llm_client_factory,
    )
    llm_citations = CitationValidationResult(citations=[], warnings=[], diagnostics={})
    answer_source: Literal["llm", "stub", "fallback", "none"] = llm_result.source
    warnings = list(llm_result.warnings)
    diagnostics = list(llm_result.diagnostics)
    answer = llm_result.answer or ""
    status = "ok"

    if llm_result.answer is not None:
        llm_citations = _build_citations(llm_result.answer, context_packet)
        warnings.extend(llm_citations.warnings)
        diagnostics.append({"code": "llm_citation_validation", **llm_citations.diagnostics})
        llm_citation_failure = any(
            code in llm_citations.warnings
            for code in ("llm_answer_missing_citations", "llm_answer_cited_rejected_or_unknown_evidence")
        )
        if llm_citation_failure and llm_config.require_llm:
            status = "llm_grounding_failed"
            answer = ""
            answer_source = "none"
        elif llm_citation_failure:
            answer = build_fallback_grounded_answer(question, context_packet)
            answer_source = "fallback"
            warnings.append("llm_fallback_used")
    else:
        if llm_config.require_llm:
            status = _classify_llm_failure_status(warnings)
            answer = ""
            answer_source = "none"
        else:
            answer = build_fallback_grounded_answer(question, context_packet)
            answer_source = "fallback"
            warnings.append("llm_fallback_used")

    citation_result = _build_citations(answer, context_packet) if answer else CitationValidationResult([], [], {})
    if answer_source != "llm":
        warnings.extend(citation_result.warnings)

    warnings = _dedupe_strs(warnings)
    provenance: dict[str, Any] = {
        "mode": "context_lookup",
        "manifest_path": str(manifest_path.relative_to(root)),
        "generated_at": _utc_now_z(),
        "grounding_summary": {
            "admitted_count": len(context_packet.get("admitted_evidence") or []),
            "rejected_count": len(context_packet.get("rejected_evidence") or []),
        },
        "grounding_prompt_policy": _grounding_prompt_policy(),
        "grounding_answer_source": answer_source,
        "llm_path_available": answer_source == "llm",
        "llm_model": llm_config.model,
        "llm_provider": llm_config.provider,
        "llm_require_llm": llm_config.require_llm,
        "llm_diagnostics": diagnostics,
    }
    if _env_flag_enabled(_DEBUG_GROUNDED_PROMPT_ENV):
        provenance["grounded_prompt"] = render_grounded_prompt(question, context_packet)

    response = _base_response(
        query_id=query_id,
        session=session,
        classification=classification,
        mode="context_lookup",
        status=status,
    )
    response.update(
        {
            "answer": answer,
            "provenance": provenance,
            "citations": citation_result.citations,
            "context_packet": context_packet,
            "warnings": warnings,
        }
    )
    return ContextLookupResult(response=response, events_to_write=[], jobs_to_queue=[])
