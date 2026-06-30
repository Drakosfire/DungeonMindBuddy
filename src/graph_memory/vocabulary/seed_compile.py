from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
from typing import Any, Iterable, Mapping

from .lexical_observation import normalize_observed_text
from .model import EntityKind, EvidenceRef, LexicalObservation, SourceArtifactRef, SourceDomain, VocabularyEntry

COMPILE_METHOD = "deterministic_vocabulary_seed_compile_v1"


@dataclass(slots=True)
class VocabularySeedScopePolicy:
    default_scope: str = "campaign"
    campaign_id: str | None = None
    world_id: str | None = None
    world_source_domains: tuple[SourceDomain, ...] = ("worldbuilding", "manual_seed")
    campaign_source_domains: tuple[SourceDomain, ...] = (
        "recap",
        "session_memory",
        "npc_note",
        "location_note",
        "faction_note",
        "item_note",
        "statblock",
    )

    def validate(self) -> None:
        if self.default_scope not in {"world", "campaign"}:
            raise ValueError("default_scope must be either 'world' or 'campaign'")


@dataclass(slots=True)
class VocabularySeedCompileResult:
    world_entries: list[VocabularyEntry]
    campaign_entries: list[VocabularyEntry]
    diagnostics: dict[str, Any] = field(default_factory=dict)


def canonical_label_from_observations(observations: Iterable[LexicalObservation]) -> str:
    ordered = list(observations)
    if not ordered:
        return ""
    counts: Counter[str] = Counter()
    first_index: dict[str, int] = {}
    for index, observation in enumerate(ordered):
        surface = observation.surface_text.strip()
        if not surface:
            continue
        counts[surface] += 1
        first_index.setdefault(surface, index)
    if not counts:
        return ordered[0].surface_text.strip()
    return sorted(counts, key=lambda surface: (-counts[surface], first_index[surface], surface))[0]


def make_vocab_seed_id(
    scope: str,
    normalized_text: str,
    entity_kind: EntityKind,
    campaign_id: str | None,
    world_id: str | None,
) -> str:
    payload = "\n".join([scope, campaign_id or "", world_id or "", normalized_text, entity_kind])
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"vocab:seed:{digest}"


def infer_seed_scope(
    observation: LexicalObservation,
    source_artifacts: Mapping[str, SourceArtifactRef] | None,
    policy: VocabularySeedScopePolicy,
) -> str:
    source_artifact = (source_artifacts or {}).get(observation.source_artifact_id)
    if source_artifact is not None:
        if source_artifact.source_domain in policy.world_source_domains:
            return "world"
        if source_artifact.source_domain in policy.campaign_source_domains:
            return "campaign"
        if source_artifact.scope in {"world", "campaign"}:
            return source_artifact.scope
    return policy.default_scope


def _unique_source_refs(observations: list[LexicalObservation]) -> list[str]:
    seen: set[str] = set()
    refs: list[str] = []
    for observation in observations:
        if observation.source_artifact_id not in seen:
            seen.add(observation.source_artifact_id)
            refs.append(observation.source_artifact_id)
    return refs


def _dedupe_evidence_refs(observations: list[LexicalObservation]) -> list[EvidenceRef]:
    seen: set[tuple[str, str | None, str | None]] = set()
    evidence_refs: list[EvidenceRef] = []
    for observation in observations:
        for evidence_ref in observation.evidence_refs:
            key = (evidence_ref.source_artifact_id, evidence_ref.source_span_ref_id, evidence_ref.quote)
            if key in seen:
                continue
            seen.add(key)
            evidence_refs.append(evidence_ref)
    return evidence_refs


def _source_artifact_values(
    observations: list[LexicalObservation], source_artifacts: Mapping[str, SourceArtifactRef], field_name: str
) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for observation in observations:
        source_artifact = source_artifacts.get(observation.source_artifact_id)
        value = getattr(source_artifact, field_name) if source_artifact is not None else None
        if value and value not in seen:
            seen.add(value)
            values.append(value)
    return values


def _confidence(observations: list[LexicalObservation]) -> float:
    values = [observation.confidence for observation in observations if observation.confidence is not None]
    if not values:
        return 0.55
    return round(sum(values) / len(values), 3)


