"""Exact native source section projection; labels are attribution, never Graph facts."""
from hashlib import sha256
from uuid import uuid4

from . import types as t
from .native_source_navigation import origin_payload
from .source_writer_output import strict_json

SCHEMA = "dmb_native_source_sections_frame_v1"
TOOL = "read_native_source_sections"
RESULT_SCHEMA = "dmb_native_source_section_result_v1"
UNAVAILABLE_SCHEMA = "dmb_native_source_section_unavailable_v1"
GAP_CODES = frozenset({"source_navigation_unavailable","source_section_unavailable",
    "source_section_over_budget","source_section_cache_unavailable","source_section_not_selected",
    "native_source_call_unverified"})
CAPABILITIES = (t.PlanNativeSourceSectionsPolicyV1, t.PlayNativeSourceSectionsPolicyV1)


def section_handle(read):
    return "n" + t.canonical_sha256({"read_event_id": str(read.event_id),
        "source_artifact_id": read.source_artifact_id,
        "native_source_revision_id": read.native_source_revision_id,
        "content_sha256": read.content_sha256, "section": read.section.model_dump(mode="json"),
        "excerpt_sha256": read.excerpt_sha256})


def source_name(execution, read):
    catalog = next(e for e in execution.events if isinstance(e,t.NativeSourceCatalogObservedV1)
        and e.event_id == read.catalog_event_id)
    nav = next(e for e in execution.events if isinstance(e,t.NativeSourceNavigationAuthorizedV1)
        and e.navigation_id == catalog.navigation_id)
    artifact = origin_payload(nav)[0]["resolution"]["artifact"]
    lineage = artifact.get("lineage")
    name = lineage.get("source_name") if isinstance(lineage,dict) else None
    if not isinstance(name,str) or not name.strip():
        raise ValueError("Native source section lacks its registered source name")
    return name.strip()


def section_row(execution, read):
    return {"section_handle": section_handle(read), "source_name": source_name(execution,read),
        "section_title": read.section.label, "line_start": read.section.line_start,
        "line_end": read.section.line_end, "text": read.text}


def project_sections(execution):
    """No source IO. Project each exact successful read once from its durable receipt."""
    reads = [e for e in execution.events if isinstance(e,t.NativeSourceSectionObservedV1)
        and e.outcome == "complete"]
    if not isinstance(execution.policy,CAPABILITIES):
        if reads: raise ValueError("Native section input requires its frozen capability")
        return None
    return {"schema": SCHEMA, "sections": [section_row(execution,e) for e in reads]}


def _current_tool_outputs(turn, body, api_mode, tool_name=TOOL):
    from .play_graph_input import _user_texts
    from .native_graph_input import _tool_outputs
    key = "messages" if api_mode == "chat_completions" else "input"
    messages = body.get(key)
    if not isinstance(messages,list):
        raise ValueError("Native section input lacks its current submission carrier")
    starts = []
    for index,message in enumerate(messages):
        for text in _user_texts({key:[message]},api_mode):
            try:
                carrier = strict_json(text)
            except (ValueError,TypeError):
                continue
            if (isinstance(carrier,dict) and carrier.get("schema") in {
                    "dmb_native_play_input_v1","dmb_native_play_input_v2","dmb_native_play_input_v3","dmb_native_play_input_v4","dmb_native_play_input_v5"}
                    and carrier.get("submission_id") == str(turn.idempotency_key)
                    and carrier.get("message") == turn.user_text):
                starts.append(index)
    if len(starts) != 1:
        raise ValueError("Native section input requires one exact current submission carrier")
    # Prior-turn tool frames remain ordinary historical context. Only outputs
    # after this exact submission can donate current-turn section handles.
    return _tool_outputs({key:messages[starts[0]:]},tool_name=tool_name)


