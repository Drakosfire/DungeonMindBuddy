"""Presentation cannot acquire source bodies or grant execution authority."""

from copy import deepcopy
from hashlib import sha256
from uuid import uuid4
import pytest
from application_state.agent_conversation.saved_citation_preview import project
from application_state.agent_conversation.authored_reference_preview import project as project_references
from application_state.errors import ApplicationStateIntegrityError
from tests.test_native_plan_assertions import lane as lane
from tests.test_plan_jev_dispatch import plan_adapter as plan_adapter
from tests.application_state.test_native_plan_statements import native_read_admission_probes as native_read_admission_probes


def native_row(surface="build"):
    text = "The source describes the ruined bridge."
    h = "a" * 64
    citation = dict(
        segment_index=0,
        text_sha256=sha256(text.encode()).hexdigest(),
        provider_attempt_id=str(uuid4()),
        envelope_sha256=h,
        read_event_id=str(uuid4()),
        catalog_sha256=h,
        source_artifact_id="source",
        native_source_revision_id="revision",
        content_sha256=h,
        excerpt_sha256=h,
        section_id=h,
        selector_policy="native_full_document_v1",
        source_name="Recap",
        section_title="Full document",
        line_start=1,
        line_end=5,
    )
    completion = dict(
        schema="dmb_surface_native_completion_v1",
        surface_id=surface,
        context_receipt_sha256=h,
        producing_provider_attempt_id=citation["provider_attempt_id"],
        answer_basis="mixed_evidence",
        answer_context_status="source_grounded",
        answer_segments=[dict(kind="source_passage_claim", text=text)],
        collaboration=None,
        saved_source_citations=[],
        native_body_citations=[citation],
        native_clause_citations=[],
        native_assertion_citations=[],
    )
    return dict(
        world_id="world-one",
        surface_id=surface,
        status="completed",
        assistant_text=text,
        completion=completion,
        answer_composition_kind="base",
        rules_summary=None,
        citation_source_basis=None,
    )


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
def test_native_preview_keeps_order_and_drops_authority_and_actions(surface):
    row = native_row(surface)
    row["completion"]["native_body_citations"].append(
        dict(row["completion"]["native_body_citations"][0], read_event_id=str(uuid4()))
    )
    original = deepcopy(row)
    result = project(row)
    assert result["status"] == "ready"
    assert result["native_body_citations"] == row["completion"]["native_body_citations"]
    assert result["answer_segments"] == row["completion"]["answer_segments"]
    assert (
        not {
            "collaboration",
            "execution",
            "context_receipt_sha256",
            "answer_basis",
            "answer_context_status",
        }
        & result.keys()
    )
    assert row == original


@pytest.mark.parametrize("version", [3, 4, 5, 6, 7])
def test_existing_native_citation_families_adopt_their_original_indexes(version):
    row = native_row("plan")
    native = row["completion"]
    c = native["native_body_citations"][0]
    section = {
        k: v for k, v in c.items() if k not in {"catalog_sha256", "selector_policy"}
    }
    section.update(
        catalog_event_id=str(uuid4()),
        app_source_revision_id=str(uuid4()),
        selector_policy="markdown_sections_v1",
    )
    completion = {
        k: native[k]
        for k in [
            "surface_id",
            "context_receipt_sha256",
            "answer_basis",
            "answer_context_status",
            "answer_segments",
        ]
    }
    completion.update(
        schema=f"dmb_surface_evidence_completion_v{version}",
        citation_map=None,
        source_citations=[],
        native_source_citations=[section],
    )
    if version >= 5:
        completion["native_body_citations"] = []
    if version >= 6:
        completion["native_clause_citations"] = []
    if version >= 7:
        completion["native_assertion_citations"] = []
    row["completion"] = completion
    result = project(row)
    assert result["status"] == "ready", result
    assert result["native_source_citations"] == [section]


@pytest.mark.parametrize("marker", ["rules_mixed_v1", "unknown", None])
def test_non_base_compositions_do_not_gain_base_markers(marker):
    row = native_row()
    row["answer_composition_kind"] = marker
    assert project(row)["status"] == "details_required"


@pytest.mark.parametrize("state", ["active", "unused", "failed"])
def test_unaccepted_rules_record_does_not_suppress_base_citations(state):
    row = native_row()
    row["rules_summary"] = dict(state=state, oversized=False, binding=None, seal=None)
    assert project(row)["status"] == "ready"


