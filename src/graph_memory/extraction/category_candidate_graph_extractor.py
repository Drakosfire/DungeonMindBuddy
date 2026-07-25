"""Category-decomposed graph extraction for runtime recap graph ingest."""
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.graph_memory import identity_resolution as ir
from src.graph_memory.anchor_quotes import coerce_anchor_quotes
from src.graph_memory.predicate_catalog import (
    prompt_markdown as predicate_catalog_prompt_markdown,
    predicate_family_for_type,
    validate_edge_predicate,
)
from src.graph_memory.party_context import (
    PartyContext,
    build_party_context_for_campaign,
)
from src.graph_memory.extraction.known_entity_mention_matcher import (
    attach_mention_evidence_to_anchors,
    filter_observation_nodes_dropping_known_entities,
    match_known_entities_in_spans,
    render_known_entity_ledger_markdown,
    validate_known_entity_ir_assertions,
)
from src.graph_memory.extraction.known_entity_mention_schema import (
    KnownEntityMentionSidecar,
)
from src.graph_memory.extraction.known_entity_registry import (
    KnownEntityRegistry,
    build_known_entity_registry,
    normalize_match_surface,
)
from src.graph_memory.extraction.extraction_profile import ExtractionPassSpec, ExtractionProfile
from src.graph_memory.extraction.recap_extraction_profile import (
    DEFAULT_SEMANTIC_STATE as RECAP_DEFAULT_SEMANTIC_STATE,
    EVIDENCE_RULE as RECAP_EVIDENCE_RULE,
    RECAP_EXTRACTION_PROFILE,
)
from src.graph_memory.source_span import document_source_ref_id
from src.graph_memory.vocabulary.dynamic_selection import build_dynamic_context_vocabulary_packet
from src.graph_memory.vocabulary.edge_context import render_edge_vocabulary_context
from src.graph_memory.vocabulary.model import ContextVocabularyPacket
from src.graph_memory.vocabulary.node_context import render_node_vocabulary_context
from src.graph_memory.session_graph_context import (
    attach_party_participation_edges,
    build_session_graph_context,
    merge_party_anchor_nodes,
    merge_party_collective,
    party_anchors_markdown,
)
from src.graph_memory.standing_context_partition import (
    ensure_standing_warning,
    partition_candidate_parts_by_provenance,
    party_registry_artifact_id,
    stamp_standing_registry_evidence,
)

logger = logging.getLogger(__name__)

BEAT_PASS_NAME = "beat_pass"
ENCOUNTER_JOB_PASS_NAME = "encounter_job_pass"
EDGE_PASS_NAME = "edge_pass"

# Back-compat constants derived from the explicit recap profile.
NODE_EXTRACTION_PASSES: tuple[tuple[str, str, str], ...] = tuple(
    (spec.pass_id, spec.default_node_type or "", spec.instruction)
    for spec in RECAP_EXTRACTION_PROFILE.node_passes
)

ALL_PASS_NAMES: tuple[str, ...] = tuple(p[0] for p in NODE_EXTRACTION_PASSES) + (
    BEAT_PASS_NAME,
    ENCOUNTER_JOB_PASS_NAME,
    EDGE_PASS_NAME,
)

PASS_PROGRESS_LABELS: dict[str, str] = {
    "actor_pass": "Extracting actors and NPCs",
    "location_pass": "Extracting locations",
    "collective_pass": "Extracting factions and collectives",
    "object_pass": "Extracting notable objects",
    "thread_pass": "Extracting mysteries and threads",
    "beat_pass": "Extracting session beats",
    "encounter_job_pass": "Extracting encounters and quests",
    "edge_pass": "Extracting relationship edges",
}

def count_category_pass_nodes_so_far(pass_outputs: Mapping[str, Mapping[str, Any]]) -> int:
    total = 0
    for pass_name, payload in pass_outputs.items():
        if pass_name == EDGE_PASS_NAME:
            continue
        nodes = payload.get("observation_nodes")
        if isinstance(nodes, list):
            total += len(nodes)
    return total


def count_category_pass_edges_so_far(pass_outputs: Mapping[str, Mapping[str, Any]]) -> int:
    payload = pass_outputs.get(EDGE_PASS_NAME) or {}
    edges = payload.get("observation_edges")
    return len(edges) if isinstance(edges, list) else 0


def planned_category_pass_names(*, enable_encounter_job_pass: bool) -> tuple[str, ...]:
    names = [name for name, _default_type, _instruction in NODE_EXTRACTION_PASSES]
    names.append(BEAT_PASS_NAME)
    if enable_encounter_job_pass:
        names.append(ENCOUNTER_JOB_PASS_NAME)
    names.append(EDGE_PASS_NAME)
    return tuple(names)


EVIDENCE_RULE = RECAP_EVIDENCE_RULE

DEFAULT_SEMANTIC_STATE = dict(RECAP_DEFAULT_SEMANTIC_STATE)

ENVELOPE_SCHEMA = "dmb_live_extractor_candidate_envelope_v0"
ENVELOPE_VERSION = "0.1"
CANDIDATE_GRAPH_SCHEMA = "dmb_candidate_graph_preview_v0"
CANDIDATE_GRAPH_VERSION = "0.1"

# Promote-eligible CandidateGraphPreview.diagnostics (matches gold / load_typed).
# Do not put extraction_mode / model_id / live LLM truth on the candidate graph.
PROMOTE_SAFE_PREVIEW_DIAGNOSTICS = {
    "preview_only": True,
    "extraction_performed": False,
    "llm_used": False,
    "runtime_connected": False,
    "plan_connected": False,
    "agent_interaction_connected": False,
    "corpus_scanned": False,
    "corpus_mutated": False,
    "facts_promoted": False,
    "canon_promoted": False,
    "unresolved_evidence_refs": 0,
    "missing_evidence_objects": 0,
    "warning_count": 0,
}

# Result/envelope sidecar only — not written onto candidate_graph.diagnostics.
EXTRACTOR_RESULT_DIAGNOSTICS = {
    "preview_only": True,
    "canon_promotion": False,
    "approved_memory_write": False,
    "corpus_mutation": False,
    "production_retrieval": False,
}

# Back-compat alias for callers that imported PREVIEW_DIAGNOSTICS as lifecycle stubs.
PREVIEW_DIAGNOSTICS = EXTRACTOR_RESULT_DIAGNOSTICS


_EDGE_PROMOTE_DROP_KEYS = frozenset({"predicate_family", "context_anchor"})
_NODE_PROMOTE_DROP_KEYS = frozenset({"context_anchor"})


def _evidence_refs_nonempty(obj: Mapping[str, Any]) -> bool:
    refs = obj.get("evidence_refs")
    return isinstance(refs, list) and any(isinstance(ref, Mapping) and ref for ref in refs)


def project_candidate_graph_for_promote(
    graph: dict[str, Any],
    *,
    warning_count: int | None = None,
    drop_empty_evidence_edges: bool = True,
) -> dict[str, Any]:
    """Project extractor graph dict onto typed promote-eligible CandidateGraphPreview IR.

    Strips catalog/telemetry fields that typed dataclasses reject, and forces
    promote-safe PreviewDiagnostics (dangerous flags false).

    Party / standing context anchors may survive sanitize with empty
    ``evidence_refs`` via ``context_anchor``. That marker is not part of the
    typed promote IR; leaving empty refs fails ``validate_candidate_graph_preview``.
    Until standing-context partition (successor slice) owns those objects,
    drop empty-evidence nodes/edges/beats here so session-evidenced extracts
    remain promotable without a hidden dependency on multi-contribution seal.

    When ``drop_empty_evidence_edges`` is False (profiles that forbid endpoint
    evidence inheritance), empty-evidence edges are retained so post-extraction
    validation can fail closed rather than silently discarding them.
    """
    for edge in graph.get("edges") or []:
        if isinstance(edge, dict):
            for key in _EDGE_PROMOTE_DROP_KEYS:
                edge.pop(key, None)
    for node in graph.get("nodes") or []:
        if isinstance(node, dict):
            for key in _NODE_PROMOTE_DROP_KEYS:
                node.pop(key, None)

    kept_nodes = [
        node
        for node in (graph.get("nodes") or [])
        if isinstance(node, Mapping) and _evidence_refs_nonempty(node)
    ]
    kept_node_ids = {
        str(node.get("node_id") or "").strip()
        for node in kept_nodes
        if str(node.get("node_id") or "").strip()
    }
    kept_edges = []
    for edge in graph.get("edges") or []:
        if not isinstance(edge, Mapping):
            continue
        if drop_empty_evidence_edges and not _evidence_refs_nonempty(edge):
            continue
        from_id = str(edge.get("from_node_id") or "").strip()
        to_id = str(edge.get("to_node_id") or "").strip()
        if from_id not in kept_node_ids or to_id not in kept_node_ids:
            continue
        kept_edges.append(dict(edge))
    kept_beats = []
    for beat in graph.get("beats") or []:
        if not isinstance(beat, Mapping) or not _evidence_refs_nonempty(beat):
            continue
        reconciled = dict(beat)
        reconciled["involved_node_ids"] = [
            nid
            for nid in (beat.get("involved_node_ids") or [])
            if str(nid).strip() in kept_node_ids
        ]
        if "unresolved_thread_node_ids" in beat:
            reconciled["unresolved_thread_node_ids"] = [
                nid
                for nid in (beat.get("unresolved_thread_node_ids") or [])
                if str(nid).strip() in kept_node_ids
            ]
        kept_beats.append(reconciled)
    graph["nodes"] = [dict(node) for node in kept_nodes]
    graph["edges"] = kept_edges
    if "beats" in graph:
        graph["beats"] = kept_beats

    diag = dict(PROMOTE_SAFE_PREVIEW_DIAGNOSTICS)
    if warning_count is not None:
        diag["warning_count"] = int(warning_count)
    elif isinstance(graph.get("diagnostics"), Mapping):
        try:
            diag["warning_count"] = int(graph["diagnostics"].get("warning_count") or 0)
        except (TypeError, ValueError):
            diag["warning_count"] = 0
    graph["diagnostics"] = diag
    return graph