def prove_input(turn, authorization, request_json, *, sequence, event_id=None):
    """Derive inclusion only from the actual prepared producing request, never a claim list."""
    execution = turn.graph_context_execution
    if (not isinstance(execution.policy,CAPABILITIES)
            or not isinstance(authorization,t.ProviderAttemptAuthorizedEventV3)
            or isinstance(authorization,t.PlanJevProviderAuthorizedV1)
            or sha256(request_json.encode()).hexdigest() != authorization.envelope_sha256):
        raise ValueError("Native section input differs from its producing authorization")
    body = strict_json(request_json)
    if not isinstance(body,dict) or body.get("model") != authorization.model:
        raise ValueError("Native section input differs from producing model")
    if isinstance(authorization,t.PlanJevWriterAuthorizedV1):
        from .plan_jev_graph_packet import frame_in_request
        frame = frame_in_request(request_json).get("native_source_sections")
        frames = [] if frame is None else [frame]
    else:
        if not isinstance(execution,t.PlayWorldGraphExecutionV1):
            raise ValueError("Native section tool proof belongs to native Play")
        frames = _current_tool_outputs(turn,body,authorization.api_mode)
    reads = {section_handle(e):e for e in execution.events
        if isinstance(e,t.NativeSourceSectionObservedV1) and e.outcome == "complete"}
    selected, seen = [], set()
    for frame in frames:
        if (isinstance(frame,dict) and set(frame) == {"schema","code"}
                and frame["schema"] == UNAVAILABLE_SCHEMA and frame["code"] in GAP_CODES):
            continue
        result = isinstance(frame,dict) and frame.get("schema") == RESULT_SCHEMA
        fields = {"schema","sections","reused_section_handles","partial"} if result else {"schema","sections"}
        if (not isinstance(frame,dict) or set(frame) != fields
                or frame["schema"] not in {SCHEMA,RESULT_SCHEMA} or not isinstance(frame["sections"],list)):
            raise ValueError("Native section frame has invalid fields")
        prior = set(seen)
        for row in frame["sections"]:
            if not isinstance(row,dict) or not isinstance(row.get("section_handle"),str):
                raise ValueError("Native section input has malformed selectors")
            handle = row["section_handle"]
            read = reads.get(handle)
            if read is None or handle in seen or t.canonical_sha256(row) != t.canonical_sha256(section_row(execution,read)):
                raise ValueError("Native section input differs from one exact successful named receipt")
            seen.add(handle)
            selected.append(read)
        if result:
            refs = frame['reused_section_handles']
            if (not isinstance(frame['partial'],bool) or not isinstance(refs,list)
                    or any(not isinstance(h,str) or h not in prior for h in refs) or len(set(refs)) != len(refs)):
                raise ValueError('Native section references lack earlier literal producing material')
    if not selected:
        raise ValueError("Native section input lacks an exact successful section")
    # Catalog selection already forbids overlapping/repeated source sections.
    # Keep this explicit when projecting multiple sources, without pretending
    # Graph-passage overlap has been deduplicated in this native accounting.
    selected.sort(key=lambda e:str(e.event_id))
    frame = {"schema":SCHEMA,"sections":[section_row(execution,e) for e in selected]}
    return t.NativeSourceProviderInclusionV1(kind="native_source_provider_inclusion_v1",
        event_id=event_id or uuid4(), sequence=sequence,
        provider_attempt_id=authorization.provider_attempt_id, envelope_sha256=authorization.envelope_sha256,
        context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,
        read_event_ids=[e.event_id for e in selected], frame_sha256=t.canonical_sha256(frame),
        selected_chars=sum(e.returned_chars for e in selected))


def validate_inclusions(execution):
    reads, pending, included = {}, None, set()
    for event in execution.events:
        if pending is not None and not isinstance(event,t.NativeSourceProviderInclusionV1):
            raise ValueError("Native source provider requires its input witness in the same transaction")
        if isinstance(event,t.NativeSourceSectionObservedV1) and event.outcome == "complete":
            reads[event.event_id] = event
        elif (isinstance(event,t.ProviderAttemptAuthorizedEventV3) and reads
                and not isinstance(event,t.PlanJevProviderAuthorizedV1)):
            pending = event
        elif isinstance(event,t.NativeSourceProviderInclusionV1):
            if (pending is None or not isinstance(execution.policy,CAPABILITIES)
                    or event.provider_attempt_id in included
                    or event.provider_attempt_id != pending.provider_attempt_id
                    or event.envelope_sha256 != pending.envelope_sha256
                    or event.context_receipt_sha256 != execution.context_receipt_sha256
                    or event.execution_policy_sha256 != execution.execution_policy_sha256
                    or any(identity not in reads for identity in event.read_event_ids)):
                raise ValueError("Native source inclusion lacks exact earlier read/provider/scope authority")
            selected = [reads[identity] for identity in event.read_event_ids]
            frame = {"schema":SCHEMA,"sections":[section_row(execution,e) for e in selected]}
            if (event.frame_sha256 != t.canonical_sha256(frame)
                    or event.selected_chars != sum(e.returned_chars for e in selected)):
                raise ValueError("Native source inclusion changed exact frame/character accounting")
            pending = None
            included.add(event.provider_attempt_id)
    if pending is not None:
        raise ValueError("Native source provider requires its input witness in the same transaction")


def partial_input(turn, authorization, raw):
    if (not isinstance(turn.graph_context_execution.policy,CAPABILITIES)
            or isinstance(authorization,t.PlanJevWriterAuthorizedV1)):return False
    body = strict_json(raw)
    for tool in (TOOL,'browse_native_source_sections'):
        for row in _current_tool_outputs(turn,body,authorization.api_mode,tool):
            if (isinstance(row,dict) and row.get('schema') == UNAVAILABLE_SCHEMA
                    or isinstance(row,dict) and row.get('schema') == RESULT_SCHEMA and row.get('partial') is True):
                return True
    return False
