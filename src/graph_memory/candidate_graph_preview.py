from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Mapping

CANDIDATE_GRAPH_PREVIEW_SCHEMA = "dmb_candidate_graph_preview_v0"
CANDIDATE_GRAPH_PREVIEW_VERSION = "0.1"

CANON_STATES = {
    "played_canon",
    "planning_scaffold",
    "worldbuilding_draft",
    "candidate_extraction",
    "diagnostic_only",
    "unknown",
}
LIFECYCLE_STATES = {"candidate", "validated", "promoted", "rejected", "stale", "diagnostic", "deferred", "ignored"}
EVIDENCE_ROLES = {"source_evidence", "navigation_hint", "diagnostic_only", "not_evidence"}
AUTHORITY_STATES = {"played_truth", "gm_prep", "system_derived", "llm_generated", "diagnostic", "unknown"}
VISIBILITY_STATES = {"gm_private", "player_visible", "internal_diagnostic", "spoiler_sensitive", "unknown"}
NODE_TYPES = {"character", "location", "item", "faction", "organization", "event", "session_beat", "clue", "thread", "mystery", "group", "warning", "promise", "debt", "rumor", "unknown_important", "combat_encounter", "quest", "landmark", "creature"}
WRITE_TYPES = {"create_node", "update_node", "create_edge", "attach_fact", "mark_ignored", "defer"}
WRITE_STATUSES = {"pending", "approved", "rejected", "deferred"}
PREVIEW_STATUSES = {"preview", "approved", "partially_approved", "rejected", "deferred"}
COMMITTED_ACTIONS = {"promote", "promoted", "commit", "committed", "approve", "approved", "write", "written"}
# corpus_ref lets an entity node resolve to (or propose) a live corpus index item
# (npc/location/etc.), so candidate-graph output is consumable by the command-board
# reference-chip resolver. resolution="resolved" => ref_id should match a live index
# key; resolution="proposed" => no corpus entity yet (pairs with a proposed_write).
CORPUS_REF_TYPES = {"npc", "pc", "location", "sublocation", "region", "faction", "creature", "item", "statblock", "roll-table"}
CORPUS_REF_RESOLUTIONS = {"resolved", "proposed"}

@dataclass(frozen=True)
class CorpusRef:
    type: str
    ref_id: str
    resolution: str = "resolved"
    hub_path: str | None = None

@dataclass(frozen=True)
class AnchorQuoteMatch:
    quote: str
    char_start: int
    char_end: int
    match_text: str

@dataclass(frozen=True)
class EvidenceRef:
    source_ref_id: str
    source_artifact_id: str
    source_anchor_id: str | None = None
    label: str | None = None
    evidence_role: str = "source_evidence"
    can_open_source: bool = False
    can_highlight_span: bool = False
    source_span_ref_id: str | None = None
    anchor_quotes: tuple[str, ...] = ()
    anchor_quote_matches: tuple[AnchorQuoteMatch, ...] = ()

@dataclass(frozen=True)
class SemanticState:
    canon_state: str
    lifecycle_state: str
    evidence_role: str
    authority_state: str
    visibility_state: str

@dataclass(frozen=True)
class CandidateNode:
    node_id: str
    label: str
    node_type: str
    description: str | None
    importance: str
    semantic_state: SemanticState
    evidence_refs: tuple[EvidenceRef, ...]
    proposed_action: str
    confidence: str
    warnings: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    corpus_ref: CorpusRef | None = None
    session_actions: tuple[str, ...] = ()
    enriched_by: str | None = None

@dataclass(frozen=True)
class CandidateEdge:
    edge_id: str
    from_node_id: str
    to_node_id: str
    label: str
    relationship_type: str
    semantic_state: SemanticState
    evidence_refs: tuple[EvidenceRef, ...]
    proposed_action: str
    confidence: str
    warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class SessionBeat:
    beat_id: str
    order: int
    title: str
    summary: str
    involved_node_ids: tuple[str, ...]
    evidence_refs: tuple[EvidenceRef, ...]
    unresolved_thread_node_ids: tuple[str, ...] = ()
    proposed_action: str = "create"
    warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class ProposedWrite:
    write_id: str
    write_type: str
    target_id: str
    label: str
    reason: str
    evidence_refs: tuple[EvidenceRef, ...]
    status: str = "pending"

