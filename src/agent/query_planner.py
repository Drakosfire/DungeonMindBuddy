"""LLM-guided query planning for knowledge graph retrieval.

The query planner sits between the retriever and the synthesis step.
It receives a compact roster of retriever candidates and asks an LLM
to select the entities and attributes most relevant to the question.

Pipeline:
    All entities (~1000+)
      → Retriever: keyword + name match (~50 candidates)
        → Query Planner: LLM triage (~5-20 focused entities)
          → Synthesis: answer from focused context
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are a query planner for a tabletop RPG campaign knowledge graph.

You receive a GM's question and a roster of candidate entities from the knowledge graph.
Your job is to select the entities and fact-types needed to answer the question.

## Entity roster format

Each line: [entity_id] Display Name (class): attribute1: summary; attribute2: summary

## Available attribute types

atmosphere, current_location, defenses, demographics, economy, geography,
goals, history, loyalty_or_alignment_context, mental_state, notable_abilities,
operational_status, physical_condition, portrayal_notes, relationship_tags,
role, species

## Rules

- Select 5-20 entities depending on question complexity.
- Always include entities mentioned by name in the question.
- Include closely related entities (factions, locations, allies of named entities).
- Choose 2-6 attribute types most relevant to the question.
- Be conservative: fewer focused entities beat many vague ones.
- If the question is about a specific event or fight, include participants and the event entity.
- If the question is about a person, include their faction, location, and allies/enemies.

Return ONLY valid JSON, no other text:
{
  "selected_entity_ids": ["ent_foo", "ent_bar"],
  "relevant_attributes": ["role", "goals"],
  "reasoning": "one sentence"
}"""

PLANNER_DEFAULT_MODEL = "gpt-5.4-nano"

_NOISE_ATTRIBUTES = frozenset({"source_comments", "unresolved_questions"})
VALID_ATTRIBUTES = frozenset(
    {
        "atmosphere",
        "current_location",
        "defenses",
        "demographics",
        "economy",
        "geography",
        "goals",
        "history",
        "loyalty_or_alignment_context",
        "mental_state",
        "notable_abilities",
        "operational_status",
        "physical_condition",
        "portrayal_notes",
        "relationship_tags",
        "role",
        "species",
    }
)

_NOISE_LABEL_PREFIXES = (
    "not mentioned",
    "no direct assertion",
    "no assertion",
    "no asserted fact",
    "not asserted",
    "text does not mention",
    "mentioned in evidence unit",
    "presence in evidence",
    "evidence unit text content",
)


@dataclass
class QueryPlan:
    """Result of LLM query planning."""

    selected_entity_ids: list[str]
    relevant_attributes: list[str] | None = None
    reasoning: str = ""
    model: str = ""
    duration_ms: int = 0
    fallback: bool = False
    raw_response: str = field(default="", repr=False)


def _normalize_attribute(raw: str) -> str | None:
    token = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    if not token:
        return None
    if token in VALID_ATTRIBUTES:
        return token

    if token.endswith("s") and token[:-1] in VALID_ATTRIBUTES:
        return token[:-1]

    aliases = {
        "portray_notes": "portrayal_notes",
        "portrait_notes": "portrayal_notes",
        "alignment_context": "loyalty_or_alignment_context",
        "alignment": "loyalty_or_alignment_context",
        "location": "current_location",
        "status": "operational_status",
        "condition": "physical_condition",
        "abilities": "notable_abilities",
        "ability": "notable_abilities",
        "relationships": "relationship_tags",
    }
    if token in aliases:
        return aliases[token]

    for valid in VALID_ATTRIBUTES:
        if token in valid or valid in token:
            return valid

    fuzzy = get_close_matches(token, list(VALID_ATTRIBUTES), n=1, cutoff=0.72)
    return fuzzy[0] if fuzzy else None


def _is_noise_label(label: str) -> bool:
    if not label or len(label.strip()) < 5:
        return True
    lowered = label.lower().strip()
    return any(lowered.startswith(p) for p in _NOISE_LABEL_PREFIXES)


def build_entity_roster(
    ranked_entities: list[tuple[str, float]],
    projection: dict[str, Any],
    entities: list[dict[str, Any]],
    *,
    max_attrs_per_entity: int = 4,
    max_label_chars: int = 120,
) -> str:
    """Build a compact text roster of candidate entities for LLM triage.

    Each entity gets one line with its top attributes, keeping total
    size small enough for a cheap LLM call.
    """
    meta_by_id: dict[str, dict[str, Any]] = {}
    for e in entities:
        eid = e.get("entity_id", "")
        if eid:
            meta_by_id[eid] = e

    proj_entities = projection.get("entities", {})
    lines: list[str] = []

    for eid, _score in ranked_entities:
        meta = meta_by_id.get(eid, {})
        name = meta.get("display_name", eid)
        cls = meta.get("entity_class", "?")

        attrs = proj_entities.get(eid, {}).get("attributes", {})
        attr_parts: list[str] = []
        for attr_name in sorted(attrs):
            if attr_name in _NOISE_ATTRIBUTES:
                continue
            label = attrs[attr_name].get("value_label", "")
            if _is_noise_label(label):
                continue
            truncated = label[:max_label_chars] + "..." if len(label) > max_label_chars else label
            attr_parts.append(f"{attr_name}: {truncated}")
            if len(attr_parts) >= max_attrs_per_entity:
                break

        attr_text = "; ".join(attr_parts) if attr_parts else "(no details)"
        lines.append(f"[{eid}] {name} ({cls}): {attr_text}")

    return "\n".join(lines)


