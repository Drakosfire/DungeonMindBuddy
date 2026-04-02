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

from src.contracts.entity_tags import DEFAULT_MAX_ENTITY_TAGS, normalize_entity_tags
from src.contracts.entity_taxonomy import (
    EntityKind,
    normalize_semantic_facets,
)
from src.contracts.schema_validation import validate_many
from src.store import FactStore

_PROMPT_ID = "phase_b_pass1_entity_extraction_v3_taxonomy_refresh"
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
_TYPE_KEYWORDS: dict[str, set[str]] = {
    "location": {
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
    "faction": {
        "flock",
        "council",
        "guild",
        "empire",
        "cult",
        "guard",
        "guards",
    },
    "item": {"artifact", "relic", "vial", "toxin", "weapon", "blade", "sword"},
}

logger = logging.getLogger(__name__)


class ExtractedEntity(BaseModel):
    entity_id: str | None = None
    entity_type: Literal["npc", "location", "faction", "item", "other"] = "other"
    entity_kind: EntityKind | None = None
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    entity_tags: list[str] = Field(default_factory=list)
    semantic_facets: list[str] = Field(default_factory=list)
    is_new: bool = True


class EntityExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)


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
        prompt: str,
        evidence_unit: dict[str, Any],
        known_entities: list[dict[str, Any]],
        prompt_id: str,
    ) -> dict[str, Any]:
        response = self._client.responses.parse(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            text_format=EntityExtractionResult,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, EntityExtractionResult):
            return parsed.model_dump()
        return EntityExtractionResult.model_validate(parsed).model_dump()


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
        prompt: str,
        evidence_unit: dict[str, Any],
        known_entities: list[dict[str, Any]],
        prompt_id: str,
    ) -> dict[str, Any]:
        response = await self._client.responses.parse(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            text_format=EntityExtractionResult,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise ValueError("OpenAI response parse did not return output_parsed.")
        if isinstance(parsed, EntityExtractionResult):
            return parsed.model_dump()
        return EntityExtractionResult.model_validate(parsed).model_dump()


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


def _infer_entity_type(display_name: str) -> Literal["npc", "location", "faction", "item", "other"]:
    lowered = display_name.lower()
    tokens = set(re.findall(r"[a-z]+", lowered))
    for label, keywords in _TYPE_KEYWORDS.items():
        if tokens & keywords:
            return label  # type: ignore[return-value]
    words = display_name.split()
    if len(words) >= 2 and all(word[:1].isupper() for word in words if word and word.lower() not in _CONNECTORS):
        return "npc"
    return "other"


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


def _heuristic_extract_entities(text: str) -> EntityExtractionResult:
    names = _candidate_name_spans(text)
    entities: list[ExtractedEntity] = []
    for display_name in _dedupe_names(names):
        entities.append(
            ExtractedEntity(
                entity_id=None,
                entity_type=_infer_entity_type(display_name),
                display_name=display_name,
                aliases=[],
                is_new=True,
            )
        )
    return EntityExtractionResult(entities=entities)


def _cache_key(unit: dict[str, Any], model_id: str) -> str:
    text_fp = blake3.blake3(str(unit.get("text", "")).encode("utf-8")).hexdigest()
    payload = f"{text_fp}|{_PROMPT_ID}|{model_id}"
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


def _build_prompt(unit: dict[str, Any], known_entities: list[dict[str, Any]]) -> str:
    unit_text = unit.get("text", "")
    known_minimal = _relevant_known_entities(known_entities, unit_text)
    return (
        "You are an entity extraction agent for a TTRPG worldbuilding system.\n"
        "Extract named entities from the text with high precision and stable taxonomy.\n"
        "Include proper names and durable named concepts that matter for retrieval across sessions.\n"
        "DO NOT output full-sentence fragments, generic prose phrases, or purely descriptive clauses.\n\n"
        "Taxonomy policy:\n"
        "- entity_type must be one of: npc, location, faction, item, other.\n"
        "- entity_kind must be one of: actor, group, place, object, event, concept, document_anchor, unknown.\n"
        "- Prefer entity_kind=event for named events/festivals/battles.\n"
        "- Prefer entity_kind=concept for named rituals/doctrines/themes/cosmology concepts.\n"
        "- Use entity_type=other only when npc/location/faction/item do not fit.\n"
        "- Keep entity_type stable and use semantic_facets for nuance.\n"
        "- semantic_facets should use controlled tokens when possible:\n"
        "  deity, species, creature_species, profession, title, festival, ritual, ceremony,\n"
        "  organization, government, trade_good, consumable, artifact, weapon,\n"
        "  document_section, plot_hook, theme, conflict, route, settlement.\n"
        "- Campaign-specific facets may be emitted as domain:<token> (example: domain:eldyrwild_cult).\n"
        "- Do not invent facets unrelated to the text.\n\n"
        f"Known entities (reuse IDs if recognized):\n{json.dumps(known_minimal, ensure_ascii=False)}\n\n"
        "Return JSON with shape: {\"entities\": [...]} where each entity has:\n"
        "entity_id (optional), entity_type, entity_kind, display_name, aliases, is_new, "
        "entity_tags (legacy optional), semantic_facets (optional).\n"
        "entity_tags may be kept for backward compatibility, but semantic_facets are preferred.\n\n"
        f"Evidence unit:\n{unit_text}"
    )


async def _call_extractor(
    unit: dict[str, Any],
    known_entities: list[dict[str, Any]],
    model_id: str,
    openai_client: Any | None,
    *,
    allow_heuristic_fallback: bool,
) -> EntityExtractionResult:
    if openai_client is None:
        if not allow_heuristic_fallback:
            raise ValueError(
                "Heuristic fallback is disabled; provide an openai_client for entity extraction."
            )
        return _heuristic_extract_entities(str(unit.get("text", "")))

    if not hasattr(openai_client, "extract_entities"):
        raise ValueError("openai_client must expose extract_entities(...)")

    payload = openai_client.extract_entities(
        model=model_id,
        prompt=_build_prompt(unit, known_entities),
        evidence_unit=unit,
        known_entities=known_entities,
        prompt_id=_PROMPT_ID,
    )
    if inspect.isawaitable(payload):
        payload = await payload
    return EntityExtractionResult.model_validate(payload)


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
    raw_facets = list(extracted.semantic_facets) + list(extracted.entity_tags)
    semantic_facets = normalize_semantic_facets(raw_facets)
    legacy_tags = normalize_entity_tags(raw_facets, max_tags=DEFAULT_MAX_ENTITY_TAGS)
    mapped_kind: EntityKind | None = extracted.entity_kind
    if mapped_kind is None:
        type_to_kind: dict[str, EntityKind] = {
            "npc": "actor",
            "location": "place",
            "faction": "group",
            "item": "object",
            "other": "unknown",
        }
        mapped_kind = type_to_kind.get(extracted.entity_type, "unknown")
        if extracted.entity_type == "other":
            facet_set = set(semantic_facets)
            if "festival" in facet_set or "ritual" in facet_set or "ceremony" in facet_set:
                mapped_kind = "event"
            elif "deity" in facet_set or "theme" in facet_set:
                mapped_kind = "concept"
    return {
        "schema_version": "0.1.0",
        "created_at": now_iso,
        "updated_at": now_iso,
        "record_status": "active",
        "entity_id": _sanitize_id(entity_id),
        "entity_type": extracted.entity_type,
        "entity_kind": mapped_kind,
        "display_name": display_name,
        "canonical_name": None,
        "aliases": aliases,
        "entity_status": "provisional",
        "merged_into_entity_id": None,
        "source_mention_ids": [_sanitize_id(mention_id, prefix="men")],
        "review_state": "unreviewed",
        "entity_tags": legacy_tags,
        "semantic_facets": semantic_facets,
        "notes": None,
    }


def _is_plausible_entity_name(
    *,
    display_name: str,
    entity_type: Literal["npc", "location", "faction", "item", "other"],
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
        if entity_type == "other" and len(tokens[0]) < 5:
            return False

    # Drop purely structural/title lines with low semantic signal.
    if entity_type == "other":
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
    cache_dir: Path | None = None,
    openai_client: Any | None = None,
    allow_heuristic_fallback: bool = True,
) -> list[dict[str, Any]]:
    known_entities = known_entities or []
    model_id = model or _load_fast_smart_model_id()
    cache_root = Path(cache_dir) if cache_dir is not None else (Path.cwd() / ".entity_extractor_cache")
    cache_root.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(max(1, concurrency))
    known_lookup = _build_known_lookup(known_entities)
    stats = {"completed": 0, "cache_hits": 0, "cache_misses": 0}
    progress_step = max(10, len(evidence_units) // 10) if evidence_units else 10
    logger.info(
        "entity_extractor start units=%d concurrency=%d model=%s cache_dir=%s",
        len(evidence_units),
        concurrency,
        model_id,
        cache_root,
    )

    async def process_unit(unit: dict[str, Any]) -> EntityExtractionResult:
        evidence_id = str(unit.get("evidence_id", "unknown"))
        cache_key = _cache_key(unit, model_id)
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
            return EntityExtractionResult.model_validate(
                json.loads(cache_file.read_text(encoding="utf-8"))
            )

        async with semaphore:
            stats["cache_misses"] += 1
            logger.debug("entity_extractor unit=%s cache=miss", evidence_id)
            result = await _call_extractor(
                unit=unit,
                known_entities=known_entities,
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
            return result

    results = await asyncio.gather(*(process_unit(unit) for unit in evidence_units))

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
    for evidence_id, source_text, idx, entity in extracted_rows:
        mention_count = mention_counts.get(_match_key(entity.display_name), 0)
        if not _is_plausible_entity_name(
            display_name=entity.display_name,
            entity_type=entity.entity_type,
            source_text=source_text,
            known_lookup=known_lookup,
            mention_count=mention_count,
        ):
            continue
        mention_id = f"men_{evidence_id}_{idx}"
        records.append(
            _entity_record_from_extracted(
                entity,
                known_lookup=known_lookup,
                mention_id=mention_id,
            )
        )

    validate_many(records, "entity.schema.json")
    deduper = FactStore(cache_root / "_dedupe")
    deduper.add_entities(records)
    deduped = deduper.list_entities()
    logger.info(
        "entity_extractor done units=%d extracted=%d deduped=%d cache_hits=%d cache_misses=%d",
        len(evidence_units),
        len(records),
        len(deduped),
        stats["cache_hits"],
        stats["cache_misses"],
    )
    return deduped


def run_entity_extraction(
    evidence_units: list[dict[str, Any]],
    *,
    known_entities: list[dict[str, Any]] | None = None,
    model: str | None = None,
    concurrency: int = 8,
    cache_dir: Path | None = None,
    openai_client: Any | None = None,
    allow_heuristic_fallback: bool = True,
) -> list[dict[str, Any]]:
    return asyncio.run(
        extract_entities_batch(
            evidence_units,
            known_entities=known_entities,
            model=model,
            concurrency=concurrency,
            cache_dir=cache_dir,
            openai_client=openai_client,
            allow_heuristic_fallback=allow_heuristic_fallback,
        )
    )
