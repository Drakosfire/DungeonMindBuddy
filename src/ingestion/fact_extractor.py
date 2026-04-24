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
from src.ingestion.entity_extractor import UsageStats, _usage_dict_from_openai_response
from src.llm.api_client import DungeonMindApiClient

_PROMPT_ID = "phase_c_pass2_fact_extraction_v3_prompt_cache"

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
    "event_outcome",
    "event_progression",
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
    "event_outcome",
    "event_progression",
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


class UnitFactResult(BaseModel):
    """Per-slot result in a batched call; index matches section order in the user prompt."""

    unit_index: int = Field(ge=0, description="0-based index of the evidence section, matching the prompt header.")
    facts: list[ExtractedFact] = Field(default_factory=list)


class BatchedFactExtractionResult(BaseModel):
    results: list[UnitFactResult] = Field(default_factory=list)


class OpenAIResponsesFactClient:
    """Adapter for OpenAI Responses API structured fact extraction."""

    def __init__(self, *, api_key: str | None = None, sdk_client: Any | None = None) -> None:
        if sdk_client is not None:
            self._client = sdk_client
            self._api_client = DungeonMindApiClient.wrap(self._client)
            return
        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAI SDK is required for OpenAIResponsesFactClient. Install 'openai'."
            ) from exc
        self._client = OpenAI(api_key=api_key)
        self._api_client = DungeonMindApiClient.wrap(self._client)

    def extract_facts(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        evidence_unit: dict[str, Any],
        entities: list[dict[str, Any]],
        prompt_id: str,
    ) -> dict[str, Any]:
        response = self._api_client.responses_parse(
            action="fact_extractor.extract",
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=FactExtractionResult,
        ).response
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, FactExtractionResult):
            result = parsed.model_dump()
        else:
            result = FactExtractionResult.model_validate(parsed).model_dump()
        result["_usage"] = _usage_dict_from_openai_response(response)
        return result

    def extract_facts_batched(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        prompt_id: str,
    ) -> dict[str, Any]:
        response = self._api_client.responses_parse(
            action="fact_extractor.extract_batched",
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=BatchedFactExtractionResult,
        ).response
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, BatchedFactExtractionResult):
            result = parsed.model_dump()
        else:
            result = BatchedFactExtractionResult.model_validate(parsed).model_dump()
        result["_usage"] = _usage_dict_from_openai_response(response)
        return result


class AsyncOpenAIResponsesFactClient:
    """Async adapter for OpenAI Responses API structured fact extraction."""

    def __init__(self, *, api_key: str | None = None, sdk_client: Any | None = None) -> None:
        if sdk_client is not None:
            self._client = sdk_client
            self._api_client = DungeonMindApiClient.wrap(self._client)
            return
        try:
            from openai import AsyncOpenAI  # type: ignore[import-untyped]
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAI SDK is required for AsyncOpenAIResponsesFactClient. Install 'openai'."
            ) from exc
        self._client = AsyncOpenAI(api_key=api_key)
        self._api_client = DungeonMindApiClient.wrap(self._client)

    async def extract_facts(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        evidence_unit: dict[str, Any],
        entities: list[dict[str, Any]],
        prompt_id: str,
    ) -> dict[str, Any]:
        response = (
            await self._api_client.responses_parse_async(
                action="fact_extractor.extract_async",
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                text_format=FactExtractionResult,
            )
        ).response
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, FactExtractionResult):
            result = parsed.model_dump()
        else:
            result = FactExtractionResult.model_validate(parsed).model_dump()
        result["_usage"] = _usage_dict_from_openai_response(response)
        return result

    async def extract_facts_batched(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        prompt_id: str,
    ) -> dict[str, Any]:
        response = (
            await self._api_client.responses_parse_async(
                action="fact_extractor.extract_batched_async",
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                text_format=BatchedFactExtractionResult,
            )
        ).response
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, BatchedFactExtractionResult):
            result = parsed.model_dump()
        else:
            result = BatchedFactExtractionResult.model_validate(parsed).model_dump()
        result["_usage"] = _usage_dict_from_openai_response(response)
        return result

    async def aclose(self) -> None:
        closer = getattr(self._client, "aclose", None)
        if callable(closer):
            maybe = closer()
            if inspect.isawaitable(maybe):
                await maybe
            return
        closer = getattr(self._client, "close", None)
        if callable(closer):
            maybe = closer()
            if inspect.isawaitable(maybe):
                await maybe


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


def _entity_aliases(entity: dict[str, Any]) -> list[str]:
    aliases: list[str] = []
    display_name = str(entity.get("display_name", "")).strip()
    if display_name:
        aliases.append(display_name)
    for alias in entity.get("aliases", []):
        name = str(alias).strip()
        if name:
            aliases.append(name)
    deduped: list[str] = []
    seen: set[str] = set()
    for name in aliases:
        key = name.lower()
        if key in seen:
            continue
        deduped.append(name)
        seen.add(key)
    return deduped