def _resolve_planner_model(model: str | None) -> str:
    if model:
        return model
    policy_candidates = [
        Path(__file__).resolve().parents[2] / "MODEL_POLICY.json",
        Path(__file__).resolve().parents[3] / "MODEL_POLICY.json",
    ]
    for policy_path in policy_candidates:
        if policy_path.exists():
            try:
                policy = json.loads(policy_path.read_text(encoding="utf-8"))
                role = policy.get("actions", {}).get("query_planning", "query_planning")
                resolved = policy.get("models", {}).get(role)
                if resolved:
                    return resolved
            except Exception:
                pass
    return PLANNER_DEFAULT_MODEL


def _load_api_key() -> str | None:
    project_root = Path(__file__).resolve().parents[2]
    for env_file in [
        project_root / ".env.development",
        project_root.parents[0] / ".env.development",
    ]:
        if env_file.exists():
            load_dotenv(env_file, override=True)
    return os.getenv("OPENAI_API_KEY")


def _parse_plan_response(raw: str, candidate_ids: set[str]) -> QueryPlan:
    """Parse the LLM response into a QueryPlan, validating entity IDs."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        stripped = raw.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            inner = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )
            data = json.loads(inner)
        else:
            raise

    selected = data.get("selected_entity_ids", [])
    if not isinstance(selected, list):
        selected = []

    valid_ids = [eid for eid in selected if eid in candidate_ids]

    relevant_attrs = data.get("relevant_attributes")
    if isinstance(relevant_attrs, list):
        normalized_attrs: list[str] = []
        seen: set[str] = set()
        for attr in relevant_attrs:
            normalized = _normalize_attribute(str(attr))
            if not normalized or normalized in seen:
                continue
            normalized_attrs.append(normalized)
            seen.add(normalized)
        relevant_attrs = normalized_attrs
    else:
        relevant_attrs = None

    return QueryPlan(
        selected_entity_ids=valid_ids,
        relevant_attributes=relevant_attrs if relevant_attrs else None,
        reasoning=str(data.get("reasoning", "")),
        raw_response=raw,
    )


async def plan_query_async(
    question: str,
    entity_roster: str,
    candidate_ids: set[str],
    *,
    model: str | None = None,
    openai_client: Any | None = None,
) -> QueryPlan:
    """Ask an LLM to select relevant entities from the retriever's candidates.

    Returns a QueryPlan. On failure, returns a fallback plan containing
    all candidate_ids so the pipeline degrades gracefully.
    """
    model_id = _resolve_planner_model(model)
    t0 = time.time()

    client = openai_client
    is_async_client = False
    if client is None:
        api_key = _load_api_key()
        if not api_key:
            logger.warning("No OPENAI_API_KEY; falling back to full candidate set")
            return QueryPlan(
                selected_entity_ids=sorted(candidate_ids),
                fallback=True,
                reasoning="no_api_key",
            )
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI SDK required for query planning") from exc
        client = AsyncOpenAI(api_key=api_key)
        is_async_client = True

    user_prompt = (
        f"GM question: {question}\n\n"
        f"Candidate entities ({len(candidate_ids)} total):\n{entity_roster}\n\n"
        "Select the entities and attributes needed to answer this question. "
        "Return JSON only."
    )

    try:
        payload = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        response = await payload if is_async_client else payload
        raw_text = response.choices[0].message.content or ""
        plan = _parse_plan_response(raw_text, candidate_ids)
    except Exception as exc:
        elapsed_ms = int((time.time() - t0) * 1000)
        logger.warning(
            "Query planner failed (%s); falling back to full candidates", exc
        )
        return QueryPlan(
            selected_entity_ids=sorted(candidate_ids),
            fallback=True,
            reasoning=f"planner_error: {exc}",
            model=model_id,
            duration_ms=elapsed_ms,
        )

    elapsed_ms = int((time.time() - t0) * 1000)
    plan.model = model_id
    plan.duration_ms = elapsed_ms

    if not plan.selected_entity_ids:
        logger.warning("Planner returned empty selection; falling back")
        plan.selected_entity_ids = sorted(candidate_ids)
        plan.fallback = True
        plan.reasoning += " (empty selection, fell back)"

    logger.info(
        "QueryPlanner: %d/%d entities selected, %s attributes, %dms (%s)",
        len(plan.selected_entity_ids),
        len(candidate_ids),
        len(plan.relevant_attributes) if plan.relevant_attributes else "all",
        elapsed_ms,
        model_id,
    )

    return plan


def plan_query(
    question: str,
    entity_roster: str,
    candidate_ids: set[str],
    *,
    model: str | None = None,
    openai_client: Any | None = None,
) -> QueryPlan:
    """Synchronous wrapper for plan_query_async."""
    import asyncio

    return asyncio.run(
        plan_query_async(
            question,
            entity_roster,
            candidate_ids,
            model=model,
            openai_client=openai_client,
        )
    )
