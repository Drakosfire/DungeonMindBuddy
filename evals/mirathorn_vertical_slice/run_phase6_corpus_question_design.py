"""Phase 6 runner: corpus inventory + candidate question design + store coverage."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = PROJECT_ROOT / "corpus" / "eldyrwild-markdown"
OUTPUT_DIR = PROJECT_ROOT / "evals" / "mirathorn_vertical_slice" / "output"
STORE_DIR = OUTPUT_DIR / "phase_d_store"

MANIFEST_PATH = OUTPUT_DIR / "phase6_corpus_manifest.json"
CANDIDATES_PATH = OUTPUT_DIR / "phase6_candidate_questions.json"
SAMPLE_REVIEW_PATH = OUTPUT_DIR / "phase6_sample_review.md"
SUMMARY_PATH = OUTPUT_DIR / "phase6_summary.json"

TOKEN_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "over",
    "under",
    "through",
    "city",
    "council",
    "session",
    "mirathorn",
    "elderwyld",
    "campaign",
}

PHRASE_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "of",
    "in",
    "to",
    "for",
    "on",
    "with",
}

TOP_DOC_LIMIT = 5
QUESTIONS_PER_DOC = 4
SAMPLE_LIMIT = 10
FUZZY_SUPPORT_THRESHOLD = 0.72


@dataclass
class EntityRecord:
    entity_id: str
    display_name: str
    aliases: list[str]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _extract_frontmatter(body: str) -> tuple[dict[str, str], str]:
    if not body.startswith("---\n"):
        return {}, body

    match = re.match(r"^---\n(.*?)\n---\n?", body, re.DOTALL)
    if not match:
        return {}, body

    raw = match.group(1)
    frontmatter: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"')
    content = body[match.end() :]
    return frontmatter, content


def _infer_narrative_type(path: Path, frontmatter: dict[str, str], text: str) -> str:
    rel = str(path.relative_to(CORPUS_ROOT)).lower()
    title = frontmatter.get("title", "").lower()
    haystack = f"{rel} {title} {text[:500].lower()}"
    if "session recap" in haystack or "/session recaps/" in haystack:
        return "session_recap"
    if "battle" in haystack or "aftermath" in haystack or "emergency" in haystack:
        return "event_sequence"
    if "council" in haystack and "proposal" in haystack:
        return "event_sequence"
    if "/npcs/" in haystack or "dossier" in haystack or "characteristics" in haystack:
        return "character_profile"
    if "notes" in haystack or "prep" in haystack or "ledger" in haystack:
        return "campaign_notes"
    return "static_description"


def _extract_entities(text: str) -> list[str]:
    # Capitalized phrase extractor for lightweight profiling.
    pattern = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b")
    phrases = pattern.findall(text)
    counts: Counter[str] = Counter()
    for phrase in phrases:
        tokens = [token.lower() for token in phrase.split()]
        if len(tokens) == 1 and tokens[0] in TOKEN_STOPWORDS:
            continue
        if all(token in PHRASE_STOPWORDS for token in tokens):
            continue
        counts[phrase] += 1
    return [name for name, _ in counts.most_common(12)]


def _compute_priority_score(record: dict[str, Any]) -> int:
    score = 0
    narrative_type = record["narrative_type"]
    if narrative_type == "event_sequence":
        score += 40
    elif narrative_type == "session_recap":
        score += 35
    elif narrative_type == "campaign_notes":
        score += 25
    elif narrative_type == "static_description":
        score += 15
    else:
        score += 10

    if record["canon_layer"] == "campaign":
        score += 12
    if "city council building" in record["path"].lower():
        score += 18
    if "general notes" in record["path"].lower():
        score += 15
    score += min(20, len(record["key_entities"]) // 2)
    score += min(15, record["word_count"] // 250)
    return score


def build_manifest() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(CORPUS_ROOT.rglob("*.md")):
        body = path.read_text(encoding="utf-8")
        frontmatter, content = _extract_frontmatter(body)
        title = frontmatter.get("title") or path.stem
        document_class = frontmatter.get("document_class", "unknown")
        canon_layer = frontmatter.get("canon_layer", "unknown")
        narrative_type = _infer_narrative_type(path, frontmatter, content)
        entities = _extract_entities(content)
        record = {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "title": title,
            "document_class": document_class,
            "canon_layer": canon_layer,
            "word_count": _word_count(content),
            "key_entities": entities,
            "narrative_type": narrative_type,
        }
        record["priority_score"] = _compute_priority_score(record)
        records.append(record)
    records.sort(key=lambda row: row["priority_score"], reverse=True)
    return records


def _entity_records() -> list[EntityRecord]:
    rows = _read_json(STORE_DIR / "entities.json")
    result: list[EntityRecord] = []
    for row in rows:
        result.append(
            EntityRecord(
                entity_id=str(row.get("entity_id", "")),
                display_name=str(row.get("display_name", "")),
                aliases=[str(alias) for alias in row.get("aliases", []) if alias],
            )
        )
    return result


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _name_tokens(value: str) -> list[str]:
    return [
        token
        for token in _normalize_name(value).split()
        if token and token not in PHRASE_STOPWORDS and len(token) >= 3
    ]


def _tokenize_text(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", value.lower()) if token]


def _exact_phrase_count(normalized_text: str, normalized_phrase: str) -> int:
    if not normalized_phrase:
        return 0
    pattern = rf"\b{re.escape(normalized_phrase)}\b"
    return len(re.findall(pattern, normalized_text))


def _max_window_jaccard(
    target_tokens: list[str],
    document_tokens: list[str],
) -> float:
    if not target_tokens or not document_tokens:
        return 0.0

    target_set = set(target_tokens)
    lengths = {max(1, len(target_tokens) - 1), len(target_tokens), len(target_tokens) + 1}
    best = 0.0
    for size in lengths:
        if size <= 0 or size > len(document_tokens):
            continue
        for start in range(0, len(document_tokens) - size + 1):
            window_set = set(document_tokens[start : start + size])
            union = len(target_set | window_set)
            if union == 0:
                continue
            score = len(target_set & window_set) / union
            if score > best:
                best = score
    return best


def _resolve_entity_ids(
    names: list[str],
    entities: list[EntityRecord],
) -> tuple[list[str], list[str]]:
    resolved_ids: list[str] = []
    unresolved_names: list[str] = []
    entity_candidates: list[tuple[str, str, set[str]]] = []
    for entity in entities:
        for candidate in [entity.display_name, *entity.aliases]:
            cn = _normalize_name(candidate)
            if not cn:
                continue
            tokens = {
                token
                for token in cn.split()
                if token and token not in PHRASE_STOPWORDS and len(token) >= 3
            }
            entity_candidates.append((entity.entity_id, cn, tokens))

    for name in names:
        normalized = _normalize_name(name)
        name_tokens = {
            token
            for token in normalized.split()
            if token and token not in PHRASE_STOPWORDS and len(token) >= 3
        }
        found = None

        # First pass: exact normalized phrase match.
        for entity_id, cn, _tokens in entity_candidates:
            if normalized == cn:
                found = entity_id
                break

        # Second pass: token overlap matching with strict threshold.
        if not found and name_tokens:
            best_score = 0.0
            best_entity = None
            for entity_id, _cn, candidate_tokens in entity_candidates:
                if not candidate_tokens:
                    continue
                overlap = len(name_tokens & candidate_tokens)
                union = len(name_tokens | candidate_tokens)
                if union == 0:
                    continue
                score = overlap / union
                if overlap >= 1 and score >= 0.6 and score > best_score:
                    best_score = score
                    best_entity = entity_id
            if best_entity:
                found = best_entity

        if found:
            resolved_ids.append(found)
        else:
            unresolved_names.append(name)
    # Preserve order but dedupe.
    seen = set()
    deduped = []
    for entity_id in resolved_ids:
        if entity_id in seen:
            continue
        seen.add(entity_id)
        deduped.append(entity_id)
    return deduped, unresolved_names


def _build_entity_lookup(entities: list[EntityRecord]) -> dict[str, EntityRecord]:
    return {entity.entity_id: entity for entity in entities}


def _check_entity_support_in_document(
    *,
    requested_name: str,
    resolved_entity_id: str | None,
    entity_lookup: dict[str, EntityRecord],
    normalized_text: str,
    document_tokens: list[str],
) -> dict[str, Any]:
    variants = [requested_name]
    if resolved_entity_id and resolved_entity_id in entity_lookup:
        entity = entity_lookup[resolved_entity_id]
        variants.extend([entity.display_name, *entity.aliases])
    # Preserve order while removing empty/duplicate variants.
    seen_variants = set()
    deduped_variants = []
    for variant in variants:
        norm = _normalize_name(variant)
        if not norm or norm in seen_variants:
            continue
        seen_variants.add(norm)
        deduped_variants.append(variant)

    exact_hits: dict[str, int] = {}
    best_fuzzy_variant = ""
    best_fuzzy_score = 0.0

    for variant in deduped_variants:
        normalized_variant = _normalize_name(variant)
        exact_count = _exact_phrase_count(normalized_text, normalized_variant)
        if exact_count > 0:
            exact_hits[variant] = exact_count

        tokens = _name_tokens(variant)
        score = _max_window_jaccard(tokens, document_tokens)
        if score > best_fuzzy_score:
            best_fuzzy_score = score
            best_fuzzy_variant = variant

    if exact_hits:
        status = "supported"
    elif best_fuzzy_score >= FUZZY_SUPPORT_THRESHOLD:
        status = "weakly_supported"
    else:
        status = "unsupported"

    return {
        "requested_name": requested_name,
        "resolved_entity_id": resolved_entity_id,
        "status": status,
        "exact_hits": exact_hits,
        "best_fuzzy_variant": best_fuzzy_variant,
        "best_fuzzy_score": round(best_fuzzy_score, 3),
    }


def preflight_check_candidates(
    candidates: list[dict[str, Any]],
    entities: list[EntityRecord],
) -> list[dict[str, Any]]:
    entity_lookup = _build_entity_lookup(entities)
    checked: list[dict[str, Any]] = []

    for candidate in candidates:
        source_path = PROJECT_ROOT / candidate["document_source"]
        raw_text = source_path.read_text(encoding="utf-8")
        _frontmatter, content = _extract_frontmatter(raw_text)
        normalized_text = _normalize_name(content)
        document_tokens = _tokenize_text(content)

        requested_names = list(candidate.get("target_entity_names_requested", []))
        resolved_ids = list(candidate.get("target_entities", []))
        unresolved_names = set(candidate.get("unresolved_target_entity_names", []))

        support_details: list[dict[str, Any]] = []
        for idx, requested_name in enumerate(requested_names):
            resolved_entity_id = resolved_ids[idx] if idx < len(resolved_ids) else None
            support_details.append(
                _check_entity_support_in_document(
                    requested_name=requested_name,
                    resolved_entity_id=resolved_entity_id,
                    entity_lookup=entity_lookup,
                    normalized_text=normalized_text,
                    document_tokens=document_tokens,
                )
            )

        # Unresolved names are explicitly unsupported in preflight.
        for unresolved in unresolved_names:
            support_details.append(
                {
                    "requested_name": unresolved,
                    "resolved_entity_id": None,
                    "status": "unsupported",
                    "exact_hits": {},
                    "best_fuzzy_variant": "",
                    "best_fuzzy_score": 0.0,
                }
            )

        statuses = [row["status"] for row in support_details]
        if statuses and all(status == "supported" for status in statuses):
            preflight_status = "supported"
        elif "supported" in statuses or "weakly_supported" in statuses:
            preflight_status = "weakly_supported"
        else:
            preflight_status = "unsupported"

        row = dict(candidate)
        row["preflight_support_status"] = preflight_status
        row["preflight_support_details"] = support_details
        checked.append(row)

    return checked


def _question_templates() -> dict[str, list[dict[str, Any]]]:
    return {
        "The Council Room.md": [
            {
                "question": "What visual details should players notice first when they enter the Council Room?",
                "expected_answer_summary": "The room features high arched ceilings, a floating chandelier, historical tapestries, and a circular oak table with metal and quartz detailing.",
                "must_hit_tokens": ["arched ceilings", "floating chandelier", "tapestries", "circular table"],
                "stale_tokens": ["plain room", "bare walls", "no magical lighting"],
                "update_signal_tokens": ["floating", "enchantments", "industrial gears"],
                "semantic_equivalences": {
                    "arched ceilings": ["vaulted ceilings", "high arches"],
                    "floating chandelier": ["levitating chandelier", "magically suspended chandelier"],
                    "circular table": ["round table", "ringed council table"],
                },
                "target_entity_names": ["Council Chamber", "Mirathorn"],
                "target_attributes": ["geography", "visual_description"],
                "surface": "core_extraction",
                "tier": "must_pass",
            },
            {
                "question": "How does the council chamber support political transparency while still allowing private deliberation?",
                "expected_answer_summary": "The main room is open and built for collaboration, while side chambers allow private discussions when needed.",
                "must_hit_tokens": ["transparency", "collaboration", "side chambers", "private deliberations"],
                "stale_tokens": ["sealed bunker", "no side rooms"],
                "update_signal_tokens": ["open design", "side chambers"],
                "semantic_equivalences": {
                    "transparency": ["open proceedings", "public-facing deliberation"],
                    "side chambers": ["adjacent rooms", "private rooms"],
                },
                "target_entity_names": ["City Council", "Council Chamber"],
                "target_attributes": ["governance", "geography"],
                "surface": "core_extraction",
                "tier": "must_pass",
            },
            {
                "question": "What sensory cues in the Council Room increase tension during roleplay scenes?",
                "expected_answer_summary": "Acoustics carry voices, the chandelier can flicker, and the walls hum with embedded gears, creating pressure and atmosphere.",
                "must_hit_tokens": ["acoustics", "voices carry", "flicker", "hum of gears"],
                "stale_tokens": ["silent room", "steady lighting", "no ambient sound"],
                "update_signal_tokens": ["flicker", "hum", "carry clearly"],
                "semantic_equivalences": {
                    "voices carry": ["sound carries", "clear acoustics"],
                    "hum of gears": ["industrial hum", "mechanical resonance"],
                },
                "target_entity_names": ["Council Chamber"],
                "target_attributes": ["sensory_description", "defenses"],
                "surface": "vertical_slice",
                "tier": "should_pass",
            },
            {
                "question": "Which symbolic features in the room reinforce Mirathorn's civic history?",
                "expected_answer_summary": "Founding tapestries and statues of gnome and dragonborn founders emphasize historical continuity and civic responsibility.",
                "must_hit_tokens": ["founding tapestries", "statues", "gnomes", "dragonborn founders"],
                "stale_tokens": ["no historical symbols", "generic decor"],
                "update_signal_tokens": ["founding", "heroes", "history"],
                "semantic_equivalences": {
                    "founding tapestries": ["historical tapestries", "city founding tapestries"],
                    "statues": ["stone statues", "founder monuments"],
                },
                "target_entity_names": ["Mirathorn", "City Council"],
                "target_attributes": ["history", "culture"],
                "surface": "core_extraction",
                "tier": "must_pass",
            },
        ],
        "Battle with The Wolf and Aftermath.md": [
            {
                "question": "What happens to The Wolf by the end of the council chamber fight?",
                "expected_answer_summary": "The Wolf is ultimately killed, with Bonogo delivering the killing blow and decapitation-style terminal outcome.",
                "must_hit_tokens": ["killed", "killing blow", "bonogo", "decapitated"],
                "stale_tokens": ["escaped safely", "still alive", "still stalling"],
                "update_signal_tokens": ["terminal outcome", "aftermath", "dead"],
                "semantic_equivalences": {
                    "killing blow": ["fatal strike", "final blow", "decapitated"],
                    "killed": ["dead", "slain"],
                },
                "target_entity_names": ["The Wolf", "Bonogo"],
                "target_attributes": ["status", "combat_outcome"],
                "surface": "core_extraction",
                "tier": "must_pass",
            },
            {
                "question": "Which environmental defenses in the council chamber change the battle flow?",
                "expected_answer_summary": "Arcane traps, falling debris, alarm pulses, and illusory walls force positioning and can trigger reinforcements.",
                "must_hit_tokens": ["arcane traps", "falling debris", "alarm pulses", "illusory walls"],
                "stale_tokens": ["normal battlefield", "no magical defenses"],
                "update_signal_tokens": ["defenses activate", "runes", "reinforcements"],
                "semantic_equivalences": {
                    "arcane traps": ["rune traps", "magical traps"],
                    "alarm pulses": ["sonic pulses", "arcane alarm"],
                },
                "target_entity_names": ["Council Chamber", "The Wolf"],
                "target_attributes": ["defenses", "combat_context"],
                "surface": "core_extraction",
                "tier": "must_pass",
            },
            {
                "question": "How does Thalia's condition differ from fully corrupted guards during this encounter?",
                "expected_answer_summary": "Thalia is presented as ensorcelled/manipulated rather than fully corrupted, while many guards are explicitly corrupted.",
                "must_hit_tokens": ["thalia", "ensorcelled", "not fully corrupted", "corrupted guards"],
                "stale_tokens": ["thalia fully corrupted", "all guards uncorrupted"],
                "update_signal_tokens": ["manipulated", "influence", "wolf betrayal"],
                "semantic_equivalences": {
                    "ensorcelled": ["charmed", "magically manipulated"],
                    "not fully corrupted": ["influenced but not corrupted", "controlled rather than corrupted"],
                },
                "target_entity_names": ["Commander Thalia Ashenvale", "The Wolf"],
                "target_attributes": ["status", "loyalty_or_alignment_context"],
                "surface": "vertical_slice",
                "tier": "must_pass",
            },
            {
                "question": "After the chamber fight, what are the main branch paths that still converge on the sewers?",
                "expected_answer_summary": "Chasing the Wolf, covert operations, or helping Torbin all eventually lead players to sewer entrances and ritual clues.",
                "must_hit_tokens": ["chase", "covert ops", "torbin", "sewers"],
                "stale_tokens": ["single linear path", "no sewer link"],
                "update_signal_tokens": ["branch", "converge", "ritual clues"],
                "semantic_equivalences": {
                    "covert ops": ["covert operations", "surgical raids"],
                    "converge": ["all paths lead", "eventual convergence"],
                },
                "target_entity_names": ["The Wolf", "Torbin"],
                "target_attributes": ["event_sequence", "goals"],
                "surface": "vertical_slice",
                "tier": "should_pass",
            },
        ],
        "The Emergency Council Meeting.md": [
            {
                "question": "What strategy does the Wizards' College propose during the emergency meeting, and what is the key tradeoff?",
                "expected_answer_summary": "They propose arcane lockdown wards for detection and containment, but at the cost of citywide disruption, panic risk, and festival cancellation.",
                "must_hit_tokens": ["wizards' college", "arcane lockdown", "wards", "tradeoff"],
                "stale_tokens": ["no magical proposal", "cost-free solution"],
                "update_signal_tokens": ["detection", "restrictions", "festival"],
                "semantic_equivalences": {
                    "arcane lockdown": ["magical lockdown", "ward lockdown"],
                    "tradeoff": ["drawback", "cost"],
                },
                "target_entity_names": ["Headmaster Tinkerbright", "Wizards' College"],
                "target_attributes": ["goals", "strategy"],
                "surface": "core_extraction",
                "tier": "must_pass",
            },
            {
                "question": "How does Thalia's proposed guard sweep become a hidden failure mode?",
                "expected_answer_summary": "Because Thalia is under the Wolf's influence, guard strike teams can be redirected to wrong locations, delaying response and enabling summoning.",
                "must_hit_tokens": ["thalia", "wolf influence", "wrong locations", "delay"],
                "stale_tokens": ["thalia fully reliable", "no internal sabotage"],
                "update_signal_tokens": ["hidden failure", "manipulation", "misdirection"],
                "semantic_equivalences": {
                    "wolf influence": ["ensorcelled by the wolf", "wolf manipulation"],
                    "wrong locations": ["misdirected strike teams", "sent to false targets"],
                },
                "target_entity_names": ["Commander Thalia Ashenvale", "The Wolf"],
                "target_attributes": ["status", "event_sequence"],
                "surface": "vertical_slice",
                "tier": "must_pass",
            },
            {
                "question": "Which council alignments emerge around purification, arming citizens, and covert operations?",
                "expected_answer_summary": "Wizards and agriculture align on purification pressure, while goblin/undercity factions can align with Torrin and Rurik; Barin aligns with covert actions.",
                "must_hit_tokens": ["wizards and agriculture aligned", "goblins", "torrin", "rurik", "barin"],
                "stale_tokens": ["all factions isolated", "no cross-faction alignment"],
                "update_signal_tokens": ["aligned", "coalition", "proposal blocs"],
                "semantic_equivalences": {
                    "aligned": ["coalition", "voting bloc"],
                },
                "target_entity_names": ["Merril Tealeaf", "Torrin Flamescale", "Rurik Stonehammer", "Barin Coppergleam", "Grobnok"],
                "target_attributes": ["faction", "goals"],
                "surface": "core_extraction",
                "tier": "should_pass",
            },
            {
                "question": "What time-pressure mechanic drives urgency during emergency council deliberation?",
                "expected_answer_summary": "Each discussion round consumes in-game time and advances a countdown roll toward the kaiju summoning trigger.",
                "must_hit_tokens": ["time pressure", "discussion rounds", "countdown", "kaiju summoning"],
                "stale_tokens": ["unlimited deliberation", "no countdown"],
                "update_signal_tokens": ["d4", "d6", "ticks down"],
                "semantic_equivalences": {
                    "countdown": ["timer", "tick-down"],
                },
                "target_entity_names": ["City Council", "Maelthor"],
                "target_attributes": ["event_sequence", "ritual"],
                "surface": "vertical_slice",
                "tier": "must_pass",
            },
        ],
        "The City Council.md": [
            {
                "question": "Who chairs Mirathorn's council, and how is her leadership style described?",
                "expected_answer_summary": "Mayor Elara Swiftwind chairs the council and is characterized as diplomatic, charismatic, and focused on unity and stability.",
                "must_hit_tokens": ["elara swiftwind", "mayor", "chairs council", "diplomatic"],
                "stale_tokens": ["anonymous leadership", "military dictatorship"],
                "update_signal_tokens": ["unity", "prosperity", "order"],
                "semantic_equivalences": {
                    "diplomatic": ["charismatic leader", "political mediator"],
                },
                "target_entity_names": ["Mayor Elara Swiftwind", "City Council"],
                "target_attributes": ["rank_or_title", "personality"],
                "surface": "core_extraction",
                "tier": "must_pass",
            },
            {
                "question": "Which council member represents arcane response, and what is his position on cult corruption?",
                "expected_answer_summary": "Headmaster Tinkerbright represents arcane interests and supports deploying wizard resources to detect and counter corruption.",
                "must_hit_tokens": ["headmaster tinkerbright", "wizard's college", "detect", "counter corruption"],
                "stale_tokens": ["arcane neutrality", "no magic response"],
                "update_signal_tokens": ["arcane resources", "dark magic concern"],
                "semantic_equivalences": {
                    "counter corruption": ["counteract cult influence", "oppose dark magic spread"],
                },
                "target_entity_names": ["Headmaster Tinkerbright", "Wizards' College"],
                "target_attributes": ["rank_or_title", "goals"],
                "surface": "core_extraction",
                "tier": "must_pass",
            },
            {
                "question": "How is Thalia's public duty in conflict with her hidden manipulation by the Wolf?",
                "expected_answer_summary": "She is duty-bound and protective as guard commander, but ensorcelment by the Wolf biases her against recognizing guard corruption.",
                "must_hit_tokens": ["thalia", "commander of the guard", "ensorcelled", "overlook corruption"],
                "stale_tokens": ["thalia fully impartial", "no manipulation"],
                "update_signal_tokens": ["hidden influence", "guard corruption"],
                "semantic_equivalences": {
                    "overlook corruption": ["dismiss accusations", "fails to detect corruption"],
                },
                "target_entity_names": ["Commander Thalia Ashenvale", "The Wolf"],
                "target_attributes": ["rank_or_title", "status"],
                "surface": "vertical_slice",
                "tier": "must_pass",
            },
            {
                "question": "Which roles do Merril, Torrin, and Rurik hold in city governance?",
                "expected_answer_summary": "Merril leads agriculture/food interests, Torrin represents guild crafts, and Rurik represents infrastructure and city planning.",
                "must_hit_tokens": ["merril", "agricultural union", "torrin", "guilds", "rurik", "infrastructure"],
                "stale_tokens": ["roles unknown", "all three in same role"],
                "update_signal_tokens": ["representative", "city governance"],
                "semantic_equivalences": {
                    "agricultural union": ["agriculture and food production"],
                    "guilds": ["craft guilds"],
                },
                "target_entity_names": ["Merril Tealeaf", "Torrin Flamescale", "Rurik Stonehammer"],
                "target_attributes": ["rank_or_title", "faction"],
                "surface": "core_extraction",
                "tier": "must_pass",
            },
        ],
        "Longmont Campaign General Notes.md": [
            {
                "question": "What does the Longmont campaign note establish about the Shepherds' ideology and patron?",
                "expected_answer_summary": "The Shepherds follow Maelthor and frame atrocities as ritual sacrifices for ascension, tied to human supremacy and otherworldly power.",
                "must_hit_tokens": ["shepherds", "maelthor", "ritual sacrifices", "ascension"],
                "stale_tokens": ["purely political gang", "no patron"],
                "update_signal_tokens": ["cult beliefs", "human supremacy", "resurrection"],
                "semantic_equivalences": {
                    "ritual sacrifices": ["sacrificial burnings", "ritual violence"],
                },
                "target_entity_names": ["The Shepherds", "Maelthor"],
                "target_attributes": ["beliefs", "goals"],
                "surface": "core_extraction",
                "tier": "must_pass",
            },
            {
                "question": "How does twisted meat function as a corruption vector in campaign-layer notes?",
                "expected_answer_summary": "Twisted meat is distributed covertly through markets, producing dreams, behavioral changes, and eventual cult recruitment.",
                "must_hit_tokens": ["twisted meat", "distributed", "dreams", "behavioral changes", "recruitment"],
                "stale_tokens": ["direct military invasion only", "no food corruption"],
                "update_signal_tokens": ["tainted food", "transformation over time"],
                "semantic_equivalences": {
                    "behavioral changes": ["aggression", "disconnected from reality"],
                    "recruitment": ["inducted into cult ranks"],
                },
                "target_entity_names": ["The Shepherds"],
                "target_attributes": ["methods", "event_sequence"],
                "surface": "core_extraction",
                "tier": "must_pass",
            },
            {
                "question": "What dual role does Commander Elric Vane play in the campaign notes?",
                "expected_answer_summary": "Elric Vane is both a tactical commander and a cult priest coordinating rituals and spread operations.",
                "must_hit_tokens": ["elric vane", "dual leadership", "tactical leader", "high priest"],
                "stale_tokens": ["single civilian role", "unrelated to rituals"],
                "update_signal_tokens": ["secret meetings", "inner circle", "ritual oversight"],
                "semantic_equivalences": {
                    "high priest": ["cult priest", "ritual authority"],
                },
                "target_entity_names": ["Commander Elric Vane", "The Shepherds"],
                "target_attributes": ["rank_or_title", "goals"],
                "surface": "vertical_slice",
                "tier": "should_pass",
            },
            {
                "question": "How should a GM reconcile world-canon council politics with campaign-layer cult operations in Longmont?",
                "expected_answer_summary": "World-canon defines institutional roles, while campaign notes overlay evolving cult methods, actor corruption, and session-specific escalation.",
                "must_hit_tokens": ["world canon", "campaign layer", "overlay", "institutional roles", "cult operations"],
                "stale_tokens": ["layers are identical", "no campaign-specific state"],
                "update_signal_tokens": ["session state", "observed updates", "layer separation"],
                "semantic_equivalences": {
                    "overlay": ["applies on top", "layered on top"],
                    "layer separation": ["world vs campaign distinction"],
                },
                "target_entity_names": ["City Council", "The Shepherds", "The Wolf"],
                "target_attributes": ["governance", "event_sequence", "status"],
                "surface": "vertical_slice",
                "tier": "must_pass",
            },
        ],
    }


def generate_candidates(
    top_records: list[dict[str, Any]],
    entities: list[EntityRecord],
) -> list[dict[str, Any]]:
    by_name = _question_templates()
    candidates: list[dict[str, Any]] = []
    for record in top_records:
        filename = Path(record["path"]).name
        rows = by_name.get(filename, [])
        for idx, row in enumerate(rows[:QUESTIONS_PER_DOC], start=1):
            target_names = row["target_entity_names"]
            target_ids, unresolved_names = _resolve_entity_ids(target_names, entities)
            question_id = f"q_{_slug(filename.replace('.md', ''))}_{idx}"
            candidates.append(
                {
                    "id": question_id,
                    "document_source": record["path"],
                    "document_title": record["title"],
                    "question": row["question"],
                    "expected_answer_summary": row["expected_answer_summary"],
                    "must_hit_tokens": row["must_hit_tokens"],
                    "stale_tokens": row["stale_tokens"],
                    "update_signal_tokens": row["update_signal_tokens"],
                    "semantic_equivalences": row["semantic_equivalences"],
                    "target_entities": target_ids,
                    "target_entity_names_requested": target_names,
                    "unresolved_target_entity_names": unresolved_names,
                    "target_attributes": row["target_attributes"],
                    "surface": row["surface"],
                    "tier": row["tier"],
                }
            )
    return candidates


def _fact_stub(fact: dict[str, Any]) -> dict[str, Any]:
    value = fact.get("value", {})
    return {
        "fact_id": fact.get("fact_id"),
        "subject_entity_id": fact.get("subject_entity_id"),
        "attribute": fact.get("attribute"),
        "value_label": value.get("label"),
        "truth_state": fact.get("truth_state"),
    }


def validate_candidates(
    candidates: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_entity_attr: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for fact in facts:
        key = (str(fact.get("subject_entity_id", "")), str(fact.get("attribute", "")))
        by_entity_attr.setdefault(key, []).append(fact)

    validated: list[dict[str, Any]] = []
    for candidate in candidates:
        target_entities = candidate["target_entities"]
        target_attributes = candidate["target_attributes"]
        matched_pairs = 0
        total_pairs = len(target_entities) * len(target_attributes)
        coverage_details: list[dict[str, Any]] = []
        closest_match: list[dict[str, Any]] = []

        for entity_id in target_entities:
            for attribute in target_attributes:
                pair_facts = by_entity_attr.get((entity_id, attribute), [])
                if pair_facts:
                    matched_pairs += 1
                coverage_details.append(
                    {
                        "subject_entity_id": entity_id,
                        "attribute": attribute,
                        "fact_count": len(pair_facts),
                    }
                )
                for fact in pair_facts[:2]:
                    closest_match.append(_fact_stub(fact))

        if total_pairs == 0 or matched_pairs == 0:
            status = "unanswerable"
        elif matched_pairs < total_pairs:
            status = "partially_answerable"
        else:
            status = "answerable"

        row = dict(candidate)
        row["coverage_status"] = status
        row["coverage_match_ratio"] = 0.0 if total_pairs == 0 else matched_pairs / total_pairs
        row["coverage_pair_totals"] = {
            "matched_pairs": matched_pairs,
            "total_pairs": total_pairs,
        }
        row["coverage_details"] = coverage_details
        row["closest_match_facts"] = closest_match[:6]
        validated.append(row)
    return validated


def _select_sample(validated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_status: dict[str, list[dict[str, Any]]] = {
        "answerable": [],
        "partially_answerable": [],
        "unanswerable": [],
    }
    for row in validated:
        by_status[row["coverage_status"]].append(row)

    sample: list[dict[str, Any]] = []
    # Keep a deliberate mix in sample order.
    for status in ("answerable", "partially_answerable", "unanswerable"):
        sample.extend(by_status[status][:3])

    if len(sample) < SAMPLE_LIMIT:
        for row in validated:
            if row in sample:
                continue
            sample.append(row)
            if len(sample) >= SAMPLE_LIMIT:
                break
    return sample[:SAMPLE_LIMIT]


def _write_sample_review(sample: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase 6 Sample Review Batch",
        "",
        "First-pass candidate questions for editorial accept/reject/revise decisions.",
        "",
    ]
    for idx, row in enumerate(sample, start=1):
        lines.append(
            f"## {idx}. {row['id']} ({row['coverage_status']}, preflight: {row['preflight_support_status']})"
        )
        lines.append(f"- source: `{row['document_source']}`")
        lines.append(f"- question: {row['question']}")
        lines.append(f"- expected_answer_summary: {row['expected_answer_summary']}")
        lines.append("- must_hit_tokens: " + ", ".join(row["must_hit_tokens"]))
        lines.append("- stale_tokens: " + ", ".join(row["stale_tokens"]))
        lines.append(
            "- target_entities: "
            + (", ".join(row["target_entities"]) if row["target_entities"] else "(none resolved)")
        )
        lines.append("- target_attributes: " + ", ".join(row["target_attributes"]))
        lines.append(
            "- coverage: "
            + f"{row['coverage_pair_totals']['matched_pairs']}/{row['coverage_pair_totals']['total_pairs']}"
        )
        lines.append(f"- preflight_support_status: {row['preflight_support_status']}")
        if row["preflight_support_details"]:
            lines.append("- preflight_support_details:")
            for support in row["preflight_support_details"]:
                lines.append(
                    "  - "
                    + f"{support['requested_name']} -> {support['status']} "
                    + f"(best_fuzzy={support['best_fuzzy_score']})"
                )
        if row["unresolved_target_entity_names"]:
            lines.append(
                "- unresolved_target_entity_names: "
                + ", ".join(row["unresolved_target_entity_names"])
            )
        if row["closest_match_facts"]:
            lines.append("- closest_match_facts:")
            for fact in row["closest_match_facts"][:3]:
                lines.append(
                    f"  - {fact['subject_entity_id']}::{fact['attribute']} -> {fact['value_label']}"
                )
        lines.append("")

    SAMPLE_REVIEW_PATH.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def run() -> dict[str, Any]:
    if not CORPUS_ROOT.exists():
        raise FileNotFoundError(f"Corpus root missing: {CORPUS_ROOT}")
    if not STORE_DIR.exists():
        raise FileNotFoundError(f"Store dir missing: {STORE_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest()
    top_records = []
    explicit_targets = {
        "The Council Room.md",
        "Battle with The Wolf and Aftermath.md",
        "The Emergency Council Meeting.md",
        "The City Council.md",
        "Longmont Campaign General Notes.md",
    }
    for record in manifest:
        if Path(record["path"]).name in explicit_targets:
            top_records.append(record)
    top_records = top_records[:TOP_DOC_LIMIT]

    entities = _entity_records()
    facts = _read_json(STORE_DIR / "facts.json")
    candidates = generate_candidates(top_records=top_records, entities=entities)
    preflight_checked = preflight_check_candidates(candidates=candidates, entities=entities)
    validated = validate_candidates(candidates=preflight_checked, facts=facts)
    sample = _select_sample(validated)

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    CANDIDATES_PATH.write_text(json.dumps(validated, indent=2), encoding="utf-8")
    _write_sample_review(sample)

    status_counts = Counter(row["coverage_status"] for row in validated)
    preflight_counts = Counter(row["preflight_support_status"] for row in validated)
    summary = {
        "corpus_documents_profiled": len(manifest),
        "priority_documents_used": [row["path"] for row in top_records],
        "candidate_questions_generated": len(validated),
        "sample_questions_for_review": len(sample),
        "coverage_status_counts": dict(status_counts),
        "preflight_support_status_counts": dict(preflight_counts),
        "artifacts": {
            "manifest": str(MANIFEST_PATH.relative_to(PROJECT_ROOT)),
            "candidates": str(CANDIDATES_PATH.relative_to(PROJECT_ROOT)),
            "sample_review": str(SAMPLE_REVIEW_PATH.relative_to(PROJECT_ROOT)),
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    out = run()
    print(json.dumps(out, indent=2))