def _normalize_entity_surface(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.strip().lower()).strip()


def _build_entity_name_index(
    entities: list[dict[str, Any]],
) -> dict[str, list[str]]:
    by_name: dict[str, list[str]] = {}
    for entity in entities:
        entity_id = str(entity.get("entity_id", "")).strip()
        if not entity_id:
            continue
        for name in _entity_aliases(entity):
            key = _normalize_entity_surface(name)
            if not key:
                continue
            by_name.setdefault(key, [])
            if entity_id not in by_name[key]:
                by_name[key].append(entity_id)
    return by_name


def _build_entity_matchers(
    entities: list[dict[str, Any]],
) -> dict[str, list[re.Pattern[str]]]:
    matchers: dict[str, list[re.Pattern[str]]] = {}
    for entity in entities:
        entity_id = str(entity.get("entity_id", "")).strip()
        if not entity_id:
            continue
        patterns: list[re.Pattern[str]] = []
        for name in _entity_aliases(entity):
            escaped = re.escape(name)
            if not escaped:
                continue
            patterns.append(re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE))
        if patterns:
            matchers[entity_id] = patterns
    return matchers


def _candidate_entity_ids_for_text(
    text: str,
    matchers: dict[str, list[re.Pattern[str]]],
) -> list[str]:
    matched: list[str] = []
    for entity_id, patterns in matchers.items():
        if any(pattern.search(text) for pattern in patterns):
            matched.append(entity_id)
    return sorted(matched)


_GROUP_VARIANT_SUFFIXES = (
    " cultists",
    " cult members",
    " protesters",
    " protestors",
    " followers",
)

_GENERIC_PLACE_NAMES = {
    "the city",
    "city",
    "the town",
    "town",
    "strategic trade hub",
    "trade hub",
}


def _resolve_subject_entity_id(
    *,
    subject_entity_id: str,
    attribute: str,
    value_label: str,
    evidence_text: str,
    entities_by_id: dict[str, dict[str, Any]],
    entity_matchers: dict[str, list[re.Pattern[str]]],
    entity_name_index: dict[str, list[str]],
) -> str:
    entity = entities_by_id.get(subject_entity_id)
    if entity is None:
        return subject_entity_id

    display_name = _normalize_entity_surface(str(entity.get("display_name", "")))
    if display_name:
        for suffix in _GROUP_VARIANT_SUFFIXES:
            if not display_name.endswith(suffix):
                continue
            base = display_name[: -len(suffix)].strip()
            if not base:
                continue
            candidates = entity_name_index.get(base, [])
            for candidate_id in candidates:
                if candidate_id == subject_entity_id:
                    continue
                candidate = entities_by_id.get(candidate_id, {})
                candidate_class = str(
                    candidate.get("entity_class", candidate.get("entity_type", ""))
                ).strip().lower()
                if candidate_class == "group":
                    return candidate_id

    mentioned = _candidate_entity_ids_for_text(evidence_text, entity_matchers)
    mentioned_places = [
        eid
        for eid in mentioned
        if eid != subject_entity_id
        and str(
            entities_by_id.get(eid, {}).get(
                "entity_class",
                entities_by_id.get(eid, {}).get("entity_type", ""),
            )
        )
        .strip()
        .lower()
        in {"place", "location"}
    ]
    dominant_place_id: str | None = None
    if mentioned_places:
        dominant_place_id = max(
            mentioned_places,
            key=lambda eid: len(entities_by_id.get(eid, {}).get("source_mention_ids", [])),
        )

    if display_name in _GENERIC_PLACE_NAMES and dominant_place_id is None:
        all_place_ids = [
            eid
            for eid, candidate in entities_by_id.items()
            if eid != subject_entity_id
            and str(candidate.get("entity_class", candidate.get("entity_type", "")))
            .strip()
            .lower()
            in {"place", "location"}
        ]
        if all_place_ids:
            dominant_place_id = max(
                all_place_ids,
                key=lambda eid: len(entities_by_id.get(eid, {}).get("source_mention_ids", [])),
            )

    if display_name in _GENERIC_PLACE_NAMES and dominant_place_id is not None:
        return dominant_place_id

    subject_class = str(
        entity.get("entity_class", entity.get("entity_type", ""))
    ).strip().lower()
    value_lower = value_label.lower()
    if dominant_place_id is not None and subject_class in {"group", "concept", "object", "event"}:
        if attribute == "history" and (
            "settlers" in value_lower
            or "founded" in value_lower
            or "settlement" in value_lower
            or "pioneer" in value_lower
        ):
            return dominant_place_id
        if attribute == "economy" and (
            "industry" in value_lower
            or "trade" in value_lower
            or "brewing" in value_lower
            or "craft" in value_lower
            or "fishing" in value_lower
            or "agriculture" in value_lower
            or "workshop" in value_lower
            or "farmland" in value_lower
        ):
            return dominant_place_id
        if subject_class in {"concept", "object", "event"} and attribute == "operational_status" and (
            "festival" in value_lower
            or "toll" in value_lower
            or "congested" in value_lower
            or "bottleneck" in value_lower
            or "crowd" in value_lower
            or "entry" in value_lower
            or "tense" in value_lower
        ):
            return dominant_place_id

    return subject_entity_id


