"""Plan tool-free writer projection; host proof stays outside model context.

Exact Graph packets are matched to durable operation digests. Opened source text
comes once from protected current-attempt capture, never another corpus request.
IDs/hashes/revisions bind host authority; compact evidence handles link the model
records and passages. Display source labels grant no factual claim authority.
"""
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from .plan_jev_decision import _owner
from .source_writer_output import strict_json
from .rules_authority_types import canonical_bytes, canonical_sha256
from .context_trace import TraceSourcePassage, TraceSourceReuse, TraceFailure

from .plan_source_selectors import FRAME_SCHEMA as SCHEMA, source_selector
_METADATA = {"reviewId", "contributionId", "publicationRevisionId", "sourceArtifactId", "sourceRevisionId", "evidenceRefIds"}
_TARGETS = (("attributes", "assertion", "assertionId"), ("reviewedSourceObservations", "assertion", "assertionId"),
            ("relationships", "relationship", "edgeId"))


@dataclass(frozen=True)
class PlanWriterProjection:
    frame: dict
    closures: tuple
    graph_event_ids: tuple
    source_event_ids: tuple
    assertion_ids: tuple
    relationship_ids: tuple
    evidence_ref_ids: tuple


def _source_trace(turn, trace):
    if (not isinstance(trace, dict) or trace.get("world_id") != turn.world_id
            or trace.get("conversation_id") != str(turn.conversation_id) or trace.get("turn_id") != str(turn.turn_id)
            or type(trace.get("attempt")) is not int or trace["attempt"] != turn.attempt
            or trace.get("capture_status") != "recording"):
        raise ValueError("Plan writer requires its complete current-attempt capture")
    return [(TraceSourceReuse if row.get("kind") == "source_passage_reuse" else TraceSourcePassage).model_validate(row)
            for row in trace.get("observations", []) if row.get("kind") in {"source_passage", "source_passage_reuse"}]


def _covered_by_native(read, native_reads):
    """Suppress a duplicate literal only with exact source/range/byte coverage."""
    if read.line_start is None or read.line_end is None:return False
    for native in native_reads:
        if (read.source_artifact_id != native.source_artifact_id
                or read.source_revision_id != native.native_source_revision_id
                or native.section.line_start > read.line_start or native.section.line_end < read.line_end):continue
        lines=native.text.splitlines(keepends=True)
        start=read.line_start-native.section.line_start
        end=read.line_end-native.section.line_start+1
        if ''.join(lines[start:end]) == read.text:return True
    return False


