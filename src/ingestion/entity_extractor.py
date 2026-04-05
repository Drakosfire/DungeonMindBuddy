from __future__ import annotations

import asyncio
import inspect
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import blake3
from pydantic import BaseModel, Field

from src.contracts.entity_tags import DEFAULT_MAX_ENTITY_TAGS, normalize_entity_tags
from src.contracts.entity_taxonomy import (
    EntityClass,
    normalize_semantic_facets,
)
from src.contracts.schema_validation import list_validation_failures, validate_many
from src.store import FactStore


@dataclass
class UsageStats:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    api_calls: int = 0

    def merge(self, other: UsageStats) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cached_tokens += other.cached_tokens
        self.api_calls += other.api_calls

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def _usage_dict_from_openai_response(response: Any) -> dict[str, int]:
    usage_raw = getattr(response, "usage", None)
    if not usage_raw:
        return {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    details = getattr(usage_raw, "input_tokens_details", None)
    cached = 0
    if details is not None:
        cached = int(getattr(details, "cached_tokens", 0) or 0)
    return {
        "input_tokens": int(getattr(usage_raw, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage_raw, "output_tokens", 0) or 0),
        "cached_tokens": cached,
    }


_PROMPT_ID = "phase_b_pass1_entity_extraction_v6_prompt_cache_split"
_STOPWORDS = {
    "A",
    "An",
    "And",
    "As",
    "At",
    "But",
    "By",
    "For",
    "From",
    "If",
    "In",
    "Into",
    "It",
    "Its",
    "Of",
    "On",
    "Or",
    "The",
    "To",
    "With",
}
_CONNECTORS = {"of", "the", "and", "for", "to", "in", "at", "by"}
_PRONOUNS = {
    "he",
    "she",
    "they",
    "it",
    "him",
    "her",
    "them",
    "his",
    "hers",
    "their",
    "theirs",
    "its",
    "we",
    "us",
    "our",
    "ours",
    "i",
    "me",
    "my",
    "mine",
    "you",
    "your",
    "yours",
}
_MAX_ENTITY_NAME_LENGTH = 60
_JUNK_ENTITY_EXACT = {
    "background",
    "description",
    "governance",
    "history",
    "location",
    "personality",
    "race",
    "role",
    "stance",
}
_JUNK_ENTITY_PREFIXES = (
    "approach to ",
    "economy and ",
    "entry and ",
    "examples in ",
    "fantastic livestock",
    "history and ",
    "key events",
    "key features",
    "key locations",
    "key npcs",
    "mapping and ",
    "narrative integration",
    "origin and ",
    "plot hooks",
    "scene for ",
)
_LOW_SIGNAL_SINGLE_TOKENS = {
    "all",
    "amidst",
    "approximately",
    "beyond",
    "chaos",
    "concerned",
    "crowded",
    "defensive",
    "disappearances",
    "due",
    "encircling",
    "exploration",
    "extracted",
    "founded",
    "growing",
    "initially",
    "interspersed",
    "livestock",
    "major",
    "mostly",
    "natural",
    "occasional",
    "official",
    "other",
    "outside",
    "over",
    "reaches",
    "rescue",
    "some",
    "something",
    "sometimes",
    "street",
    "tainted",
    "temporary",
    "light",
    "water",
    "roots",
    "smoke",
    "fire",
    "meat",
    "corruption",
    "breath",
    "music",
    "rune",
    "signs",
    "knowledge",
    "healing",
    "group",
}
_LOW_SIGNAL_PHRASES = {
    "a spark",
    "brewing competition",
    "city fortification",
    "cult recruitment",
    "cultural exhibitions",
    "internal corruption",
    "key npcs",
    "local myths",
    "magical demonstrations",
    "magical disturbances",
    "magical manipulation",
    "major industries",
    "market fair",
    "massive gathering",
    "natural disasters",
    "opening ceremony",
    "plot hooks and encounters",
}
_DND_SKILLS = {
    "acrobatics",
    "animal handling",
    "arcana",
    "athletics",
    "deception",
    "history",
    "insight",
    "intimidation",
    "investigation",
    "medicine",
    "nature",
    "perception",
    "performance",
    "persuasion",
    "religion",
    "sleight of hand",
    "stealth",
    "survival",
}
_DND_SPELLS = {
    "detect magic",
    "mage hand",
    "eldritch blast",
    "sleep",
    "invisibility",
    "hunter's mark",
}
_MECHANICS_PATTERNS = (
    re.compile(r"\bdc\s*\d+\b", re.IGNORECASE),
    re.compile(r"\b(?:saving throw|save)\b", re.IGNORECASE),
    re.compile(r"\b(?:athletics|arcana|insight|perception|persuasion)\s+check\b", re.IGNORECASE),
    re.compile(r"\b\d+d\d+\b", re.IGNORECASE),
)
_CLASS_KEYWORDS: dict[str, set[str]] = {
    "place": {
        "city",
        "town",
        "village",
        "lake",
        "peaks",
        "mount",
        "mountain",
        "forest",
        "swamp",
        "outtown",
        "district",
        "gate",
        "gates",
        "tower",
        "roads",
        "road",
    },
    "group": {
        "flock",
        "council",
        "guild",
        "empire",
        "cult",
        "guard",
        "guards",
    },
    "object": {"artifact", "relic", "vial", "toxin", "weapon", "blade", "sword", "key", "letter"},
    "event": {"festival", "ceremony", "battle", "protest", "meeting", "ritual"},
    "concept": {"doctrine", "prophecy", "curse", "law", "principle"},
}

logger = logging.getLogger(__name__)


class ExtractedEntity(BaseModel):
    entity_id: str | None = None
    decision: Literal["entity", "exclude"] = "entity"
    exclude_reason: Literal[
        "generic_noun",
        "descriptive_phrase",
        "document_structure",
        "game_mechanic",
        "sentence_fragment",
        "temporal_connector",
        "underspecified_collective",
    ] | None = None
    entity_class: EntityClass | None = None
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    subtype_facets: list[str] = Field(default_factory=list)
    narrative_tags: list[str] = Field(default_factory=list)
    document_tags: list[str] = Field(default_factory=list)
    source_profile: str | None = None
    authority: str | None = None
    confidence: float | None = None
    span_text: str | None = None
    extraction_method: Literal["llm", "heuristic"] = "llm"
    # Legacy compatibility fields accepted from old prompts/cache.
    entity_type: Literal["npc", "location", "faction", "item", "other"] | None = None
    entity_kind: EntityClass | None = None
    entity_tags: list[str] = Field(default_factory=list)
    semantic_facets: list[str] = Field(default_factory=list)
    is_new: bool = True


class EntityExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)


class UnitEntityResult(BaseModel):
    """Per-slot result in a batched call; index matches section order in the user prompt (not evidence_id)."""

    unit_index: int = Field(ge=0, description="0-based index of the evidence section, matching the prompt header.")
    entities: list[ExtractedEntity] = Field(default_factory=list)


class BatchedEntityExtractionResult(BaseModel):
    results: list[UnitEntityResult] = Field(default_factory=list)


