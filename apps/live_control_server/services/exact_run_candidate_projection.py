"""Read a frozen candidate without source sealing, native queries or mutation."""

from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
import os
import stat
from pathlib import Path
import re
import yaml
from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.models.exact_run_candidate_projection import (
    CandidateReadEdge,
    CandidateReadEvidence,
    CandidateReadNode,
    ExactRunCandidateProjection,
    SourceDisplaySegment,
)
from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    assert_run_reviewable_evidence,
    get_extraction_run,
    validate_recap_source_run_world_binding,
)
from apps.live_control_server.services.managed_world_graph_projection import (
    resolve_managed_world_binding,
)
from apps.live_control_server.services.source_artifact_registry import (
    get_source_artifact,
)
from graph_memory.candidate_graph_to_contribution import load_typed_candidate_graph
from graph_memory.projection.markdown_mentions import (
    LocatedMentionBinding,
    project_markdown_mentions,
)
from graph_memory.projection.node_view import GraphProjectionNodeView
from graph_memory.projection.recap_projection_contracts import RecapProjectionSourceSpan
from graph_memory.source_span import (
    source_span_index_from_dict,
    validate_source_span_index,
)


class CandidateProjectionError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "candidate_inspection_unavailable",
        status_code: int = 422,
    ):
        super().__init__(message)
        self.code, self.status_code = code, status_code