def _build_entry(
    scope: str,
    normalized_text: str,
    entity_kind: EntityKind,
    observations: list[LexicalObservation],
    source_artifacts: Mapping[str, SourceArtifactRef],
    policy: VocabularySeedScopePolicy,
) -> VocabularyEntry:
    campaign_ids = _source_artifact_values(observations, source_artifacts, "campaign_id")
    world_ids = _source_artifact_values(observations, source_artifacts, "world_id")
    session_ids = sorted(_source_artifact_values(observations, source_artifacts, "session_id"))

    campaign_id = policy.campaign_id if scope == "campaign" and policy.campaign_id else (campaign_ids[0] if campaign_ids else None)
    world_id = world_ids[0] if world_ids else policy.world_id

    return VocabularyEntry(
        vocab_id=make_vocab_seed_id(scope, normalized_text, entity_kind, campaign_id, world_id),
        canonical_label=canonical_label_from_observations(observations),
        entity_kind=entity_kind,
        scope=scope,
        campaign_id=campaign_id,
        world_id=world_id,
        entity_kind_confidence=_confidence(observations),
        global_node_id=None,
        candidate_global_node_ids=[],
        aliases=[],
        candidate_aliases=[],
        negative_aliases=[],
        do_not_merge_with=[],
        source_refs=_unique_source_refs(observations),
        evidence_refs=_dedupe_evidence_refs(observations),
        first_seen_session=session_ids[0] if session_ids else None,
        last_seen_session=session_ids[-1] if session_ids else None,
        status="candidate",
        authority="derived_memory",
        notes="Compiled from deterministic lexical observations; not reviewed canon.",
    )


def compile_vocabulary_seed_entries(
    observations: Iterable[LexicalObservation],
    *,
    source_artifacts: Iterable[SourceArtifactRef] | None = None,
    policy: VocabularySeedScopePolicy | None = None,
    compile_method: str = COMPILE_METHOD,
) -> VocabularySeedCompileResult:
    policy = policy or VocabularySeedScopePolicy()
    policy.validate()
    source_artifact_lookup = {item.source_artifact_id: item for item in source_artifacts or []}

    ordered_observations = list(observations)
    groups: dict[tuple[str, str, EntityKind], list[LexicalObservation]] = {}
    skipped_observation_count = 0
    observation_artifact_counts: Counter[str] = Counter()

    for observation in ordered_observations:
        normalized = normalize_observed_text(observation.normalized_text or observation.surface_text)
        if not normalized:
            skipped_observation_count += 1
            continue
        scope = infer_seed_scope(observation, source_artifact_lookup, policy)
        groups.setdefault((scope, normalized, observation.observed_kind_hint), []).append(observation)
        observation_artifact_counts[observation.source_artifact_id] += 1

    entries: list[VocabularyEntry] = []
    for (scope, normalized, entity_kind), group_observations in groups.items():
        entries.append(_build_entry(scope, normalized, entity_kind, group_observations, source_artifact_lookup, policy))

    entries = sorted(entries, key=lambda entry: (entry.canonical_label.lower(), entry.entity_kind, entry.vocab_id))
    world_entries = [entry for entry in entries if entry.scope == "world"]
    campaign_entries = [entry for entry in entries if entry.scope == "campaign"]

    entry_kind_counts: Counter[str] = Counter(entry.entity_kind for entry in entries)
    scope_counts: Counter[str] = Counter(entry.scope for entry in entries)
    warnings: list[str] = []
    if not policy.campaign_id and not policy.world_id:
        warnings.append("policy has neither campaign_id nor world_id; scoped entries may be invalid without source artifact IDs")

    diagnostics = {
        "observation_count": len(ordered_observations),
        "compiled_entry_count": len(entries),
        "world_entry_count": len(world_entries),
        "campaign_entry_count": len(campaign_entries),
        "skipped_observation_count": skipped_observation_count,
        "scope_counts": dict(sorted(scope_counts.items())),
        "entity_kind_counts": dict(sorted(entry_kind_counts.items())),
        "source_artifact_counts": dict(sorted(observation_artifact_counts.items())),
        "warnings": warnings,
        "compile_method": compile_method,
    }
    return VocabularySeedCompileResult(world_entries=world_entries, campaign_entries=campaign_entries, diagnostics=diagnostics)


def seed_entries_to_artifact_payload(entries: Iterable[VocabularyEntry]) -> list[dict[str, Any]]:
    return [entry.to_dict() for entry in entries]
