"""LLM-guided document selection before chunk-level evidence retrieval."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.agent.evidence_retriever import _unit_allowed
from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.llm.api_client import DungeonMindApiClient

logger = logging.getLogger(__name__)

DOCUMENT_PLANNER_PROMPT = """You are a document selector for a tabletop RPG knowledge graph.

You receive a GM's question and a roster of source documents with metadata.
Select which documents are likely to contain information needed to answer the question.

## Document roster format
Each entry: [doc_id] Title (type, source_class, canon_layer, N chunks)
  Path: topical grouping from section headings
  Sections: top section headings from the document
  Summary: brief description or first lines

## Rules
- Select 2-8 documents depending on question scope. Fewer is better for focused questions.
- Always include documents whose title, path, or summary mentions entities/events/locations from the question.
- Include session recap documents if the question asks about what happened in play (observed events).
- Include world reference documents if the question asks about locations, NPCs, or world details.
- Use the path to identify topical relevance.
- If uncertain, include more rather than fewer — false negatives are worse than false positives here.
- For broad questions ("tell me about the campaign"), select broadly across categories.
- For narrow questions ("what happened to The Wolf?"), select tightly.

Return ONLY valid JSON:
{
  "selected_document_ids": ["doc_foo", "doc_bar"],
  "reasoning": "one sentence"
}"""

DEFAULT_MODEL = "gpt-5.4-nano"


def _first_summary_snippet(text: str, max_chars: int = 220) -> str:
    t = " ".join(str(text).split())
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 3] + "..."


def build_document_roster(
    evidence_units: list[dict[str, Any]],
    *,
    campaign_id: str | None,
) -> tuple[str, set[str]]:
    """Build roster text and the set of valid document_ids for validation."""
    by_doc: dict[str, list[dict[str, Any]]] = {}
    for unit in evidence_units:
        if not _unit_allowed(unit, campaign_id):
            continue
        doc_id = str(unit.get("document_id", "")).strip()
        if not doc_id:
            continue
        by_doc.setdefault(doc_id, []).append(unit)

    if not by_doc:
        return "", set()

    lines: list[str] = []
    candidate_ids: set[str] = set()

    for doc_id in sorted(by_doc.keys()):
        units = by_doc[doc_id]
        try:
            units.sort(key=lambda u: int(u.get("source_order_index", 0) or 0))
        except (TypeError, ValueError):
            pass
        first = units[0]
        title = str(first.get("document_title", doc_id)).strip() or doc_id
        dtype = str(first.get("document_type", "")).strip() or "unknown"
        sclass = str(first.get("source_class", "")).strip() or "unknown"
        layer = str(first.get("canon_layer", "")).strip() or "unknown"
        n_chunks = len(units)

        tops: set[str] = set()
        for u in units:
            sp = u.get("section_path") or []
            if isinstance(sp, list) and sp:
                tops.add(str(sp[0]).strip())
            if len(tops) >= 8:
                break
        tops_list = sorted(tops)[:5]
        path_str = " > ".join(tops_list) if tops_list else "(unknown)"
        sections_str = ", ".join(tops_list[:5]) if tops_list else "(none)"

        summary_src = str(first.get("text", "")).strip()
        summary = _first_summary_snippet(summary_src)

        lines.append(
            f"[{doc_id}] {title} ({dtype}, {sclass}, {layer}, {n_chunks} chunks)\n"
            f"  Path: {path_str}\n"
            f"  Sections: {sections_str}\n"
            f"  Summary: {summary}"
        )
        candidate_ids.add(doc_id)

    return "\n\n".join(lines), candidate_ids


def _resolve_document_planner_model(model: str | None) -> str:
    if model:
        return model
    from src.model_policy import load_buddy_model_policy

    policy = load_buddy_model_policy()
    if policy:
        try:
            role = policy.get("actions", {}).get(
                "document_planning",
                policy.get("actions", {}).get("query_planning", "query_planning"),
            )
            resolved = policy.get("models", {}).get(role)
            if resolved:
                return str(resolved)
        except Exception:
            pass
    return DEFAULT_MODEL


def _parse_document_plan(raw: str, candidate_ids: set[str]) -> tuple[list[str], str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        stripped = raw.strip()
        if stripped.startswith("```"):
            inner_lines = [
                line for line in stripped.split("\n") if not line.strip().startswith("```")
            ]
            data = json.loads("\n".join(inner_lines))
        else:
            raise
    selected = data.get("selected_document_ids", [])
    if not isinstance(selected, list):
        selected = []
    valid = [str(x).strip() for x in selected if str(x).strip() in candidate_ids]
    reasoning = str(data.get("reasoning", ""))
    return valid, reasoning


@dataclass(frozen=True)
class DocumentPlan:
    selected_document_ids: list[str]
    reasoning: str
    model: str
    duration_ms: int
    fallback: bool = False


async def plan_documents_async(
    question: str,
    roster: str,
    candidate_ids: set[str],
    *,
    model: str | None = None,
    openai_client: Any | None = None,
) -> DocumentPlan:
    model_id = _resolve_document_planner_model(model)
    t0 = time.perf_counter()

    if not candidate_ids or not roster.strip():
        return DocumentPlan(
            selected_document_ids=sorted(candidate_ids),
            reasoning="empty_roster",
            model=model_id,
            duration_ms=0,
            fallback=True,
        )

    client = openai_client
    is_async_client = False
    if client is None:
        load_dungeonmindbuddy_dotenv()
        if not (os.getenv("OPENAI_API_KEY") or "").strip():
            logger.warning("No OPENAI_API_KEY; document planner fallback (all docs)")
            return DocumentPlan(
                selected_document_ids=sorted(candidate_ids),
                reasoning="no_api_key",
                model=model_id,
                duration_ms=0,
                fallback=True,
            )
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI SDK required for document planning") from exc
        client = AsyncOpenAI()
        is_async_client = True
    api_client = DungeonMindApiClient.wrap(client)

    user_prompt = (
        f"GM question: {question}\n\n"
        f"Documents ({len(candidate_ids)} total):\n{roster}\n\n"
        "Select document IDs needed to answer. Return JSON only."
    )

    try:
        request_kwargs = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": DOCUMENT_PLANNER_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        if is_async_client:
            response = (
                await api_client.chat_completions_create_async(
                    action="document_planner.plan", **request_kwargs
                )
            ).response
        else:
            response = api_client.chat_completions_create(
                action="document_planner.plan", **request_kwargs
            ).response
        raw_text = response.choices[0].message.content or ""
        valid, reasoning = _parse_document_plan(raw_text, candidate_ids)
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        logger.warning("Document planner failed (%s); fallback all docs", exc)
        return DocumentPlan(
            selected_document_ids=sorted(candidate_ids),
            reasoning=f"planner_error: {exc}",
            model=model_id,
            duration_ms=elapsed_ms,
            fallback=True,
        )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    if not valid:
        logger.warning("Document planner empty; fallback all docs")
        return DocumentPlan(
            selected_document_ids=sorted(candidate_ids),
            reasoning=(reasoning or "") + " (empty selection, fell back)",
            model=model_id,
            duration_ms=elapsed_ms,
            fallback=True,
        )

    return DocumentPlan(
        selected_document_ids=valid,
        reasoning=reasoning,
        model=model_id,
        duration_ms=elapsed_ms,
        fallback=False,
    )


def plan_documents(
    question: str,
    roster: str,
    candidate_ids: set[str],
    *,
    model: str | None = None,
    openai_client: Any | None = None,
) -> DocumentPlan:
    import asyncio

    return asyncio.run(
        plan_documents_async(
            question,
            roster,
            candidate_ids,
            model=model,
            openai_client=openai_client,
        )
    )