class OpenAIResponsesEntityClient:
    """Adapter for OpenAI Responses API structured parsing."""

    def __init__(self, *, api_key: str | None = None, sdk_client: Any | None = None) -> None:
        if sdk_client is not None:
            self._client = sdk_client
            return
        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover - import failure surfaced in caller.
            raise RuntimeError(
                "OpenAI SDK is required for OpenAIResponsesEntityClient. Install dependency 'openai'."
            ) from exc
        self._client = OpenAI(api_key=api_key)

    def extract_entities(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        evidence_unit: dict[str, Any],
        known_entities: list[dict[str, Any]],
        prompt_id: str,
    ) -> dict[str, Any]:
        response = self._client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=EntityExtractionResult,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, EntityExtractionResult):
            result = parsed.model_dump()
        else:
            result = EntityExtractionResult.model_validate(parsed).model_dump()
        result["_usage"] = _usage_dict_from_openai_response(response)
        return result

    def extract_recap(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        evidence_unit: dict[str, Any],
        known_entities: list[dict[str, Any]],
        prompt_id: str,
    ) -> dict[str, Any]:
        # Lazy import: recap_models imports ExtractedEntity from this module.
        from src.ingestion.recap_models import RecapExtractionResult as _RecapExtractionResult

        response = self._client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=_RecapExtractionResult,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, _RecapExtractionResult):
            result = parsed.model_dump()
        else:
            result = _RecapExtractionResult.model_validate(parsed).model_dump()
        result["_usage"] = _usage_dict_from_openai_response(response)
        return result

    def extract_entities_batched(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        prompt_id: str,
    ) -> dict[str, Any]:
        response = self._client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=BatchedEntityExtractionResult,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, BatchedEntityExtractionResult):
            result = parsed.model_dump()
        else:
            result = BatchedEntityExtractionResult.model_validate(parsed).model_dump()
        result["_usage"] = _usage_dict_from_openai_response(response)
        return result


class AsyncOpenAIResponsesEntityClient:
    """Async adapter for OpenAI Responses API structured parsing."""

    def __init__(self, *, api_key: str | None = None, sdk_client: Any | None = None) -> None:
        if sdk_client is not None:
            self._client = sdk_client
            return
        try:
            from openai import AsyncOpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "OpenAI SDK is required for AsyncOpenAIResponsesEntityClient. Install dependency 'openai'."
            ) from exc
        self._client = AsyncOpenAI(api_key=api_key)

    async def extract_entities(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        evidence_unit: dict[str, Any],
        known_entities: list[dict[str, Any]],
        prompt_id: str,
    ) -> dict[str, Any]:
        response = await self._client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=EntityExtractionResult,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, EntityExtractionResult):
            result = parsed.model_dump()
        else:
            result = EntityExtractionResult.model_validate(parsed).model_dump()
        result["_usage"] = _usage_dict_from_openai_response(response)
        return result

    async def extract_recap(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        evidence_unit: dict[str, Any],
        known_entities: list[dict[str, Any]],
        prompt_id: str,
    ) -> dict[str, Any]:
        from src.ingestion.recap_models import RecapExtractionResult as _RecapExtractionResult

        response = await self._client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=_RecapExtractionResult,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, _RecapExtractionResult):
            result = parsed.model_dump()
        else:
            result = _RecapExtractionResult.model_validate(parsed).model_dump()
        result["_usage"] = _usage_dict_from_openai_response(response)
        return result

    async def extract_entities_batched(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        prompt_id: str,
    ) -> dict[str, Any]:
        response = await self._client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=BatchedEntityExtractionResult,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, BatchedEntityExtractionResult):
            result = parsed.model_dump()
        else:
            result = BatchedEntityExtractionResult.model_validate(parsed).model_dump()
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


def _load_fast_smart_model_id() -> str:
    policy_path = Path(__file__).resolve().parents[3] / "MODEL_POLICY.json"
    if not policy_path.exists():
        return "fast_smart"
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    actions = payload.get("actions", {})
    models = payload.get("models", {})
    role = actions.get("structured_generation", "fast_smart")
    return models.get(role, role)


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _snake_case(value: str) -> str:
    cleaned = re.sub(r"[’']", "", value.lower())
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "entity"


def _sanitize_id(raw: str, prefix: str = "ent") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]+", "_", raw)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_.:-")
    if not cleaned:
        cleaned = prefix
    if cleaned[0].isdigit():
        cleaned = f"{prefix}_{cleaned}"
    return cleaned


def _entity_id_for_name(display_name: str) -> str:
    return _sanitize_id(f"ent_{_snake_case(display_name)}")


def _match_key(name: str) -> str:
    return _normalize_space(name).lower()


