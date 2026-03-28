from __future__ import annotations

import asyncio
import inspect
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import blake3
from pydantic import BaseModel, Field

from src.contracts.schema_validation import validate_many

_PROMPT_ID = "phase_c_pass2_fact_extraction_v1"

_VALID_ATTRIBUTES = {
    "species",
    "role",
    "rank_or_title",
    "faction",
    "current_location",
    "physical_condition",
    "mental_state",
    "loyalty_or_alignment_context",
    "relationship_tags",
    "operational_status",
    "portrayal_notes",
    "unresolved_questions",
    "source_comments",
    "history",
    "geography",
    "demographics",
    "defenses",
    "economy",
    "governance",
    "atmosphere",
    "goals",
}

_TRUTH_STATE_MAP: dict[tuple[str, str], tuple[str, str]] = {
    ("world", "seed_reference"): ("CANON", "seed_prep"),
    ("campaign", "planning_document"): ("PREP", "planning_prep"),
    ("campaign", "observed_session_recap"): ("OBSERVED", "observed_recap"),
    ("campaign", "ledger_or_dossier"): ("OBSERVED", "observed_recap"),
}

logger = logging.getLogger(__name__)

AttributeType = Literal[
    "species",
    "role",
    "rank_or_title",
    "faction",
    "current_location",
    "physical_condition",
    "mental_state",
    "loyalty_or_alignment_context",
    "relationship_tags",
    "operational_status",
    "portrayal_notes",
    "unresolved_questions",
    "source_comments",
    "history",
    "geography",
    "demographics",
    "defenses",
    "economy",
    "governance",
    "atmosphere",
    "goals",
]


class FactValueOutput(BaseModel):
    kind: Literal["scalar", "state", "entity_ref", "set", "interpretive"]
    label: str
    normalized: str | None = None
    entity_id: str | None = None
    values: list[str] | None = None
    interpretation_level: (
        Literal["direct_assertion", "derived_summary", "interpretive_inference"] | None
    ) = None
    strength: Literal["weak", "moderate", "strong"] | None = None


class ExtractedFact(BaseModel):
    fact_id: str
    subject_entity_id: str
    attribute: AttributeType
    value: FactValueOutput


class FactExtractionResult(BaseModel):
    facts: list[ExtractedFact] = Field(default_factory=list)


class OpenAIResponsesFactClient:
    """Adapter for OpenAI Responses API structured fact extraction."""

    def __init__(self, *, api_key: str | None = None, sdk_client: Any | None = None) -> None:
        if sdk_client is not None:
            self._client = sdk_client
            return
        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAI SDK is required for OpenAIResponsesFactClient. Install 'openai'."
            ) from exc
        self._client = OpenAI(api_key=api_key)

    def extract_facts(
        self,
        *,
        model: str,
        prompt: str,
        evidence_unit: dict[str, Any],
        entities: list[dict[str, Any]],
        prompt_id: str,
    ) -> dict[str, Any]:
        response = self._client.responses.parse(
            model=model,
            input=[{"role": "user", "content": prompt}],
            text_format=FactExtractionResult,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, FactExtractionResult):
            return parsed.model_dump()
        return FactExtractionResult.model_validate(parsed).model_dump()


class AsyncOpenAIResponsesFactClient:
    """Async adapter for OpenAI Responses API structured fact extraction."""

    def __init__(self, *, api_key: str | None = None, sdk_client: Any | None = None) -> None:
        if sdk_client is not None:
            self._client = sdk_client
            return
        try:
            from openai import AsyncOpenAI  # type: ignore[import-untyped]
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAI SDK is required for AsyncOpenAIResponsesFactClient. Install 'openai'."
            ) from exc
        self._client = AsyncOpenAI(api_key=api_key)

    async def extract_facts(
        self,
        *,
        model: str,
        prompt: str,
        evidence_unit: dict[str, Any],
        entities: list[dict[str, Any]],
        prompt_id: str,
    ) -> dict[str, Any]:
        response = await self._client.responses.parse(
            model=model,
            input=[{"role": "user", "content": prompt}],
            text_format=FactExtractionResult,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, FactExtractionResult):
            return parsed.model_dump()
        return FactExtractionResult.model_validate(parsed).model_dump()


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_model_id() -> str:
    policy_path = Path(__file__).resolve().parents[3] / "MODEL_POLICY.json"
    if not policy_path.exists():
        return "fast_smart"
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    actions = payload.get("actions", {})
    models = payload.get("models", {})
    role = actions.get("structured_generation", "fast_smart")
    return models.get(role, role)