def _cache_key(unit: dict[str, Any], model_id: str, entity_fp: str) -> str:
    text_fp = blake3.blake3(str(unit.get("text", "")).encode("utf-8")).hexdigest()
    payload = f"{text_fp}|{_PROMPT_ID}|{model_id}|{entity_fp}"
    return blake3.blake3(payload.encode("utf-8")).hexdigest()


def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


def _build_fact_system_prompt() -> str:
    """Static fact-extraction instructions; sized for OpenAI prefix caching."""
    return (
        "You are a fact extraction agent for a TTRPG worldbuilding system.\n\n"
        "TASK: For each entity listed in the user message, extract what the evidence unit text "
        "ASSERTS about that entity. Only extract facts that are directly stated or strongly implied. "
        "Do not invent facts. If the text does not support a fact for an entity, omit it.\n\n"
        "OUTPUT: Return JSON {\"facts\": [...]} with no markdown fences.\n\n"
        "ATTRIBUTE ENUM (subject_entity_id must be one of the provided entity_id values):\n"
        "species, role, rank_or_title, faction, current_location, physical_condition, mental_state, "
        "loyalty_or_alignment_context, relationship_tags, operational_status, event_outcome, "
        "event_progression, portrayal_notes, "
        "unresolved_questions, source_comments, history, geography, demographics, defenses, economy, "
        "governance, atmosphere, goals\n\n"
        "ATTRIBUTE GUIDANCE:\n"
        "- species: biological or species label when explicit.\n"
        "- role / rank_or_title: jobs, offices, formal titles.\n"
        "- faction: organizational membership or allegiance.\n"
        "- current_location: whereabouts asserted in the passage.\n"
        "- physical_condition / mental_state: wounds, exhaustion, mood when stated.\n"
        "- loyalty_or_alignment_context: devotion, moral stance, political leaning when explicit.\n"
        "- relationship_tags: named relationships (ally, rival, sibling) when explicit.\n"
        "- operational_status: readiness, siege state, business open/closed, etc.\n"
        "- event_outcome: terminal or consequential result of an event/scene for the subject.\n"
        "- event_progression: sequence step, transition, or before/after movement in an event timeline.\n"
        "- portrayal_notes: how something is depicted (tone, aesthetic) when factual in text.\n"
        "- unresolved_questions: explicit open threads the text raises.\n"
        "- source_comments: meta about the document itself if present.\n"
        "- history / geography / demographics / defenses / economy / governance / atmosphere / goals: "
        "setting assertions at city or place scale.\n\n"
        "VALUE KINDS (FactValueOutput):\n"
        "- scalar: simple factual value (label + optional normalized).\n"
        "- state: current condition that may change over time.\n"
        "- entity_ref: reference to another entity; include entity_id when known from context.\n"
        "- set: list of items; include values array.\n"
        "- interpretive: requires interpretation_level "
        "(direct_assertion | derived_summary | interpretive_inference) "
        "and strength (weak | moderate | strong).\n\n"
        "VALUE FIELD RULES:\n"
        "- label: human-readable assertion text grounded in the evidence.\n"
        "- normalized: machine-friendly snake_case slug (e.g. 'trade_hub:brewing:crafts'); null if N/A.\n"
        "- For entity_ref, entity_id must match a provided entity when possible.\n"
        "- For set, values must be distinct strings.\n\n"
        "FACT ID HINTS:\n"
        "Prefer fact_id shaped like 'fact_<entity_suffix>_<attribute>_<short_descriptor>' using stable slugs.\n\n"
        "EXTRACTED FACT SCHEMA:\n"
        "- fact_id: string, unique per fact.\n"
        "- subject_entity_id: must equal an entity_id from the user list.\n"
        "- attribute: one enum value above.\n"
        "- value: object with kind, label, normalized, optional entity_id, values, interpretation_level, strength.\n\n"
        "QUALITY BAR:\n"
        "- One fact row per distinct asserted proposition; merge duplicates only when truly identical.\n"
        "- Do not copy headings or section titles as facts unless they assert world truth.\n"
        "- Prefer shorter labels that remain self-contained.\n\n"
        "EDGE CASES:\n"
        "- Multiple entities in one sentence: emit separate facts with correct subject_entity_id for each.\n"
        "- Comparative statements ('older than', 'richer than') may need interpretive value kind with moderate strength.\n"
        "- Negation ('not allied with X') still counts as an assertion; use clear label text.\n"
        "- Historical versus present tense: use history or current_location as appropriate to the assertion.\n"
        "- Lists of industries, districts, or factions: prefer set kind with values when the text enumerates.\n\n"
        "ANTI-PATTERNS:\n"
        "- Do not attach facts to the wrong subject_entity_id just because names are similar.\n"
        "- Do not infer relationships not supported by the passage.\n"
        "- Do not output facts for entities not present in the user-provided entity list.\n"
        "- Do not duplicate the same semantic fact under two attributes unless the text clearly supports both.\n\n"
        "NORMALIZATION EXAMPLES:\n"
        "- 'Temple District' near waterways -> normalized like 'district:temple:waterfront' when sensible.\n"
        "- Military readiness -> operational_status with scalar or state as fits the wording.\n"
        "- 'The Wolf was killed by Bonogo' -> event_outcome, kind=state or scalar.\n"
        "- 'After stalling in council chamber, he fled to sewers' -> event_progression.\n"
        "- Population counts -> demographics with numeric label preserved in label field.\n"
    )


