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
