"""Identity resolution and dedup primitives for candidate graphs.

This module is the shared substrate for two related problems:

1. **Comparator matching** (candidate-vs-gold): match semantically equivalent
   nodes/edges/beats across two graphs that were authored independently and so
   disagree on ``node_id`` strings, ``label`` wording, fine-grained
   ``node_type`` (``group`` vs ``organization``), and ``relationship_type``
   verb (``works_with`` vs ``allied_with``).

2. **Production dedup / cross-session merge**: when several sessions each emit a
   "Lysandra" / "Mirathorn" / "the swamp" node, collapse them into one
   canonical entity rather than accumulating duplicates, and collapse
   inverse-relationship duplicates (``parent_of(A,B)`` + ``child_of(B,A)``).

It is deliberately pure (no I/O, no LLM, no corpus access) and tolerant of both
plain ``Mapping`` payloads (gold/candidate JSON) and the
``CandidateGraphPreview`` dataclasses. The class maps are aligned to the closed
vocabularies in ``src/graph_memory/candidate_graph_preview.py`` (``NODE_TYPES``,
``CORPUS_REF_TYPES``) and the registry predicate families in
``evals/graph_memory_layer/taxonomy_registry.json``
(``relationship_predicate_family``).
"""

from __future__ import annotations

import re
from typing import Any, Callable, Iterable, Mapping, Sequence

# --------------------------------------------------------------------------- #
# Equivalence classes
# --------------------------------------------------------------------------- #

# node_type / corpus_ref.type -> coarse identity class. Aligns the candidate
# preview NODE_TYPES + CORPUS_REF_TYPES so that e.g. character/npc/pc and
# group/organization/faction do not fork during matching or dedup.
NODE_TYPE_CLASS: dict[str, str] = {
    # actors
    "character": "actor", "npc": "actor", "pc": "actor", "creature": "actor",
    # collectives
    "group": "collective", "organization": "collective", "faction": "collective",
    "party": "collective",
    # places
    "location": "place", "sublocation": "place", "region": "place",
    "route": "place", "hub": "place",
    # unresolved / narrative threads
    "mystery": "thread", "clue": "thread", "thread": "thread", "rumor": "thread",
    "promise": "thread", "debt": "thread", "hook": "thread", "quest": "thread",
    "unknown_important": "thread", "threat": "thread",
    # phenomena / temporal
    "event": "phenomenon", "warning": "phenomenon", "session": "phenomenon",
    "campaign": "phenomenon",
    # objects
    "item": "object", "statblock": "object", "roll-table": "object", "roll_table": "object",
    # structural
    "session_beat": "beat",
}

# raw relationship_type verb -> registry predicate family (closed set of 18 in
# taxonomy_registry.json:relationship_predicate_family). Unknown verbs fall back
# to ``rel:<verb>`` so that an exact-verb match still works but distinct unknown
# verbs do not silently collide.
PREDICATE_FAMILY: dict[str, str] = {
    # kinship
    "parent_of": "kinship", "child_of": "kinship", "sibling_of": "kinship",
    "married_to": "kinship", "spouse_of": "kinship",
    # location hierarchy
    "located_in": "location_hierarchy", "part_of": "location_hierarchy",
    "within": "location_hierarchy", "contains": "location_hierarchy",
    "sublocation_of": "location_hierarchy", "north_of": "location_hierarchy",
    "south_of": "location_hierarchy", "east_of": "location_hierarchy",
    "west_of": "location_hierarchy", "near": "location_hierarchy",
    "defends_weakened_location": "location_hierarchy",
    # routing
    "travels_to": "routing", "routes_to": "routing", "leads_to": "routing",
    "road_to": "routing", "path_to": "routing",
    # membership
    "member_of": "membership", "belongs_to": "membership", "serves": "membership",
    "recruits_for": "membership", "part_of_group": "membership",
    # authority
    "governs": "authority", "commands": "authority", "hires": "authority",
    "reports_to": "authority", "carries_report_to": "authority", "rules": "authority",
    # knowledge / awareness
    "knows_about": "knowledge", "aware_of": "knowledge", "suspects": "knowledge",
    "missing_contact": "knowledge", "replaced_contact": "knowledge",
    "reports_threat_in": "knowledge", "controls_comms_with": "knowledge",
    "refers_to": "knowledge",
    # social relations
    "works_with": "social_relation", "allied_with": "social_relation",
    "cooperates_with": "social_relation", "distrusts": "social_relation",
    "trusts": "social_relation", "rivals": "social_relation",
    "associated_with": "social_relation", "linked_to": "social_relation",
    # ownership
    "owns": "ownership", "holds": "ownership", "carries": "ownership",
    "possesses": "ownership",
    # causality
    "causes": "causality", "caused_by": "causality", "results_in": "causality",
    # participation / hook
    "participates_in": "participation", "present_at": "participation",
    "attends": "participation", "mission_targets": "hook_relation",
    "mission_focus": "hook_relation", "pursues": "hook_relation",
    "objective_of": "hook_relation",
    # identity / alias
    "same_as": "identity", "identified_as": "identity", "is_a": "identity",
    "alias_of": "alias", "also_known_as": "alias",
}