def _build_fact_user_prompt(unit: dict[str, Any], entities: list[dict[str, Any]]) -> str:
    entities_minimal = [
        {
            "entity_id": e.get("entity_id"),
            "display_name": e.get("display_name"),
            "entity_class": e.get("entity_class", e.get("entity_type")),
        }
        for e in entities
    ]
    text = unit.get("text", "")
    return (
        "Entities (use these exact entity_ids as subject_entity_id):\n"
        f"{json.dumps(entities_minimal, ensure_ascii=False)}\n\n"
        f"Text:\n{text}"
    )


def _prompt_entities_for_unit(
    unit: dict[str, Any],
    *,
    entities: list[dict[str, Any]],
    entities_by_id: dict[str, dict[str, Any]],
    entity_matchers: dict[str, list[re.Pattern[str]]],
    entity_fp: str,
) -> tuple[list[dict[str, Any]], str]:
    unit_text = str(unit.get("text", ""))
    candidate_entity_ids = _candidate_entity_ids_for_text(unit_text, entity_matchers)
    prompt_entities = (
        [entities_by_id[eid] for eid in candidate_entity_ids if eid in entities_by_id]
        if candidate_entity_ids
        else entities
    )
    prompt_entity_fp = _entity_context_fingerprint(prompt_entities) if prompt_entities else entity_fp
    return prompt_entities, prompt_entity_fp


def _build_batched_fact_user_prompt(
    units_with_entities: list[tuple[dict[str, Any], list[dict[str, Any]]]],
) -> str:
    sections: list[str] = []
    for slot_idx, (unit, prompt_entities) in enumerate(units_with_entities):
        entities_minimal = [
            {
                "entity_id": e.get("entity_id"),
                "display_name": e.get("display_name"),
                "entity_class": e.get("entity_class", e.get("entity_type")),
            }
            for e in prompt_entities
        ]
        text = unit.get("text", "")
        sections.append(
            f"--- unit_index: {slot_idx} ---\n"
            f"Entities (use these exact entity_ids as subject_entity_id):\n"
            f"{json.dumps(entities_minimal, ensure_ascii=False)}\n\n"
            f"Text:\n{text}"
        )
    joined = "\n\n".join(sections)
    n = len(units_with_entities)
    last = n - 1 if n else 0
    return (
        "Process each evidence unit below. Return JSON with shape "
        '{"results": [{"unit_index": <int>, "facts": [...]}, ...]} only (no markdown fences). '
        "Include exactly one results entry per section. For each entry, unit_index must be the integer "
        f"from that section's header (0 through {last}). Emit facts only for entity_ids listed in that section. "
        "Do not invent or copy internal database ids for unit_index.\n\n"
        + joined
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
    resolved_subject_entity_id: str | None = None,
) -> dict[str, Any] | None:
    subject_entity_id = resolved_subject_entity_id or extracted.subject_entity_id
    if subject_entity_id not in entity_id_set:
        return None
    if extracted.attribute not in _VALID_ATTRIBUTES:
        return None

    now_iso = _now_utc_iso()
    evidence_id = str(evidence_unit.get("evidence_id", "unknown"))
    inferred_session = evidence_unit.get("document_session")
    if inferred_session is None:
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
        subject_entity_id, extracted.attribute, extracted.value.label
    )
    value_dict = _build_fact_value_dict(extracted.value)

    record: dict[str, Any] = {
        "schema_version": "0.1.0",
        "created_at": now_iso,
        "updated_at": now_iso,
        "record_status": "active",
        "fact_id": fact_id,
        "subject_entity_id": subject_entity_id,
        "attribute": extracted.attribute,
        "value": value_dict,
        "truth_state": truth_state,
        "source_authority": source_authority,
        "evidence_ids": [evidence_id],
        "asserted_in_session": asserted_in_session,
        "sequence_index_within_session": sequence_index,
    }
    raw_anchors = evidence_unit.get("source_anchors")
    if isinstance(raw_anchors, list) and raw_anchors:
        record["source_anchors"] = list(raw_anchors)
    return record