@pytest.mark.parametrize(
    "summary",
    [
        {},
        True,
        dict(state="accepted", oversized=False, binding=None, seal=None),
        dict(state="active", oversized=True, binding=None, seal=None),
        dict(state="unused", oversized=False, binding={}, seal=None),
        dict(state="failed", oversized=False, binding=None, seal="a" * 64),
    ],
)
def test_invalid_base_rules_authority_keeps_details_fallback(summary):
    row = native_row()
    row["rules_summary"] = summary
    assert project(row)["status"] == "details_required"


@pytest.mark.parametrize(
    "change", ["text", "surface", "citation", "extra", "unopened_legacy", "null"]
)
def test_invalid_or_unsupported_completion_keeps_text_with_details_fallback(change):
    row = native_row()
    if change == "text":
        row["assistant_text"] = "Different answer"
    elif change == "surface":
        row["surface_id"] = "plan"
    elif change == "citation":
        row["completion"]["native_body_citations"][0]["segment_index"] = 4
    elif change == "extra":
        row["completion"]["execute"] = True
    elif change == "unopened_legacy":
        row["completion"] = dict(
            schema="dmb_build_graph_completion_v1", source_opened=False
        )
    else:
        row["completion"] = None
    assert project(row)["status"] == "details_required"


@pytest.mark.parametrize("status", ["accepted", "running", "interrupted", "failed"])
def test_incomplete_attempts_have_no_preview(status):
    row = native_row()
    row["status"] = status
    assert project(row) is None


def test_saved_claim_uses_only_the_actual_source_stamp():
    row = native_row()
    h = "b" * 64
    row["completion"]["answer_segments"] = [
        dict(kind="saved_source_claim", text=row["assistant_text"], content_sha256=h)
    ]
    row["completion"].update(
        native_body_citations=[],
        saved_source_citations=[
            dict(
                segment_index=0,
                text_sha256=sha256(row["assistant_text"].encode()).hexdigest(),
                section_event_ids=[str(uuid4())],
            )
        ],
    )
    row["citation_source_basis"] = dict(
        world_id="world-one",
        document_id="page",
        registry_revision=7,
        content_sha256=h,
        visibility="internal",
    )
    assert project(row)["source_basis"] == row["citation_source_basis"]
    row["citation_source_basis"]["world_id"] = "foreign"
    assert project(row)["status"] == "details_required"


def test_active_snapshot_projects_stored_native_metadata_without_full_turn_reads(
    lane, tmp_path, monkeypatch, application_state_dsn
):
    from application_state.agent_conversation import library, repository
    from tests.test_surface_native_build_ordinary import _fresh_case

    before_response = []
    def inspect_input(adapter, provider):
        if provider == "typesafe" and not before_response:
            selected = adapter.request.build_authored_references
            snapshot = library.read_active_messages(adapter.world_id)
            before_response.append(snapshot["messages"][-1]["authored_references"])
            assert before_response[-1] == selected.model_dump(mode="json", by_alias=True)
            from application_state.agent_conversation import types as t
            execution = adapter.fence.turn.graph_context_execution
            writer = execution.policy.provider_roles.writer.identity()
            assert not any(isinstance(event, t.ProviderAttemptAuthorizedEventV1)
                and (event.provider, event.model, event.api_mode) == writer for event in execution.events)

    case = _fresh_case(
        lane,
        tmp_path,
        monkeypatch,
        None,
        False,
        False,
        False,
        native_body="direct_support",
        authored_source="full_document",
        before_provider=inspect_input,
    )
    assert before_response == [case.selected.model_dump(mode="json", by_alias=True)]
    pointer = case.service.get_world_pointer(case.world)

    def forbidden(*args, **kwargs):
        raise AssertionError("Full receipt/execution loaded for citation presentation")

    with monkeypatch.context() as patch:
        patch.setattr(repository, "_turn_from_row", forbidden)
        page = library.read_active_messages(case.world)
    assert page["schema"] == "dmb_active_conversation_messages_v4"
    message = page["messages"][0]
    assert message["authored_references"] == case.selected.model_dump(mode="json", by_alias=True)
    import psycopg

    with psycopg.connect(
        application_state_dsn, options="-c default_transaction_read_only=on"
    ) as conn:
        shape = conn.execute(
            "SELECT answer_composition_kind, EXISTS(SELECT 1 FROM agent.turn_rules_execution r WHERE r.turn_id=t.turn_id) FROM agent.turn t WHERE turn_id=%s",
            (case.turn.turn_id,),
        ).fetchone()
    assert message["citation_preview"]["status"] == "ready", (
        message["citation_preview"],
        shape,
    )
    assert message["citation_preview"]["native_body_citations"] == [
        c.model_dump(mode="json") for c in case.turn.completion.native_body_citations
    ]
    assert message["assistant_text"] == case.turn.assistant_text
    assert case.service.get_world_pointer(case.world) == pointer
    opened = case.client.get(
        f"/api/live/agent/worlds/{case.world}/conversation/turns/{case.turn.turn_id}/native-body-excerpts/0"
    )
    assert (
        opened.status_code == 200
        and opened.json()["citation"]
        == message["citation_preview"]["native_body_citations"][0]
    )



