"""Eldyrwild residual relationship semantic adjudication (characterization only).

This module turns the exact v3 ``RELATIONSHIP_PREDICATE = 59`` residual set into a
closed, source-grounded successor ledger. It does not publish vocabulary, mutate
the World Graph, or implement adoption.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_world_object_v3_vocabulary,
)

from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    _load_exact_buddy_revision,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v3 import (
    PredicateDisposition,
    _classify_edge_predicate_v3,
    _endpoint_dm_kinds,
    edge_has_reverse_direction_qualifier_v3,
    resolve_buddy_predicate_mapping_v3,
)

RELATIONSHIP_RESIDUAL_ADJUDICATION_SCHEMA = (
    "dmb_dungeonmind_relationship_residual_adjudication_v1"
)

ELDYRWILD_WORLD_ID = "eldyrwild"
ELDYRWILD_CAMPAIGN_ID = "longmont-c2"
ELDYRWILD_REVISION_ID = "rev:3413bf6f5044cf2680233f5e37c90dcf"
ELDYRWILD_PAYLOAD_SHA256 = (
    "346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa"
)

EXPECTED_RESIDUAL_COUNT = 59
EXPECTED_RESIDUAL_BY_PREDICATE: dict[str, int] = {
    "carries": 4,
    "carries_report_to": 1,
    "contains": 2,
    "controls_comms_with": 3,
    "defends_weakened_location": 1,
    "identified_as": 4,
    "leads": 2,
    "leads_to": 5,
    "located_in": 5,
    "member_of": 1,
    "mission_targets": 1,
    "objective_of": 2,
    "part_of": 4,
    "part_of_group": 1,
    "participates_in": 6,
    "present_at": 2,
    "reports_threat_in": 1,
    "routes_to": 1,
    "same_as": 5,
    "serves": 3,
    "threatens": 1,
    "travels_to": 2,
    "within": 2,
}

FORBIDDEN_CATCH_ALL_TERMS = frozenset(
    {
        "dnd5e:related_to",
        "related_to",
        "dnd5e:same_as",
        "same_as",
    }
)


class ResidualDisposition(str, Enum):
    EXISTING_TERM_ENDPOINT_EXTENSION_CANDIDATE = (
        "EXISTING_TERM_ENDPOINT_EXTENSION_CANDIDATE"
    )
    EXPLICIT_ADAPTER_CANDIDATE = "EXPLICIT_ADAPTER_CANDIDATE"
    NEW_PREDICATE_CANDIDATE = "NEW_PREDICATE_CANDIDATE"
    IDENTITY_NOT_RELATIONSHIP = "IDENTITY_NOT_RELATIONSHIP"
    SOURCE_CORRECTION_REQUIRED = "SOURCE_CORRECTION_REQUIRED"
    COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP = (
        "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP"
    )
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ReasonCode(str, Enum):
    IDENTITY_EQUIVALENCE = "IDENTITY_EQUIVALENCE"
    DIRECTION_CONTRADICTION = "DIRECTION_CONTRADICTION"
    REVERSE_ENDPOINT_FORM = "REVERSE_ENDPOINT_FORM"
    ENDPOINT_KIND_TOO_NARROW = "ENDPOINT_KIND_TOO_NARROW"
    ENDPOINT_BLOCKED_BY_KIND_MISCODING = "ENDPOINT_BLOCKED_BY_KIND_MISCODING"
    PREDICATE_MISAPPLIED = "PREDICATE_MISAPPLIED"
    COMPOUND_MULTI_CLAIM = "COMPOUND_MULTI_CLAIM"
    CONDITION_ATTRIBUTION_NOT_IDENTITY = "CONDITION_ATTRIBUTION_NOT_IDENTITY"
    ATOMIC_MISSING_PREDICATE = "ATOMIC_MISSING_PREDICATE"
    EXPLICIT_RENAME_TO_EXISTING = "EXPLICIT_RENAME_TO_EXISTING"
    INSUFFICIENT_SOURCE_SUPPORT = "INSUFFICIENT_SOURCE_SUPPORT"


class NextAction(str, Enum):
    EXTEND_DUNGEONMIND_ENDPOINTS = "EXTEND_DUNGEONMIND_ENDPOINTS"
    PUBLISH_NEW_DUNGEONMIND_PREDICATE = "PUBLISH_NEW_DUNGEONMIND_PREDICATE"
    ADD_BUDDY_EXPLICIT_ADAPTER = "ADD_BUDDY_EXPLICIT_ADAPTER"
    AUTHOR_BUDDY_SOURCE_CORRECTION = "AUTHOR_BUDDY_SOURCE_CORRECTION"
    MIGRATE_VIA_IDENTITY_SEAM = "MIGRATE_VIA_IDENTITY_SEAM"
    DECOMPOSE_COMPOUND_ASSERTION = "DECOMPOSE_COMPOUND_ASSERTION"
    GATHER_OR_CLARIFY_EVIDENCE = "GATHER_OR_CLARIFY_EVIDENCE"


class ResponsibleRepo(str, Enum):
    DUNGEONMIND = "DungeonMind"
    DUNGEONMINDBUDDY = "DungeonMindBuddy"


@dataclass(frozen=True)
class AdjudicationFinding:
    """Source-grounded finding for one residual edge (characterization only)."""

    disposition: ResidualDisposition
    reason_code: ReasonCode
    responsible_repo: ResponsibleRepo
    next_action: NextAction
    candidate_dungeonmind_term: str | None = None
    reverse_endpoints: bool = False
    requires_source_mutation: bool = False
    rationale: str = ""


@dataclass(frozen=True)
class RelationshipResidualAdjudicationRecord:
    schema: str
    edge_id: str
    buddy_predicate: str
    source_node_id: str
    source_buddy_kind: str
    target_node_id: str
    target_buddy_kind: str
    evidence_ref_ids: list[str]
    supporting_assertion_ids: list[str]
    supporting_contribution_ids: list[str]
    disposition: str
    candidate_dungeonmind_term: str | None
    reverse_endpoints: bool
    requires_source_mutation: bool
    responsible_repo: str
    next_action: str
    reason_code: str
    rationale: str = ""
    source_dm_kind: str | None = None
    target_dm_kind: str | None = None
    v3_disposition: str | None = None
    mapped_dm_term_from_v3: str | None = None


@dataclass
class RelationshipResidualAdjudicationReport:
    schema: str
    world_id: str
    campaign_id: str
    revision_id: str
    graph_payload_sha256: str
    relationship_semantic_count: int
    relationship_represented_count: int
    relationship_residual_count: int
    uses_statblock_mechanics_count: int
    adjudicated_count: int
    missing_adjudication_count: int
    extra_adjudication_count: int
    residual_by_predicate: list[dict[str, Any]]
    by_disposition: list[dict[str, Any]]
    by_responsible_repo: list[dict[str, Any]]
    by_buddy_predicate: list[dict[str, Any]]
    by_endpoint_kind_pair: list[dict[str, Any]]
    by_next_action: list[dict[str, Any]]
    records: list[RelationshipResidualAdjudicationRecord] = field(default_factory=list)
    world_graph_digest_before: str | None = None
    world_graph_digest_after: str | None = None
    successor_slices: list[dict[str, Any]] = field(default_factory=list)


class RelationshipResidualAdjudicationError(RuntimeError):
    """Raised when residual identity or adjudication coverage fails closed."""


def _counter_rows(counter: Counter[str]) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in sorted(counter.items())]


def _finding(
    disposition: ResidualDisposition,
    reason_code: ReasonCode,
    responsible_repo: ResponsibleRepo,
    next_action: NextAction,
    *,
    candidate_dungeonmind_term: str | None = None,
    reverse_endpoints: bool = False,
    requires_source_mutation: bool = False,
    rationale: str = "",
) -> AdjudicationFinding:
    if candidate_dungeonmind_term in FORBIDDEN_CATCH_ALL_TERMS:
        raise RelationshipResidualAdjudicationError(
            f"forbidden catch-all candidate term: {candidate_dungeonmind_term}"
        )
    if candidate_dungeonmind_term and candidate_dungeonmind_term.startswith("dnd5e:"):
        # Guard against accidental generic prefix invention in findings.
        pass
    return AdjudicationFinding(
        disposition=disposition,
        reason_code=reason_code,
        responsible_repo=responsible_repo,
        next_action=next_action,
        candidate_dungeonmind_term=candidate_dungeonmind_term,
        reverse_endpoints=reverse_endpoints,
        requires_source_mutation=requires_source_mutation,
        rationale=rationale,
    )


def _ext(
    term: str,
    *,
    rationale: str,
) -> AdjudicationFinding:
    return _finding(
        ResidualDisposition.EXISTING_TERM_ENDPOINT_EXTENSION_CANDIDATE,
        ReasonCode.ENDPOINT_KIND_TOO_NARROW,
        ResponsibleRepo.DUNGEONMIND,
        NextAction.EXTEND_DUNGEONMIND_ENDPOINTS,
        candidate_dungeonmind_term=term,
        rationale=rationale,
    )


def _adapter(
    term: str,
    *,
    reverse_endpoints: bool = False,
    rationale: str,
) -> AdjudicationFinding:
    return _finding(
        ResidualDisposition.EXPLICIT_ADAPTER_CANDIDATE,
        ReasonCode.REVERSE_ENDPOINT_FORM
        if reverse_endpoints
        else ReasonCode.EXPLICIT_RENAME_TO_EXISTING,
        ResponsibleRepo.DUNGEONMINDBUDDY,
        NextAction.ADD_BUDDY_EXPLICIT_ADAPTER,
        candidate_dungeonmind_term=term,
        reverse_endpoints=reverse_endpoints,
        rationale=rationale,
    )


def _new_pred(*, rationale: str, term_hint: str | None = None) -> AdjudicationFinding:
    return _finding(
        ResidualDisposition.NEW_PREDICATE_CANDIDATE,
        ReasonCode.ATOMIC_MISSING_PREDICATE,
        ResponsibleRepo.DUNGEONMIND,
        NextAction.PUBLISH_NEW_DUNGEONMIND_PREDICATE,
        candidate_dungeonmind_term=term_hint,
        rationale=rationale,
    )


def _identity(*, rationale: str) -> AdjudicationFinding:
    return _finding(
        ResidualDisposition.IDENTITY_NOT_RELATIONSHIP,
        ReasonCode.IDENTITY_EQUIVALENCE,
        ResponsibleRepo.DUNGEONMINDBUDDY,
        NextAction.MIGRATE_VIA_IDENTITY_SEAM,
        requires_source_mutation=False,
        rationale=rationale,
    )


def _source(
    *,
    rationale: str,
    reason: ReasonCode = ReasonCode.PREDICATE_MISAPPLIED,
) -> AdjudicationFinding:
    return _finding(
        ResidualDisposition.SOURCE_CORRECTION_REQUIRED,
        reason,
        ResponsibleRepo.DUNGEONMINDBUDDY,
        NextAction.AUTHOR_BUDDY_SOURCE_CORRECTION,
        requires_source_mutation=True,
        rationale=rationale,
    )


def _compound(*, rationale: str) -> AdjudicationFinding:
    return _finding(
        ResidualDisposition.COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP,
        ReasonCode.COMPOUND_MULTI_CLAIM,
        ResponsibleRepo.DUNGEONMINDBUDDY,
        NextAction.DECOMPOSE_COMPOUND_ASSERTION,
        requires_source_mutation=True,
        rationale=rationale,
    )


def _insufficient(*, rationale: str) -> AdjudicationFinding:
    return _finding(
        ResidualDisposition.INSUFFICIENT_EVIDENCE,
        ReasonCode.INSUFFICIENT_SOURCE_SUPPORT,
        ResponsibleRepo.DUNGEONMINDBUDDY,
        NextAction.GATHER_OR_CLARIFY_EVIDENCE,
        rationale=rationale,
    )


# Exact Eldyrwild residual findings. Keys must equal the live v3 residual set.
ELDYRWILD_RESIDUAL_FINDINGS: dict[str, AdjudicationFinding] = {
    "edge:combat_shatter_mages_tower_spider:located_in:item_shatter_mages_tower": _source(
        reason=ReasonCode.ENDPOINT_BLOCKED_BY_KIND_MISCODING,
        rationale=(
            "Encounter is inside Shatter Mage's tower; tower is mistyped as item. "
            "located_in would admit once the place is a location — do not widen "
            "located_in object to arbitrary items for this case."
        ),
    ),
    "edge:group_session24_refugees_of_edge:part_of:loc_3": _source(
        rationale=(
            "Refugees 'from Edge' encodes origin/provenance, not mereological "
            "part_of a location."
        ),
    ),
    "edge:group_session24_refugees_of_edge:part_of_group:mystery_7": _compound(
        rationale=(
            "part_of_group bundles group membership with an unresolved refugee "
            "mystery/situation; cannot flatten to one relationship term."
        ),
    ),
    "edge:group_the_group:participates_in:location_007": _source(
        rationale=(
            "Clearing rats from basements is activity at a place, not "
            "participates_in a location (object must be encounter/event)."
        ),
    ),
    "edge:item-001:located_in:pc:karsemine": _source(
        rationale=(
            "Source describes a monster attacking the cube/Ogonob while Karsemine "
            "fights on the wall; does not support cube located_in Karsemine."
        ),
    ),
    "edge:item:session11:council-headquarters:same_as:loc:the-council:same-place-as": _identity(
        rationale="Council headquarters and 'the Council' place are the same site.",
    ),
    "edge:item:session11:magical-runes:leads_to:item:session11:tainted-meat": _source(
        rationale=(
            "Runes are a detection tool for corrupted meat — investigative/causal "
            "use, not dnd5e:leads_to path connectivity between locations."
        ),
    ),
    "edge:item:session11:paper-bird-summons:present_at:npc_grobnok": _source(
        rationale=(
            "Paper bird flies around Grobnok; present_at object should be a place/"
            "event, not a person. Widening would weaken present_at."
        ),
    ),
    "edge:item:session12:invisibility_potion:carries:node:wolf": _adapter(
        "dnd5e:carries",
        reverse_endpoints=True,
        rationale=(
            "Wolf downs the Invisibility Potion; durable edge has item→npc "
            "inverted from agent-carries-item."
        ),
    ),
    "edge:item:session17:centipede_meat_creature:leads_to:loc:ceiling": _source(
        rationale=(
            "Creature climbs toward the ceiling; motion/approach, not location "
            "path leads_to."
        ),
    ),
    "edge:item:session17:seed:located_in:pc:stafl": _adapter(
        "dnd5e:carries",
        reverse_endpoints=True,
        rationale=(
            "Seed falls into Stafl's hand; possession is PC carries item, not "
            "item located_in PC."
        ),
    ),
    "edge:item:torch:carries:pc:baergrom:passed-to": _adapter(
        "dnd5e:carries",
        reverse_endpoints=True,
        rationale="Torch tossed to Baergrom; reverse to agent-carries-item.",
    ),
    "edge:item:torch:carries:pc:karsemine:passed-to": _adapter(
        "dnd5e:carries",
        reverse_endpoints=True,
        rationale="Torch tossed to Karsemine; reverse to agent-carries-item.",
    ),
    "edge:item_enormous_boulder:same_as:item_foot_of_statue": _identity(
        rationale="Boulder resolves into the statue foot — same object identity.",
    ),
    "edge:item_glowkindle_help_request:located_in:item_job_board": _ext(
        "dnd5e:located_in",
        rationale=(
            "Help request posted on the job board is spatial location-on-container; "
            "existing located_in semantics stay intact if item objects (surfaces/"
            "containers) are admitted."
        ),
    ),
    "edge:item_glowkindle_help_request:mission_targets:group_mercenaries": _compound(
        rationale=(
            "Job posting solicits mercenaries — audience/mission targeting plus "
            "request semantics; not one atomic relationship."
        ),
    ),
    "edge:item_session2_hidden_alchemy_room:same_as:location_003": _identity(
        rationale="Hidden alchemy room item/location duplicate of one place.",
    ),
    "edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of": _source(
        reason=ReasonCode.ENDPOINT_BLOCKED_BY_KIND_MISCODING,
        rationale=(
            "Label 'site of' inverts containment and types the project as party; "
            "authored structure is wrong for located_in."
        ),
    ),
    "edge:loc:last_warehouse:same_as:loc:chilled_warehouse": _identity(
        rationale="Last warehouse reached is the chilled warehouse — same place.",
    ),
    "edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9": _source(
        reason=ReasonCode.ENDPOINT_BLOCKED_BY_KIND_MISCODING,
        rationale=(
            "Packing area belongs to a logistics site/network mistyped as party; "
            "correct kinds before any part_of endpoint work."
        ),
    ),
    "edge:loc:stone_bridge:contains:mystery_stone_bridge_river_name": _source(
        reason=ReasonCode.ENDPOINT_BLOCKED_BY_KIND_MISCODING,
        rationale=(
            "River beside/under Stone Bridge is a location mistyped as mystery; "
            "do not widen contains to mysteries."
        ),
    ),
    "edge:loc:stormspire-academy:objective_of:mystery:session7:glowing_mushrooms": _compound(
        rationale=(
            "Academy tied to potion-making use of mushrooms mixes institution, "
            "objective, and mystery topic."
        ),
    ),
    "edge:loc:underground-entrance:same_as:mystery:session9:second_underground_entrance": _identity(
        rationale="Discovered entrance location duplicates the mystery node.",
    ),
    "edge:loc:wizard_college:within:node:city_mirathorn": _source(
        reason=ReasonCode.ENDPOINT_BLOCKED_BY_KIND_MISCODING,
        rationale=(
            "College within Mirathorn is location→location located_in once the city "
            "is typed as location (currently party)."
        ),
    ),
    "edge:mystery:session7:glowing_mushrooms:leads_to:loc:stormspire-academy": _compound(
        rationale=(
            "Mushrooms 'to be taken to academy' mixes transport intent, destination, "
            "and mystery topic — not path leads_to."
        ),
    ),
    "edge:mystery_1:within:item-001": _ext(
        "dnd5e:located_in",
        rationale=(
            "Ogonob/mystery contained in the dark cube; located_in with item as "
            "container object preserves spatial semantics."
        ),
    ),
    "edge:node:barin_coppergleam:leads_to:node:guardhouse": _source(
        rationale=(
            "Barin proposes operations at guardhouses; plan involvement, not a "
            "path edge from NPC to location."
        ),
    ),
    "edge:node:berin_ironfoot:carries_report_to:loc:stormspire-academy:sends-meat-sample-for-analysis": _compound(
        rationale=(
            "carries_report_to encodes courier + report + destination/analysis "
            "request in one predicate."
        ),
    ),
    "edge:node:cultist:serves:item:session17:centipede_meat_creature": _ext(
        "dnd5e:serves",
        rationale=(
            "Cultist ritually feeds/heals the meat creature; serves semantics hold "
            "if object kinds admit the served entity (item/threat/creature)."
        ),
    ),
    "edge:node:cultists_of_longmont:part_of:node:lesandra:led-by": _adapter(
        "dnd5e:leads",
        reverse_endpoints=True,
        rationale=(
            "Label led_by and source show Lesandra leading cultists; reverse to "
            "dnd5e:leads rather than part_of."
        ),
    ),
    "edge:node:fey_entity:objective_of:node:torbin:offers-torbin-over-as-part-of-the-bargain": _compound(
        rationale=(
            "Fey bargain offering Torbin mixes deal terms, objective, and custody — "
            "not one relationship."
        ),
    ),
    "edge:node:fey_entity:present_at:pc:ephanna:appears-to-ephanna-in-prison": _new_pred(
        term_hint="dnd5e:appears_to",
        rationale=(
            "Fey appears to Ephanna in prison — directed appearance/visitation, not "
            "present_at a person as place."
        ),
    ),
    "edge:node:grit_and_grime:contains:node:goblins_hobgoblins_bugbears": _source(
        rationale=(
            "Warehouse club 'for' goblinoids is venue association; party contains "
            "faction is the wrong structural encoding."
        ),
    ),
    "edge:node:headmaster_tinkerbright:leads:loc:wizard_college": _source(
        reason=ReasonCode.ENDPOINT_BLOCKED_BY_KIND_MISCODING,
        rationale=(
            "Head of the Wizard's College is organizational leadership; college is "
            "mistyped as location. Extending leads to locations would confuse path/"
            "escort senses."
        ),
    ),
    "edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry": _source(
        reason=ReasonCode.ENDPOINT_BLOCKED_BY_KIND_MISCODING,
        rationale=(
            "Townsfolk gather for revelry; revelry is mistyped as group rather than "
            "event/encounter required by participates_in."
        ),
    ),
    "edge:node:pippa:leads_to:loc:stone_bridge": _adapter(
        "dnd5e:travels_to",
        rationale=(
            "Pippa led the crew to Stone Bridge — travel to a location. Map to "
            "existing travels_to; do not widen location-path leads_to to agents."
        ),
    ),
    "edge:node:pippa:travels_to:node:bubbles": _source(
        rationale=(
            "Pippa hitches Bubbles to the wagon — accompaniment/harness, not "
            "travels_to a creature destination."
        ),
    ),
    "edge:node:session6_item_dead_horse:serves:pc:ephanna:served-for-ephanna": _source(
        rationale=(
            "Recap: dead horse served for Bonogo by Ephanna; durable edge subject/"
            "object and label disagree with source food-service claim."
        ),
    ),
    "edge:node:session6_item_runaway_cart:participates_in:pc:baergrom:stopped-by-baergrom": _source(
        rationale=(
            "Runaway cart stopped by Baergrom is patient/agent inversion under "
            "participates_in; requires source correction."
        ),
    ),
    "edge:node:torbin:identified_as:mystery:session8:torbin-oily-eyes:begins-showing-oily-eye-symptoms": _finding(
        ResidualDisposition.COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP,
        ReasonCode.CONDITION_ATTRIBUTION_NOT_IDENTITY,
        ResponsibleRepo.DUNGEONMINDBUDDY,
        NextAction.DECOMPOSE_COMPOUND_ASSERTION,
        requires_source_mutation=True,
        rationale=(
            "Torbin begins showing oily-eye symptoms — condition attribution linked "
            "to a mystery node, not identity and not a single relationship."
        ),
    ),
    "edge:node:torrin_flamescale:serves:loc:guilds:represents": _source(
        reason=ReasonCode.ENDPOINT_BLOCKED_BY_KIND_MISCODING,
        rationale=(
            "Representative of the Guilds; guilds mistyped as location. serves to a "
            "faction would already be endpoint-admitted."
        ),
    ),
    "edge:node:torvak_hempdealer:reports_threat_in:mystery:session4:hempholm-moving-tree": _compound(
        rationale=(
            "reports_threat_in bundles reporting speech act + threat topic + place "
            "context."
        ),
    ),
    "edge:node:torvak_hempdealer_crew:member_of:item:torvak-hemp-caravan": _source(
        reason=ReasonCode.ENDPOINT_BLOCKED_BY_KIND_MISCODING,
        rationale=(
            "Crew belongs to Torvak's caravan group mistyped as item; member_of "
            "already admits group/faction/party objects."
        ),
    ),
    "edge:node:wolf:part_of:item:session17:centipede_meat_creature": _ext(
        "dnd5e:part_of",
        rationale=(
            "Wolf's head materializes as part of the meat creature; mereological "
            "part_of stays coherent if creature/npc subjects are admitted with item "
            "composites."
        ),
    ),
    "edge:npc:bill_the_belly:identified_as:mystery:session8:oil-eyed-guards:shows-oily-eye-symptoms": _finding(
        ResidualDisposition.COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP,
        ReasonCode.CONDITION_ATTRIBUTION_NOT_IDENTITY,
        ResponsibleRepo.DUNGEONMINDBUDDY,
        NextAction.DECOMPOSE_COMPOUND_ASSERTION,
        requires_source_mutation=True,
        rationale=(
            "Bill shows oily-eye symptoms / link to oily-eyed guards mystery — "
            "condition attribution, not identity."
        ),
    ),
    "edge:npc_lysandra:controls_comms_with:loc:mirathorn_gate:may-close-gate": _compound(
        rationale=(
            "may-close-gate mixes authority/control over a location with a "
            "communications-shaped predicate name."
        ),
    ),
    "edge:npc_lysandra:leads:pc:caelynn": _source(
        rationale=(
            "Coordinates assault with Caelynn is tactical coordination of a person, "
            "not organizational leads (object should be group/faction/party)."
        ),
    ),
    "edge:npc_lysandra:threatens:node:cultists_of_longmont:is-threatened-by-cultists": _source(
        reason=ReasonCode.DIRECTION_CONTRADICTION,
        rationale=(
            "Structural threatens Lysandra→cultists contradicts durable qualifier "
            "is-threatened-by-cultists; requires authored correction, not auto-reverse."
        ),
    ),
    "edge:obj:session9:corrupted_meat_pile:routes_to:obj:session9:meat_rack:crawls-toward": _source(
        rationale=(
            "Meat pile crawls toward rack — locomotion toward an object, not "
            "routes_to/leads_to path semantics."
        ),
    ),
    "edge:obj:session9:oil:carries:obj:session9:meat_rack:applied-to": _source(
        rationale=(
            "Oil poured/applied onto the meat rack; application, not carries."
        ),
    ),
    "edge:obj:session9:oil:identified_as:node:wolf": _source(
        rationale=(
            "Evidence discusses oily eyes on Wolf/guards, not that oil is identified "
            "as Wolf."
        ),
    ),
    "edge:obj:session9:scroll_abyssal:identified_as:mystery:session9:scroll_in_strange_language": _identity(
        rationale=(
            "Scroll item and mystery describing the same discovered scroll are "
            "identity duplicates, not a factual relationship."
        ),
    ),
    "edge:pc:bonogo:defends_weakened_location:node:prisoners_session9:protects": _new_pred(
        term_hint="dnd5e:protects",
        rationale=(
            "Bonogo bars the door to protect prisoners — atomic protection of a "
            "group; Buddy predicate name is compound but source claim is protects."
        ),
    ),
    "edge:pc:bonogo:travels_to:pc:karsemine": _source(
        rationale=(
            "Bonogo climbs to reach/heal Karsemine — approach to a person, not "
            "travels_to a location; widening destinations to PCs would weaken the term."
        ),
    ),
    "edge:pc:caelynn:controls_comms_with:npc_grobnok": _new_pred(
        term_hint="dnd5e:communicates_with",
        rationale=(
            "Caelynn calls Grobnok — atomic communication. Do not inherit the "
            "compound controls_comms_with name as the published term."
        ),
    ),
    "edge:pc:caelynn:participates_in:node:hempholm_folk_revelry": _source(
        reason=ReasonCode.ENDPOINT_BLOCKED_BY_KIND_MISCODING,
        rationale=(
            "Caelynn joins festivities; revelry mistyped as group instead of event."
        ),
    ),
    "edge:pc:ephanna:controls_comms_with:item:mage_hand_lasso": _source(
        rationale=(
            "Ephanna uses mage hand to lasso Bubbles — tool use, not communications."
        ),
    ),
    "edge:pc:ephanna:participates_in:node:shepherds_flock": _adapter(
        "dnd5e:member_of",
        rationale=(
            "Ephanna goes along with / joins The Shepherds Flock — membership, not "
            "participates_in an event."
        ),
    ),
    "edge:pc:stafl:participates_in:node:heroes-party:performed-for-the-party": _adapter(
        "dnd5e:member_of",
        rationale=(
            "Stafl is part of the heroes party; durable participates_in + performance "
            "label overstates a membership fact."
        ),
    ),
}


def iter_v3_residual_edges(store: Any, vocabulary: Any) -> list[Any]:
    residuals: list[Any] = []
    for edge in store.edges.values():
        *_rest, disposition, _mapped, _reverse = _classify_edge_predicate_v3(
            edge, store, vocabulary
        )
        if disposition in (
            PredicateDisposition.EXISTING_EXPLICIT_ADAPTER,
            PredicateDisposition.MECHANICS_SPECIALIZATION,
        ):
            continue
        residuals.append(edge)
    residuals.sort(key=lambda e: e.edge_id)
    return residuals


def collect_v3_residual_edge_ids(store: Any, vocabulary: Any) -> set[str]:
    return {edge.edge_id for edge in iter_v3_residual_edges(store, vocabulary)}


def _supports_for_edge(store: Any, edge_id: str) -> list[dict[str, Any]]:
    supports: list[dict[str, Any]] = []
    for support in store.assertion_support.values():
        if support.get("graph_object_id") == edge_id:
            supports.append(support)
    return supports


def _ground_edge(store: Any, edge: Any, vocabulary: Any) -> dict[str, Any]:
    source = store.nodes[edge.source_node_id]
    target = store.nodes[edge.target_node_id]
    source_dm, _ = _endpoint_dm_kinds(store, edge.source_node_id)
    target_dm, _ = _endpoint_dm_kinds(store, edge.target_node_id)
    *_r, disposition, mapped, reverse = _classify_edge_predicate_v3(
        edge, store, vocabulary
    )
    supports = _supports_for_edge(store, edge.edge_id)
    assertion_ids = [
        sid for sid in (s.get("assertion_id") for s in supports) if isinstance(sid, str)
    ]
    contribution_ids: list[str] = []
    for support in supports:
        contribution_ids.extend(support.get("active_contribution_ids") or [])
        intro = support.get("introduced_by_contribution_id")
        if isinstance(intro, str):
            contribution_ids.append(intro)
    state = edge.state if isinstance(edge.state, dict) else {}
    intro = state.get("introduced_by_contribution_id")
    if isinstance(intro, str):
        contribution_ids.append(intro)
    # preserve order, unique
    contribution_ids = list(dict.fromkeys(contribution_ids))
    evidence_ids = list(dict.fromkeys(list(edge.evidence_ref_ids or [])))
    for support in supports:
        evidence_ids.extend(support.get("evidence_ref_ids") or [])
        for refs in (support.get("per_contribution_evidence_ref_ids") or {}).values():
            evidence_ids.extend(refs or [])
    evidence_ids = list(dict.fromkeys(evidence_ids))
    return {
        "edge": edge,
        "source_buddy_kind": source.kind,
        "target_buddy_kind": target.kind,
        "source_dm_kind": source_dm,
        "target_dm_kind": target_dm,
        "v3_disposition": disposition.value
        if hasattr(disposition, "value")
        else str(disposition),
        "mapped_dm_term": mapped,
        "reverse_endpoints_v3": reverse,
        "evidence_ref_ids": evidence_ids,
        "supporting_assertion_ids": assertion_ids,
        "supporting_contribution_ids": contribution_ids,
        "has_reverse_qualifier": edge_has_reverse_direction_qualifier_v3(
            buddy_predicate=edge.predicate,
            edge_id=edge.edge_id,
        ),
        "mapping": resolve_buddy_predicate_mapping_v3(edge.predicate),
    }


def adjudicate_synthetic_residual(
    *,
    buddy_predicate: str,
    source_buddy_kind: str,
    target_buddy_kind: str,
    edge_id: str,
    evidence_supports_exact_dm_term: str | None = None,
    reverse_endpoints: bool = False,
    is_identity: bool = False,
    is_compound: bool = False,
    direction_contradiction: bool = False,
    insufficient_evidence: bool = False,
    endpoint_extension_safe: bool = False,
    predicate_misapplied: bool = False,
    mechanics_predicate: bool = False,
) -> AdjudicationFinding:
    """Rule-facing adjudicator for synthetic tests (no catch-alls)."""
    if mechanics_predicate or buddy_predicate == "uses_statblock":
        raise RelationshipResidualAdjudicationError(
            "uses_statblock must never enter residual relationship adjudication"
        )
    if insufficient_evidence:
        return _insufficient(rationale="synthetic insufficient evidence")
    if direction_contradiction:
        return _source(
            reason=ReasonCode.DIRECTION_CONTRADICTION,
            rationale="synthetic direction contradiction",
        )
    if is_identity or buddy_predicate == "same_as":
        if evidence_supports_exact_dm_term == "dnd5e:same_as":
            raise RelationshipResidualAdjudicationError(
                "identity must not become dnd5e:same_as relationship"
            )
        return _identity(rationale="synthetic identity")
    if is_compound:
        return _compound(rationale="synthetic compound assertion")
    if predicate_misapplied:
        return _source(rationale="synthetic predicate misapplied")
    if evidence_supports_exact_dm_term:
        if evidence_supports_exact_dm_term in FORBIDDEN_CATCH_ALL_TERMS:
            raise RelationshipResidualAdjudicationError("catch-all forbidden")
        # Matching predicate string alone is not enough — require explicit support flag.
        if endpoint_extension_safe:
            return _ext(
                evidence_supports_exact_dm_term,
                rationale="synthetic safe endpoint extension",
            )
        return _adapter(
            evidence_supports_exact_dm_term,
            reverse_endpoints=reverse_endpoints,
            rationale="synthetic explicit adapter",
        )
    # Unknown / no mapping support
    if endpoint_extension_safe:
        raise RelationshipResidualAdjudicationError(
            "endpoint extension requires an exact existing DM term"
        )
    return _new_pred(rationale="synthetic unknown atomic predicate")


def _build_record(
    grounded: Mapping[str, Any],
    finding: AdjudicationFinding,
) -> RelationshipResidualAdjudicationRecord:
    edge = grounded["edge"]
    return RelationshipResidualAdjudicationRecord(
        schema=RELATIONSHIP_RESIDUAL_ADJUDICATION_SCHEMA,
        edge_id=edge.edge_id,
        buddy_predicate=edge.predicate,
        source_node_id=edge.source_node_id,
        source_buddy_kind=grounded["source_buddy_kind"],
        target_node_id=edge.target_node_id,
        target_buddy_kind=grounded["target_buddy_kind"],
        evidence_ref_ids=list(grounded["evidence_ref_ids"]),
        supporting_assertion_ids=list(grounded["supporting_assertion_ids"]),
        supporting_contribution_ids=list(grounded["supporting_contribution_ids"]),
        disposition=finding.disposition.value,
        candidate_dungeonmind_term=finding.candidate_dungeonmind_term,
        reverse_endpoints=finding.reverse_endpoints,
        requires_source_mutation=finding.requires_source_mutation,
        responsible_repo=finding.responsible_repo.value,
        next_action=finding.next_action.value,
        reason_code=finding.reason_code.value,
        rationale=finding.rationale,
        source_dm_kind=grounded["source_dm_kind"],
        target_dm_kind=grounded["target_dm_kind"],
        v3_disposition=grounded["v3_disposition"],
        mapped_dm_term_from_v3=grounded["mapped_dm_term"],
    )


def derive_successor_slices(
    records: Iterable[RelationshipResidualAdjudicationRecord],
) -> list[dict[str, Any]]:
    """Mechanically derive successor work slices from adjudications."""
    rows = list(records)
    by_disp = Counter(r.disposition for r in rows)
    slices: list[dict[str, Any]] = []

    def _slice(
        name: str,
        owner: str,
        dispositions: list[str],
        note: str,
    ) -> None:
        matched = [r for r in rows if r.disposition in dispositions]
        if not matched:
            return
        slices.append(
            {
                "name": name,
                "responsible_repo": owner,
                "edge_count": len(matched),
                "dispositions": sorted({r.disposition for r in matched}),
                "edge_ids": sorted(r.edge_id for r in matched),
                "note": note,
            }
        )

    _slice(
        "dungeonmind-endpoint-extensions",
        ResponsibleRepo.DUNGEONMIND.value,
        [ResidualDisposition.EXISTING_TERM_ENDPOINT_EXTENSION_CANDIDATE.value],
        "Smallest world-object relationship endpoint widenings for proven terms only.",
    )
    _slice(
        "dungeonmind-new-predicates",
        ResponsibleRepo.DUNGEONMIND.value,
        [ResidualDisposition.NEW_PREDICATE_CANDIDATE.value],
        "Publish only adjudicated atomic missing predicates (no catch-alls).",
    )
    _slice(
        "buddy-explicit-adapters",
        ResponsibleRepo.DUNGEONMINDBUDDY.value,
        [ResidualDisposition.EXPLICIT_ADAPTER_CANDIDATE.value],
        "Buddy→DungeonMind explicit adapters including local reversals.",
    )
    _slice(
        "buddy-source-corrections",
        ResponsibleRepo.DUNGEONMINDBUDDY.value,
        [ResidualDisposition.SOURCE_CORRECTION_REQUIRED.value],
        "Author governed correction contributions for defective edges.",
    )
    _slice(
        "buddy-compound-decomposition",
        ResponsibleRepo.DUNGEONMINDBUDDY.value,
        [ResidualDisposition.COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP.value],
        "Decompose compound Buddy assertions before relationship mapping.",
    )
    _slice(
        "identity-migration",
        ResponsibleRepo.DUNGEONMINDBUDDY.value,
        [ResidualDisposition.IDENTITY_NOT_RELATIONSHIP.value],
        "Identity seam — must not enter ordinary relationship vocabulary.",
    )
    _slice(
        "evidence-clarification",
        ResponsibleRepo.DUNGEONMINDBUDDY.value,
        [ResidualDisposition.INSUFFICIENT_EVIDENCE.value],
        "Gather or clarify durable support before semantic migration.",
    )
    slices.append(
        {
            "name": "summary-disposition-counts",
            "responsible_repo": "derived",
            "edge_count": len(rows),
            "dispositions": _counter_rows(by_disp),
            "edge_ids": [],
            "note": "Counts are findings, not targets to zero in this PR.",
        }
    )
    return slices


def analyze_eldyrwild_relationship_residual_adjudication(
    *,
    root: Path,
    world_id: str = ELDYRWILD_WORLD_ID,
    revision_id: str = ELDYRWILD_REVISION_ID,
    findings: Mapping[str, AdjudicationFinding] | None = None,
) -> RelationshipResidualAdjudicationReport:
    findings_map = dict(findings or ELDYRWILD_RESIDUAL_FINDINGS)
    digest_before = snapshot_world_graph_tree_digest(root, world_id)
    manifest, store = _load_exact_buddy_revision(
        root=root, world_id=world_id, revision_id=revision_id
    )
    payload_sha = getattr(manifest, "graph_payload_sha256", None) or getattr(
        manifest, "payload_sha256", None
    )
    if hasattr(manifest, "model_dump"):
        md = manifest.model_dump()
        payload_sha = payload_sha or md.get("graph_payload_sha256") or md.get(
            "payload_sha256"
        )
    if payload_sha != ELDYRWILD_PAYLOAD_SHA256 and world_id == ELDYRWILD_WORLD_ID:
        raise RelationshipResidualAdjudicationError(
            f"payload sha mismatch: {payload_sha} != {ELDYRWILD_PAYLOAD_SHA256}"
        )

    vocabulary = load_builtin_world_object_v3_vocabulary()
    residual_edges = iter_v3_residual_edges(store, vocabulary)
    residual_ids = {edge.edge_id for edge in residual_edges}
    if len(residual_edges) != EXPECTED_RESIDUAL_COUNT:
        raise RelationshipResidualAdjudicationError(
            f"v3 residual count {len(residual_edges)} != {EXPECTED_RESIDUAL_COUNT}"
        )

    pred_counts = Counter(edge.predicate for edge in residual_edges)
    if dict(pred_counts) != EXPECTED_RESIDUAL_BY_PREDICATE:
        raise RelationshipResidualAdjudicationError(
            f"residual predicate table drift: {dict(pred_counts)}"
        )

    # Count represented / mechanics for report parity with v3
    represented = 0
    mechanics = 0
    semantic = 0
    for edge in store.edges.values():
        *_r, disposition, _m, _rev = _classify_edge_predicate_v3(
            edge, store, vocabulary
        )
        if disposition == PredicateDisposition.MECHANICS_SPECIALIZATION:
            mechanics += 1
            continue
        semantic += 1
        if disposition == PredicateDisposition.EXISTING_EXPLICIT_ADAPTER:
            represented += 1

    missing = sorted(residual_ids - set(findings_map))
    extra = sorted(set(findings_map) - residual_ids)
    if missing or extra:
        raise RelationshipResidualAdjudicationError(
            f"adjudication coverage drift missing={missing[:5]} extra={extra[:5]}"
        )

    records: list[RelationshipResidualAdjudicationRecord] = []
    for edge in residual_edges:
        if edge.predicate == "uses_statblock":
            raise RelationshipResidualAdjudicationError(
                "uses_statblock leaked into residual adjudication set"
            )
        grounded = _ground_edge(store, edge, vocabulary)
        finding = findings_map[edge.edge_id]
        if (
            finding.candidate_dungeonmind_term
            and finding.candidate_dungeonmind_term in FORBIDDEN_CATCH_ALL_TERMS
        ):
            raise RelationshipResidualAdjudicationError(
                f"forbidden term on {edge.edge_id}"
            )
        if edge.predicate == "same_as" and finding.disposition != (
            ResidualDisposition.IDENTITY_NOT_RELATIONSHIP
        ):
            raise RelationshipResidualAdjudicationError(
                f"same_as must be IDENTITY_NOT_RELATIONSHIP: {edge.edge_id}"
            )
        records.append(_build_record(grounded, finding))

    digest_after = snapshot_world_graph_tree_digest(root, world_id)
    if digest_before != digest_after:
        raise RelationshipResidualAdjudicationError(
            "world graph mutated during residual adjudication"
        )

    by_disposition = Counter(r.disposition for r in records)
    by_repo = Counter(r.responsible_repo for r in records)
    by_pred = Counter(r.buddy_predicate for r in records)
    by_pair = Counter(
        f"{r.source_buddy_kind}->{r.target_buddy_kind}" for r in records
    )
    by_action = Counter(r.next_action for r in records)

    return RelationshipResidualAdjudicationReport(
        schema=RELATIONSHIP_RESIDUAL_ADJUDICATION_SCHEMA,
        world_id=world_id,
        campaign_id=ELDYRWILD_CAMPAIGN_ID,
        revision_id=revision_id,
        graph_payload_sha256=str(payload_sha),
        relationship_semantic_count=semantic,
        relationship_represented_count=represented,
        relationship_residual_count=len(residual_edges),
        uses_statblock_mechanics_count=mechanics,
        adjudicated_count=len(records),
        missing_adjudication_count=0,
        extra_adjudication_count=0,
        residual_by_predicate=_counter_rows(pred_counts),
        by_disposition=_counter_rows(by_disposition),
        by_responsible_repo=_counter_rows(by_repo),
        by_buddy_predicate=_counter_rows(by_pred),
        by_endpoint_kind_pair=_counter_rows(by_pair),
        by_next_action=_counter_rows(by_action),
        records=records,
        world_graph_digest_before=digest_before,
        world_graph_digest_after=digest_after,
        successor_slices=derive_successor_slices(records),
    )


def compact_relationship_residual_adjudication_report(
    report: RelationshipResidualAdjudicationReport,
) -> dict[str, Any]:
    """Durable fixture JSON (stable key order for regression)."""
    payload = {
        "schema": report.schema,
        "world_id": report.world_id,
        "campaign_id": report.campaign_id,
        "revision_id": report.revision_id,
        "graph_payload_sha256": report.graph_payload_sha256,
        "relationship_semantic_count": report.relationship_semantic_count,
        "relationship_represented_count": report.relationship_represented_count,
        "relationship_residual_count": report.relationship_residual_count,
        "uses_statblock_mechanics_count": report.uses_statblock_mechanics_count,
        "adjudicated_count": report.adjudicated_count,
        "missing_adjudication_count": report.missing_adjudication_count,
        "extra_adjudication_count": report.extra_adjudication_count,
        "residual_by_predicate": report.residual_by_predicate,
        "by_disposition": report.by_disposition,
        "by_responsible_repo": report.by_responsible_repo,
        "by_buddy_predicate": report.by_buddy_predicate,
        "by_endpoint_kind_pair": report.by_endpoint_kind_pair,
        "by_next_action": report.by_next_action,
        "successor_slices": [
            {
                "name": s["name"],
                "responsible_repo": s["responsible_repo"],
                "edge_count": s["edge_count"],
                "dispositions": s["dispositions"],
                "note": s["note"],
                "edge_ids": s["edge_ids"],
            }
            for s in report.successor_slices
        ],
        "records": [
            {
                "schema": r.schema,
                "edge_id": r.edge_id,
                "buddy_predicate": r.buddy_predicate,
                "source_node_id": r.source_node_id,
                "source_buddy_kind": r.source_buddy_kind,
                "target_node_id": r.target_node_id,
                "target_buddy_kind": r.target_buddy_kind,
                "evidence_ref_ids": r.evidence_ref_ids,
                "supporting_assertion_ids": r.supporting_assertion_ids,
                "supporting_contribution_ids": r.supporting_contribution_ids,
                "disposition": r.disposition,
                "candidate_dungeonmind_term": r.candidate_dungeonmind_term,
                "reverse_endpoints": r.reverse_endpoints,
                "requires_source_mutation": r.requires_source_mutation,
                "responsible_repo": r.responsible_repo,
                "next_action": r.next_action,
                "reason_code": r.reason_code,
                "rationale": r.rationale,
                "source_dm_kind": r.source_dm_kind,
                "target_dm_kind": r.target_dm_kind,
                "v3_disposition": r.v3_disposition,
                "mapped_dm_term_from_v3": r.mapped_dm_term_from_v3,
            }
            for r in sorted(report.records, key=lambda row: row.edge_id)
        ],
    }
    return payload


def record_to_dict(record: RelationshipResidualAdjudicationRecord) -> dict[str, Any]:
    return asdict(record)
