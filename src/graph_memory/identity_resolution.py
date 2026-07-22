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
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence

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
    "route": "place", "hub": "place", "landmark": "place",
    # landmark = notable physical/environmental feature (structural damage,
    # ambiguous monuments, terrain waypoints) distinct from a full location;
    # folded into "place" since it is still physical and locatable.
    # unresolved / narrative threads
    "mystery": "thread", "clue": "thread", "thread": "thread", "rumor": "thread",
    "promise": "thread", "debt": "thread", "hook": "thread", "quest": "thread",
    "unknown_important": "thread", "threat": "thread",
    # phenomena / temporal
    "event": "phenomenon", "warning": "phenomenon", "session": "phenomenon",
    "campaign": "phenomenon", "phenomenon": "phenomenon",
    "unresolved_phenomenon": "phenomenon", "combat_encounter": "phenomenon",
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
    "road_to": "routing", "path_to": "routing", "displaced_from": "routing",
    # threat / antagonism
    "threatens": "threat_relation", "besieges": "threat_relation",
    "attacks": "threat_relation",
    # membership
    "member_of": "membership", "belongs_to": "membership", "serves": "membership",
    "recruits_for": "membership", "part_of_group": "membership",
    # authority
    "governs": "authority", "commands": "authority", "hires": "authority",
    "reports_to": "authority", "carries_report_to": "authority", "rules": "authority",
    "leads": "authority",
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


def evidence_line_spans(obj: Any) -> set[tuple[int, int]]:
    """Resolved source line spans ``(start, end)`` carried on evidence refs.

    Parallels :func:`evidence_anchor_ids`: where two independently-authored
    graphs cite the same source location via *different* addressing schemes —
    gold via curated ``source_anchor_id``, an autonomous extractor via
    paragraph ``source_span_ref_id`` — both still resolve to the same line
    range. Exposing that range lets the matcher use span overlap as the
    same-entity rescue signal even when anchor strings cannot align.
    """
    spans: set[tuple[int, int]] = set()
    for ref in _get(obj, "evidence_refs", []) or []:
        start = _get(ref, "source_line_start")
        end = _get(ref, "source_line_end", start)
        if start is None:
            continue
        try:
            s, e = int(start), int(end if end is not None else start)
        except (TypeError, ValueError):
            continue
        spans.add((s, e) if s <= e else (e, s))
    return spans


def _line_spans_overlap(a: set[tuple[int, int]], b: set[tuple[int, int]]) -> bool:
    for (as_, ae) in a:
        for (bs, be) in b:
            if as_ <= be and bs <= ae:
                return True
    return False