# Inverse verb pairs that name the same durable fact in opposite directions.
# Canonicalizing these collapses ``parent_of(A,B)`` and ``child_of(B,A)`` into a
# single directed edge.
INVERSE_VERBS: dict[str, str] = {
    "child_of": "parent_of",
    "parent_of": "parent_of",
}

# Families whose endpoints carry no inherent direction; matched as an unordered
# pair so a swapped ``A associated_with B`` / ``B associated_with A`` still pairs.
SYMMETRIC_FAMILIES: frozenset[str] = frozenset(
    {"social_relation", "alias", "identity"}
)

_ARTICLES = {"the", "a", "an"}
_HONORIFICS = {
    "private", "commander", "professor", "captain", "sergeant", "lieutenant",
    "lord", "lady", "sir", "dame", "mister", "mr", "mrs", "ms", "dr", "general",
    "king", "queen", "prince", "princess", "the",
}


# --------------------------------------------------------------------------- #
# Tolerant accessors (dict or dataclass)
# --------------------------------------------------------------------------- #

def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def node_type_of(node: Any) -> str:
    return str(_get(node, "node_type", _get(node, "kind", "")) or "")


def node_type_class(node_type: str | Any) -> str:
    """Coarse identity class for a node_type string (or node-like object)."""
    raw = node_type if isinstance(node_type, str) else node_type_of(node_type)
    raw = (raw or "").strip().lower()
    return NODE_TYPE_CLASS.get(raw, f"type:{raw}" if raw else "type:unknown")


def predicate_family(relationship_type: str) -> str:
    """Registry predicate family for a relationship verb (fallback ``rel:<verb>``)."""
    raw = (relationship_type or "").strip().lower()
    return PREDICATE_FAMILY.get(raw, f"rel:{raw}" if raw else "rel:unknown")


def normalize_label(value: str) -> str:
    """Casefold, drop articles/honorifics and punctuation, collapse whitespace."""
    if not value:
        return ""
    lowered = re.sub(r"[^a-z0-9 ]+", " ", value.lower())
    tokens = [t for t in lowered.split() if t]
    # strip leading articles/honorifics (rank prefixes carry no identity)
    while tokens and tokens[0] in _ARTICLES | _HONORIFICS:
        tokens.pop(0)
    return " ".join(tokens).strip()


def label_tokens(value: str) -> set[str]:
    norm = normalize_label(value)
    return {t for t in norm.split() if t and t not in _ARTICLES}


# --------------------------------------------------------------------------- #
# Evidence anchors & corpus refs
# --------------------------------------------------------------------------- #

def evidence_anchor_ids(obj: Any) -> set[str]:
    anchors: set[str] = set()
    for ref in _get(obj, "evidence_refs", []) or []:
        anchor = _get(ref, "source_anchor_id")
        if anchor:
            anchors.add(str(anchor))
    return anchors


def corpus_ref_identity(node: Any) -> tuple[str, str] | None:
    """Return (type_class, normalized_ref) when a node carries a corpus_ref.

    Used as a confirmation/boost during matching and as the strongest key for
    production cross-session merge when a hub_path is resolved.
    """
    cr = _get(node, "corpus_ref")
    if not cr:
        return None
    hub_path = _get(cr, "hub_path")
    ref_type = node_type_class(str(_get(cr, "type", "") or ""))
    if hub_path:
        return ("hub", str(hub_path).strip().lower())
    ref_id = _get(cr, "ref_id")
    if ref_id:
        return (ref_type, normalize_label(str(ref_id).replace("_", " ")))
    return None


# --------------------------------------------------------------------------- #
# Node matching
# --------------------------------------------------------------------------- #

