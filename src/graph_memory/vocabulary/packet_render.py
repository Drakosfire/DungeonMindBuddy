from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import hashlib
from typing import Any, Iterable, Mapping, TypeVar

from .model import AliasCandidate, ContainmentHint, ContextVocabularyPacket, DoNotMergeDecision, EntityKind, VocabularyEntry

RENDER_METHOD = "deterministic_context_vocabulary_packet_render_v1"
T = TypeVar("T")


@dataclass(slots=True)
class ContextPacketBudgetPolicy:
    max_world_entry_refs: int = 24
    max_campaign_entry_refs: int = 36
    max_known_names: int = 48
    max_alias_hints: int = 12
    max_candidate_alias_hints: int = 12
    max_do_not_merge_hints: int = 16
    max_containment_hints: int = 16
    max_type_hints: int = 48
    max_predicate_hints: int = 48
    max_combat_encounter_hints: int = 12

    def validate(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if not isinstance(value, int):
                raise ValueError(f"{item.name} must be an integer")
            if value < 0:
                raise ValueError(f"{item.name} must be greater than or equal to 0")

    def to_dict(self, *, render_method: str = RENDER_METHOD) -> dict[str, Any]:
        payload = asdict(self)
        payload["render_method"] = render_method
        return payload


@dataclass(slots=True)
class ContextPacketRenderResult:
    packet: ContextVocabularyPacket
    diagnostics: dict[str, Any]


def _dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _sorted_entries(entries: Iterable[VocabularyEntry]) -> list[VocabularyEntry]:
    return sorted(entries, key=lambda entry: (entry.canonical_label.lower(), entry.entity_kind, entry.vocab_id))


def _trim(values: list[T], limit: int) -> tuple[list[T], int]:
    return values[:limit], max(0, len(values) - limit)


def _trimmed_counts(**counts: int) -> dict[str, int]:
    return {key: value for key, value in counts.items() if value > 0}


def _sort_alias_candidates(hints: Iterable[AliasCandidate]) -> list[AliasCandidate]:
    return sorted(hints, key=lambda hint: (hint.alias_candidate_id, hint.left_surface.lower(), hint.right_surface.lower()))


def _sort_do_not_merge(hints: Iterable[DoNotMergeDecision]) -> list[DoNotMergeDecision]:
    return sorted(hints, key=lambda hint: (hint.decision_id, hint.left_vocab_id, hint.right_vocab_id))


def _sort_containment(hints: Iterable[ContainmentHint]) -> list[ContainmentHint]:
    return sorted(hints, key=lambda hint: (hint.hint_id, hint.child_label.lower(), hint.parent_label.lower()))


def make_context_packet_id(
    scope: str,
    world_entries: Iterable[VocabularyEntry],
    campaign_entries: Iterable[VocabularyEntry],
    packet_seed: str | None = None,
) -> str:
    payload = "\n".join(
        [
            scope,
            packet_seed or "",
            *sorted(entry.vocab_id for entry in world_entries),
            *sorted(entry.vocab_id for entry in campaign_entries),
        ]
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"packet:vocab:{digest}"


def _known_names(world_entries: list[VocabularyEntry], campaign_entries: list[VocabularyEntry]) -> list[str]:
    return _dedupe_preserving_order(
        [entry.canonical_label for entry in world_entries] + [entry.canonical_label for entry in campaign_entries]
    )


def _entry_alias_groups(entries: list[VocabularyEntry]) -> dict[str, list[str]]:
    return {entry.canonical_label: list(entry.aliases) for entry in entries if entry.aliases}


def _candidate_entry_alias_groups(entries: list[VocabularyEntry]) -> dict[str, list[str]]:
    return {entry.canonical_label: list(entry.candidate_aliases) for entry in entries if entry.candidate_aliases}


def _entry_labels(entries: list[VocabularyEntry]) -> dict[str, str]:
    return {entry.vocab_id: entry.canonical_label for entry in entries}


def _entry_kinds(entries: list[VocabularyEntry]) -> dict[str, EntityKind]:
    return {entry.vocab_id: entry.entity_kind for entry in entries}


def _alias_count(groups: Mapping[str, list[str]]) -> int:
    return sum(len(values) for values in groups.values())


def _type_hints(entries: list[VocabularyEntry], limit: int) -> tuple[dict[str, EntityKind], int]:
    pairs = [(entry.canonical_label, entry.entity_kind) for entry in entries]
    trimmed, trimmed_count = _trim(pairs, limit)
    return dict(trimmed), trimmed_count


def _predicate_hints(
    supplied: Mapping[str, Iterable[str]] | None,
    allowed_labels: set[str],
    limit: int,
) -> tuple[dict[str, list[str]], int]:
    pairs: list[tuple[str, list[str]]] = []
    for label in sorted((supplied or {}).keys(), key=lambda value: value.lower()):
        if label not in allowed_labels:
            continue
        values = _dedupe_preserving_order(supplied[label])
        if values:
            pairs.append((label, values))
    trimmed, trimmed_count = _trim(pairs, limit)
    return dict(trimmed), trimmed_count


def render_context_vocabulary_packet(
    *,
    scope: str = "campaign",
    world_entries: Iterable[VocabularyEntry] = (),
    campaign_entries: Iterable[VocabularyEntry] = (),
    alias_hints: Iterable[AliasCandidate] = (),
    candidate_alias_hints: Iterable[AliasCandidate] = (),
    do_not_merge_hints: Iterable[DoNotMergeDecision] = (),
    containment_hints: Iterable[ContainmentHint] = (),
    predicate_hints: Mapping[str, Iterable[str]] | None = None,
    budget_policy: ContextPacketBudgetPolicy | None = None,
    packet_seed: str | None = None,
    render_method: str = RENDER_METHOD,
) -> ContextPacketRenderResult:
    if not scope.strip():
        raise ValueError("scope must be non-empty")
    policy = budget_policy or ContextPacketBudgetPolicy()
    policy.validate()

    sorted_world_entries = _sorted_entries(world_entries)
    sorted_campaign_entries = _sorted_entries(campaign_entries)
    retained_world_entries, trimmed_world = _trim(sorted_world_entries, policy.max_world_entry_refs)
    retained_campaign_entries, trimmed_campaign = _trim(sorted_campaign_entries, policy.max_campaign_entry_refs)
    retained_entries = retained_world_entries + retained_campaign_entries

    all_known_names = _known_names(retained_world_entries, retained_campaign_entries)
    known_names, trimmed_known_names = _trim(all_known_names, policy.max_known_names)
    type_hints, trimmed_type_hints = _type_hints(retained_entries, policy.max_type_hints)
    entry_aliases = _entry_alias_groups(retained_entries)
    candidate_entry_aliases = _candidate_entry_alias_groups(retained_entries)
    entry_labels = _entry_labels(retained_entries)
    entry_kinds = _entry_kinds(retained_entries)
    combat_hints, trimmed_combat_hints = _trim(
        [entry.canonical_label for entry in retained_entries if entry.entity_kind == "combat_encounter"],
        policy.max_combat_encounter_hints,
    )

    allowed_predicate_labels = set(known_names) | {entry.canonical_label for entry in retained_entries}
    scoped_predicate_hints, trimmed_predicate_hints = _predicate_hints(
        predicate_hints,
        allowed_predicate_labels,
        policy.max_predicate_hints,
    )

    retained_alias_hints, trimmed_alias_hints = _trim(_sort_alias_candidates(alias_hints), policy.max_alias_hints)
    retained_candidate_alias_hints, trimmed_candidate_alias_hints = _trim(
        _sort_alias_candidates(candidate_alias_hints), policy.max_candidate_alias_hints
    )
    retained_do_not_merge_hints, trimmed_do_not_merge_hints = _trim(
        _sort_do_not_merge(do_not_merge_hints), policy.max_do_not_merge_hints
    )
    retained_containment_hints, trimmed_containment_hints = _trim(
        _sort_containment(containment_hints), policy.max_containment_hints
    )

    packet_id = make_context_packet_id(scope, retained_world_entries, retained_campaign_entries, packet_seed)
    packet = ContextVocabularyPacket(
        packet_id=packet_id,
        scope=scope,
        world_entry_refs=[entry.vocab_id for entry in retained_world_entries],
        campaign_entry_refs=[entry.vocab_id for entry in retained_campaign_entries],
        known_names=known_names,
        entry_aliases=entry_aliases,
        candidate_entry_aliases=candidate_entry_aliases,
        entry_labels=entry_labels,
        entry_kinds=entry_kinds,
        alias_hints=retained_alias_hints,
        candidate_alias_hints=retained_candidate_alias_hints,
        do_not_merge_hints=retained_do_not_merge_hints,
        containment_hints=retained_containment_hints,
        type_hints=type_hints,
        predicate_hints=scoped_predicate_hints,
        combat_encounter_hints=combat_hints,
        budget_policy=policy.to_dict(render_method=render_method),
    )
    diagnostics = {
        "packet_id": packet_id,
        "scope": scope,
        "world_entry_count": len(retained_world_entries),
        "campaign_entry_count": len(retained_campaign_entries),
        "known_name_count": len(known_names),
        "entry_alias_count": _alias_count(entry_aliases),
        "candidate_entry_alias_count": _alias_count(candidate_entry_aliases),
        "alias_hint_count": len(retained_alias_hints),
        "candidate_alias_hint_count": len(retained_candidate_alias_hints),
        "do_not_merge_hint_count": len(retained_do_not_merge_hints),
        "containment_hint_count": len(retained_containment_hints),
        "type_hint_count": len(type_hints),
        "predicate_hint_count": len(scoped_predicate_hints),
        "combat_encounter_hint_count": len(combat_hints),
        "trimmed_counts": _trimmed_counts(
            world_entry_refs=trimmed_world,
            campaign_entry_refs=trimmed_campaign,
            known_names=trimmed_known_names,
            alias_hints=trimmed_alias_hints,
            candidate_alias_hints=trimmed_candidate_alias_hints,
            do_not_merge_hints=trimmed_do_not_merge_hints,
            containment_hints=trimmed_containment_hints,
            type_hints=trimmed_type_hints,
            predicate_hints=trimmed_predicate_hints,
            combat_encounter_hints=trimmed_combat_hints,
        ),
        "render_method": render_method,
    }
    return ContextPacketRenderResult(packet=packet, diagnostics=diagnostics)


def context_packet_to_artifact_payload(packet: ContextVocabularyPacket) -> dict[str, Any]:
    return packet.to_dict()