@dataclass(frozen=True)
class IgnoredItem:
    item_id: str
    label: str
    reason: str
    evidence_refs: tuple[EvidenceRef, ...]
    warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class DeferredItem:
    item_id: str
    label: str
    reason: str
    evidence_refs: tuple[EvidenceRef, ...]
    suggested_next_step: str | None = None
    warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class PreviewDiagnostics:
    preview_only: bool
    extraction_performed: bool
    llm_used: bool
    runtime_connected: bool
    plan_connected: bool
    agent_interaction_connected: bool
    corpus_scanned: bool
    corpus_mutated: bool
    facts_promoted: bool
    canon_promoted: bool
    unresolved_evidence_refs: int
    missing_evidence_objects: int
    warning_count: int

@dataclass(frozen=True)
class CandidateGraphPreview:
    schema: str
    version: str
    preview_id: str
    campaign_id: str | None
    session_id: str | None
    source_artifact_ids: tuple[str, ...]
    status: str
    nodes: tuple[CandidateNode, ...]
    edges: tuple[CandidateEdge, ...]
    beats: tuple[SessionBeat, ...]
    proposed_writes: tuple[ProposedWrite, ...]
    ignored_items: tuple[IgnoredItem, ...]
    deferred_items: tuple[DeferredItem, ...]
    diagnostics: PreviewDiagnostics

@dataclass(frozen=True)
class CandidateGraphPreviewIssue:
    severity: str
    code: str
    message: str
    object_id: str | None = None
    field: str | None = None

@dataclass(frozen=True)
class CandidateGraphPreviewValidationReport:
    schema: str
    version: str
    preview_id: str
    total_nodes: int
    total_edges: int
    total_beats: int
    total_proposed_writes: int
    total_ignored_items: int
    total_deferred_items: int
    evidence_ref_count: int
    resolvable_evidence_ref_count: int
    unresolved_evidence_ref_count: int
    issue_counts: Mapping[str, int]
    issues: tuple[CandidateGraphPreviewIssue, ...]

def semantic_state_from_dict(data: Mapping[str, Any]) -> SemanticState: return SemanticState(**data)
def semantic_state_to_dict(state: SemanticState) -> dict[str, Any]: return asdict(state)

def anchor_quote_match_from_dict(data: Mapping[str, Any]) -> AnchorQuoteMatch:
    return AnchorQuoteMatch(
        quote=str(data["quote"]),
        char_start=int(data["char_start"]),
        char_end=int(data["char_end"]),
        match_text=str(data["match_text"]),
    )

def anchor_quote_match_to_dict(match: AnchorQuoteMatch) -> dict[str, Any]:
    return asdict(match)

def evidence_ref_from_dict(data: Mapping[str, Any]) -> EvidenceRef:
    anchor_quotes = tuple(
        str(x).strip() for x in (data.get("anchor_quotes") or []) if str(x).strip()
    )
    raw_matches = data.get("anchor_quote_matches") or []
    anchor_quote_matches = tuple(
        anchor_quote_match_from_dict(m) for m in raw_matches if isinstance(m, Mapping)
    )
    return EvidenceRef(
        source_ref_id=str(data["source_ref_id"]),
        source_artifact_id=str(data["source_artifact_id"]),
        source_anchor_id=data.get("source_anchor_id"),
        label=data.get("label"),
        evidence_role=str(data.get("evidence_role") or "source_evidence"),
        can_open_source=bool(data.get("can_open_source")),
        can_highlight_span=bool(data.get("can_highlight_span")),
        source_span_ref_id=data.get("source_span_ref_id"),
        anchor_quotes=anchor_quotes,
        anchor_quote_matches=anchor_quote_matches,
    )

def evidence_ref_to_dict(ref: EvidenceRef) -> dict[str, Any]: return asdict(ref)
def corpus_ref_from_dict(data: Mapping[str, Any] | None) -> CorpusRef | None: return CorpusRef(**data) if data else None

def _refs(items: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...]) -> tuple[EvidenceRef, ...]:
    return tuple(evidence_ref_from_dict(x) for x in items)

def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

