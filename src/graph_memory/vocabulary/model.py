from __future__ import annotations

from dataclasses import dataclass, fields, field
from typing import Any, ClassVar, Literal, Mapping, Self, TypeVar, get_args, get_origin, get_type_hints

SourceDomain = Literal[
    "recap",
    "worldbuilding",
    "npc_note",
    "location_note",
    "faction_note",
    "item_note",
    "statblock",
    "session_memory",
    "manual_seed",
    "future_artifact",
    "prior_graph_observation",
]
"""Vocabulary source-domain contract.

This intentionally mirrors the contextual-vocabulary design doc's initial
source-domain vocabulary. It overlaps with ``graph_memory.evidence.source_domain``
while adding ``prior_graph_observation`` for vocabulary artifacts; the evidence
module remains unchanged for existing graph-memory behavior.
"""

EntityKind = Literal[
    "actor",
    "place",
    "collective",
    "object",
    "thread",
    "phenomenon",
    "combat_encounter",
    "social_encounter",
    "session_beat",
    "unknown",
]

Status = Literal[
    "observed",
    "candidate",
    "accepted",
    "rejected",
    "needs_review",
    "do_not_merge",
    "deprecated",
    "superseded",
]

AuthorityLabel = Literal[
    "world_reference",
    "canon_play",
    "campaign_dossier",
    "statblock_reference",
    "derived_memory",
    "prior_graph_observation",
    "inferred_from_recap",
    "llm_candidate",
    "gm_reviewed",
    "manual_seed",
]

RiskFlag = Literal[
    "cross_type",
    "eponymous_group",
    "place_vs_polity",
    "person_vs_faction",
    "single_shared_token",
    "source_span_only",
    "gold_only_support",
    "conflicting_kind_hint",
    "ambiguous_place_or_leadership_body",
    "combat_encounter_vs_creature_group",
]

T = TypeVar("T", bound="_VocabularyModel")


def _require_non_empty(value: str | None, field_name: str) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")


def _validate_confidence(value: float | None, field_name: str = "confidence") -> None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")