def _sanitize_id(raw: str, prefix: str = "fact") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]+", "_", raw)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_.:-")
    if not cleaned:
        cleaned = prefix
    if cleaned[0].isdigit():
        cleaned = f"{prefix}_{cleaned}"
    return cleaned


def _compute_fact_id(subject_entity_id: str, attribute: str, label: str) -> str:
    payload = f"{subject_entity_id}|{attribute}|{label}"
    digest = blake3.blake3(payload.encode("utf-8")).hexdigest()[:12]
    subject_short = subject_entity_id.removeprefix("ent_")
    return _sanitize_id(f"fact_{subject_short}_{attribute}_{digest}")


def derive_truth_state(canon_layer: str, source_class: str) -> tuple[str, str]:
    """Return (truth_state, source_authority) for given layer/class combo."""
    return _TRUTH_STATE_MAP.get((canon_layer, source_class), ("CANON", "unknown"))


def _entity_context_fingerprint(entities: list[dict[str, Any]]) -> str:
    ids = sorted(str(e.get("entity_id", "")) for e in entities)
    return blake3.blake3("|".join(ids).encode("utf-8")).hexdigest()[:16]


def _cache_key(unit: dict[str, Any], model_id: str, entity_fp: str) -> str:
    text_fp = blake3.blake3(str(unit.get("text", "")).encode("utf-8")).hexdigest()
    payload = f"{text_fp}|{_PROMPT_ID}|{model_id}|{entity_fp}"
    return blake3.blake3(payload.encode("utf-8")).hexdigest()


def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


def _build_prompt(unit: dict[str, Any], entities: list[dict[str, Any]]) -> str:
    entities_minimal = [
        {
            "entity_id": e.get("entity_id"),
            "display_name": e.get("display_name"),
            "entity_type": e.get("entity_type"),
        }
        for e in entities
    ]
    evidence_id = unit.get("evidence_id", "unknown")
    text = unit.get("text", "")

    return (
        "You are a fact extraction agent for a TTRPG worldbuilding system.\n"
        "For each entity mentioned in this evidence unit text, extract what this text "
        "ASSERTS about it.\n"
        "Only extract facts that are directly stated or strongly implied. "
        "Do not invent facts.\n\n"
        f"Entities (use these exact entity_ids as subject_entity_id):\n"
        f"{json.dumps(entities_minimal, ensure_ascii=False)}\n\n"
        "Attribute enum: species, role, rank_or_title, faction, current_location, "
        "physical_condition, mental_state, loyalty_or_alignment_context, "
        "relationship_tags, operational_status, portrayal_notes, unresolved_questions, "
        "source_comments, history, geography, demographics, defenses, economy, "
        "governance, atmosphere, goals\n\n"
        "Value kinds:\n"
        "- scalar: simple factual value\n"
        "- state: current condition that may change\n"
        "- entity_ref: reference to another entity (include entity_id field)\n"
        "- set: list of items (include values array)\n"
        "- interpretive: requires interpretation_level "
        "(direct_assertion | derived_summary | interpretive_inference) "
        "and strength (weak | moderate | strong)\n\n"
        "For value.normalized: use machine-friendly snake_case slug "
        "(e.g. 'trade_hub:brewing:crafts'). Use null if not applicable.\n\n"
        "For fact_id: use format 'fact_<entity_suffix>_<attribute>_<short_descriptor>'\n\n"
        f"Evidence unit ID: {evidence_id}\n\n"
        f"Text:\n{text}"
    )


