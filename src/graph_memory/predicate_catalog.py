"""Runtime-owned v1 exact-predicate catalogue and closed family vocabulary."""

from __future__ import annotations

from typing import Any

from src.graph_memory import identity_resolution as ir

# Preserve the full extraction schema, including families with no exact predicates.
PREDICATE_FAMILY_IDS = frozenset(
    {
        "alias",
        "authority",
        "causality",
        "citation",
        "hook_relation",
        "identity",
        "kinship",
        "knowledge",
        "location_hierarchy",
        "membership",
        "ownership",
        "participation",
        "routing",
        "social_relation",
        "source_derivation",
        "temporal_sequence",
        "threat_relation",
        "visibility",
    }
)

# v1 exact predicates grouped by runtime predicate family.
V1_EXACT_PREDICATES: dict[str, str] = dict(ir.PREDICATE_FAMILY)

PREDICATE_VALIDATION_CODES = frozenset(
    {
        "unknown_relationship_type",
        "unknown_predicate_family",
        "relationship_family_mismatch",
    }
)


def predicate_family_ids() -> tuple[str, ...]:
    """Sorted closed family IDs admitted by the extraction schema."""
    return tuple(sorted(PREDICATE_FAMILY_IDS))


def exact_predicate_ids() -> tuple[str, ...]:
    """Sorted v1 exact ``relationship_type`` ids allowed in edge extraction."""
    return tuple(sorted(V1_EXACT_PREDICATES))


def predicates_by_family() -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for predicate, family in sorted(V1_EXACT_PREDICATES.items()):
        grouped.setdefault(family, []).append(predicate)
    return {family: tuple(sorted(predicates)) for family, predicates in sorted(grouped.items())}


def predicate_family_for_type(relationship_type: str) -> str:
    """Catalogue family for a catalog predicate; unknown verbs use ``rel:<verb>``."""
    raw = (relationship_type or "").strip().lower()
    if not raw:
        return "rel:unknown"
    return V1_EXACT_PREDICATES.get(raw, f"rel:{raw}")


def edge_predicate_family(edge: Any) -> str:
    """Prefer explicit ``predicate_family`` on an edge; else infer from ``relationship_type``."""
    explicit = ir._get(edge, "predicate_family", None)
    if explicit:
        return str(explicit).strip()
    return predicate_family_for_type(str(ir._get(edge, "relationship_type", "") or ""))


def validate_edge_predicate(
    relationship_type: str,
    predicate_family: str | None,
) -> list[str]:
    """Return validation issue codes for a relationship_type / predicate_family pair."""
    rel = (relationship_type or "").strip().lower()
    fam = (predicate_family or "").strip()
    issues: list[str] = []

    if rel and rel not in V1_EXACT_PREDICATES:
        issues.append("unknown_relationship_type")

    if fam:
        if fam not in PREDICATE_FAMILY_IDS:
            issues.append("unknown_predicate_family")
        elif rel in V1_EXACT_PREDICATES and V1_EXACT_PREDICATES[rel] != fam:
            issues.append("relationship_family_mismatch")
    elif rel in V1_EXACT_PREDICATES:
        # Missing family is not an error during normalization; caller may fill it in.
        pass

    return issues


def prompt_markdown(*, max_predicates_per_family: int | None = None) -> str:
    """Compact markdown catalog grouped by runtime predicate family."""
    lines = [
        "## Controlled edge predicates (v1)",
        "",
        "Choose **exactly one** `relationship_type` from this catalog and set matching "
        "`predicate_family`. Do not invent verbs (e.g. `recognizes`, `warns_of`, `launches`). "
        "If no catalog predicate fits, omit the edge.",
        "",
    ]
    for family in predicate_family_ids():
        predicates = predicates_by_family().get(family, ())
        if not predicates:
            continue
        shown = predicates
        if max_predicates_per_family is not None:
            shown = predicates[:max_predicates_per_family]
        pred_list = ", ".join(f"`{p}`" for p in shown)
        lines.append(f"- **{family}**: {pred_list}")
    return "\n".join(lines)


def catalog_cross_check_issues() -> list[str]:
    """Human-readable issues when exact predicates refer to an undefined family."""
    catalog_families = PREDICATE_FAMILY_IDS
    issues: list[str] = []
    for predicate, family in V1_EXACT_PREDICATES.items():
        if family not in catalog_families:
            issues.append(f"predicate {predicate!r} maps to unknown family {family!r}")
    used_families = set(V1_EXACT_PREDICATES.values())
    for family in sorted(used_families):
        if family not in catalog_families:
            issues.append(f"catalog uses family {family!r} missing from runtime catalogue")
    return issues