def _dedupe_preserving_order(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _to_payload(value: Any) -> Any:
    if isinstance(value, _VocabularyModel):
        return value.to_dict()
    if isinstance(value, list):
        return [_to_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_payload(item) for key, item in value.items()}
    return value


def _from_payload(annotation: Any, value: Any) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        if value not in args:
            raise ValueError(f"expected one of {args!r}, got {value!r}")
        return value
    if origin is list:
        item_type = args[0] if args else Any
        return [_from_payload(item_type, item) for item in value]
    if origin is dict:
        value_type = args[1] if len(args) > 1 else Any
        return {key: _from_payload(value_type, item) for key, item in value.items()}
    if origin in (type(None),):
        return value
    if origin is not None and type(None) in args:
        non_none = [arg for arg in args if arg is not type(None)]
        if value is None:
            return None
        if len(non_none) == 1:
            return _from_payload(non_none[0], value)
    if isinstance(annotation, type) and issubclass(annotation, _VocabularyModel):
        return annotation.from_dict(value)
    return value


@dataclass(slots=True)
class _VocabularyModel:
    _field_types: ClassVar[dict[str, Any]]

    def __post_init__(self) -> None:
        self._validate_literals()

    def _validate_literals(self) -> None:
        for field_name, annotation in get_type_hints(type(self)).items():
            if field_name.startswith("_"):
                continue
            value = getattr(self, field_name)
            if value is None:
                continue
            _from_payload(annotation, _to_payload(value))

    def to_dict(self) -> dict[str, Any]:
        return {item.name: _to_payload(getattr(self, item.name)) for item in fields(self)}

    @classmethod
    def from_dict(cls: type[T], payload: Mapping[str, Any]) -> T:
        known = {item.name for item in fields(cls)}
        unknown = set(payload) - known
        if unknown:
            raise ValueError(f"unknown fields for {cls.__name__}: {sorted(unknown)}")
        hints = get_type_hints(cls)
        kwargs = {name: _from_payload(hints[name], payload[name]) for name in payload}
        return cls(**kwargs)


@dataclass(slots=True)
class EvidenceRef(_VocabularyModel):
    source_artifact_id: str
    source_span_ref_id: str | None = None
    quote: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_non_empty(self.source_artifact_id, "source_artifact_id")
        if self.line_start is not None and self.line_end is not None and self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")
        _validate_confidence(self.confidence)


@dataclass(slots=True)
class SourceArtifactRef(_VocabularyModel):
    source_artifact_id: str
    source_domain: SourceDomain
    scope: str
    campaign_id: str | None = None
    world_id: str | None = None
    session_id: str | None = None
    uri: str | None = None
    content_hash: str | None = None
    document_class: str | None = None
    subject_class: str | None = None
    authority: AuthorityLabel | None = None
    indexed_at: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_non_empty(self.source_artifact_id, "source_artifact_id")
        _require_non_empty(self.scope, "scope")
        if self.scope != "global" and not (self.campaign_id or self.world_id):
            raise ValueError("campaign_id or world_id is required unless scope is global")


@dataclass(slots=True)
class LexicalObservation(_VocabularyModel):
    observation_id: str
    source_artifact_id: str
    surface_text: str
    normalized_text: str
    observed_kind_hint: EntityKind = "unknown"
    source_span_ref_id: str | None = None
    context_window_hash: str | None = None
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    extraction_method: str | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_non_empty(self.observation_id, "observation_id")
        _require_non_empty(self.source_artifact_id, "source_artifact_id")
        _require_non_empty(self.surface_text, "surface_text")
        _require_non_empty(self.normalized_text, "normalized_text")
        _validate_confidence(self.confidence)


@dataclass(slots=True)
class VocabularyEntry(_VocabularyModel):
    vocab_id: str
    canonical_label: str
    entity_kind: EntityKind
    scope: str
    campaign_id: str | None = None
    world_id: str | None = None
    entity_kind_confidence: float | None = None
    global_node_id: str | None = None
    candidate_global_node_ids: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    candidate_aliases: list[str] = field(default_factory=list)
    negative_aliases: list[str] = field(default_factory=list)
    do_not_merge_with: list[str] = field(default_factory=list)
    related_entries: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    first_seen_session: str | None = None
    last_seen_session: str | None = None
    status: Status = "candidate"
    authority: AuthorityLabel | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_non_empty(self.vocab_id, "vocab_id")
        _require_non_empty(self.canonical_label, "canonical_label")
        _require_non_empty(self.scope, "scope")
        if self.global_node_id and self.global_node_id in self.candidate_global_node_ids:
            raise ValueError("global_node_id must not appear in candidate_global_node_ids")
        self.candidate_global_node_ids = _dedupe_preserving_order(self.candidate_global_node_ids)
        canonical = self.canonical_label.strip()
        self.aliases = [alias for alias in _dedupe_preserving_order(self.aliases) if alias.strip() != canonical]
        self.candidate_aliases = _dedupe_preserving_order(self.candidate_aliases)
        self.negative_aliases = _dedupe_preserving_order(self.negative_aliases)
        self.do_not_merge_with = _dedupe_preserving_order(self.do_not_merge_with)
        self.related_entries = _dedupe_preserving_order(self.related_entries)
        self.source_refs = _dedupe_preserving_order(self.source_refs)
        _validate_confidence(self.entity_kind_confidence, "entity_kind_confidence")
        if self.scope == "campaign" and not self.campaign_id:
            raise ValueError("campaign_id is required for campaign scope")
        if self.scope == "world" and not self.world_id:
            raise ValueError("world_id is required for world scope")


@dataclass(slots=True)
class AliasCandidate(_VocabularyModel):
    alias_candidate_id: str
    left_surface: str
    right_surface: str
    left_vocab_id: str | None = None
    right_vocab_id: str | None = None
    candidate_cluster_id: str | None = None
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    supporting_sources: list[str] = field(default_factory=list)
    contradicting_sources: list[str] = field(default_factory=list)
    confidence: float | None = None
    status: Status = "candidate"
    reason: str | None = None
    risk_flags: list[RiskFlag] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_non_empty(self.alias_candidate_id, "alias_candidate_id")
        _require_non_empty(self.left_surface, "left_surface")
        _require_non_empty(self.right_surface, "right_surface")
        if self.left_surface.strip() == self.right_surface.strip():
            raise ValueError("left_surface and right_surface must differ")
        _validate_confidence(self.confidence)
        self.supporting_sources = _dedupe_preserving_order(self.supporting_sources)
        self.contradicting_sources = _dedupe_preserving_order(self.contradicting_sources)
        self.risk_flags = _dedupe_preserving_order(self.risk_flags)


@dataclass(slots=True)
class DoNotMergeDecision(_VocabularyModel):
    decision_id: str
    left_vocab_id: str
    right_vocab_id: str
    status: Status = "candidate"
    source: str | None = None
    reason: str | None = None
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    created_by: str | None = None
    reviewed_by: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_non_empty(self.decision_id, "decision_id")
        _require_non_empty(self.left_vocab_id, "left_vocab_id")
        _require_non_empty(self.right_vocab_id, "right_vocab_id")
        if self.left_vocab_id == self.right_vocab_id:
            raise ValueError("left_vocab_id and right_vocab_id must differ")


@dataclass(slots=True)
class ContainmentHint(_VocabularyModel):
    hint_id: str
    child_label: str
    parent_label: str
    child_vocab_id: str | None = None
    parent_vocab_id: str | None = None
    relationship_type: str = "contained_in"
    confidence: float | None = None
    status: Status = "candidate"
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    authority: AuthorityLabel | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_non_empty(self.hint_id, "hint_id")
        _require_non_empty(self.child_label, "child_label")
        _require_non_empty(self.parent_label, "parent_label")
        if self.child_label.strip() == self.parent_label.strip():
            raise ValueError("child_label and parent_label must differ")
        _validate_confidence(self.confidence)


@dataclass(slots=True)
class ContextVocabularyPacket(_VocabularyModel):
    packet_id: str
    scope: str
    world_entry_refs: list[str] = field(default_factory=list)
    campaign_entry_refs: list[str] = field(default_factory=list)
    known_names: list[str] = field(default_factory=list)
    alias_hints: list[AliasCandidate] = field(default_factory=list)
    candidate_alias_hints: list[AliasCandidate] = field(default_factory=list)
    do_not_merge_hints: list[DoNotMergeDecision] = field(default_factory=list)
    containment_hints: list[ContainmentHint] = field(default_factory=list)
    type_hints: dict[str, EntityKind] = field(default_factory=dict)
    predicate_hints: dict[str, list[str]] = field(default_factory=dict)
    combat_encounter_hints: list[str] = field(default_factory=list)
    budget_policy: dict[str, Any] = field(default_factory=dict)
    generated_at: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_non_empty(self.packet_id, "packet_id")
        _require_non_empty(self.scope, "scope")
        self.world_entry_refs = _dedupe_preserving_order(self.world_entry_refs)
        self.campaign_entry_refs = _dedupe_preserving_order(self.campaign_entry_refs)
        self.known_names = _dedupe_preserving_order(self.known_names)
        self.combat_encounter_hints = _dedupe_preserving_order(self.combat_encounter_hints)
        self.predicate_hints = {key: _dedupe_preserving_order(values) for key, values in self.predicate_hints.items()}