def _build_fact_value_dict(fv: FactValueOutput) -> dict[str, Any]:
    kind = fv.kind
    set_values: list[str] = []

    if kind == "entity_ref" and not fv.entity_id:
        kind = "scalar"
    if kind == "set":
        set_values = list(dict.fromkeys(v for v in (fv.values or []) if v))
        if not set_values:
            kind = "scalar"

    d: dict[str, Any] = {"kind": kind, "label": fv.label, "normalized": fv.normalized}

    if kind == "entity_ref":
        d["entity_id"] = fv.entity_id
    if kind == "set":
        d["values"] = set_values
    if kind == "interpretive":
        d["interpretation_level"] = fv.interpretation_level or "direct_assertion"
        d["strength"] = fv.strength or "moderate"

    return d


def _build_fact_record(
    extracted: ExtractedFact,
    *,
    evidence_unit: dict[str, Any],
    truth_state: str,
    source_authority: str,
    entity_id_set: set[str],
) -> dict[str, Any] | None:
    if extracted.subject_entity_id not in entity_id_set:
        return None
    if extracted.attribute not in _VALID_ATTRIBUTES:
        return None

    now_iso = _now_utc_iso()
    evidence_id = str(evidence_unit.get("evidence_id", "unknown"))
    inferred_session = evidence_unit.get("inferred_session")
    try:
        asserted_in_session = int(inferred_session) if inferred_session is not None else None
    except (TypeError, ValueError):
        asserted_in_session = None
    source_order = evidence_unit.get("source_order_index")
    try:
        sequence_index = int(source_order) if source_order is not None else None
    except (TypeError, ValueError):
        sequence_index = None

    fact_id = _compute_fact_id(
        extracted.subject_entity_id, extracted.attribute, extracted.value.label
    )
    value_dict = _build_fact_value_dict(extracted.value)

    return {
        "schema_version": "0.1.0",
        "created_at": now_iso,
        "updated_at": now_iso,
        "record_status": "active",
        "fact_id": fact_id,
        "subject_entity_id": extracted.subject_entity_id,
        "attribute": extracted.attribute,
        "value": value_dict,
        "truth_state": truth_state,
        "source_authority": source_authority,
        "evidence_ids": [evidence_id],
        "asserted_in_session": asserted_in_session,
        "sequence_index_within_session": sequence_index,
    }


def _dedup_key(fact: dict[str, Any]) -> str:
    subject = fact["subject_entity_id"]
    attr = fact["attribute"]
    normalized = fact["value"].get("normalized") or ""
    if not normalized:
        normalized = re.sub(r"[^a-z0-9]+", "_", fact["value"]["label"].lower()).strip("_")[:80]
    return f"{subject}|{attr}|{normalized.lower()}"


def _deduplicate_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for fact in facts:
        key = _dedup_key(fact)
        if key in seen:
            existing = seen[key]
            combined = list(dict.fromkeys(existing["evidence_ids"] + fact["evidence_ids"]))
            existing["evidence_ids"] = combined
            if len(fact["value"]["label"]) > len(existing["value"]["label"]):
                existing["value"]["label"] = fact["value"]["label"]
                existing["fact_id"] = fact["fact_id"]
        else:
            seen[key] = fact
    return list(seen.values())


async def _call_extractor(
    unit: dict[str, Any],
    entities: list[dict[str, Any]],
    model_id: str,
    openai_client: Any | None,
    *,
    allow_heuristic_fallback: bool,
) -> FactExtractionResult:
    if openai_client is None:
        if not allow_heuristic_fallback:
            raise ValueError(
                "Heuristic fallback is disabled; provide an openai_client for fact extraction."
            )
        return FactExtractionResult(facts=[])

    if not hasattr(openai_client, "extract_facts"):
        raise ValueError("openai_client must expose extract_facts(...)")

    payload = openai_client.extract_facts(
        model=model_id,
        prompt=_build_prompt(unit, entities),
        evidence_unit=unit,
        entities=entities,
        prompt_id=_PROMPT_ID,
    )
    if inspect.isawaitable(payload):
        payload = await payload
    return FactExtractionResult.model_validate(payload)