def _label_similarity(a: str, b: str) -> float:
    na, nb = normalize_label(a), normalize_label(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.9
    ta, tb = label_tokens(a), label_tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    if inter == 0:
        return 0.0
    return inter / len(ta | tb)


def label_similarity(a: str, b: str) -> float:
    """Public label-similarity score in [0, 1] (normalized equality / overlap)."""
    return _label_similarity(a, b)


def node_match_score(a: Any, b: Any) -> float:
    """Continuous match score in [0, 1] for two node-like objects."""
    class_a, class_b = node_type_class(node_type_of(a)), node_type_class(node_type_of(b))
    class_ok = class_a == class_b
    # resolved corpus identity is decisive when both sides resolve equally
    ca, cb = corpus_ref_identity(a), corpus_ref_identity(b)
    if ca and cb and ca == cb:
        return 1.0
    lab = _label_similarity(str(_get(a, "label", "")), str(_get(b, "label", "")))
    anchors_overlap = bool(evidence_anchor_ids(a) & evidence_anchor_ids(b))
    score = 0.0
    if class_ok:
        score += 0.15
    score += 0.55 * lab
    # shared source anchor is a strong same-entity signal within a session; it is
    # the lever that rescues semantically-equal nodes whose phrasing diverges
    # (e.g. "converging hail storm" vs "approaching major storm").
    if anchors_overlap:
        score += 0.4
    # a class mismatch caps the score so unrelated kinds do not pair on a
    # coincidental shared token (e.g. character "Frank" vs item "Frank's bottle").
    if not class_ok:
        score = min(score, 0.45)
    return round(min(score, 1.0), 4)


def nodes_match(a: Any, b: Any, *, threshold: float = 0.6) -> bool:
    return node_match_score(a, b) >= threshold


# --------------------------------------------------------------------------- #
# Greedy global best-match assignment (fixes first-hit collisions)
# --------------------------------------------------------------------------- #

def best_match_assignment(
    gold_objs: Sequence[Any],
    cand_objs: Sequence[Any],
    score_fn: Callable[[Any, Any], float],
    *,
    threshold: float = 0.6,
) -> list[tuple[int, int, float]]:
    """Assign each gold object to at most one candidate by descending score.

    Returns ``(gold_index, cand_index, score)`` tuples. Scoring all pairs and
    assigning highest-first prevents the greedy first-hit collision where a
    broad gold label (``Mireward Reach``) consumes the candidate (``Mireward``)
    that a narrower gold label needed.
    """
    scored: list[tuple[float, int, int]] = []
    for gi, g in enumerate(gold_objs):
        for ci, c in enumerate(cand_objs):
            s = score_fn(g, c)
            if s >= threshold:
                scored.append((s, gi, ci))
    scored.sort(key=lambda t: (-t[0], t[1], t[2]))
    used_gold: set[int] = set()
    used_cand: set[int] = set()
    pairs: list[tuple[int, int, float]] = []
    for s, gi, ci in scored:
        if gi in used_gold or ci in used_cand:
            continue
        used_gold.add(gi)
        used_cand.add(ci)
        pairs.append((gi, ci, s))
    return pairs


# --------------------------------------------------------------------------- #
# Edge matching (endpoint-aware, inverse-aware)
# --------------------------------------------------------------------------- #

def _node_index(nodes: Sequence[Any]) -> dict[str, Any]:
    index: dict[str, Any] = {}
    for n in nodes:
        nid = _get(n, "node_id")
        if nid:
            index[str(nid)] = n
    return index


def _endpoint_nodes(edge: Any, node_index: Mapping[str, Any]) -> tuple[Any, Any]:
    return (
        node_index.get(str(_get(edge, "from_node_id", ""))),
        node_index.get(str(_get(edge, "to_node_id", ""))),
    )


def _canonical_endpoints(edge: Any, node_index: Mapping[str, Any]) -> tuple[Any, Any, str]:
    """Resolve endpoints and canonicalize direction for inverse verbs."""
    rel = str(_get(edge, "relationship_type", "") or "")
    family = predicate_family(rel)
    frm, to = _endpoint_nodes(edge, node_index)
    if INVERSE_VERBS.get(rel.lower()) and rel.lower() == "child_of":
        frm, to = to, frm
    return frm, to, family


def edge_match_score(
    gold_edge: Any,
    cand_edge: Any,
    gold_nodes_index: Mapping[str, Any],
    cand_nodes_index: Mapping[str, Any],
) -> float:
    """Score two edges by endpoint-node match and predicate-family agreement."""
    g_from, g_to, g_family = _canonical_endpoints(gold_edge, gold_nodes_index)
    c_from, c_to, c_family = _canonical_endpoints(cand_edge, cand_nodes_index)
    if g_from is None or g_to is None or c_from is None or c_to is None:
        return 0.0
    family_ok = g_family == c_family
    forward = min(node_match_score(g_from, c_from), node_match_score(g_to, c_to))
    backward = min(node_match_score(g_from, c_to), node_match_score(g_to, c_from))
    if g_family in SYMMETRIC_FAMILIES or c_family in SYMMETRIC_FAMILIES:
        endpoint_score = max(forward, backward)
    else:
        endpoint_score = forward
    if endpoint_score < 0.6:
        return 0.0
    # full credit only when family agrees; otherwise partial (relationship drift)
    return round(endpoint_score * (1.0 if family_ok else 0.6), 4)


# --------------------------------------------------------------------------- #
# Beat matching (anchor + involved-node overlap + title)
# --------------------------------------------------------------------------- #

def _involved_node_match_fraction(
    gold_beat: Any,
    cand_beat: Any,
    gold_nodes_index: Mapping[str, Any],
    cand_nodes_index: Mapping[str, Any],
) -> float:
    g_ids = [str(i) for i in (_get(gold_beat, "involved_node_ids", []) or [])]
    c_nodes = [cand_nodes_index.get(str(i)) for i in (_get(cand_beat, "involved_node_ids", []) or [])]
    c_nodes = [n for n in c_nodes if n is not None]
    if not g_ids:
        return 0.0
    matched = 0
    for gid in g_ids:
        g_node = gold_nodes_index.get(gid)
        if g_node is None:
            continue
        if any(nodes_match(g_node, cn) for cn in c_nodes):
            matched += 1
    return matched / len(g_ids)


def beat_match_score(
    gold_beat: Any,
    cand_beat: Any,
    gold_nodes_index: Mapping[str, Any] | None = None,
    cand_nodes_index: Mapping[str, Any] | None = None,
) -> float:
    title = _label_similarity(str(_get(gold_beat, "title", "")), str(_get(cand_beat, "title", "")))
    anchors = bool(evidence_anchor_ids(gold_beat) & evidence_anchor_ids(cand_beat))
    involved = 0.0
    if gold_nodes_index is not None and cand_nodes_index is not None:
        involved = _involved_node_match_fraction(
            gold_beat, cand_beat, gold_nodes_index, cand_nodes_index
        )
    score = 0.6 * title + 0.25 * involved + (0.15 if anchors else 0.0)
    return round(min(score, 1.0), 4)


# --------------------------------------------------------------------------- #
# Intra-graph dedup (production: cross-session merge prep)
# --------------------------------------------------------------------------- #

def canonical_node_key(node: Any) -> tuple[str, str]:
    """Strongest available merge key for a single node.

    Resolved corpus identity (hub_path or type+ref_id) wins; otherwise
    normalized label + type class.
    """
    cr = corpus_ref_identity(node)
    if cr is not None:
        return ("corpus", f"{cr[0]}::{cr[1]}")
    return (node_type_class(node_type_of(node)), normalize_label(str(_get(node, "label", ""))))


def canonical_edge_key(edge: Any, node_index: Mapping[str, Any]) -> tuple[str, str, str]:
    """Direction- and inverse-normalized merge key for a single edge."""
    frm, to, family = _canonical_endpoints(edge, node_index)
    frm_key = canonical_node_key(frm) if frm is not None else ("missing", str(_get(edge, "from_node_id", "")))
    to_key = canonical_node_key(to) if to is not None else ("missing", str(_get(edge, "to_node_id", "")))
    frm_s, to_s = "::".join(frm_key), "::".join(to_key)
    if family in SYMMETRIC_FAMILIES:
        frm_s, to_s = sorted((frm_s, to_s))
    return (family, frm_s, to_s)


def dedup_edges(edges: Sequence[Any], nodes: Sequence[Any]) -> dict[str, Any]:
    """Collapse exact + inverse-duplicate edges within one graph.

    Returns ``{"kept": [...], "merged": [(kept_edge_id, dropped_edge_id), ...]}``.
    The first edge seen for a canonical key is kept; later duplicates are
    reported as merged (e.g. ``parent_of`` kept, ``child_of`` dropped).
    """
    node_index = _node_index(nodes)
    seen: dict[tuple[str, str, str], Any] = {}
    kept: list[Any] = []
    merged: list[tuple[str, str]] = []
    for edge in edges:
        key = canonical_edge_key(edge, node_index)
        if key in seen:
            merged.append((str(_get(seen[key], "edge_id", "")), str(_get(edge, "edge_id", ""))))
            continue
        seen[key] = edge
        kept.append(edge)
    return {"kept": kept, "merged": merged}


def dedup_nodes(nodes: Sequence[Any]) -> dict[str, Any]:
    """Collapse nodes that share a canonical merge key within one graph."""
    seen: dict[tuple[str, str], Any] = {}
    kept: list[Any] = []
    merged: list[tuple[str, str]] = []
    for node in nodes:
        key = canonical_node_key(node)
        if key in seen:
            merged.append((str(_get(seen[key], "node_id", "")), str(_get(node, "node_id", ""))))
            continue
        seen[key] = node
        kept.append(node)
    return {"kept": kept, "merged": merged}


def node_index(nodes: Sequence[Any]) -> dict[str, Any]:
    """Public alias for building a node_id -> node lookup."""
    return _node_index(nodes)
