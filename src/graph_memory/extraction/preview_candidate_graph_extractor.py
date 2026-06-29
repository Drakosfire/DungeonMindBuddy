from __future__ import annotations

"""Compact single-pass preview candidate graph extractor (deprecated).

Product recap graph ingest uses ``category_candidate_graph_extractor`` instead.
Retained for fixture imports and legacy tests.
"""

import json
import logging
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
logger = logging.getLogger(__name__)

STRING = {"type": "string"}
STRING_OR_NULL = {"type": ["string", "null"]}
STRING_ARRAY = {"type": "array", "items": STRING}
PREVIEW_CANDIDATE_GRAPH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "candidate_nodes",
        "candidate_edges",
        "session_beats",
        "ignored_or_deferred_candidates",
        "source_artifacts",
        "evidence_refs",
        "diagnostics",
    ],
    "properties": {
        "candidate_nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "kind", "label", "role", "summary", "evidence_refs"],
                "properties": {
                    "id": STRING,
                    "kind": STRING,
                    "label": STRING,
                    "role": STRING_OR_NULL,
                    "summary": STRING,
                    "evidence_refs": STRING_ARRAY,
                },
            },
        },
        "candidate_edges": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "source", "target", "type", "summary", "evidence_refs"],
                "properties": {
                    "id": STRING,
                    "source": STRING,
                    "target": STRING,
                    "type": STRING,
                    "summary": STRING,
                    "evidence_refs": STRING_ARRAY,
                },
            },
        },
        "session_beats": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "summary", "evidence_refs"],
                "properties": {
                    "id": STRING,
                    "summary": STRING,
                    "evidence_refs": STRING_ARRAY,
                },
            },
        },
        "ignored_or_deferred_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["summary", "reason", "evidence_refs"],
                "properties": {
                    "summary": STRING,
                    "reason": STRING,
                    "evidence_refs": STRING_ARRAY,
                },
            },
        },
        "source_artifacts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["artifact_id", "kind", "label", "uri"],
                "properties": {
                    "artifact_id": STRING,
                    "kind": STRING,
                    "label": STRING,
                    "uri": STRING,
                },
            },
        },
        "evidence_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "span_id", "text_excerpt"],
                "properties": {
                    "id": STRING,
                    "span_id": STRING,
                    "text_excerpt": STRING,
                },
            },
        },
        "diagnostics": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "preview_only",
                "canon_promotion",
                "approved_memory_write",
                "corpus_mutation",
                "production_retrieval",
            ],
            "properties": {
                "preview_only": {"type": "boolean"},
                "canon_promotion": {"type": "boolean"},
                "approved_memory_write": {"type": "boolean"},
                "corpus_mutation": {"type": "boolean"},
                "production_retrieval": {"type": "boolean"},
            },
        },
    },
}


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
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class PreviewCandidateGraphExtractionResult:
    candidate_graph: dict[str, Any]
    raw_model_response: str | None
    model_id: str
    diagnostics: dict[str, Any]


class PreviewCandidateGraphParseError(ValueError):
    def __init__(self, message: str, *, raw_model_response: str):
        super().__init__(message)
        self.raw_model_response = raw_model_response


class FixtureCandidateGraphModelClient:
    def __init__(self, response: str):
        self.response = response

    def extract_candidate_graph(self, prompt: str, *, model_id: str) -> str:
        return self.response


def _responses_create_kwargs(
    *, prompt: str, model_id: str, max_output_tokens: int | None = None
) -> dict[str, Any]:
    """Build Responses API kwargs compatible with GPT-5 reasoning models."""

    kwargs: dict[str, Any] = {
        "model": model_id,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "preview_candidate_graph",
                "schema": PREVIEW_CANDIDATE_GRAPH_SCHEMA,
                "strict": True,
            }
        },
    }
    if max_output_tokens is not None:
        kwargs["max_output_tokens"] = max_output_tokens
    return kwargs


