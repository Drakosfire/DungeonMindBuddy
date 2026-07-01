"""Pure reporting helpers for blocked cross-class node collisions."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

REVIEW_ACTIONS = {
    "needs_human_review",
    "candidate_merge_policy",
    "candidate_keep_blocked",
    "candidate_new_node_type",
    "insufficient_context",
}


@dataclass(frozen=True)
class BlockedCollisionNodeRef:
    node_id: str
    label: str | None = None
    node_type: str | None = None
    type_class: str | None = None
    description: str | None = None
    evidence_count: int = 0
    source_span_refs: tuple[str, ...] = ()
    corpus_ref: str | None = None


@dataclass(frozen=True)
class BlockedCollisionRecord:
    bed_id: str
    variant: str
    label: str
    normalized_label: str
    classes: tuple[str, ...]
    reason: str
    node_ids: tuple[str, ...]
    nodes: tuple[BlockedCollisionNodeRef, ...]
    suggested_review_action: str
    review_notes: str


def _nested(mapping: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = mapping
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _blocked_nodes(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    paths = [
        ("consolidation_diagnostics", "cross_class_blocked_nodes"),
        ("extraction_run_diagnostics", "consolidation_diagnostics", "cross_class_blocked_nodes"),
        ("diagnostics", "consolidation_diagnostics", "cross_class_blocked_nodes"),
        ("cross_class_blocked_nodes",),
        ("run_diagnostics", "consolidation_diagnostics", "cross_class_blocked_nodes"),
    ]
    for path in paths:
        value = _nested(payload, path)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _node_items(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    paths = [
        ("nodes",),
        ("extracted_nodes",),
        ("candidate_graph", "nodes"),
        ("graph", "nodes"),
        ("extraction_run_diagnostics", "nodes"),
    ]
    for path in paths:
        value = _nested(payload, path)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _node_id(node: Mapping[str, Any]) -> str | None:
    for key in ("node_id", "id"):
        value = node.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _evidence_count(node: Mapping[str, Any]) -> int:
    for key in ("evidence_refs", "evidence", "source_spans", "source_span_refs"):
        value = node.get(key)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, tuple):
            return len(value)
    return 0


def _source_span_refs(node: Mapping[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for item in node.get("evidence_refs", ()) or ():
        if not isinstance(item, Mapping):
            continue
        if isinstance(item.get("source_anchor_id"), str):
            refs.append(item["source_anchor_id"])
        elif item.get("source_line_start") is not None:
            start = item.get("source_line_start")
            end = item.get("source_line_end", start)
            refs.append(f"L{start}-L{end}")
    return tuple(sorted(dict.fromkeys(refs)))


def _corpus_ref(node: Mapping[str, Any]) -> str | None:
    value = node.get("corpus_ref")
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("ref_id", "hub_path", "type"):
            if isinstance(value.get(key), str):
                return value[key]
    return None


def _node_ref(node: Mapping[str, Any], fallback_class: str | None = None) -> BlockedCollisionNodeRef | None:
    nid = _node_id(node)
    if not nid:
        return None
    return BlockedCollisionNodeRef(
        node_id=nid,
        label=node.get("label") if isinstance(node.get("label"), str) else None,
        node_type=node.get("node_type") if isinstance(node.get("node_type"), str) else node.get("entity_kind") if isinstance(node.get("entity_kind"), str) else None,
        type_class=node.get("type_class") if isinstance(node.get("type_class"), str) else fallback_class,
        description=node.get("description") if isinstance(node.get("description"), str) else None,
        evidence_count=_evidence_count(node),
        source_span_refs=_source_span_refs(node),
        corpus_ref=_corpus_ref(node),
    )


def _suggestion(classes: tuple[str, ...], nodes: tuple[BlockedCollisionNodeRef, ...]) -> tuple[str, str]:
    class_set = set(classes)
    if not nodes:
        return "insufficient_context", "Blocked diagnostics were present, but node details were unavailable in the payload."
    if "actor" in class_set:
        return "candidate_keep_blocked", "Actor-involved exact-label collisions are high-risk false-merge candidates."
    if class_set == {"collective", "place"}:
        return "candidate_merge_policy", "Place/collective collision is unexpected under current policy; verify before changing policy."
    if class_set == {"object", "place"}:
        return "candidate_new_node_type", "Object/place collisions often indicate structure or establishment modeling pressure; do not merge blindly."
    if ("thread" in class_set or "phenomenon" in class_set) and (class_set - {"thread", "phenomenon"}):
        return "candidate_keep_blocked", "Narrative thread or phenomenon labels can overlap concrete entities; keep blocked unless reviewed."
    return "needs_human_review", "Exact-label cross-class collision requires human review before any policy change."


def summarize_blocked_collision_records(*, bed_id: str, variant: str, extraction_payload: Mapping[str, Any]) -> list[BlockedCollisionRecord]:
    nodes_by_id = {nid: node for node in _node_items(extraction_payload) if (nid := _node_id(node))}
    records: list[BlockedCollisionRecord] = []
    for blocked in _blocked_nodes(extraction_payload):
        label = str(blocked.get("label") or "")
        normalized_label = str(blocked.get("normalized_label") or label).strip().lower()
        classes = tuple(sorted(str(c) for c in blocked.get("classes", ()) if c is not None))
        node_ids = tuple(str(nid) for nid in blocked.get("node_ids", ()) if nid is not None)
        node_refs = tuple(ref for nid in node_ids if (ref := _node_ref(nodes_by_id[nid], None) if nid in nodes_by_id else None))
        action, note = _suggestion(classes, node_refs)
        records.append(BlockedCollisionRecord(
            bed_id=bed_id or "unknown",
            variant=variant or "unknown",
            label=label,
            normalized_label=normalized_label,
            classes=classes,
            reason=str(blocked.get("reason") or "unknown"),
            node_ids=node_ids,
            nodes=node_refs,
            suggested_review_action=action,
            review_notes=note,
        ))
    return sorted(records, key=lambda r: (r.bed_id, r.variant, r.normalized_label, r.classes, r.node_ids))


def summarize_records_by_action(records: Sequence[BlockedCollisionRecord]) -> dict[str, int]:
    counts = Counter(record.suggested_review_action for record in records)
    return {action: counts[action] for action in sorted(counts)}


def _counts_by(records: Sequence[BlockedCollisionRecord], key) -> dict[str, int]:
    counts = Counter(key(record) for record in records)
    return {name: counts[name] for name in sorted(counts)}


def _escape(value: object) -> str:
    text = str(value).replace("|", "\\|").replace("\n", " ").strip()
    return text


def render_blocked_collision_markdown(
    records: Sequence[BlockedCollisionRecord],
    *,
    title: str = "Graph Memory Cross-Class Blocked Collision Diagnostics",
    source_note: str | None = None,
    generated_date: str | None = None,
) -> str:
    generated = generated_date or date.today().isoformat()
    ordered = sorted(records, key=lambda r: (r.bed_id, r.variant, r.normalized_label, r.classes, r.node_ids))
    lines: list[str] = [
        f"# {title}",
        "",
        "**Status:** Diagnostic report  ",
        f"**Generated:** {generated}  ",
        "**Scope:** Existing checked-in dogfood / extraction diagnostics only  ",
        "**Policy:** No merge-policy changes in this report",
        "",
        "**Purpose:** Review blocked exact-label cross-class collisions before changing merge policy.",
        "",
        "This report is a review surface for PR 03; it does not change identity resolution, merge policy, extraction prompts, candidate graph contracts, or corpus content.",
        "",
        "This report does not change merge policy.",
        "",
        "## Summary",
        "",
        f"- Total blocked collision records found: {len(ordered)}",
    ]
    if source_note:
        lines += [f"- Source note: {_escape(source_note)}"]
    for title_, counts in (
        ("Count by bed", _counts_by(ordered, lambda r: r.bed_id)),
        ("Count by suggested review action", summarize_records_by_action(ordered)),
        ("Count by class pair", _counts_by(ordered, lambda r: " + ".join(r.classes) or "unknown")),
    ):
        lines += [f"- {title_}:"]
        if counts:
            lines += [f"  - `{k}`: {v}" for k, v in counts.items()]
        else:
            lines += ["  - none"]
    if not ordered:
        lines += ["", "No checked-in blocked collision diagnostics found in the inspected payloads."]
    lines += [
        "",
        "## Review table",
        "",
        "| Bed | Variant | Label | Classes | Node IDs | Suggested review action | Human decision | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for record in ordered:
        lines.append(
            "| " + " | ".join([
                _escape(record.bed_id), _escape(record.variant), _escape(record.label),
                _escape(", ".join(record.classes)), _escape(", ".join(record.node_ids)),
                _escape(record.suggested_review_action), "TBD", _escape(record.review_notes),
            ]) + " |"
        )
    lines += ["", "## Records by bed", ""]
    if ordered:
        for bed, count in _counts_by(ordered, lambda r: r.bed_id).items():
            lines += [f"### {bed}", "", f"- Blocked records: {count}"]
            for record in [r for r in ordered if r.bed_id == bed]:
                lines.append(f"- `{record.variant}` / `{record.label}` / `{', '.join(record.classes)}` / `{record.suggested_review_action}`")
            lines.append("")
    else:
        lines.append("No records to group by bed.")
    lines += [
        "## Suggested human review actions",
        "",
        "- `needs_human_review`: default for cases where the diagnostic is not enough to classify safely.",
        "- `candidate_merge_policy`: possible future policy case, only after human confirmation.",
        "- `candidate_keep_blocked`: likely safer as a visible duplicate than a false merge.",
        "- `candidate_new_node_type`: may indicate taxonomy/pass design pressure rather than merge-policy pressure.",
        "- `insufficient_context`: blocked row exists, but node details were not available for review enrichment.",
        "",
        "## Manual review checklist",
        "",
        "- [ ] For each `candidate_merge_policy` row, confirm that the same label truly refers to one entity rather than two related concepts.",
        "- [ ] For each `candidate_keep_blocked` row, confirm that blocked duplication is preferable to false merge.",
        "- [ ] For each `candidate_new_node_type` row, decide whether the failure belongs to taxonomy/pass design rather than merge policy.",
        "- [ ] For every row involving an actor class, prefer keeping blocked unless there is explicit reviewed evidence.",
        "- [ ] Before PR 03, choose a tiny allowlist of policy cases; do not generalize from one attractive example.",
        "",
        "## Non-goals",
        "",
        "This report does not authorize:",
        "- changing `should_merge_cross_class_label_collision`;",
        "- changing `_CROSS_CLASS_TYPE_PRIORITY`;",
        "- changing node taxonomy;",
        "- changing extraction prompts;",
        "- mutating corpus files;",
        "- promoting graph memory to canon.",
        "",
        "## Next step",
        "",
        "PR 03 may use this report to implement a conservative cross-class merge-policy v0, but only for reviewed cases. False merges are worse than visible duplicates.",
        "",
    ]
    return "\n".join(lines)