class CategoryGraphExtractionError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        pass_name: str | None = None,
        raw_model_response: str | None = None,
    ):
        super().__init__(message)
        self.pass_name = pass_name
        self.raw_model_response = raw_model_response


class CategoryGraphPassClient(Protocol):
    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
        pass_spec: ExtractionPassSpec | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CategoryGraphExtractionOptions:
    campaign_id: str
    session_id: str | None
    session_number: int | None
    source_span_index: Mapping[str, Any]
    model_id: str | None = None
    source_text: str | None = None
    source_artifact_id: str | None = None
    source_ref_id: str | None = None
    enable_edge_vocabulary_packet: bool = False
    edge_vocabulary_packet: ContextVocabularyPacket | None = None
    enable_node_vocabulary_packet: bool = False
    node_vocabulary_packet: ContextVocabularyPacket | None = None
    enable_dynamic_node_vocabulary_packet: bool = False
    dynamic_node_vocabulary_nodes: tuple[Mapping[str, Any], ...] = ()
    enable_encounter_job_pass: bool = False
    enable_party_participation_attachment: bool = False
    enable_encounter_job_edge_guidance: bool = False
    profile: ExtractionProfile | None = None


def resolve_source_identity(
    options: CategoryGraphExtractionOptions,
) -> tuple[str, str]:
    """Resolve registered source_artifact_id and canonical document source_ref_id.

    Never reconstructs identity from campaign/session — both must come from the
    normalized source / SourceSpanIndex (or explicit options fields).
    """
    index = options.source_span_index
    artifact = str(
        options.source_artifact_id
        or index.get("source_artifact_id")
        or ""
    ).strip()
    if not artifact:
        for span in index.get("spans") or []:
            if not isinstance(span, Mapping):
                continue
            candidate = str(span.get("source_artifact_id") or "").strip()
            if candidate:
                artifact = candidate
                break
    if not artifact:
        raise ValueError(
            "source_artifact_id is required on CategoryGraphExtractionOptions "
            "or source_span_index; do not reconstruct from campaign/session"
        )
    source_ref = str(
        options.source_ref_id
        or index.get("source_ref_id")
        or ""
    ).strip()
    if not source_ref:
        for span in index.get("spans") or []:
            if not isinstance(span, Mapping):
                continue
            candidate = str(span.get("source_ref_id") or "").strip()
            if candidate:
                source_ref = candidate
                break
    if not source_ref:
        source_ref = document_source_ref_id(artifact)
    return artifact, source_ref


def resolve_extraction_profile(options: CategoryGraphExtractionOptions) -> ExtractionProfile:
    if options.profile is not None:
        return options.profile
    return RECAP_EXTRACTION_PROFILE


def _empty_party_context(campaign_id: str | None) -> PartyContext:
    return PartyContext(
        campaign_id=campaign_id,
        session="",
        party_names=(),
        members=(),
        warnings=("party context omitted: null session",),
    )


def _empty_known_entity_registry(campaign_id: str | None) -> KnownEntityRegistry:
    return KnownEntityRegistry(
        campaign_id=campaign_id or "",
        session_key="",
        roster_session_key=None,
        roster_carry_forward=False,
        registry_relpath=None,
        entities=(),
        warnings=("known entity registry omitted: null session",),
    )


@dataclass(frozen=True)
class CategoryGraphExtractionResult:
    candidate_graph: dict[str, Any]
    envelope: dict[str, Any]
    pass_outputs: dict[str, dict[str, Any]]
    pass_telemetry: dict[str, Any]
    consolidation_diagnostics: dict[str, Any]
    model_id: str
    total_cost_usd: float
    diagnostics: dict[str, Any] = field(default_factory=dict)
    registry_context_graph: dict[str, Any] | None = None
    known_entity_mentions: dict[str, Any] | None = None


def _policy_paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.parents[2] / "MODEL_POLICY.json",
        here.parents[3] / "MODEL_POLICY.json",
    ]


def resolve_category_graph_model(model_id: str | None) -> str:
    if model_id and model_id.strip():
        return model_id.strip()
    for policy_path in _policy_paths():
        if policy_path.exists():
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            role = policy.get("actions", {}).get(
                "graph_memory_category_extraction", "fast_smart_mini"
            )
            resolved = policy.get("models", {}).get(role)
            if isinstance(resolved, str) and resolved.strip():
                return resolved.strip()
    return "gpt-5.4-mini"


def source_packet_rows_from_span_index(
    span_index: Mapping[str, Any],
    *,
    source_text: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = source_text.splitlines() if source_text is not None else None
    for span in span_index.get("spans") or []:
        if not isinstance(span, Mapping):
            continue
        kind = span.get("kind")
        if kind == "full_text":
            continue
        spref = (
            span.get("source_span_ref_id")
            or span.get("span_id")
            or span.get("source_span_id")
        )
        if not isinstance(spref, str) or not spref.strip():
            continue
        start_line = int(span.get("line_start") or span.get("start_line") or 1)
        end_line = int(span.get("line_end") or span.get("end_line") or start_line)
        text = str(span.get("text") or span.get("text_excerpt") or "").strip()
        if not text and lines is not None and start_line >= 1:
            text = "\n".join(lines[start_line - 1 : end_line]).strip()
        if not text:
            continue
        rows.append(
            {
                "source_span_ref_id": spref,
                "source_unit_id": str(
                    span.get("span_id") or span.get("source_span_id") or spref
                ),
                "line_start": start_line,
                "line_end": end_line,
                "text": text,
            }
        )
    return rows


def _prompt_key(pass_name: str) -> str:
    return f"{pass_name}.md"


def _source_packet_md(rows: Sequence[dict[str, Any]]) -> str:
    parts: list[str] = []
    for row in rows:
        parts.append(
            f"### {row['source_span_ref_id']} / {row['source_unit_id']} / "
            f"lines {row['line_start']}-{row['line_end']}\n\n"
            f"```text\n{row['text']}\n```"
        )
    return "\n\n".join(parts)


def _party_anchors_block(party_ctx: PartyContext) -> str:
    return party_anchors_markdown(party_ctx)


def render_category_pass_prompts(
    source_rows: Sequence[dict[str, Any]],
    *,
    party_ctx: PartyContext,
    known_entity_sidecar: KnownEntityMentionSidecar | None = None,
    known_entity_registry: KnownEntityRegistry | None = None,
    profile: ExtractionProfile | None = None,
) -> dict[str, str]:
    active_profile = profile or RECAP_EXTRACTION_PROFILE
    evidence_rule = active_profile.evidence_rule
    src = _source_packet_md(source_rows)
    anchors = _party_anchors_block(party_ctx)
    ledger = ""
    if known_entity_sidecar is not None:
        ledger = (
            render_known_entity_ledger_markdown(
                known_entity_sidecar,
                registry=known_entity_registry,
            )
            + "\n\n"
        )
    safety = (
        "Preview-only graph memory extraction. "
        "Forbidden: approve memory, commit graph records, promote canon, execute writes."
    )
    prompts: dict[str, str] = {}
    for pass_spec in active_profile.node_passes:
        pass_name = pass_spec.pass_id
        default_type = pass_spec.default_node_type or ""
        instruction = pass_spec.instruction
        extra = ""
        if pass_spec.include_dispositions:
            extra = (
                "\n\nAlso include JSON keys `ignored_items` and `deferred_items` (arrays, may be empty). "
                "Each item: `item_id`, `label`, `reason`, `evidence_refs`; deferred may include `suggested_next_step`."
            )
        prompts[_prompt_key(pass_name)] = (
            f"# Category Graph Extraction — {pass_name}\n\n{safety}\n\n{anchors}\n\n{ledger}"
            f"## Task\n\n{instruction}\n\n"
            f"Default node_type for this pass: `{default_type}`.\n\n"
            f"Return JSON with key `observation_nodes` (array). Each node: "
            f"`node_id`, `label`, `node_type`, `description`, `importance` (high|medium|low), `evidence_refs`.\n"
            f"{evidence_rule}{extra}\n\n## Source Packet\n\n{src}\n"
        )
    if active_profile.beat_pass is not None:
        beat = active_profile.beat_pass
        prompts[_prompt_key(beat.pass_id)] = (
            f"# Category Graph Extraction — {beat.pass_id}\n\n{safety}\n\n{ledger}"
            f"## Task\n\n{beat.instruction}\n"
            "Return JSON with key `observation_beats` (array). Each beat: "
            "`beat_id`, `order` (positive int), `title`, `summary`, `involved_node_ids` (may be empty), `evidence_refs`.\n"
            f"{evidence_rule}\n\n## Source Packet\n\n{src}\n"
        )
    predicate_catalog = predicate_catalog_prompt_markdown()
    edge = active_profile.edge_pass
    session_volume = ""
    relationship_sweep = ""
    if active_profile.enable_session_relationship_sweep:
        session_volume = (
            "For a session-sized graph, expect roughly 10-30 durable edges when evidence supports them; "
            "do not stop after the first few obvious edges.\n\n"
        )
        relationship_sweep = (
            "## Relationship extraction sweep\n\n"
            "Review the source and nodes systematically before returning JSON:\n"
            "- Location containment: emit `located_in`, `part_of`, `within`, or related location predicates for gates, walls, roads, inns, rooms, settlements, and regions.\n"
            "- Authority and command: emit `governs`, `leads`, `commands`, or `reports_to` for mayors, commanders, leaders, and organized refugee groups.\n"
            "- Threat and displacement: emit `threatens`, `besieges`, `attacks`, or `displaced_from` for attackers, fleeing groups, sieges, and evacuation pressure.\n"
            "- Knowledge and reports: emit `knows_about`, `aware_of`, or `reports_threat_in` for explicit knowledge, messages, warnings, and learned weaknesses.\n"
            "- Composition and participation: emit `part_of`, `member_of`, or `participates_in` for waves, groups, encounters, and participants.\n\n"
        )
    prompts[_prompt_key(edge.pass_id)] = (
        f"# Category Graph Extraction — {edge.pass_id}\n\n{safety}\n\n{ledger}"
        f"## Task\n\n{edge.instruction}\n"
        "Using ONLY the Source Packet and consolidated node list supplied below, propose durable relationship edges. "
        "Do NOT create new nodes. Use exact `node_id` values from the consolidated nodes. "
        f"{session_volume}"
        f"{relationship_sweep}"
        "Prefer specific supported predicates over generic `associated_with` / `linked_to`. "
        "Omit an edge only when no catalog predicate is supported by a source quote or one endpoint cannot be bound to a listed node.\n\n"
        "Return JSON with key `observation_edges` (array). "
        "Each edge: `edge_id`, `from_node_id`, `to_node_id`, `label`, `relationship_type`, "
        "`predicate_family`, `evidence_refs`.\n"
        f"{predicate_catalog}\n\n"
        f"{evidence_rule}\n\n## Source Packet\n\n{src}\n\n## Consolidated nodes\n\n"
        "(injected at runtime)\n"
    )
    return prompts


def parse_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1)
        raw = re.sub(r"\s*```\s*$", "", raw.strip())
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise CategoryGraphExtractionError("model output must be a JSON object")
    return parsed