class OpenAICandidateGraphModelClient:
    def __init__(self, *, max_output_tokens: int | None = None):
        self.max_output_tokens = max_output_tokens

    def extract_candidate_graph(self, prompt: str, *, model_id: str) -> str:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not configured; supply candidate_graph_path or disable graph extraction."
            )
        from openai import OpenAI  # lazy import so tests do not require OpenAI

        client = OpenAI()
        request_kwargs = _responses_create_kwargs(
            prompt=prompt,
            model_id=model_id,
            max_output_tokens=self.max_output_tokens,
        )
        logger.info(
            "openai candidate graph request model=%s prompt_chars=%s response_format=%s schema_name=%s strict=%s max_output_tokens=%s",
            model_id,
            len(prompt),
            request_kwargs.get("text", {}).get("format", {}).get("type"),
            request_kwargs.get("text", {}).get("format", {}).get("name"),
            request_kwargs.get("text", {}).get("format", {}).get("strict"),
            request_kwargs.get("max_output_tokens"),
        )
        response = client.responses.create(**request_kwargs)
        text = getattr(response, "output_text", None)
        usage = getattr(response, "usage", None)
        if usage is not None and hasattr(usage, "model_dump"):
            usage = usage.model_dump()
        logger.info(
            "openai candidate graph response id=%s status=%s model=%s output_text_chars=%s usage=%s",
            getattr(response, "id", None),
            getattr(response, "status", None),
            getattr(response, "model", None),
            len(text) if isinstance(text, str) else None,
            usage,
        )
        if isinstance(text, str):
            logger.info(
                "openai candidate graph raw output begin\n%s\nopenai candidate graph raw output end",
                text,
            )
        if getattr(response, "status", None) == "incomplete":
            raw = text if isinstance(text, str) else response.model_dump_json()
            details = getattr(response, "incomplete_details", None)
            reason = getattr(details, "reason", None)
            if reason is None and isinstance(details, dict):
                reason = details.get("reason")
            raise PreviewCandidateGraphParseError(
                f"candidate graph model response incomplete: {reason or 'unknown reason'}",
                raw_model_response=raw,
            )
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
Keep the output compact: at most 12 candidate_nodes, 18 candidate_edges, 8 session_beats, 8 ignored_or_deferred_candidates, and 24 evidence_refs.
Return JSON matching the supplied response schema exactly: top-level arrays candidate_nodes, candidate_edges, session_beats, ignored_or_deferred_candidates, source_artifacts, evidence_refs, and diagnostics.
Nodes: extract PCs, NPCs, factions, locations, artifacts, threats, monsters, events, mysteries, fronts, and unresolved threads. Prefer id format node:<slug>; include id, kind, label, role (or null), summary, evidence_refs.
Edges: extract navigation-relevant relationships using types such as located_at, allied_with, opposed_by, threatens, discovered, travels_to, owns, commands, investigates, protects, changed_by, foreshadows, unresolved_thread. Include id, source, target, type, summary, evidence_refs.
Session beats: extract 3-12 concise beats with id, summary, and evidence_refs.
Evidence refs must be top-level objects like {{"id":"ev:1","span_id":"<catalog span id>","text_excerpt":"short supporting excerpt"}}; candidates then cite those evidence ids.
Defer uncertain identities, spelling ambiguity, unsupported inference, or chat noise in ignored_or_deferred_candidates with summary, reason, and evidence_refs.
Diagnostics must set preview_only true and canon_promotion, approved_memory_write, corpus_mutation, and production_retrieval false.

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
    model_client = client or OpenAICandidateGraphModelClient(
        max_output_tokens=options.max_output_tokens
    )
    prompt = build_preview_candidate_graph_prompt(options)
    raw = model_client.extract_candidate_graph(prompt, model_id=options.model_id)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PreviewCandidateGraphParseError(
            f"candidate graph model returned invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}",
            raw_model_response=raw,
        ) from exc
    candidate_graph = enforce_preview_only_candidate_graph(payload)
    return PreviewCandidateGraphExtractionResult(
        candidate_graph=candidate_graph,
        raw_model_response=raw,
        model_id=options.model_id,
        diagnostics={"extraction_mode": "llm", "model_id": options.model_id, **PREVIEW_DIAGNOSTICS},
    )