def project(turn, proof, trace):
    from . import types as t
    receipt, execution = _owner(turn)
    from .plan_source_context import capability_bases
    graph_receipt = capability_bases(receipt).graph
    if not isinstance(execution.policy,t.PlanNativeSourceSectionsPolicyV1):
        raise ValueError('Current Plan writer requires its native selector capability')
    required={"graph_packets", "source_names", "plan_markdown", "session_evidence", "dialogue"}
    if isinstance(execution.policy,t.PlanAuthoringPolicyV1):required.add('authoring_capture')
    if isinstance(execution.policy,t.PlanPlacementAuthoringPolicyV1):required.update({'original_authoring_capture','placement_catalog'})
    if not isinstance(proof,dict) or set(proof)!=required:
        raise ValueError("Plan writer requires its complete host evidence proof")
    capture=None
    if isinstance(execution.policy,t.PlanAuthoringPolicyV1):
        from .plan_authoring import PlanAuthoringCaptureV1, parse_authoring_capture
        raw=proof['authoring_capture']
        capture=parse_authoring_capture(raw) if raw is not None else None
        expected_capture_sha=execution.policy.plan_authoring_capture_sha256
        placement_label=None
        if isinstance(execution.policy,t.PlanPlacementAuthoringPolicyV1):
            from .plan_placement import PlanPlacementCatalogV1
            original=PlanAuthoringCaptureV1.model_validate(proof["original_authoring_capture"]) if proof["original_authoring_capture"] is not None else None
            catalog=PlanPlacementCatalogV1.model_validate(proof["placement_catalog"]) if proof["placement_catalog"] is not None else None
            if ((original.sha256 if original is not None else None)!=expected_capture_sha
                    or (catalog.sha256 if catalog is not None else None)!=execution.policy.placement_catalog_sha256):
                raise ValueError("Plan writer original page/catalog differs from its frozen intent")
            choices=[event for event in execution.events if isinstance(event,t.PlanRequestedWorkSelectedV2)]
            if len(choices)!=1:
                raise ValueError("Plan writer lacks its exact resolved placement decision")
            if catalog is not None:
                catalog.require_original(original)
            choice=choices[0]
            if (choice.original_capture!=proof['original_authoring_capture']
                    or choice.placement_catalog!=proof['placement_catalog']):
                raise ValueError('Plan writer placement proof differs from the retained decision event')
            if choice.requested_work=="write_current_page":
                if catalog is None or original is None or choice.placement_selector is None:
                    raise ValueError("Plan writer has no resolved offered page location")
                resolved=catalog.resolve(original,choice.placement_selector)
                if resolved.sha256!=choice.target_capture_sha256:
                    raise ValueError("Plan writer target differs from the admitted placement")
                expected_capture_sha=resolved.sha256
                placement_label=next(entry.label for entry in catalog.entries if entry.selector==choice.placement_selector)
        if ((capture.sha256 if capture is not None else None)!=expected_capture_sha
                or capture is not None and (capture.world_id,capture.conversation_id,capture.document_id,
                    capture.base_revision,capture.base_content_sha256)!=(turn.world_id,turn.conversation_id,
                    receipt.plan_basis.document_id,receipt.plan_basis.object_revision,receipt.plan_basis.content_sha256)):
            raise ValueError('Plan writer working draft differs from its frozen current-page capture')
    markdown, sessions, dialogue = proof["plan_markdown"], proof["session_evidence"], proof["dialogue"]
    if not isinstance(markdown, str) or sha256(markdown.encode()).hexdigest() != receipt.plan_basis.content_sha256:
        raise ValueError("Plan writer text differs from its exact committed Plan")
    if (not isinstance(dialogue, list) or any(not isinstance(row, dict) or set(row) != {"role", "content"}
            or row["role"] not in {"user", "assistant"} or not isinstance(row["content"], str) for row in dialogue)):
        raise ValueError("Plan writer dialogue must be reference-only conversation messages")
    if not isinstance(sessions, list):
        raise ValueError("Plan writer session evidence must be explicit")
    frozen_sessions = {(ref.object_id, ref.revision): ref.content_sha256 for ref in turn.provenance.supporting_work
                       if ref.kind == "session_evidence_v1"}
    supplied = {}
    for session in sessions:
        if not isinstance(session, dict) or session.get("world_id") != turn.world_id:
            raise ValueError("Plan writer session evidence has a foreign owner")
        key = (session.get("run_id"), str(session.get("review_revision")))
        body = {k: v for k, v in session.items() if k != "sha256"}
        if key in supplied or session.get("sha256") != canonical_sha256(body):
            raise ValueError("Plan writer session evidence is changed or repeated")
        supplied[key] = session["sha256"]
    if supplied != frozen_sessions:
        raise ValueError("Plan writer session notes/reflections differ from frozen provenance")
    packets = proof["graph_packets"]
    if not isinstance(packets, dict):
        raise ValueError("Plan writer requires exact Graph packet bytes")
    operations = {e.event_id: e for e in execution.events if isinstance(e, t.ValidatedGraphOperationEventV3)}
    originals = []
    seen_operations = set()
    refs = set()
    for identity, raw in packets.items():
        event_id = UUID(identity) if isinstance(identity, str) else identity
        if event_id in seen_operations or not isinstance(raw, str):
            raise ValueError("Plan writer repeats or changes a Graph packet identity")
        seen_operations.add(event_id)
        event = operations.get(event_id)
        original = strict_json(raw)
        snapshot = original.get("snapshot", {}) if isinstance(original, dict) else {}
        if (graph_receipt is None or event is None or not isinstance(original, dict) or canonical_sha256(original) != event.result_packet_sha256
                or event.graph_revision != graph_receipt.graph_authority.graph_revision
                or snapshot.get("revisionId") != graph_receipt.graph_authority.graph_revision
                or snapshot.get("worldId") != graph_receipt.graph_authority.native_world_id):
            raise ValueError("Plan writer Graph bytes differ from their durable operation/snapshot")
        originals.append((event_id, event, original))
        refs.update(event.evidence_ref_ids)
    originals.sort(key=lambda item: str(item[0]))
    handles = {ref: f"e{index}" for index, ref in enumerate(sorted(refs))}
    records, closures, assertions, relationships, entities = [], set(), set(), set(), []
    record_indexes = {}
    incomplete_closure = False
    for _, event, original in originals:
        indexes = set()
        for node in original.get("nodes", []):
            label = {key: node[key] for key in ("nodeId", "label", "kind") if key in node}
            if label and label not in entities:
                entities.append(label)
        anchors = {row.get("evidenceRefId") for row in original.get("sourceAnchors", [])}
        for key, kind, id_key in _TARGETS:
            for row in original.get(key, []):
                target, evidence = row.get(id_key), row.get("evidenceRefIds")
                allowed = event.assertion_ids if kind == "assertion" else event.relationship_ids
                if (not isinstance(target, str) or target not in allowed or not isinstance(evidence, list)
                        or not evidence or any(not isinstance(ref, str) for ref in evidence)):
                    raise ValueError("Plan Graph record lacks its exact admitted evidence closure")
                if not set(evidence) <= set(event.evidence_ref_ids) & anchors:
                    # A bounded search may return a relationship whose source
                    # lies outside its evidence page. It is navigation only:
                    # never expose it as a citable record or abort other facts.
                    if not event.truncated and event.coverage_status == "complete":
                        raise ValueError("Plan Graph record lacks its exact admitted evidence closure")
                    incomplete_closure = True
                    continue
                qualified = {k: v for k, v in row.items() if k not in _METADATA | {id_key}}
                record = {"kind": kind, "target_id": target, "record": qualified,
                          "evidence": [handles[ref] for ref in evidence]}
                if record not in records:
                    records.append(record)
                indexes.add(records.index(record))
                closures.add((kind, target, tuple(sorted(set(evidence)))))
                (assertions if kind == "assertion" else relationships).add(target)
        record_indexes[event.event_id] = sorted(indexes)
    # Qualify each read with compact indexes into the one record table. Exact
    # assertion/relationship selectors remain there once, and in the host proof.
    retrievals = [{
        "records": record_indexes[event.event_id],
        "evidence": [handles[ref] for ref in event.evidence_ref_ids],
        "coverage": event.coverage_status, "truncated": event.truncated,
        "evidence_sufficiency": event.evidence_sufficiency_status,
    } for _, event, _ in originals]
    names = proof["source_names"]
    if not isinstance(names, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v.strip() for k, v in names.items()):
        raise ValueError("Plan source labels must be host display metadata")
    sources = {e.event_id: e for e in execution.events if isinstance(e, t.SOURCE_PASSAGE_EVENTS)}
    passages, source_events, present, seen = [], set(), set(), set()
    passage_origins = []
    for passage in _source_trace(turn, trace):
        if passage.evidence_ref_id not in handles:
            continue
        source = sources.get(passage.source_read_event_id)
        matches = [row for row in source.receipts if row.source_read_id == passage.source_read_id] if source else []
        if (len(matches) != 1 or passage.source_read_id in seen
                or (passage.world_id, passage.graph_revision) != (turn.world_id, graph_receipt.graph_authority.graph_revision)):
            raise ValueError("Plan source capture differs from its actual receipt")
        read = matches[0]
        for field in ("anchor_id", "evidence_ref_id", "source_artifact_id", "source_revision_id", "content_sha256", "returned_chars", "outcome", "line_start", "line_end"):
            if getattr(read, field) != getattr(passage, field):
                raise ValueError("Plan captured passage changed its exact source identity")
        if sha256(passage.text.encode()).hexdigest() != read.content_sha256 or len(passage.text) != read.returned_chars:
            raise ValueError("Plan captured passage changed its source bytes")
        passage_origins.append((source.event_id,passage))
        seen.add(passage.source_read_id)
        source_events.add(source.event_id)
        present.add(passage.evidence_ref_id)
        from .surface_source_answer import eligible
        passages.append({**({"passage_handle": source_selector(turn,source,source.receipts.index(read))} if eligible(read) else {}), "evidence": handles[passage.evidence_ref_id], "source_name": names.get(passage.source_read_id, "Opened source"),
            "text": passage.text, "line_start": passage.line_start, "line_end": passage.line_end, "outcome": passage.outcome, "truncated": read.truncated,
            "evidence_sufficiency": read.evidence_sufficiency_status})
    if not set(names) <= seen:
        raise ValueError("Plan source display label has no included captured passage")
    # A source event is the inclusion unit. Drop it only when every captured
    # literal in that event is already present in an exact native section.
    # Partial overlaps stay intact; native bytes do not donate Graph authority.
    native_reads=[e for e in execution.events if isinstance(e,t.NativeSourceSectionObservedV1) and e.outcome=='complete']
    covered={event_id for event_id in source_events if all(_covered_by_native(p,native_reads)
        for origin,p in passage_origins if origin==event_id)}
    if covered:
        passages=[row for row,(event_id,_) in zip(passages,passage_origins,strict=True) if event_id not in covered]
        source_events-=covered
        present={p.evidence_ref_id for event_id,p in passage_origins if event_id not in covered}
    gaps = sorted({(failure.phase, failure.code)
        for row in trace.get("observations", []) if row.get("kind") == "failure"
        for failure in (TraceFailure.model_validate(row),)
        if failure.phase in {"graph_retrieval", "source_read"}})
    if incomplete_closure:
        gaps = sorted(set(gaps) | {("graph_retrieval", "incomplete_evidence_closure")})
    from .surface_evidence_answer import POLICY, plan_authored_sources, authored_frame_rows
    frame = {"schema": SCHEMA, "answer_policy": POLICY,
        "authored_sources": authored_frame_rows(plan_authored_sources(turn, markdown, sessions), sessions),
        "user_question": turn.user_text, "committed_plan_markdown": markdown,
        "session_evidence": [{key: session[key] for key in ("title", "run_id", "review_revision", "ended_at", "session_content_sha256") if key in session}
            | {"sources": [{key: source[key] for key in ("kind", "element_id", "text") if key in source}
                for source in session.get("sources", [])]} for session in sessions],
        "dialogue_reference": dialogue, "retrieval_gaps": [{"operation": phase, "reason": code} for phase, code in gaps],
        "entity_index": entities, "retrieval_results": retrievals, "graph_records": records, "opened_passages": passages,
        "unopened_evidence": [handles[ref] for ref in sorted(refs - present)]}
    corpus_searches = [e for e in execution.events if isinstance(e, t.CorpusSourceSearchObservedV1)]
    if corpus_searches:
        frame['source_discovery_coverage'] = {'coverage': corpus_searches[-1].coverage,
            'global_atomic_completeness': 'not_established', 'semantic_recall': 'not_established',
            'navigation_matches_are_not_claim_support': True}
    from .authored_excerpt_blocks import selection_catalog,project_selection_blocks
    authored = plan_authored_sources(turn,markdown,frame['session_evidence'],block_policy=True)
    rows = authored_frame_rows(authored,frame['session_evidence'])
    catalog=selection_catalog(((source.handle,source.text) for source in authored),str(turn.idempotency_key))
    def blank_blocks(text):
        if text.strip():raise ValueError('Nonblank authored body has no exact selectable owner')
        return [{'selection_id':None,'text':text}] if text else []
    for source,row in zip(authored,rows,strict=True):
        path=row['body_path']; parent=frame
        for key in path[:-1]: parent=parent[key]
        parent[path[-1]]=project_selection_blocks(source.text,source.handle,catalog)
    plan_body=frame.pop('committed_plan_markdown')
    frame['committed_plan_blocks']=plan_body if isinstance(plan_body,list) else blank_blocks(plan_body)
    for session in frame['session_evidence']:
        for source in session['sources']:
            source_body=source.pop('text','')
            source['text_blocks']=source_body if isinstance(source_body,list) else blank_blocks(source_body)
    frame['authored_sources']=[{**row,'body_path':[('committed_plan_blocks' if x=='committed_plan_markdown' else 'text_blocks' if x=='text' else x) for x in row['body_path']]} for row in rows]
    from .native_source_input import project_sections
    native_sections = project_sections(execution)
    if native_sections is not None:
        from .surface_evidence_answer import PLAN_POLICY
        frame["answer_policy"] = PLAN_POLICY
        from .native_source_input import section_handle
        native_aliases={section_handle(read):source_selector(turn,read) for read in native_reads}
        frame["native_source_sections"] = {**native_sections,'sections':[
            {**row,'section_handle':native_aliases[row['section_handle']]}
            for row in native_sections['sections']]}
    if isinstance(receipt, t.PlanSourceContextReceiptV1):
        from .native_corpus import model_body_frame
        from .surface_evidence_answer import BODY_POLICY
        frame['schema'] = 'dmb_plan_jev_writer_frame_v6'
        frame['answer_policy'] = BODY_POLICY
        frame['native_body_evidence'] = model_body_frame(turn)
    if isinstance(receipt, t.PlanNativeContextReceiptV1):
        from .native_plan_statements import model_frame, POLICY
        frame.update(schema='dmb_plan_jev_writer_frame_v7', answer_policy=POLICY, native_statements=model_frame(turn))
    from .native_plan_assertions import NativePlanQueryV2
    if isinstance(getattr(receipt, 'native_query', None), NativePlanQueryV2):
        from .native_plan_assertions import model_frame as assertion_frame, POLICY as assertion_policy
        frame.update(schema='dmb_plan_jev_writer_frame_v8', answer_policy=assertion_policy, native_assertions=assertion_frame(turn))
    if isinstance(execution.policy, t.PlanAuthoringPolicyV1):
        choices = [event for event in execution.events if isinstance(event, t.PlanRequestedWorkSelectedV1)]
        if len(choices) != 1:
            raise ValueError('Plan writer requires its exact semantic requested-work choice')
        frame['requested_work'] = choices[0].requested_work
    if capture is not None:
        same=capture.draft_markdown==markdown
        frame['current_page_draft']={'state':'same_as_committed' if same else 'unsaved_working_draft',
            'primary_authoring_context':True,
            **({'body_path':['committed_plan_blocks']} if same else {'markdown':capture.draft_markdown})}
        frame['focused_edit_target']={'kind':capture.target_kind,
            **({'location':placement_label} if isinstance(execution.policy,t.PlanPlacementAuthoringPolicyV1) and placement_label is not None else {}),
            **({'selected_text':capture.selected_text} if capture.target_kind=='replace_selection' else {}),
            **({'playable_body':capture.playable_target.body_markdown} if capture.playable_target is not None else {})}
    return PlanWriterProjection(frame, tuple(sorted(closures)), tuple(item[0] for item in originals),
        tuple(sorted(source_events, key=str)), tuple(sorted(assertions)), tuple(sorted(relationships)), tuple(sorted(refs)))