def candidate_node_from_dict(data: Mapping[str, Any]) -> CandidateNode:
    return CandidateNode(
        node_id=str(data["node_id"]),
        label=str(data["label"]),
        node_type=str(data["node_type"]),
        description=data.get("description"),
        importance=str(data["importance"]),
        semantic_state=semantic_state_from_dict(data["semantic_state"]),
        evidence_refs=_refs(data.get("evidence_refs", ())),
        proposed_action=str(data["proposed_action"]),
        confidence=str(data["confidence"]),
        warnings=tuple(data.get("warnings", ())),
        aliases=tuple(str(a).strip() for a in (data.get("aliases") or ()) if str(a).strip()),
        corpus_ref=corpus_ref_from_dict(data.get("corpus_ref")),
        session_actions=tuple(str(a).strip() for a in (data.get("session_actions") or ()) if str(a).strip()),
        enriched_by=_optional_str(data.get("enriched_by")),
    )

def candidate_graph_preview_from_dict(data: Mapping[str, Any]) -> CandidateGraphPreview:
    return CandidateGraphPreview(
        schema=data["schema"], version=data["version"], preview_id=data["preview_id"],
        campaign_id=data.get("campaign_id"), session_id=data.get("session_id"),
        source_artifact_ids=tuple(data.get("source_artifact_ids", ())), status=data["status"],
        nodes=tuple(candidate_node_from_dict(n) for n in data.get("nodes", ())),
        edges=tuple(CandidateEdge(**{**e, "semantic_state": semantic_state_from_dict(e["semantic_state"]), "evidence_refs": _refs(e.get("evidence_refs", ())), "warnings": tuple(e.get("warnings", ()))}) for e in data.get("edges", ())),
        beats=tuple(SessionBeat(**{**b, "involved_node_ids": tuple(b.get("involved_node_ids", ())), "evidence_refs": _refs(b.get("evidence_refs", ())), "unresolved_thread_node_ids": tuple(b.get("unresolved_thread_node_ids", ())), "warnings": tuple(b.get("warnings", ()))}) for b in data.get("beats", ())),
        proposed_writes=tuple(ProposedWrite(**{**w, "evidence_refs": _refs(w.get("evidence_refs", ()))}) for w in data.get("proposed_writes", ())),
        ignored_items=tuple(IgnoredItem(**{**i, "evidence_refs": _refs(i.get("evidence_refs", ())), "warnings": tuple(i.get("warnings", ()))}) for i in data.get("ignored_items", ())),
        deferred_items=tuple(DeferredItem(**{**d, "evidence_refs": _refs(d.get("evidence_refs", ())), "warnings": tuple(d.get("warnings", ()))}) for d in data.get("deferred_items", ())),
        diagnostics=PreviewDiagnostics(**data["diagnostics"]),
    )

def candidate_graph_preview_to_dict(preview: CandidateGraphPreview) -> dict[str, Any]: return asdict(preview)

def _all_refs(p: CandidateGraphPreview) -> tuple[EvidenceRef, ...]:
    refs=[]
    for seq in (p.nodes,p.edges,p.beats,p.proposed_writes,p.ignored_items,p.deferred_items):
        for o in seq: refs.extend(o.evidence_refs)
    return tuple(refs)