def _fold_plural(token: str) -> str:
    """Light singular/plural fold so storm/storms, puddle/puddles, reflection/
    reflections collapse. Only trims a trailing 's' on tokens long enough that
    the fold cannot butcher a genuinely short word (e.g. 'is', 'as')."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _shared_content_tokens(a: str, b: str) -> set[str]:
    ta = {_fold_plural(t) for t in label_tokens(a)}
    tb = {_fold_plural(t) for t in label_tokens(b)}
    return ta & tb


def _span_overlap_supported(a: Any, b: Any) -> bool:
    """Whether a paragraph-level span overlap may grant the same-source boost.

    A paragraph can name several distinct entities, so span overlap alone is not
    enough: require a substring label relationship or at least two shared content
    tokens. This blocks the failure where two distinct "...Reach" places in one
    paragraph pair on the single generic token "reach", while still rescuing
    multi-token paraphrases ("unseen knocking door" vs "knocking on a door that
    cannot be found")."""
    la, lb = str(_get(a, "label", "")), str(_get(b, "label", ""))
    na, nb = normalize_label(la), normalize_label(lb)
    if na and nb and (na in nb or nb in na):
        return True
    return len(_shared_content_tokens(la, lb)) >= 2


def corpus_ref_identity(node: Any) -> tuple[str, str] | None:
    """Return (type_class, normalized_ref) when a node carries a corpus_ref.

    Used as a confirmation/boost during matching and as the strongest key for
    production cross-session merge when a hub_path is resolved.
    """
    cr = _get(node, "corpus_ref")
    if not cr:
        return None
    hub_path = _get(cr, "hub_path")
    ref_id = _get(cr, "ref_id")
    ref_type = node_type_class(str(_get(cr, "type", "") or ""))
    # ``ref_id`` is the entity-specific slug; ``hub_path`` is only where the docs
    # live. A single location/collection hub (e.g. Mireward) is the documentation
    # home for many distinct sub-entities (North gate, townspeople, the city
    # itself), each with its own ``ref_id``. Keying on ``hub_path`` alone collapses
    # all of them into one node — silent cross-session corruption that compounds
    # per ingested session. Pair ``hub_path`` WITH ``ref_id`` so a multi-entity hub
    # splits correctly, while a single-entity hub (one NPC = one ref_id, identical
    # across sessions) still merges. The failure mode degrades to fail-to-merge
    # (visible duplicate, recoverable) — never false-merge (silent entity loss).
    hub = str(hub_path).strip().lower() if hub_path else ""
    ref = str(ref_id).strip().lower() if ref_id else ""
    if hub and ref:
        return ("hub", f"{hub}::{ref}")
    if hub:
        return ("hub", hub)
    if ref:
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
    # span overlap is the addressing-scheme-agnostic form of the anchor signal:
    # gold cites a curated source_anchor_id, an autonomous extractor cites a
    # paragraph source_span_ref_id, but both resolve to the same line range.
    spans_overlap = _line_spans_overlap(evidence_line_spans(a), evidence_line_spans(b))
    # Shared source location rescues semantically-equal nodes whose phrasing
    # diverges (e.g. "converging hail storm" vs "approaching major storm"). A
    # curated source_anchor_id pins the exact claim and earns the boost
    # outright; a paragraph-level span is coarser (one paragraph can name
    # several distinct entities), so it earns the boost only when the labels
    # also share a substring or >=2 content tokens — blocking the two-distinct-
    # "...Reach"-places-in-one-paragraph false pair.
    same_source = anchors_overlap or (spans_overlap and _span_overlap_supported(a, b))
    score = 0.0
    if class_ok:
        score += 0.15
    score += 0.55 * lab
    if same_source:
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


def _edge_predicate_family(edge: Any) -> str:
    explicit = _get(edge, "predicate_family", None)
    if explicit:
        return str(explicit).strip()
    rel = str(_get(edge, "relationship_type", "") or "")
    return predicate_family(rel)


def _canonical_endpoints(edge: Any, node_index: Mapping[str, Any]) -> tuple[Any, Any, str]:
    """Resolve endpoints and canonicalize direction for inverse verbs."""
    rel = str(_get(edge, "relationship_type", "") or "")
    family = _edge_predicate_family(edge)
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


def _edge_endpoint_score(
    gold_edge: Any,
    cand_edge: Any,
    gold_nodes_index: Mapping[str, Any],
    cand_nodes_index: Mapping[str, Any],
) -> tuple[float, str, str, str, str]:
    """Return endpoint score and predicate metadata for diagnostics."""
    g_from, g_to, g_family = _canonical_endpoints(gold_edge, gold_nodes_index)
    c_from, c_to, c_family = _canonical_endpoints(cand_edge, cand_nodes_index)
    g_rel = str(_get(gold_edge, "relationship_type", "") or "")
    c_rel = str(_get(cand_edge, "relationship_type", "") or "")
    if g_from is None or g_to is None or c_from is None or c_to is None:
        return 0.0, g_family, c_family, g_rel, c_rel
    forward = min(node_match_score(g_from, c_from), node_match_score(g_to, c_to))
    backward = min(node_match_score(g_from, c_to), node_match_score(g_to, c_from))
    if g_family in SYMMETRIC_FAMILIES or c_family in SYMMETRIC_FAMILIES:
        endpoint_score = max(forward, backward)
    else:
        endpoint_score = forward
    return endpoint_score, g_family, c_family, g_rel, c_rel


def classify_edge_alignment(
    gold_edge: Any,
    live_edge: Any,
    gold_nodes_index: Mapping[str, Any],
    cand_nodes_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify how a gold edge aligns with a live edge candidate."""
    edge_id = str(_get(gold_edge, "edge_id", "") or "")
    live_edge_id = str(_get(live_edge, "edge_id", "") or "")
    g_from, g_to, g_family = _canonical_endpoints(gold_edge, gold_nodes_index)
    if g_from is None or g_to is None:
        return {
            "edge_id": edge_id,
            "reason": "endpoint_missing",
            "detail": "gold edge endpoint not resolved in gold node index",
            "gold_relationship_type": str(_get(gold_edge, "relationship_type", "") or ""),
            "gold_predicate_family": g_family,
        }

    endpoint_score, g_family, c_family, g_rel, c_rel = _edge_endpoint_score(
        gold_edge,
        live_edge,
        gold_nodes_index,
        cand_nodes_index,
    )
    score = edge_match_score(gold_edge, live_edge, gold_nodes_index, cand_nodes_index)
    base = {
        "edge_id": edge_id,
        "best_live_edge_id": live_edge_id,
        "best_score": score,
        "endpoint_score": round(endpoint_score, 4),
        "gold_relationship_type": g_rel,
        "gold_predicate_family": g_family,
        "live_relationship_type": c_rel,
        "live_predicate_family": c_family,
    }
    c_from, c_to, _ = _canonical_endpoints(live_edge, cand_nodes_index)
    if c_from is None or c_to is None:
        return {
            **base,
            "reason": "endpoint_missing",
            "detail": "live edge endpoint not resolved in live node index",
        }
    if endpoint_score < 0.6:
        return {
            **base,
            "reason": "endpoint_score_below_threshold",
            "detail": "live edge endpoints do not align with gold endpoints",
        }
    if g_family != c_family:
        return {
            **base,
            "reason": "family_mismatch",
            "detail": "relationship predicate family differs between gold and live",
        }
    if g_rel.strip().lower() != c_rel.strip().lower():
        return {
            **base,
            "reason": "exact_predicate_mismatch",
            "detail": "predicate family matches but exact relationship_type differs",
        }
    return {
        **base,
        "reason": "aligned",
        "detail": "gold and live edges align on endpoints and predicate",
    }


def explain_edge_miss(
    gold_edge: Any,
    live_edges: Sequence[Any],
    gold_nodes_index: Mapping[str, Any],
    cand_nodes_index: Mapping[str, Any],
    *,
    threshold: float = 0.6,
) -> dict[str, Any]:
    """Explain why a gold edge has no live match at or above ``threshold``."""
    edge_id = str(_get(gold_edge, "edge_id", "") or "")
    g_from, g_to, g_family = _canonical_endpoints(gold_edge, gold_nodes_index)
    if g_from is None or g_to is None:
        return {
            "edge_id": edge_id,
            "reason": "endpoint_missing",
            "detail": "gold edge endpoint not resolved in gold node index",
            "gold_relationship_type": str(_get(gold_edge, "relationship_type", "") or ""),
            "gold_predicate_family": g_family,
        }
    if not live_edges:
        return {
            "edge_id": edge_id,
            "reason": "no_comparable_live_edge",
            "detail": "live graph has no edges",
            "gold_relationship_type": str(_get(gold_edge, "relationship_type", "") or ""),
            "gold_predicate_family": g_family,
        }

    best_score = -1.0
    best_edge: Any | None = None
    for cand in live_edges:
        score = edge_match_score(gold_edge, cand, gold_nodes_index, cand_nodes_index)
        if score > best_score:
            best_score = score
            best_edge = cand

    if best_edge is None:
        return {
            "edge_id": edge_id,
            "reason": "no_comparable_live_edge",
            "detail": "no live edge candidates available",
            "gold_relationship_type": str(_get(gold_edge, "relationship_type", "") or ""),
            "gold_predicate_family": g_family,
        }

    diagnosis = classify_edge_alignment(
        gold_edge,
        best_edge,
        gold_nodes_index,
        cand_nodes_index,
    )
    diagnosis["best_score"] = round(best_score, 4)
    if best_score >= threshold:
        diagnosis["reason"] = "matched_below_report_threshold"
        diagnosis["detail"] = "best live edge meets threshold but was not assigned"
    elif diagnosis["reason"] == "aligned":
        diagnosis["reason"] = "no_comparable_live_edge"
        diagnosis["detail"] = "no live edge met the comparison threshold"
    return diagnosis


def build_edge_miss_diagnostics(
    missing_gold_edge_ids: Sequence[str],
    gold_edges: Sequence[Any],
    live_edges: Sequence[Any],
    gold_nodes_index: Mapping[str, Any],
    cand_nodes_index: Mapping[str, Any],
    *,
    threshold: float = 0.6,
) -> dict[str, dict[str, Any]]:
    gold_by_id = {str(_get(edge, "edge_id", "")): edge for edge in gold_edges}
    out: dict[str, dict[str, Any]] = {}
    for edge_id in missing_gold_edge_ids:
        gold_edge = gold_by_id.get(edge_id)
        if gold_edge is None:
            continue
        out[edge_id] = explain_edge_miss(
            gold_edge,
            live_edges,
            gold_nodes_index,
            cand_nodes_index,
            threshold=threshold,
        )
    return out


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


# Preferred surviving type class when an exact-label collision spans classes.
# A proper noun extracted as both a place and a polity (e.g. "Mireward Reach"
# as ``location`` and ``organization``) should collapse to the more concrete
# kind; actors win over places, places over collectives, and so on. Threads /
# phenomena are least preferred so a thread label never swallows a concrete
# entity that happens to share its text.
_CROSS_CLASS_TYPE_PRIORITY: dict[str, int] = {
    "actor": 6,
    "place": 5,
    "collective": 4,
    "object": 3,
    "phenomenon": 2,
    "thread": 1,
}


def _cross_class_priority(node: Any) -> int:
    return _CROSS_CLASS_TYPE_PRIORITY.get(node_type_class(node_type_of(node)), 0)


_CROSS_CLASS_POLICY_VERSION = "cross_class_exact_label_policy_v0"

_CROSS_CLASS_POLICY_REASON_BY_CLASS_SET: dict[frozenset[str], str] = {
    frozenset({"place", "collective"}): "place_collective_exact_label",
    frozenset({"object", "place"}): "object_place_structure_pressure",
    frozenset({"collective", "object"}): "collective_object_role_pressure",
    frozenset({"collective", "object", "place"}): "collective_object_place_establishment_pressure",
    frozenset({"place", "thread"}): "place_thread_narrative_overlap",
    frozenset({"place", "phenomenon"}): "place_phenomenon_narrative_overlap",
}


def _class_set_policy_reason(classes: set[str]) -> str:
    explicit = _CROSS_CLASS_POLICY_REASON_BY_CLASS_SET.get(frozenset(classes))
    if explicit:
        return explicit
    if "actor" in classes:
        return "actor_cross_class_collision_high_risk"
    if "thread" in classes or "phenomenon" in classes:
        return "narrative_concrete_collision_high_risk"
    if "object" in classes and "place" in classes:
        return "object_place_structure_pressure"
    return "unsafe_cross_class_exact_label"


def _cross_class_collision_policy(classes: set[str]) -> dict[str, Any]:
    sorted_classes = sorted(classes)
    policy_reason = _class_set_policy_reason(classes)
    if classes == {"place", "collective"}:
        return {
            "action": "merge",
            "reason": "place_collective_exact_label",
            "policy_reason": policy_reason,
            "policy_version": _CROSS_CLASS_POLICY_VERSION,
            "classes": sorted_classes,
        }
    return {
        "action": "block",
        "reason": "unsafe_cross_class_exact_label",
        "policy_reason": policy_reason,
        "policy_version": _CROSS_CLASS_POLICY_VERSION,
        "classes": sorted_classes,
    }


def should_merge_cross_class_label_collision(members: Sequence[Any]) -> dict[str, Any]:
    """Return the conservative exact-label policy decision for a class collision.

    This intentionally only inspects coarse node type classes today. Future
    vocabulary work can extend this seam with aliases, do-not-merge decisions,
    evidence hints, or corpus authority without reopening the reconciliation
    loop itself.
    """
    classes = {node_type_class(node_type_of(member)) for member in members}
    return _cross_class_collision_policy(classes)


def _clean_cross_class_description(value: Any, *, max_chars: int = 180) -> str | None:
    text = str(value or "").replace("\n", " ").strip()
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _cross_class_member_summary(node: Any) -> dict[str, Any]:
    evidence_refs = _get(node, "evidence_refs", []) or []
    summary: dict[str, Any] = {
        "node_id": str(_get(node, "node_id", "") or ""),
        "label": str(_get(node, "label", "") or ""),
        "node_type": node_type_of(node),
        "type_class": node_type_class(node_type_of(node)),
        "evidence_count": len(evidence_refs) if isinstance(evidence_refs, Sequence) else 0,
    }
    description = _clean_cross_class_description(_get(node, "description", ""))
    if description:
        summary["description"] = description
    return summary


def _rewrite_node_id(node: Any, new_id: str) -> Any:
    """Best-effort in-place node_id rewrite for mapping/dataclass nodes."""
    if isinstance(node, MutableMapping):
        node["node_id"] = new_id
        return node
    if hasattr(node, "node_id"):
        try:
            setattr(node, "node_id", new_id)
            return node
        except Exception:
            pass
    return node


def _disambiguate_blocked_cross_class_ids(
    members: Sequence[Any],
) -> tuple[list[Any], list[tuple[str, str]]]:
    """Ensure blocked cross-class members keep distinct durable node_ids.

    Category passes often mint the same slug for a person and a mis-typed
    organization (``node:captain_lysandra_ironveil`` ×2). Blocking correctly
    refuses to merge them, but a shared id later collapses into one
    graph_object_id with disagreeing kinds and merge/projection fail closed.

    Higher-priority type class keeps the original id; others receive a
    ``:{node_type}`` suffix (with numeric fallback if still taken). Edges that
    already pointed at the shared id stay on the priority survivor — we cannot
    attribute shared-id edges to the renamed duplicate.
    """
    if len(members) <= 1:
        return list(members), []

    ordered = sorted(
        members,
        key=lambda m: (
            -_cross_class_priority(m),
            -len(_get(m, "evidence_refs", []) or []),
            str(_get(m, "node_id", "") or ""),
            node_type_of(m),
        ),
    )
    claimed: set[str] = set()
    rewritten: list[Any] = []
    renames: list[tuple[str, str]] = []
    for member in ordered:
        original_id = str(_get(member, "node_id", "") or "").strip()
        if not original_id:
            rewritten.append(member)
            continue
        if original_id not in claimed:
            claimed.add(original_id)
            rewritten.append(member)
            continue
        node_type = re.sub(r"[^a-z0-9]+", "_", node_type_of(member).strip().lower()).strip("_")
        suffix = node_type or "dup"
        candidate = f"{original_id}:{suffix}"
        n = 2
        while candidate in claimed:
            candidate = f"{original_id}:{suffix}:{n}"
            n += 1
        claimed.add(candidate)
        rewritten.append(_rewrite_node_id(member, candidate))
        renames.append((original_id, candidate))
    return rewritten, renames


def _merge_evidence_refs(into: Any, extra: Any) -> None:
    """Union ``extra``'s evidence_refs onto ``into`` (best-effort, dedup-by-repr)."""
    if not isinstance(into, Mapping):
        return
    base = list(into.get("evidence_refs") or [])
    seen = {json_safe_key(r) for r in base}
    for ref in _get(extra, "evidence_refs", []) or []:
        key = json_safe_key(ref)
        if key not in seen:
            base.append(ref)
            seen.add(key)
    if base:
        into["evidence_refs"] = base


def json_safe_key(value: Any) -> str:
    try:
        import json as _json

        return _json.dumps(value, sort_keys=True, default=str)
    except Exception:  # pragma: no cover - defensive
        return repr(value)


def reconcile_cross_class_label_collisions(
    nodes: Sequence[Any],
    edges: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Merge nodes whose *normalized labels are exactly equal* across type classes.

    The category extractor runs one observation pass per node type, so a single
    proper noun can surface as several nodes with different ``node_type`` values
    (e.g. "Mireward Reach" as a ``location`` AND an ``organization``).
    :func:`dedup_nodes` keys on ``(type_class, normalized_label)`` and therefore
    keeps both, which (a) inflates the node count and (b) makes downstream
    endpoint binding ``ambiguous`` — two equally scored targets for the same
    phrase — so the edge is dropped instead of matched.

    This step applies an explicit safety policy before collapsing exact-label
    collisions. Today only place/collective duplicates are approved to merge;
    other cross-class collisions stay separate and are surfaced in ``blocked``
    diagnostics. When blocked members share a durable ``node_id`` (common when
    category passes mint the same slug for a person and a mis-typed organization),
    lower-priority members are rewritten to ``:{node_type}`` so merge/projection
    do not see two kinds on one graph object. Approved merges still prefer the
    higher-priority type class (see ``_CROSS_CLASS_TYPE_PRIORITY``), union evidence
    refs onto the survivor, and rewrite any edge endpoints that referenced a
    dropped id. Self-loops created by approved merges are dropped.

    Conservative by construction: only policy-approved *byte-identical normalized
    labels* merge. The degradation direction is fail-to-merge with diagnostics,
    never false-merge of distinct identities.

    Returns ``{"kept", "edges", "merged", "remap", "blocked"}`` where ``merged``
    is a list of ``(survivor_id, dropped_id)`` pairs, ``remap`` maps dropped ids
    to survivor ids, and ``blocked`` lists unsafe exact-label class collisions.
    ``edges`` is ``None`` when no edge sequence was supplied.
    """
    groups: dict[str, list[Any]] = {}
    order: list[str] = []
    for node in nodes:
        label = normalize_label(str(_get(node, "label", "")))
        if not label:
            order.append(f"__empty__::{id(node)}")
            groups[order[-1]] = [node]
            continue
        if label not in groups:
            groups[label] = []
            order.append(label)
        groups[label].append(node)

    kept: list[Any] = []
    merged: list[tuple[str, str]] = []
    remap: dict[str, str] = {}
    blocked: list[dict[str, Any]] = []
    for key in order:
        members = groups.get(key) or []
        if not members:
            continue
        classes = {node_type_class(node_type_of(m)) for m in members}
        if len(members) == 1 or len(classes) <= 1:
            # Single node, or a same-class residue dedup_nodes already handles.
            kept.extend(members)
            continue
        policy = should_merge_cross_class_label_collision(members)
        if policy["action"] != "merge":
            distinct_members, id_renames = _disambiguate_blocked_cross_class_ids(members)
            sorted_members = sorted(
                distinct_members, key=lambda m: str(_get(m, "node_id", "") or "")
            )
            blocked_entry: dict[str, Any] = {
                "label": key,
                "node_ids": [str(_get(m, "node_id", "")) for m in sorted_members],
                "classes": policy["classes"],
                "reason": "unsafe_cross_class_exact_label",
                "policy_reason": policy["policy_reason"],
                "policy_version": _CROSS_CLASS_POLICY_VERSION,
                "member_summaries": [
                    _cross_class_member_summary(m) for m in sorted_members
                ],
            }
            if id_renames:
                blocked_entry["disambiguated_node_ids"] = [
                    {"from": old, "to": new} for old, new in id_renames
                ]
            blocked.append(blocked_entry)
            kept.extend(distinct_members)
            continue
        survivor = max(
            members,
            key=lambda m: (_cross_class_priority(m), len(_get(m, "evidence_refs", []) or [])),
        )
        survivor_id = str(_get(survivor, "node_id", ""))
        for m in members:
            if m is survivor:
                continue
            dropped_id = str(_get(m, "node_id", ""))
            _merge_evidence_refs(survivor, m)
            if dropped_id and dropped_id != survivor_id:
                remap[dropped_id] = survivor_id
                merged.append((survivor_id, dropped_id))
        kept.append(survivor)

    rewritten_edges: list[Any] | None = None
    if edges is not None:
        rewritten_edges = []
        for edge in edges:
            frm = remap.get(str(_get(edge, "from_node_id", "")), _get(edge, "from_node_id"))
            to = remap.get(str(_get(edge, "to_node_id", "")), _get(edge, "to_node_id"))
            if frm == to:
                continue  # merge collapsed both endpoints into a self-loop
            if isinstance(edge, MutableMapping):
                edge["from_node_id"] = frm
                edge["to_node_id"] = to
            rewritten_edges.append(edge)

    return {
        "kept": kept,
        "edges": rewritten_edges,
        "merged": merged,
        "remap": remap,
        "blocked": blocked,
    }