def reference_bundle(kind='object', schema='dmb_authored_references_v2'):
    ref=dict(schema='dmb_authored_graph_reference_v1',managed_world_id='world-one',native_world_id='native',binding_version=1,graph_revision='revision',node_id='node',label='Selected object')
    if kind=='source':
        ref=dict(schema='dmb_authored_source_reference_v1',managed_world_id='world-one',native_world_id='native',binding_version=1,knowledge_revision='revision',source_artifact_id='recap',source_revision_id='saved-revision',evidence_ref_id='evidence',content_sha256='a'*64,selection_kind='full_document',section_id=None,label='Selected recap')
    return dict(schema=schema,references=[ref])

@pytest.mark.parametrize('kind,schema',[('object','dmb_authored_graph_references_v1'),('object','dmb_authored_references_v2'),('source','dmb_authored_references_v2')])
def test_existing_selection_versions_roundtrip_without_execution_or_source_content(kind,schema):
    raw=[reference_bundle(kind,schema)];before=deepcopy(raw)
    assert project_references(raw,'world-one')==raw[0]
    assert raw==before
    assert set(project_references(raw,'world-one'))=={'schema','references'}

@pytest.mark.parametrize('raw',[None,[]])
def test_absent_input_stays_absent(raw):
    assert project_references(raw,'world-one') is None

@pytest.mark.parametrize('change',['world','ambiguous','unknown','malformed','duplicate','null_capture'])
def test_invalid_or_ambiguous_selection_never_becomes_display_or_authority(change):
    raw=[reference_bundle()]
    if change=='null_capture':raw=[None]
    elif change=='world':raw[0]['references'][0]['managed_world_id']='foreign'
    elif change=='ambiguous':raw.append(deepcopy(raw[0]))
    elif change=='unknown':raw[0]['schema']='unregistered'
    elif change=='duplicate':raw[0]['references']*=2
    else:raw[0]['references'][0]['reader_authority']='forged'
    with pytest.raises(ApplicationStateIntegrityError,match='cannot be displayed safely'):
        project_references(raw,'world-one')


@pytest.mark.parametrize("surface", ["build", "plan"])
def test_related_saved_page_preview_reuses_exact_claim_without_source_io(surface):
    row = native_row(surface)
    page = dict(world_id=row["world_id"], document_id=str(uuid4()), registry_revision=3,
                title="Edge", visibility="internal", content_sha256="b" * 64)
    claim = dict(kind="related_page_claim", text="Edge has an old bath house.",
                 read_id=str(uuid4()), page=page)
    row["assistant_text"] = claim["text"]
    row["completion"].update(answer_segments=[claim], native_body_citations=[],
                              answer_context_status="authored_grounded")
    original = deepcopy(row)
    assert project(row)["answer_segments"] == [claim]
    assert row == original
    for change in ("world", "read", "revision", "digest", "surface", "text"):
        damaged = deepcopy(row)
        segment = damaged["completion"]["answer_segments"][0]
        if change == "world": segment["page"]["world_id"] = "another-world"
        elif change == "read": segment["read_id"] = "invalid"
        elif change == "revision": segment["page"]["registry_revision"] = 0
        elif change == "digest": segment["page"]["content_sha256"] = "invalid"
        elif change == "surface":
            damaged["surface_id"] = damaged["completion"]["surface_id"] = "play"
        else: damaged["assistant_text"] = "Different visible answer"
        assert project(damaged)["status"] == "details_required", change