def _dedup_key(fact: dict[str, Any]) -> str:
    subject = fact["subject_entity_id"]
    attr = fact["attribute"]
    normalized = fact["value"].get("normalized") or ""
    if not normalized:
        normalized = re.sub(r"[^a-z0-9]+", "_", fact["value"]["label"].lower()).strip("_")[:80]
    return f"{subject}|{attr}|{normalized.lower()}"


def _merge_source_anchors(
    left: list[Any] | None, right: list[Any] | None
) -> list[dict[str, Any]]:
    """Union anchors from two evidence units, keyed by content_hash (dedup merge)."""
    by_hash: dict[str, dict[str, Any]] = {}
    for seq in (left or [], right or []):
        for item in seq:
            if not isinstance(item, dict):
                continue
            h = str(item.get("content_hash", "")).strip()
            if h and h not in by_hash:
                by_hash[h] = item
    return list(by_hash.values())


def _deduplicate_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for fact in facts:
        key = _dedup_key(fact)
        if key in seen:
            existing = seen[key]
            combined = list(dict.fromkeys(existing["evidence_ids"] + fact["evidence_ids"]))
            existing["evidence_ids"] = combined
            merged_anchors = _merge_source_anchors(
                existing.get("source_anchors") if isinstance(existing.get("source_anchors"), list) else [],
                fact.get("source_anchors") if isinstance(fact.get("source_anchors"), list) else [],
            )
            if merged_anchors:
                existing["source_anchors"] = merged_anchors
            if len(fact["value"]["label"]) > len(existing["value"]["label"]):
                existing["value"]["label"] = fact["value"]["label"]
                existing["fact_id"] = fact["fact_id"]
        else:
            seen[key] = fact
    return list(seen.values())


def _pop_usage_from_fact_payload(payload: Any) -> tuple[dict[str, Any], dict[str, int]]:
    if not isinstance(payload, dict):
        raise TypeError("extract_facts payload must be a dict")
    raw = payload.pop("_usage", None) or {}
    usage = {
        "input_tokens": int(raw.get("input_tokens", 0) or 0),
        "output_tokens": int(raw.get("output_tokens", 0) or 0),
        "cached_tokens": int(raw.get("cached_tokens", 0) or 0),
    }
    return payload, usage


async def _call_extractor(
    unit: dict[str, Any],
    entities: list[dict[str, Any]],
    model_id: str,
    openai_client: Any | None,
    *,
    allow_heuristic_fallback: bool,
    system_prompt: str,
) -> tuple[FactExtractionResult, dict[str, int]]:
    if openai_client is None:
        if not allow_heuristic_fallback:
            raise ValueError(
                "Heuristic fallback is disabled; provide an openai_client for fact extraction."
            )
        return FactExtractionResult(facts=[]), {}

    if not hasattr(openai_client, "extract_facts"):
        raise ValueError("openai_client must expose extract_facts(...)")

    payload = openai_client.extract_facts(
        model=model_id,
        system_prompt=system_prompt,
        user_prompt=_build_fact_user_prompt(unit, entities),
        evidence_unit=unit,
        entities=entities,
        prompt_id=_PROMPT_ID,
    )
    if inspect.isawaitable(payload):
        payload = await payload
    body, usage = _pop_usage_from_fact_payload(payload)
    return FactExtractionResult.model_validate(body), usage


