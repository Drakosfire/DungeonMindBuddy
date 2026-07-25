"""Read-only graph preview surface adapter for /plan toolbox projection."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.recap_artifacts import (
    GraphRunRef,
    RecapArtifactRecord,
    RecapArtifactRegistryError,
    ensure_recap_artifacts_registry,
    resolve_recap_artifact_record,
)
from src.graph_memory.anchor_quotes import (
    anchor_quote_matches_to_dicts,
    coerce_anchor_quotes,
    find_anchor_quote_matches,
    quote_found_in_paragraph,
)

GRAPH_PREVIEW_SURFACE_SCHEMA = "dmb_graph_preview_surface_v1"
GRAPH_PREVIEW_SURFACE_VERSION = "0.1"

GRAPH_PREVIEW_ARTIFACTS_ENV = "DUNGEONMIND_GRAPH_PREVIEW_ARTIFACTS_ROOT"
DEFAULT_ARTIFACTS_REL = "evals/graph_memory_layer/artifacts/category_graph_model_study"
LAST_COHORT_MIRROR_REL = "evals/artifacts/category_graph_model_study/last_cohort_summary.json"

CandidateSection = Literal["nodes", "edges", "beats", "ignored_items", "deferred_items"]

SECTION_ID_KEYS: dict[str, tuple[str, ...]] = {
    "nodes": ("node_id",),
    "edges": ("edge_id",),
    "beats": ("beat_id",),
    "ignored_items": ("item_id",),
    "deferred_items": ("item_id",),
}


class GraphPreviewSurfaceError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class AnchorQuoteMatchRow(BaseModel):
    quote: str
    char_start: int
    char_end: int
    match_text: str


class GraphPreviewEvidenceRef(BaseModel):
    source_ref_id: str | None = None
    source_artifact_id: str | None = None
    source_span_ref_id: str | None = None
    source_anchor_id: str | None = None
    label: str | None = None
    evidence_role: str | None = None
    can_open_source: bool = False
    can_highlight_span: bool = False
    anchor_quotes: list[str] = Field(default_factory=list)
    anchor_quote_matches: list[AnchorQuoteMatchRow] = Field(default_factory=list)
    paragraph_text: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    recap_source_path: str | None = None


class GraphPreviewCandidateRow(BaseModel):
    section: CandidateSection
    object_id: str
    label: str
    kind: str
    description: str | None = None
    importance: str | None = None
    evidence_count: int = 0
    evidence_refs: list[GraphPreviewEvidenceRef] = Field(default_factory=list)


class GraphPreviewHealth(BaseModel):
    canonical_ir_valid: bool = False
    reconcile_error: str | None = None
    node_count: int = 0
    edge_count: int = 0
    beat_count: int = 0
    ignored_count: int = 0
    deferred_count: int = 0
    evidence_ref_count: int = 0
    resolvable_evidence_ref_count: int = 0
    model_id: str | None = None
    scenario_estimated_cost_usd: float | None = None
    node_recall: float | None = None


class GraphPreviewRunSummary(BaseModel):
    run_dir: str
    model_id: str | None = None
    run_index: int | None = None
    canonical_ir_valid: bool | None = None
    scenario_estimated_cost_usd: float | None = None


class GraphPreviewSurfaceResponse(BaseModel):
    schema_version: Literal["dmb_graph_preview_surface_v1"] = GRAPH_PREVIEW_SURFACE_SCHEMA
    version: str = GRAPH_PREVIEW_SURFACE_VERSION
    run_dir: str
    run_bundle_dir: str | None = None
    recap_source_path: str | None = None
    health: GraphPreviewHealth
    candidates: list[GraphPreviewCandidateRow] = Field(default_factory=list)


class GraphPreviewRunsResponse(BaseModel):
    schema_version: Literal["dmb_graph_preview_surface_v1"] = GRAPH_PREVIEW_SURFACE_SCHEMA
    version: str = GRAPH_PREVIEW_SURFACE_VERSION
    runs: list[GraphPreviewRunSummary] = Field(default_factory=list)


class RecapGraphChip(BaseModel):
    label: str
    tone: Literal["new", "recurring", "evidence", "warning", "neutral"] = "neutral"
    source_session: int | None = None


class RecapGraphNode(BaseModel):
    object_id: str
    label: str
    kind: str
    role: str = "node"
    description: str | None = None
    evidence_count: int = 0
    chips: list[RecapGraphChip] = Field(default_factory=list)


class RecapGraphLink(BaseModel):
    href: str
    object_id: str
    label: str
    source_span_ref_id: str
    char_start: int
    char_end: int
    evidence_ref_ids: list[str] = Field(default_factory=list)


class RecapGraphPresentationResponse(BaseModel):
    schema_version: Literal["dmb_recap_graph_presentation_v1"] = "dmb_recap_graph_presentation_v1"
    version: str = GRAPH_PREVIEW_SURFACE_VERSION
    run_dir: str
    recap_source_path: str | None = None
    markdown: str
    nodes: dict[str, RecapGraphNode] = Field(default_factory=dict)
    links: list[RecapGraphLink] = Field(default_factory=list)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def artifacts_root(root: Path) -> Path:
    override = os.environ.get(GRAPH_PREVIEW_ARTIFACTS_ENV, "").strip()
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = root / candidate
        return candidate
    return root / DEFAULT_ARTIFACTS_REL


def _paragraph_text_for_span(recap_text: str, span: Mapping[str, Any]) -> str:
    lines = recap_text.splitlines()
    start = int(span.get("line_start") or span.get("start_line") or 0)
    end = int(span.get("line_end") or span.get("end_line") or 0)
    if start < 1 or end < start:
        return ""
    return "\n".join(lines[start - 1 : end])


def _span_lookup_key(span: Mapping[str, Any]) -> str | None:
    for key in ("source_span_ref_id", "source_span_id", "span_id"):
        value = span.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _recap_text_for_run_bundle(
    root: Path,
    run_bundle: Path,
    *,
    source_recap_path: str | None = None,
) -> tuple[str, str]:
    base = run_bundle if run_bundle.is_absolute() else root / run_bundle
    manifest = _load_json(base / "run_manifest.json")
    input_rel = (source_recap_path or str(manifest["source"]["input_path_record"])).replace("\\", "/")
    recap_path = Path(input_rel)
    if not recap_path.is_absolute():
        recap_path = root / recap_path
    if not recap_path.is_file():
        raise GraphPreviewSurfaceError(f"recap source not found: {input_rel}", status_code=404)
    return recap_path.read_text(encoding="utf-8"), input_rel


def _default_run_bundle_dir(root: Path) -> Path:
    ensure_recap_artifacts_registry(root)
    record = resolve_recap_artifact_record(root)
    return root / record.run_bundle_uri


def _graph_preview_run_summaries_from_refs(refs: list[GraphRunRef]) -> list[GraphPreviewRunSummary]:
    return [
        GraphPreviewRunSummary(
            run_dir=ref.run_uri,
            model_id=ref.model_id,
            run_index=ref.run_index,
            canonical_ir_valid=ref.canonical_ir_valid,
            scenario_estimated_cost_usd=ref.scenario_estimated_cost_usd,
        )
        for ref in refs
    ]


def _resolve_recap_artifact(
    root: Path,
    *,
    artifact_id: str | None = None,
    campaign_id: str | None = None,
    session_id: str | None = None,
) -> RecapArtifactRecord:
    ensure_recap_artifacts_registry(root)
    return resolve_recap_artifact_record(
        root,
        artifact_id=artifact_id,
        campaign_id=campaign_id,
        session_id=session_id,
    )


def _resolve_run_dir(root: Path, run_dir: str) -> Path:
    raw = run_dir.strip().replace("\\", "/")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise GraphPreviewSurfaceError("run_dir escapes repository", status_code=422)
    if not resolved.is_dir():
        raise GraphPreviewSurfaceError(f"run_dir not found: {run_dir}", status_code=404)
    return resolved


def _collect_runs_from_cohort(cohort: Mapping[str, Any]) -> list[GraphPreviewRunSummary]:
    rows: list[GraphPreviewRunSummary] = []
    for entry in cohort.get("runs") or []:
        if not isinstance(entry, Mapping):
            continue
        run_dir = str(entry.get("run_dir") or "").strip()
        if not run_dir:
            continue
        rows.append(
            GraphPreviewRunSummary(
                run_dir=run_dir.replace("\\", "/"),
                model_id=str(entry.get("model_id") or "") or None,
                run_index=int(entry["run_index"]) if entry.get("run_index") is not None else None,
                canonical_ir_valid=bool(entry.get("canonical_ir_valid")) if entry.get("canonical_ir_valid") is not None else None,
                scenario_estimated_cost_usd=float(entry["scenario_estimated_cost_usd"])
                if entry.get("scenario_estimated_cost_usd") is not None
                else None,
            )
        )
    return rows


def discover_graph_preview_runs(
    root: Path | None = None,
    *,
    artifact_id: str | None = None,
    campaign_id: str | None = None,
    session_id: str | None = None,
) -> list[GraphPreviewRunSummary]:
    base = root or repo_root()
    try:
        record = _resolve_recap_artifact(
            base,
            artifact_id=artifact_id,
            campaign_id=campaign_id,
            session_id=session_id,
        )
        if record.graph_run_refs:
            return _graph_preview_run_summaries_from_refs(record.graph_run_refs)
        return []
    except RecapArtifactRegistryError:
        pass

    seen: set[str] = set()
    runs: list[GraphPreviewRunSummary] = []

    mirror = base / LAST_COHORT_MIRROR_REL
    if mirror.is_file():
        runs.extend(_collect_runs_from_cohort(_load_json(mirror)))

    artifacts = artifacts_root(base)
    if artifacts.is_dir():
        for cohort_path in sorted(artifacts.rglob("cohort_summary.json")):
            runs.extend(_collect_runs_from_cohort(_load_json(cohort_path)))

    deduped: list[GraphPreviewRunSummary] = []
    for row in runs:
        if row.run_dir in seen:
            continue
        seen.add(row.run_dir)
        deduped.append(row)
    return deduped


def _graph_from_run_dir(root: Path, run_dir: str) -> dict[str, Any] | None:
    try:
        resolved = _resolve_run_dir(root, run_dir)
    except GraphPreviewSurfaceError:
        return None
    validation_path = resolved / "validation_report.json"
    candidate_path = resolved / "candidate_output.json"
    if validation_path.is_file():
        validation = _load_json(validation_path)
        if validation.get("reconciled_candidate_graph"):
            return dict(validation["reconciled_candidate_graph"])
    if candidate_path.is_file():
        envelope = _load_json(candidate_path)
        return dict(envelope.get("candidate_graph") or envelope)
    return None


def _run_has_resolvable_evidence(root: Path, run_dir: str) -> bool:
    """Cheap probe: does any evidence ref carry a source_span_ref_id we can locate?"""
    graph = _graph_from_run_dir(root, run_dir)
    if graph is None:
        return False
    for section in ("nodes", "edges", "beats", "ignored_items", "deferred_items"):
        for obj in graph.get(section) or []:
            if not isinstance(obj, Mapping):
                continue
            for ref in obj.get("evidence_refs") or []:
                if isinstance(ref, Mapping) and ref.get("source_span_ref_id"):
                    return True
    return False


def _pick_latest_run(root: Path, runs: list[GraphPreviewRunSummary]) -> GraphPreviewRunSummary | None:
    if not runs:
        return None
    # Prefer runs whose evidence can actually be located in the source (spref-backed),
    # so the source-highlight panel has something to render. Among resolvable runs,
    # prefer canonical-IR-valid; otherwise fall back to IR-valid, then most recent.
    resolvable = [r for r in runs if _run_has_resolvable_evidence(root, r.run_dir)]
    if resolvable:
        valid_resolvable = [r for r in resolvable if r.canonical_ir_valid]
        return (valid_resolvable or resolvable)[-1]
    valid = [r for r in runs if r.canonical_ir_valid]
    return (valid or runs)[-1]


def _object_id(section: str, obj: Mapping[str, Any]) -> str:
    for key in SECTION_ID_KEYS.get(section, ("id",)):
        if obj.get(key):
            return str(obj[key])
    return "<unknown>"


def _object_kind(section: str, obj: Mapping[str, Any]) -> str:
    if section == "nodes":
        return str(obj.get("node_type") or "node")
    if section == "edges":
        return str(obj.get("relationship_type") or obj.get("label") or "edge")
    if section == "beats":
        return "beat"
    return str(obj.get("item_type") or section.replace("_items", ""))


def _session_from_span_ref(span_ref_id: str | None) -> int | None:
    if not span_ref_id:
        return None
    marker = "session-"
    if marker not in span_ref_id:
        return None
    tail = span_ref_id.split(marker, 1)[1]
    raw = tail.split(":", 1)[0]
    return int(raw) if raw.isdigit() else None


def _markdown_link_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("]", "\\]")


ENTITY_SECTION_ROLES = {
    "pcs": "pc",
    "npcs": "npc",
    "locations": "location",
    "factions": "faction",
    "items": "item",
    "new_hub_candidates": "node",
}

CANONICAL_LABEL_OVERRIDES = {
    # The corpus route is still the town hub, but table-facing display should use
    # the current region name.
    "mireward": "Mireward Reach",
}


def _strip_yaml_frontmatter_lines(lines: list[str]) -> list[str]:
    if not lines or lines[0].strip() != "---":
        return lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[index + 1 :]
    return lines


def _frontmatter_text(markdown: str) -> str:
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index])
    return ""


def _session_from_recap_path(path: str | None) -> int | None:
    if not path:
        return None
    match = re.search(r"Session\s+(\d+)", path)
    return int(match.group(1)) if match else None


def _seed_path_for_recap(root: Path, recap_path: str) -> Path | None:
    if "/_normalized/" not in recap_path:
        return None
    seed_rel = recap_path.replace("/_normalized/", "/_breadcrumbed/").removesuffix(".md")
    return root / f"{seed_rel}.frontmatter_seed.md"


def _label_from_slug(slug: str) -> str:
    if slug in CANONICAL_LABEL_OVERRIDES:
        return CANONICAL_LABEL_OVERRIDES[slug]
    return " ".join(part.capitalize() for part in slug.split("_") if part)


def _clean_seed_value(value: str) -> str:
    return value.strip().strip("'\"")


def _parse_inline_aliases(value: str) -> list[str]:
    raw = value.strip()
    if not raw.startswith("[") or not raw.endswith("]"):
        return []
    return [_clean_seed_value(part) for part in raw[1:-1].split(",") if _clean_seed_value(part)]


def _candidate_aliases(label: str, slug: str | None = None, extra_aliases: list[str] | None = None) -> list[str]:
    aliases: list[str] = []
    for alias in [label, *(extra_aliases or [])]:
        cleaned = alias.strip()
        if cleaned and cleaned not in aliases:
            aliases.append(cleaned)
    parts = label.split()
    if len(parts) > 1 and parts[0] and parts[0][0].isupper() and parts[0] not in aliases:
        aliases.append(parts[0])
    if slug == "mireward" and "Mireward" not in aliases:
        aliases.append("Mireward")
    return aliases


def _parse_seed_entities(seed_markdown: str) -> list[dict[str, Any]]:
    frontmatter = _frontmatter_text(seed_markdown)
    entities: list[dict[str, Any]] = []
    current_section: str | None = None
    current: dict[str, Any] | None = None
    collecting_aliases = False

    def flush() -> None:
        nonlocal current
        if current and current.get("slug"):
            entities.append(current)
        current = None

    for raw_line in frontmatter.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if raw_line.startswith("  ") and not raw_line.startswith("    ") and stripped.endswith(":"):
            current_section = stripped[:-1]
            collecting_aliases = False
            continue
        if stripped.startswith("- slug:"):
            flush()
            slug = _clean_seed_value(stripped.split(":", 1)[1])
            role = ENTITY_SECTION_ROLES.get(current_section or "", "node")
            current = {"slug": slug, "role": role, "aliases": []}
            collecting_aliases = False
            continue
        if current is None:
            continue
        if stripped.startswith("route:"):
            current["route"] = _clean_seed_value(stripped.split(":", 1)[1])
            collecting_aliases = False
            continue
        if stripped.startswith("proposed_route:"):
            current["route"] = _clean_seed_value(stripped.split(":", 1)[1])
            collecting_aliases = False
            continue
        if stripped.startswith("subject_type:"):
            current["role"] = _clean_seed_value(stripped.split(":", 1)[1])
            collecting_aliases = False
            continue
        if stripped.startswith("aliases_in_recap:"):
            current["aliases"].extend(_parse_inline_aliases(stripped.split(":", 1)[1]))
            collecting_aliases = True
            continue
        if collecting_aliases and stripped.startswith("- "):
            current["aliases"].append(_clean_seed_value(stripped[2:]))
            continue
        collecting_aliases = False
    flush()
    return entities


def _route_seed_nodes(root: Path, recap_path: str | None) -> tuple[dict[str, RecapGraphNode], dict[str, list[str]]]:
    if not recap_path:
        return {}, {}
    seed_path = _seed_path_for_recap(root, recap_path)
    if seed_path is None or not seed_path.is_file():
        return {}, {}

    session = _session_from_recap_path(recap_path)
    nodes: dict[str, RecapGraphNode] = {}
    aliases_by_node: dict[str, list[str]] = {}
    for entity in _parse_seed_entities(seed_path.read_text(encoding="utf-8")):
        slug = str(entity.get("slug") or "").strip()
        if not slug:
            continue
        role = str(entity.get("role") or "node").strip() or "node"
        object_id = f"{role}_{slug}"
        label = _label_from_slug(slug)
        chips = [RecapGraphChip(label="route seed", tone="neutral")]
        if session is not None:
            chips.insert(0, RecapGraphChip(label=f"S{session}", tone="evidence", source_session=session))
        nodes[object_id] = RecapGraphNode(
            object_id=object_id,
            label=label,
            kind=role,
            role=role,
            description=f"Routed from {entity.get('route') or 'recap entity_index'}",
            evidence_count=0,
            chips=chips,
        )
        aliases_by_node[object_id] = _candidate_aliases(
            label,
            slug=slug,
            extra_aliases=[str(alias) for alias in entity.get("aliases") or []],
        )
    return nodes, aliases_by_node


def _levenshtein_at_most_two(left: str, right: str) -> bool:
    left = left.lower()
    right = right.lower()
    if abs(len(left) - len(right)) > 2:
        return False
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        current = [i]
        row_min = i
        for j, right_char in enumerate(right, 1):
            value = min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (left_char != right_char),
            )
            current.append(value)
            row_min = min(row_min, value)
        if row_min > 2:
            return False
        previous = current
    return previous[-1] <= 2


def _span_links_for_nodes(
    paragraph: str,
    span_ref_id: str,
    nodes: Mapping[str, RecapGraphNode],
    aliases_by_node: Mapping[str, list[str]],
) -> list[RecapGraphLink]:
    link_candidates: list[tuple[int, int, int, RecapGraphLink]] = []
    for object_id, aliases in aliases_by_node.items():
        node = nodes.get(object_id)
        if not node:
            continue
        for alias in sorted(set(aliases), key=len, reverse=True):
            if not alias or not alias[0].isupper():
                continue
            for match in re.finditer(rf"(?<![\w]){re.escape(alias)}(?![\w])", paragraph):
                link_candidates.append(
                    (
                        match.start(),
                        -(match.end() - match.start()),
                        0,
                        RecapGraphLink(
                            href=f"dmb-node:{object_id}",
                            object_id=object_id,
                            label=node.label,
                            source_span_ref_id=span_ref_id,
                            char_start=match.start(),
                            char_end=match.end(),
                            evidence_ref_ids=[f"mention:{object_id}:{span_ref_id}"],
                        ),
                    )
                )
        if node.role not in {"pc", "npc"}:
            continue
        fuzzy_aliases = [alias for alias in aliases if alias.isalpha() and len(alias) >= 5 and " " not in alias]
        for word_match in re.finditer(r"\b[A-Z][A-Za-z]{4,}\b", paragraph):
            word = word_match.group(0)
            for alias in fuzzy_aliases:
                if word == alias or word[0].lower() != alias[0].lower():
                    continue
                if _levenshtein_at_most_two(word, alias):
                    link_candidates.append(
                        (
                            word_match.start(),
                            -(word_match.end() - word_match.start()),
                            1,
                            RecapGraphLink(
                                href=f"dmb-node:{object_id}",
                                object_id=object_id,
                                label=node.label,
                                source_span_ref_id=span_ref_id,
                                char_start=word_match.start(),
                                char_end=word_match.end(),
                                evidence_ref_ids=[f"fuzzy-mention:{object_id}:{span_ref_id}"],
                            ),
                        )
                    )
                    break

    links: list[RecapGraphLink] = []
    occupied_until = -1
    for _, _, _, link in sorted(link_candidates, key=lambda item: item[:3]):
        if link.char_start < occupied_until:
            continue
        links.append(link)
        occupied_until = link.char_end
    return links


def _candidate_node_chips(candidate: GraphPreviewCandidateRow) -> list[RecapGraphChip]:
    sessions = sorted(
        {
            session
            for ref in candidate.evidence_refs
            for session in [_session_from_span_ref(ref.source_span_ref_id)]
            if session is not None
        }
    )
    chips = [
        RecapGraphChip(label=f"S{session}", tone="evidence", source_session=session)
        for session in sessions
    ]
    if candidate.importance:
        chips.append(RecapGraphChip(label=candidate.importance, tone="neutral"))
    if candidate.evidence_count:
        chips.append(RecapGraphChip(label=f"{candidate.evidence_count} evidence", tone="evidence"))
    return chips


def _insert_markdown_node_links(
    paragraph: str,
    links: list[RecapGraphLink],
) -> str:
    ordered = sorted(links, key=lambda link: (link.char_start, -(link.char_end - link.char_start)))
    chunks: list[str] = []
    cursor = 0
    for link in ordered:
        if link.char_start < cursor or link.char_start >= link.char_end:
            continue
        chunks.append(paragraph[cursor : link.char_start])
        label = _markdown_link_text(paragraph[link.char_start : link.char_end])
        chunks.append(f"[{label}]({link.href})")
        cursor = link.char_end
    chunks.append(paragraph[cursor:])
    return "".join(chunks)


def _recap_graph_nodes_for_candidates(
    candidates: list[GraphPreviewCandidateRow],
) -> tuple[dict[str, RecapGraphNode], dict[str, list[str]]]:
    nodes: dict[str, RecapGraphNode] = {}
    aliases_by_node: dict[str, list[str]] = {}

    for candidate in candidates:
        if candidate.section != "nodes":
            continue
        role = "npc" if candidate.kind in {"character", "npc", "person"} else candidate.kind
        label = CANONICAL_LABEL_OVERRIDES.get(candidate.object_id.removeprefix("loc_"), candidate.label)
        nodes[candidate.object_id] = RecapGraphNode(
            object_id=candidate.object_id,
            label=label,
            kind=candidate.kind,
            role=role,
            description=candidate.description,
            evidence_count=candidate.evidence_count,
            chips=_candidate_node_chips(candidate),
        )
        extra_aliases = [candidate.label] if candidate.label != label else []
        aliases_by_node[candidate.object_id] = _candidate_aliases(label, extra_aliases=extra_aliases)
    return nodes, aliases_by_node


def _enrich_evidence_ref(
    ref: Mapping[str, Any],
    *,
    span_lookup: Mapping[str, Mapping[str, Any]],
    recap_text: str,
    recap_path: str,
    entity_label: str | None,
) -> GraphPreviewEvidenceRef:
    spref = str(ref.get("source_span_ref_id") or "") or None
    anchor = str(ref.get("source_anchor_id") or "") or None
    paragraph = ""
    line_start: int | None = None
    line_end: int | None = None
    if spref and spref in span_lookup:
        span = span_lookup[spref]
        line_start = int(span.get("line_start") or span.get("start_line") or 0) or None
        line_end = int(span.get("line_end") or span.get("end_line") or 0) or None
        paragraph = _paragraph_text_for_span(recap_text, span)

    anchor_quotes = coerce_anchor_quotes(ref.get("anchor_quotes"))
    raw_matches = list(ref.get("anchor_quote_matches") or [])
    matches: list[dict[str, Any]] = []
    if raw_matches:
        matches = [dict(m) for m in raw_matches if isinstance(m, Mapping)]
    elif paragraph:
        if anchor_quotes:
            matches = anchor_quote_matches_to_dicts(find_anchor_quote_matches(paragraph, anchor_quotes))
        elif entity_label and quote_found_in_paragraph(paragraph, entity_label):
            matches = anchor_quote_matches_to_dicts(find_anchor_quote_matches(paragraph, [entity_label]))

    return GraphPreviewEvidenceRef(
        source_ref_id=str(ref.get("source_ref_id") or "") or None,
        source_artifact_id=str(ref.get("source_artifact_id") or "") or None,
        source_span_ref_id=spref,
        source_anchor_id=anchor,
        label=str(ref.get("label") or "") or None,
        evidence_role=str(ref.get("evidence_role") or "") or None,
        can_open_source=bool(ref.get("can_open_source")),
        can_highlight_span=bool(ref.get("can_highlight_span")),
        anchor_quotes=anchor_quotes,
        anchor_quote_matches=[AnchorQuoteMatchRow.model_validate(m) for m in matches],
        paragraph_text=paragraph or None,
        line_start=line_start,
        line_end=line_end,
        recap_source_path=recap_path if paragraph else None,
    )


def _build_candidates(
    graph: Mapping[str, Any],
    *,
    span_lookup: Mapping[str, Mapping[str, Any]],
    recap_text: str,
    recap_path: str,
) -> list[GraphPreviewCandidateRow]:
    rows: list[GraphPreviewCandidateRow] = []
    for section in ("nodes", "edges", "beats", "ignored_items", "deferred_items"):
        for obj in graph.get(section) or []:
            if not isinstance(obj, Mapping):
                continue
            label = str(obj.get("label") or obj.get("title") or _object_id(section, obj))
            enriched = [
                _enrich_evidence_ref(
                    ref,
                    span_lookup=span_lookup,
                    recap_text=recap_text,
                    recap_path=recap_path,
                    entity_label=label,
                )
                for ref in obj.get("evidence_refs") or []
                if isinstance(ref, Mapping)
            ]
            rows.append(
                GraphPreviewCandidateRow(
                    section=section,
                    object_id=_object_id(section, obj),
                    label=label,
                    kind=_object_kind(section, obj),
                    description=str(obj.get("description") or obj.get("summary") or "") or None,
                    importance=str(obj.get("importance") or "") or None,
                    evidence_count=len(enriched),
                    evidence_refs=enriched,
                )
            )
    return rows


def build_graph_preview_surface(
    root: Path,
    run_dir: str,
    *,
    run_bundle_dir: Path | None = None,
    artifact_record: RecapArtifactRecord | None = None,
) -> GraphPreviewSurfaceResponse:
    resolved_run = _resolve_run_dir(root, run_dir)
    rel_run_dir = resolved_run.relative_to(root.resolve()).as_posix()

    validation_path = resolved_run / "validation_report.json"
    run_summary_path = resolved_run / "run_summary.json"
    candidate_path = resolved_run / "candidate_output.json"

    validation = _load_json(validation_path) if validation_path.is_file() else {}
    run_summary = _load_json(run_summary_path) if run_summary_path.is_file() else {}

    graph: dict[str, Any] | None = None
    if validation.get("reconciled_candidate_graph"):
        graph = dict(validation["reconciled_candidate_graph"])
    elif candidate_path.is_file():
        envelope = _load_json(candidate_path)
        graph = dict(envelope.get("candidate_graph") or envelope)

    if graph is None:
        raise GraphPreviewSurfaceError(f"no graph artifact in run_dir: {rel_run_dir}")

    bundle = run_bundle_dir
    if bundle is None and artifact_record is not None:
        bundle = root / artifact_record.run_bundle_uri
    if bundle is None:
        bundle = _default_run_bundle_dir(root)
    if not bundle.is_dir():
        raise GraphPreviewSurfaceError(f"run bundle not found: {bundle}", status_code=404)

    span_index = _load_json(bundle / "source_span_index.json")
    span_lookup = {
        key: sp
        for sp in span_index.get("spans", [])
        if isinstance(sp, Mapping)
        for key in [_span_lookup_key(sp)]
        if key is not None
    }
    recap_text, recap_path = _recap_text_for_run_bundle(
        root,
        bundle,
        source_recap_path=artifact_record.source_recap_path if artifact_record else None,
    )

    candidates = _build_candidates(
        graph,
        span_lookup=span_lookup,
        recap_text=recap_text,
        recap_path=recap_path,
    )

    evidence_ref_count = sum(len(c.evidence_refs) for c in candidates)
    resolvable = sum(
        1
        for c in candidates
        for ref in c.evidence_refs
        if ref.paragraph_text or ref.source_anchor_id
    )

    health = GraphPreviewHealth(
        canonical_ir_valid=bool(validation.get("canonical_ir_valid")),
        reconcile_error=str(validation.get("reconcile_error") or "") or None,
        node_count=len(graph.get("nodes") or []),
        edge_count=len(graph.get("edges") or []),
        beat_count=len(graph.get("beats") or []),
        ignored_count=len(graph.get("ignored_items") or []),
        deferred_count=len(graph.get("deferred_items") or []),
        evidence_ref_count=evidence_ref_count,
        resolvable_evidence_ref_count=resolvable,
        model_id=str(run_summary.get("model_id") or "") or None,
        scenario_estimated_cost_usd=float(run_summary["scenario_estimated_cost_usd"])
        if run_summary.get("scenario_estimated_cost_usd") is not None
        else None,
        node_recall=float((run_summary.get("scores") or {}).get("node_recall"))
        if (run_summary.get("scores") or {}).get("node_recall") is not None
        else None,
    )

    bundle_rel = bundle.relative_to(root.resolve()).as_posix() if bundle.is_relative_to(root.resolve()) else str(bundle)

    return GraphPreviewSurfaceResponse(
        run_dir=rel_run_dir,
        run_bundle_dir=bundle_rel,
        recap_source_path=recap_path,
        health=health,
        candidates=candidates,
    )


def build_latest_graph_preview_surface(
    root: Path | None = None,
    *,
    artifact_id: str | None = None,
    campaign_id: str | None = None,
    session_id: str | None = None,
) -> GraphPreviewSurfaceResponse:
    base = root or repo_root()
    record = _resolve_recap_artifact(
        base,
        artifact_id=artifact_id,
        campaign_id=campaign_id,
        session_id=session_id,
    )
    runs = discover_graph_preview_runs(
        base,
        artifact_id=record.artifact_id,
        campaign_id=record.campaign_id,
        session_id=record.session_id,
    )
    run_dir = record.default_graph_run_uri
    if not run_dir:
        picked = _pick_latest_run(base, runs)
        if picked is None:
            raise GraphPreviewSurfaceError("no graph preview runs discovered", status_code=404)
        run_dir = picked.run_dir
    return build_graph_preview_surface(
        base,
        run_dir,
        run_bundle_dir=base / record.run_bundle_uri,
        artifact_record=record,
    )


def build_recap_graph_presentation(
    root: Path,
    run_dir: str | None = None,
    *,
    run_bundle_dir: Path | None = None,
    artifact_id: str | None = None,
    campaign_id: str | None = None,
    session_id: str | None = None,
) -> RecapGraphPresentationResponse:
    record = _resolve_recap_artifact(
        root,
        artifact_id=artifact_id,
        campaign_id=campaign_id,
        session_id=session_id,
    )
    bundle = run_bundle_dir or (root / record.run_bundle_uri)
    selected_run = run_dir or record.default_graph_run_uri
    if not selected_run:
        runs = discover_graph_preview_runs(
            root,
            artifact_id=record.artifact_id,
            campaign_id=record.campaign_id,
            session_id=record.session_id,
        )
        picked = _pick_latest_run(root, runs)
        if picked is None:
            recap_text, recap_path = _recap_text_for_run_bundle(
                root,
                bundle,
                source_recap_path=record.source_recap_path,
            )
            display_lines = _strip_yaml_frontmatter_lines(recap_text.splitlines())
            return RecapGraphPresentationResponse(
                run_dir=record.run_bundle_uri,
                recap_source_path=recap_path,
                markdown="\n".join(display_lines).strip(),
                nodes={},
                links=[],
            )
        selected_run = picked.run_dir

    surface = build_graph_preview_surface(
        root,
        selected_run,
        run_bundle_dir=bundle,
        artifact_record=record,
    )
    span_index = _load_json(bundle / "source_span_index.json")
    span_lookup = {
        key: sp
        for sp in span_index.get("spans", [])
        if isinstance(sp, Mapping)
        for key in [_span_lookup_key(sp)]
        if key is not None
    }
    recap_text, _ = _recap_text_for_run_bundle(
        root,
        bundle,
        source_recap_path=record.source_recap_path,
    )
    nodes, aliases_by_node = _recap_graph_nodes_for_candidates(surface.candidates)
    seeded_nodes, seeded_aliases = _route_seed_nodes(root, surface.recap_source_path)
    for object_id, node in seeded_nodes.items():
        nodes.setdefault(object_id, node)
        aliases_by_node.setdefault(object_id, seeded_aliases.get(object_id, [node.label]))

    lines = recap_text.splitlines()
    all_links: list[RecapGraphLink] = []
    for span_ref_id, span in span_lookup.items():
        paragraph = _paragraph_text_for_span(recap_text, span)
        if paragraph.lstrip().startswith("---"):
            continue
        span_links = _span_links_for_nodes(paragraph, span_ref_id, nodes, aliases_by_node)
        if not span_links:
            continue
        start = int(span["line_start"])
        end = int(span["line_end"])
        lines[start - 1 : end] = [_insert_markdown_node_links(paragraph, span_links)]
        all_links.extend(span_links)
    display_lines = _strip_yaml_frontmatter_lines(lines)

    return RecapGraphPresentationResponse(
        run_dir=surface.run_dir,
        recap_source_path=surface.recap_source_path,
        markdown="\n".join(display_lines).strip(),
        nodes=nodes,
        links=sorted(all_links, key=lambda link: (link.source_span_ref_id, link.char_start, link.object_id)),
    )