def frame_in_request(raw):
    from .source_writer_output import responses_text_frame
    return responses_text_frame(raw, schemas={SCHEMA,"dmb_plan_jev_writer_frame_v8","dmb_plan_jev_writer_frame_v7","dmb_plan_jev_writer_frame_v6","dmb_plan_jev_writer_frame_v4","dmb_plan_jev_writer_frame_v3","dmb_plan_jev_writer_frame_v2","dmb_plan_jev_writer_frame_v1"}, label="Plan writer")


def verify_writer_input(turn, authorization, raw, proof, trace):
    from .types import PlanJevWriterAuthorizedV1
    from . import types as t
    projected = project(turn, proof, trace)
    body = strict_json(raw)
    if (not isinstance(authorization, PlanJevWriterAuthorizedV1)
            or body.get("model") != authorization.model
            or sha256(raw.encode()).hexdigest() != authorization.envelope_sha256
            or canonical_bytes(frame_in_request(raw)) != canonical_bytes(projected.frame)
            or authorization.frame_sha256 != canonical_sha256(projected.frame)
            or set(authorization.included_graph_event_ids) != set(projected.graph_event_ids)
            or set(t.included_passage_event_ids(authorization)) != set(projected.source_event_ids)
            or tuple(authorization.included_assertion_ids) != projected.assertion_ids
            or tuple(authorization.included_relationship_ids) != projected.relationship_ids
            or tuple(authorization.included_evidence_ref_ids) != projected.evidence_ref_ids):
        raise ValueError("Plan writer actual input differs from its exact opened evidence projection")
    if isinstance(turn.graph_context_receipt, t.PlanNativeContextReceiptV1):
        from .native_plan_statements import producing_reads
        producing_reads(turn, authorization, raw)
    from .plan_writer_output_schema import verify_format
    from .rules_authority_plan_packet import _frame_in_actual_request
    verify_format(body, projected.frame, _frame_in_actual_request(body))
    return projected


