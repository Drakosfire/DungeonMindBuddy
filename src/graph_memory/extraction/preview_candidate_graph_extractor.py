from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

PREVIEW_DIAGNOSTICS = {
    "preview_only": True,
    "canon_promotion": False,
    "approved_memory_write": False,
    "corpus_mutation": False,
    "production_retrieval": False,
}
ARRAY_FIELDS = (
    "candidate_nodes",
    "candidate_edges",
    "session_beats",
    "ignored_or_deferred_candidates",
    "source_artifacts",
    "evidence_refs",
)


class CandidateGraphModelClient(Protocol):
    def extract_candidate_graph(self, prompt: str, *, model_id: str) -> str: ...


@dataclass(frozen=True)
class PreviewCandidateGraphExtractionOptions:
    campaign_id: str
    session_id: str
    recap_markdown: str
    source_span_id: str
    source_span_catalog: list[dict[str, Any]] | None = None
    model_id: str = "gpt-5-mini"
    temperature: float = 0.0
    max_output_tokens: int = 6000


@dataclass(frozen=True)
class PreviewCandidateGraphExtractionResult:
    candidate_graph: dict[str, Any]
    raw_model_response: str | None
    model_id: str
    diagnostics: dict[str, Any]


class FixtureCandidateGraphModelClient:
    def __init__(self, response: str):
        self.response = response

    def extract_candidate_graph(self, prompt: str, *, model_id: str) -> str:
        return self.response


class OpenAICandidateGraphModelClient:
    def extract_candidate_graph(self, prompt: str, *, model_id: str) -> str:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not configured; supply candidate_graph_path or disable graph extraction."
            )
        from openai import OpenAI  # lazy import so tests do not require OpenAI

        client = OpenAI()
        response = client.responses.create(
            model=model_id,
            input=prompt,
            temperature=0,
            max_output_tokens=6000,
            text={"format": {"type": "json_object"}},
        )
        text = getattr(response, "output_text", None)
        if isinstance(text, str):
            return text
        return response.model_dump_json()


def enforce_preview_only_candidate_graph(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("candidate graph model output must be a JSON object")
    sanitized = dict(payload)
    malformed: dict[str, int] = {}
    for field in ARRAY_FIELDS:
        value = sanitized.get(field)
        if not isinstance(value, list):
            if value is not None:
                malformed[field] = 1
            sanitized[field] = []
            continue
        if field == "evidence_refs":
            kept = [item for item in value if isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("span_id"), str)]
        else:
            kept = [item for item in value if isinstance(item, dict)]
        malformed_count = len(value) - len(kept)
        if malformed_count:
            malformed[field] = malformed_count
        sanitized[field] = kept
    diagnostics = sanitized.get("diagnostics") if isinstance(sanitized.get("diagnostics"), dict) else {}
    diagnostics = {**diagnostics, **PREVIEW_DIAGNOSTICS}
    if malformed:
        diagnostics["malformed_candidates_quarantined"] = malformed
    sanitized["diagnostics"] = diagnostics
    return sanitized


def _format_source_span_catalog(options: PreviewCandidateGraphExtractionOptions) -> str:
    spans = options.source_span_catalog or []
    rows = []
    for span in spans:
        if not isinstance(span, dict):
            continue
        span_id = span.get("span_id") or span.get("source_span_ref_id")
        if not isinstance(span_id, str):
            continue
        kind = span.get("kind") or "span"
        ordinal = span.get("ordinal")
        excerpt = str(span.get("text_excerpt") or span.get("text") or "").replace("\n", " ")[:240]
        rows.append(f"- {span_id} ({kind} {ordinal}) — {excerpt}")
    return "\n".join(rows) if rows else f"- {options.source_span_id} (full_text fallback)"


def build_preview_candidate_graph_prompt(options: PreviewCandidateGraphExtractionOptions) -> str:
    source_catalog = _format_source_span_catalog(options)
    return f"""You are extracting preview-only candidate graph facts from a TTRPG session recap.
Extract only facts supported by the recap. Prefer fewer, higher-confidence candidates.
Every candidate node, edge, and beat must reference evidence_refs. Prefer paragraph span ids from the source span catalog whenever possible; use the full_text span only when a fact is broadly supported across the whole recap. Full-text fallback span id: {options.source_span_id}
Do not infer canon beyond the text. Do not promote anything to approved memory.
Return JSON only with top-level arrays candidate_nodes, candidate_edges, session_beats, ignored_or_deferred_candidates, source_artifacts, evidence_refs, and diagnostics.
Nodes: extract PCs, NPCs, factions, locations, artifacts, threats, monsters, events, mysteries, fronts, and unresolved threads. Prefer id format node:<slug>; include kind, label, role when obvious, summary, evidence_refs.
Edges: extract navigation-relevant relationships using types such as located_at, allied_with, opposed_by, threatens, discovered, travels_to, owns, commands, investigates, protects, changed_by, foreshadows, unresolved_thread.
Session beats: extract 3-12 concise beats with summary and evidence_refs.
Evidence refs must be top-level objects like {"id":"ev:1","span_id":"<catalog span id>","text_excerpt":"short supporting excerpt"}; candidates then cite those evidence ids.
Defer uncertain identities, spelling ambiguity, unsupported inference, or chat noise in ignored_or_deferred_candidates.

Available source spans:
{source_catalog}

Campaign: {options.campaign_id}
Session: {options.session_id}
Recap markdown:
{options.recap_markdown}
"""


def extract_preview_candidate_graph(
    options: PreviewCandidateGraphExtractionOptions,
    *,
    client: CandidateGraphModelClient | None = None,
) -> PreviewCandidateGraphExtractionResult:
    model_client = client or OpenAICandidateGraphModelClient()
    prompt = build_preview_candidate_graph_prompt(options)
    raw = model_client.extract_candidate_graph(prompt, model_id=options.model_id)
    payload = json.loads(raw)
    candidate_graph = enforce_preview_only_candidate_graph(payload)
    return PreviewCandidateGraphExtractionResult(
        candidate_graph=candidate_graph,
        raw_model_response=raw,
        model_id=options.model_id,
        diagnostics={"extraction_mode": "llm", "model_id": options.model_id, **PREVIEW_DIAGNOSTICS},
    )