def _build_known_lookup(known_entities: list[dict[str, Any]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for entity in known_entities:
        entity_id = str(entity.get("entity_id", "")).strip()
        if not entity_id:
            continue
        names = [str(entity.get("display_name", "")).strip()]
        names.extend(str(alias).strip() for alias in entity.get("aliases", []))
        for name in names:
            key = _match_key(name)
            if key:
                lookup[key] = entity_id
    return lookup


def _infer_entity_class(display_name: str) -> EntityClass:
    lowered = display_name.lower()
    tokens = set(re.findall(r"[a-z]+", lowered))
    for label, keywords in _CLASS_KEYWORDS.items():
        if tokens & keywords:
            return label  # type: ignore[return-value]
    words = display_name.split()
    if len(words) >= 2 and all(word[:1].isupper() for word in words if word and word.lower() not in _CONNECTORS):
        return "actor"
    return "concept"


def _dedupe_names(names: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for name in names:
        normalized = _normalize_space(name)
        key = normalized.lower()
        if normalized and key not in seen:
            seen[key] = normalized
    return sorted(seen.values())


def _candidate_name_spans(text: str) -> list[str]:
    pattern = re.compile(
        r"\b[A-Z][A-Za-z0-9'’.-]*(?:\s+(?:[A-Z][A-Za-z0-9'’.-]*|of|the|and|for|to|in|at|by)){0,5}\b"
    )
    candidates: list[str] = []
    for match in pattern.finditer(text):
        candidate = _normalize_space(match.group(0))
        words = candidate.split()
        while words and words[-1].lower() in _CONNECTORS:
            words.pop()
        candidate = " ".join(words).strip(" ,.;:-")
        if not candidate or candidate in _STOPWORDS:
            continue
        if len(candidate) < 3:
            continue
        candidates.append(candidate)
    return candidates


def _resolve_source_profile(unit: dict[str, Any]) -> str:
    """Map evidence unit metadata to a SourceProfile for prompt dispatch."""
    source_class = str(unit.get("source_class", "")).strip()
    canon_layer = str(unit.get("canon_layer", "")).strip()
    if source_class == "observed_session_recap":
        return "session_recap"
    if canon_layer == "world":
        return "worldbuilding"
    if source_class in ("planning_document", "seed_reference"):
        return "worldbuilding"
    if source_class == "ledger_or_dossier":
        return "npc_dossier"
    return "worldbuilding"


_WORLDBUILDING_PREFIX = (
    "Extract durable world referents and stable descriptive relations. "
    "Prefer named people, places, factions, artifacts, rituals, events, and doctrines. "
    "Exclude headings, prose atmosphere, scene instructions, and generic materials."
)

_SESSION_RECAP_PREFIX = (
    "Extract only continuity-relevant world referents and what changed about them. "
    "Prefer named participants, places, and events. "
    "Record suspicions, plans, and rumors as claims with uncertainty, not as settled canon. "
    "Ignore generic scene description unless it changes future play."
)

_PROFILE_PREFIXES: dict[str, str] = {
    "worldbuilding": _WORLDBUILDING_PREFIX,
    "session_recap": _SESSION_RECAP_PREFIX,
}


def _heuristic_extract_entities(text: str) -> EntityExtractionResult:
    names = _candidate_name_spans(text)
    entities: list[ExtractedEntity] = []
    for display_name in _dedupe_names(names):
        entities.append(
            ExtractedEntity(
                entity_id=None,
                decision="entity",
                entity_class=_infer_entity_class(display_name),
                display_name=display_name,
                aliases=[],
                is_new=True,
                extraction_method="heuristic",
            )
        )
    return EntityExtractionResult(entities=entities)


def _cache_key(unit: dict[str, Any], model_id: str, source_profile: str = "worldbuilding") -> str:
    text_fp = blake3.blake3(str(unit.get("text", "")).encode("utf-8")).hexdigest()
    payload = f"{text_fp}|{_PROMPT_ID}|{model_id}|{source_profile}"
    return blake3.blake3(payload.encode("utf-8")).hexdigest()


def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


_MAX_ALIASES_IN_PROMPT = 3


def _relevant_known_entities(
    known_entities: list[dict[str, Any]], unit_text: str
) -> list[dict[str, Any]]:
    """Return only entities whose display_name appears in the evidence unit text."""
    text_lower = unit_text.lower()
    relevant: list[dict[str, Any]] = []
    for entity in known_entities:
        display = str(entity.get("display_name", "")).strip()
        if not display or len(display) < 3:
            continue
        if display.lower() in text_lower:
            aliases = entity.get("aliases", [])
            short_aliases = sorted(aliases, key=len)[:_MAX_ALIASES_IN_PROMPT]
            relevant.append(
                {
                    "entity_id": entity.get("entity_id"),
                    "display_name": display,
                    "aliases": short_aliases,
                }
            )
    return relevant


def _build_entity_system_prompt() -> str:
    """Static instructions shared by every standard (non-recap-lane) entity extraction call.

    Kept large enough for OpenAI automatic prefix caching (>= ~1024 tokens).
    """
    return (
        "You are an entity extraction agent for a TTRPG worldbuilding system.\n\n"
        "SOURCE PROFILES: The user message includes exactly one active profile label. "
        "Interpret that label together with the profile-specific instruction block in the user message.\n"
        "- worldbuilding: setting bible, gazetteers, prep documents about places, factions, lore.\n"
        "- session_recap: table record of play; prioritize continuity and named participants.\n"
        "- npc_dossier: character sheets, ledgers, in-world dossiers focused on people or roles.\n"
        "- item_card: item-focused reference blocks.\n"
        "- encounter_table: encounter or scene scaffolding text.\n"
        "- cultural_event_doc: festivals, ceremonies, public events as documented.\n\n"
        "Core gate: decision must be entity or exclude.\n"
        "If a span would not plausibly be asked about later as a campaign-world thing, choose exclude.\n\n"
        "Ontology policy:\n"
        "- entity_class must be one of: actor, group, place, object, event, concept.\n"
        "- Never emit unknown, other, or document_anchor classes.\n"
        "- subtype_facets describe ontology detail (deity, guild, festival, doctrine, artifact, settlement, institution).\n"
        "- narrative_tags are story-function labels (plot_hook, theme, conflict, mystery, reveal, threat).\n"
        "- document_tags are structure labels (summary, prep_note, boxed_text, branch_point, section_header).\n"
        "- Keep ontology and narrative/document tags separate.\n\n"
        "Explicit excludes:\n"
        "- generic nouns: candlelight, roots, water, smoke\n"
        "- document structure: Executive DM Summary, Running the Location\n"
        "- mechanics fragments: Dexterity save (DC 12), 1d8 necrotic damage\n"
        "- underspecified collectives: students, guards (unless a named group)\n"
        "- temporal connectors: Within minutes, Later that day\n\n"
        "Authority and profile fields on each entity:\n"
        "- source_profile should be one of: worldbuilding, session_recap, npc_dossier, item_card, encounter_table, "
        "cultural_event_doc.\n"
        "- authority should be one of: canon_reference, planning_note, play_record, rumor_or_belief, mechanic_reference.\n"
        "- If uncertain, infer from wording but do not hallucinate extra facts.\n\n"
        "OUTPUT: Return JSON with shape {\"entities\": [...]} only (no markdown fences).\n\n"
        "Per-entity JSON fields (authoritative reference):\n"
        "- entity_id: optional string; when the mention matches a known entity from the user-provided list, reuse that id.\n"
        "- decision: required string \"entity\" or \"exclude\".\n"
        "- exclude_reason: when decision is exclude, one of generic_noun, descriptive_phrase, document_structure, "
        "game_mechanic, sentence_fragment, temporal_connector, underspecified_collective.\n"
        "- display_name: required human-readable canonical surface form for the span.\n"
        "- aliases: optional string list of alternate surface forms for the same referent.\n"
        "- entity_class: when decision is entity, one of actor, group, place, object, event, concept.\n"
        "- subtype_facets: optional string list; ontology refinements (guild, settlement, artifact, doctrine, ...).\n"
        "- narrative_tags: optional string list; story-role labels separate from ontology.\n"
        "- document_tags: optional string list; document-structure labels separate from narrative_tags.\n"
        "- source_profile: optional string; best-effort classification for this mention.\n"
        "- authority: optional string; provenance of the assertion (canon vs play record vs rumor, etc.).\n"
        "- confidence: optional float from 0.0 to 1.0 for extraction confidence.\n"
        "- span_text: optional string; verbatim or near-verbatim substring from the evidence supporting the mention.\n"
        "- is_new: optional boolean; true if this appears to be a first-time mention not linked to a known id.\n"
        "- extraction_method: optional; leave default llm unless instructed otherwise.\n"
        "Legacy fields (accept if model emits them, but prefer modern fields): entity_type, entity_kind, entity_tags, "
        "semantic_facets.\n\n"
        "Quality rules:\n"
        "- Prefer precise named entities over vague noun phrases.\n"
        "- Do not invent proper names absent from the evidence.\n"
        "- When two surface forms are the same referent, align aliases and reuse entity_id when supplied.\n"
        "- Split distinct referents into separate entities even if they appear in one sentence.\n\n"
        "Examples of entity (non-exhaustive): named NPCs, named settlements, factions with proper names, unique artifacts, "
        "named festivals, specific in-world documents, titled locations.\n"
        "Examples of exclude: sensory fluff, dice instructions, purely structural headings, generic crowds without a "
        "proper group name, skill names and spell names as mechanics.\n\n"
        "Repeat: respond with {\"entities\": [...]} matching the schema above.\n"
    )


def _build_entity_user_prompt(
    unit: dict[str, Any],
    known_entities: list[dict[str, Any]],
) -> str:
    """Per-unit variable content for standard entity extraction."""
    unit_text = unit.get("text", "")
    source_profile = _resolve_source_profile(unit)
    known_minimal = _relevant_known_entities(known_entities, unit_text)
    profile_prefix = _PROFILE_PREFIXES.get(source_profile, _WORLDBUILDING_PREFIX)
    return (
        f"Source profile: {source_profile}\n"
        f"{profile_prefix}\n\n"
        f"Known entities (reuse IDs if recognized):\n{json.dumps(known_minimal, ensure_ascii=False)}\n\n"
        f"Evidence unit:\n{unit_text}"
    )


def _build_batched_entity_user_prompt(
    units: list[dict[str, Any]],
    known_entities: list[dict[str, Any]],
) -> str:
    """Bundle multiple standard (non-recap) evidence units; output schema is BatchedEntityExtractionResult."""
    sections: list[str] = []
    for slot_idx, unit in enumerate(units):
        unit_text = str(unit.get("text", ""))
        source_profile = _resolve_source_profile(unit)
        known_minimal = _relevant_known_entities(known_entities, unit_text)
        profile_prefix = _PROFILE_PREFIXES.get(source_profile, _WORLDBUILDING_PREFIX)
        sections.append(
            f"--- unit_index: {slot_idx} ---\n"
            f"Source profile: {source_profile}\n"
            f"{profile_prefix}\n\n"
            f"Known entities (reuse IDs if recognized):\n"
            f"{json.dumps(known_minimal, ensure_ascii=False)}\n\n"
            f"Text:\n{unit_text}"
        )
    joined = "\n\n".join(sections)
    n = len(units)
    last = n - 1 if n else 0
    return (
        "Process each evidence unit below. Return JSON with shape "
        '{"results": [{"unit_index": <int>, "entities": [...]}, ...]} only (no markdown fences). '
        "Include exactly one results entry per section. For each entry, unit_index must be the integer "
        f"from that section's header (0 through {last}). Do not invent or copy internal database ids.\n\n"
        + joined
    )


def _pop_usage_from_entity_payload(payload: Any) -> tuple[dict[str, Any], dict[str, int]]:
    if not isinstance(payload, dict):
        raise TypeError("extract_entities payload must be a dict")
    raw = payload.pop("_usage", None) or {}
    usage = {
        "input_tokens": int(raw.get("input_tokens", 0) or 0),
        "output_tokens": int(raw.get("output_tokens", 0) or 0),
        "cached_tokens": int(raw.get("cached_tokens", 0) or 0),
    }
    return payload, usage


async def _call_extractor(
    unit: dict[str, Any],
    known_entities: list[dict[str, Any]],
    model_id: str,
    openai_client: Any | None,
    *,
    allow_heuristic_fallback: bool,
    system_prompt: str,
) -> tuple[EntityExtractionResult, dict[str, int]]:
    if openai_client is None:
        if not allow_heuristic_fallback:
            raise ValueError(
                "Heuristic fallback is disabled; provide an openai_client for entity extraction."
            )
        return _heuristic_extract_entities(str(unit.get("text", ""))), {}

    if not hasattr(openai_client, "extract_entities"):
        raise ValueError("openai_client must expose extract_entities(...)")

    payload = openai_client.extract_entities(
        model=model_id,
        system_prompt=system_prompt,
        user_prompt=_build_entity_user_prompt(unit, known_entities),
        evidence_unit=unit,
        known_entities=known_entities,
        prompt_id=_PROMPT_ID,
    )
    if inspect.isawaitable(payload):
        payload = await payload
    body, usage = _pop_usage_from_entity_payload(payload)
    return EntityExtractionResult.model_validate(body), usage


def _build_recap_system_prompt() -> str:
    """Static recap-lane instructions (session_recap units); sized for prefix caching."""
    return (
        "You are an entity and event extraction agent for a TTRPG session recap.\n\n"
        "The user message states Source profile: session_recap and includes recap-specific focus text—follow it.\n\n"
        "Core gate: decision must be entity or exclude.\n"
        "If a span would not plausibly be asked about later as a campaign-world thing, choose exclude.\n\n"
        "Ontology policy:\n"
        "- entity_class must be one of: actor, group, place, object, event, concept.\n"
        "- Never emit unknown, other, or document_anchor classes.\n"
        "- subtype_facets describe ontology detail (deity, guild, festival, doctrine, artifact, settlement, institution).\n"
        "- narrative_tags are story-function labels (plot_hook, theme, conflict, mystery, reveal, threat).\n"
        "- document_tags are structure labels (summary, prep_note, boxed_text, branch_point, section_header).\n"
        "- Keep ontology and narrative/document tags separate.\n\n"
        "Explicit excludes:\n"
        "- generic nouns: candlelight, roots, water, smoke\n"
        "- document structure: Executive DM Summary, Running the Location\n"
        "- mechanics fragments: Dexterity save (DC 12), 1d8 necrotic damage\n"
        "- underspecified collectives: students, guards (unless a named group)\n"
        "- temporal connectors: Within minutes, Later that day\n\n"
        "Authority and profile:\n"
        "- source_profile for entities is typically session_recap when appropriate.\n"
        "- authority should be one of: canon_reference, planning_note, play_record, rumor_or_belief, mechanic_reference.\n"
        "- For session recaps, most entities carry authority=play_record.\n"
        "- Suspicions and rumors should be captured as claims, not entities.\n\n"
        "EVENT RECORDS:\n"
        "Extract concrete in-fiction happenings as event_records.\n"
        "Each event_record has:\n"
        "- event_name (string or null): a short label for the event.\n"
        "- event_class: one of conversation, travel, combat, discovery, transfer, ritual, betrayal, disaster, "
        "investigation, social_conflict.\n"
        "- participants: list of entity names involved.\n"
        "- location: place name or null.\n"
        "- outcomes: list of strings describing what changed.\n"
        "- time_scope: scene, session, or historical_reference.\n"
        "- certainty: observed, inferred, or uncertain.\n\n"
        "EVENT_RECORD FIELD NOTES:\n"
        "- Prefer specific scene beats over vague summaries.\n"
        "- If timing is ambiguous, use time_scope=session and certainty=inferred or uncertain.\n"
        "- participants should use display names as they appear in the recap text.\n\n"
        "CLAIMS:\n"
        "Extract propositions asserted in the recap that may or may not be canon.\n"
        "Each claim has:\n"
        "- subject: entity name or text.\n"
        "- predicate: what is asserted.\n"
        "- object: entity name or text.\n"
        "- claim_type: fact, suspicion, rumor, intent, or memory.\n"
        "- speaker_or_source: entity name or 'narrator'.\n"
        "- certainty: high, medium, or low.\n\n"
        "CLAIM FIELD NOTES:\n"
        "- Use claim_type=suspicion or rumor when the text frames belief, not established fact.\n"
        "- Use speaker_or_source for in-character attribution when explicit.\n\n"
        "ENTITY JSON fields (entities[] items):\n"
        "- entity_id, decision, exclude_reason, display_name, aliases, entity_class, subtype_facets, narrative_tags, "
        "document_tags, source_profile, authority, confidence (0..1), span_text, is_new.\n\n"
        "Return JSON with shape:\n"
        "{\n"
        '  "entities": [...],\n'
        '  "event_records": [...],\n'
        '  "claims": [...]\n'
        "}\n"
        "No markdown fences. Arrays may be empty but must be present.\n\n"
        "Recap quality bar:\n"
        "- Entities: named people, places, factions, objects that will matter in future sessions.\n"
        "- Events: things that happened, not hypothetical advice to the DM.\n"
        "- Claims: beliefs, suspicions, plans, and memories stated in the recap voice.\n\n"
        "EDGE CASES:\n"
        "- If the recap mixes in-character dialogue and narrator summary, attribute claims to the speaker when clear.\n"
        "- Combat outcomes: prefer event_class=combat with outcomes listing casualties, retreats, or tactical shifts.\n"
        "- Travel montages: one travel event_record per distinct leg if the text distinguishes destinations.\n"
        "- Flashbacks: use time_scope=historical_reference and certainty appropriate to framing (memory vs established lore).\n"
        "- Duplicate mentions of the same scene: one event_record with merged outcomes unless clearly separate scenes.\n"
        "- Empty evidence: return empty arrays; never fabricate entities, events, or claims.\n\n"
        "ANTI-PATTERNS:\n"
        "- Do not emit entities for dice rolls, DC numbers, or rules jargon without in-world names.\n"
        "- Do not treat DM advice ('you might want to') as in-fiction claims.\n"
        "- Do not collapse unrelated NPCs into one entity; keep display names distinct.\n"
    )


def _build_recap_user_prompt(unit: dict[str, Any], known_entities: list[dict[str, Any]]) -> str:
    unit_text = unit.get("text", "")
    known_minimal = _relevant_known_entities(known_entities, unit_text)
    return (
        "Source profile: session_recap\n"
        f"{_SESSION_RECAP_PREFIX}\n\n"
        f"Known entities (reuse IDs if recognized):\n{json.dumps(known_minimal, ensure_ascii=False)}\n\n"
        f"Evidence unit:\n{unit_text}"
    )


_RECAP_PROMPT_ID = "recap_extraction_v2_prompt_cache"


async def _call_recap_extractor(
    unit: dict[str, Any],
    known_entities: list[dict[str, Any]],
    model_id: str,
    openai_client: Any | None,
    *,
    allow_heuristic_fallback: bool,
    system_prompt: str,
) -> tuple[Any, dict[str, int]]:
    from src.ingestion.recap_models import RecapExtractionResult

    if openai_client is None:
        if not allow_heuristic_fallback:
            raise ValueError(
                "Heuristic fallback is disabled; provide an openai_client for recap extraction."
            )
        heuristic_entities = _heuristic_extract_entities(str(unit.get("text", "")))
        return RecapExtractionResult(entities=heuristic_entities.entities), {}

    if hasattr(openai_client, "extract_recap"):
        extract_fn = openai_client.extract_recap
    elif hasattr(openai_client, "extract_entities"):
        extract_fn = openai_client.extract_entities
    else:
        raise ValueError("openai_client must expose extract_recap(...) or extract_entities(...)")

    payload = extract_fn(
        model=model_id,
        system_prompt=system_prompt,
        user_prompt=_build_recap_user_prompt(unit, known_entities),
        evidence_unit=unit,
        known_entities=known_entities,
        prompt_id=_RECAP_PROMPT_ID,
    )
    if inspect.isawaitable(payload):
        payload = await payload
    body, usage = _pop_usage_from_entity_payload(payload)
    return RecapExtractionResult.model_validate(body), usage


def _entity_record_from_extracted(
    extracted: ExtractedEntity,
    *,
    known_lookup: dict[str, str],
    mention_id: str,
) -> dict[str, Any]:
    display_name = _normalize_space(extracted.display_name)
    aliases = _dedupe_names([display_name, *extracted.aliases])
    matched_id = None
    for name in aliases:
        key = _match_key(name)
        if key in known_lookup:
            matched_id = known_lookup[key]
            break
    entity_id = matched_id or extracted.entity_id or _entity_id_for_name(display_name)
    now_iso = _now_utc_iso()
    raw_subtype_facets = (
        list(extracted.subtype_facets) + list(extracted.semantic_facets) + list(extracted.entity_tags)
    )
    subtype_facets = normalize_semantic_facets(raw_subtype_facets)
    legacy_tags = normalize_entity_tags(
        list(extracted.narrative_tags) + list(extracted.document_tags) + list(extracted.entity_tags),
        max_tags=DEFAULT_MAX_ENTITY_TAGS,
    )
    mapped_class: EntityClass | None = extracted.entity_class or extracted.entity_kind
    if mapped_class is None and extracted.entity_type:
        type_to_class: dict[str, EntityClass] = {
            "npc": "actor",
            "location": "place",
            "faction": "group",
            "item": "object",
            "other": "concept",
        }
        mapped_class = type_to_class.get(extracted.entity_type, "concept")
    if mapped_class is None:
        mapped_class = _infer_entity_class(display_name)
    legacy_type_map: dict[EntityClass, str] = {
        "actor": "npc",
        "group": "faction",
        "place": "location",
        "object": "item",
        "event": "other",
        "concept": "other",
    }
    return {
        "schema_version": "0.1.0",
        "created_at": now_iso,
        "updated_at": now_iso,
        "record_status": "active",
        "entity_id": _sanitize_id(entity_id),
        "entity_class": mapped_class,
        "entity_type": extracted.entity_type or legacy_type_map[mapped_class],
        "entity_kind": mapped_class,
        "decision": extracted.decision,
        "exclude_reason": extracted.exclude_reason,
        "source_profile": extracted.source_profile,
        "authority": extracted.authority,
        "confidence": extracted.confidence,
        "span_text": extracted.span_text or display_name,
        "extraction_method": extracted.extraction_method,
        "display_name": display_name,
        "canonical_name": None,
        "aliases": aliases,
        "entity_status": "provisional",
        "merged_into_entity_id": None,
        "source_mention_ids": [_sanitize_id(mention_id, prefix="men")],
        "review_state": "unreviewed",
        "entity_tags": legacy_tags,
        "semantic_facets": subtype_facets,
        "subtype_facets": subtype_facets,
        "narrative_tags": normalize_entity_tags(extracted.narrative_tags, max_tags=DEFAULT_MAX_ENTITY_TAGS),
        "document_tags": normalize_entity_tags(extracted.document_tags, max_tags=DEFAULT_MAX_ENTITY_TAGS),
        "notes": None,
    }


def _is_plausible_entity_name(
    *,
    display_name: str,
    entity_class: EntityClass | None,
    source_text: str,
    known_lookup: dict[str, str],
    mention_count: int,
) -> bool:
    normalized = _normalize_space(display_name)
    if not normalized:
        return False

    key = _match_key(normalized)
    if key in known_lookup:
        return True

    lowered = normalized.lower()

    if lowered in _PRONOUNS:
        return False

    if len(normalized) > _MAX_ENTITY_NAME_LENGTH:
        return False
    if lowered in _JUNK_ENTITY_EXACT:
        return False
    if lowered in _LOW_SIGNAL_PHRASES:
        return False
    if any(lowered.startswith(prefix) for prefix in _JUNK_ENTITY_PREFIXES):
        return False
    if lowered in _DND_SKILLS or lowered in _DND_SPELLS:
        return False
    if any(pattern.search(normalized) for pattern in _MECHANICS_PATTERNS):
        return False

    # Enforce phrase presence in chunk text to reject model hallucinations.
    if lowered not in source_text.lower():
        return False

    tokens = [tok for tok in re.findall(r"[A-Za-z]+", normalized)]
    if not tokens:
        return False

    if len(tokens) == 1:
        token = tokens[0].lower()
        if token in _LOW_SIGNAL_SINGLE_TOKENS:
            return False
        if entity_class in {"concept", "event"} and len(tokens[0]) < 5:
            return False

    # Drop purely structural/title lines with low semantic signal.
    if entity_class in {"concept", "event"}:
        if mention_count < 2 and len(tokens) <= 2:
            return False
        if all(token.lower() in _CONNECTORS for token in tokens):
            return False
        uppercase_tokens = [tok for tok in normalized.split() if tok[:1].isupper()]
        if len(uppercase_tokens) == 0:
            return False

    return True


async def extract_entities_batch(
    evidence_units: list[dict[str, Any]],
    *,
    known_entities: list[dict[str, Any]] | None = None,
    model: str | None = None,
    concurrency: int = 8,
    batch_size: int = 1,
    cache_dir: Path | None = None,
    openai_client: Any | None = None,
    allow_heuristic_fallback: bool = True,
    recap_artifacts: dict[str, list[dict[str, Any]]] | None = None,
    schema_repair_batch: bool = False,
    schema_repair_model: str = "gpt-5.4",
    schema_repair_poll_interval: float = 30.0,
    schema_repair_work_dir: Path | None = None,
) -> dict[str, Any]:
    from src.ingestion.recap_models import RecapExtractionResult

    known_entities = known_entities or []
    model_id = model or _load_fast_smart_model_id()
    cache_root = Path(cache_dir) if cache_dir is not None else (Path.cwd() / ".entity_extractor_cache")
    cache_root.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(max(1, concurrency))
    known_lookup = _build_known_lookup(known_entities)
    stats = {"completed": 0, "cache_hits": 0, "cache_misses": 0}
    progress_step = max(10, len(evidence_units) // 10) if evidence_units else 10
    effective_batch = max(1, batch_size)
    logger.info(
        "entity_extractor start units=%d concurrency=%d batch_size=%d model=%s cache_dir=%s",
        len(evidence_units),
        concurrency,
        effective_batch,
        model_id,
        cache_root,
    )

    entity_system_prompt = _build_entity_system_prompt()
    recap_system_prompt = _build_recap_system_prompt()

    collected_event_records: list[dict[str, Any]] = []
    collected_claims: list[dict[str, Any]] = []

    def _usage_for_call(udict: dict[str, int]) -> UsageStats:
        billed = openai_client is not None
        return UsageStats(
            input_tokens=udict.get("input_tokens", 0),
            output_tokens=udict.get("output_tokens", 0),
            cached_tokens=udict.get("cached_tokens", 0),
            api_calls=1 if billed else 0,
        )

    slot_results: list[EntityExtractionResult | None] = [None] * len(evidence_units)
    recap_misses: list[tuple[int, dict[str, Any]]] = []
    standard_misses: list[tuple[int, dict[str, Any]]] = []

    def _load_cached_entity_unit(evidence_id: str, source_profile: str, cached_data: Any) -> EntityExtractionResult:
        if source_profile == "session_recap":
            recap_result = RecapExtractionResult.model_validate(cached_data)
            if recap_artifacts is not None:
                for ev in recap_result.event_records:
                    collected_event_records.append({**ev.model_dump(), "evidence_id": evidence_id})
                for cl in recap_result.claims:
                    collected_claims.append({**cl.model_dump(), "evidence_id": evidence_id})
            return EntityExtractionResult(entities=recap_result.entities)
        return EntityExtractionResult.model_validate(cached_data)

    for i, unit in enumerate(evidence_units):
        evidence_id = str(unit.get("evidence_id", "unknown"))
        source_profile = _resolve_source_profile(unit)
        cache_key = _cache_key(unit, model_id, source_profile)
        cache_file = _cache_path(cache_root, cache_key)
        if cache_file.exists():
            stats["cache_hits"] += 1
            stats["completed"] += 1
            logger.debug("entity_extractor unit=%s cache=hit", evidence_id)
            if stats["completed"] % progress_step == 0:
                logger.info(
                    "entity_extractor progress completed=%d/%d cache_hits=%d cache_misses=%d",
                    stats["completed"],
                    len(evidence_units),
                    stats["cache_hits"],
                    stats["cache_misses"],
                )
            cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
            slot_results[i] = _load_cached_entity_unit(evidence_id, source_profile, cached_data)
            continue
        if source_profile == "session_recap":
            recap_misses.append((i, unit))
        else:
            standard_misses.append((i, unit))

    total_usage = UsageStats()

    async def process_recap_miss(idx: int, unit: dict[str, Any]) -> None:
        evidence_id = str(unit.get("evidence_id", "unknown"))
        source_profile = _resolve_source_profile(unit)
        cache_key = _cache_key(unit, model_id, source_profile)
        cache_file = _cache_path(cache_root, cache_key)
        async with semaphore:
            stats["cache_misses"] += 1
            logger.debug("entity_extractor unit=%s cache=miss profile=%s", evidence_id, source_profile)
            recap_result, udict = await _call_recap_extractor(
                unit=unit,
                known_entities=known_entities,
                model_id=model_id,
                openai_client=openai_client,
                allow_heuristic_fallback=allow_heuristic_fallback,
                system_prompt=recap_system_prompt,
            )
            cache_file.write_text(recap_result.model_dump_json(indent=2), encoding="utf-8")
            if recap_artifacts is not None:
                for ev in recap_result.event_records:
                    collected_event_records.append({**ev.model_dump(), "evidence_id": evidence_id})
                for cl in recap_result.claims:
                    collected_claims.append({**cl.model_dump(), "evidence_id": evidence_id})
            result = EntityExtractionResult(entities=recap_result.entities)
            slot_results[idx] = result
            total_usage.merge(_usage_for_call(udict))
            stats["completed"] += 1
            logger.debug("entity_extractor unit=%s extracted_entities=%d", evidence_id, len(result.entities))
            if stats["completed"] % progress_step == 0:
                logger.info(
                    "entity_extractor progress completed=%d/%d cache_hits=%d cache_misses=%d",
                    stats["completed"],
                    len(evidence_units),
                    stats["cache_hits"],
                    stats["cache_misses"],
                )

    async def process_standard_one(idx: int, unit: dict[str, Any]) -> None:
        evidence_id = str(unit.get("evidence_id", "unknown"))
        source_profile = _resolve_source_profile(unit)
        cache_key = _cache_key(unit, model_id, source_profile)
        cache_file = _cache_path(cache_root, cache_key)
        async with semaphore:
            stats["cache_misses"] += 1
            logger.debug("entity_extractor unit=%s cache=miss profile=%s", evidence_id, source_profile)
            result, udict = await _call_extractor(
                unit=unit,
                known_entities=known_entities,
                model_id=model_id,
                openai_client=openai_client,
                allow_heuristic_fallback=allow_heuristic_fallback,
                system_prompt=entity_system_prompt,
            )
            cache_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            slot_results[idx] = result
            total_usage.merge(_usage_for_call(udict))
            stats["completed"] += 1
            logger.debug("entity_extractor unit=%s extracted_entities=%d", evidence_id, len(result.entities))
            if stats["completed"] % progress_step == 0:
                logger.info(
                    "entity_extractor progress completed=%d/%d cache_hits=%d cache_misses=%d",
                    stats["completed"],
                    len(evidence_units),
                    stats["cache_hits"],
                    stats["cache_misses"],
                )

    async def process_standard_batch(pairs: list[tuple[int, dict[str, Any]]]) -> None:
        if not pairs:
            return
        units_only = [u for _, u in pairs]
        async with semaphore:
            for _ in pairs:
                stats["cache_misses"] += 1
            if openai_client is None:
                if not allow_heuristic_fallback:
                    raise ValueError(
                        "Heuristic fallback is disabled; provide an openai_client for entity extraction."
                    )
                for idx, unit in pairs:
                    evidence_id = str(unit.get("evidence_id", "unknown"))
                    source_profile = _resolve_source_profile(unit)
                    cache_file = _cache_path(cache_root, _cache_key(unit, model_id, source_profile))
                    result = _heuristic_extract_entities(str(unit.get("text", "")))
                    cache_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                    slot_results[idx] = result
                    stats["completed"] += 1
                    logger.debug(
                        "entity_extractor unit=%s extracted_entities=%d",
                        evidence_id,
                        len(result.entities),
                    )
                    if stats["completed"] % progress_step == 0:
                        logger.info(
                            "entity_extractor progress completed=%d/%d cache_hits=%d cache_misses=%d",
                            stats["completed"],
                            len(evidence_units),
                            stats["cache_hits"],
                            stats["cache_misses"],
                        )
                return

            if not hasattr(openai_client, "extract_entities_batched"):
                raise ValueError(
                    "openai_client must expose extract_entities_batched(...) when batch_size > 1."
                )

            user_prompt = _build_batched_entity_user_prompt(units_only, known_entities)
            payload = openai_client.extract_entities_batched(
                model=model_id,
                system_prompt=entity_system_prompt,
                user_prompt=user_prompt,
                prompt_id=_PROMPT_ID,
            )
            if inspect.isawaitable(payload):
                payload = await payload
            body, udict = _pop_usage_from_entity_payload(payload)
            parsed = BatchedEntityExtractionResult.model_validate(body)
            by_slot: dict[int, UnitEntityResult] = {}
            for row in parsed.results:
                ui = row.unit_index
                if ui in by_slot:
                    logger.warning(
                        "entity_extractor batched call duplicate unit_index=%s (using last result)",
                        ui,
                    )
                by_slot[ui] = row
            expected_idx = set(range(len(pairs)))
            returned_idx = set(by_slot.keys())
            missing_idx = expected_idx - returned_idx
            extra_idx = returned_idx - expected_idx
            if missing_idx:
                logger.warning(
                    "entity_extractor batched call missing unit_index slots: %s",
                    sorted(missing_idx),
                )
            if extra_idx:
                logger.warning(
                    "entity_extractor batched call unexpected unit_index values: %s",
                    sorted(extra_idx),
                )
            total_usage.merge(_usage_for_call(udict))
            for local_j, (idx, unit) in enumerate(pairs):
                evidence_id = str(unit.get("evidence_id", "unknown"))
                source_profile = _resolve_source_profile(unit)
                cache_file = _cache_path(cache_root, _cache_key(unit, model_id, source_profile))
                row = by_slot.get(local_j)
                if row is None:
                    result = EntityExtractionResult(entities=[])
                else:
                    result = EntityExtractionResult(entities=list(row.entities))
                cache_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                slot_results[idx] = result
                stats["completed"] += 1
                logger.debug(
                    "entity_extractor unit=%s extracted_entities=%d",
                    evidence_id,
                    len(result.entities),
                )
                if stats["completed"] % progress_step == 0:
                    logger.info(
                        "entity_extractor progress completed=%d/%d cache_hits=%d cache_misses=%d",
                        stats["completed"],
                        len(evidence_units),
                        stats["cache_hits"],
                        stats["cache_misses"],
                    )

    try:
        tasks: list[Any] = [process_recap_miss(i, u) for i, u in recap_misses]
        if effective_batch <= 1:
            tasks.extend(process_standard_one(i, u) for i, u in standard_misses)
        else:
            for batch_i in range(0, len(standard_misses), effective_batch):
                chunk = standard_misses[batch_i : batch_i + effective_batch]
                tasks.append(process_standard_batch(chunk))
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
                logger.debug("entity_extractor client close failed", exc_info=True)

    if recap_artifacts is not None:
        recap_artifacts.setdefault("event_records", []).extend(collected_event_records)
        recap_artifacts.setdefault("claims", []).extend(collected_claims)

    results: list[EntityExtractionResult] = []
    for i, slot in enumerate(slot_results):
        if slot is None:
            raise RuntimeError(f"entity_extractor internal error: missing result for unit index {i}")
        results.append(slot)

    extracted_rows: list[tuple[str, str, int, ExtractedEntity]] = []
    for unit, result in zip(evidence_units, results, strict=False):
        evidence_id = str(unit.get("evidence_id", "unknown"))
        source_text = str(unit.get("text", ""))
        for idx, entity in enumerate(result.entities):
            extracted_rows.append((evidence_id, source_text, idx, entity))

    mention_counts: dict[str, int] = {}
    for _evidence_id, _source_text, _idx, entity in extracted_rows:
        key = _match_key(entity.display_name)
        if key:
            mention_counts[key] = mention_counts.get(key, 0) + 1

    records: list[dict[str, Any]] = []
    excluded_candidates: list[dict[str, Any]] = []
    for evidence_id, source_text, idx, entity in extracted_rows:
        if entity.decision == "exclude":
            excluded_candidates.append({
                "display_name": entity.display_name,
                "exclude_reason": entity.exclude_reason,
                "entity_class": entity.entity_class,
                "source": "llm_exclude",
                "evidence_id": evidence_id,
            })
            continue
        mention_count = mention_counts.get(_match_key(entity.display_name), 0)
        if not _is_plausible_entity_name(
            display_name=entity.display_name,
            entity_class=entity.entity_class or entity.entity_kind,
            source_text=source_text,
            known_lookup=known_lookup,
            mention_count=mention_count,
        ):
            excluded_candidates.append({
                "display_name": entity.display_name,
                "exclude_reason": "heuristic_filter",
                "entity_class": entity.entity_class,
                "source": "heuristic_filter",
                "evidence_id": evidence_id,
            })
            continue
        mention_id = f"men_{evidence_id}_{idx}"
        records.append(
            _entity_record_from_extracted(
                entity,
                known_lookup=known_lookup,
                mention_id=mention_id,
            )
        )

    if excluded_candidates:
        excluded_path = cache_root / "excluded_candidates.json"
        existing_excluded: list[dict[str, Any]] = []
        if excluded_path.exists():
            try:
                existing_excluded = json.loads(excluded_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                existing_excluded = []
        existing_excluded.extend(excluded_candidates)
        excluded_path.write_text(
            json.dumps(existing_excluded, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    if schema_repair_batch and list_validation_failures(records, "entity.schema.json"):
        import os

        from openai import OpenAI

        from src.ingestion.schema_repair_batch import repair_entity_records_via_openai_batch

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("schema_repair_batch requires OPENAI_API_KEY when records fail validation.")
        rdir = schema_repair_work_dir or (cache_root / "schema_repair")
        repair_client = OpenAI(api_key=api_key)
        records, rmeta = repair_entity_records_via_openai_batch(
            records,
            client=repair_client,
            repair_model=schema_repair_model,
            work_dir=rdir,
            poll_interval_sec=schema_repair_poll_interval,
            print_status=True,
        )
        if not rmeta.get("skipped"):
            ru = rmeta.get("usage") or {}
            total_usage.merge(
                UsageStats(
                    input_tokens=int(ru.get("input_tokens", 0)),
                    output_tokens=int(ru.get("output_tokens", 0)),
                    cached_tokens=int(ru.get("cached_tokens", 0)),
                    api_calls=1,
                )
            )

    validate_many(records, "entity.schema.json")
    deduper = FactStore(cache_root / "_dedupe")
    deduper.add_entities(records)
    deduped = deduper.list_entities()
    logger.info(
        "entity_extractor done units=%d extracted=%d deduped=%d excluded=%d cache_hits=%d cache_misses=%d",
        len(evidence_units),
        len(records),
        len(deduped),
        len(excluded_candidates),
        stats["cache_hits"],
        stats["cache_misses"],
    )
    return {
        "entities": deduped,
        "usage": total_usage.to_dict(),
        "cache_hits": stats["cache_hits"],
        "cache_misses": stats["cache_misses"],
        "model_name": model_id,
    }


def run_entity_extraction(
    evidence_units: list[dict[str, Any]],
    *,
    known_entities: list[dict[str, Any]] | None = None,
    model: str | None = None,
    concurrency: int = 8,
    batch_size: int = 1,
    cache_dir: Path | None = None,
    openai_client: Any | None = None,
    allow_heuristic_fallback: bool = True,
    recap_artifacts: dict[str, list[dict[str, Any]]] | None = None,
    schema_repair_batch: bool = False,
    schema_repair_model: str = "gpt-5.4",
    schema_repair_poll_interval: float = 30.0,
    schema_repair_work_dir: Path | None = None,
) -> dict[str, Any]:
    return asyncio.run(
        extract_entities_batch(
            evidence_units,
            known_entities=known_entities,
            model=model,
            concurrency=concurrency,
            batch_size=batch_size,
            cache_dir=cache_dir,
            openai_client=openai_client,
            allow_heuristic_fallback=allow_heuristic_fallback,
            recap_artifacts=recap_artifacts,
            schema_repair_batch=schema_repair_batch,
            schema_repair_model=schema_repair_model,
            schema_repair_poll_interval=schema_repair_poll_interval,
            schema_repair_work_dir=schema_repair_work_dir,
        )
    )


def prepare_entity_batch_requests(
    evidence_units: list[dict[str, Any]],
    *,
    known_entities: list[dict[str, Any]],
    model: str,
    batch_size: int = 5,
    cache_dir: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build JSONL request lines for OpenAI Batch API (/v1/responses). Skips cache hits.

    Returns (jsonl_line_dicts, manifest) where manifest[custom_id] describes how to apply results.
    """
    from src.ingestion.openai_batch_pipeline import (
        build_jsonl_request_line,
        build_responses_batch_request_body,
    )
    from src.ingestion.recap_models import RecapExtractionResult

    known_entities = list(known_entities)
    model_id = model
    cache_root = Path(cache_dir) if cache_dir is not None else (Path.cwd() / ".entity_extractor_cache")
    cache_root.mkdir(parents=True, exist_ok=True)

    recap_misses: list[dict[str, Any]] = []
    standard_misses: list[dict[str, Any]] = []

    for unit in evidence_units:
        source_profile = _resolve_source_profile(unit)
        cache_key = _cache_key(unit, model_id, source_profile)
        cache_file = _cache_path(cache_root, cache_key)
        if cache_file.exists():
            continue
        if source_profile == "session_recap":
            recap_misses.append(unit)
        else:
            standard_misses.append(unit)

    lines: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {}
    batch_index = 0
    entity_system = _build_entity_system_prompt()
    recap_system = _build_recap_system_prompt()

    for unit in recap_misses:
        cid = f"entity_recap_{batch_index:04d}"
        batch_index += 1
        user_prompt = _build_recap_user_prompt(unit, known_entities)
        body = build_responses_batch_request_body(
            model=model_id,
            system_prompt=recap_system,
            user_prompt=user_prompt,
            text_format=RecapExtractionResult,
        )
        lines.append(build_jsonl_request_line(custom_id=cid, body=body))
        manifest[cid] = {"kind": "recap", "unit": unit}

    effective_batch = max(1, batch_size)
    for i in range(0, len(standard_misses), effective_batch):
        chunk = standard_misses[i : i + effective_batch]
        cid = f"entity_batch_{batch_index:04d}"
        batch_index += 1
        user_prompt = _build_batched_entity_user_prompt(chunk, known_entities)
        body = build_responses_batch_request_body(
            model=model_id,
            system_prompt=entity_system,
            user_prompt=user_prompt,
            text_format=BatchedEntityExtractionResult,
        )
        lines.append(build_jsonl_request_line(custom_id=cid, body=body))
        manifest[cid] = {"kind": "batched_entities", "units": chunk}

    return lines, manifest


def apply_entity_batch_outputs_to_cache(
    output_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    model_id: str,
    cache_dir: Path,
) -> tuple[list[str], dict[str, int]]:
    """Parse batch output rows and write entity extractor cache files.

    Returns (failed_custom_ids, usage_totals).
    """
    from src.ingestion.openai_batch_pipeline import (
        extract_output_text_from_responses_body,
        extract_response_body_from_batch_line,
        extract_status_code_from_batch_line,
        merge_usage,
        usage_dict_from_responses_body,
    )
    from src.ingestion.recap_models import RecapExtractionResult

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
        kind = spec.get("kind")
        try:
            if kind == "recap":
                unit = spec["unit"]
                source_profile = _resolve_source_profile(unit)
                recap_result = RecapExtractionResult.model_validate_json(text)
                cache_file = _cache_path(cache_root, _cache_key(unit, model_id, source_profile))
                cache_file.write_text(recap_result.model_dump_json(indent=2), encoding="utf-8")
            elif kind == "batched_entities":
                parsed = BatchedEntityExtractionResult.model_validate_json(text)
                by_slot: dict[int, UnitEntityResult] = {}
                for r in parsed.results:
                    ui = r.unit_index
                    if ui in by_slot:
                        logger.warning(
                            "entity batch output duplicate unit_index=%s (using last)",
                            ui,
                        )
                    by_slot[ui] = r
                for slot_j, unit in enumerate(spec["units"]):
                    source_profile = _resolve_source_profile(unit)
                    cache_file = _cache_path(cache_root, _cache_key(unit, model_id, source_profile))
                    row_result = by_slot.get(slot_j)
                    if row_result is None:
                        single = EntityExtractionResult(entities=[])
                    else:
                        single = EntityExtractionResult(entities=list(row_result.entities))
                    cache_file.write_text(single.model_dump_json(indent=2), encoding="utf-8")
            else:
                failures.append(cid)
        except Exception:
            failures.append(cid)

    return failures, usage_totals