async def extract_facts_batch(
    evidence_units: list[dict[str, Any]],
    *,
    entities: list[dict[str, Any]],
    canon_layer: str,
    campaign_id: str | None,
    source_class: str,
    model: str | None = None,
    concurrency: int = 8,
    batch_size: int = 1,
    cache_dir: Path | None = None,
    openai_client: Any | None = None,
    allow_heuristic_fallback: bool = True,
) -> dict[str, Any]:
    model_id = model or _load_model_id()
    cache_root = (
        Path(cache_dir) if cache_dir is not None else (Path.cwd() / ".fact_extractor_cache")
    )
    cache_root.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(max(1, concurrency))
    entity_fp = _entity_context_fingerprint(entities)
    entities_by_id = {
        str(entity.get("entity_id", "")).strip(): entity
        for entity in entities
        if str(entity.get("entity_id", "")).strip()
    }
    entity_name_index = _build_entity_name_index(entities)
    entity_matchers = _build_entity_matchers(entities)
    entity_id_set = {str(e.get("entity_id", "")) for e in entities}
    truth_state, source_authority = derive_truth_state(canon_layer, source_class)
    stats = {"completed": 0, "cache_hits": 0, "cache_misses": 0, "scoped_prompts": 0}
    progress_step = max(10, len(evidence_units) // 10) if evidence_units else 10
    effective_batch = max(1, batch_size)
    logger.info(
        "fact_extractor start units=%d entities=%d concurrency=%d batch_size=%d model=%s cache_dir=%s",
        len(evidence_units),
        len(entities),
        concurrency,
        effective_batch,
        model_id,
        cache_root,
    )

    fact_system_prompt = _build_fact_system_prompt()

    def _usage_for_call(udict: dict[str, int]) -> UsageStats:
        billed = openai_client is not None
        return UsageStats(
            input_tokens=udict.get("input_tokens", 0),
            output_tokens=udict.get("output_tokens", 0),
            cached_tokens=udict.get("cached_tokens", 0),
            api_calls=1 if billed else 0,
        )

    slot_results: list[FactExtractionResult | None] = [None] * len(evidence_units)
    misses: list[tuple[int, dict[str, Any], list[dict[str, Any]], str]] = []

    for i, unit in enumerate(evidence_units):
        evidence_id = str(unit.get("evidence_id", "unknown"))
        unit_text = str(unit.get("text", ""))
        candidate_entity_ids = _candidate_entity_ids_for_text(unit_text, entity_matchers)
        prompt_entities, prompt_entity_fp = _prompt_entities_for_unit(
            unit,
            entities=entities,
            entities_by_id=entities_by_id,
            entity_matchers=entity_matchers,
            entity_fp=entity_fp,
        )
        if candidate_entity_ids:
            stats["scoped_prompts"] += 1
        key = _cache_key(unit, model_id, prompt_entity_fp)
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
            slot_results[i] = FactExtractionResult.model_validate(
                json.loads(cache_file.read_text(encoding="utf-8"))
            )
            continue
        misses.append((i, unit, prompt_entities, prompt_entity_fp))

    total_usage = UsageStats()

    async def process_one(
        idx: int,
        unit: dict[str, Any],
        prompt_entities: list[dict[str, Any]],
        prompt_entity_fp: str,
    ) -> None:
        evidence_id = str(unit.get("evidence_id", "unknown"))
        key = _cache_key(unit, model_id, prompt_entity_fp)
        cache_file = _cache_path(cache_root, key)
        async with semaphore:
            stats["cache_misses"] += 1
            logger.debug("fact_extractor unit=%s cache=miss", evidence_id)
            result, udict = await _call_extractor(
                unit=unit,
                entities=prompt_entities,
                model_id=model_id,
                openai_client=openai_client,
                allow_heuristic_fallback=allow_heuristic_fallback,
                system_prompt=fact_system_prompt,
            )
            cache_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            slot_results[idx] = result
            total_usage.merge(_usage_for_call(udict))
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

    async def process_batch(
        chunk: list[tuple[int, dict[str, Any], list[dict[str, Any]], str]],
    ) -> None:
        if not chunk:
            return
        async with semaphore:
            for _ in chunk:
                stats["cache_misses"] += 1
            pairs_for_prompt = [(u, pe) for _, u, pe, _ in chunk]
            if openai_client is None:
                if not allow_heuristic_fallback:
                    raise ValueError(
                        "Heuristic fallback is disabled; provide an openai_client for fact extraction."
                    )
                for idx, unit, _pe, pfp in chunk:
                    evidence_id = str(unit.get("evidence_id", "unknown"))
                    key = _cache_key(unit, model_id, pfp)
                    cache_file = _cache_path(cache_root, key)
                    result = FactExtractionResult(facts=[])
                    cache_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                    slot_results[idx] = result
                    stats["completed"] += 1
                    logger.debug("fact_extractor unit=%s extracted_facts=0 (heuristic)", evidence_id)
                    if stats["completed"] % progress_step == 0:
                        logger.info(
                            "fact_extractor progress completed=%d/%d cache_hits=%d cache_misses=%d",
                            stats["completed"],
                            len(evidence_units),
                            stats["cache_hits"],
                            stats["cache_misses"],
                        )
                return

            if not hasattr(openai_client, "extract_facts_batched"):
                raise ValueError(
                    "openai_client must expose extract_facts_batched(...) when batch_size > 1."
                )

            user_prompt = _build_batched_fact_user_prompt(pairs_for_prompt)
            payload = openai_client.extract_facts_batched(
                model=model_id,
                system_prompt=fact_system_prompt,
                user_prompt=user_prompt,
                prompt_id=_PROMPT_ID,
            )
            if inspect.isawaitable(payload):
                payload = await payload
            body, udict = _pop_usage_from_fact_payload(payload)
            parsed = BatchedFactExtractionResult.model_validate(body)
            by_slot: dict[int, UnitFactResult] = {}
            for row in parsed.results:
                ui = row.unit_index
                if ui in by_slot:
                    logger.warning(
                        "fact_extractor batched call duplicate unit_index=%s (using last result)",
                        ui,
                    )
                by_slot[ui] = row
            expected_idx = set(range(len(chunk)))
            returned_idx = set(by_slot.keys())
            missing_idx = expected_idx - returned_idx
            extra_idx = returned_idx - expected_idx
            if missing_idx:
                logger.warning(
                    "fact_extractor batched call missing unit_index slots: %s",
                    sorted(missing_idx),
                )
            if extra_idx:
                logger.warning(
                    "fact_extractor batched call unexpected unit_index values: %s",
                    sorted(extra_idx),
                )
            total_usage.merge(_usage_for_call(udict))
            for local_j, (idx, unit, _pe, pfp) in enumerate(chunk):
                evidence_id = str(unit.get("evidence_id", "unknown"))
                key = _cache_key(unit, model_id, pfp)
                cache_file = _cache_path(cache_root, key)
                row = by_slot.get(local_j)
                if row is None:
                    result = FactExtractionResult(facts=[])
                else:
                    result = FactExtractionResult(facts=list(row.facts))
                cache_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                slot_results[idx] = result
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

    try:
        tasks: list[Any] = []
        if effective_batch <= 1:
            for idx, unit, pe, pfp in misses:
                tasks.append(process_one(idx, unit, pe, pfp))
        else:
            for batch_i in range(0, len(misses), effective_batch):
                tasks.append(process_batch(misses[batch_i : batch_i + effective_batch]))
        if tasks:
            await asyncio.gather(*tasks)
    finally:
        closer = getattr(openai_client, "aclose", None)
        if callable(closer):
            try:
                maybe = closer()
                if inspect.isawaitable(maybe):
                    await maybe
            except Exception:  # pragma: no cover - best-effort cleanup
                logger.debug("fact_extractor client close failed", exc_info=True)

    results: list[FactExtractionResult] = []
    for i, slot in enumerate(slot_results):
        if slot is None:
            raise RuntimeError(f"fact_extractor internal error: missing result for unit index {i}")
        results.append(slot)

    records: list[dict[str, Any]] = []
    for unit, result in zip(evidence_units, results, strict=False):
        for extracted in result.facts:
            record = _build_fact_record(
                extracted,
                evidence_unit=unit,
                truth_state=truth_state,
                source_authority=source_authority,
                entity_id_set=entity_id_set,
                resolved_subject_entity_id=_resolve_subject_entity_id(
                    subject_entity_id=extracted.subject_entity_id,
                    attribute=extracted.attribute,
                    value_label=extracted.value.label,
                    evidence_text=str(unit.get("text", "")),
                    entities_by_id=entities_by_id,
                    entity_matchers=entity_matchers,
                    entity_name_index=entity_name_index,
                ),
            )
            if record is not None:
                records.append(record)

    records = _deduplicate_facts(records)
    validate_many(records, "fact.schema.json")
    logger.info(
        "fact_extractor done units=%d records=%d cache_hits=%d cache_misses=%d scoped_prompts=%d truth_state=%s",
        len(evidence_units),
        len(records),
        stats["cache_hits"],
        stats["cache_misses"],
        stats["scoped_prompts"],
        truth_state,
    )
    return {
        "facts": records,
        "usage": total_usage.to_dict(),
        "cache_hits": stats["cache_hits"],
        "cache_misses": stats["cache_misses"],
        "scoped_prompts": stats["scoped_prompts"],
        "model_name": model_id,
    }


def run_fact_extraction(
    evidence_units: list[dict[str, Any]],
    *,
    entities: list[dict[str, Any]],
    canon_layer: str,
    campaign_id: str | None,
    source_class: str,
    model: str | None = None,
    concurrency: int = 8,
    batch_size: int = 1,
    cache_dir: Path | None = None,
    openai_client: Any | None = None,
    allow_heuristic_fallback: bool = True,
) -> dict[str, Any]:
    return asyncio.run(
        extract_facts_batch(
            evidence_units,
            entities=entities,
            canon_layer=canon_layer,
            campaign_id=campaign_id,
            source_class=source_class,
            model=model,
            concurrency=concurrency,
            batch_size=batch_size,
            cache_dir=cache_dir,
            openai_client=openai_client,
            allow_heuristic_fallback=allow_heuristic_fallback,
        )
    )


def prepare_fact_batch_requests_chunked(
    evidence_units: list[dict[str, Any]],
    *,
    entities: list[dict[str, Any]],
    model: str,
    batch_size: int = 5,
    cache_dir: Path | None = None,
    custom_id_prefix: str = "fact_batch",
    batch_index_start: int = 0,
) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    """Build JSONL lines for OpenAI Batch fact extraction. Skips cache hits."""
    from src.ingestion.openai_batch_pipeline import (
        build_jsonl_request_line,
        build_responses_batch_request_body,
    )

    model_id = model or _load_model_id()
    cache_root = (
        Path(cache_dir) if cache_dir is not None else (Path.cwd() / ".fact_extractor_cache")
    )
    cache_root.mkdir(parents=True, exist_ok=True)
    entity_fp = _entity_context_fingerprint(entities)
    entities_by_id = {
        str(entity.get("entity_id", "")).strip(): entity
        for entity in entities
        if str(entity.get("entity_id", "")).strip()
    }
    entity_matchers = _build_entity_matchers(entities)

    misses: list[dict[str, Any]] = []

    for unit in evidence_units:
        prompt_entities, prompt_entity_fp = _prompt_entities_for_unit(
            unit,
            entities=entities,
            entities_by_id=entities_by_id,
            entity_matchers=entity_matchers,
            entity_fp=entity_fp,
        )
        key = _cache_key(unit, model_id, prompt_entity_fp)
        cache_file = _cache_path(cache_root, key)
        if cache_file.exists():
            continue
        misses.append(
            {
                "unit": unit,
                "prompt_entities": prompt_entities,
                "prompt_entity_fp": prompt_entity_fp,
            }
        )

    lines: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {}
    fact_system = _build_fact_system_prompt()
    effective_batch = max(1, batch_size)
    batch_index = max(0, int(batch_index_start))

    for i in range(0, len(misses), effective_batch):
        chunk = misses[i : i + effective_batch]
        cid = f"{custom_id_prefix}_{batch_index:04d}"
        batch_index += 1
        pairs = [(m["unit"], m["prompt_entities"]) for m in chunk]
        user_prompt = _build_batched_fact_user_prompt(pairs)
        body = build_responses_batch_request_body(
            model=model_id,
            system_prompt=fact_system,
            user_prompt=user_prompt,
            text_format=BatchedFactExtractionResult,
        )
        lines.append(build_jsonl_request_line(custom_id=cid, body=body))
        manifest[cid] = {
            "kind": "batched_facts",
            "entries": [
                {
                    "cache_key": _cache_key(entry["unit"], model_id, entry["prompt_entity_fp"]),
                }
                for entry in chunk
            ],
        }

    return lines, manifest, batch_index


def prepare_fact_batch_requests(
    evidence_units: list[dict[str, Any]],
    *,
    entities: list[dict[str, Any]],
    model: str,
    batch_size: int = 5,
    cache_dir: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lines, manifest, _next_batch_index = prepare_fact_batch_requests_chunked(
        evidence_units,
        entities=entities,
        model=model,
        batch_size=batch_size,
        cache_dir=cache_dir,
    )
    return lines, manifest


def apply_fact_batch_outputs_to_cache(
    output_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    model_id: str,
    cache_dir: Path,
) -> tuple[list[str], dict[str, int]]:
    from src.ingestion.openai_batch_pipeline import (
        extract_output_text_from_responses_body,
        extract_response_body_from_batch_line,
        extract_status_code_from_batch_line,
        merge_usage,
        usage_dict_from_responses_body,
    )

    cache_root = Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    usage_totals: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}

    for row in output_rows:
        cid = str(row.get("custom_id", "") or "")
        if row.get("error"):
            failures.append(cid or "(missing custom_id)")
            continue
        spec = manifest.get(cid) if cid else None
        if not spec:
            failures.append(cid or "(missing custom_id)")
            continue
        code = extract_status_code_from_batch_line(row)
        if code is not None and code != 200:
            failures.append(cid)
            continue
        body = extract_response_body_from_batch_line(row)
        if not body:
            failures.append(cid)
            continue
        merge_usage(usage_totals, usage_dict_from_responses_body(body))
        text = extract_output_text_from_responses_body(body)
        if not text:
            failures.append(cid)
            continue
        if spec.get("kind") != "batched_facts":
            failures.append(cid)
            continue
        try:
            parsed = BatchedFactExtractionResult.model_validate_json(text)
            by_slot: dict[int, UnitFactResult] = {}
            for r in parsed.results:
                ui = r.unit_index
                if ui in by_slot:
                    logger.warning(
                        "fact batch output duplicate unit_index=%s (using last)",
                        ui,
                    )
                by_slot[ui] = r
            for slot_j, entry in enumerate(spec["entries"]):
                cache_key = str(entry.get("cache_key", "") or "").strip()
                if not cache_key:
                    failures.append(cid)
                    continue
                cache_file = _cache_path(cache_root, cache_key)
                row_fr = by_slot.get(slot_j)
                if row_fr is None:
                    single = FactExtractionResult(facts=[])
                else:
                    single = FactExtractionResult(facts=list(row_fr.facts))
                cache_file.write_text(single.model_dump_json(indent=2), encoding="utf-8")
        except Exception:
            failures.append(cid)

    return failures, usage_totals