def test_persisted_native_plan_related_claim_survives_lightweight_reload_without_full_turn(
        lane, tmp_path, monkeypatch, native_read_admission_probes):
    from tests.test_native_plan_assertions import _ordinary_native_case
    from application_state.agent_conversation import library, repository
    _ordinary_native_case(lane, tmp_path, monkeypatch, False, False, None, None,
                          False, native_read_admission_probes, related_page=True)
    def forbidden(*args, **kwargs):
        raise AssertionError("Lightweight authored citations loaded a full turn")
    with monkeypatch.context() as patch:
        patch.setattr(repository, "_turn_from_row", forbidden)
        first = library.read_active_messages(lane.world.world_id)
        reloaded = library.read_active_messages(lane.world.world_id)
    assert first == reloaded
    message = first["messages"][-1]
    preview = message["citation_preview"]
    assert preview["status"] == "ready"
    claims = [s for s in preview["answer_segments"] if s["kind"] == "related_page_claim"]
    assert len(claims) == 1
    assert claims[0]["page"]["world_id"] == lane.world.world_id
    assert claims[0]["page"]["title"] == "Saved Edge page"
    assert "\n".join(s["text"] for s in preview["answer_segments"]) == message["assistant_text"]


def session_summary():
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    from application_state.agent_conversation.authored_excerpt_blocks import block_handle
    supports=[]
    run=str(uuid4())
    for ordinal,kind in enumerate(("scene_note", "closing_reflections")):
        text=("The gate stayed closed. 🐸\r\n" if ordinal==0 else "Ask which path to take next.")
        digest=sha256(text.encode()).hexdigest()
        element="scene:gate" if ordinal==0 else None
        entry=canonical_sha256(dict(kind=kind,element_id=element,ordinal=ordinal))
        identity=dict(source_kind="session",object_id=run,revision="54",
                      body_sha256=digest,owner_sha256="b"*64,entry_identity=entry)
        handle="q"+canonical_sha256(identity)
        end=len(text.encode())
        supports.append(dict(kind="authored_excerpt",text=text,source_handle=handle,
            source_name="Gate rehearsal — notes and reflections",**identity,
            block_handle=block_handle(handle,0,end,digest),partition_version="markdown_source_blocks_v1",
            byte_start=0,byte_end=end,block_sha256=digest,source_ordinal=ordinal,
            entry_kind=kind,element_id=element,checkpoint_content_sha256="c"*64))
    return dict(kind="session_summary",text="The rehearsal left the route unresolved.",supports=supports)


def test_plan_summary_preserves_exact_saved_entry_pins_and_native_indexes():
    row=native_row("plan")
    summary=session_summary()
    row["completion"]["answer_segments"].insert(0,summary)
    row["completion"]["native_body_citations"][0]["segment_index"]=1
    row["completion"]["answer_context_status"]="source_grounded"
    row["assistant_text"]=summary["text"]+"\n"+row["assistant_text"]
    original=deepcopy(row)
    result=project(row)
    assert result["status"]=="ready"
    assert result["answer_segments"][0]==summary
    assert result["native_body_citations"][0]["segment_index"]==1
    assert row==original
    for mutation in ("text","entry","block","owner","source","surface","extra"):
        damaged=deepcopy(row)
        support=damaged["completion"]["answer_segments"][0]["supports"][0]
        if mutation=="text": support["text"]+=" changed"
        elif mutation=="entry": support["entry_identity"]="f"*64
        elif mutation=="block": support["block_sha256"]="f"*64
        elif mutation=="owner": support["owner_sha256"]="f"*64
        elif mutation=="source": support["source_kind"]="play"
        elif mutation=="surface": damaged["surface_id"]=damaged["completion"]["surface_id"]="play"
        else: support["execution"]={}
        assert project(damaged)["status"]=="details_required",mutation


def test_persisted_summary_lightweight_reload_uses_no_full_turn(plan_adapter, monkeypatch):
    import asyncio,json
    from tests.test_plan_session_summaries import stage_summary
    from tests.test_plan_jev_writer import WriterWire
    from application_state.agent_conversation import library,repository
    writer,packet,payload=stage_summary(plan_adapter)
    result=asyncio.run(writer.run(transport=WriterWire(plan_adapter,json.dumps(payload)),api_key="synthetic"))
    def forbidden(*args,**kwargs):
        raise AssertionError("Saved summary presentation loaded a full Turn")
    with monkeypatch.context() as patch:
        patch.setattr(repository,"_turn_from_row",forbidden)
        page=library.read_active_messages(result.world_id)
        reloaded=library.read_active_messages(result.world_id)
    assert page==reloaded
    message=next(m for m in page["messages"] if m["turn_id"]==str(result.turn_id))
    assert message["citation_preview"]["status"]=="ready"
    summary=message["citation_preview"]["answer_segments"][0]
    assert summary==result.completion.answer_segments[0].model_dump(mode="json")
    assert [s["source_ordinal"] for s in summary["supports"]]==[0,1]
    assert all(s["object_id"]==packet["run_id"] and s["revision"]=="4" for s in summary["supports"])