async def extract_facts_batch(
    evidence_units: list[dict[str, Any]],
    *,
    entities: list[dict[str, Any]],
    canon_layer: str,
    campaign_id: str | None,
    source_class: str,
    model: str | None = None,
    concurrency: int = 8,
    cache_dir: Path | None = None,
    openai_client: Any | None = None,
    allow_heuristic_fallback: bool = True,
) -> list[dict[str, Any]]:
    model_id = model or _load_model_id()
    cache_root = (
        Path(cache_dir) if cache_dir is not None else (Path.cwd() / ".fact_extractor_cache")
    )
    cache_root.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(max(1, concurrency))
    entity_fp = _entity_context_fingerprint(entities)
    entity_id_set = {str(e.get("entity_id", "")) for e in entities}
    truth_state, source_authority = derive_truth_state(canon_layer, source_class)
    stats = {"completed": 0, "cache_hits": 0, "cache_misses": 0}
    progress_step = max(10, len(evidence_units) // 10) if evidence_units else 10
    logger.info(
        "fact_extractor start units=%d entities=%d concurrency=%d model=%s cache_dir=%s",
        len(evidence_units),
        len(entities),
        concurrency,
        model_id,
        cache_root,
    )

    async def process_unit(unit: dict[str, Any]) -> FactExtractionResult:
        evidence_id = str(unit.get("evidence_id", "unknown"))
        key = _cache_key(unit, model_id, entity_fp)
        cache_file = _cache_path(cache_root, key)
        if cache_file.exists():
            stats["cache_hits"] += 1
            stats["completed"] += 1
            logger.debug("fact_extractor unit=%s cache=hit", evidence_id)
            if stats["completed"] % progress_step == 0:
                logger.info(
                    "fact_extractor progress completed=%d/%d cache_hits=%d cache_misses=%d",
                    stats["completed"],
                    len(evidence_units),
                    stats["cache_hits"],
                    stats["cache_misses"],
                )
            return FactExtractionResult.model_validate(
                json.loads(cache_file.read_text(encoding="utf-8"))
            )
        async with semaphore:
            stats["cache_misses"] += 1
            logger.debug("fact_extractor unit=%s cache=miss", evidence_id)
            result = await _call_extractor(
                unit=unit,
                entities=entities,
                model_id=model_id,
                openai_client=openai_client,
                allow_heuristic_fallback=allow_heuristic_fallback,
            )
            cache_file.write_text(
                result.model_dump_json(indent=2),
                encoding="utf-8",
            )
            stats["completed"] += 1
            logger.debug(
                "fact_extractor unit=%s extracted_facts=%d",
                evidence_id,
                len(result.facts),
            )
            if stats["completed"] % progress_step == 0:
                logger.info(
                    "fact_extractor progress completed=%d/%d cache_hits=%d cache_misses=%d",
                    stats["completed"],
                    len(evidence_units),
                    stats["cache_hits"],
                    stats["cache_misses"],
                )
            return result

    results = await asyncio.gather(*(process_unit(unit) for unit in evidence_units))

    records: list[dict[str, Any]] = []
    for unit, result in zip(evidence_units, results, strict=False):
        for extracted in result.facts:
            record = _build_fact_record(
                extracted,
                evidence_unit=unit,
                truth_state=truth_state,
                source_authority=source_authority,
                entity_id_set=entity_id_set,
            )
            if record is not None:
                records.append(record)

    records = _deduplicate_facts(records)
    validate_many(records, "fact.schema.json")
    logger.info(
        "fact_extractor done units=%d records=%d cache_hits=%d cache_misses=%d truth_state=%s",
        len(evidence_units),
        len(records),
        stats["cache_hits"],
        stats["cache_misses"],
        truth_state,
    )
    return records


def run_fact_extraction(
    evidence_units: list[dict[str, Any]],
    *,
    entities: list[dict[str, Any]],
    canon_layer: str,
    campaign_id: str | None,
    source_class: str,
    model: str | None = None,
    concurrency: int = 8,
    cache_dir: Path | None = None,
    openai_client: Any | None = None,
    allow_heuristic_fallback: bool = True,
) -> list[dict[str, Any]]:
    return asyncio.run(
        extract_facts_batch(
            evidence_units,
            entities=entities,
            canon_layer=canon_layer,
            campaign_id=campaign_id,
            source_class=source_class,
            model=model,
            concurrency=concurrency,
            cache_dir=cache_dir,
            openai_client=openai_client,
            allow_heuristic_fallback=allow_heuristic_fallback,
        )
    )