def validate_candidate_graph_preview(preview: CandidateGraphPreview) -> CandidateGraphPreviewValidationReport:
    issues=[]
    def add(code,msg,obj=None,field=None,severity="error"): issues.append(CandidateGraphPreviewIssue(severity,code,msg,obj,field))
    if preview.schema != CANDIDATE_GRAPH_PREVIEW_SCHEMA: add("invalid_semantic_state","schema mismatch",preview.preview_id,"schema")
    if preview.version != CANDIDATE_GRAPH_PREVIEW_VERSION: add("invalid_semantic_state","version mismatch",preview.preview_id,"version")
    if preview.status != "preview" or preview.status not in PREVIEW_STATUSES: add("invalid_preview_status","preview status must be preview",preview.preview_id,"status")
    if not preview.preview_id: add("invalid_preview_status","preview_id must be non-empty",None,"preview_id")
    def dup(ids, code):
        for k,c in Counter(ids).items():
            if c>1: add(code,f"duplicate id: {k}",k)
    dup([n.node_id for n in preview.nodes],"duplicate_node_id"); dup([e.edge_id for e in preview.edges],"duplicate_edge_id"); dup([b.beat_id for b in preview.beats],"duplicate_beat_id"); dup([w.write_id for w in preview.proposed_writes],"duplicate_write_id")
    item_ids=[i.item_id for i in preview.ignored_items]+[d.item_id for d in preview.deferred_items]; dup(item_ids,"duplicate_write_id")
    node_ids={n.node_id for n in preview.nodes}; target_ids=node_ids|{e.edge_id for e in preview.edges}|{b.beat_id for b in preview.beats}|set(item_ids)
    for e in preview.edges:
        if e.from_node_id not in node_ids: add("missing_edge_endpoint","from_node_id missing",e.edge_id,"from_node_id")
        if e.to_node_id not in node_ids: add("missing_edge_endpoint","to_node_id missing",e.edge_id,"to_node_id")
    for b in preview.beats:
        if b.order <= 0: add("invalid_semantic_state","beat order must be positive",b.beat_id,"order")
        for nid in b.involved_node_ids + b.unresolved_thread_node_ids:
            if nid not in node_ids: add("missing_beat_node","beat node missing",b.beat_id,"involved_node_ids")
    for w in preview.proposed_writes:
        if w.target_id not in target_ids: add("missing_write_target","write target missing",w.write_id,"target_id")
        if w.status != "pending" or w.status not in WRITE_STATUSES: add("committed_write_forbidden","write status must remain pending",w.write_id,"status")
        if w.write_type not in WRITE_TYPES: add("invalid_semantic_state","invalid write_type",w.write_id,"write_type")
    for n in preview.nodes:
        if n.node_type not in NODE_TYPES: add("invalid_semantic_state","invalid node_type",n.node_id,"node_type")
        if n.corpus_ref is not None:
            cr=n.corpus_ref
            if cr.type not in CORPUS_REF_TYPES: add("invalid_corpus_ref","invalid corpus_ref type",n.node_id,"corpus_ref.type")
            if cr.resolution not in CORPUS_REF_RESOLUTIONS: add("invalid_corpus_ref","invalid corpus_ref resolution",n.node_id,"corpus_ref.resolution")
            if not cr.ref_id: add("invalid_corpus_ref","corpus_ref.ref_id must be non-empty",n.node_id,"corpus_ref.ref_id")
    for obj in list(preview.nodes)+list(preview.edges):
        s=obj.semantic_state
        if s.canon_state not in CANON_STATES or s.lifecycle_state not in LIFECYCLE_STATES or s.evidence_role not in EVIDENCE_ROLES or s.authority_state not in AUTHORITY_STATES or s.visibility_state not in VISIBILITY_STATES: add("invalid_semantic_state","invalid semantic state",getattr(obj,"node_id",getattr(obj,"edge_id",None)),"semantic_state")
        if s.lifecycle_state == "promoted": add("promoted_lifecycle_forbidden","promoted lifecycle forbidden",getattr(obj,"node_id",getattr(obj,"edge_id",None)),"semantic_state.lifecycle_state")
        if obj.proposed_action in COMMITTED_ACTIONS: add("committed_write_forbidden","committed action forbidden",getattr(obj,"node_id",getattr(obj,"edge_id",None)),"proposed_action")
    for seq in (preview.nodes,preview.edges,preview.beats,preview.proposed_writes):
        for obj in seq:
            if not obj.evidence_refs: add("missing_evidence_ref","missing evidence refs",getattr(obj,"node_id",getattr(obj,"edge_id",getattr(obj,"beat_id",getattr(obj,"write_id",None)))),"evidence_refs")
    for ref in _all_refs(preview):
        if not ref.can_open_source: add("unopenable_evidence_ref","evidence ref must be openable",ref.source_ref_id,"can_open_source")
        if ref.evidence_role == "source_evidence" and not ref.can_highlight_span: add("unhighlightable_source_evidence","source evidence must be highlightable",ref.source_ref_id,"can_highlight_span")
    d=preview.diagnostics
    if not d.preview_only or any([d.extraction_performed,d.llm_used,d.runtime_connected,d.plan_connected,d.agent_interaction_connected,d.corpus_scanned,d.corpus_mutated,d.facts_promoted,d.canon_promoted]): add("dangerous_diagnostic_flag","dangerous diagnostic flag",preview.preview_id,"diagnostics")
    counts=dict(Counter(i.code for i in issues))
    refs=_all_refs(preview)
    unresolved=sum(1 for r in refs if not r.can_open_source)
    return CandidateGraphPreviewValidationReport(preview.schema, preview.version, preview.preview_id, len(preview.nodes), len(preview.edges), len(preview.beats), len(preview.proposed_writes), len(preview.ignored_items), len(preview.deferred_items), len(refs), len(refs)-unresolved, unresolved, counts, tuple(issues))