def _fail(message: str):
    raise CandidateProjectionError(message)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_component(root: Path, ref) -> tuple[bytes, str]:
    uri = ref.uri
    raw = uri.removeprefix("repo://")
    if "://" in raw or not raw or ".." in Path(raw).parts:
        _fail("Candidate component locator is not confined.")
    path = Path(raw) if Path(raw).is_absolute() else root / raw
    try:
        relative = path.relative_to(root)
    except ValueError:
        _fail("Candidate component escapes its artifact root.")
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            _fail("Symlinked candidate evidence is not supported.")
    if not path.is_file():
        _fail("An exact candidate component is missing.")
    # Traverse relative to directory descriptors so a concurrent symlink swap
    # cannot turn a confined read into an out-of-root read.
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor
            )
            os.close(descriptor)
            descriptor = child
        leaf = os.open(
            relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor
        )
        with os.fdopen(leaf, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                _fail("Candidate component is not a regular file.")
            data = handle.read()
    finally:
        os.close(descriptor)
    digest = _sha(data)
    if digest != (ref.sha256 or "").removeprefix("sha256:"):
        _fail("An exact candidate component digest changed.")
    return data, digest


def narrative_segments(
    source: str, *, campaign_id: str, session_id: str
) -> tuple[str, list[SourceDisplaySegment], list[str]]:
    """Only a recognized leading envelope and its exact duplicate can be hidden."""
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    hidden: list[tuple[int, int]] = []
    diagnostics: list[str] = []
    if lines and lines[0].strip() == "---":
        closing = next(
            (i for i in range(1, min(len(lines), 256)) if lines[i].strip() == "---"),
            None,
        )
        if closing is not None:
            try:
                meta = yaml.safe_load("".join(lines[1:closing]))
            except yaml.YAMLError:
                meta = None
            expected_session = session_id.removeprefix("session-")
            if (
                isinstance(meta, dict)
                and meta.get("normalization_schema") == "dmb_recap_normalized_v1"
                and meta.get("document_class") == "play"
                and meta.get("subject_doc_kind") == "recap"
                and meta.get("campaign_id") == campaign_id
                and str(meta.get("session")) == expected_session
            ):
                hidden.append((0, offsets[closing + 1]))
                heading = closing + 1
                # The only supported nested envelope is an exact duplicate of the
                # original envelope plus its precise heading, in the next paragraph.
                if (
                    heading < len(lines)
                    and lines[heading].strip() == f"# Session {expected_session} Recap"
                ):
                    duplicate = heading + 2
                    flat = " ".join("".join(lines[: heading + 1]).split())
                    if duplicate < len(lines) and not lines[heading + 1].strip():
                        if " ".join(lines[duplicate].split()) == flat:
                            hidden.append((offsets[duplicate], offsets[duplicate + 1]))
                            diagnostics.append(
                                "recognized_duplicate_normalization_envelope_hidden"
                            )
                        elif lines[duplicate].lstrip().startswith("---"):
                            diagnostics.append(
                                "unrecognized_source_formatting_retained"
                            )
            else:
                diagnostics.append("unrecognized_source_envelope_retained")
    pieces: list[str] = []
    segments: list[SourceDisplaySegment] = []
    cursor = display = 0
    for start, end in sorted(hidden) + [(len(source), len(source))]:
        if start > cursor:
            text = source[cursor:start]
            pieces.append(text)
            segments.append(
                SourceDisplaySegment(
                    source_start=cursor,
                    source_end=start,
                    display_start=display,
                    display_end=display + len(text),
                )
            )
            display += len(text)
        cursor = end
    return "".join(pieces), segments, diagnostics


def _map_span(
    start: int, end: int, segments: list[SourceDisplaySegment]
) -> tuple[int, int] | None:
    for segment in segments:
        if segment.source_start <= start <= end <= segment.source_end:
            shift = segment.display_start - segment.source_start
            return start + shift, end + shift
    return None


def build_exact_run_candidate_projection(
    root: Path, run_id: str, managed_world_id: str
) -> ExactRunCandidateProjection:
    try:
        return _build(artifact_data_root(default=root), run_id, managed_world_id)
    except CandidateProjectionError:
        raise
    except GraphRunRegistryError as exc:
        raise CandidateProjectionError(
            "The exact stored run or evidence is unavailable.",
            status_code=exc.status_code,
        ) from exc
    except Exception as exc:
        # Do not expose filesystem locators or recover by creating missing artifacts.
        raise CandidateProjectionError(
            "The pinned candidate evidence could not be verified."
        ) from exc


def _build(
    root: Path, run_id: str, managed_world_id: str
) -> ExactRunCandidateProjection:
    root = root.resolve(strict=True)
    run = get_extraction_run(root, run_id)
    if str(run.status) not in {"reviewable", "promoted"}:
        _fail("Only a sealed reviewable or promoted candidate can be inspected.")
    if run.source_domain != "recap" or run.profile_id != "recap_category_v1@1.0":
        _fail("This exact candidate profile is not supported by the recap reader.")
    assert_run_reviewable_evidence(root, run)
    artifact = get_source_artifact(root, run.source_artifact_id)
    binding = resolve_managed_world_binding(managed_world_id)
    if not artifact.world_id or artifact.world_id != binding.native_world_id:
        _fail("The exact source does not belong to this verified World.")
    if artifact.campaign_id != run.campaign_id or artifact.session_id != run.session_id:
        _fail("The exact source and run campaign or session disagree.")
    context = run.lineage.get("world_campaign_ingest_context")
    legacy_world = run.lineage.get("native_world_id")
    if run.lineage.get("campaign_id") not in (None, run.campaign_id):
        _fail("The stored run lineage campaign conflicts with its source.")
    if context is not None or legacy_world is not None:
        validate_recap_source_run_world_binding(
            source_world_id=artifact.world_id,
            campaign_id=run.campaign_id,
            lineage=run.lineage,
        )
    if context is not None and (
        context.get("managed_world_id") != managed_world_id
        or context.get("binding_version") != binding.binding_version
    ):
        _fail("The frozen run and selected World bindings disagree.")
    captured = {
        key: _read_component(root, run.components[key])
        for key in ["source_artifact", "candidate_graph", "source_span_index"]
    }
    source = captured["source_artifact"][0].decode("utf-8")
    source_sha = captured["source_artifact"][1]
    if source_sha != (artifact.content_sha256 or "").removeprefix("sha256:"):
        _fail("The captured source no longer matches its registered revision.")
    payload = json.loads(captured["candidate_graph"][0])
    if payload.get("version") != "0.1" or payload.get("source_artifact_ids") != [
        run.source_artifact_id
    ]:
        _fail("Candidate schema or source identity is unsupported.")
    preview = load_typed_candidate_graph(payload)
    if preview.campaign_id != run.campaign_id or preview.session_id != run.session_id:
        _fail("Candidate campaign or session disagrees with its stored run.")
    index = source_span_index_from_dict(json.loads(captured["source_span_index"][0]))
    validate_source_span_index(
        index, source_artifact_id=run.source_artifact_id, content_sha256=source_sha
    )
    lines = source.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    span_map = {}
    for span in index.spans:
        if span.source_span_id in span_map or not (
            1 <= span.start_line <= span.end_line <= len(lines)
        ):
            _fail("Source-span coordinates are ambiguous or out of range.")
        span_map[span.source_span_id] = (
            span,
            starts[span.start_line - 1],
            starts[span.end_line],
        )
    display, segments, diagnostics = narrative_segments(
        source, campaign_id=run.campaign_id or "", session_id=run.session_id or ""
    )

    def evidence(refs) -> list[CandidateReadEvidence]:
        result = []
        for ref in refs:
            captured_span = span_map.get(ref.source_span_ref_id)
            if (
                captured_span is None
                or ref.source_artifact_id != run.source_artifact_id
                or ref.source_ref_id != index.source_ref_id
            ):
                diagnostics.append("unresolved_candidate_evidence")
                continue
            span, start, end = captured_span
            paragraph = source[start:end].rstrip("\r\n")
            literal = bool(ref.anchor_quotes) and all(
                q and q in paragraph for q in ref.anchor_quotes
            )
            if not literal:
                diagnostics.append("nonliteral_candidate_evidence_not_linked")
            result.append(
                CandidateReadEvidence(
                    source_span_id=span.source_span_id,
                    start_line=span.start_line,
                    end_line=span.end_line,
                    paragraph_text=paragraph,
                    anchor_quotes=list(ref.anchor_quotes),
                    can_highlight=literal,
                )
            )
        return result

    candidate_sha = captured["candidate_graph"][1]
    keys = {
        n.node_id: f"candidate:{run.run_id}:{candidate_sha}:{_sha(n.node_id.encode())}"
        for n in preview.nodes
    }
    if len(keys) != len(preview.nodes) or len(set(keys.values())) != len(keys):
        _fail("Candidate node identity is ambiguous.")
    nodes = [
        CandidateReadNode(
            view_key=keys[n.node_id],
            candidate_node_id=n.node_id,
            label=n.label,
            node_type=n.node_type,
            description=n.description or "",
            confidence=n.confidence,
            semantic_state=asdict(n.semantic_state),
            warnings=list(n.warnings),
            evidence=evidence(n.evidence_refs),
        )
        for n in preview.nodes
    ]
    owners: dict[tuple[int, int], set[str]] = {}
    surfaces = {}
    for node in nodes:
        if not node.label or any(c in node.label for c in "\n\r[]"):
            diagnostics.append("unsupported_literal_label_not_linked")
            continue
        for ref in node.evidence:
            if not ref.can_highlight:
                continue
            span, start, end = span_map[ref.source_span_id]
            for match in re.finditer(re.escape(node.label), source[start:end]):
                s, e = start + match.start(), start + match.end()
                if (
                    s > 0
                    and node.label[0].isalnum()
                    and (source[s - 1].isalnum() or source[s - 1] == "_")
                ) or (
                    e < len(source)
                    and node.label[-1].isalnum()
                    and (source[e].isalnum() or source[e] == "_")
                ):
                    continue
                mapped = _map_span(s, e, segments)
                if mapped is not None:
                    owners.setdefault(mapped, set()).add(node.view_key)
                    surfaces[mapped] = node.label
    located = []
    intervals = list(owners)
    for interval, view_keys in owners.items():
        if len(view_keys) != 1 or any(
            interval != other and interval[0] < other[1] and interval[1] > other[0]
            for other in intervals
        ):
            diagnostics.append("ambiguous_candidate_mention_not_linked")
            continue
        located.append(
            LocatedMentionBinding(
                surface=surfaces[interval],
                node_id=next(iter(view_keys)),
                start_offset=interval[0],
                end_offset=interval[1],
            )
        )
    projected, mentions, mention_diagnostics = project_markdown_mentions(
        display, [], located_bindings=located
    )
    diagnostics.extend(d.code for d in mention_diagnostics)
    linked = {m.node_id for m in mentions}
    edges = [
        CandidateReadEdge(
            candidate_edge_id=e.edge_id,
            from_view_key=keys.get(e.from_node_id),
            to_view_key=keys.get(e.to_node_id),
            from_candidate_id=e.from_node_id,
            to_candidate_id=e.to_node_id,
            relationship_type=e.relationship_type,
            label=e.label,
            evidence=evidence(e.evidence_refs),
        )
        for e in preview.edges
    ]
    views = {
        n.view_key: GraphProjectionNodeView(
            node_id=n.view_key,
            label=n.label,
            kind="candidate",
            role="unpublished_candidate",
            source_domains=["recap"],
            summary=None,
        )
        for n in nodes
    }
    read_spans = [
        RecapProjectionSourceSpan(
            span_id=span.source_span_id,
            kind="paragraph",
            ordinal=i,
            text_excerpt=source[start:end].rstrip("\r\n"),
            line_start=span.start_line,
            line_end=span.end_line,
        )
        for i, (span, start, end) in enumerate(span_map.values())
        if _map_span(start, end, segments) is not None
    ]
    if (
        get_extraction_run(root, run_id) != run
        or resolve_managed_world_binding(managed_world_id) != binding
    ):
        _fail("The run or World binding changed during inspection.")
    current_artifact = get_source_artifact(root, run.source_artifact_id)
    if current_artifact != artifact:
        _fail("The registered source changed during inspection.")
    return ExactRunCandidateProjection(
        run_id=run.run_id,
        run_revision=run.revision,
        run_status=str(run.status),
        profile_id=run.profile_id,
        source_artifact_id=run.source_artifact_id,
        source_revision_id="sha256:" + source_sha,
        source_sha256="sha256:" + source_sha,
        candidate_sha256="sha256:" + candidate_sha,
        span_index_sha256="sha256:" + captured["source_span_index"][1],
        campaign_id=run.campaign_id or "",
        session_id=run.session_id or "",
        managed_world_id=binding.managed_world_id,
        native_world_id=binding.native_world_id,
        binding_version=binding.binding_version,
        run_world_binding_status="frozen_verified"
        if context is not None
        else "source_only",
        source_markdown=source,
        narrative_markdown=display,
        projected_markdown=projected,
        source_display_segments=segments,
        nodes=nodes,
        edges=edges,
        node_views=views,
        source_spans=read_spans,
        mentions_count=len(mentions),
        unlinked_node_count=len(nodes) - len(linked),
        beat_count=len(preview.beats),
        diagnostics=sorted(set(diagnostics)),
    )