# Reviewed prompt guidance for Buddy custom recap relationships. These meanings
# are not native vocabulary mappings, endpoint gates or source-truth evidence.
# Worldbuilding uses its own publication contract and does not consume this block.
RECAP_PREDICATE_MEANINGS: dict[str, str] = {
    'alias_of': 'Subject is an alias of object; spelling resemblance alone does not establish an alias.',
    'allied_with': 'Subject is allied with object; meeting alone is insufficient.',
    'also_known_as': 'Subject is also known as object; contextual name similarity alone is insufficient.',
    'associated_with': "Subject is associated with object; preserve the source's limited association without stronger membership or identity.",
    'attacks': 'Subject attacks object; a visit, sighting, warning or planned attack is not an actual attack.',
    'attends': 'Subject attends object, the attended event or gathering.',
    'aware_of': 'Subject is aware of object.',
    'belongs_to': 'Subject belongs to object in the source’s stated ownership or membership sense. Object is the owner or containing group; do not infer ownership from mere use.',
    'besieges': 'Subject besieges object; mere presence near a location is insufficient.',
    'carries': 'Subject carries object; object is what is carried.',
    'carries_report_to': 'Subject carries a report to object, the recipient or destination.',
    'caused_by': 'Subject is caused by object; object is the cause.',
    'causes': 'Subject causes object; sequence or proximity alone does not establish causation.',
    'child_of': 'Subject is a child of object.',
    'commands': 'Subject commands object.',
    'contains': 'Subject contains object; subject is the container.',
    'controls_comms_with': 'Subject controls communications with object; stopping movement, summoning, or waking someone does not establish this.',
    'cooperates_with': 'Subject cooperates with object.',
    'defends_weakened_location': 'Subject defends object, a location whose weakened state is supported; tense guards alone establish neither condition.',
    'displaced_from': 'Subject has been displaced from object, the prior location; do not invent an exact fictional-time anchor.',
    'distrusts': 'Subject distrusts object; dislike or hatred alone does not establish distrust.',
    'east_of': 'Subject is spatially east of object.',
    'governs': 'Subject governs object; selling goods or being present does not establish governing authority.',
    'hires': 'Subject hires object.',
    'holds': 'Subject holds object in an explicitly supported custody, possession or position sense. Being the subject of a contract does not establish holding it.',
    'identified_as': 'Subject is identified as object by the source. Keep the identifying source and uncertainty; identification alone does not authorize canonical merging.',
    'is_a': 'Subject is an instance or kind of object, the stated type or category. A participant is not its event and a nearby entity is not a type.',
    'knows_about': 'Subject knows about object; knowledge content and attribution must remain supported.',
    'leads': 'Subject leads object; object is the led entity.',
    'leads_to': 'Subject leads to object as a route, access point or stated connection endpoint. Do not infer causation from proximity.',
    'linked_to': 'Subject is linked to object; a link does not establish identity or ownership.',
    'located_in': 'Subject is located in object; object is the containing place.',
    'married_to': 'Subject is married to object.',
    'member_of': 'Subject is a member of object; participating in a scene together does not establish membership.',
    'missing_contact': 'Subject lacks expected or recent contact with object. This asserts the subject’s contact gap, not that object is missing or endangered.',
    'mission_focus': 'Subject mission or mission-directing actor has object as the mission focus. The focus is the object, not the subject; intention is not completion.',
    'mission_targets': 'Subject mission or mission-directing actor targets object as the mission target. State the mission context; do not infer an accomplished outcome.',
    'near': 'Subject is spatially near object; shared topic, event preparation or association is insufficient.',
    'north_of': 'Subject is spatially north of object.',
    'objective_of': 'Subject is the objective pursued by object, the actor or activity with that objective. Do not reverse objective and pursuer or assert completion.',
    'owns': 'Subject owns object; use of an object or naming proximity alone does not establish ownership.',
    'parent_of': 'Subject is a parent of object.',
    'part_of': 'Subject is a constituent part of object, not merely a nearby participant.',
    'part_of_group': 'Subject is part of object, a group; mere co-presence is insufficient.',
    'participates_in': 'Subject participates in object, an activity or event; participant is not identical to event.',
    'path_to': 'Subject is a path leading to object, its destination. Do not reverse path and endpoint.',
    'possesses': 'Subject possesses or has custody/control of object; the possessed item does not possess its holder. Possession does not imply ownership.',
    'present_at': 'Subject is present at object; a plan to attend is insufficient.',
    'protects': 'Subject protects object from a threat; direction is protector to protected.',
    'pursues': 'Subject pursues object as an objective; an objective is not a completed outcome.',
    'recruits_for': 'Subject recruits for object.',
    'refers_to': 'Subject refers to object; reference is not identity.',
    'replaced_contact': 'Subject replaces object in a contact or communication role. A device changing hands alone does not establish replacement of that role.',
    'reports_threat_in': 'Subject reports a threat in object; grumbling or disapproval alone is not a threat report.',
    'reports_to': 'Subject reports to object as the reporting recipient or superior supported by the source.',
    'results_in': 'Subject results in object; object is the result.',
    'rivals': 'Subject is a rival of object.',
    'road_to': 'Subject is a road leading to object, its destination. Traveling along a road does not make the road the traveler’s destination.',
    'routes_to': 'Subject routes toward object, the route destination. Keep the source’s route or routing-actor role; association with a traveler is not a destination.',
    'rules': 'Subject rules object.',
    'same_as': 'Subject and object are the same referent; participant, event, role, location and related entity are not interchangeable.',
    'serves': 'Subject serves object; direction is serving actor to the served entity.',
    'sibling_of': 'Subject is a sibling of object.',
    'south_of': 'Subject is spatially south of object.',
    'spouse_of': 'Subject is a spouse of object.',
    'sublocation_of': 'Subject is a smaller location within object.',
    'suspects': "Subject suspects object; this is the subject's suspicion, not objective confirmation.",
    'threatens': 'Subject threatens object; disapproval alone is insufficient and attack is not implied.',
    'travels_to': 'Subject travels toward object as a destination; traveling with someone does not make that person the destination.',
    'trusts': 'Subject trusts object.',
    'west_of': 'Subject is spatially west of object.',
    'within': 'Subject is within object, which supplies the containing boundary.',
    'works_with': 'Subject works or collaborates with object; drinking, meeting or catching up alone does not establish collaboration.',
}


def recap_predicate_meaning_guidance() -> str:
    """Render one source of custom meanings for the Recap edge instruction."""
    lines = [
        "## Recap relationship meanings",
        "",
        "Read each relationship as subject → predicate → object. These meanings "
        "do not prove source support or authorize canonical identity changes.",
        "",
    ]
    lines.extend(
        f"- `{predicate}`: {meaning}"
        for predicate, meaning in sorted(RECAP_PREDICATE_MEANINGS.items())
    )
    return "\n".join(lines)