def producing_closures(turn, authorization, proof):
    """Recheck admitted record bytes in the actual tool-free producing frame."""
    from . import types as t
    receipt, execution = _owner(turn)
    from .plan_source_context import capability_bases
    graph_receipt = capability_bases(receipt).graph
    if not isinstance(authorization, t.PlanJevWriterAuthorizedV1):
        raise ValueError("Plan direct Graph support requires its own writer authorization")
    frame = frame_in_request(proof.prepared_request_json)
    if (sha256(proof.prepared_request_json.encode()).hexdigest() != authorization.envelope_sha256
            or canonical_sha256(frame) != authorization.frame_sha256):
        raise ValueError("Plan producing frame changed after exact admission")
    events = {e.event_id: e for e in execution.events if isinstance(e, t.ValidatedGraphOperationEventV3)}
    if not set(proof.graph_packets) <= set(authorization.included_graph_event_ids):
        raise ValueError("Plan producing Graph proof includes an unexposed operation")
    refs = set(authorization.included_evidence_ref_ids)
    handles = {ref: f"e{index}" for index, ref in enumerate(sorted(refs))}
    closures = set()
    for identity, raw in proof.graph_packets.items():
        event = events.get(identity)
        original = strict_json(raw)
        if event is None or canonical_sha256(original) != event.result_packet_sha256:
            raise ValueError("Plan producing record differs from its actual Graph operation")
        anchors = {row.get("evidenceRefId") for row in original.get("sourceAnchors", [])}
        for key, kind, id_key in _TARGETS:
            for row in original.get(key, []):
                target, evidence = row.get(id_key), row.get("evidenceRefIds")
                admitted = authorization.included_assertion_ids if kind == "assertion" else authorization.included_relationship_ids
                if (target not in admitted or not isinstance(evidence, list) or not evidence
                        or not set(evidence) <= refs & set(event.evidence_ref_ids) & anchors):
                    continue
                qualified = {k: v for k, v in row.items() if k not in _METADATA | {id_key}}
                record = {"kind": kind, "target_id": target, "record": qualified,
                    "evidence": [handles[ref] for ref in evidence]}
                if record not in frame.get("graph_records", []):
                    raise ValueError("Plan Graph target has no exact complete producing-frame record")
                closures.add((kind, target, tuple(sorted(set(evidence)))))
    return tuple(sorted(closures))