def _usage_from_response(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    cached = 0
    reasoning_tokens = 0
    if usage is not None:
        details = getattr(usage, "input_tokens_details", None)
        if details is not None:
            cached = int(getattr(details, "cached_tokens", 0) or 0)
        output_details = getattr(usage, "output_tokens_details", None)
        if output_details is not None:
            reasoning_tokens = int(getattr(output_details, "reasoning_tokens", 0) or 0)
        out = {
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            "cached_tokens": cached,
        }
        if reasoning_tokens:
            out["reasoning_tokens"] = reasoning_tokens
        return out
    return {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}


def _canonical_spref(value: str, allowed_span_refs: set[str]) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    candidates = [raw]
    if not raw.startswith("spref:"):
        candidates.append(f"spref:{raw}")
    for cand in candidates:
        if cand in allowed_span_refs:
            return cand
    return None


def _normalize_evidence_refs(
    refs: Any,
    allowed_span_refs: set[str] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(refs, list):
        return out
    for ref in refs:
        if isinstance(ref, Mapping) and ref.get("source_span_ref_id"):
            spref = str(ref["source_span_ref_id"])
            if allowed_span_refs is not None:
                canonical = _canonical_spref(spref, allowed_span_refs)
                if not canonical and spref in allowed_span_refs:
                    canonical = spref
                if not canonical:
                    for cand in (spref, f"spref:{spref}"):
                        if cand in allowed_span_refs:
                            canonical = cand
                            break
                if canonical:
                    entry: dict[str, Any] = {"source_span_ref_id": canonical}
                    quotes = coerce_anchor_quotes(ref.get("anchor_quotes"))
                    if quotes:
                        entry["anchor_quotes"] = quotes
                    out.append(entry)
            else:
                entry = {"source_span_ref_id": spref}
                quotes = coerce_anchor_quotes(ref.get("anchor_quotes"))
                if quotes:
                    entry["anchor_quotes"] = quotes
                out.append(entry)
    return out


def materialize_promote_evidence_ref(
    ref: Mapping[str, Any],
    *,
    source_artifact_id: str,
    source_ref_id: str | None = None,
) -> dict[str, Any] | None:
    """Expand an extractor span stub into promote-eligible EvidenceRef IR.

    Already-full refs (``source_ref_id`` + ``source_artifact_id``) pass through.
    Missing ``source_span_ref_id`` returns None (caller drops).
    """
    artifact = str(source_artifact_id or "").strip()
    if not artifact:
        raise ValueError("source_artifact_id is required to materialize evidence refs")
    document_ref = str(source_ref_id or "").strip() or document_source_ref_id(artifact)

    existing_ref = str(ref.get("source_ref_id") or "").strip()
    existing_artifact = str(ref.get("source_artifact_id") or "").strip()
    if existing_ref and existing_artifact:
        return dict(ref)

    spref = str(ref.get("source_span_ref_id") or "").strip()
    if not spref:
        return None

    out: dict[str, Any] = {
        "source_ref_id": document_ref,
        "source_artifact_id": artifact,
        "source_anchor_id": f"anchor:{spref}",
        "label": spref,
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": spref,
    }
    quotes = coerce_anchor_quotes(ref.get("anchor_quotes"))
    if quotes:
        out["anchor_quotes"] = quotes
    matches = ref.get("anchor_quote_matches")
    if isinstance(matches, list) and matches:
        out["anchor_quote_matches"] = list(matches)
    return out


_EVIDENCE_COLLECTIONS = (
    "nodes",
    "edges",
    "beats",
    "proposed_writes",
    "ignored_items",
    "deferred_items",
)


def stamp_graph_evidence_refs(
    graph: dict[str, Any],
    *,
    source_artifact_id: str,
    source_ref_id: str | None = None,
) -> dict[str, Any]:
    """Stamp promote-eligible EvidenceRef fields on every collection in-place."""
    document_ref = str(source_ref_id or "").strip() or document_source_ref_id(source_artifact_id)
    for key in _EVIDENCE_COLLECTIONS:
        items = graph.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            raw_refs = item.get("evidence_refs")
            if not isinstance(raw_refs, list):
                continue
            stamped: list[dict[str, Any]] = []
            for ref in raw_refs:
                if not isinstance(ref, Mapping):
                    continue
                materialised = materialize_promote_evidence_ref(
                    ref,
                    source_artifact_id=source_artifact_id,
                    source_ref_id=document_ref,
                )
                if materialised is not None:
                    stamped.append(materialised)
            item["evidence_refs"] = stamped
    return graph


def _normalize_node(
    raw: Mapping[str, Any],
    default_type: str,
    *,
    semantic_state: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    node_id = str(raw.get("node_id") or "").strip() or f"node:{ir.normalize_label(str(raw.get('label', 'unknown')))}"
    return {
        "node_id": node_id,
        "label": str(raw.get("label") or "").strip() or node_id,
        "node_type": str(raw.get("node_type") or default_type),
        "description": str(raw.get("description") or "").strip() or None,
        "importance": str(raw.get("importance") or "medium"),
        "semantic_state": dict(semantic_state or DEFAULT_SEMANTIC_STATE),
        "evidence_refs": _normalize_evidence_refs(raw.get("evidence_refs")),
        "proposed_action": "create",
        "confidence": str(raw.get("confidence") or "medium"),
        "warnings": list(raw.get("warnings") or []),
        "corpus_ref": raw.get("corpus_ref"),
    }


ENCOUNTER_JOB_ALLOWED_NODE_TYPES = frozenset({"combat_encounter", "quest"})


def _normalize_encounter_job_node(
    raw: Mapping[str, Any],
    *,
    semantic_state: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    explicit_type = raw.get("node_type")
    node_type = str(explicit_type or "").strip()
    if not node_type:
        raw = dict(raw)
        raw["node_type"] = "quest"
    elif node_type not in ENCOUNTER_JOB_ALLOWED_NODE_TYPES:
        node_id = str(raw.get("node_id") or "").strip()
        if not node_id:
            node_id = f"node:{ir.normalize_label(str(raw.get('label', 'unknown')))}"
        return None, node_id
    return _normalize_node(raw, "quest", semantic_state=semantic_state), None


def _normalize_beat(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "beat_id": str(raw.get("beat_id") or "beat:unknown"),
        "order": int(raw.get("order") or 1),
        "title": str(raw.get("title") or ""),
        "summary": str(raw.get("summary") or ""),
        "involved_node_ids": [str(x) for x in (raw.get("involved_node_ids") or [])],
        "evidence_refs": _normalize_evidence_refs(raw.get("evidence_refs")),
        "proposed_action": "create",
        "warnings": list(raw.get("warnings") or []),
    }


def _normalize_edge(
    raw: Mapping[str, Any],
    *,
    semantic_state: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    relationship_type = str(raw.get("relationship_type") or "").strip().lower()
    predicate_family = str(raw.get("predicate_family") or "").strip()
    if relationship_type and not predicate_family:
        predicate_family = predicate_family_for_type(relationship_type)

    warnings = [str(w) for w in (raw.get("warnings") or [])]
    for code in validate_edge_predicate(relationship_type, predicate_family):
        marker = f"predicate_validation:{code}"
        if marker not in warnings:
            warnings.append(marker)

    return {
        "edge_id": str(raw.get("edge_id") or "edge:unknown"),
        "from_node_id": str(raw.get("from_node_id") or ""),
        "to_node_id": str(raw.get("to_node_id") or ""),
        "label": str(raw.get("label") or ""),
        "relationship_type": relationship_type,
        "predicate_family": predicate_family,
        "semantic_state": dict(semantic_state or DEFAULT_SEMANTIC_STATE),
        "evidence_refs": _normalize_evidence_refs(raw.get("evidence_refs")),
        "proposed_action": "create",
        "confidence": str(raw.get("confidence") or "medium"),
        "warnings": warnings,
    }


def _normalize_disposition(raw: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "item_id": str(raw.get("item_id") or f"{prefix}:unknown"),
        "label": str(raw.get("label") or ""),
        "reason": str(raw.get("reason") or ""),
        "evidence_refs": _normalize_evidence_refs(raw.get("evidence_refs")),
        "warnings": list(raw.get("warnings") or []),
    }
    # suggested_next_step is DeferredItem-only in CandidateGraphPreview IR.
    if prefix == "deferred" and raw.get("suggested_next_step"):
        out["suggested_next_step"] = str(raw.get("suggested_next_step"))
    return out


def consolidate_category_outputs(
    pass_outputs: Mapping[str, Mapping[str, Any]],
    *,
    campaign_id: str,
    session: int | None,
    enable_party_participation_attachment: bool = False,
    known_entity_sidecar: KnownEntityMentionSidecar | None = None,
    known_entity_registry: KnownEntityRegistry | None = None,
    profile: ExtractionProfile | None = None,
) -> dict[str, Any]:
    active_profile = profile or RECAP_EXTRACTION_PROFILE
    semantic_state = dict(active_profile.default_semantic_state)
    if session is None:
        party_ctx = _empty_party_context(campaign_id)
    else:
        party_ctx = build_party_context_for_campaign(campaign_id, session)
    per_pass_counts: dict[str, int] = {}
    nodes: list[dict[str, Any]] = []
    beats: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    encounter_job_diag: dict[str, Any] = {"enabled": False}

    for pass_spec in active_profile.node_passes:
        pass_name = pass_spec.pass_id
        default_type = pass_spec.default_node_type or "entity"
        payload = pass_outputs.get(pass_name, {})
        raw_nodes = payload.get("observation_nodes") or []
        per_pass_counts[pass_name] = len(raw_nodes)
        for raw in raw_nodes:
            if isinstance(raw, Mapping):
                nodes.append(_normalize_node(raw, default_type, semantic_state=semantic_state))
        if pass_spec.include_dispositions:
            for raw in payload.get("ignored_items") or []:
                if isinstance(raw, Mapping):
                    ignored.append(_normalize_disposition(raw, "ignored"))
            for raw in payload.get("deferred_items") or []:
                if isinstance(raw, Mapping):
                    deferred.append(_normalize_disposition(raw, "deferred"))

    encounter_pass_id = (
        active_profile.encounter_job_pass.pass_id
        if active_profile.encounter_job_pass is not None
        else ENCOUNTER_JOB_PASS_NAME
    )
    encounter_payload = pass_outputs.get(encounter_pass_id)
    if encounter_payload is not None:
        raw_encounter_nodes = encounter_payload.get("observation_nodes") or []
        per_pass_counts[encounter_pass_id] = len(raw_encounter_nodes)
        dropped_invalid_node_type_ids: list[str] = []
        kept_count = 0
        for raw in raw_encounter_nodes:
            if not isinstance(raw, Mapping):
                continue
            normalized, dropped_id = _normalize_encounter_job_node(
                raw, semantic_state=semantic_state
            )
            if dropped_id:
                dropped_invalid_node_type_ids.append(dropped_id)
                continue
            if normalized is not None:
                kept_count += 1
                nodes.append(normalized)
        encounter_job_diag = {
            "enabled": True,
            "raw_node_count": len(raw_encounter_nodes),
            "kept_node_count": kept_count,
            "dropped_invalid_node_type_ids": dropped_invalid_node_type_ids,
        }

    beat_pass_id = (
        active_profile.beat_pass.pass_id if active_profile.beat_pass is not None else BEAT_PASS_NAME
    )
    beat_payload = pass_outputs.get(beat_pass_id, {})
    raw_beats = beat_payload.get("observation_beats") or []
    per_pass_counts[beat_pass_id] = len(raw_beats)
    for raw in raw_beats:
        if isinstance(raw, Mapping):
            beats.append(_normalize_beat(raw))

    nodes_before_dedup = len(nodes)
    if active_profile.enable_automatic_identity_consolidation:
        node_dedup = ir.dedup_nodes(nodes)
        deduped_nodes = list(node_dedup["kept"])
    else:
        # Profile forbids automatic identity merges: preserve ambiguous
        # same-label / cross-class collisions as separate candidates.
        node_dedup = {
            "kept": list(nodes),
            "merged": [],
            "automatic_identity_consolidation": False,
        }
        deduped_nodes = list(nodes)
    deduped_nodes, anchor_merge_diag = merge_party_anchor_nodes(
        deduped_nodes,
        party_ctx,
        default_semantic_state=semantic_state,
    )

    known_entity_diag: dict[str, Any] = {"enabled": False}
    if known_entity_registry is not None:
        known_ids = {entity.canonical_entity_id for entity in known_entity_registry.entities}
        known_slugs = {entity.slug for entity in known_entity_registry.entities}
        known_labels_norm = {
            normalize_match_surface(entity.display_name)
            for entity in known_entity_registry.entities
            if entity.display_name
        }
        deduped_nodes, dropped_ids = filter_observation_nodes_dropping_known_entities(
            deduped_nodes,
            known_ids=known_ids,
            known_slugs=known_slugs,
            known_labels_norm=known_labels_norm,
        )
        attach_diag: dict[str, Any] = {"mention_evidence_attachments": 0}
        if known_entity_sidecar is not None:
            deduped_nodes, attach_diag = attach_mention_evidence_to_anchors(
                deduped_nodes,
                known_entity_sidecar,
            )
        ir_report = validate_known_entity_ir_assertions(
            nodes=deduped_nodes,
            edges=[],
            beats=beats,
            known_ids=known_ids,
            known_slugs=known_slugs,
            known_labels_norm=known_labels_norm,
        )
        known_entity_diag = {
            "enabled": True,
            "dropped_duplicate_node_ids": dropped_ids,
            "mention_count": (
                len(known_entity_sidecar.mentions) if known_entity_sidecar is not None else 0
            ),
            **attach_diag,
            **ir_report,
        }

    # One observation pass per node type means a single proper noun can surface
    # as both a place and a polity (e.g. "Mireward Reach" as location AND
    # organization). dedup_nodes keys on (type_class, label) and keeps both,
    # which makes endpoint binding ambiguous downstream. Collapse exact-label
    # collisions across type classes into one canonical node and remap edges —
    # unless the profile forbids automatic identity consolidation.
    if active_profile.enable_automatic_identity_consolidation:
        cross_class = ir.reconcile_cross_class_label_collisions(deduped_nodes)
        deduped_nodes = list(cross_class["kept"])
        cross_class_remap: dict[str, str] = cross_class["remap"]
    else:
        cross_class = {
            "kept": list(deduped_nodes),
            "merged": [],
            "blocked": [],
            "remap": {},
            "automatic_identity_consolidation": False,
        }
        cross_class_remap = {}

    edge_pass_id = active_profile.edge_pass.pass_id
    edge_payload = pass_outputs.get(edge_pass_id, {})
    raw_edges = edge_payload.get("observation_edges") or []
    per_pass_counts[edge_pass_id] = len(raw_edges)
    node_ids = {n["node_id"] for n in deduped_nodes}
    edges: list[dict[str, Any]] = []
    dropped_edges: list[dict[str, str]] = []
    for raw in raw_edges:
        if not isinstance(raw, Mapping):
            continue
        edge = _normalize_edge(raw, semantic_state=semantic_state)
        edge["from_node_id"] = cross_class_remap.get(edge["from_node_id"], edge["from_node_id"])
        edge["to_node_id"] = cross_class_remap.get(edge["to_node_id"], edge["to_node_id"])
        if edge["from_node_id"] in node_ids and edge["to_node_id"] in node_ids:
            edges.append(edge)
        else:
            dropped_edges.append(
                {
                    "edge_id": edge["edge_id"],
                    "from_node_id": edge["from_node_id"],
                    "to_node_id": edge["to_node_id"],
                }
            )
    deduped_nodes, edges, party_collective_diag = merge_party_collective(
        deduped_nodes,
        edges,
        party_ctx,
        default_semantic_state=semantic_state,
    )
    if enable_party_participation_attachment:
        edges, party_participation_diag = attach_party_participation_edges(
            deduped_nodes,
            edges,
            party_ctx,
            default_semantic_state=semantic_state,
        )
    else:
        party_participation_diag = {"enabled": False}
    edge_dedup = ir.dedup_edges(edges, deduped_nodes)
    edge_predicate_issues = [
        {
            "edge_id": edge["edge_id"],
            "relationship_type": edge.get("relationship_type"),
            "predicate_family": edge.get("predicate_family"),
            "issues": [
                w.removeprefix("predicate_validation:")
                for w in edge.get("warnings", [])
                if str(w).startswith("predicate_validation:")
            ],
        }
        for edge in edges
        if any(str(w).startswith("predicate_validation:") for w in edge.get("warnings", []))
    ]

    if known_entity_registry is not None:
        known_ids = {entity.canonical_entity_id for entity in known_entity_registry.entities}
        known_slugs = {entity.slug for entity in known_entity_registry.entities}
        known_labels_norm = {
            normalize_match_surface(entity.display_name)
            for entity in known_entity_registry.entities
            if entity.display_name
        }
        edge_ir = validate_known_entity_ir_assertions(
            nodes=deduped_nodes,
            edges=list(edge_dedup["kept"]),
            beats=beats,
            known_ids=known_ids,
            known_slugs=known_slugs,
            known_labels_norm=known_labels_norm,
        )
        known_entity_diag.update(edge_ir)
        # Drop missing-evidence known-entity edges before generic evidence repair can
        # inherit endpoint mention citations onto hallucinated relationships.
        rejected_edge_ids = {
            str(edge_id)
            for edge_id in (edge_ir.get("rejected_known_entity_edges_missing_evidence") or [])
            if str(edge_id).strip()
        }
        if rejected_edge_ids:
            kept_edges = [
                edge
                for edge in edge_dedup["kept"]
                if str(edge.get("edge_id") or "") not in rejected_edge_ids
            ]
            edge_dedup = {
                **edge_dedup,
                "kept": kept_edges,
                "dropped_known_entity_missing_evidence": sorted(rejected_edge_ids),
            }
            known_entity_diag["removed_missing_evidence_edge_ids"] = sorted(rejected_edge_ids)

    if session is None:
        session_ctx_warnings: list[str] = ["session graph context omitted: null session"]
        registry_relpath = None
    else:
        session_ctx = build_session_graph_context(campaign_id, session)
        session_ctx_warnings = list(session_ctx.warnings)
        registry_relpath = session_ctx.registry_relpath
    diagnostics = {
        "per_pass_counts": per_pass_counts,
        "nodes_before_dedup": nodes_before_dedup,
        "party_companion_slugs": [m.slug for m in party_ctx.companions()],
        "merged_nodes": node_dedup["merged"],
        "cross_class_merged_nodes": cross_class["merged"],
        "cross_class_blocked_nodes": cross_class.get("blocked", []),
        "automatic_identity_consolidation": (
            active_profile.enable_automatic_identity_consolidation
        ),
        "merged_edges": edge_dedup["merged"],
        "dropped_edges_missing_endpoints": dropped_edges,
        "edge_predicate_issues": edge_predicate_issues,
        "party_anchor_hub_paths": sorted(party_ctx.anchor_hub_paths()),
        "inserted_party_anchor_slugs": anchor_merge_diag.get("inserted_party_anchor_slugs", []),
        "party_collective_inserted": party_collective_diag.get("party_collective_inserted", False),
        "party_membership_edge_slugs": party_collective_diag.get("party_membership_edge_slugs", []),
        "party_participation_attachment": party_participation_diag,
        "registry_relpath": registry_relpath,
        "session_graph_context_warnings": session_ctx_warnings,
        ENCOUNTER_JOB_PASS_NAME: encounter_job_diag,
        "known_entity_mentions": known_entity_diag,
    }
    return {
        "nodes": deduped_nodes,
        "edges": list(edge_dedup["kept"]),
        "beats": beats,
        "ignored_items": ignored,
        "deferred_items": deferred,
        "proposed_writes": [],
        "consolidation_diagnostics": diagnostics,
    }


def repair_edge_evidence_refs(
    parts: Mapping[str, Any],
    allowed_span_refs: set[str],
    *,
    inherit_from_endpoints: bool = True,
) -> dict[str, int]:
    """Normalize edge evidence; optionally inherit from endpoints when empty.

    Endpoint inheritance is a recap convenience. Profiles that require
    relationship-native evidence must pass ``inherit_from_endpoints=False``.
    """
    node_refs: dict[str, list[dict[str, str]]] = {}
    for node in parts.get("nodes") or []:
        if isinstance(node, Mapping):
            refs = _normalize_evidence_refs(node.get("evidence_refs"), allowed_span_refs)
            if refs:
                node_refs[str(node.get("node_id") or "")] = refs

    repaired = 0
    for edge in parts.get("edges") or []:
        if not isinstance(edge, Mapping):
            continue
        refs = _normalize_evidence_refs(edge.get("evidence_refs"), allowed_span_refs)
        if refs:
            edge["evidence_refs"] = refs
            continue
        if not inherit_from_endpoints:
            edge["evidence_refs"] = []
            continue
        from_id = str(edge.get("from_node_id") or "")
        to_id = str(edge.get("to_node_id") or "")
        inherited = node_refs.get(from_id) or node_refs.get(to_id)
        if inherited:
            edge["evidence_refs"] = list(inherited[:1])
            repaired += 1
        else:
            edge["evidence_refs"] = []
    return {
        "repaired_edge_evidence_refs": repaired,
        "edge_evidence_inheritance": inherit_from_endpoints,
    }


def sanitize_parts(
    parts: Mapping[str, Any],
    allowed_span_refs: set[str],
    *,
    drop_empty_evidence_edges: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    dropped: dict[str, list[str]] = {}
    out: dict[str, Any] = {}

    def filter_refs(refs: Any) -> list[dict[str, str]]:
        return _normalize_evidence_refs(refs, allowed_span_refs)

    for key in ("nodes", "edges", "beats", "ignored_items", "deferred_items", "proposed_writes"):
        kept: list[Any] = []
        dropped_ids: list[str] = []
        for obj in parts.get(key) or []:
            if not isinstance(obj, Mapping):
                continue
            refs = filter_refs(obj.get("evidence_refs"))
            is_context_anchor = bool(obj.get("context_anchor"))
            has_resolved_corpus = (
                isinstance(obj.get("corpus_ref"), Mapping)
                and obj.get("corpus_ref", {}).get("resolution") == "resolved"
            )
            drop_empty = True
            if key == "edges" and not drop_empty_evidence_edges:
                drop_empty = False
            if (
                drop_empty
                and key in ("nodes", "edges", "beats")
                and not refs
                and not is_context_anchor
                and not (key == "nodes" and has_resolved_corpus)
            ):
                id_key = next(
                    (k for k in ("node_id", "edge_id", "beat_id", "write_id", "item_id") if k in obj),
                    "id",
                )
                dropped_ids.append(str(obj.get(id_key, "")))
                continue
            clone = dict(obj)
            clone["evidence_refs"] = refs
            kept.append(clone)
        out[key] = kept
        if dropped_ids:
            dropped[key] = dropped_ids
    return out, {"dropped_no_valid_evidence": dropped}


def assemble_envelope(
    consolidated: Mapping[str, Any],
    *,
    campaign_id: str,
    session_id: str,
    source_artifact_id: str,
    model_id: str,
    preview_suffix: str = "category",
    source_ref_id: str | None = None,
    drop_empty_evidence_edges: bool = True,
) -> dict[str, Any]:
    warning_count = len(
        consolidated.get("consolidation_diagnostics", {}).get("merged_nodes", [])
    )
    graph = {
        "schema": CANDIDATE_GRAPH_SCHEMA,
        "version": CANDIDATE_GRAPH_VERSION,
        "preview_id": f"candidate-preview:{campaign_id}:{session_id}:{preview_suffix}",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "source_artifact_ids": [source_artifact_id],
        "status": "preview",
        "nodes": list(consolidated.get("nodes") or []),
        "edges": list(consolidated.get("edges") or []),
        "beats": list(consolidated.get("beats") or []),
        "proposed_writes": list(consolidated.get("proposed_writes") or []),
        "ignored_items": list(consolidated.get("ignored_items") or []),
        "deferred_items": list(consolidated.get("deferred_items") or []),
        "diagnostics": dict(PROMOTE_SAFE_PREVIEW_DIAGNOSTICS),
    }
    stamp_graph_evidence_refs(
        graph,
        source_artifact_id=source_artifact_id,
        source_ref_id=source_ref_id,
    )
    project_candidate_graph_for_promote(
        graph,
        warning_count=warning_count,
        drop_empty_evidence_edges=drop_empty_evidence_edges,
    )
    return {
        "schema": ENVELOPE_SCHEMA,
        "version": ENVELOPE_VERSION,
        "candidate_graph": graph,
        "review_sidecar": {
            "high_risk_claims": [],
            "notes": ["assembled deterministically from category passes"],
            "extraction_mode": "category_decomposed",
            "model_id": model_id,
        },
    }


def resolve_node_vocabulary_packet_for_options(
    options: CategoryGraphExtractionOptions,
) -> tuple[ContextVocabularyPacket | None, dict[str, Any]]:
    if options.node_vocabulary_packet is not None and (
        options.enable_node_vocabulary_packet or options.enable_dynamic_node_vocabulary_packet
    ):
        diag = {
            "enabled": True,
            "source": "explicit_node_vocabulary_packet",
            "packet_id": options.node_vocabulary_packet.packet_id,
        }
        if options.enable_dynamic_node_vocabulary_packet and options.dynamic_node_vocabulary_nodes:
            diag["dynamic_nodes_ignored"] = True
        return options.node_vocabulary_packet, diag
    if not options.enable_dynamic_node_vocabulary_packet:
        return None, {"enabled": False}
    if not options.dynamic_node_vocabulary_nodes:
        return None, {
            "enabled": True,
            "source": "dynamic_node_vocabulary_nodes",
            "packet_id": None,
            "selected_entry_count": 0,
            "skipped_reason": "no_dynamic_nodes",
        }
    result = build_dynamic_context_vocabulary_packet(
        nodes=options.dynamic_node_vocabulary_nodes,
        campaign_id=options.campaign_id,
    )
    return result.packet, {
        **result.diagnostics,
        "source": "dynamic_node_vocabulary_nodes",
    }


def edge_vocabulary_ablation_diagnostics(options: CategoryGraphExtractionOptions) -> dict[str, Any]:
    if not options.enable_edge_vocabulary_packet or options.edge_vocabulary_packet is None:
        return {"enabled": False}
    return render_edge_vocabulary_context(options.edge_vocabulary_packet).diagnostics


def build_node_pass_prompt(
    pass_name: str,
    node_prompt_template: str,
    *,
    options: CategoryGraphExtractionOptions,
    node_vocabulary_packet_override: ContextVocabularyPacket | None = None,
) -> tuple[str, dict[str, Any]]:
    active_profile = resolve_extraction_profile(options)
    allowed_passes = {spec.pass_id for spec in active_profile.node_passes}
    if pass_name not in allowed_passes:
        raise ValueError(f"pass_name must be one of {sorted(allowed_passes)}")

    packet = node_vocabulary_packet_override or (
        options.node_vocabulary_packet if options.enable_node_vocabulary_packet else None
    )
    if packet is None:
        return node_prompt_template, {"enabled": False}

    context = render_node_vocabulary_context(packet, pass_name=pass_name)
    prompt = node_prompt_template
    marker = "\n\n## Source Packet\n\n"
    if marker in prompt and context.context_text:
        prompt = prompt.replace(marker, f"\n\n{context.context_text}{marker}", 1)
    elif context.context_text:
        prompt = f"{prompt}\n\n{context.context_text}\n"
    return prompt, context.diagnostics


def build_edge_pass_prompt(
    edge_prompt_template: str,
    nodes: Sequence[Mapping[str, Any]],
    *,
    options: CategoryGraphExtractionOptions,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    nodes_json = json.dumps([_edge_prompt_node_summary(n) for n in nodes], indent=2)
    prompt = edge_prompt_template.replace("(injected at runtime)", nodes_json)
    diagnostics = {"enabled": False}
    if options.enable_edge_vocabulary_packet and options.edge_vocabulary_packet is not None:
        edge_vocab_context = render_edge_vocabulary_context(options.edge_vocabulary_packet)
        prompt = f"{prompt}\n\n{edge_vocab_context.context_text}\n"
        diagnostics = edge_vocab_context.diagnostics

    encounter_job_edge_diag: dict[str, Any] = {
        "enabled": False,
        "guidance_added": False,
        "reason": "option_disabled",
    }
    if options.enable_encounter_job_edge_guidance:
        encounter_job_guidance, encounter_job_edge_diag = render_encounter_job_edge_guidance(nodes)
        if encounter_job_guidance:
            prompt = f"{prompt}\n\n{encounter_job_guidance}\n"
    return prompt, diagnostics, encounter_job_edge_diag


def render_encounter_job_edge_guidance(
    nodes: Sequence[Mapping[str, Any]],
) -> tuple[str, dict[str, Any]]:
    encounter_job_nodes = [
        n
        for n in nodes
        if str(n.get("node_type") or "").strip() in {"quest", "combat_encounter"}
    ]
    quest_node_ids = [str(n.get("node_id")) for n in encounter_job_nodes if n.get("node_type") == "quest"]
    combat_encounter_node_ids = [
        str(n.get("node_id"))
        for n in encounter_job_nodes
        if n.get("node_type") == "combat_encounter"
    ]
    if not encounter_job_nodes:
        return "", {
            "enabled": True,
            "guidance_added": False,
            "reason": "no_encounter_or_quest_nodes",
            "quest_node_ids": [],
            "combat_encounter_node_ids": [],
        }

    summaries = [_edge_prompt_node_summary(n) for n in encounter_job_nodes]
    nodes_json = json.dumps(summaries, indent=2, sort_keys=True)
    guidance = (
        "## Encounter/job edge guidance\n\n"
        "The consolidated node list includes durable `quest` and/or `combat_encounter` nodes.\n\n"
        "Use these nodes as relationship targets when the source text supports the edge. Do not create new nodes.\n\n"
        "Do not duplicate deterministic party context edges. If an edge from `node:heroes-party` to a quest or combat encounter is already obvious from party context, omit it unless the source explicitly names a different subject or stronger relation.\n\n"
        "Do not emit generic `node:heroes-party -> quest` or `node:heroes-party -> combat_encounter` edges when deterministic party attachment already covers them. Prefer more specific source-supported edges: encounter location, adversaries, mission targets, consequences, employers, and explicitly named non-party participants.\n\n"
        "Use existing predicates only. Do not invent relationship_type values.\n\n"
        "### Encounter/job nodes available for edge binding\n\n"
        f"```json\n{nodes_json}\n```\n\n"
        "For `combat_encounter` nodes:\n\n"
        "- Link encounter to location with `located_in` when the source states where the fight, defense, battle, ambush, or confrontation occurs.\n"
        "  Direction: `combat_encounter -> location`.\n"
        "- Link adversary/creature/group actors to the encounter with `participates_in` when the source says they fought, attacked, defended, swarmed, ambushed, or appeared in the fight.\n"
        "  Direction: `actor/group -> combat_encounter`.\n"
        "- Link notable objects or hazards to the encounter with `present_at` only when they are materially present in the scene.\n"
        "  Direction: `object/hazard -> combat_encounter`.\n"
        "- Link encounter consequences with `results_in` only when the source explicitly states a durable outcome.\n"
        "  Direction: `combat_encounter -> outcome/quest/thread/condition node`.\n\n"
        "For `quest` nodes:\n\n"
        "- Link quest to the target/problem/objective with `mission_targets` when the source states what must be cleared, rescued, defended, delivered, found, investigated, or stopped.\n"
        "  Direction: `quest -> target node`.\n"
        "- Link quest to its focus/location/context with `mission_focus` when the source frames a location, institution, warning, or mystery as the focus of the work.\n"
        "  Direction: `quest -> focus node`.\n"
        "- Link explicit subject actors to quests with `pursues` only when the source names them and no deterministic party edge already covers the generic party case.\n"
        "  Direction: `actor/party -> quest`.\n"
        "- Use `hires` or `commands` for employer/authority-to-quest relationships only when the catalog supports the exact predicate and the source explicitly supports the relationship. If no catalog predicate fits, omit the edge."
    )
    return guidance, {
        "enabled": True,
        "guidance_added": True,
        "quest_node_ids": quest_node_ids,
        "combat_encounter_node_ids": combat_encounter_node_ids,
    }


def _edge_prompt_node_summary(node: Mapping[str, Any]) -> dict[str, Any]:
    """Compact node payload for edge extraction.

    Edges need more than labels: descriptions and node evidence help the model
    bind endpoints and copy valid quotes without seeing the full candidate graph
    shape. Keep the payload bounded and review-friendly.
    """
    summary: dict[str, Any] = {
        "node_id": node.get("node_id"),
        "label": node.get("label"),
        "node_type": node.get("node_type"),
    }
    description = str(node.get("description") or "").strip()
    if description:
        summary["description"] = description
    evidence_refs = node.get("evidence_refs")
    if evidence_refs:
        summary["evidence_refs"] = evidence_refs
    if node.get("context_anchor"):
        summary["context_anchor"] = True
    return summary


def _encounter_job_beat_summary(beat: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "beat_id": beat.get("beat_id"),
        "order": beat.get("order"),
        "title": beat.get("title"),
        "summary": beat.get("summary"),
        "involved_node_ids": list(beat.get("involved_node_ids") or []),
        "evidence_refs": list(beat.get("evidence_refs") or []),
    }


def render_encounter_job_pass_prompt(
    source_rows: Sequence[dict[str, Any]],
    *,
    party_ctx: PartyContext,
    nodes: Sequence[Mapping[str, Any]],
    beats: Sequence[Mapping[str, Any]],
    vocabulary_context: str | None = None,
    instruction: str | None = None,
) -> str:
    src = _source_packet_md(source_rows)
    anchors = _party_anchors_block(party_ctx)
    safety = (
        "Preview-only graph memory extraction. "
        "Forbidden: approve memory, commit graph records, promote canon, execute writes."
    )
    nodes_json = json.dumps([_edge_prompt_node_summary(n) for n in nodes], indent=2)
    beats_json = json.dumps([_encounter_job_beat_summary(b) for b in beats], indent=2)
    forbidden_types = (
        "character, location, organization, faction, group, item, thread, mystery, "
        "warning, event, job, task, mission, bounty, errand, adversary, monster, pc, party"
    )
    vocabulary_block = f"{vocabulary_context}\n\n" if vocabulary_context else ""
    task = instruction or (
        "Extract only durable job/quest/objective nodes and discrete combat encounter nodes.\n\n"
        "Create `quest` nodes for accepted, offered, assigned, discovered, or pursued objectives. "
        "Use `quest` for jobs, tasks, missions, bounties, errands, and requests. "
        "Do not use `job`, `task`, `mission`, `bounty`, or `errand` as node_type.\n\n"
        "Create `combat_encounter` nodes for discrete conflict scenes or tactical confrontations. "
    )
    return (
        f"# Category Graph Extraction — {ENCOUNTER_JOB_PASS_NAME}\n\n{safety}\n\n"
        f"{anchors}\n\n"
        f"{vocabulary_block}"
        f"## Task\n\n{task}"
        "A combat encounter is not the monster, not the location, not the quest, and not the recap beat.\n\n"
        "Separate a quest from the encounter that occurs while pursuing it.\n\n"
        "Do not recreate actors, PCs, party members, employers, locations, objects, rewards, mysteries, warnings, or threats. "
        "Those belong to other passes or later edge/attachment passes.\n\n"
        "Emit only node_type values `combat_encounter` and `quest`.\n"
        f"Forbidden node_type values: {forbidden_types}.\n"
        "Do not use `job`.\n"
        "Do not recreate locations.\n\n"
        "Return JSON with key `observation_nodes` only. Each node must include:\n"
        "`node_id`, `label`, `node_type`, `description`, `importance`, `evidence_refs`.\n"
        f"{EVIDENCE_RULE}\n\n"
        f"## Existing consolidated nodes\n\n```json\n{nodes_json}\n```\n\n"
        f"## Source-local beats\n\n```json\n{beats_json}\n```\n\n"
        f"## Source Packet\n\n{src}\n"
    )


def canonical_graph_for_runner(
    envelope: Mapping[str, Any],
    *,
    drop_empty_evidence_edges: bool = True,
) -> dict[str, Any]:
    """Return candidate graph payload suitable for graph_preview_runner artifacts.

    Always re-projects to promote-eligible IR so runner artifacts stay prepare-safe.
    When ``drop_empty_evidence_edges`` is False, empty-evidence edges are retained
    so profile validation can fail closed on missing relationship evidence.
    """
    graph = dict(envelope.get("candidate_graph") or envelope)
    # Deep-copy mutable collections so we do not mutate the envelope in place.
    for key in (
        "nodes",
        "edges",
        "beats",
        "proposed_writes",
        "ignored_items",
        "deferred_items",
    ):
        items = graph.get(key)
        if isinstance(items, list):
            graph[key] = [dict(x) if isinstance(x, dict) else x for x in items]
    warning_count = None
    if isinstance(graph.get("diagnostics"), Mapping):
        try:
            warning_count = int(graph["diagnostics"].get("warning_count") or 0)
        except (TypeError, ValueError):
            warning_count = 0
    project_candidate_graph_for_promote(
        graph,
        warning_count=warning_count,
        drop_empty_evidence_edges=drop_empty_evidence_edges,
    )
    return graph


class OpenAICategoryGraphPassClient:
    """Responses API client for category graph passes.

    Optional constructor knobs are used by the live preview runner and Luna
    benchmarks; default construction remains zero-arg for the Kernel path.
    """

    def __init__(
        self,
        *,
        reasoning_effort: str | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._reasoning_effort = (
            reasoning_effort.strip() if isinstance(reasoning_effort, str) and reasoning_effort.strip() else None
        )
        self._max_retries = max_retries

    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
        pass_spec: ExtractionPassSpec | None = None,
    ) -> dict[str, Any]:
        from src.graph_memory.extraction.category_candidate_graph_schema import (
            category_pass_text_format,
            category_pass_text_format_for_spec,
        )

        load_dungeonmindbuddy_dotenv()
        if not os.environ.get("OPENAI_API_KEY"):
            raise CategoryGraphExtractionError(
                "OPENAI_API_KEY is not configured; supply candidate_graph_path or disable graph extraction."
            )
        from openai import OpenAI

        from src.agent.planner_pricing import usage_cost_usd

        openai_kwargs: dict[str, Any] = {}
        if self._max_retries is not None:
            openai_kwargs["max_retries"] = self._max_retries
        client = OpenAI(**openai_kwargs)
        text_format = (
            category_pass_text_format_for_spec(pass_spec)
            if pass_spec is not None
            else category_pass_text_format(pass_name)
        )
        create_kwargs: dict[str, Any] = {
            "model": model_id.strip(),
            "instructions": instructions,
            "input": [{"type": "message", "role": "user", "content": user_content}],
            "text": text_format,
        }
        if self._reasoning_effort is not None:
            create_kwargs["reasoning"] = {"effort": self._reasoning_effort}
        t0 = time.perf_counter()
        response = client.responses.create(**create_kwargs)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        refusal = getattr(response, "refusal", None)
        if refusal:
            raise CategoryGraphExtractionError(
                f"model refused {pass_name}: {refusal}",
                pass_name=pass_name,
            )
        if getattr(response, "status", None) == "incomplete":
            raw = getattr(response, "output_text", None) or response.model_dump_json()
            raise CategoryGraphExtractionError(
                f"model response incomplete for {pass_name}",
                pass_name=pass_name,
                raw_model_response=str(raw),
            )
        raw_text = (getattr(response, "output_text", None) or "").strip()
        usage = _usage_from_response(response)
        cost_info = usage_cost_usd(
            model_id=model_id.strip(),
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cached_tokens=usage["cached_tokens"],
        )
        try:
            parsed = parse_json_object(raw_text) if raw_text else {}
        except json.JSONDecodeError as exc:
            raise CategoryGraphExtractionError(
                f"{pass_name} returned invalid JSON: {exc.msg}",
                pass_name=pass_name,
                raw_model_response=raw_text,
            ) from exc
        result: dict[str, Any] = {
            "parsed": parsed,
            "raw_text": raw_text,
            "usage": usage,
            "cost_usd": float(cost_info.get("total_usd") or 0.0),
            "cost_info": cost_info,
            "elapsed_ms": elapsed_ms,
            "response_id": str(getattr(response, "id", "") or ""),
        }
        if self._reasoning_effort is not None:
            result["reasoning_effort"] = self._reasoning_effort
        return result


class FixtureCategoryGraphPassClient:
    """Deterministic pass outputs for tests (pass_name -> parsed JSON)."""

    def __init__(self, pass_outputs: Mapping[str, Mapping[str, Any]]):
        self._pass_outputs = {k: dict(v) for k, v in pass_outputs.items()}

    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
        pass_spec: ExtractionPassSpec | None = None,
    ) -> dict[str, Any]:
        return {
            "parsed": dict(self._pass_outputs.get(pass_name, {})),
            "raw_text": json.dumps(self._pass_outputs.get(pass_name, {})),
            "usage": {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0},
            "cost_usd": 0.0,
            "cost_info": {},
            "elapsed_ms": 0.0,
            "response_id": f"fixture-{pass_name}",
        }


def run_category_pipeline(
    client: CategoryGraphPassClient,
    options: CategoryGraphExtractionOptions,
    *,
    progress_callback: Any | None = None,
) -> CategoryGraphExtractionResult:
    active_profile = resolve_extraction_profile(options)
    model_id = resolve_category_graph_model(options.model_id)
    source_rows = source_packet_rows_from_span_index(
        options.source_span_index,
        source_text=options.source_text,
    )
    allowed_span_refs = {r["source_span_ref_id"] for r in source_rows}
    for span in options.source_span_index.get("spans") or []:
        if isinstance(span, Mapping):
            for key in ("source_span_ref_id", "span_id", "source_span_id"):
                val = span.get(key)
                if isinstance(val, str):
                    allowed_span_refs.add(val)

    if options.session_number is None:
        party_ctx = _empty_party_context(options.campaign_id)
        known_entity_registry = _empty_known_entity_registry(options.campaign_id)
    else:
        party_ctx = build_party_context_for_campaign(
            options.campaign_id, options.session_number
        )
        known_entity_registry = build_known_entity_registry(
            options.campaign_id,
            options.session_number,
            party_ctx=party_ctx,
        )
    known_entity_sidecar = match_known_entities_in_spans(
        source_rows,
        known_entity_registry,
        session_id=options.session_id,
    )
    prompts = render_category_pass_prompts(
        source_rows,
        party_ctx=party_ctx,
        known_entity_sidecar=known_entity_sidecar,
        known_entity_registry=known_entity_registry,
        profile=active_profile,
    )
    pass_outputs: dict[str, dict[str, Any]] = {}
    pass_telemetry: dict[str, Any] = {}
    total_cost = 0.0
    system = "Category-decomposed graph memory extraction."
    node_vocabulary_pass_diagnostics: dict[str, Any] = {}
    effective_node_vocabulary_packet, dynamic_node_vocabulary_diag = resolve_node_vocabulary_packet_for_options(options)

    def _notify(pass_name: str, state: str) -> None:
        if progress_callback is None:
            return
        progress_callback(
            pass_name,
            state,
            nodes_so_far=count_category_pass_nodes_so_far(pass_outputs),
            edges_so_far=count_category_pass_edges_so_far(pass_outputs),
        )

    for pass_spec in active_profile.node_passes:
        pass_name = pass_spec.pass_id
        _notify(pass_name, "running")
        node_prompt, node_vocabulary_diag = build_node_pass_prompt(
            pass_name,
            prompts[_prompt_key(pass_name)],
            options=options,
            node_vocabulary_packet_override=effective_node_vocabulary_packet,
        )
        node_vocabulary_pass_diagnostics[pass_name] = node_vocabulary_diag
        result = client.run_pass(
            pass_name,
            model_id=model_id,
            instructions=system,
            user_content=node_prompt,
            pass_spec=pass_spec,
        )
        pass_outputs[pass_name] = result["parsed"]
        pass_telemetry[pass_name] = {
            "cost_usd": result["cost_usd"],
            "usage": result["usage"],
            "elapsed_ms": result["elapsed_ms"],
            "response_id": result["response_id"],
            "progress_label": pass_spec.progress_label,
        }
        total_cost += result["cost_usd"]
        _notify(pass_name, "complete")

    if active_profile.beat_pass is not None:
        beat = active_profile.beat_pass
        _notify(beat.pass_id, "running")
        beat_result = client.run_pass(
            beat.pass_id,
            model_id=model_id,
            instructions=system,
            user_content=prompts[_prompt_key(beat.pass_id)],
            pass_spec=beat,
        )
        pass_outputs[beat.pass_id] = beat_result["parsed"]
        pass_telemetry[beat.pass_id] = {
            "cost_usd": beat_result["cost_usd"],
            "usage": beat_result["usage"],
            "elapsed_ms": beat_result["elapsed_ms"],
            "response_id": beat_result["response_id"],
            "progress_label": beat.progress_label,
        }
        total_cost += beat_result["cost_usd"]
        _notify(beat.pass_id, "complete")

    consolidated = consolidate_category_outputs(
        pass_outputs,
        campaign_id=options.campaign_id,
        session=options.session_number,
        enable_party_participation_attachment=options.enable_party_participation_attachment,
        known_entity_sidecar=known_entity_sidecar,
        known_entity_registry=known_entity_registry,
        profile=active_profile,
    )
    encounter_pass = active_profile.encounter_job_pass
    if options.enable_encounter_job_pass:
        encounter_pass_id = (
            encounter_pass.pass_id if encounter_pass is not None else ENCOUNTER_JOB_PASS_NAME
        )
        encounter_progress = (
            encounter_pass.progress_label
            if encounter_pass is not None
            else PASS_PROGRESS_LABELS[ENCOUNTER_JOB_PASS_NAME]
        )
        encounter_instruction = (
            encounter_pass.instruction if encounter_pass is not None else None
        )
        encounter_vocabulary_context = ""
        if effective_node_vocabulary_packet is not None:
            encounter_vocabulary = render_node_vocabulary_context(
                effective_node_vocabulary_packet, pass_name=encounter_pass_id
            )
            encounter_vocabulary_context = encounter_vocabulary.context_text
            node_vocabulary_pass_diagnostics[encounter_pass_id] = (
                encounter_vocabulary.diagnostics
            )
        encounter_prompt = render_encounter_job_pass_prompt(
            source_rows,
            party_ctx=party_ctx,
            nodes=consolidated["nodes"],
            beats=consolidated["beats"],
            vocabulary_context=encounter_vocabulary_context,
            instruction=encounter_instruction,
        )
        _notify(encounter_pass_id, "running")
        encounter_spec = encounter_pass or ExtractionPassSpec(
            pass_id=encounter_pass_id,
            default_node_type=None,
            instruction=encounter_instruction or "",
            progress_label=encounter_progress,
            kind="encounter_job",
            allowed_node_types=("combat_encounter", "quest"),
        )
        encounter_result = client.run_pass(
            encounter_pass_id,
            model_id=model_id,
            instructions=system,
            user_content=encounter_prompt,
            pass_spec=encounter_spec,
        )
        pass_outputs[encounter_pass_id] = encounter_result["parsed"]
        pass_telemetry[encounter_pass_id] = {
            "cost_usd": encounter_result["cost_usd"],
            "usage": encounter_result["usage"],
            "elapsed_ms": encounter_result["elapsed_ms"],
            "response_id": encounter_result["response_id"],
            "progress_label": encounter_progress,
        }
        total_cost += encounter_result["cost_usd"]
        _notify(encounter_pass_id, "complete")
        consolidated = consolidate_category_outputs(
            pass_outputs,
            campaign_id=options.campaign_id,
            session=options.session_number,
            enable_party_participation_attachment=options.enable_party_participation_attachment,
            known_entity_sidecar=known_entity_sidecar,
            known_entity_registry=known_entity_registry,
            profile=active_profile,
        )
    edge = active_profile.edge_pass
    edge_prompt, edge_vocabulary_diag, encounter_job_edge_diag = build_edge_pass_prompt(
        prompts[_prompt_key(edge.pass_id)],
        consolidated["nodes"],
        options=options,
    )
    _notify(edge.pass_id, "running")
    edge_result = client.run_pass(
        edge.pass_id,
        model_id=model_id,
        instructions=system,
        user_content=edge_prompt,
        pass_spec=edge,
    )
    pass_outputs[edge.pass_id] = edge_result["parsed"]
    pass_telemetry[edge.pass_id] = {
        "cost_usd": edge_result["cost_usd"],
        "usage": edge_result["usage"],
        "elapsed_ms": edge_result["elapsed_ms"],
        "response_id": edge_result["response_id"],
        "progress_label": edge.progress_label,
    }
    total_cost += edge_result["cost_usd"]
    _notify(edge.pass_id, "complete")

    consolidated = consolidate_category_outputs(
        pass_outputs,
        campaign_id=options.campaign_id,
        session=options.session_number,
        enable_party_participation_attachment=options.enable_party_participation_attachment,
        known_entity_sidecar=known_entity_sidecar,
        known_entity_registry=known_entity_registry,
        profile=active_profile,
    )
    inherit_edge_evidence = active_profile.enable_edge_evidence_inheritance
    repair_diag = repair_edge_evidence_refs(
        consolidated,
        allowed_span_refs,
        inherit_from_endpoints=inherit_edge_evidence,
    )
    sanitized, sanitize_diag = sanitize_parts(
        consolidated,
        allowed_span_refs,
        drop_empty_evidence_edges=inherit_edge_evidence,
    )
    recap_parts, standing_parts, partition_diag = partition_candidate_parts_by_provenance(
        sanitized
    )
    merged_diag = {
        **consolidated["consolidation_diagnostics"],
        **repair_diag,
        **sanitize_diag,
        "standing_context_partition": partition_diag,
        "profile_id": active_profile.profile_id,
        "profile_version": active_profile.profile_version,
    }
    source_artifact_id, source_ref_id = resolve_source_identity(options)
    registry_artifact_id = party_registry_artifact_id(options.campaign_id)
    envelope = assemble_envelope(
        recap_parts,
        campaign_id=options.campaign_id,
        session_id=options.session_id,
        source_artifact_id=source_artifact_id,
        source_ref_id=source_ref_id,
        model_id=model_id,
        drop_empty_evidence_edges=inherit_edge_evidence,
    )
    candidate_graph = canonical_graph_for_runner(
        envelope,
        drop_empty_evidence_edges=inherit_edge_evidence,
    )
    registry_context_graph: dict[str, Any] | None = None
    if standing_parts.get("nodes"):
        ensure_standing_warning(standing_parts)
        standing_envelope = assemble_envelope(
            standing_parts,
            campaign_id=options.campaign_id,
            session_id=options.session_id,
            source_artifact_id=registry_artifact_id,
            source_ref_id=document_source_ref_id(registry_artifact_id),
            model_id=model_id,
            preview_suffix="standing",
            drop_empty_evidence_edges=inherit_edge_evidence,
        )
        registry_context_graph = canonical_graph_for_runner(
            standing_envelope,
            drop_empty_evidence_edges=inherit_edge_evidence,
        )
        stamp_standing_registry_evidence(
            registry_context_graph, source_artifact_id=registry_artifact_id
        )
        ensure_standing_warning(registry_context_graph)
    node_vocabulary_enabled = effective_node_vocabulary_packet is not None
    node_vocabulary_diag: dict[str, Any] = {"enabled": False}
    if node_vocabulary_enabled:
        node_vocabulary_diag = {
            "enabled": True,
            "packet_id": effective_node_vocabulary_packet.packet_id,
            "passes": node_vocabulary_pass_diagnostics,
        }
    return CategoryGraphExtractionResult(
        candidate_graph=candidate_graph,
        envelope=envelope,
        pass_outputs=pass_outputs,
        pass_telemetry=pass_telemetry,
        consolidation_diagnostics=merged_diag,
        model_id=model_id,
        total_cost_usd=round(total_cost, 6),
        diagnostics={
            "extraction_mode": "category_decomposed",
            "model_id": model_id,
            "edge_vocabulary_ablation": edge_vocabulary_diag,
            "encounter_job_edge_guidance": encounter_job_edge_diag,
            "node_vocabulary_ablation": node_vocabulary_diag,
            "dynamic_node_vocabulary_packet": dynamic_node_vocabulary_diag,
            "standing_context_partition": partition_diag,
            **EXTRACTOR_RESULT_DIAGNOSTICS,
        },
        registry_context_graph=registry_context_graph,
        known_entity_mentions=known_entity_sidecar.to_dict(),
    )


def extract_category_candidate_graph(
    options: CategoryGraphExtractionOptions,
    *,
    client: CategoryGraphPassClient | None = None,
    progress_callback: Any | None = None,
) -> CategoryGraphExtractionResult:
    model_client = client or OpenAICategoryGraphPassClient()
    return run_category_pipeline(
        model_client, options, progress_callback=progress_callback
    )
