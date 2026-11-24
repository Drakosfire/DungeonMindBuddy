"""Ordinary Build HTTP/default factory proof, not a prebuilt native component."""
import json
from types import SimpleNamespace
from hashlib import sha256
from uuid import UUID, uuid4

import httpx
import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.page_fixtures import create_page_fixture, save_page
from tests.test_native_plan_assertions import lane as lane, publish, admit_unrelated
from tests.test_build_jev_estimated_continuations import counter
from application_state.agent_conversation import AgentConversationService, types as t
from application_state.agent_conversation.native_plan_assertions import POLICY as NATIVE_ANSWER_POLICY
from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1, AuthoredGraphReferencesV1
from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot


@pytest.mark.parametrize('failure,with_draft,saved,proposal',
    [(f,d,s,False) for f,d,s in ([(f,d,False) for f in (None,'revision','node','reference_world') for d in (False,True)]
        +[(None,d,True) for d in (False,True)]+[(f,False,True) for f in ('section_scope','selection_text')])]
    +[(f,True,False,mode) for mode in (True,'image')
        for f in (None,'native_work','rules_frame','attempt_count','sdk_model','stale_rules','used_rules')]
    +[('unsafe_direction',True,False,'image')])
def test_fresh_build_default_factory_answers_human_reference_and_reopens_exact_support(lane, tmp_path, monkeypatch, failure, with_draft,saved,proposal):
    _fresh_case(lane,tmp_path,monkeypatch,failure,with_draft,saved,proposal)


def test_aw_edge_table_proposal_saves_and_reopens(lane, tmp_path, monkeypatch):
    table = (
        "| NPC | Job | Detail |\n| --- | --- | --- |\n"
        "| Nia | Baker | Carries a copper bell |\n"
        "| Oren | Ferryman | Keeps a tide diary |\n"
        "| Tavi | Mason | Carves tiny birds |\n"
        "| Ivo | Cobbler | Sings while working |\n"
        "| Mara | Courier | Knows the flood routes |\n"
        "| Sela | Gardener | Grows striped mint |"
    )
    _fresh_case(
        lane, tmp_path, monkeypatch, None, True, False, True,
        message="Create six NPCs for Edge, with jobs and a distinguishing detail, and add them as a table.",
        proposal_markdown=table,
    )


def test_build_proposal_without_a_target_returns_selection_guidance(lane, tmp_path, monkeypatch):
    _fresh_case(lane, tmp_path, monkeypatch, "target_unavailable", True, False, True)


@pytest.mark.parametrize("boundary_scope", ["unique", "mixed", "caret", "ambiguous", "missing", "different", "stale", "foreign", "page_end", "page_body"])
def test_build_native_paragraph_proposal_replays_exact_boundary(lane, tmp_path, monkeypatch, boundary_scope):
    location = {"ambiguous": "", "missing": " in North"}.get(boundary_scope, " in East")
    message = {
        "caret": "Add two ordinary paragraphs about how the station maintains this road.",
        "page_end": "Append a line about a copper lamp at the end of this page.",
        "page_body": "Replace the whole page with a paragraph about a copper lamp.",
        "different": "On the separate Lanterns page, add a line after the orchid paragraph in East.",
    }.get(boundary_scope, f"After the orchid paragraph{location}, add a line about a copper lamp.")
    callouts = (
        "> [!READ-ALOUD] Watchtower\n> A copper lamp glows in the window.\n\n"
        "> [!GM-NOTE] Signal\n> Keep its meaning private."
    ) if boundary_scope == "mixed" else None
    _fresh_case(
        lane, tmp_path, monkeypatch, None, True, False, True, contextual=boundary_scope,
        message=message, proposal_markdown=callouts,
    )


@pytest.mark.parametrize("disposition", ["ready", "wrong_kind", "different_page", "remapped_inventory"])
def test_ordinary_build_graph_reference_replays_without_writer(lane, tmp_path, monkeypatch, disposition):
    request = ("Insert a reference to the selected object on the separate Lanterns page."
               if disposition == "different_page"
               else "Insert a reference to the selected object after the orchid paragraph in East.")
    _fresh_case(lane, tmp_path, monkeypatch, None, True, False, True, contextual="unique",
                message=request,
                graph_reference=disposition)


@pytest.mark.parametrize(("message", "disposition"), [
    ("Move the Harbour map to the empty slot on its right.", "ready"),
    ("What would happen if we moved the Harbour map to the right?", "discussion"),
    ("Move the Harbour map to the right slot in the Watchtower row.", "different_row"),
    ("Move the Harbour map to the slot on its right.", "foreign_capture"),
    ("Move the Harbour map to the slot on its right.", "forged_editor"),
    ("What would happen if we moved the Harbour map to the next slot?", "other_discussion"),
    ("How would it look in the empty slot?", "other_discussion"),
    ("How would it look in the empty slot?", "other_discussion_tied_work"),
    ("Move the Harbour map to the empty slot on its right.", "tied_menu"),
    ("Move the Harbour map beside the departure advice to the empty slot on its right.", "duplicate_context"),
])
def test_ordinary_build_image_move_replays_inert_review(lane, tmp_path, monkeypatch, message, disposition):
    _fresh_case(lane, tmp_path, monkeypatch, None, False, False, False,
                message=message, image_move=disposition)


def test_ordinary_read_only_discussion_clarifies_a_tied_source_scope(lane, tmp_path, monkeypatch):
    _fresh_case(
        lane, tmp_path, monkeypatch, "discussion_source_tie", False, False, False,
        message="Describe what the image shows and how it relates to the surrounding notes.",
        requested_work="discuss",
    )


def test_deferred_image_advice_clarifies_before_graph_preparation(lane, tmp_path, monkeypatch):
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter

    def inspect(adapter, provider):
        assert provider == "typesafe"
        assert callable(adapter.prepare_deferred_build_query)

    def unexpected_graph_settlement(*args):
        raise AssertionError("Source-scope clarification must precede Graph settlement")

    monkeypatch.setattr(_PolicyExecutionAdapter, "settle_deferred_build_query", unexpected_graph_settlement)

    _fresh_case(
        lane, tmp_path, monkeypatch, "discussion_source_tie", False, False, False,
        message="How would the Harbour map look in the slot to its right?",
        requested_work="discuss", image_move="other_discussion", before_provider=inspect,
    )


def test_graph_nomination_preparation_uses_the_admitted_build_capture(lane, tmp_path, monkeypatch):
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.services import build_graph_reference

    message = "After the orchid paragraph in East, add a line about a copper lamp."
    prepared = []

    def inspect(adapter, provider):
        if provider != "typesafe" or prepared:
            return
        execution = adapter.fence.turn.graph_context_execution
        principal = adapter.native_query_context.principal
        selected = build_graph_reference.captured_build_graph_reference(execution)
        assert selected is not None

        def admitted_candidates(world_id, caller):
            assert world_id == lane.world.world_id
            assert caller is principal
            return (build_graph_reference.BuildGraphReferenceCandidate(reference=selected, entity_kind="threat"),)

        monkeypatch.setattr(build_graph_reference, "read_build_graph_reference_candidates", admitted_candidates)
        decision = build_graph_reference.prepare_build_graph_reference_decision(
            execution, principal, title="Edge", dialogue=(),
        )
        assert decision.question == message
        assert decision.basis == execution.policy.action.write_capability.basis
        assert decision.author_selected == selected
        state = decision.request().state
        assert state["author_selected_object"] == "object1"
        assert state["graph_objects"]["object1"]["name"] == selected.label
        assert selected.node_id not in decision.request().model_dump_json()
        with monkeypatch.context() as patch:
            changed = selected.model_copy(update={"graph_revision": "changed"})
            candidate = build_graph_reference.BuildGraphReferenceCandidate(reference=changed, entity_kind="threat")
            patch.setattr(build_graph_reference, "read_build_graph_reference_candidates", lambda *_: (candidate,))
            with pytest.raises(ApplicationStateConflictError, match="identity changed"):
                build_graph_reference.prepare_build_graph_reference_decision(
                    execution, principal, title="Edge", dialogue=(),
                )
        prepared.append(decision)

    _fresh_case(lane, tmp_path, monkeypatch, None, True, False, True,
                contextual="unique", message=message, before_provider=inspect)
    assert len(prepared) == 1


@pytest.mark.parametrize("reference_image", ["saved", "unbound", "wrong_same_page", "saved_large"])
def test_build_selected_revision_uses_only_the_bound_saved_image(lane, tmp_path, monkeypatch, reference_image):
    _fresh_case(lane, tmp_path, monkeypatch, None, True, False, True, reference_image=reference_image)


def test_image_grounded_revision_continues_with_its_original_image(lane, tmp_path, monkeypatch):
    _fresh_case(lane, tmp_path, monkeypatch, "target_unavailable", True, False, True,
        reference_image="saved")


def _fresh_case(lane,tmp_path,monkeypatch,failure,with_draft,saved,proposal,*,recovery_dsn=None,recovery_mutation=None,retry_mutation=None,connected_review=None,native_body=None,authored_source=None,historical_query_versions=None,direct_source=False,native_source_text=None,before_provider=None,message=None,capture_write=False,selection_probabilities=None,reference_image=None,saved_statblock=False,proposal_markdown=None,requested_work=None,dispatch=None,source_need="source_lookup",read_optional_page=False,variant_validation="valid",lore_limitation=False,contextual=False,graph_reference=None,image_move=None,source_answer_output=None,lore_title="Glass Regent",lore_legacy_menu=False):
    if lore_legacy_menu:
        from application_state.agent_conversation import build_intentional_response as intent
        work, guidance = intent._PRE_LORE_OUTCOME_WORK, intent._PRE_LORE_OUTCOME_GUIDANCE
        monkeypatch.setattr(intent, 'WORK', work)
        monkeypatch.setattr(intent, 'GUIDANCE', guidance)
        monkeypatch.setattr(intent, 'MENU_DIGEST', intent.digest(intent.question(guidance=guidance, work_options=work)))
        monkeypatch.setattr(intent, 'RESOLVER_DIGEST', intent._resolver_digest(work))
        # The function's default captured the new digest at import time; emulate
        # the old producer's actual instructions as well as its menu commitments.
        instructions = intent.decision_instructions
        old_menu = intent.MENU_DIGEST
        monkeypatch.setattr(intent, 'decision_instructions',
            lambda menu_digest=old_menu: instructions(menu_digest))
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import native_graph_reads as native, managed_world_graph_projection as managed
    from apps.live_control_server.services import build_jev_runtime as factory
    if historical_query_versions is not None:
        from dataclasses import replace
        from application_state.agent_conversation.native_plan_assertions import NativeGraphQueryV3
        prepare_current = native.prepare_query
        def prepare_historical_first(*args, **kwargs):
            context, query = prepare_current(*args, **kwargs)
            if not historical_query_versions:
                raw = query.model_dump(mode='json', by_alias=True, exclude={'object_matches'})
                query = NativeGraphQueryV3.model_validate(raw | {'schema':'dmb_native_graph_query_v3'})
                context = replace(context, query=query)
            historical_query_versions.append(query.schema_)
            return context, query
        monkeypatch.setattr(native, 'prepare_query', prepare_historical_first)
    publish(lane, qualified=True)
    world = lane.world.world_id
    if saved_statblock:
        from apps.live_control_server.services import statblock_saved_revision
        from application_state.world_mechanics.types import MechanicsLocator

        locator = MechanicsLocator(provider="dungeonmind", statblock_id="sb_meatmind",
            revision_id="rev_meatmind", contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0", definition_digest="sha256:" + "a" * 64)
        draft_id = str(uuid4())
        definition = {"identity": {"name": "Meat Mind"}, "vitality": {"hit_points": 41}}
        if dispatch or requested_work == "draft_in_conversation":
            from tests.test_statblock_acceptance_reconciliation import _definition

            definition = _definition().model_dump(mode="json")
        monkeypatch.setattr(statblock_saved_revision, "iter_saved_mechanics",
            lambda root, *, world_id: [("Meat Mind", draft_id, locator)] if world_id == world else [])
        pdf_support = {"scope": {"managed_world_id": world, "native_world_id": world,
                                 "binding_version": 1, "revision_id": lane.repo.get_head(world).head_revision_id,
                                 "scope_mode": "world", "campaign_id": None},
                       "support": [{"assertion_id": "assertion:fixture", "evidence_ref_id": "pdf-region:fixture",
                                    "text": "Hit Points 41"}]}
        if saved_statblock in {"associated", "by-name"}:
            from apps.live_control_server.integrations.dungeonmind import native_registry_source
            from apps.live_control_server.services import native_graph_inspection, native_pdf_evidence
            monkeypatch.setattr(native_registry_source, "read_repository", lambda: lane.repo)
            monkeypatch.setattr(native_pdf_evidence, "reviewed_pdf_regions", lambda *args, **kwargs: ("crop",))
            monkeypatch.setattr(native_graph_inspection, "statblock_pdf_support",
                                lambda ref, *_, **__: pdf_support | {"scope": pdf_support["scope"] | {"revision_id": ref.graph_revision}})

        def open_statblock(root, *, world_id, draft_id, revision_id):
            assert world_id == world and revision_id == locator.revision_id
            return {"world_id": world_id, "draft_id": draft_id,
                    "locator": locator.model_dump(mode="json"), "resource": {"definition": definition}}
        monkeypatch.setattr(statblock_saved_revision, "open_version", open_statblock)
    original_revision = lane.repo.get_head(world).head_revision_id
    page = create_page_fixture(tmp_path, world_id=world, campaign_id=world, title='Working page',
        kind='worldbuilding_source', source_domain='worldbuilding', document_class='lore',
        authority_state='draft', visibility_state='internal')
    image_markdown = ''
    if reference_image:
        from io import BytesIO
        from PIL import Image
        from application_state import media

        original = BytesIO()
        if reference_image == "saved_large":
            from random import Random

            fixture = Image.frombytes("RGB", (1024, 1024), Random(7).randbytes(1024 * 1024 * 3))
            fixture.paste((217, 22, 67), (0, 0, 64, 64))
        else:
            fixture = Image.new("RGB", (64, 48), (217, 22, 67))
        fixture.save(original, format="PNG")
        asset = media.stage_image(original.getvalue(), "local_operator", {"fixture": "bath house map"})
        wrong = media.stage_image(original.getvalue(), "local_operator", {"fixture": "unrelated artwork"})
        image_markdown = (f"![Other artwork](dmb-media:{wrong['asset_id']})\n\n"
            + "Unrelated introduction.\n\n"
            + f"![Bath house map](dmb-media:{asset['asset_id']})\n\n")
    save_page(tmp_path, page.document_id, '# Working page\n\n'
        + (image_markdown if reference_image in {"saved", "wrong_same_page", "saved_large"} else '') + 'A proposed conversation.\n')
    if image_move:
        from io import BytesIO
        from PIL import Image
        from application_state import media
        from application_state.content import pages
        from application_state.content.markdown_source_blocks import source_block_spans
        from application_state.content.page_presentation import BlockBinding, PagePresentation, Row, Slot

        picture = BytesIO()
        Image.new("RGB", (30, 20), (48, 75, 65)).save(picture, "PNG")
        asset_id = str(media.stage_image(picture.getvalue(), "local_operator", {"fixture": "Harbour map"})["asset_id"])
        media_markdown = f"![Harbour map](dmb-media:{asset_id})"
        rows = [("harbour-row", "left-slot", "right-slot", [("map-block", media_markdown)])]
        if image_move == "duplicate_context":
            rows[0][3].insert(0, ("when-block", "Leave after sunset and the third bell."))
            rows.append(("inn-row", "inn-left", "inn-right", [
                ("coat-block", "Borrow a dry coat from the innkeeper."),
                ("repeat-map", media_markdown),
            ]))
        markdown = "\n\n".join(text for _, _, _, row in rows for _, text in row) + "\n"
        raw = markdown.encode()
        bindings = {
            block_id: BlockBinding(id=block_id, byte_start=start, byte_end=end, sha256=sha256(raw[start:end]).hexdigest())
            for block_id, (start, end) in zip(
                (block_id for _, _, _, row in rows for block_id, _ in row), source_block_spans(markdown), strict=True,
            )
        }
        layout = PagePresentation(markdown_sha256=sha256(raw).hexdigest(), items=[
            Row(id=row_id, min_height=16, line_mode="border", slots=[
                Slot(id=left_id, width=7, blocks=[bindings[key] for key, _ in row]),
                Slot(id=right_id, width=5, blocks=[]),
            ]) for row_id, left_id, right_id, row in rows
        ])
        saved_basis = pages.committed_page(page.document_id, world_id=world)
        pages.commit_page(page.document_id, markdown, world_id=world,
                          expected_revision=saved_basis.page.object_revision,
                          expected_working_copy_revision=saved_basis.working_copy_revision,
                          page_presentation=layout)
        image_editor = json.dumps({"type": "doc", "content": [{
            "type": "pageRow", "attrs": {"id": row_id, "min_height": 16, "line_mode": "border"},
            "content": [
                {"type": "pageSlot", "attrs": {"id": left_id, "width": 7}, "content": [{
                    "type": "paragraph", "attrs": {"pageBlockId": key}, "content": [
                        {"type": "mediaImage", "attrs": {"assetId": asset_id, "alt": "Harbour map"}}
                        if text == media_markdown else {"type": "text", "text": text},
                    ],
                } for key, text in row]},
                {"type": "pageSlot", "attrs": {"id": right_id, "width": 5}},
            ],
        } for row_id, left_id, right_id, row in rows]})
    source = get_workspace_document_snapshot(tmp_path, page.document_id)
    draft = None
    editor_json = None
    if with_draft:
        from application_state.agent_conversation.build_draft_context import BuildDraftSnapshotV1, BuildDraftContextRequestV1
        from tests.application_state.test_agent_conversation_postgres import _new
        service = AgentConversationService()
        conversation = _new(service,world)
        pointer = service.get_world_pointer(world)
        text = image_markdown + 'An unsaved orchid possibility. Never a played fact. 🌸'
        if contextual:
            def block(kind, content, **attrs):
                node = {"type": kind, "content": [{"type": "text", "text": content}]}
                return node | ({"attrs": attrs} if attrs else {})

            protected = []
            protected_markdown = ""
            if contextual in {"mixed", "caret"}:
                protected = [{
                    "type": "callout", "attrs": {"kind": "gm-note", "label": "Keep hidden"},
                    "content": [block("paragraph", "Do not reveal the orchid.")],
                }]
                protected_markdown = "> [!GM-NOTE] Keep hidden\n> Do not reveal the orchid.\n\n"
            editor_json = json.dumps({"type": "doc", "content": [
                block("heading", "West", level=2), block("paragraph", text),
                *protected, block("heading", "East", level=2), block("paragraph", text),
            ]}, ensure_ascii=False)
            text = f"## West\n\n{text}\n\n{protected_markdown}## East\n\n{text}\n"
        snapshot = BuildDraftSnapshotV1(world_id=world,document_id=page.document_id,
            registry_revision=source.loaded_revision,content_sha256=source.content_sha256,visibility='internal',
            draft_markdown=text,draft_sha256=sha256(text.encode()).hexdigest(),
            editor_sha256=sha256(editor_json.encode()).hexdigest() if editor_json else 'c'*64,draft_generation=3)
        draft = BuildDraftContextRequestV1(snapshot=snapshot,conversation_id=conversation.conversation_id,
            expected_pointer_revision=pointer.revision)
    selected = AuthoredGraphReferencesV1(references=(AuthoredGraphReferenceV1(managed_world_id=world,
        native_world_id=world, binding_version=1, graph_revision=original_revision,
        node_id=lane.ids['B'], label='DISPLAY ONLY: never evidence'),))
    if saved_statblock in {"associated", "by-name"}:
        from apps.live_control_server.services import statblock_definition_validation
        from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import compute_definition_digest
        from apps.live_control_server.integrations.dungeonmind_statblocks.generated import ValidationReceiptV1

        def validate_variant(*, definition, client=None):
            if variant_validation is None:
                return SimpleNamespace(validation_receipt=None)
            if variant_validation == "malformed":
                raise ValueError("validation digest mismatch between response and receipt")
            digest = "sha256:" + "0" * 64 if variant_validation == "mismatched" else compute_definition_digest(definition)
            status = "valid" if variant_validation == "mismatched" else variant_validation
            receipt = ValidationReceiptV1.model_validate(dict(definition_digest=digest,
                status=status, issues=[], mode="editor_preview",
                canonicalizer_version="statblock-canonicalizer-v1",
                validator_version="statblock-validator-v1.2", validated_at="2026-01-01T00:00:00Z"))
            return SimpleNamespace(definition_digest=digest, validation_receipt=receipt)

        monkeypatch.setattr(statblock_definition_validation, "validate_definition", validate_variant)
        from application_state.world_mechanics import service as associations
        from application_state.world_mechanics.types import WorldMechanicsTarget
        from apps.live_control_server.services import world_creature_selection

        target = WorldMechanicsTarget(
            managed_world_id=world, native_world_id=world, binding_version=1,
            graph_revision_id=original_revision, node_id=lane.ids["B"],
            label="Meat Mind", kind="creature", role="", campaign_scope=None,
        )
        record = SimpleNamespace(
            association_id=uuid4(),
            request=SimpleNamespace(target=target, draft_id=draft_id),
            proof=SimpleNamespace(locator=locator),
        )
        monkeypatch.setattr(associations, "list_current", lambda **kwargs: [record])
        monkeypatch.setattr(world_creature_selection, "catalog", lambda *args, **kwargs: SimpleNamespace(
            managed_world_id=world, native_world_id=world, binding_version=1, revision_id=kwargs["revision_id"], head_revision_id=lane.repo.get_head(world).head_revision_id if saved_statblock == "by-name" or (dispatch and kwargs["revision_id"] != original_revision) else original_revision, targets=(target,),
        ))
        monkeypatch.setattr(statblock_saved_revision, "iter_saved_mechanics", lambda *args, **kwargs: [
            *([("Meat Mind", str(uuid4()), locator.model_copy(update={"revision_id": "rev_wrong"}))] if saved_statblock == "associated" else []),
            ("Meat Mind", draft_id, locator),
        ])
    if failure in {'revision','node','reference_world'}:
        field,value = {'revision':('graph_revision','rev:missing'), 'node':('node_id','ent:missing'),
            'reference_world':('managed_world_id','foreign-world')}[failure]
        selected = selected.model_copy(update={'references':(selected.references[0].model_copy(update={field:value}),)})
    if authored_source or direct_source == 'covered-batch' or native_source_text is not None:
        from dungeonmind.application.vnext import publish_native_text_source_evidence, list_admitted_native_text_sources
        from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
        from graph_memory.vnext.domain_runtime import dungeonbuddy_world_domain_contract, dungeonbuddy_dnd5e_custom_predicate_profile
        from tests.test_native_plan_assertions import NOW, GM
        from apps.live_control_server.integrations.dungeonmind.native_corpus_source import prepare_native_source_context
        from application_state.agent_conversation.authored_graph_references import AuthoredSourceReferenceV1, AuthoredReferencesV2
        from application_state.agent_conversation.native_source_catalog import section_catalog
        human_text=native_source_text or '# Opening\nA proposed note.\n# Episode\nThe source describes a source-local episode. 🌿\n'
        raw=human_text.encode()
        admission=publish_native_text_source_evidence(repository=lane.repo,domain_contract=dungeonbuddy_world_domain_contract(),
            semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),request=NativeTextSourceAdmissionV1(
                space_id=world,admission_id='human-selected-source',expected_parent_revision_id=lane.repo.get_head(world).head_revision_id,
                created_at=NOW,body_text=human_text,expected_body_sha256=sha256(raw).hexdigest(),source_classification='dungeonbuddy.source:session_recap',authority='primary',
                visibility={'kind':'labels_any','labels':['dungeonbuddy.visibility:gm']},spans=[dict(client_ref='opening',evidence_role='context',start_byte=0,end_byte=len(raw),expected_slice_sha256=sha256(raw).hexdigest())]))
        if authored_source:
            context=prepare_native_source_context(managed_world_id=world,principal=GM,repository=lane.repo,
                resolve_identity=lambda _:SimpleNamespace(managed_world_id=world,native_world_id=world,binding_version=1,provisioning_id=None))
            meta=next(row for row in list_admitted_native_text_sources(context.access).sources if row.source_artifact.source_artifact_id==admission.source_artifact_id)
            sections=section_catalog(human_text,source_artifact_id=admission.source_artifact_id,native_source_revision_id=admission.source_revision_id,content_sha256=sha256(raw).hexdigest())
            source_ref=AuthoredSourceReferenceV1(managed_world_id=world,native_world_id=world,binding_version=1,knowledge_revision=context.authority.revision_id,
                source_artifact_id=admission.source_artifact_id,source_revision_id=admission.source_revision_id,evidence_ref_id=meta.evidence_ref_ids[0],content_sha256=sha256(raw).hexdigest(),
                selection_kind='full_document' if authored_source=='full_document' else 'section',section_id=None if authored_source=='full_document' else sections[1].section_id,label='DISPLAY ONLY source label')
            selected=AuthoredReferencesV2(references=(() if authored_source=='source_only' else selected.references)+(source_ref,))
    admit_unrelated(lane, 'after-human-pick-before-http')
    current_revision = lane.repo.get_head(world).head_revision_id
    assert current_revision != original_revision
    if graph_reference:
        from apps.live_control_server.services import build_graph_reference

        reference = selected.references[0].model_copy(update={"graph_revision": current_revision})
        selected = selected.model_copy(update={"references": (reference,)})
        identities = [{"node_id": reference.node_id, "label": reference.label, "kind": "threat", "selectable": True}]
        if graph_reference == "remapped_inventory":
            from dataclasses import replace

            identities.append({"node_id": "fixture-other", "label": "Other threat", "kind": "threat", "selectable": True})
            original_complete = AgentConversationService.complete_build_graph_reference_turn

            def complete_with_remap(service, *, decision, **kwargs):
                first, second = decision.candidates
                remapped = second.model_copy(update={"reference": second.reference.model_copy(update={"node_id": "fixture-remapped"})})
                altered = replace(decision, candidates=(first, remapped))
                assert altered.request() == decision.request()
                return original_complete(service, decision=altered, **kwargs)

            monkeypatch.setattr(AgentConversationService, "complete_build_graph_reference_turn", complete_with_remap)
        monkeypatch.setattr(build_graph_reference, "authoring_identities", lambda scope, principal: {
            "scope": {"managed_world_id": world, "native_world_id": world, "binding_version": 1,
                      "revision_id": current_revision, "scope_mode": "world", "campaign_id": None},
            "identities": identities,
        })
    binding = SimpleNamespace(managed_world_id=world, native_world_id=world, binding_version=1, provisioning_id=None)
    monkeypatch.setattr(managed, 'resolve_managed_source_identity', lambda _: binding)
    monkeypatch.setattr(native, 'resolve_managed_world_binding', lambda _: binding)
    if authored_source=='source_only':
        from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
        def no_object_binding(_):
            raise WorldGraphProjectionServiceError('No active object Graph',code='native_graph_binding_missing',status_code=409)
        monkeypatch.setattr(native,'resolve_managed_world_binding',no_object_binding)
    monkeypatch.setattr(agent, 'repo_root', lambda: tmp_path)
    monkeypatch.setattr(agent, 'session_dir', lambda: tmp_path / 'sessions')
    monkeypatch.setattr(agent, '_managed_world_root', lambda: tmp_path)
    monkeypatch.setattr('apps.live_control_server.services.build_document_proposal.managed_world_data_root',lambda:tmp_path)
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE', 'local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT', 'local')
    token = 'synthetic-native-build-test-token-1234567890'
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN', token)
    monkeypatch.setenv('TYPESAFE_JEV_API_KEY', 'synthetic-only')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-only')
    monkeypatch.setattr('apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference',
        lambda **_: ('openai-api', 'gpt-6.1-sol', 'https://api.openai.com/v1'))
    classic_calls = []
    def classic(*_args, **_kwargs):
        classic_calls.append('classic_graph_services')
        raise AssertionError('Fresh Build used classic Graph broker instead of shared native access')
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config', classic)

    if read_optional_page:
        monkeypatch.setattr("apps.live_control_server.services.build_related_pages.root", lambda: tmp_path)
        optional_page = create_page_fixture(tmp_path, world_id=world, campaign_id=world,
            title="Optional lore", kind="worldbuilding_source", source_domain="worldbuilding",
            document_class="lore", authority_state="draft", visibility_state="internal")
        save_page(tmp_path, optional_page.document_id, "The local node is proposed to want freedom." if source_answer_output else "This unrelated lore should remain unread.")

    class Decisions(httpx2.AsyncBaseTransport):
        def __init__(self):
            self.calls = []
            self.deny_routing=False
        async def handle_async_request(self, req):
            self.calls.append(req)
            if before_provider is not None:
                before_provider(writer.adapter, 'typesafe')
            body = json.loads(req.content)
            answers = {}
            candidates=body.get('state',{}).get('candidates',[])
            selected={i for i,c in enumerate(candidates) if (saved and c['kind'].startswith('Saved authored page block'))
                or (saved_statblock and c['kind'].startswith('Saved statblock'))
                or ((failure=='used_rules' or failure=='mixed_questions' and writer.review is not None) and c['kind']=='public_rules_lookup')
                or (native_body and c['kind'] in ({'Explicit admitted full-source read; metadata choice, not evidence'} | ({'Source lexical navigation; not evidence or semantic completeness'} if direct_source=='mixed' else set()) if direct_source else {'Source lexical navigation; not evidence or semantic completeness','Explicit full-document read'} | ({'Explicit admitted full-source read; metadata choice, not evidence'} if any(c['kind'].startswith('Navigation scan:') for c in body['state'].get('examined_subjects',[])) else set())))}
            if failure == "deferred_graph_citation":
                selected = {i for i, c in enumerate(candidates) if "Native Graph object;" in c["kind"]}
            if direct_source == 'covered-batch' and candidates:
                scanned = any(c['kind'].startswith('Navigation scan:')
                    for c in body['state'].get('examined_subjects', []))
                kinds = ({'Explicit admitted full-source read; metadata choice, not evidence', 'Exact source section'}
                    if scanned else {'Source lexical navigation; not evidence or semantic completeness'})
                selected = {i for i,c in enumerate(candidates) if c['kind'] in kinds}
            if saved_statblock and "operation" in body["questions"]:
                from application_state.agent_conversation.build_saved_statblock import BuildSavedStatblockReadV1
                events = writer.adapter._broker_execution().events
                if any(isinstance(event, BuildSavedStatblockReadV1) for event in events):
                    examined = body["state"]["examined_subjects"]
                    assert any(row["kind"] == "Saved statblock: acquired exact mechanics in this turn"
                               and row["label"] == "Meat Mind" for row in examined), examined
            current_work = requested_work(writer.adapter.request.message) if callable(requested_work) else requested_work
            for name, question in body['questions'].items():
                if self.deny_routing and name=='requested_work':
                    raise AssertionError('The reviewed operation must not be reselected by a model')
                choices = question['criteria']
                if name == "source_need" and failure == "discussion_source_tie":
                    answers[name] = dict(type="choice", choice="uncertain", confidence=.07,
                                         probabilities={"anchored": .24, "source_lookup": .38, "uncertain": .38})
                    continue
                if name.startswith("image_move_"):
                    assert image_move and "Harbour map" in str(body["state"]["interaction"]["image_move"])
                    assert asset_id not in json.dumps(body)
                    assert all(value not in json.dumps(body) for value in ("map-block", "harbour-row", "left-slot"))
                    advice = image_move in {"other_discussion", "other_discussion_tied_work"}
                    chosen = {"image_move_intent": "other" if advice else "move_existing",
                              "image_move_destination": "same_row_right", "image_move_occurrence": "image1",
                              "image_move_affirmation": "description_or_discussion" if advice or image_move == "discussion"
                                  else "author_requests_move", "image_move_contextual_identity": "image1"}[name]
                    answers[name] = dict(type="choice", choice=chosen, confidence=1,
                                         probabilities={key: float(key == chosen) for key in choices})
                    continue
                if name == "requested_work" and image_move in {"tied_menu", "other_discussion_tied_work"}:
                    voting = {"discuss": .4, "clarify_request": .4, "other_creation": .2}
                    answers[name] = dict(type="choice", choice="other_creation", confidence=.2,
                                         probabilities={key: voting.get(key, 0) for key in choices})
                    continue
                if name == "typed_graph_reference":
                    chosen = "place_existing_reference" if graph_reference else "other_work"
                    answers[name] = dict(type="choice", choice=chosen, confidence=1,
                                         probabilities={key: float(key == chosen) for key in choices})
                    continue
                if "reference_intent" in body["questions"]:
                    chosen = {"work": "place_paragraph", "destination": "current_page", "relation": "after",
                              "anchor_occurrence": "passage2",
                              "reference_nomination": "object1",
                              "scope": "named", "text0": "include", "scope0": "exclude", "scope1": "include",
                              "reference_intent": "different_page" if graph_reference == "different_page" else "place_existing",
                              "object1": "include", "object2": "exclude",
                              "reference_kind_constraint": "requires_or_excludes_type",
                              "reference_kind": "other_kind" if graph_reference == "wrong_kind" else "class1"}[name]
                    answers[name] = dict(type="choice", choice=chosen, confidence=1,
                                         probabilities={key: float(key == chosen) for key in choices})
                    continue
                chosen = ((current_work or ('review_connected_page' if connected_review else 'prepare_image' if proposal=='image' else 'write_current_page' if proposal else 'discuss')) if name=='requested_work' else (source_need(writer.adapter.request.message) if callable(source_need) else source_need) if name=='source_need'
                    else ('select_candidates' if selected and 'select_candidates' in choices else 'finish_retrieval') if name=='operation'
                    else ('include' if int(name.split('_')[-1]) in selected else 'exclude') if name.startswith('candidate_')
                    else "read" if read_optional_page and name.startswith("related_page_")
                    else {"paragraph_work": f"explicit_{contextual}" if contextual in {"page_end", "page_body"} else "place_paragraph",
                          "paragraph_destination": "different_page" if contextual == "different" else "current_page",
                          "paragraph_insertion_location": "unstated",
                          "paragraph_relation": "unresolved" if contextual == "caret" else "after",
                          "paragraph_scope": "unscoped" if contextual in {"ambiguous", "caret"} else "named",
                          "paragraph_text0": "exclude" if contextual == "caret" else "include", "paragraph_scope0": "exclude",
                          "paragraph_scope1": "include" if contextual in {"unique", "mixed", "different"} else "exclude"}[name]
                    if name.startswith("paragraph_")
                    else (native_body if native_body and body['state']['sources'][list(body['state']['sources'])[int(name[1:])]]['kind']=='native_body' else 'direct_support') if name.startswith('s') and name[1:].isdigit() else 'skip')
                assert chosen in choices, (name, choices)
                answers[name] = dict(type='choice', choice=chosen, confidence=1,
                    probabilities=(selection_probabilities if name=='requested_work' and selection_probabilities is not None else {key: float(key == chosen) for key in choices}))
            return httpx2.Response(200, request=req, json=dict(model='jev-1.14.0', answers=answers,
                usage=dict(input_tokens=37, output_tokens=9)))

    class Writer(httpx.AsyncBaseTransport):
        def __init__(self):
            from threading import local
            self.calls = []
            self._execution = local()
            self._last_adapter = None
            self.mode = proposal
            self.review = None
        @property
        def adapter(self):
            return getattr(self._execution, 'adapter', self._last_adapter)
        @adapter.setter
        def adapter(self, value):
            # The fake transport is shared by concurrent HTTP requests. Its
            # provider assertions must inspect that request's own execution.
            self._execution.adapter = value
            self._last_adapter = value
        async def handle_async_request(self,req):
            try:
                return await self._handle(req)
            except Exception as exc:
                import traceback
                traceback.print_exception(exc)
                raise
        async def _handle(self, req):
            mode=self.mode
            self.calls.append(req)
            if before_provider is not None:
                before_provider(self.adapter, 'openai')
            if failure=='retry_unknown':
                raise httpx.ReadTimeout('synthetic unknown writer outcome',request=req)
            body = json.loads(req.content)
            assert body['model'] == self.adapter._broker_execution().policy.provider_roles.writer.model
            current_work = requested_work(self.adapter.request.message) if callable(requested_work) else requested_work
            from application_state.agent_conversation.writer_evidence_selection import native_conversation_terminal

            using_prior_citations = native_conversation_terminal(self.adapter.turn) is not None
            expected_effort = 'medium' if (using_prior_citations and current_work == 'review_lore_page_from_conversation'
                or current_work == 'draft_in_conversation' and saved_statblock == 'associated') else 'low'
            if body.get('reasoning', {}).get('effort') != expected_effort:
                return httpx.Response(400, request=req, json={'error': {
                    'message': 'Unsupported reasoning effort for configured writer',
                    'type': 'invalid_request_error', 'param': 'reasoning.effort',
                    'code': 'unsupported_value'}})
            if reference_image in {'saved', 'saved_large'}:
                from base64 import b64decode
                from io import BytesIO
                from PIL import Image

                assert len(body['input']) == 1 and body['input'][0]['role'] == 'user'
                packet, image = body['input'][0]['content']
                assert packet['type'] == 'input_text'
                assert image['type'] == 'input_image' and image['detail'] == 'high'
                assert 'attached page image' in body['instructions']
                prefix, encoded = image['image_url'].split(',', 1)
                assert prefix == 'data:image/jpeg;base64'
                expected_size = (1024, 1024) if reference_image == "saved_large" else (64, 48)
                if reference_image == "saved_large":
                    assert len(req.content) > 262144
                with Image.open(BytesIO(b64decode(encoded))) as pixels:
                    assert pixels.size == expected_size
                    assert all(abs(a-b) < 5 for a,b in zip(pixels.getpixel((20, 20)), (217, 22, 67)))
                # Only the outgoing transport contains pixels. The unchanged
                # semantic packet is validated below as for a text-only proposal.
                body['input'] = packet['text']
            inputs = [json.loads(body['input'])] if isinstance(body['input'], str) else [json.loads(row['content']) for row in body['input'] if row['content'].lstrip().startswith('{')]
            if mode:
                inputs=[inputs[0]['native_evidence'],inputs[0]['surface_work']]
            from application_state.agent_conversation.native_evidence_view import is_semantic_frame
            frame = next(row for row in inputs if is_semantic_frame(row))
            work = next(row['build_work'] for row in inputs if 'build_work' in row)
            if not mode:
                if requested_work == "review_lore_page" and self.adapter.turn.sequence == 2:
                    assert len(inputs) == 5
                    assert inputs[:2] == [{"conversation": message}, {"conversation": ""}]
                    assert inputs[-1] == frame
                else:
                    from application_state.agent_conversation.retained_conversation import dialogue_messages, current_request_message
                    expected = dialogue_messages(self.adapter.turn.graph_context_execution)
                    if expected is None:
                        expected = [dict(role=role, content=json.dumps({"conversation": pair[role]}))
                            for pair in getattr(self.adapter, "build_frozen_history", ())
                            for role in ("user", "assistant")]
                    current = current_request_message(self.adapter.turn.graph_context_execution)
                    start = 3 if current is not None else 0
                    assert isinstance(body['input'], list)
                    assert len(body['input']) == len(expected) + 3 + (current is not None)
                    if current is not None:
                        assert body['input'][-1] == current
                    for row, wanted in zip(body['input'][start:start+len(expected)], expected, strict=True):
                        assert row['role'] == wanted['role']
                        assert json.loads(row['content']) == json.loads(wanted['content'])
                    assert inputs[start:start+len(expected)] == [json.loads(row['content']) for row in expected]
                    frames = body['input'][:3] if current is not None else body['input'][-3:]
                    assert all(row['role'] == 'user' for row in frames)
                    decoded = [json.loads(row['content']) for row in frames]
                    assert decoded[0] == {"build_work": work}
                    assert set(decoded[1]) == {'lookups', 'ruleset', 'supports'}
                    assert decoded[2] == frame
            if self.adapter.submitted_intent.reviewed_step is not None:
                from application_state.agent_conversation.reviewed_action import writer_scope,SCOPE_KEY
                scope=writer_scope(self.adapter._broker_execution())
                projected = work.get('reviewed_task')
                assert (projected is not None) == (scope is not None)
                if scope is not None:
                    assert projected['task']['text'] == scope['scope']['task']['text']
                    assert projected['objective'] == scope['scope']['objective_context']
                    assert projected['siblings'][0]['selected'] == scope['scope']['sibling_context'][0]['selected']
                if scope is not None:
                    assert scope['scope']['task']['text'] == ('Can I end my move in an occupied space?' if failure == 'mixed_questions' else 'Discuss where the lamp belongs.')
                    assert scope['scope']['sibling_context'][0]['selected'] is False
            if with_draft and "passages" in work['current_draft']:
                from application_state.agent_conversation.native_build_work_view import variant_draft_passages

                assert work['current_draft']['passages'] == variant_draft_passages({
                    "working_draft_context": {"draft_markdown": draft.snapshot.draft_markdown},
                })
            elif with_draft:
                expected_draft = draft.snapshot.draft_markdown
                if reference_image:
                    expected_draft = expected_draft.replace(
                        f"![Other artwork](dmb-media:{wrong['asset_id']})", "[Image: Other artwork]",
                    ).replace(
                        f"![Bath house map](dmb-media:{asset['asset_id']})", "[Image: Bath house map]",
                    )
                    assert all(str(row['asset_id']) not in req.content.decode() for row in (asset, wrong))
                assert work['current_draft']['markdown'] == expected_draft
                if mode:
                    assert body['input'].count(json.dumps(expected_draft, ensure_ascii=False)[1:-1]) == 1
                else:
                    assert sum(expected_draft in row['content'] for row in body['input']) == 1
            handles = [row['assertion_handle'] for row in frame['native_assertions']['assertions']] if frame['native_assertions'] else []
            assert (handles or getattr(self.adapter._broker_execution().policy.action.intent, "authored_references", None) is None
                    or saved_statblock in {"associated", "by-name"}
                    or authored_source == 'source_only'
                    or image_move == "other_discussion"
                    or current_work in {"review_lore_page", "review_lore_page_from_conversation", "review_blank_lore_page"})
            assert 'DISPLAY ONLY' not in str(frame)
            if saved_statblock:
                from application_state.agent_conversation.response_prompt import VARIANT_BASE

                assert (VARIANT_BASE.text in body["instructions"]) == (current_work == "draft_in_conversation")
                expected = {"mechanics": definition if current_work == "draft_in_conversation"
                            else {key: value for key, value in definition.items() if key != "ruleset"}}
                if saved_statblock in {"associated", "by-name"}:
                    expected["reviewed_pdf_excerpts"] = [{"source": "pdf0:0", "text": "Hit Points 41"}]
                if current_work == "draft_in_conversation":
                    expected["variant_source"] = "statblock0"
                    assert work.get("requested_work", {}).get("requested_work") == "draft_in_conversation", work.get("requested_work")
                    assert "statblock_variant" in body["text"]["format"]["schema"]["properties"], (work["requested_work"], [list(row) for row in work["saved_statblocks"]])
                assert work["saved_statblocks"] == [expected]
                assert locator.revision_id not in req.content.decode()
            if (work.get('citation_policy') == 'supplied_source_references_v1'
                    or body['text']['format']['name'] in {'lore_page_response', 'build_reply'}):
                assert 'supporting_quotes containing' not in body['instructions']
                if work['saved_sections'] or work.get('related_pages'):
                    assert 'Do not return supporting_quotes' in body['instructions']
                else:
                    assert 'For saved_source_claim select' not in body['instructions']
            sections = work['saved_sections']
            def source_text(row):
                if 'text' in row:
                    return row['text']
                assert row['body_ref'] == 'current_draft'
                return work['current_draft']['markdown']
            read_ids=[row['selection'] for row in sections]
            if saved:
                assert (read_ids or using_prior_citations) and 'A proposed conversation.' in str(work)
            if mode:
                target = contextual if contextual in {"page_end", "page_body"} else "prose_target" if contextual else "captured"
                candidate=dict(destination='current_page',target=target,replacement_markdown=proposal_markdown or 'A proposed copper lamp.',
                    summary='Proposed detail.',assumptions=['The lamp is invented.'])
                if failure == 'target_unavailable' and len(self.calls) == 1:
                    candidate.update(target='unavailable', replacement_markdown='', summary='Untrusted provider summary.')
                if mode=='image':
                    candidate=dict(prompt='https://not-an-image.test/directive' if failure=='unsafe_direction' else 'A proposed copper lamp beside an orchid.',alt='Proposed copper lamp illustration',purpose='illustration')
                text=json.dumps(candidate)
                response=dict(id='resp_native_build_proposal',object='response',created_at=1,status='completed',
                    model='foreign-model' if failure=='sdk_model' else body['model'],output=[dict(type='message',id='msg_native_build_proposal',role='assistant',
                        status='completed',content=[dict(type='output_text',text=text,annotations=[])])],
                    usage=dict(input_tokens=100,output_tokens=40,total_tokens=140))
                if mode=='image':
                    return httpx.Response(200,request=req,json=response)
                events=[dict(type='response.output_text.delta',sequence_number=1,item_id='msg_native_build_proposal',
                    output_index=0,content_index=0,delta=text),dict(type='response.completed',sequence_number=2,response=response)]
                return httpx.Response(200,request=req,headers={'content-type':'text/event-stream'},
                    content=''.join('data: '+json.dumps(e)+'\n\n' for e in events).encode())
            candidate = dict(schema=NATIVE_ANSWER_POLICY,
                answer_segments=([dict(kind='native_assertion_claim', text='The Graph retains the qualified description.', assertion_handles=handles)] if handles else [])+([dict(kind='saved_source_claim',text='The saved page proposes a conversation.',section_read_ids=read_ids,**({} if work.get('citation_policy') == 'supplied_source_references_v1' or body['text']['format']['name'] in {'lore_page_response', 'build_reply'} else {'supporting_quotes':[source_text(r) for r in sections]}))] if saved else []),
                limitations=[], requested_detail_gaps=[], collaboration=self.review)
            if image_move == "other_discussion":
                candidate["answer_segments"] = [
                    dict(kind="discussion", text="The image would sit to the right of the nearby material."),
                ]
            if saved_statblock in {"associated", "by-name"}:
                candidate["answer_segments"] = [dict(kind="statblock_pdf_claim",
                    source="pdf0:0", quote="Hit Points 41")]
            if saved_statblock and current_work == "draft_in_conversation":
                new_rule = definition["rule_elements"][0] | {"key": "truce", "name": "Terms of Truce", "costs": None}
                variant_schema = body["text"]["format"]["schema"]["properties"]["statblock_variant"]
                fields = next(option["properties"] for option in variant_schema.get("anyOf", [variant_schema])
                              if "properties" in option)
                rule_fields = fields["add_rules"]["items"]["properties"]
                if "authored_quotes" in rule_fields:
                    new_rule = {"rule": new_rule, "authored_quotes": []}
                if "authored_passages" in rule_fields:
                    new_rule = {"rule": new_rule, "authored_passages": []}
                if "carried_condition" in rule_fields:
                    new_rule["carried_condition"] = None
                candidate["statblock_variant"] = {
                    "source": "statblock0",
                    "add_rules": [new_rule],
                    "replace_rules": [],
                }
                if "passage_review" in fields:
                    passages = work["current_draft"]["passages"]
                    review = fields["passage_review"]
                    assert list(passages) == list(review["properties"]) == review["required"]
                    assert "markdown" not in work["current_draft"]
                    candidate["statblock_variant"]["passage_review"] = dict.fromkeys(passages, "omit")
                    if "authored_passages" in rule_fields:
                        offered = rule_fields["authored_passages"]["items"]["enum"]
                        assert offered == list(passages)
                        handle = offered[0]
                        candidate["statblock_variant"]["passage_review"][handle] = "retain"
                        new_rule["authored_passages"] = [handle]
            if (native_body or authored_source) and not using_prior_citations:
                from application_state.agent_conversation import native_corpus as corpus
                acquired = corpus.acquired_body_reads(self.adapter._broker_execution())
                assert acquired
                exposed = frame['native_body_evidence']['excerpts']
                assert bool(exposed) == (bool(authored_source) or native_body != 'irrelevant')
                if exposed:
                    candidate['answer_segments'].append(dict(kind='native_body_claim',
                        text='The source describes a source-local episode.',
                        excerpt_handles=[r['excerpt_handle'] for r in exposed]))
                else:
                    assert all(r.excerpt.text not in json.dumps(frame) for r in acquired)
            if using_prior_citations:
                exposed = frame["native_body_evidence"]["excerpts"]
                assert exposed
                retained = next((event for event in self.adapter.turn.graph_context_execution.events
                    if isinstance(event, t.BuildPriorBodyEvidenceAdmittedV2)), None)
                if retained is None:
                    assert all(row["prior_claim"] == "The source describes a source-local episode."
                        for row in exposed)
                else:
                    assert retained.native_context
                    assert all("prior_claim" not in row for row in exposed)
                candidate["answer_segments"] = [dict(kind="native_body_claim",
                    text="The source describes a source-local episode.",
                    excerpt_handles=[row["excerpt_handle"] for row in exposed])]
            if current_work in {"review_lore_page", "review_lore_page_from_conversation", "review_blank_lore_page"}:
                from apps.live_control_server.services.plan_jev_writer import LORE_PROPOSAL_GUIDANCE

                author_text = self.adapter.turn.user_text
                assert (LORE_PROPOSAL_GUIDANCE in body["instructions"]) == (current_work != "review_blank_lore_page")
                candidate["answer_segments"] = [
                    segment for segment in candidate["answer_segments"]
                    if segment["kind"] == "native_body_claim"
                ]
                if current_work == "review_blank_lore_page":
                    candidate["answer_segments"] = []
                if lore_limitation and candidate["answer_segments"]:
                    candidate["limitations"] = ["missing_requested_details"]
                candidate["collaboration"] = {
                    "kind": "lore_page",
                    "destination": {"request": "current_author_request", "title": lore_title},
                }
                if current_work == "review_lore_page_from_conversation":
                    candidate["collaboration"]["open_questions"] = ["Why did the Regent leave?"]
                    if lore_limitation == "authored_context":
                        candidate["answer_segments"].extend([
                            dict(kind="proposal", label="invented_idea",
                                text="Authored note context, not a played event: The Regent's house stands beside three bridges."),
                            dict(kind="proposal", label="invented_idea",
                                text="Proposed direction: The Regent accepts a truthful memory instead of coins."),
                        ])
            if connected_review:
                section=next(row for row in sections if 'A proposed conversation.' in source_text(row))
                candidate['answer_segments']=([dict(kind='proposal',label='invented_idea',
                    text='# A neighboring workshop\n\n' + '| 1 | An errand awaits. |\n' * 260)]
                    if connected_review=='full_page' else [])
                candidate['collaboration']={'kind':'connected_page','title':'A proposed neighboring workshop',
                    'read_id':str(uuid4()) if connected_review=='foreign_read' else section['selection'],
                    'quote':'A phrase absent from the source.' if connected_review=='foreign_quote' else 'A proposed conversation.',
                    'person_label':None,'relationships':[],'instructions':'Prepare a separate page for author review.'}
            if failure == "mixed_questions" and self.review:
                candidate["answer_segments"] = [
                    dict(kind="discussion", text="We can discuss the route before choosing.")
                ]
                candidate = dict(
                    kind="rules_answer", base_output=candidate,
                    rules_segments=[dict(kind="rules_context", category="gap",
                                         text="No additional applicable rule is established.")],
                    ordered_refs=[dict(domain="base", segment_index=None),
                                  dict(domain="rules", segment_index=0)],
                )
            segment_schema = body['text']['format']['schema'].get('properties', {}).get('answer_segments', {}).get('items', {})
            if (body["text"]["format"]["name"] == "surface_native_evidence_selectors_v7"
                    or segment_schema.get('properties', {}).get('kind', {}).get('const') == 'discussion'):
                candidate["answer_segments"] = [
                    dict(kind="discussion", text="We can explore a truce for this creature.")
                ]
            if source_answer_output:
                if source_answer_output in {'typed', 'typed_gap_format', 'host_schema_echo', 'foreign_source_alias', 'regenerated_quote'}:
                    candidate['answer_segments'] = [dict(kind='related_page_claim',
                        text='The saved lore proposes that the local node wants freedom.',
                        read_id=next(page['selection'] for page in work['related_pages'] if page['title'] == 'Optional lore'))]
                    if source_answer_output == 'foreign_source_alias':
                        candidate['answer_segments'][0]['read_id'] = 'source_foreign'
                    if source_answer_output == 'regenerated_quote':
                        candidate['answer_segments'][0]['supporting_quotes'] = ['The saved lore proposes freedom.']
                    if source_answer_output == 'typed_gap_format':
                        candidate['limitations'] = ['missing_requested_details']
                        candidate['requested_detail_gaps'] = [dict(question_phrase="the local node's alliance")]
                elif source_answer_output in {'uncited', 'creative'}:
                    candidate['answer_segments'] = [dict(kind='discussion', text='The local node wants freedom.' if source_answer_output == 'uncited' else 'We can explore that possibility.')]
                elif source_answer_output == 'empty':
                    candidate['answer_segments'] = []
                    candidate['limitations'] = []
                    candidate['requested_detail_gaps'] = []
                elif source_answer_output in {'lore_stale_gap', 'lore_valid_gap', 'lore_malformed_gap', 'lore_empty_gap', 'lore_invalid_destination', 'lore_null_gap', 'lore_extra_schema'}:
                    candidate['answer_segments'] = [dict(kind='proposal', label='invented_idea',
                        text='Proposed direction: The local node seeks freedom and values its simulated town life. Its deeper plans remain open.')]
                    candidate['limitations'] = ['missing_requested_details']
                    candidate['requested_detail_gaps'] = [dict(question_phrase=(
                        'unresolved motive' if source_answer_output == 'lore_valid_gap'
                        else ['invalid'] if source_answer_output == 'lore_malformed_gap' else 'cosmology I have been operating with'))]
                    if source_answer_output == 'lore_empty_gap':
                        candidate['answer_segments'] = []
                        candidate['collaboration'] = None
                    if source_answer_output == 'lore_null_gap':
                        candidate['collaboration'] = None
                    if source_answer_output == 'lore_invalid_destination':
                        candidate['collaboration']['destination']['request'] = 'prior_author_request'
                elif source_answer_output in {'lore_context_question', 'lore_context_mixed'}:
                    candidate['answer_segments'] = ([] if source_answer_output == 'lore_context_question'
                        else [dict(kind='proposal', label='invented_idea', text='An unsolicited draft.')])
                    candidate['collaboration'] = dict(kind='needs_context', question='  Which subject\n and premise should the page describe?  ')
                elif source_answer_output in {'lore_ack', 'lore_clarify', 'lore_uncited_body'}:
                    candidate['answer_segments'] = [dict(kind='discussion', text='Understood. I will keep the workpad unchanged and create nothing yet.')]
                    if source_answer_output in {'lore_ack', 'lore_clarify'}:
                        candidate['collaboration'] = None
                    if source_answer_output == 'lore_clarify':
                        candidate['answer_segments'][0]['text'] = 'Which subject and premise should the page describe?'
                elif source_answer_output == 'blank_warning':
                    candidate['limitations'] = ['missing_requested_details']
                elif source_answer_output in {'blank_body', 'blank_questions'}:
                    if source_answer_output == 'blank_body':
                        candidate['answer_segments'] = [dict(kind='proposal', label='invented_idea', text='Invented body on an empty page.')]
                    else:
                        candidate['collaboration']['open_questions'] = ['Who wrote the ledger?']
                elif source_answer_output in {'unknown_limit_code', 'retired_gap_field'}:
                    candidate['answer_segments'] = []
                    candidate['limitations'] = ['not_a_limit_code'] if source_answer_output == 'unknown_limit_code' else ['missing_requested_details']
                    candidate['requested_detail_gaps'] = [{'question_phrase': 'obsolete witness'}]
                elif source_answer_output in {'gap', 'gap_format'}:
                    candidate['answer_segments'] = []
                    candidate['limitations'] = ['missing_requested_details']
                    candidate['requested_detail_gaps'] = [dict(question_phrase='the local node’s alliance' if source_answer_output == 'gap' else "the local node's alliance")]
            if 'requested_detail_gaps' not in body['text']['format']['schema'].get('$defs', {}).get('Base', body['text']['format']['schema'])['properties']:
                base = candidate['base_output'] if candidate.get('kind') == 'rules_answer' else candidate
                if base is not None and source_answer_output not in {'lore_malformed_gap', 'retired_gap_field'}:
                    base.pop('requested_detail_gaps', None)
            output_base = body['text']['format']['schema'].get('$defs', {}).get('Base', body['text']['format']['schema'])
            if 'schema' not in output_base['properties']:
                base = candidate['base_output'] if candidate.get('kind') == 'rules_answer' else candidate
                if base is not None and source_answer_output not in {'lore_extra_schema', 'host_schema_echo'}:
                    base.pop('schema', None)
            self.actual_output=json.dumps(candidate)
            return httpx.Response(200, request=req, json=dict(id='resp_native_build', object='response',
                created_at=1, status='incomplete' if failure in {'writer_incomplete_limit','writer_incomplete_filter','writer_incomplete_unknown'} else 'completed', model=body['model'], output=[dict(type='message', id='msg_native_build',
                    role='assistant', status='completed', content=[dict(type='output_text', text=self.actual_output, annotations=[])])],
                usage=dict(input_tokens=100, output_tokens=40, total_tokens=140),
                **({'incomplete_details':{'reason':'max_output_tokens' if failure=='writer_incomplete_limit' else 'content_filter'}}
                    if failure in {'writer_incomplete_limit','writer_incomplete_filter'} else {})))
    decisions, writer = Decisions(), Writer()
    if proposal and failure in {'native_work','rules_frame'}:
        from apps.live_control_server.services import build_document_proposal as proposal_owner,build_image_writer
        selected_owner=build_image_writer if proposal=='image' else proposal_owner
        method='writer_request' if proposal=='image' else '_writer_request'
        original_request=getattr(selected_owner,method)
        def changed_request(*args,**kwargs):
            prepared=original_request(*args,**kwargs)
            packet=json.loads(prepared['input'])
            if failure=='native_work':
                packet['surface_work']['build_work']['current_draft']['markdown']='Changed captured draft'
            else:
                packet['rules_evidence']['ruleset']='foreign-rules'
            prepared['input']=json.dumps(packet,ensure_ascii=False,separators=(',',':'))
            return prepared
        monkeypatch.setattr(selected_owner,method,changed_request)
    if proposal and failure=='attempt_count':
        from generationengine import GenerationClient,TextCompleted
        from dataclasses import replace
        original_stream=GenerationClient.stream_text
        async def changed_stream(self,*args,**kwargs):
            async for event in original_stream(self,*args,**kwargs):
                if isinstance(event,TextCompleted):
                    event=replace(event,observation=event.observation.model_copy(update={'provider_attempt_count':2}))
                yield event
        if proposal=='image':
            original_generate=GenerationClient.generate_structured
            async def changed_generate(self,*args,**kwargs):
                result=await original_generate(self,*args,**kwargs)
                return result.model_copy(update={'observation':result.observation.model_copy(update={'provider_attempt_count':2})})
            monkeypatch.setattr(GenerationClient,'generate_structured',changed_generate)
        else:
            monkeypatch.setattr(GenerationClient,'stream_text',changed_stream)
    if proposal and failure=='stale_rules':
        original_complete=AgentConversationService.complete_native_base_turn
        def stale_complete(self,*args,**kwargs):
            return original_complete(self,*args,**{**kwargs,'expected_rules_revision':kwargs['expected_rules_revision']+1})
        monkeypatch.setattr(AgentConversationService,'complete_native_base_turn',stale_complete)
    rules_reads=[]
    if proposal and failure=='used_rules':
        from apps.live_control_server.services import rules_lookup_broker
        read_rules=rules_lookup_broker.prepare_plan_lookup
        def completed_rules(*args,**kwargs):
            result=read_rules(*args,**kwargs)
            rules_reads.append(result)
            return result
        monkeypatch.setattr(rules_lookup_broker,'prepare_plan_lookup',completed_rules)
    actual_harness = factory.BuildJevHarness
    if failure=='selection_text':
        from dataclasses import replace
        from apps.live_control_server.services.build_jev_writer_selection import WriterSelectionDriver
        original_stage=WriterSelectionDriver.stage
        def substituted_stage(self):
            plan=original_stage(self)
            state=plan.state()
            next(iter(state['sources'].values()))['text']='Substituted private-looking source body.'
            self._plan=replace(plan,state_json=json.dumps(state,sort_keys=True,separators=(',',':')))
            return self._plan
        monkeypatch.setattr(WriterSelectionDriver,'stage',substituted_stage)
    class Harness(actual_harness):
        def _capture_failure(self, adapter, exc):
            import traceback
            traceback.print_exception(exc)
            super()._capture_failure(adapter, exc)
        def __init__(self, **values):
            super().__init__(decision_transport=decisions, writer_transport=writer, **values)
        def execute(self, adapter):
            writer.adapter = adapter
            if failure=='section_scope':
                original_read=adapter.read_build_section
                adapter.read_build_section=lambda **args:original_read(line_start=args['line_start']+999,line_end=args['line_end']+999)
            return super().execute(adapter)
    monkeypatch.setattr(factory, 'BuildJevHarness', Harness)
    app = FastAPI()
    app.include_router(agent.router, prefix='/api/live')
    from apps.live_control_server.routes.conversation_library import router as conversations_router
    app.include_router(conversations_router)
    app.state.build_jev_runtime_factory = factory.PreparedBuildJevRuntime(accounting=counter())
    client = TestClient(app, client=('127.0.0.1', 42000), headers={'Authorization': 'Bearer ' + token})
    body = dict(schema='dmb_agent_turn_request_v1', client_thread_id=str(uuid4()), turn_id=str(uuid4()),
        surface=dict(surface_id='build', instance_id=page.document_id), owner_scope=dict(kind='world', world_id=world),
        primary_work=dict(kind='build', object_id=page.document_id, expected_revision=source.loaded_revision,
            expected_content_sha256=source.content_sha256), client_work_state='saved_clean',
        graph_request=dict(mode='world', world_id=world, campaign_id=None, revision_pin=None,
            focus=dict(kind='none', session_id=None, campaign_id=None)), graph_selection=None,
        build_authored_references=None if saved_statblock == 'by-name' or failure == 'deferred_graph_citation' else selected.model_dump(mode='json', by_alias=True), message=message or ('Describe the selected object and source-local episode.' if native_body else 'Describe the object I selected.'))
    if image_move:
        from application_state.build_proposal.image_move_decision import BuildImageMoveCapture
        from tests.application_state.test_agent_conversation_postgres import _new

        service = AgentConversationService()
        conversa = _new(service, world)
        pointer = service.get_world_pointer(world)
        capture = BuildImageMoveCapture(
            basis=dict(world_id=world, document_id=page.document_id, registry_revision=source.loaded_revision,
                       content_sha256=source.content_sha256, draft_sha256=source.content_sha256,
                       editor_sha256=sha256(image_editor.encode()).hexdigest(), visibility="internal",
                       draft_generation=0, selection_generation=0, caret=1),
            editor_json=image_editor, conversation_id=conversa.conversation_id, expected_pointer_revision=pointer.revision,
        )
        body["build_image_move_capture"] = capture.model_dump(mode="json")
        if image_move == "foreign_capture":
            body["build_image_move_capture"]["basis"]["world_id"] = "foreign-world"
        elif image_move == "forged_editor":
            edited = image_editor.replace("Harbour map", "Forged map")
            body["build_image_move_capture"]["editor_json"] = edited
            body["build_image_move_capture"]["basis"]["editor_sha256"] = sha256(edited.encode()).hexdigest()
        body["build_authored_references"] = None
    if draft is not None:
        body['build_draft_context']=draft.model_dump(mode='json',by_alias=True)
        body['client_work_state']='saved_dirty'
    if proposal or capture_write:
        from application_state.build_proposal.types import BuildWriteCapability
        offers = {}
        caret = 1
        if contextual == "caret":
            from application_state.agent_conversation.plan_slot_layout import prose_editor_node_size

            before_caret = json.loads(editor_json)["content"][:2]
            caret = sum(prose_editor_node_size(node) for node in before_caret) - 1
        if contextual in {"page_body", "page_end"}:
            from application_state.agent_conversation.plan_slot_layout import prose_editor_node_size

            end = sum(prose_editor_node_size(node) for node in json.loads(editor_json)["content"])
            offers = {"page_end_offer": {"end": end}, "page_body_offer": {"end": end}}
        cap=BuildWriteCapability(idempotency_key=uuid4(),conversation_id=draft.conversation_id,
            expected_pointer_revision=draft.expected_pointer_revision,draft_markdown=draft.snapshot.draft_markdown,
            boundary_editor_json=editor_json,
            basis=dict(**{k:getattr(draft.snapshot,k) for k in ('world_id','document_id','registry_revision',
                'content_sha256','visibility','draft_sha256','editor_sha256','draft_generation')},
                caret=caret,selection_generation=0), **offers)
        body['build_write_capability']=cap.model_dump(mode='json')
        if reference_image:
            body['build_write_capability']['reference_image_id'] = str((wrong if reference_image == 'wrong_same_page' else asset)['asset_id'])
            body['build_write_capability']['basis']['selection'] = {'end': 3, 'text': 'An'}
        if proposal:
            body['message']=message or ('Add a scene about this: Can I end my move in an occupied space?'
                if failure=='used_rules' else 'Prepare an illustration of a copper lamp beside the orchid.'
                if proposal=='image' else 'Add a proposed copper lamp to this page.')
    if connected_review:
        body['message']='Prepare a separate connected page from the saved proposal.'
    def current_creative():
        if proposal=='image':
            from uuid import uuid5
            from application_state.build_proposal.images import BuildImageService
            return BuildImageService().get(uuid5(cap.idempotency_key,'image'),writer.adapter.build_image_owner)
        from application_state.build_proposal.service import BuildProposalService
        return BuildProposalService().get(world,cap.idempotency_key)
    if failure=='retry_authoring_selection':
        from copy import deepcopy
        from apps.live_control_server.services.build_jev_driver import BuildJevDriver
        original_accept=BuildJevDriver.accept_decision
        def fail_selection(self,*args,**kwargs):
            raise ValueError('synthetic failure before authoring resolution')
        monkeypatch.setattr(BuildJevDriver,'accept_decision',fail_selection)
        refused=client.post('/api/live/agent/turn',json=body)
        assert refused.status_code==503 and not writer.calls,refused.text
        monkeypatch.setattr(BuildJevDriver,'accept_decision',original_accept)
        service=AgentConversationService();failed=service.inspect_turn(world_id=world,turn_id=writer.adapter.turn.turn_id)
        assert failed.status=='interrupted'
        assert not any(isinstance(e,t.BuildRequestedWorkResolutionV1) for e in failed.graph_context_execution.events)
        prefix=f'/api/live/agent/worlds/{world}/conversations/{failed.conversation_id}'
        eligibility=client.get(prefix+'/retry-context',params={'turn_ids':str(failed.turn_id)})
        assert eligibility.status_code==200 and eligibility.json()['turns'][0]['context']['eligible']
        retained=client.get(prefix+f'/turns/{failed.turn_id}/discussion-retry-input',params={'revision':failed.revision})
        assert retained.status_code==409 and retained.json()['detail']['code']=='build_authoring_retry_required',retained.text
        retry=deepcopy(body);retry['turn_id']=str(uuid4())
        retry['retry_of']={'turn_id':str(failed.turn_id),'revision':failed.revision}
        pointer=service.get_world_pointer(world)
        retry['build_draft_context']['expected_pointer_revision']=pointer.revision
        retry['build_write_capability'].update(idempotency_key=str(uuid4()),expected_pointer_revision=pointer.revision)
        if retry_mutation=='capability':retry['build_write_capability']=body['build_write_capability']
        elif retry_mutation=='question':retry['message']+=' Changed.'
        elif retry_mutation=='reference':retry['build_authored_references']=None
        elif retry_mutation=='revision':retry['retry_of']['revision']+=1
        before=len(decisions.calls),len(writer.calls)
        response=client.post('/api/live/agent/turn',json=retry)
        if retry_mutation:
            assert response.status_code==409,response.text
            assert (len(decisions.calls),len(writer.calls))==before
        else:
            assert response.status_code==200,response.text
            assert len(writer.calls)==1
            context=client.get(prefix+'/retry-context',params={'turn_ids':str(failed.turn_id)})
            assert context.json()['turns'][0]['context']['successor_id']==str(writer.adapter.turn.turn_id)
            replay=client.post('/api/live/agent/turn',json=retry)
            assert replay.status_code==200 and replay.json()['knowledge_context']['delivery_replay'] is True
            assert len(writer.calls)==1
        assert service.inspect_turn(world_id=world,turn_id=failed.turn_id)==failed
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return
    if failure in {'crash_live','crash_expired','crash_interrupted'}:
        from application_state.agent_conversation import types as ledger
        from uuid import uuid5
        import psycopg
        original_complete=AgentConversationService.complete_native_base_turn
        def crash_after_persistence(*args,**kwargs):
            raise SystemExit('synthetic crash after native object persistence')
        monkeypatch.setattr(AgentConversationService,'complete_native_base_turn',crash_after_persistence)
        with pytest.raises(SystemExit,match='synthetic crash'):
            client.post('/api/live/agent/turn',json=body)
        monkeypatch.setattr(AgentConversationService,'complete_native_base_turn',original_complete)
        prior=writer.adapter.service.inspect_turn(world_id=world,turn_id=writer.adapter.turn.turn_id)
        assert prior.status=='running'
        if failure=='crash_expired':
            import psycopg
            with psycopg.connect(recovery_dsn) as conn:
                conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 minute' WHERE turn_id=%s",(prior.turn_id,))
        elif failure=='crash_interrupted':
            writer.adapter.service.fail_turn(ledger.TurnFailure(world_id=world,conversation_id=prior.conversation_id,
                turn_id=prior.turn_id,expected_revision=prior.revision,failure_code='synthetic_persistence_interrupt'),interrupted=True)
        save_page(tmp_path,page.document_id,'A newer author page must survive recovery.')
        newer=get_workspace_document_snapshot(tmp_path,page.document_id)
        assert newer.content_sha256!=source.content_sha256
        from apps.live_control_server.services import plan_source_turn
        def forbid_fresh_source(*args,**kwargs):
            raise AssertionError('Prepared recovery must not reacquire current source authority')
        monkeypatch.setattr(plan_source_turn,'prepare',forbid_fresh_source)
        if recovery_mutation is not None:
            import psycopg
            from psycopg.types.json import Jsonb
            with psycopg.connect(recovery_dsn) as conn:
                if recovery_mutation=='raw':
                    key=uuid5(cap.idempotency_key,'image') if proposal=='image' else cap.idempotency_key
                    obj=conn.execute('SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s',(world,key)).fetchone()[0]
                    if proposal=='image':
                        obj['writer_proof']['raw_response']='{}'
                    else:
                        obj['raw_response']='{}'
                    conn.execute('UPDATE agent.build_proposal SET payload=%s WHERE world_id=%s AND action_id=%s',(Jsonb(obj),world,key))
                elif recovery_mutation in {'seal','scope','unknown'}:
                    row=conn.execute('SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s AND product_attempt=%s',(prior.turn_id,prior.attempt)).fetchone()[0]
                    sealed=next(e for e in row['events'] if e['kind']=='native_provider_outcome')
                    if recovery_mutation=='scope':
                        row['scope']['conversation_id']=str(uuid4())
                    elif recovery_mutation=='unknown':
                        sealed['status']='unknown'
                    else:
                        sealed['output_sha256']='0'*64
                    conn.execute('UPDATE agent.turn_rules_execution SET payload=%s WHERE turn_id=%s AND product_attempt=%s',(Jsonb(row),prior.turn_id,prior.attempt))
                elif recovery_mutation=='trace':
                    row=conn.execute('SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s',(prior.turn_id,prior.attempt)).fetchone()[0]
                    for observation in row['observations']:
                        if observation.get('kind')=='context_snapshot' and observation.get('stage')=='after':
                            observation['materials']=[m for m in observation['materials'] if not m.get('item_id','').startswith('unvalidated-provider-answer:')]
                    conn.execute('UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s AND attempt=%s',(Jsonb(row),prior.turn_id,prior.attempt))
                else:
                    raise AssertionError(recovery_mutation)
        calls_before_recovery=len(decisions.calls),len(writer.calls)
        response=client.post('/api/live/agent/turn',json=body)
        if recovery_mutation is not None:
            assert response.status_code==409,response.text
            assert response.json()['detail']['code']=='build_prepared_recovery_invalid'
            assert (len(decisions.calls),len(writer.calls))==calls_before_recovery
            assert get_workspace_document_snapshot(tmp_path,page.document_id)==newer
            return
        assert response.status_code==200,response.text
        assert response.json()['knowledge_context']['delivery_replay'] is True
        assert (len(decisions.calls),len(writer.calls))==calls_before_recovery
        after=writer.adapter.service.inspect_turn(world_id=world,turn_id=prior.turn_id)
        assert after.status=='completed' and after.attempt==prior.attempt
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==newer
        with psycopg.connect(recovery_dsn) as conn:
            state=conn.execute("SELECT payload->>'state' FROM agent.turn_rules_execution WHERE turn_id=%s AND product_attempt=%s",(prior.turn_id,prior.attempt)).fetchone()[0]
        assert state==('failed' if failure=='crash_interrupted' else 'unused')
        return
    if failure in {'retry_discussion','retry_unknown'}:
        original_complete=AgentConversationService.complete_native_base_turn
        def interrupted_delivery(*args,**kwargs):
            raise RuntimeError('synthetic delivery interruption after writer response')
        monkeypatch.setattr(AgentConversationService,'complete_native_base_turn',interrupted_delivery)
        refused=client.post('/api/live/agent/turn',json=body)
        assert refused.status_code==503,refused.text
        monkeypatch.setattr(AgentConversationService,'complete_native_base_turn',original_complete)
        failed=writer.adapter.service.inspect_turn(world_id=world,turn_id=writer.adapter.turn.turn_id)
        assert failed.status=='interrupted'
        prefix=f'/api/live/agent/worlds/{world}/conversations/{failed.conversation_id}'
        eligible=client.get(prefix+'/retry-context',params={'turn_ids':str(failed.turn_id)})
        assert eligible.status_code==200,eligible.text
        eligibility=eligible.json()['turns'][0]['context']
        if failure=='retry_unknown':
            assert eligibility['eligible'] is False and eligibility['reason']=='unknown_outcome',eligible.text
            blocked=client.get(prefix+f'/turns/{failed.turn_id}/discussion-retry-input',params={'revision':failed.revision})
            assert blocked.status_code==409,blocked.text
            assert len(writer.calls)==1
            return
        assert eligibility['eligible'] is True,eligible.text
        retained=client.get(prefix+f'/turns/{failed.turn_id}/discussion-retry-input',params={'revision':failed.revision})
        assert retained.status_code==200,retained.text
        assert retained.json()['snapshot']==draft.snapshot.model_dump(mode='json',by_alias=True)
        assert retained.json()['authored_references']==selected.model_dump(mode='json',by_alias=True)
        assert retained.json()['message']==body['message']
        retry={**body,'turn_id':str(uuid4()),'retry_of':{'turn_id':str(failed.turn_id),'revision':failed.revision,
            'retained_snapshot_sha256':draft.snapshot.snapshot_sha256}}
        retry.pop('build_write_capability',None)
        if capture_write:
            from application_state.agent_conversation.build_draft_context import native_build_action
            original_action=native_build_action(failed.graph_context_execution)
            assert original_action.write_capability is not None
            resolution,=[e for e in failed.graph_context_execution.events if type(e) is t.BuildRequestedWorkResolutionV1]
            assert resolution.requested_work=='review_connected_page' and resolution.operation=='answer_from_sources'
        expected_page=source
        if retry_mutation=='write_capability':
            retry['build_write_capability']=body['build_write_capability']
        elif retry_mutation=='newer_page':
            save_page(tmp_path,page.document_id,'A newer saved author page must survive explicit Retry.')
            expected_page=get_workspace_document_snapshot(tmp_path,page.document_id)
        elif retry_mutation=='question':
            retry['message']+=' Change the original question.'
        elif retry_mutation=='reference':
            retry['build_authored_references']=None
        elif retry_mutation=='revision':
            retry['retry_of']={**retry['retry_of'],'revision':failed.revision+1}
        count=len(writer.calls)
        all_calls=len(decisions.calls),len(writer.calls)
        if retry_mutation=='race':
            from concurrent.futures import ThreadPoolExecutor
            candidates=[retry,{**retry,'turn_id':str(uuid4())}]
            with ThreadPoolExecutor(max_workers=2) as pool:
                responses=list(pool.map(lambda candidate:client.post('/api/live/agent/turn',json=candidate),candidates))
            assert sorted(r.status_code for r in responses)==[200,409],[r.text for r in responses]
            winner=next(i for i,r in enumerate(responses) if r.status_code==200)
            retry,answer=candidates[winner],responses[winner]
            import psycopg
            with psycopg.connect(recovery_dsn) as conn:
                edges=conn.execute('SELECT ordinal FROM agent.turn_retry WHERE predecessor_id=%s',(failed.turn_id,)).fetchall()
            assert edges==[(1,)]
        else:
            answer=client.post('/api/live/agent/turn',json=retry)
        if retry_mutation in {'question','reference','revision','newer_page','write_capability'}:
            assert answer.status_code==409,answer.text
            assert (len(decisions.calls),len(writer.calls))==all_calls
            assert get_workspace_document_snapshot(tmp_path,page.document_id)==expected_page
            return
        assert answer.status_code==200,answer.text
        assert len(writer.calls)==count+1
        assert answer.json()['knowledge_context']['delivery_replay'] is False
        replay=client.post('/api/live/agent/turn',json=retry)
        assert replay.status_code==200 and replay.json()['knowledge_context']['delivery_replay'] is True,replay.text
        assert len(writer.calls)==count+1
        again=client.post('/api/live/agent/turn',json={**retry,'turn_id':str(uuid4())})
        assert again.status_code==409,again.text
        assert len(writer.calls)==count+1
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==expected_page
        after=client.get(prefix+'/retry-context',params={'turn_ids':str(failed.turn_id)})
        assert after.status_code==200 and after.json()['turns'][0]['context']['reason']=='retried',after.text
        if capture_write:
            successor_id=UUID(after.json()['turns'][0]['context']['successor_id'])
            successor=AgentConversationService().inspect_turn(world_id=world,turn_id=successor_id)
            action=native_build_action(successor.graph_context_execution)
            assert action.write_capability is None and action.intent.build_write_capability_sha256 is None
            assert successor.completion.collaboration.kind=='connected_page'
        original=writer.adapter.service.inspect_turn(world_id=world,turn_id=failed.turn_id)
        assert original==failed
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return
    if contextual == "stale":
        save_page(tmp_path, page.document_id, source.markdown + "\nA newer saved paragraph.\n")
    elif contextual == "foreign":
        body["build_write_capability"]["basis"]["world_id"] = "foreign-world"
    response = (dispatch(client, world, body) if dispatch else client.post('/api/live/agent/turn', json=body))
    if source_answer_output:
        turn = AgentConversationService().inspect_turn(world_id=world, turn_id=writer.adapter.turn.turn_id)
        assert lane.repo.get_head(world).head_revision_id == current_revision
        assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
        return SimpleNamespace(client=client, world=world, response=response, turn=turn,
            writer=writer, decisions=decisions, request=body)

    if image_move and failure != "discussion_source_tie":
        from application_state.build_proposal.image_move_review import BuildImageMoveReviewService
        from application_state.errors import ApplicationStateNotFoundError

        if image_move == "other_discussion":
            assert response.status_code == 200, response.text
            context = response.json()["knowledge_context"]
            assert context["completion"]["schema"] != "dmb_build_image_move_completion_v1"
            assert "The image would sit to the right" in str(context["completion"])
            assert len(writer.calls) == 1
            with pytest.raises(ApplicationStateNotFoundError):
                BuildImageMoveReviewService().get(world, writer.adapter.turn.turn_id)
            counts = len(decisions.calls), len(writer.calls)
            replay = client.post("/api/live/agent/turn", json=body)
            assert replay.status_code == 200 and replay.json()["knowledge_context"]["delivery_replay"] is True
            assert (len(decisions.calls), len(writer.calls)) == counts
            assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
            assert lane.repo.get_head(world).head_revision_id == current_revision
            return
        if image_move in {"foreign_capture", "forged_editor"}:
            assert response.status_code == (422 if image_move == "foreign_capture" else 409), response.text
            assert not decisions.calls and not writer.calls
            assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
            return
        assert response.status_code == 200, response.text
        completion = response.json()["knowledge_context"]["completion"]
        expected = {"tied_menu": "ready", "duplicate_context": "ready",
                    "other_discussion_tied_work": "discussion"}.get(image_move, image_move)
        assert completion["disposition"] == expected
        turn_id = writer.adapter.turn.turn_id
        if expected == "ready":
            review = BuildImageMoveReviewService().get(world, turn_id)
            assert completion["action_id"] == str(turn_id) and review.state == "editing"
            assert review.placement.image_block_id == "map-block"
            assert review.placement.destination_slot_id == "right-slot"
            feed = client.get(f"/api/live/agent/worlds/{world}/conversations/active/messages")
            assert feed.status_code == 200, feed.text
            row = next(row for row in feed.json()["messages"] if row["turn_id"] == str(turn_id))
            assert row["reply_object"] == {
                "kind": "build_image_move", "placement_sha256": completion["placement_sha256"],
                "source": {"world_id": world, "conversation_id": str(review.conversation_id),
                           "document_id": page.document_id, "turn_id": str(turn_id), "surface_id": "build"},
            }
            endpoint = f"/api/live/agent/worlds/{world}/build-image-moves/{turn_id}/review"
            fetched = client.get(endpoint)
            assert fetched.status_code == 200 and fetched.json() == {
                "review": review.model_dump(mode="json"), "issued": False,
            }
            modified = json.loads(image_editor)
            left, right = modified["content"][0]["content"]
            right["content"] = [left["content"].pop()]
            if not left["content"]:
                del left["content"]
            claim = {"operation": "claim", "expected_revision": review.revision, "claim_id": str(uuid4()),
                     "editor_json": image_editor, "after_editor_json": json.dumps(modified)}
            invalid = client.post(endpoint, json={**claim, "after_editor_json": image_editor})
            assert invalid.status_code == 409, invalid.text
            claimed = client.post(endpoint, json=claim)
            assert claimed.status_code == 200 and claimed.json()["issued"], claimed.text
            duplicate = client.post(endpoint, json=claim)
            assert duplicate.status_code == 200 and duplicate.json() == claimed.json() | {"issued": False}, duplicate.text
            premature = client.post(endpoint, json={"operation": "confirm", "claim_id": claim["claim_id"]})
            assert premature.status_code == 409, premature.text
        else:
            assert completion["action_id"] is None
            with pytest.raises(ApplicationStateNotFoundError):
                BuildImageMoveReviewService().get(world, turn_id)
        replay = client.post("/api/live/agent/turn", json=body)
        assert replay.status_code == 200, replay.text
        assert replay.json()["knowledge_context"]["completion"] == completion
        assert replay.json()["knowledge_context"]["delivery_replay"] and len(decisions.calls) == 1
        assert not writer.calls
        assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
        return
    if graph_reference:
        from application_state.build_proposal.graph_reference_review import BuildGraphReferenceReviewService
        from application_state.errors import ApplicationStateNotFoundError

        store = BuildGraphReferenceReviewService()
        if graph_reference == "remapped_inventory":
            assert response.status_code == 503, response.text
            assert len(decisions.calls) == 2 and not writer.calls
            with pytest.raises(ApplicationStateNotFoundError):
                store.get(world, writer.adapter.turn.turn_id)
            assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
            return
        assert response.status_code == 200, response.text
        completion = response.json()["knowledge_context"]["completion"]
        assert completion["disposition"] == graph_reference
        assert len(decisions.calls) == 2 and not writer.calls
        turn = writer.adapter.turn
        assert turn.status == "completed"
        if graph_reference == "ready":
            review = store.get(world, turn.turn_id)
            assert completion["action_id"] == str(review.action_id)
            assert review.state == "editing" and review.placement.reference == selected.references[0]
        else:
            assert completion["action_id"] is None
            with pytest.raises(ApplicationStateNotFoundError):
                store.get(world, turn.turn_id)
        messages = client.get(f"/api/live/agent/worlds/{world}/conversations/active/messages")
        assert messages.status_code == 200, messages.text
        saved = next(row for row in messages.json()["messages"] if row["turn_id"] == str(turn.turn_id))
        if graph_reference == "ready":
            assert saved["reply_object"] == {
                "kind": "build_graph_reference", "placement_sha256": completion["placement_sha256"],
                "source": {"world_id": world, "conversation_id": str(turn.conversation_id),
                           "document_id": page.document_id, "turn_id": str(turn.turn_id), "surface_id": "build"},
            }
        else:
            assert saved["reply_object"] is None
        assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
        replay = client.post('/api/live/agent/turn', json=body)
        assert replay.status_code == 200, replay.text
        assert replay.json()["knowledge_context"]["completion"] == completion
        assert replay.json()["knowledge_context"]["delivery_replay"] and len(decisions.calls) == 2
        return
    if contextual in {"stale", "foreign"}:
        from application_state.build_proposal.service import BuildProposalService

        assert response.status_code == (409 if contextual == "stale" else 422), response.text
        assert not decisions.calls and not writer.calls
        assert BuildProposalService().list(world, cap.conversation_id) == []
        committed = get_workspace_document_snapshot(tmp_path, page.document_id)
        assert committed.markdown == (source.markdown + "\nA newer saved paragraph.\n"
                                      if contextual == "stale" else source.markdown)
        return
    if failure in {"deferred_settlement_drift", "deferred_provider_failure"}:
        from application_state.agent_conversation.native_execution import NativeBuildQuerySettledV1
        assert response.status_code == 503, response.text
        assert len(decisions.calls) == 1 and not writer.calls
        turn = writer.adapter.service.inspect_turn(world_id=world, turn_id=writer.adapter.turn.turn_id)
        assert turn.status == "interrupted"
        assert not any(isinstance(e, NativeBuildQuerySettledV1)
                       for e in turn.graph_context_execution.events)
        assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
        return
    if failure=='initial_context':
        assert response.status_code in {502,503},response.text
        assert not decisions.calls and not writer.calls
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return SimpleNamespace(response=response,decisions=decisions,writer=writer)
    if connected_review:
        if connected_review not in {'valid','full_page'}:
            assert response.status_code==503,response.text
            assert len(writer.calls)==1
            assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
            assert lane.repo.get_head(world).head_revision_id==current_revision
            return
        assert response.status_code==200,response.text
        completion=response.json()['knowledge_context']['completion']
        assert completion['collaboration']['kind']=='connected_page'
        if connected_review=='full_page':
            assert len(completion['answer_segments'][0]['text']) > 5737
            assert completion['answer_segments'][0]['text']==json.loads(writer.actual_output)['answer_segments'][0]['text']
        else:
            assert completion['answer_segments']==[]
        current=writer.adapter.service.inspect_turn(world_id=world,turn_id=writer.adapter.turn.turn_id)
        assert current.status=='completed'
        from apps.live_control_server.services.agent_connected_page_origin import open_origin
        direct_origin=open_origin(writer.adapter.service,world,current.turn_id)
        origin_url=f'/api/live/agent/worlds/{world}/conversation/turns/{current.turn_id}/connected-page-origin'
        opened=client.get(origin_url)
        assert opened.status_code==200,opened.text
        assert opened.json()==direct_origin
        origin=opened.json()['origin']
        assert origin['document_id']==page.document_id and origin['content_sha256']==source.content_sha256
        assert 'A proposed conversation.' in origin['selected_text']
        assert opened.json()['read_id']==completion['collaboration']['read_id']
        save_page(tmp_path,page.document_id,'A newer page must not replace the reviewed origin.')
        newer=get_workspace_document_snapshot(tmp_path,page.document_id)
        again=client.get(origin_url)
        assert again.status_code==200 and again.json()==opened.json(),again.text
        before=len(decisions.calls),len(writer.calls)
        history=client.get(f'/api/live/agent/worlds/{world}/conversation',params={'include_turn_correlation':'true'})
        assert history.status_code==200,history.text
        assert history.json()['turns'][0]['knowledge_context']['completion']==completion
        replay=client.post('/api/live/agent/turn',json=body)
        assert replay.status_code==200 and replay.json()['knowledge_context']['delivery_replay'] is True,replay.text
        assert (len(decisions.calls),len(writer.calls))==before
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==newer
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return
    if failure in {'writer_incomplete_limit','writer_incomplete_filter','writer_incomplete_unknown'}:
        assert response.status_code==503,response.text
        limited=failure=='writer_incomplete_limit'
        expected='provider_output_limit_exceeded' if limited else 'plan_context_delivery_failure'
        assert response.json()['detail']['code']==('provider_output_limit_exceeded' if limited else 'build_jev_delivery_failure')
        service=AgentConversationService()
        turn=service.inspect_turn(world_id=world,turn_id=writer.adapter.turn.turn_id)
        assert turn.status=='interrupted' and turn.failure_code==expected and turn.completion is None
        trace=service.list_context_trace_attempts(world_id=world,turn_id=turn.turn_id)[-1]
        failures=[row for row in trace.observations if row.kind=='failure']
        snapshots=[row for row in trace.observations if row.kind=='context_snapshot' and row.snapshot_kind=='provider_response']
        drafts=[material.text for row in snapshots for material in row.materials
            if material.item_id.startswith('unvalidated-provider-answer:')]
        assert drafts==[writer.actual_output] and turn.assistant_text is None
        assert not any(row.code=='plan_writer_draft_rejected' for row in failures)
        from application_state.agent_conversation.native_execution import NATIVE_WRITER_TYPES
        writer_attempt=next(e.provider_attempt_id for e in turn.graph_context_execution.events if type(e) in NATIVE_WRITER_TYPES)
        assert not any(e.kind=='provider_outcome' and e.provider_attempt_id==writer_attempt and e.outcome=='response_received'
            for e in turn.graph_context_execution.events)
        assert failures[-1].stage=='writer_generation'
        assert failures[-1].phase=='provider'
        assert failures[-1].code==('provider_output_limit_exceeded' if limited else 'build_execution_exception')
        assert any(row.kind=='prompt_reference' and row.provider=='openai' for row in trace.observations)
        assert any(row.kind=='provider_call' and row.input_tokens==100 and row.output_tokens==40 for row in trace.observations)
        assert len(writer.calls)==1 and not classic_calls
        replay=client.post('/api/live/agent/turn',json=body)
        assert replay.status_code in {409,503} and len(writer.calls)==1
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return
    if failure in {'revision','node','reference_world'}:
        assert response.status_code == (422 if failure=='reference_world' else 409), response.text
        if failure!='reference_world':
            assert response.json()['detail']['code']=='native_graph_query_rejected'
        assert not decisions.calls and not writer.calls and not classic_calls
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return
    if failure == "discussion_source_tie":
        assert response.status_code == 409, response.text
        assert response.json()["detail"] == {
            "code": "build_discussion_source_uncertain",
            "message": "Should I answer from this Page alone, or look for other sources?",
        }
        assert len(decisions.calls) == 1 and not writer.calls and not classic_calls
        assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
        assert lane.repo.get_head(world).head_revision_id == current_revision
        return
    if failure in {'section_scope','selection_text'}:
        assert response.status_code==503,response.text
        assert not writer.calls and not classic_calls
        if failure=='selection_text':
            assert all('writer_selection' not in req.content.decode() for req in decisions.calls)
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return
    if proposal and failure is not None:
        from application_state.build_proposal.service import BuildProposalService
        if failure == 'target_unavailable':
            assert response.status_code == 409, response.text
            assert response.json()['detail'] == {
                'code': 'build_compose_target_unavailable',
                'message': 'Select the passage you want Buddy to revise, then continue the saved request.',
            }
            root = f'/api/live/agent/worlds/{world}/conversations'
            messages = client.get(root + '/active/messages')
            assert messages.status_code == 200, messages.text
            row = messages.json()['messages'][-1]
            assert row['status'] == 'interrupted'
            assert row['author_interaction'] == 'select_passage'
            retry = client.get(root + f"/{messages.json()['conversation_id']}/retry-context",
                               params={'turn_ids': row['turn_id']})
            assert retry.status_code == 200, retry.text
            assert retry.json()['turns'][0]['context']['author_interaction'] == 'select_passage'
            assert retry.json()['turns'][0]['context']['eligible'] is True
            if reference_image:
                assert retry.json()['turns'][0]['context']['reference_image_id'] == str(asset['asset_id'])
        else:
            assert response.status_code == 503, response.text
        assert len(writer.calls)==(0 if failure in {'native_work','rules_frame','used_rules'} else 1)
        assert not classic_calls
        if failure=='used_rules':
            from application_state.errors import ApplicationStateNotFoundError
            assert len(rules_reads)==1 and rules_reads[0].observation.status=='evidence'
            used=writer.adapter.rules_runtime.native.record.execution
            assert used.budget_use.calls==1 and used.supports
            with pytest.raises(ApplicationStateNotFoundError):
                current_creative()
            assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
            assert lane.repo.get_head(world).head_revision_id==current_revision
            return
        if proposal=='image' and failure!='stale_rules':
            from application_state.errors import ApplicationStateNotFoundError
            with pytest.raises(ApplicationStateNotFoundError):
                current_creative()
        else:
            record=current_creative()
            if failure!='stale_rules':
                assert record.state in {'failed','unknown'} and record.proposal is None
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        if failure == 'target_unavailable':
            from copy import deepcopy

            service = AgentConversationService()
            original = service.inspect_turn(world_id=world, turn_id=UUID(row['turn_id']))
            resumed = deepcopy(body)
            resumed['turn_id'] = str(uuid4())
            resumed['retry_of'] = {'turn_id': row['turn_id'], 'revision': original.revision}
            pointer = service.get_world_pointer(world).revision
            resumed['build_draft_context']['expected_pointer_revision'] = pointer
            capability = resumed['build_write_capability']
            capability.update(idempotency_key=str(uuid4()), expected_pointer_revision=pointer)
            before_calls = len(decisions.calls), len(writer.calls)
            capability['basis'].pop('selection', None)
            no_selection = client.post('/api/live/agent/turn', json=resumed)
            assert no_selection.status_code == (422 if reference_image else 409), no_selection.status_code
            if not reference_image:
                assert no_selection.json()['detail']['code'] == 'build_retry_unavailable'
            assert (len(decisions.calls), len(writer.calls)) == before_calls
            capability['basis']['selection'] = {'end': 18, 'text': 'An unsaved orchid'}
            for offer in ('page_body_offer', 'page_end_offer'):
                capability[offer] = {'end': 50}
                wider = client.post('/api/live/agent/turn', json=resumed)
                assert wider.status_code == (422 if reference_image else 409), wider.status_code
                if not reference_image:
                    assert wider.json()['detail']['code'] == 'build_retry_unavailable'
                assert (len(decisions.calls), len(writer.calls)) == before_calls
                del capability[offer]
            if reference_image:
                original_id = capability.pop('reference_image_id')
                text_only = client.post('/api/live/agent/turn', json=resumed)
                assert text_only.status_code == 409, text_only.text
                assert (len(decisions.calls), len(writer.calls)) == before_calls
                capability['reference_image_id'] = original_id
            result = client.post('/api/live/agent/turn', json=resumed)
            assert result.status_code == 200, result.text
            assert len(writer.calls) == 2
            proposal_record = BuildProposalService().get(world, UUID(capability['idempotency_key']))
            assert proposal_record.state == 'proposed'
            assert proposal_record.reservation.basis.selection.text == 'An unsaved orchid'
            assert not proposal_record.inserted_in_draft
            assert service.inspect_turn(world_id=world, turn_id=original.turn_id) == original
            assert get_workspace_document_snapshot(tmp_path,page.document_id) == source
            assert lane.repo.get_head(world).head_revision_id == current_revision
        return
    if reference_image in {'unbound', 'wrong_same_page'}:
        assert response.status_code == 503, response.text
        assert not writer.calls
        assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
        return
    if contextual in {"ambiguous", "missing", "different"}:
        from application_state.build_proposal.service import BuildProposalService

        assert response.status_code == 409, response.text
        detail = response.json()["detail"]
        assert detail["code"] == "build_contextual_placement_unresolved"
        assert {
            "ambiguous": "appears more than once",
            "missing": "in the requested section",
            "different": "names a different page",
        }[contextual] in detail["message"]
        assert len(decisions.calls) == 1 and not writer.calls
        assert BuildProposalService().list(world, cap.conversation_id) == []
        assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
        return
    assert response.status_code == 200, response.text + str(classic_calls)
    assert not classic_calls and len(writer.calls) == 1
    payload = response.json()
    context = payload['knowledge_context']
    assert context['schema'] == 'dmb_agent_surface_native_context_response_v1'
    assert context['receipt']['work_context']['surface_id'] == 'build'
    if authored_source=='source_only':
        assert context['receipt']['native_query']['reason']=='native_graph_binding_unavailable'
    else:
        assert context['receipt']['native_query']['authority']['revision_id'] == current_revision
    if authored_source!='source_only' and saved_statblock != 'by-name' and failure != 'deferred_graph_citation':
        assert context['receipt']['native_query']['authored_targets'][0]['selection_revision_id'] == original_revision
    service = AgentConversationService()
    turn = service.inspect_turn(world_id=world, turn_id=writer.adapter.turn.turn_id)
    assert turn.status == 'completed' and type(turn.graph_context_receipt) is t.SurfaceNativeContextReceiptV1
    if authored_source:
        from application_state.agent_conversation.native_corpus import NativeAuthoredSourceReadV1
        reads=[e for e in turn.graph_context_execution.events if isinstance(e,NativeAuthoredSourceReadV1)]
        assert len(reads)==1 and reads[0].catalog.source.revision.source_revision_id==source_ref.source_revision_id
        assert not hasattr(reads[0],'provider_attempt_id')
        from application_state.agent_conversation.native_corpus import selected_body_reads, body_selection_unit_id
        from application_state.agent_conversation.writer_evidence_selection import acquired_catalog
        assert reads[0] in selected_body_reads(turn.graph_context_execution)
        assert body_selection_unit_id(reads[0]) not in acquired_catalog(
            turn.graph_context_execution, {'capture_status':'recording'})
        vote=next(e for e in turn.graph_context_execution.events if isinstance(e,t.BuildWriterEvidenceSelectionV2))
        forged=vote.model_copy(update={'judgments':dict(vote.judgments)|{body_selection_unit_id(reads[0]):'irrelevant'}})
        altered=turn.graph_context_execution.model_copy(update={'events':[forged if e.event_id==vote.event_id else e
            for e in turn.graph_context_execution.events]})
        with pytest.raises(ValueError,match='complete acquired extent closure'):
            selected_body_reads(altered)
        from application_state.agent_conversation.native_execution import NATIVE_WRITER_TYPES
        writer_event=next(e for e in turn.graph_context_execution.events if type(e) in NATIVE_WRITER_TYPES)
        assert reads[0].event_id in writer_event.native_read_event_ids
        assert 'source-local episode' in reads[0].excerpt.text
        assert ('A proposed note.' in reads[0].excerpt.text)==(authored_source=='full_document')
        citations=[c for c in turn.completion.native_body_citations if c.read_event_id==reads[0].event_id]
        assert len(citations)==1
        citation_index=turn.completion.native_body_citations.index(citations[0])
        opened=client.get(f'/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/native-body-excerpts/{citation_index}')
        assert opened.status_code==200,opened.text
        assert opened.json()['content']==reads[0].excerpt.text
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        before=len(decisions.calls),len(writer.calls)
        replay=client.post('/api/live/agent/turn',json=body)
        assert replay.status_code==200 and replay.json()['knowledge_context']['delivery_replay'] is True
        assert (len(decisions.calls),len(writer.calls))==before
        return SimpleNamespace(client=client,world=world,page=page,source=source,request=body,draft=draft,
            selected=selected,writer=writer,decisions=decisions,turn=turn,service=service,revision=current_revision)
    if with_draft:
        captured = next(e for e in turn.graph_context_execution.events if isinstance(e,t.BuildDraftContextCapturedV1))
        assert captured.record.snapshot==draft.snapshot
        assert captured.sequence < next(e.sequence for e in turn.graph_context_execution.events if isinstance(e,t.ProviderAttemptAuthorizedEventV1))
        if contextual:
            assert "unsaved orchid" in decisions.calls[0].content.decode()
            assert all("unsaved orchid" not in req.content.decode() for req in decisions.calls[1:])
            assert all("boundary_editor_json" not in req.content.decode() for req in decisions.calls)
        else:
            assert all('unsaved orchid' not in req.content.decode() for req in decisions.calls)
    assert not any(isinstance(e,(t.BuildDraftProviderInclusionV1,t.BuildSectionProviderInclusionV1))
        for e in turn.graph_context_execution.events)
    captures = [event for event in turn.graph_context_execution.events if isinstance(event, t.BuildAuthoredReferencesCapturedV1)]
    if saved_statblock == "by-name" or failure == "deferred_graph_citation":
        assert not captures
    else:
        assert len(captures) == 1 and captures[0].references == selected
    if proposal:
        from application_state.agent_conversation.retry import retained_discussion_capture, RetryUnavailableError
        with pytest.raises(RetryUnavailableError,match='authoring target'):
            retained_discussion_capture(turn)
        from application_state.build_proposal.service import BuildProposalService
        if proposal=='image':
            from uuid import uuid5
            from application_state.build_proposal.images import BuildImageService
            record=BuildImageService().get(uuid5(cap.idempotency_key,'image'),writer.adapter.build_image_owner)
            assert record.state=='prepared' and record.prompt=='A proposed copper lamp beside an orchid.'
            assert record.purpose=='illustration' and record.asset_id is None
            authorization=record.writer_proof.authorization
            assert context['completion']['schema']=='dmb_build_image_preparation_completion_v1'
        else:
            record=BuildProposalService().get(world,cap.idempotency_key)
            assert record.state=='proposed' and record.proposal.replacement_markdown==(proposal_markdown or 'A proposed copper lamp.')
            if contextual in {"unique", "mixed"}:
                assert record.reservation.prose_target.alias == "passage2:insert_after"
                assert record.reservation.basis.caret == 1
                assert record.reservation.prose_target.operation == "insert_after"
                packet = json.loads(json.loads(writer.calls[-1].content)["input"])
                assert packet["paragraph_placement"]["section"] == ["East"]
            if contextual == "caret":
                assert record.reservation.prose_target.alias == "passage1:insert_after"
                assert record.reservation.prose_target.from_ == caret + 1
                assert record.reservation.basis.caret == caret
                packet = json.loads(json.loads(writer.calls[-1].content)["input"])
                assert packet["paragraph_placement"]["section"] == ["West"]
            if contextual in {"page_end", "page_body"}:
                assert record.proposal.target == contextual
                assert record.reservation.basis.caret == 1
                packet = json.loads(json.loads(writer.calls[-1].content)["input"])
                assert not {"page_body_offer", "page_end_offer"} & packet.keys()
            authorization=record.authorization
            assert context['completion']['schema']=='dmb_build_authoring_completion_v1'
        assert context['completion']['action_id']==str(record.action_id)
        assert authorization.provider_attempt_id==turn.completion.provider_attempt_id
        for correlated in (False,True):
            history=client.get(f'/api/live/agent/worlds/{world}/conversation',params={'include_turn_correlation':str(correlated).lower()})
            assert history.status_code==200,history.text
            assert history.json()['turns'][0]['knowledge_context']['completion']==context['completion']
        import os
        if proposal=='image' and (destination:=os.environ.get('DMB_NATIVE_BUILD_IMAGE_CONTEXT')):
            from pathlib import Path
            path=Path(destination)
            captured=json.loads(path.read_text())
            captured['image_context']=context
            path.write_text(json.dumps(captured,indent=2)+'\n')
        if proposal!='image' and (destination:=os.environ.get('DMB_NATIVE_BUILD_PROPOSAL_WIRE')):
            from pathlib import Path
            path=Path(destination)
            captured=json.loads(path.read_text())
            captured['proposal_wire']=dict(request=body,response=payload,history=history.json(),
                record=record.model_dump(mode='json',exclude={'raw_response'}))
            path.write_text(json.dumps(captured,indent=2)+'\n')
        before=len(decisions.calls),len(writer.calls)
        replay=client.post('/api/live/agent/turn',json=body)
        assert replay.status_code==200,replay.text
        assert replay.json()['knowledge_context']['delivery_replay'] is True
        assert replay.json()['knowledge_context']['completion']==context['completion']
        assert (len(decisions.calls),len(writer.calls))==before
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        if proposal_markdown is not None:
            assert record.reservation.basis.caret == 1
            edited = proposal_markdown + "\n\n" + draft.snapshot.draft_markdown
            save_page(tmp_path, page.document_id, edited)
            reopened = get_workspace_document_snapshot(tmp_path, page.document_id)
            assert reopened.markdown == edited
            assert reopened.markdown.count(proposal_markdown) == 1
            assert lane.repo.get_head(world).head_revision_id == current_revision
        return
    if saved_statblock in {"associated", "by-name"}:
        expected_status = (
            'discussion'
            if json.loads(writer.calls[-1].content)["text"]["format"]["name"]
            == "surface_native_evidence_selectors_v7"
            else 'source_grounded'
        )
        assert context['completion']['answer_context_status'] == expected_status
        assert context['completion']['native_assertion_citations'] == []
        return SimpleNamespace(client=client, world=world, turn=turn, decisions=decisions)
    if (requested_work(message) if callable(requested_work) else requested_work) in {
            "review_lore_page", "review_lore_page_from_conversation", "review_blank_lore_page"}:
        assert context["completion"]["collaboration"]["kind"] == "lore_page"
        assert not context["completion"]["native_assertion_citations"]
        history = client.get(
            f"/api/live/agent/worlds/{world}/conversation",
            params={"include_turn_correlation": "true"},
        )
        assert history.status_code == 200, history.text
        retained = history.json()["turns"][0]["knowledge_context"]["completion"]
        assert retained == context["completion"]
        calls_before_replay = len(decisions.calls), len(writer.calls)
        replay = client.post("/api/live/agent/turn", json=body)
        assert replay.status_code == 200, replay.text
        replay_context = replay.json()["knowledge_context"]
        assert replay_context["delivery_replay"] is True
        assert replay_context["completion"] == retained
        assert (len(decisions.calls), len(writer.calls)) == calls_before_replay
        assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
        assert lane.repo.get_head(world).head_revision_id == current_revision
        return SimpleNamespace(client=client, world=world, turn=turn, decisions=decisions)
    citations = context['completion']['native_assertion_citations']
    assert citations and all(c['read_revision_id'] == current_revision for c in citations)
    opened = client.get(f'/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/native-assertion-sources/0')
    assert opened.status_code == 200, opened.text
    assert opened.json()['content'] and opened.json()['citation'] == citations[0]
    for correlated in (False, True):
        history = client.get(f'/api/live/agent/worlds/{world}/conversation',
            params={'include_turn_correlation': str(correlated).lower()})
        assert history.status_code == 200, history.text
        row = history.json()['turns'][0]
        assert 'plan_context' not in row
        assert ('idempotency_key' in row) is correlated
        assert row['knowledge_context']['receipt'] == context['receipt']
        assert row['knowledge_context']['completion'] == context['completion']
    import os
    if not with_draft and (destination := os.environ.get('DMB_NATIVE_BUILD_WIRE')):
        from pathlib import Path
        captured=dict(request=body,response=payload,history=history.json(),source=opened.json())
        if saved:
            cite=context['completion']['saved_source_citations'][0]
            saved_read=client.get(f'/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/saved-sections/{cite["segment_index"]}/{cite["section_event_ids"][0]}')
            assert saved_read.status_code==200,saved_read.text
            captured['saved_source']=saved_read.json()
        Path(destination).write_text(json.dumps(captured,indent=2)+'\n')
    before = (len(decisions.calls), len(writer.calls))
    replay = client.post('/api/live/agent/turn', json=body)
    assert replay.status_code == 200, replay.text
    assert replay.json()['knowledge_context']['delivery_replay'] is True
    if saved:
        from apps.live_control_server.services.agent_saved_sections import saved_section_targets
        targets=saved_section_targets(turn)
        assert targets
        cite=context['completion']['saved_source_citations'][0]
        assert cite['segment_index']==1
        assert any(isinstance(e,t.BuildWriterEvidenceSelectionV1) and e.mode=='jev' for e in turn.graph_context_execution.events)
        for identity in cite['section_event_ids']:
            url=f'/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/saved-sections/{cite["segment_index"]}/{identity}'
            original=client.get(url)
            assert original.status_code==200,original.text
            assert original.json()['target']['source_basis']==context['receipt']['work_context']['source_basis']
        save_page(tmp_path,page.document_id,'# Changed after the accepted reply\n\nNewer text must never replace a citation.\n')
        reopened=client.get(url)
        assert reopened.status_code==200 and reopened.json()==original.json()
        source=get_workspace_document_snapshot(tmp_path,page.document_id)
    assert (len(decisions.calls), len(writer.calls)) == before
    assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
    assert lane.repo.get_head(world).head_revision_id == current_revision

    return SimpleNamespace(client=client,world=world,page=page,source=source,request=body,
        draft=draft,selected=selected,writer=writer,decisions=decisions,turn=turn,service=service,
        revision=current_revision)


@pytest.mark.parametrize('long_exchange', [False, True])
def test_native_build_retrieval_receives_frozen_followup_dialogue(lane, tmp_path, monkeypatch, long_exchange):
    case = _fresh_case(lane, tmp_path, monkeypatch, None, False, False, False)
    initial = [json.loads(req.content)['state'] for req in case.decisions.calls
        if 'candidates' in json.loads(req.content).get('state', {})]
    assert initial and all('dialogue_reference' not in state for state in initial)
    expected = [dict(role='user', content=case.request['message']),
        dict(role='assistant', content=case.turn.assistant_text)]
    messages = ['The proposed place is the copper observatory. 🌌']
    if long_exchange:
        messages[0] += ' Author-supplied possibility, not a played fact. ' * 320
        assert len(messages[0]) > 12000
    messages.append('Retrieve context for that place; do not treat my proposed details as played facts.')
    for message in messages:
        start = len(case.decisions.calls)
        request = case.request | dict(turn_id=str(uuid4()), message=message)
        response = case.client.post('/api/live/agent/turn', json=request)
        assert response.status_code == 200, response.text
        states = [json.loads(req.content)['state'] for req in case.decisions.calls[start:]
            if 'candidates' in json.loads(req.content).get('state', {})]
        assert states and all(state.get('dialogue_reference') == expected for state in states)
        frozen = case.writer.adapter.build_frozen_history
        assert [dict(role=role, content=pair[key]) for pair in frozen
            for role, key in (('user', 'user'), ('assistant', 'assistant'))] == expected
        assert all('not source evidence' in state['questions']['operation']['instructions']
            or 'never evidence' in state['questions']['operation']['instructions']
            for state in [json.loads(req.content) for req in case.decisions.calls[start:]
                if 'candidates' in json.loads(req.content).get('state', {})])
        counts = len(case.decisions.calls), len(case.writer.calls)
        replay = case.client.post('/api/live/agent/turn', json=request)
        assert replay.status_code == 200 and replay.json()['knowledge_context']['delivery_replay'] is True
        assert (len(case.decisions.calls), len(case.writer.calls)) == counts
        assert get_workspace_document_snapshot(tmp_path, case.page.document_id) == case.source
        assert lane.repo.get_head(case.world).head_revision_id == case.revision
        expected += [dict(role='user', content=message),
            dict(role='assistant', content=response.json()['answer']['text'])]


@pytest.mark.parametrize('kind,related,mutation,output_review',[
    ('discuss',False,None,None),('discuss',False,None,'questions'),('discuss',False,None,'mixed_questions'),('discuss',False,None,'plan'),
    ('prepare_insertion',False,None,None),('prepare_insertion',True,None,None),
    ('discuss',False,'message',None),('prepare_insertion',False,'command',None)]
    +[(kind,False,mutation,None) for kind in ('discuss','prepare_insertion')
        for mutation in ('writer_allowance','writer_input')])
def test_native_reviewed_step_preserves_the_author_choice(lane,tmp_path,monkeypatch,application_state_dsn,kind,related,mutation,output_review,authored_source=None):
    from application_state.agent_conversation import work_plan as w
    from application_state.build_proposal.types import BuildWriteCapability
    case=_fresh_case(lane,tmp_path,monkeypatch,'mixed_questions' if output_review=='mixed_questions' else None,True,False,False,authored_source=authored_source)
    if related:
        page=create_page_fixture(tmp_path,world_id=case.world,campaign_id=case.world,title='Related authored note',
            kind='worldbuilding_source',source_domain='worldbuilding',document_class='lore',
            authority_state='draft',visibility_state='internal')
        save_page(tmp_path,page.document_id,'A separate proposed lamp note.')
    step=w.StepV2(step_id=uuid4(),text=('Can I end my move in an occupied space?' if output_review=='mixed_questions' else 'Discuss where the lamp belongs.') if kind=='discuss' else 'Prepare a proposed lamp detail.',
        selected=True,kind=kind,references=())
    deferred=w.StepV2(step_id=uuid4(),text='Write a useful paragraph only after placement is chosen.',selected=False,kind='prepare_insertion',references=())
    review=w.ReviewV3(expected_revision=0,objective='Choose placement, then prepare writing for review.',
        steps=[step,deferred],root_references=case.selected.references)
    plan=w.save(case.world,case.turn.conversation_id,case.turn.turn_id,review)
    continued=w.continue_step(case.world,case.turn.conversation_id,case.turn.turn_id,
        w.Continue(expected_revision=plan['revision'],step_id=step.step_id,command_id=uuid4()))
    dispatch=continued['dispatch']
    cap=BuildWriteCapability(idempotency_key=uuid4(),conversation_id=case.draft.conversation_id,
        expected_pointer_revision=case.draft.expected_pointer_revision,draft_markdown=case.draft.snapshot.draft_markdown,
        basis=dict(**{k:getattr(case.draft.snapshot,k) for k in ('world_id','document_id','registry_revision',
            'content_sha256','visibility','draft_sha256','editor_sha256','draft_generation')},caret=1,selection_generation=0))
    body={**case.request,'client_thread_id':dispatch['client_thread_id'],'turn_id':dispatch['client_turn_id'],
        'message':dispatch['message'],'reviewed_step':continued['reviewed_step'],
        'build_write_capability':cap.model_dump(mode='json'),
        'build_authored_references':dispatch['authored_references']}
    if mutation=='message':
        body['message']+=' Change this approved instruction.'
    if mutation=='command':
        body['reviewed_step']={**body['reviewed_step'],'command_id':str(uuid4())}
    before=len(case.decisions.calls),len(case.writer.calls)
    case.decisions.deny_routing=True
    case.writer.mode=kind=='prepare_insertion'
    if output_review is not None:
        case.writer.review=({'kind':'questions','questions':[{'text':'Where should the lamp stand?'}]} if output_review in {'questions','mixed_questions'}
            else {'kind':'plan','objective':'Unapproved work','steps':[{'text':'Write the deferred paragraph.','kind':'prepare_insertion','selected':True}]})
    accounting_refusals=[]
    if mutation in {'writer_allowance','writer_input'}:
        from tests.application_state.test_surface_native_writers import snapshot
        from application_state.errors import ApplicationStateValidationError
        from apps.live_control_server.services.agent_turn_service import _json_node_count
        original=AgentConversationService.authorize_native_writer
        def changed_physical_request(owner,world_id,conversation_id,turn_id,**values):
            turn=owner.inspect_turn(world_id=world_id,turn_id=turn_id)
            assert turn.graph_context_receipt.assembled_input.assembler_version=='reviewed_author_admission_v1'
            auth=values['authorization']
            if mutation=='writer_allowance':
                request=json.loads(values['prepared_request_json'])
                request['max_output_tokens']=auth.output_token_reserve+1
                raw=json.dumps(request,ensure_ascii=False)
                values={**values,'prepared_request_json':raw,'authorization':auth.model_copy(update={
                    'envelope_sha256':sha256(raw.encode()).hexdigest(),
                    'input_tokens':len(raw.encode())+64*(1+_json_node_count(request))})}
            else:
                values={**values,'authorization':auth.model_copy(update={'input_tokens':0})}
            persisted=SimpleNamespace(dsn=application_state_dsn,turn=turn)
            prior=snapshot(persisted)
            try:
                original(owner,world_id,conversation_id,turn_id,**values)
            except ApplicationStateValidationError:
                assert snapshot(persisted)==prior
                accounting_refusals.append(mutation)
                raise
            raise AssertionError('APP admitted forged physical writer accounting')
        monkeypatch.setattr(AgentConversationService,'authorize_native_writer',changed_physical_request)
    response=case.client.post('/api/live/agent/turn',json=body)
    if mutation in {'writer_allowance','writer_input'}:
        assert response.status_code==503,response.text
        assert accounting_refusals==[mutation]
        assert len(case.writer.calls)==before[1]
        assert get_workspace_document_snapshot(tmp_path,case.page.document_id)==case.source
        return
    if mutation:
        assert response.status_code in {404,409},response.text
        assert (len(case.decisions.calls),len(case.writer.calls))==before
        return
    if output_review=='plan':
        assert response.status_code==503,response.text
        assert len(case.writer.calls)==before[1]+1
        return
    assert response.status_code==200,response.text
    context=(response.json()['rules_context']['base_context'] if output_review=='mixed_questions' else response.json()['knowledge_context'])
    if kind=='discuss':
        assert context['completion']['collaboration']==case.writer.review
    assert context['receipt']['assembled_input']['assembler_version']=='reviewed_author_admission_v1'
    actual=case.service.inspect_turn(world_id=case.world,turn_id=case.writer.adapter.turn.turn_id)
    mixed = output_review == 'mixed_questions'
    if mixed:
        assert actual.base_projection.kind == 'approved'
    base = actual.base_projection.turn if mixed else actual
    assert base.status == 'completed'
    selections=[e for e in base.graph_context_execution.events if isinstance(e,t.BuildReviewedActionSelectionV1)]
    assert len(selections)==1 and selections[0].operation==('answer_from_sources' if kind=='discuss' else 'propose_build_insertion')
    assert not any(isinstance(e,t.BuildRequestedWorkResolutionV1) for e in base.graph_context_execution.events)
    expected='dmb_surface_native_completion_v1' if kind=='discuss' else 'dmb_build_authoring_completion_v1'
    assert context['completion']['schema']==expected
    assert len(case.writer.calls)==before[1]+1
    after=len(case.decisions.calls),len(case.writer.calls)
    replay=case.client.post('/api/live/agent/turn',json=body)
    assert replay.status_code==200 and (replay.json()['rules_context']['base_context'] if mixed else replay.json()['knowledge_context'])['delivery_replay'] is True,replay.text
    assert (len(case.decisions.calls),len(case.writer.calls))==after
    assert get_workspace_document_snapshot(tmp_path,case.page.document_id)==case.source

    if output_review in {"questions", "mixed_questions"}:
        from application_state.agent_conversation import library

        page = library.read_turns(base.world_id, base.conversation_id)
        assert page["schema"] == "dmb_conversation_library_turns_v3"
        row = next(row for row in page["turns"] if row["turn_id"] == str(base.turn_id))
        assert row["assistant_text"] == actual.assistant_text
        assert row["reply_object"] == {
            **case.writer.review,
            "source": {
                "world_id": base.world_id,
                "conversation_id": str(base.conversation_id),
                "turn_id": str(base.turn_id),
                "document_id": case.page.document_id,
                "surface_id": "build",
            },
        }
        pointer = case.service.get_world_pointer(base.world_id)
        case.service.new_conversation(t.ConversationCommand(
            world_id=base.world_id,
            command_id=uuid4(),
            expected_pointer_revision=pointer.revision,
            expected_active_conversation_id=base.conversation_id,
        ))
        archived_pointer = case.service.get_world_pointer(base.world_id)
        assert library.read_turns(base.world_id, base.conversation_id) == page
        assert case.service.get_world_pointer(base.world_id) == archived_pointer
        assert case.service.inspect_turn(world_id=base.world_id, turn_id=base.turn_id) == actual
        assert library._reply_object(actual, "foreign-world", base.conversation_id) is None
        assert library._reply_object(actual, base.world_id, uuid4()) is None


@pytest.mark.parametrize('proposal',[True,'image'])
@pytest.mark.parametrize('state',['live','expired','interrupted'])
def test_native_persisted_object_recovers_without_another_provider(lane,tmp_path,monkeypatch,application_state_dsn,proposal,state):
    _fresh_case(lane,tmp_path,monkeypatch,'crash_'+state,True,False,proposal,recovery_dsn=application_state_dsn)


@pytest.mark.parametrize('proposal',[True,'image'])
@pytest.mark.parametrize('mutation',['raw','seal','trace','scope','unknown'])
def test_native_persisted_object_recovery_refuses_corrupted_owners(lane,tmp_path,monkeypatch,application_state_dsn,proposal,mutation):
    _fresh_case(lane,tmp_path,monkeypatch,'crash_live',True,False,proposal,recovery_dsn=application_state_dsn,recovery_mutation=mutation)


@pytest.mark.parametrize('mutation',[None,'race','newer_page','question','reference','revision','unknown'])
def test_native_failed_discussion_exposes_original_context_and_one_explicit_retry(lane,tmp_path,monkeypatch,application_state_dsn,mutation):
    _fresh_case(lane,tmp_path,monkeypatch,'retry_unknown' if mutation=='unknown' else 'retry_discussion',True,False,False,
        recovery_dsn=application_state_dsn,retry_mutation=mutation)


@pytest.mark.parametrize('review',['valid','full_page','foreign_read','foreign_quote'])
def test_native_connected_page_review_uses_its_included_saved_origin(lane,tmp_path,monkeypatch,review):
    _fresh_case(lane,tmp_path,monkeypatch,None,True,True,False,connected_review=review)


def test_create_page_after_connected_review_stays_on_the_existing_build_route(lane, tmp_path, monkeypatch):
    from apps.live_control_server.services import plan_source_turn
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError

    checked = []
    def dispatch(client, world, body):
        reply = client.post("/api/live/agent/turn", json=body)
        assert reply.json()["knowledge_context"]["completion"]["collaboration"]["kind"] == "connected_page"

        def stop_before_provider(*args, **kwargs):
            checked.append(True)
            raise AgentTurnServiceError("Existing Build route reached", code="existing_build_route", status_code=418)

        with monkeypatch.context() as patch:
            patch.setattr(plan_source_turn, "prepare", stop_before_provider)
            followup = client.post("/api/live/agent/turn", json={
                **body, "turn_id": str(uuid4()), "message": "Create the page",
            })
        assert followup.status_code == 418, followup.text
        return reply

    _fresh_case(lane, tmp_path, monkeypatch, None, True, True, False,
                connected_review="valid", dispatch=dispatch)
    assert checked == [True]


@pytest.mark.parametrize('judgment',['direct_support','qualification_or_conflict','uncertain','irrelevant'])
def test_ordinary_build_selects_native_body_and_reopens_only_included_support(lane,tmp_path,monkeypatch,judgment):
    from application_state.agent_conversation import native_corpus as corpus, writer_evidence_selection as selection
    case=_fresh_case(lane,tmp_path,monkeypatch,None,False,False,False,native_body=judgment)
    events=case.turn.graph_context_execution.events
    vote,=[e for e in events if type(e) is t.BuildWriterEvidenceSelectionV2]
    acquired=corpus.acquired_body_reads(case.turn.graph_context_execution)
    assert acquired and not vote.source_event_ids
    assert {k:v for k,v in vote.judgments.items() if k.startswith('body:')}=={
        corpus.body_selection_unit_id(r):judgment for r in acquired}
    calls=[json.loads(r.content) for r in case.decisions.calls
           if json.loads(r.content)['questions'] and all(k.startswith('s') and k[1:].isdigit() for k in json.loads(r.content)['questions'])]
    assert len(calls)==1
    catalog = selection.acquired_catalog(case.turn.graph_context_execution,{'capture_status':'complete'})
    for read in acquired:
        slot='s'+str(list(catalog).index(corpus.body_selection_unit_id(read)))
        unit=calls[0]['state']['sources'][slot]
        assert unit['text']==read.excerpt.text
    citations=case.turn.completion.native_body_citations
    assert bool(citations)==(judgment!='irrelevant')
    for index,citation in enumerate(citations):
        opened=case.client.get(f'/api/live/agent/worlds/{case.world}/conversation/turns/{case.turn.turn_id}/native-body-excerpts/{index}')
        assert opened.status_code==200,opened.text
        assert opened.json()['content']


def test_ordinary_native_body_selector_rejects_substituted_input_before_dispatch(lane,tmp_path,monkeypatch):
    _fresh_case(lane,tmp_path,monkeypatch,'selection_text',False,False,False,native_body='direct_support')


@pytest.mark.parametrize('copies', [3200, 6200])
def test_native_writer_selector_uses_its_verified_long_context_at_app_boundary(lane,tmp_path,monkeypatch,copies):
    from dungeonmind.application.vnext import publish_native_text_source_evidence
    from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
    from graph_memory.vnext.domain_runtime import dungeonbuddy_world_domain_contract,dungeonbuddy_dnd5e_custom_predicate_profile
    from tests.test_source_statements import NOW
    from application_state.agent_conversation.build_decision_context import LONG_LIMIT
    # A real acquired body exceeds the initial64k envelope; the larger case also
    # exceeds the retired256KB request limit while fitting frozen token admission.
    text='# Retained source\n\n'+'An unrelated source-local episode was recorded.\n'*copies
    raw=text.encode()
    publish_native_text_source_evidence(repository=lane.repo,
        domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
        request=NativeTextSourceAdmissionV1(space_id=lane.world.world_id,admission_id='large-selector-source',
            expected_parent_revision_id=lane.repo.get_head(lane.world.world_id).head_revision_id,
            created_at=NOW,body_text=text,expected_body_sha256=sha256(raw).hexdigest(),
            source_classification='dungeonbuddy.source:session_recap',authority='primary',
            visibility={'kind':'labels_any','labels':['dungeonbuddy.visibility:gm']},
            spans=[dict(client_ref='context',evidence_role='context',start_byte=0,end_byte=len(raw),
                        expected_slice_sha256=sha256(raw).hexdigest())]))
    from application_state.agent_conversation import writer_evidence_selection as selection
    from application_state.errors import ApplicationStateValidationError
    append=AgentConversationService.record_build_writer_evidence_selection
    checked=[]

    def check_append(self,world,conversation,turn_id,**kwargs):
        before=self.inspect_turn(world_id=world,turn_id=turn_id)
        proof=kwargs['producer_proof']
        vote=kwargs['selection']
        auth=next(e for e in before.graph_context_execution.events
                  if isinstance(e,t.ProviderAttemptAuthorizedEventV3)
                  and e.provider_attempt_id==vote.controller_attempt_id)
        assert sha256(proof['request_json'].encode()).hexdigest()==auth.envelope_sha256
        assert (len(proof['request_json'].encode())>256000)==(copies==6200)
        assert before.graph_context_execution.policy.controller_continuation_accounting.raw_wire_limit_bytes is None
        for kind in ('request','response','oversized_response'):
            changed=dict(proof)
            event=vote
            if kind=='oversized_response':
                changed['response_json']+=' '*256001
                event=vote.model_copy(update={'controller_response_sha256':sha256(changed['response_json'].encode()).hexdigest()})
            else:
                changed[kind+'_json']+=' '
            with pytest.raises(ApplicationStateValidationError,match='Selection producer bytes differ'):
                append(self,world,conversation,turn_id,**{**kwargs,'selection':event,'producer_proof':changed})
            assert self.inspect_turn(world_id=world,turn_id=turn_id)==before
        if copies==6200:
            # Frozen historical requests retain their bound, independently of the
            # current producer. No retained row or historical policy is rewritten.
            execution=before.graph_context_execution
            old=t.BuildControllerContinuationAccountingV3.model_validate({
                **execution.policy.controller_continuation_accounting.model_dump(),
                'policy':'o200k_double_plus_4096_adaptive_context_v3','raw_wire_limit_bytes':256000})
            historical=before.model_copy(update={'graph_context_execution':execution.model_copy(update={
                'policy':execution.policy.model_copy(update={'controller_continuation_accounting':old})})})
            trace,=self.list_context_trace_attempts(world_id=world,turn_id=turn_id)
            with pytest.raises(ValueError,match='Selection producer bytes differ'):
                selection.validate_selection_proof(historical,vote,trace.model_dump(mode='json',by_alias=True),proof)
        result=append(self,world,conversation,turn_id,**kwargs)
        checked.append(True)
        return result

    monkeypatch.setattr(AgentConversationService,'record_build_writer_evidence_selection',check_append)
    case=_fresh_case(lane,tmp_path,monkeypatch,None,False,False,False,native_body='irrelevant')
    assert checked==[True]
    record=case.turn.graph_context_execution
    event,=[e for e in record.events if type(e) is t.ProviderAttemptAuthorizedEventV5
            and e.context_phase=='writer_selection']
    assembled=case.turn.graph_context_receipt.assembled_input
    assert assembled.context_window_limit==64000
    assert assembled.context_window_limit < event.input_tokens <= LONG_LIMIT
    assert event.context_mode=='long_context'
    prefix=record.model_copy(update={'events':record.events[:event.sequence]})
    t.validate_provider_envelope_accounting(assembled,prefix,event)
    request,=[json.loads(req.content) for req in case.decisions.calls
              if json.loads(req.content)['questions'] and all(k.startswith('s') and k[1:].isdigit() for k in json.loads(req.content)['questions'])]
    assert any(row['text']==text for row in request['state']['sources'].values())
    assert len(case.writer.calls)==1 and text not in case.writer.calls[0].content.decode()
    # A mode declaration alone cannot relax scope, phase or accounting. These
    # are rejected by the same owner used for actual APP authorization above.
    for update in ({'context_mode':'default'},{'context_phase':'select'},
                   {'input_tokens':LONG_LIMIT+1},{'output_token_reserve':LONG_LIMIT},
                   {'dispatch_identity_sha256':'f'*64},{'model':'another-model'}):
        with pytest.raises(ValueError):
            t.validate_provider_envelope_accounting(assembled,prefix,event.model_copy(update=update))
    fields={k:v for k,v in event.model_dump().items() if k in t.ProviderAttemptAuthorizedEventV3.model_fields}
    fields['kind']='provider_attempt_authorized_v3'
    unbound=t.ProviderAttemptAuthorizedEventV3.model_validate(fields)
    with pytest.raises(ValueError,match='frozen context window'):
        t.validate_provider_envelope_accounting(assembled,prefix,unbound)


@pytest.mark.parametrize('selection',['section','full_document','source_only'])
def test_ordinary_build_human_source_reaches_writer_and_reopens_exact_citation(lane,tmp_path,monkeypatch,selection):
    _fresh_case(lane,tmp_path,monkeypatch,None,False,False,False,authored_source=selection)


def test_ordinary_build_source_status_guidance_reaches_the_provider(lane, tmp_path, monkeypatch):
    case = _fresh_case(lane, tmp_path, monkeypatch, None, False, False, False,
                       authored_source="full_document")
    assert len(case.writer.calls) == 1
    request = json.loads(case.writer.calls[0].content)
    assert "next-session pickup or resume instruction" in request["instructions"]
    assert "Report supported completed events as completed" in request["instructions"].replace("\n", " ")
    assert case.turn.completion is not None


def test_ordinary_build_projects_managed_images_in_both_sdk_requests(lane, tmp_path, monkeypatch):
    asset = "5086d264-54f6-4411-846b-a59cbf0abcde"
    image = f"![Harbor survey](dmb-media:{asset})"
    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, False, False, False,
        native_body="direct_support",
        native_source_text=f"# Opening\nA proposed note.\n# Episode\nThe source describes a source-local episode.\n{image}\n",
    )
    decisions = [request.content.decode() for request in case.decisions.calls]
    writers = [request.content.decode() for request in case.writer.calls]
    assert any("[Image: Harbor survey]" in request for request in decisions)
    assert len(writers) == 1 and "[Image: Harbor survey]" in writers[0]
    assert all(asset not in request for request in decisions + writers)
    from application_state.agent_conversation.native_corpus import acquired_body_reads
    reads = acquired_body_reads(case.turn.graph_context_execution)
    assert any(image in read.excerpt.text for read in reads)
    assert case.turn.completion.native_body_citations


def test_build_dialogue_cache_checks_same_revision_storage_drift(lane, tmp_path, monkeypatch):
    from application_state.agent_conversation import repository
    from application_state.errors import ApplicationStateIntegrityError, ApplicationStateNotFoundError
    from application_state.unit_of_work import unit_of_work

    case = _fresh_case(lane, tmp_path, monkeypatch, None, False, False, False,
                       authored_source="section")
    world, conversation = case.world, case.turn.conversation_id
    turn_id = case.turn.turn_id
    before = case.service.list_turns(world, conversation, limit=6)
    expected = [item for turn in before if (item := repository._build_dialogue_item(turn)) is not None]
    hydrated = []
    decode = repository._turn_from_row

    def count(conn, row, **fields):
        hydrated.append(row["turn_id"])
        return decode(conn, row, **fields)

    monkeypatch.setattr(repository, "_turn_from_row", count)
    projected = case.service.list_build_dialogue(world, conversation)
    assert projected == expected and hydrated.count(turn_id) == 1
    projected[-1]["assistant"] = "Caller mutation"
    assert case.service.list_build_dialogue(world, conversation) == expected
    assert hydrated.count(turn_id) == 1
    with pytest.raises(ApplicationStateNotFoundError):
        case.service.list_build_dialogue("foreign-world", conversation)

    with unit_of_work() as conn:
        conn.execute("UPDATE agent.turn SET assistant_text=%s WHERE turn_id=%s",
                     ("Changed outside the normal storage owner", turn_id))
    with pytest.raises(ApplicationStateIntegrityError, match="producing output"):
        case.service.list_build_dialogue(world, conversation)
    assert hydrated.count(turn_id) == 2


def test_human_source_is_required_even_when_optional_bodies_are_irrelevant(lane,tmp_path,monkeypatch):
    _fresh_case(lane,tmp_path,monkeypatch,None,False,False,False,
        native_body='irrelevant',authored_source='section')


def test_human_source_survives_reviewed_work_plan_continuation(lane,tmp_path,monkeypatch,application_state_dsn):
    test_native_reviewed_step_preserves_the_author_choice(lane,tmp_path,monkeypatch,application_state_dsn,
        'discuss',False,None,None,authored_source='section')


@pytest.mark.parametrize('change',[None,'newer_page'])
def test_human_source_survives_explicit_retry_without_replacing_draft(lane,tmp_path,monkeypatch,application_state_dsn,change):
    _fresh_case(lane,tmp_path,monkeypatch,'retry_discussion',True,False,False,
        recovery_dsn=application_state_dsn,retry_mutation=change,authored_source='section')


def test_ordinary_human_source_refusal_keeps_request_and_never_dispatches_writer(lane,tmp_path,monkeypatch):
    case=_fresh_case(lane,tmp_path,monkeypatch,None,False,False,False,authored_source='section')
    import copy
    body=copy.deepcopy(case.request)
    body['turn_id']=str(uuid4())
    body['client_thread_id']=str(uuid4())
    body['build_authored_references']['references'][-1]['content_sha256']='f'*64
    before=len(case.writer.calls)
    response=case.client.post('/api/live/agent/turn',json=body)
    assert response.status_code==409,response.text
    assert response.json()['detail']['code']=='authored_source_unavailable'
    assert len(case.writer.calls)==before
    retained=case.service.inspect_turn(world_id=case.world,turn_id=case.writer.adapter.turn.turn_id)
    assert retained.graph_context_execution.policy.action.intent.authored_references.model_dump(mode='json',by_alias=True)==body['build_authored_references']
    from application_state.agent_conversation.native_execution import NATIVE_WRITER_TYPES
    assert not any(type(e) in NATIVE_WRITER_TYPES for e in retained.graph_context_execution.events)
    assert get_workspace_document_snapshot(tmp_path,case.page.document_id)==case.source


def test_saved_v3_human_source_request_retries_with_current_object_navigation(
        lane,tmp_path,monkeypatch,application_state_dsn):
    versions=[]
    _fresh_case(lane,tmp_path,monkeypatch,'retry_discussion',True,False,False,
        recovery_dsn=application_state_dsn,authored_source='section',
        historical_query_versions=versions)
    assert versions[0] == 'dmb_native_graph_query_v3'
    assert len(versions) >= 2 and set(versions[1:]) == {'dmb_native_graph_query_v4'}


@pytest.mark.parametrize('failure',['writer_incomplete_limit','writer_incomplete_filter','writer_incomplete_unknown'])
def test_native_build_reports_actual_incomplete_writer_reason_without_acceptance_or_retry(lane,tmp_path,monkeypatch,failure):
    _fresh_case(lane,tmp_path,monkeypatch,failure,True,False,False)


@pytest.mark.parametrize('failure', [None, 'writer_incomplete_filter'])
@pytest.mark.parametrize('prompt_capture', [False, True])
def test_native_authorization_is_visible_before_actual_provider_transport(lane,tmp_path,monkeypatch,failure,prompt_capture):
    if prompt_capture:
        monkeypatch.setenv('DMB_AGENT_PROMPT_CAPTURE','1')
    else:
        monkeypatch.delenv('DMB_AGENT_PROMPT_CAPTURE',raising=False)
    observed=[]
    def inspect_before_response(adapter,provider):
        capture=adapter.context_capture
        attempt=adapter.last_provider_attempt_id
        trace=capture.trace
        assert trace.turn_id==adapter.fence.turn.turn_id
        assert trace.conversation_id==adapter.fence.turn.conversation_id
        assert trace.attempt==adapter.fence.turn.attempt
        prompts=[o for o in trace.observations if o.kind=='prompt_reference' and o.provider_attempt_id==attempt]
        grants=[o for o in trace.observations if o.kind=='provider_call' and o.provider_attempt_id==attempt and o.outcome=='authorized']
        assert len(prompts)==len(grants)==1, 'Actual native provider entry lacks one recorded authorization'
        assert grants[0].provider==prompts[0].provider==provider
        assert grants[0].model==prompts[0].model
        assert grants[0].sequence>prompts[0].sequence
        assert not any(o.kind=='provider_call' and o.provider_attempt_id==attempt and o.outcome=='response_received'
            for o in trace.observations)
        observed.append((adapter,attempt,provider))
    _fresh_case(lane,tmp_path,monkeypatch,failure,False,False,False,before_provider=inspect_before_response)
    assert {provider for _,_,provider in observed}=={'typesafe','openai'}
    assert len({attempt for _,attempt,_ in observed})==len(observed)
    adapter=observed[-1][0]
    trace=adapter.service.list_context_trace_attempts(world_id=adapter.turn.world_id,turn_id=adapter.turn.turn_id)[-1]
    for _,attempt,_ in observed:
        assert sum(o.kind=='provider_call' and o.provider_attempt_id==attempt and o.outcome=='authorized'
            for o in trace.observations)==1
    assert trace.terminal_status==('interrupted' if failure else 'completed')
    if failure:
        assert any(o.kind=='failure' and o.stage=='writer_generation' for o in trace.observations)


@pytest.mark.parametrize('mutation',[None,'race','newer_page','question','reference','revision','unknown','write_capability'])
def test_native_connected_review_retries_retained_context_without_inheriting_write_authority(lane,tmp_path,monkeypatch,application_state_dsn,mutation):
    _fresh_case(lane,tmp_path,monkeypatch,'retry_unknown' if mutation=='unknown' else 'retry_discussion',
        True,True,False,recovery_dsn=application_state_dsn,retry_mutation=mutation,
        connected_review='valid',capture_write=True,authored_source='section')


@pytest.mark.parametrize('draft',[False,True])
def test_fresh_build_initial_sdk_exposes_semantic_context_and_keeps_authority_host_side(lane,tmp_path,monkeypatch,draft):
    case=_fresh_case(lane,tmp_path,monkeypatch,None,draft,False,False,authored_source='section',capture_write=draft)
    first=json.loads(case.decisions.calls[0].content)
    assert set(first['state'])=={'user_question','interaction'}
    context=first['state']['interaction']
    assert set(context)<={'allowed_operations','current_page_title','history','page_target','working_draft_available','author_selected_references','related_page_labels'}
    assert context['working_draft_available'] is draft
    assert all(set(row)<={'kind','label','selection_kind'} for row in context['author_selected_references'])
    assert any(row['kind']=='source' and row['selection_kind']=='section' for row in context['author_selected_references'])
    assert case.turn.graph_context_receipt.assembled_input.assembler_version=='native_build_semantic_initial_v2'
    retained=type(case.turn).model_validate_json(case.turn.model_dump_json(by_alias=True))
    assert retained==case.turn


@pytest.mark.parametrize('mutation',['user','title','operations','target','proposed_work','questions','request_id','codec','capability','destination'])
def test_fresh_build_rejects_changed_initial_parent_before_provider(lane,tmp_path,monkeypatch,mutation):
    from dataclasses import replace
    from apps.live_control_server.services.build_jev_driver import BuildJevDriver,canonical
    original=BuildJevDriver.stage
    def changed(driver):
        plan=original(driver)
        if plan.host_phase!='select':return plan
        state=plan.state()
        updates={}
        if mutation=='user':state['user_question']='A different task'
        elif mutation=='title':state['interaction']['current_page_title']='Wrong destination'
        elif mutation=='operations':state['interaction']['allowed_operations']=['propose_build_insertion']
        elif mutation=='target':state['interaction']['page_target']={'kind':'replace_selection','text':'Uncaptured target'}
        elif mutation=='proposed_work':state['interaction']['history']=[{'user':'Other request','assistant':'','proposed_work':{'kind':'questions','questions':[{'text':'Wrong question'}]}}]
        elif mutation=='questions':updates['questions_json']=canonical({'requested_work':{'type':'choice','instructions':'Changed task','criteria':{'discuss':None}}})
        elif mutation=='request_id':updates['request_id']='select:'+'f'*64
        elif mutation=='codec':updates['host_phase']=None
        elif mutation in {'capability','destination'}:
            host=driver._interaction
            if mutation=='capability':host['capability_sha256']='f'*64
            else:host['current_page']['document_id']='foreign-page'
            updates['host_interaction_json']=canonical(host)
        updates['state_json']=canonical(state)
        driver._pending=replace(plan,**updates)
        return driver._pending
    monkeypatch.setattr(BuildJevDriver,'stage',changed)
    _fresh_case(lane,tmp_path,monkeypatch,'initial_context',False,False,False)


def test_native_selection_semantic_sdk_wire_and_exact_legacy_v2_reader(lane,tmp_path,monkeypatch):
    from copy import deepcopy
    from application_state.agent_conversation import writer_evidence_selection as selection
    append = AgentConversationService.record_build_writer_evidence_selection
    checked=[]
    def inspect(self,world,conversation,turn_id,**kwargs):
        before=self.inspect_turn(world_id=world,turn_id=turn_id)
        execution=before.graph_context_execution
        assert before.graph_context_receipt.assembled_input.assembler_version=='native_build_semantic_initial_v2'
        vote,proof=kwargs['selection'],kwargs['producer_proof']
        auth=next(e for e in execution.events if isinstance(e,t.ProviderAttemptAuthorizedEventV5)
                  and e.provider_attempt_id==vote.controller_attempt_id)
        trace,=self.list_context_trace_attempts(world_id=world,turn_id=turn_id)
        trace=trace.model_dump(mode='json',by_alias=True)
        request,catalog=selection.validate_prepared_selection(before,auth,proof['request_json'],trace)
        assert set(request['state'])=={'user_question','sources','rules'}
        assert list(request['state']['sources'])==list(request['questions'])
        host=selection.selection_state(before,catalog,vote.terminal_disposition,selection.selection_history(before,auth))
        for key in ('catalog_sha256','basis_sha256','native_query_sha256','source_basis','historical_initial','context_accounting','phase'):
            assert key not in request['state']
        for key in catalog:
            assert key not in proof['request_json']
        for unit in catalog.values():
            for key in ('source_artifact_id','source_revision_id'):
                assert unit['passage'][key] not in proof['request_json']
            assert any(row['text']==unit['passage']['text'] for row in request['state']['sources'].values())
        legacy=dict(model=auth.model,state=host,questions=selection.questions(catalog))
        legacy_raw=selection.canonical(legacy)
        old_auth=auth.model_copy(update={'envelope_sha256':sha256(legacy_raw.encode()).hexdigest()})
        selection.validate_prepared_selection(before,old_auth,legacy_raw,trace)
        # A retained V2 initial receipt with legacy final-selection bytes still
        # reconstructs the exact old host commitment and response closure.
        old_execution=execution.model_copy(update={'events':[old_auth if e is auth else e for e in execution.events]})
        old_before=before.model_copy(update={'graph_context_execution':old_execution})
        old_vote=vote.model_copy(update={'controller_envelope_sha256':old_auth.envelope_sha256,
            'basis_sha256':host['basis_sha256']})
        selection.validate_selection_proof(old_before,old_vote,trace,{**proof,'request_json':legacy_raw})
        selection.validate_selection_proof(before,vote,trace,proof)
        for mutation in ('hybrid','unknown','text','question','source_id'):
            changed=deepcopy(request)
            if mutation=='hybrid':changed['state']['phase']='writer_selection'
            elif mutation=='unknown':changed['state']['unexpected']='ignored?'
            elif mutation=='text':next(iter(changed['state']['sources'].values()))['text']='Different evidence'
            elif mutation=='question':changed['questions']['s0']['instructions']='Classify another source'
            else:next(iter(changed['state']['sources'].values()))['source_artifact_id']='not allowed'
            raw=selection.canonical(changed)
            changed_auth=auth.model_copy(update={'envelope_sha256':sha256(raw.encode()).hexdigest()})
            with pytest.raises(ValueError):selection.validate_prepared_selection(before,changed_auth,raw,trace)
        for field in ('catalog_sha256','basis_sha256'):
            bad_vote=vote.model_copy(update={field:'0'*64})
            with pytest.raises(ValueError,match='basis'):
                selection.validate_selection_proof(before,bad_vote,trace,proof)
        bad_terminal=vote.model_copy(update={'terminal_disposition':{'status':'ready','reason':'invented'}})
        with pytest.raises(ValueError,match='terminal'):
            selection.validate_selection_proof(before,bad_terminal,trace,proof)
        checked.append(True)
        return append(self,world,conversation,turn_id,**kwargs)
    monkeypatch.setattr(AgentConversationService,'record_build_writer_evidence_selection',inspect)
    case=_fresh_case(lane,tmp_path,monkeypatch,None,False,False,False,native_body='direct_support')
    assert checked==[True] and case.turn.completion.native_body_citations


def test_low_score_valid_image_selection_prepares_review_through_ordinary_http(lane,tmp_path,monkeypatch):
    # Derived from the captured .40 winner, with zero votes for newer menu labels.
    # This synthetic response exercises the unique maximum, not a .90 gate. No image provider is called.
    scores=dict(build_encounter=0.0,change_mechanics=0.0,clarify_creation=.07,clarify_request=.04,
        discuss=0.0,draft_in_conversation=0.0,other_creation=.27,place_map_coordinates=0.0,plan=.02,prepare_image=.40,
        publish_relationships=0.0,review_connected_page=.01,review_relationship=0.0,
        review_variant_approval=0.0,review_lore_page=0.0,review_lore_page_from_conversation=0.0,review_blank_lore_page=0.0,save_page=0.0,write_current_page=.19)
    _fresh_case(lane,tmp_path,monkeypatch,None,True,False,'image',selection_probabilities=scores,
        message='Create an interior design detailed enough to generate a map from.')


@pytest.mark.parametrize('mutation',[None,'capability','question','reference','revision'])
def test_native_unresolved_authoring_retry_requires_fresh_capture_and_preserves_failure(lane,tmp_path,monkeypatch,mutation):
    _fresh_case(lane,tmp_path,monkeypatch,'retry_authoring_selection',True,False,True,retry_mutation=mutation)


@pytest.mark.parametrize("mode", [True, "associated", "by-name"])
def test_fresh_build_can_open_saved_statblock(lane, tmp_path, monkeypatch, mode):
    from threading import Event
    from application_state.agent_conversation.native_context import NativeBuildQueryPendingV1
    from application_state.agent_conversation.native_execution import NativeBuildQuerySettledV1
    from apps.live_control_server.services import native_graph_reads

    first_wire = Event()
    query_calls = []

    def witness(adapter, provider):
        if mode != "by-name" or provider != "typesafe" or first_wire.is_set():
            return
        phase_names = [span["name"] for span in adapter.trace.spans]
        assert phase_names.count("build_first_jev_request_preparation") == 1
        assert phase_names.index("build_first_jev_request_preparation") < phase_names.index(
            "build_first_jev_authorization"
        )
        assert isinstance(adapter.native_query, NativeBuildQueryPendingV1)
        assert not any(isinstance(event, NativeBuildQuerySettledV1)
                       for event in adapter.turn.graph_context_execution.events)
        from application_state.agent_conversation.context_trace import TracePromptReference, TraceProviderCall
        from apps.live_control_server.services.agent_prompt_evidence import read_prompt

        turn = adapter.turn
        (trace,) = adapter.service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)
        (prompt,) = [item for item in trace.observations if isinstance(item, TracePromptReference)]
        authorized = trace.observations[prompt.sequence + 1]
        assert isinstance(authorized, TraceProviderCall)
        assert authorized.outcome == "authorized"
        assert authorized.provider_attempt_id == prompt.provider_attempt_id
        actual = adapter._prepared_build_decision
        assert read_prompt(prompt).encode("utf-8") == actual.body
        assert prompt.payload_sha256 == actual.body_sha256
        first_wire.set()

    if mode == "by-name":
        prepare = native_graph_reads.prepare_query

        def wait_for_opening(*args, **kwargs):
            assert first_wire.wait(timeout=5), "Graph preparation blocked opening transport"
            query_calls.append(True)
            return prepare(*args, **kwargs)

        monkeypatch.setattr(native_graph_reads, "prepare_query", wait_for_opening)

    case = _fresh_case(lane, tmp_path, monkeypatch, None, False, False, False,
        message="This is a challenging question, now we have to design this meat node and it's abilities, see if you can find the statblock for the meat mind.",
        saved_statblock=mode, before_provider=witness)
    if mode == "by-name":
        assert first_wire.is_set() and query_calls == [True]
        (settlement,) = [event for event in case.turn.graph_context_execution.events
                        if isinstance(event, NativeBuildQuerySettledV1)]
        assert settlement.query.authority == case.turn.graph_context_receipt.native_query.authority
    root = f"/api/live/agent/worlds/{case.world}/conversations"
    response = case.client.get(root + "/active/messages")
    assert response.status_code == 200, response.text
    references = response.json()["messages"][-1]["saved_statblocks"]
    assert len(references) == 1
    assert references[0]["name"] == "Meat Mind"
    assert references[0]["revision_id"] == "rev_meatmind"
    from application_state.agent_conversation.build_saved_statblock import BuildSavedStatblockReadV1
    read, = [event for event in case.turn.graph_context_execution.events if isinstance(event, BuildSavedStatblockReadV1)]
    assert read.locator.revision_id == "rev_meatmind"
    sources = references[0]["pdf_sources"]
    if mode in {"associated", "by-name"}:
        assert "Hit Points 41" in response.json()["messages"][-1]["assistant_text"]
        assert sources["scope"]["managed_world_id"] == case.world
        assert sources["support"] == [{"assertion_id": "assertion:fixture", "evidence_ref_id": "pdf-region:fixture"}]
    else:
        assert sources is None


@pytest.mark.parametrize("scope", ["anchored", "source_lookup"])
def test_draft_acquires_optional_page_only_for_source_lookup(lane, tmp_path, monkeypatch, scope):
    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, True, False, False,
        message="Draft the variant for this encounter in conversation.",
        requested_work="draft_in_conversation", saved_statblock="associated",
        source_need=scope, read_optional_page=True,
    )
    requests = [json.loads(call.content) for call in case.decisions.calls]
    assert any(name.startswith("related_page_") for request in requests for name in request["questions"])
    events = case.turn.graph_context_execution.events
    assert any(isinstance(event, t.BuildDraftContextCapturedV1) for event in events)
    assert any(event.kind == "build_related_page_read_v1" for event in events) == (scope == "source_lookup")
    assert any(event.kind == "build_saved_statblock_read_v1" for event in events)


def test_anchored_discussion_only_offers_current_page_and_saved_mechanics(lane, tmp_path, monkeypatch):
    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, True, False, False,
        message="Let's brainstorm this creature.", requested_work="discuss",
        saved_statblock="associated", source_need="anchored", read_optional_page=True,
    )
    resolution, = [event for event in case.turn.graph_context_execution.events
                   if isinstance(event, t.BuildRequestedWorkResolutionV1)]
    assert resolution.resolution["source_scope"] == "anchored"
    requests = [json.loads(call.content) for call in case.decisions.calls]
    assert any(name.startswith("related_page_") for request in requests for name in request["questions"])
    assert not any(event.kind.startswith("build_related_page") for event in case.turn.graph_context_execution.events)
    retrieval = [request for request in requests if "operation" in request["questions"]]
    assert retrieval
    kinds = [candidate["kind"] for request in retrieval
             for candidate in request["state"].get("candidates", [])]
    assert any(kind.startswith("Saved statblock") for kind in kinds)
    assert all(kind.startswith(("Saved statblock", "Saved authored page block"))
               or kind == "public_rules_lookup" for kind in kinds)
    assert all("discover_more" not in request["questions"]["operation"]["criteria"]
               for request in retrieval)


@pytest.mark.parametrize("editor_mounted", [False, True])
def test_benchmark_captures_consecutive_mounted_build_turns(lane, tmp_path, monkeypatch, editor_mounted):
    from evals.buddy_benchmark import workflow

    thread_id = str(uuid4())
    draft_request = "Draft a playable variant in this conversation for review."
    template = {}
    snapshot = None

    def first(client, world, body):
        nonlocal snapshot
        template.update((key, value) for key, value in body.items() if key != "message")
        if editor_mounted:
            from application_state.agent_conversation.build_draft_context import BuildDraftSnapshotV1
            work = body["primary_work"]
            page = get_workspace_document_snapshot(tmp_path, work["object_id"])
            snapshot = BuildDraftSnapshotV1(world_id=world, document_id=work["object_id"],
                registry_revision=page.loaded_revision, content_sha256=page.content_sha256,
                visibility=page.record.visibility_state, draft_markdown=page.markdown,
                draft_sha256=page.content_sha256, editor_sha256="c" * 64, draft_generation=0)
        return workflow.capture_case(client, world, template, {"question": body["message"]},
                                     tmp_path / "first-capture", build_thread_id=thread_id, build_editor_snapshot=snapshot)

    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, False, False, False,
        message="Let's brainstorm a variant of this creature.",
        requested_work=lambda message: "draft_in_conversation" if message == draft_request else "discuss",
        saved_statblock="associated", dispatch=first,
    )
    from unittest.mock import Mock
    from apps.live_control_server.services import native_graph_inspection

    fresh_pdf_reads = Mock(wraps=native_graph_inspection.statblock_pdf_support)
    monkeypatch.setattr(native_graph_inspection, "statblock_pdf_support", fresh_pdf_reads)
    for index, question in enumerate((
        "Could it negotiate?",
        "What choice could I offer the players?",
        "Keep the Dust Walker in conflict with it.",
        draft_request,
    ), start=2):
        response = workflow.capture_case(
            case.client, case.world, template, {"question": question},
            tmp_path / f"capture-{index}", build_thread_id=thread_id,
            expected_conversation_id=str(case.turn.conversation_id), build_editor_snapshot=snapshot,
        )
        assert response.status_code == 200, response.text
    history = case.client.get(f"/api/live/agent/worlds/{case.world}/conversation").json()
    assert len(history["turns"]) == 5
    if editor_mounted:
        for capture in (tmp_path / "first-capture", tmp_path / "capture-5"):
            request = json.loads((capture / "request.json").read_text())
            before_name = "fresh-history" if capture.name == "first-capture" else "history-before"
            before = json.loads((capture / f"{before_name}.json").read_text())["body"]
            assert request["build_draft_context"]["expected_pointer_revision"] == before["pointer_revision"]
            assert request["build_draft_context"]["conversation_id"] == before["active_conversation_id"]
            assert request["build_draft_context"]["snapshot"]["draft_markdown"] == snapshot.draft_markdown
    service = AgentConversationService()
    turns = [service.inspect_turn(world_id=case.world, turn_id=UUID(row["turn_id"])) for row in history["turns"]]
    from application_state.agent_conversation.build_saved_statblock import BuildSavedStatblockReadV1

    reads = [[event for event in turn.graph_context_execution.events
        if isinstance(event, BuildSavedStatblockReadV1)] for turn in turns]
    assert all(len(events) == 1 for events in reads)
    initial_pin = reads[0][0].pdf_support.scope.revision_id
    current_pin = turns[1].graph_context_receipt.source_authority.revision_id
    assert initial_pin != current_pin
    assert fresh_pdf_reads.call_count == 1
    assert fresh_pdf_reads.call_args.args[0].graph_revision == current_pin
    assert reads[1][0].reused_from_turn_id is None
    assert all(events[0].pdf_support.scope.revision_id == current_pin for events in reads[1:])
    assert all(events[0].reused_from_turn_id is not None for events in reads[2:])
    assert all(turn.conversation_id == case.turn.conversation_id for turn in turns)
    assert service.conversation_draft_turn_ids(case.world, case.turn.conversation_id,
        [turn.turn_id for turn in turns]) == {turns[-1].turn_id}
    root = f"/api/live/agent/worlds/{case.world}/conversations/{case.turn.conversation_id}"
    draft_path = f"{root}/drafts/{turns[-1].turn_id}"
    draft = case.client.get(draft_path)
    review_id, = draft.json()["variant_review_ids"]
    review = case.client.get(f"{draft_path}/variant-reviews/{review_id}").json()
    assert review["base_locator"]["revision_id"] == "rev_meatmind"
    from tests.test_statblock_acceptance_reconciliation import _definition

    base = _definition().model_dump(mode="json")
    new_rule = base["rule_elements"][0] | {"key": "truce", "name": "Terms of Truce", "costs": []}
    assert review["definition"] == base | {"rule_elements": [*base["rule_elements"], new_rule]}
    assert review["saved"] is False
    from tests.application_state.test_conversation_drafts import _check_variant_response_loss

    _check_variant_response_loss(
        service, {"world_id": case.world, "conversation_id": case.turn.conversation_id,
                  "turn_id": turns[-1].turn_id}, monkeypatch, case.client.app, draft_path,
        existing_review=UUID(review_id), existing_definition=review["definition"], mounted_client=case.client,
    )
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document
    from tests.test_authored_page_database_cutover import save

    page_id = template["primary_work"]["object_id"]
    page = get_workspace_document(tmp_path, page_id)
    preceding = get_workspace_document_snapshot(tmp_path, page_id)
    assert preceding.content_sha256 == template["primary_work"]["expected_content_sha256"]
    href = (
        f"/statblock?world={case.world}&conversation={case.turn.conversation_id}"
        f"&turn={turns[-1].turn_id}&variantReview={review_id}"
    )
    edited = preceding.markdown.rstrip() + f"\n\n[Open saved statblock variant]({href})\n"
    result, _ = save(tmp_path, page, edited)
    reopened = get_workspace_document_snapshot(tmp_path, page_id)
    assert reopened.loaded_revision == result.committed_record.revision
    assert reopened.markdown == edited
    assert reopened.markdown.count(href) == 1
    saved_variant = case.client.get(f"{draft_path}/variant-reviews/{review_id}/saved")
    assert saved_variant.status_code == 200, saved_variant.text
    assert saved_variant.json()["locator"]["revision_id"] == "rev_variant01"



def test_followup_reoffers_only_the_bound_statblock_on_the_same_page(lane, tmp_path, monkeypatch):
    from application_state.agent_conversation.build_saved_statblock import BuildSavedStatblockReadV1
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver

    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, False, False, False,
        message="Let's brainstorm a variant of this creature.",
        requested_work="discuss", saved_statblock="associated",
    )
    previous = case.turn
    read, = [event for event in previous.graph_context_execution.events
             if isinstance(event, BuildSavedStatblockReadV1)]
    current = previous.model_copy(update={"sequence": previous.sequence + 1})
    driver = object.__new__(PlanJevDriver)
    driver.statblock_world = case.world
    from application_state.agent_conversation.types import BuildAuthoredReferencesCapturedV1
    capture, = [event for event in previous.graph_context_execution.events
                if isinstance(event, BuildAuthoredReferencesCapturedV1)]
    reference, = capture.references.references
    entry = (reference.label, read.draft_id, read.locator, reference)
    calls = []

    def list_turns(world, conversation, **kwargs):
        calls.append((world, conversation, kwargs))
        return [previous]

    driver.adapter = SimpleNamespace(
        fence=SimpleNamespace(turn=current), service=SimpleNamespace(list_turns=list_turns),
    )
    monkeypatch.setattr(driver, "_published_statblock_reference", lambda draft, locator: reference)
    assert driver._prior_bound_statblock() == (entry,)
    assert calls == [(case.world, current.conversation_id, {"limit": 12, "before_sequence": current.sequence})]

    execution = previous.graph_context_execution
    action = execution.policy.action
    unselected_action = action.model_copy(update={
        "intent": action.intent.model_copy(update={"authored_references": None}),
    })
    discussion = previous.model_copy(update={
        "sequence": current.sequence,
        "graph_context_execution": execution.model_copy(update={
            "policy": execution.policy.model_copy(update={"action": unselected_action}),
            "events": tuple(event for event in execution.events
                            if not isinstance(event, (BuildSavedStatblockReadV1, BuildAuthoredReferencesCapturedV1))),
        }),
    })
    driver.adapter.fence.turn = current.model_copy(update={"sequence": current.sequence + 1})
    driver.adapter.service.list_turns = lambda *_args, **_kwargs: [previous, discussion]
    assert driver._prior_bound_statblock() == (entry,)
    assert read.association_anchor is not None
    with monkeypatch.context() as drift:
        drift.setattr(driver, "_current_statblock_anchor", lambda *_: read.association_anchor.model_copy(
            update={"association_id": uuid4()},
        ))
        assert driver._prior_bound_statblock() == ()

    intervening_selection = discussion.model_copy(update={
        "graph_context_execution": discussion.graph_context_execution.model_copy(update={
            "events": (*discussion.graph_context_execution.events, capture),
        }),
    })
    driver.adapter.service.list_turns = lambda *_args, **_kwargs: [previous, intervening_selection]
    assert driver._prior_bound_statblock() == ()

    empty_selection = action.intent.authored_references.model_copy(update={"references": ()})
    empty_action = action.model_copy(update={
        "intent": action.intent.model_copy(update={"authored_references": empty_selection}),
    })
    discussion_execution = discussion.graph_context_execution
    cleared = discussion.model_copy(update={
        "graph_context_execution": discussion_execution.model_copy(update={
            "policy": execution.policy.model_copy(update={"action": empty_action}),
        }),
    })
    driver.adapter.service.list_turns = lambda *_args, **_kwargs: [previous, cleared]
    assert driver._prior_bound_statblock() == ()

    driver.adapter.fence.turn = current
    driver.adapter.service.list_turns = list_turns
    monkeypatch.setattr(driver, "_published_statblock_reference", lambda draft, locator: None)
    assert driver._prior_bound_statblock() == ()

    from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
    driver.adapter.service.list_turns = lambda *_args, **_kwargs: [MixedCompletedTurnV1.model_construct()]
    assert driver._prior_bound_statblock() == ()
    driver.adapter.service.list_turns = list_turns

    work = current.graph_context_receipt.work_context
    changed_basis = work.source_basis.model_copy(update={"source_revision": 99, "document_id": uuid4()})
    changed_work = work.model_copy(update={"source_basis": changed_basis})
    changed_receipt = current.graph_context_receipt.model_copy(update={"work_context": changed_work})
    driver.adapter.fence.turn = current.model_copy(update={"graph_context_receipt": changed_receipt})
    monkeypatch.setattr(driver, "_published_statblock_reference", lambda *_: pytest.fail("Changed page must not resolve mechanics"))
    assert driver._prior_bound_statblock() == ()


def test_referenced_statblock_excludes_historical_graph_reference(monkeypatch):
    from application_state.world_mechanics import service as associations
    from apps.live_control_server.services import world_creature_selection
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver

    driver = object.__new__(PlanJevDriver)
    driver.statblock_world = "fixture-world"
    target = SimpleNamespace(node_id="ent:fixture", matches_association_target=lambda _: True)
    record = SimpleNamespace(request=SimpleNamespace(target=target, draft_id="draft"),
                             proof=SimpleNamespace(locator="current mechanics"))
    monkeypatch.setattr(associations, "list_current", lambda **kwargs: [record])
    monkeypatch.setattr(world_creature_selection, "catalog", lambda *args, **kwargs: SimpleNamespace(
        native_world_id="fixture-world", binding_version=1, revision_id="rev:old",
        head_revision_id="rev:current", targets=(target,),
    ))
    reference = AuthoredGraphReferenceV1(
        managed_world_id="fixture-world", native_world_id="fixture-world", binding_version=1,
        graph_revision="rev:old", node_id="ent:fixture", label="Fixture",
    )
    assert driver._referenced_statblocks((reference,)) == []


@pytest.mark.parametrize("variant_validation", ["valid", "warnings", "invalid", None, "malformed", "mismatched"])
def test_ordinary_build_attaches_variant_review_to_conversation_draft(
    lane, tmp_path, monkeypatch, variant_validation, application_state_dsn,
):
    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, False, False, False,
        message="Draft the Meat Mind variant in this conversation for review.",
        requested_work="draft_in_conversation", saved_statblock="associated",
        variant_validation=variant_validation,
    )
    root = f"/api/live/agent/worlds/{case.world}/conversations/{case.turn.conversation_id}"
    draft_path = f"{root}/drafts/{case.turn.turn_id}"
    draft = case.client.get(draft_path)
    assert draft.status_code == 200, draft.text
    messages = case.client.get(f"/api/live/agent/worlds/{case.world}/conversations/active/messages")
    assert messages.status_code == 200, messages.text
    row = messages.json()["messages"][-1]
    assert row["turn_id"] == str(case.turn.turn_id)
    assert row.get("variant_draft_reviewed") is (True if variant_validation in {"valid", "warnings"} else None)
    if variant_validation not in {"valid", "warnings"}:
        assert draft.json()["markdown"]
        assert not draft.json().get("variant_review_ids")
        return
    review_id, = draft.json()["variant_review_ids"]
    reviewed = case.client.get(f"{draft_path}/variant-reviews/{review_id}")
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["base_locator"]["revision_id"] == "rev_meatmind"

    definition = reviewed.json()["definition"]
    markdown = draft.json()["markdown"]
    assert markdown.startswith(f"# {definition['identity']['name']}\n")
    assert all(rule["rules_text"] in markdown for rule in definition["rule_elements"])
    assert markdown != case.turn.assistant_text
    # Editing the draft invalidates the associated review and its chat projection.
    edited = case.client.put(draft_path, json={"expected_revision": 1, "markdown": markdown + "\nEdited."})
    assert edited.status_code == 200, edited.text
    assert "variant_review_ids" not in edited.json()
    reopened = case.client.get(f"/api/live/agent/worlds/{case.world}/conversations/active/messages")
    assert reopened.status_code == 200, reopened.text
    assert "variant_draft_reviewed" not in reopened.json()["messages"][-1]

    # When the newer revision gains its own review, the chat can present it.
    from uuid import uuid4

    import psycopg

    from application_state.agent_conversation.conversation_variant_save import store_review

    with psycopg.connect(application_state_dsn) as conn:
        store_review(
            conn, world_id=case.world, conversation_id=case.turn.conversation_id,
            turn_id=case.turn.turn_id, revision=2, review_id=uuid4(),
            definition=definition, base_locator=reviewed.json()["base_locator"],
        )
    reopened = case.client.get(f"/api/live/agent/worlds/{case.world}/conversations/active/messages")
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["messages"][-1]["variant_draft_reviewed"] is True


def test_requested_chat_draft_is_persisted_by_ordinary_build(lane, tmp_path, monkeypatch):
    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, False, False, False,
        message="Write an editable Markdown draft in chat for review.",
        requested_work="draft_in_conversation",
    )
    light = case.client.get(f"/api/live/agent/worlds/{case.world}/conversations/active/messages")
    assert light.status_code == 200, light.text
    assert light.json()["messages"][-1]["conversation_draft_available"] is True
    assert case.service.conversation_draft_turn_ids(
        case.world, case.turn.conversation_id, [case.turn.turn_id],
    ) == {case.turn.turn_id}, (
        type(case.turn).__name__, type(case.turn.completion).__name__,
        [getattr(event, "requested_work", None) for event in case.turn.graph_context_execution.events
         if hasattr(event, "requested_work")],
    )
    root = f"/api/live/agent/worlds/{case.world}/conversation"
    history = case.client.get(root, params={"include_turn_correlation": True})
    assert history.status_code == 200, history.text
    page = history.json()
    turn = page["turns"][-1]
    assert turn["conversation_draft_available"] is True
    draft = case.client.get(
        f"{root}s/{page['conversation_id']}/drafts/{turn['turn_id']}"
    )
    assert draft.status_code == 200, draft.text
    assert draft.json() == {"revision": 1, "markdown": turn["assistant_text"]}


def test_brainstorm_stays_in_chat_without_creating_a_draft(lane, tmp_path, monkeypatch):
    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, False, False, False,
        message="Let's brainstorm how a clockwork fox could help the Lantern Market.",
        requested_work="discuss",
    )
    light = case.client.get(f"/api/live/agent/worlds/{case.world}/conversations/active/messages")
    assert light.status_code == 200, light.text
    assert "conversation_draft_available" not in light.json()["messages"][-1]
    assert case.service.conversation_draft_turn_ids(
        case.world, case.turn.conversation_id, [case.turn.turn_id],
    ) == set()
    response = case.client.get(
        f"/api/live/agent/worlds/{case.world}/conversation",
        params={"include_turn_correlation": True},
    )
    assert response.status_code == 200, response.text
    reply = response.json()["turns"][-1]
    assert "conversation_draft_available" not in reply
    assert not case.turn.completion.collaboration
    assert not any(
        getattr(event, "operation", None) == "propose_build_insertion"
        for event in case.turn.graph_context_execution.events
    )


def test_selected_mechanics_are_available_without_repeating_the_artifact_name(lane, tmp_path, monkeypatch):
    case = _fresh_case(lane, tmp_path, monkeypatch, None, False, False, False,
        message="Let's brainstorm why it wants freedom and whether the party could negotiate.",
        saved_statblock="associated")
    response = case.client.get(f"/api/live/agent/worlds/{case.world}/conversations/active/messages")
    assert response.status_code == 200
    references = response.json()["messages"][-1]["saved_statblocks"]
    assert [(ref["name"], ref["revision_id"]) for ref in references] == [("Meat Mind", "rev_meatmind")]


def test_variant_markdown_preserves_cross_references_and_armor_profiles():
    from apps.live_control_server.services.conversation_variant_markdown import render_variant_markdown
    from tests.test_statblock_acceptance_reconciliation import _definition

    base = _definition()
    data = base.model_dump(mode="json")
    data["defenses"]["armor_classes"] = [
        {"key": "base", "default": True, "value": 16},
        {"key": "shell", "default": False, "value": 19, "condition": "While concealed"},
    ]
    data["resources"] = [{"key": "charge_pool", "name": "Charge", "maximum": 2, "refresh": "At dawn"}]
    rule = data["rule_elements"][0]
    rule["usage"] = {"kind": "manual", "resource_key": "charge_pool"}
    markdown = render_variant_markdown(type(base).model_validate(data))

    assert "**Armor class** 16 (default)" in markdown
    assert "**Armor class** 19 (alternate) (While concealed)" in markdown
    assert "**Resources** Key: charge_pool; Maximum: 2; Name: Charge; Refresh: At dawn" in markdown
    assert "**Use** Kind: manual; Resource key: charge_pool" in markdown
    assert f"**Rule reference** `{rule['key']}`" in markdown


def test_variant_correction_creates_a_new_review_without_saving(lane, tmp_path, monkeypatch):
    from copy import deepcopy
    from datetime import datetime, timezone
    from application_state.agent_conversation.conversation_variant_save import approval_handoff
    from application_state.unit_of_work import unit_of_work

    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, False, False, False,
        message="Draft the Meat Mind variant in this conversation for review.",
        requested_work="draft_in_conversation", saved_statblock="associated",
    )
    root = f"/api/live/agent/worlds/{case.world}/conversations/{case.turn.conversation_id}"
    draft_path = f"{root}/drafts/{case.turn.turn_id}"
    draft = case.client.get(draft_path).json()
    review_id, = draft["variant_review_ids"]
    prior_path = f"{draft_path}/variant-reviews/{review_id}"
    prior = case.client.get(prior_path).json()
    target = prior["definition"]["rule_elements"][-1]
    revised = target["rules_text"] + " This only happens after the warning."
    correction = {"expected_revision": 1, "replacements": [{
        "rule_key": target["key"], "field": "rules_text",
        "replace_exact": target["rules_text"], "with_text": revised,
    }]}
    original_approval_time = datetime.now(timezone.utc)
    result = case.client.put(prior_path, json=correction)
    assert result.status_code == 200, result.text
    successor = result.json()
    assert successor["revision"] == 2
    assert successor["review_id"] != review_id
    assert case.client.get(prior_path).json() == prior
    successor_path = f"{draft_path}/variant-reviews/{successor['review_id']}"
    review = case.client.get(successor_path).json()
    expected = deepcopy(prior)
    expected["revision"] = 2
    expected["definition"]["rule_elements"][-1]["rules_text"] = revised
    assert review == expected
    assert case.client.get(successor_path + "/saved").status_code == 404
    assert case.client.post(prior_path + "/confirm").status_code == 409
    assert case.client.put(prior_path, json=correction).status_code == 409
    new_draft = case.client.get(draft_path).json()
    assert new_draft["variant_review_ids"] == [successor["review_id"]]
    assert revised in new_draft["markdown"]
    primary = case.turn.provenance.primary_work
    target_scope = dict(
        world_id=case.world, conversation_id=case.turn.conversation_id,
        prior_to=case.turn.sequence + 1, page_id=primary.object_id, page_kind=primary.kind,
    )
    with unit_of_work() as conn:
        assert approval_handoff(conn, **target_scope, accepted_at=original_approval_time) == {"status": "stale"}
        fresh = approval_handoff(conn, **target_scope, accepted_at=datetime.now(timezone.utc))
    assert fresh["status"] == "ready"
    assert str(fresh["review_id"]) == successor["review_id"]
    edited = case.client.put(draft_path, json={
        "expected_revision": 2, "markdown": new_draft["markdown"] + "\nUnreviewed edit.",
    })
    assert edited.status_code == 200, edited.text
    with unit_of_work() as conn:
        assert approval_handoff(conn, **target_scope, accepted_at=datetime.now(timezone.utc)) == {"status": "stale"}


def test_variant_exact_correction_rejects_overlapping_matches():
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.services.conversation_variant_save import (
        VariantTextReplacement, apply_variant_text_corrections,
    )

    definition = {"rule_elements": [{"key": "fixture", "rules_text": "aaa"}]}
    edit = VariantTextReplacement(rule_key="fixture", field="rules_text", replace_exact="aa", with_text="b")
    with pytest.raises(ApplicationStateConflictError, match="one exact rule passage"):
        apply_variant_text_corrections(definition, [edit])


def test_standalone_page_intent_preserves_the_page_owner_boundary(lane, tmp_path, monkeypatch):
    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, False, False, False,
        message="Create a standalone lore page about the Glass Regent.",
        requested_work="review_lore_page",
        source_need="anchored", lore_legacy_menu=True,
    )
    selection, = [
        event for event in case.turn.graph_context_execution.events
        if isinstance(event, t.BuildRequestedWorkResolutionV1)
    ]
    assert selection.requested_work == "review_lore_page"
    assert selection.resolution["barrier"] is None
    draft = case.turn.completion.collaboration
    assert draft.kind == "lore_page"
    assert draft.destination.title == "Glass Regent"
    assert not case.turn.completion.answer_segments



def test_anchored_lore_label_on_eager_graph_route_preserves_related_context(lane, tmp_path, monkeypatch):
    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, True, False, False,
        message="Create a page for Glass Regent.",
        requested_work="review_lore_page_from_conversation",
        source_need="anchored",
        read_optional_page=True, source_answer_output='lore_valid_gap',
    )
    assert case.turn.completion.collaboration.kind == "lore_page"
    from application_state.agent_conversation import build_related_pages

    execution = case.turn.graph_context_execution
    assert build_related_pages.project(execution) is not None
    assert not any(isinstance(event, t.BuildPriorBodyEvidenceAdmittedV1) for event in execution.events)


@pytest.mark.parametrize("carry,synthesis", [
    (None, "Create a page for Glass Regent."),
    ("anchored", "Create a page for Glass Regent."),
    ("uncertain", "Create a page for Glass Regent."),
    ("anchored", "Create the page about Glass Regent"),
    ("source_head_unavailable", "Create the page about Glass Regent"),
    ("authored_context", "Create the page about Glass Regent"),
])
def test_ordinary_populated_lore_draft_reopens_its_exact_passages(lane, tmp_path, monkeypatch, carry, synthesis):
    from application_state.agent_conversation.native_corpus import acquired_body_reads

    from evals.buddy_benchmark import workflow

    thread_id, template = str(uuid4()), {}

    def first(client, world, body):
        body["client_thread_id"] = thread_id
        template.update((key, value) for key, value in body.items() if key != "message")
        return client.post("/api/live/agent/turn", json=body)

    case = _fresh_case(
        lane, tmp_path, monkeypatch, None, False, False, False,
        message="Create a blank page for Glass Regent.",
        requested_work=lambda message: "review_lore_page_from_conversation" if message == synthesis else "review_blank_lore_page" if "blank page" in message else "review_lore_page",
        native_body="direct_support", dispatch=first,
        lore_limitation="authored_context" if carry == "authored_context" else True,
        source_need=lambda message: ("anchored" if carry in {"source_head_unavailable", "authored_context"} else carry) if message == synthesis else "source_lookup",
    )
    blank = case.turn
    assert not blank.completion.answer_segments
    response = workflow.capture_case(
        case.client, case.world, template,
        {"question": "Create a page for Glass Regent and populate it with what we know."},
        tmp_path / "lore-populate", build_thread_id=thread_id,
        expected_conversation_id=str(blank.conversation_id),
    )
    assert response.status_code == 200, response.text
    from application_state.agent_conversation.service import AgentConversationService
    history = case.client.get(f"/api/live/agent/worlds/{case.world}/conversation")
    assert history.status_code == 200, history.text
    row = max(history.json()["turns"], key=lambda turn: turn["sequence"])
    populated = AgentConversationService().inspect_turn(world_id=case.world, turn_id=UUID(row["turn_id"]))
    from application_state.agent_conversation.lore_page_confirmation import LorePageConfirmation
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    from application_state.content import pages

    producing = populated
    if carry:
        from application_state.agent_conversation.native_context import NativeBuildQueryPendingV1
        from application_state.agent_conversation.native_execution import NativeBuildQuerySettledV1

        from apps.live_control_server.services import native_graph_reads

        def unexpected_graph_preparation(*args, **kwargs):
            pytest.fail("Conversation-only draft started Graph preparation")

        with monkeypatch.context() as patch:
            if carry == "source_head_unavailable":
                from apps.live_control_server.services import plan_source_turn
                from application_state.agent_conversation.native_plan_statements import NativePlanQueryUnavailableV1

                patch.setattr(plan_source_turn, "prepare", lambda world, *args, **kwargs: (
                    None, t.NativeCorpusUnavailableV1(managed_world_id=world,
                        failure_code="native_source_head_unavailable")))
                # New Worlds have neither an admitted corpus head nor object Graph.
                patch.setattr(native_graph_reads, "prepare_query", lambda world, *args, **kwargs: (
                    None, NativePlanQueryUnavailableV1(managed_world_id=world,
                        reason="native_graph_binding_unavailable")))
            else:
                patch.setattr(native_graph_reads, "prepare_query", unexpected_graph_preparation)
            response = workflow.capture_case(
                case.client, case.world, template, {"question": synthesis},
                tmp_path / "lore-synthesis", build_thread_id=thread_id,
                expected_conversation_id=str(blank.conversation_id),
            )
        assert response.status_code == 200, response.text
        history = case.client.get(f"/api/live/agent/worlds/{case.world}/conversation")
        row = max(history.json()["turns"], key=lambda turn: turn["sequence"])
        populated = AgentConversationService().inspect_turn(world_id=case.world, turn_id=UUID(row["turn_id"]))
        if carry == "source_head_unavailable":
            assert populated.graph_context_receipt.source_authority.failure_code == "native_source_head_unavailable"
        else:
            assert isinstance(populated.graph_context_receipt.native_query, NativeBuildQueryPendingV1)
        assert not any(isinstance(e, NativeBuildQuerySettledV1) for e in populated.graph_context_execution.events)
        from application_state.agent_conversation.writer_evidence_selection import native_conversation_terminal
        assert native_conversation_terminal(populated)["reason"] == (
            "native_lore_page_from_conversation_with_open_questions" if carry == "uncertain"
            else "native_lore_page_from_conversation"
        )
        assert not acquired_body_reads(populated.graph_context_execution)
        assert all(c.prior_reference is None and c.read_event_id in {
            read.event_id for origin in (blank, producing)
            for read in acquired_body_reads(origin.graph_context_execution)
        } for c in populated.completion.native_body_citations)
        for number in range(6 if carry == "anchored" else 0):
            response = workflow.capture_case(
                case.client, case.world, template, {"question": synthesis},
                tmp_path / f"lore-revision-{number}", build_thread_id=thread_id,
                expected_conversation_id=str(blank.conversation_id),
            )
            assert response.status_code == 200, response.text
        history = case.client.get(f"/api/live/agent/worlds/{case.world}/conversation")
        row = max(history.json()["turns"], key=lambda turn: turn["sequence"])
        populated = AgentConversationService().inspect_turn(world_id=case.world, turn_id=UUID(row["turn_id"]))
        if carry == "anchored":
            assert producing.turn_id not in {
                pin.turn_id for pin in populated.graph_context_receipt.assembled_input.included_history
            }
        assert populated.completion.native_body_citations
        assert all(c.prior_reference is None and c.read_event_id in {
            read.event_id for origin in (blank, producing)
            for read in acquired_body_reads(origin.graph_context_execution)
        } for c in populated.completion.native_body_citations)

    completion = populated.completion
    assert completion.collaboration.destination.title == "Glass Regent"
    from application_state.agent_conversation import library, repository
    with monkeypatch.context() as patch:
        patch.setattr(repository, "_turn_from_row", lambda *args, **kwargs: pytest.fail("Compact lore review decoded execution"))
        compact = library.read_active_messages(case.world)
    descriptor = compact["messages"][-1]["reply_object"]
    assert descriptor == {"kind": "page_object", "object_kind": "lore_page", "source": {
        "world_id": case.world, "conversation_id": str(populated.conversation_id),
        "turn_id": str(populated.turn_id), "document_id": populated.provenance.primary_work.object_id,
        "surface_id": "build"}}
    followup = workflow.capture_case(
        case.client, case.world, template,
        {"question": "Create the page"},
        tmp_path / "lore-create", build_thread_id=thread_id,
        expected_conversation_id=str(populated.conversation_id),
    )
    assert followup.status_code == 200, followup.text
    reference = followup.json()["lore_save_review"]
    assert reference == {
        "schema": "dmb_lore_save_review_reference_v1",
        "conversation_id": str(populated.conversation_id),
        "turn_id": str(populated.turn_id),
        "review_sha256": canonical_sha256(completion),
        "title": "Glass Regent",
    }
    assert followup.json()["answer"]["trace"]["model_calls"] == []
    followup_history = case.client.get(
        f"/api/live/agent/worlds/{case.world}/conversation", params={"include_turn_correlation": "true"},
    ).json()
    assert followup_history["turns"][-1]["lore_save_review"] == reference
    import json
    sent = json.loads((tmp_path / "lore-create" / "request.json").read_text())
    repeated = case.client.post("/api/live/agent/turn", json=sent)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["lore_save_review"] == reference
    assert repeated.json()["answer"]["trace"]["model_calls"] == []
    request = LorePageConfirmation(conversation_id=populated.conversation_id,
        turn_id=populated.turn_id, review_sha256=canonical_sha256(completion))
    url = f"/api/live/agent/worlds/{case.world}/conversation/lore-pages/confirm"
    body = request.model_dump(mode="json")
    before = len(pages.list_pages(world_id=case.world))
    stale = case.client.post(url, json={**body, "turn_id": str(blank.turn_id),
        "review_sha256": canonical_sha256(blank.completion)})
    assert stale.status_code == 409 and "superseded" in stale.text, stale.text
    unseen = case.client.post(url, json={**body, "turn_id": str(uuid4())})
    assert unseen.status_code == 404, unseen.text
    rejected = case.client.post(url, json={**body, "review_sha256": "0" * 64})
    assert rejected.status_code == 409, rejected.text
    assert len(pages.list_pages(world_id=case.world)) == before
    unopened = case.client.post(url, json=body)
    assert unopened.status_code == 409 and "Open the exact" in unopened.text, unopened.text
    assert len(pages.list_pages(world_id=case.world)) == before
    shown = case.client.post(url.removesuffix("/confirm") + "/review", json=body)
    assert shown.status_code == 200 and shown.json() == {"review_sha256": body["review_sha256"]}, shown.text
    assert len(pages.list_pages(world_id=case.world)) == before
    created = case.client.post(url, json=body)
    assert created.status_code == 200, created.text
    receipt = created.json()
    replay = case.client.post(url, json=body)
    assert replay.status_code == 200 and replay.json() == receipt, replay.text
    assert len(pages.list_pages(world_id=case.world)) == before + 1
    reopened = pages.committed_page(receipt["document_id"], world_id=case.world)
    assert reopened.page.title == "Glass Regent"
    assert str(reopened.revision.work_revision_id) == receipt["revision_id"]
    assert completion.answer_segments[0].text in reopened.revision.markdown
    if carry:
        assert completion.collaboration.open_questions == ("Why did the Regent leave?",)
        assert "## Open questions\n\n- Why did the Regent leave?" in reopened.revision.markdown
    assert f"/conversation/turns/{populated.turn_id}/native-body-excerpts/0" in reopened.revision.markdown
    expected_kinds = {"source_passage_claim", "limitation"}
    if carry == "authored_context":
        expected_kinds.add("proposal")
        proposals = [segment for segment in completion.answer_segments if segment.kind == "proposal"]
        assert len(proposals) == 2
        assert all(segment.label == "invented_idea" for segment in proposals)
        assert "Authored note context, not a played event" in reopened.revision.markdown
        assert "three bridges" in reopened.revision.markdown
        assert "Proposed direction" in reopened.revision.markdown
        assert "truthful memory" in reopened.revision.markdown
        assert all(segment.text in reopened.revision.markdown for segment in proposals)
    assert {segment.kind for segment in completion.answer_segments} == expected_kinds
    assert all(segment.text not in reopened.revision.markdown for segment in completion.answer_segments
               if segment.kind == "limitation")
    reads = {
        read.event_id: read.excerpt.text for origin in (blank, producing)
        for read in acquired_body_reads(origin.graph_context_execution)
    }
    assert completion.native_body_citations
    import re
    links = re.findall(r"\[Source \d+\]\((/api/live/agent/[^)]+)\)", reopened.revision.markdown)
    assert len(links) == len(completion.native_body_citations)
    for link, citation in zip(links, completion.native_body_citations, strict=True):
        opened = case.client.get(link)
        assert opened.status_code == 200, opened.text
        assert opened.json()["content"] == reads[citation.read_event_id]


@pytest.mark.parametrize("component,value", [
    ("managed_world_id", "foreign-managed"),
    ("native_world_id", "foreign-native"),
    ("binding_version", 999),
    ("revision_id", "rev:unadmitted"),
])
def test_followup_rejects_inadmissible_fresh_pdf_support(lane, tmp_path, monkeypatch, component, value):
    from evals.buddy_benchmark import workflow
    from apps.live_control_server.services import native_graph_inspection

    template = {}
    thread = str(uuid4())

    def first(client, world, body):
        template.update((key, value) for key, value in body.items() if key != "message")
        return workflow.capture_case(client, world, template, {"question": body["message"]},
            tmp_path / "initial", build_thread_id=thread)

    case = _fresh_case(lane, tmp_path, monkeypatch, None, False, False, False,
        message="Let's brainstorm a variant of this creature.", requested_work="discuss",
        saved_statblock="associated", dispatch=first)
    original = native_graph_inspection.statblock_pdf_support
    calls = []

    def invalid(reference, *args, **kwargs):
        calls.append(reference)
        support = original(reference, *args, **kwargs)
        return support | {"scope": support["scope"] | {component: value}}

    monkeypatch.setattr(native_graph_inspection, "statblock_pdf_support", invalid)
    head = lane.repo.get_head(case.world)
    response = workflow.capture_case(case.client, case.world, template,
        {"question": "Could it negotiate?"}, tmp_path / "followup", build_thread_id=thread,
        expected_conversation_id=str(case.turn.conversation_id))
    assert response.status_code == 503, response.text
    assert calls
    assert lane.repo.get_head(case.world) == head


@pytest.mark.parametrize("drift", ["source_epoch", "graph_binding"])
def test_deferred_build_rejects_drift_after_graph_preparation(lane, tmp_path, monkeypatch, drift):
    from dataclasses import replace
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter

    settle = _PolicyExecutionAdapter.settle_deferred_build_query
    refresh = native_corpus_source._refresh_native_context

    def drifted(adapter, context, query):
        with monkeypatch.context() as patch:
            if drift == "source_epoch":
                def refreshed(*args, **kwargs):
                    fresh = refresh(*args, **kwargs)
                    changed = fresh.authority.model_copy(
                        update={"acquisition_epoch": fresh.authority.acquisition_epoch + 1},
                    )
                    return replace(fresh, authority=changed)

                patch.setattr(native_corpus_source, "_refresh_native_context", refreshed)
            else:
                context = replace(context, resolve_binding=lambda _world: None)
            return settle(adapter, context, query)

    monkeypatch.setattr(_PolicyExecutionAdapter, "settle_deferred_build_query", drifted)
    _fresh_case(lane, tmp_path, monkeypatch, "deferred_settlement_drift",
                False, False, False, saved_statblock="by-name")


def test_deferred_build_recovers_same_id_after_accept_before_claim(lane, tmp_path, monkeypatch):
    from application_state.agent_conversation.native_context import NativeBuildQueryPendingV1
    from application_state.agent_conversation.native_execution import NativeBuildQuerySettledV1

    def send(client, _world, body):
        def interrupted(*_args, **_kwargs):
            raise RuntimeError("interrupted after durable acceptance")

        with monkeypatch.context() as patch:
            patch.setattr(AgentConversationService, "claim_turn", interrupted)
            first = client.post("/api/live/agent/turn", json=body)
        assert first.status_code == 503, first.text
        return client.post("/api/live/agent/turn", json=body)

    case = _fresh_case(lane, tmp_path, monkeypatch, None, False, False, False,
                       saved_statblock="by-name", dispatch=send, message="Find the statblock for the Meat Mind.")
    assert isinstance(case.turn.graph_context_receipt.native_query, NativeBuildQueryPendingV1)
    events = case.turn.graph_context_execution.events
    assert sum(isinstance(event, NativeBuildQuerySettledV1) for event in events) == 1
    assert sum(isinstance(event, t.ProviderAttemptAuthorizedEventV5)
               and event.context_phase == "select" for event in events) == 1


def test_deferred_build_opening_prompt_failure_rolls_back_authorization(lane, tmp_path, monkeypatch):
    from application_state.agent_conversation import context_trace_store
    from application_state.agent_conversation.context_trace import TracePromptReference

    save_trace = context_trace_store._save_trace
    attempted = []

    def fail_after_save(conn, trace):
        save_trace(conn, trace)
        if not attempted and any(isinstance(item, TracePromptReference) for item in trace.observations):
            attempted.append(trace)
            raise RuntimeError("interrupted after writing the opening prompt trace")

    monkeypatch.setattr(context_trace_store, "_save_trace", fail_after_save)
    _fresh_case(lane, tmp_path, monkeypatch, "initial_context",
                False, False, False, saved_statblock="by-name")
    (failed_trace,) = attempted
    app = AgentConversationService()
    turn = app.inspect_turn(world_id=failed_trace.world_id, turn_id=failed_trace.turn_id)
    assert not any(isinstance(item, t.ProviderAttemptAuthorizedEventV5)
                   for item in turn.graph_context_execution.events)
    traces = app.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)
    assert traces
    assert not any(isinstance(item, TracePromptReference)
                   for trace in traces for item in trace.observations)


def test_deferred_build_provider_failure_never_starts_unselected_graph(lane, tmp_path, monkeypatch):
    from threading import Event
    from apps.live_control_server.services import native_graph_reads

    started, release, finished = Event(), Event(), Event()

    def blocked(*_args, **_kwargs):
        started.set()
        try:
            assert release.wait(timeout=15)
            raise RuntimeError("unused speculative Graph read")
        finally:
            finished.set()

    def fail_at_transport(_adapter, provider):
        assert provider == "typesafe" and not started.is_set()
        raise RuntimeError("opening transport failed")

    monkeypatch.setattr(native_graph_reads, "prepare_query", blocked)
    try:
        _fresh_case(lane, tmp_path, monkeypatch, "deferred_provider_failure",
                    False, False, False, saved_statblock="by-name", before_provider=fail_at_transport)
        assert not started.is_set() and not finished.is_set()
    finally:
        release.set()
        if started.is_set():
            assert finished.wait(timeout=5)


def test_deferred_build_display_keeps_admission_and_exact_native_citations(lane, tmp_path, monkeypatch):
    from apps.live_control_server.services.agent_turn_service import project_plan_turn_context

    case = _fresh_case(lane, tmp_path, monkeypatch, "deferred_graph_citation",
                       False, False, False, message="Describe A and B.")
    for replay in (False, True):
        context = project_plan_turn_context(case.turn, delivery_replay=replay).model_dump(mode="json", by_alias=True)
        receipt = context["receipt"]
        assert receipt == case.turn.graph_context_receipt.model_dump(mode="json", by_alias=True)
        assert receipt["native_query"]["schema"] == "dmb_native_build_query_pending_v1"
        membership = context["deferred_build_citations"]
        assert membership["context_receipt_sha256"] == receipt["context_receipt_sha256"]
        assert membership["producing_provider_attempt_id"] == context["completion"]["producing_provider_attempt_id"]
        assert membership["assertions"] == sorted([list(item) for item in {
            (cite.assertion_id, cite.assertion_sha256) for cite in case.turn.completion.native_assertion_citations
        }])
        assert membership["assertions"]


@pytest.mark.parametrize('output', ['typed', 'uncited', 'empty', 'gap', 'typed_gap_format', 'gap_format'])
def test_source_lookup_discussion_requires_bound_claims_without_forcing_a_fact(lane, tmp_path, monkeypatch, output):
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='discuss', source_need='source_lookup', read_optional_page=True,
        source_answer_output=output, message='What does the saved lore establish about the local node’s alliance?' if output in {'gap', 'typed_gap_format', 'gap_format'}
        else 'What does the saved lore propose about the local node?')
    request = json.loads(case.writer.calls[0].content)
    assert request['text']['format']['name'] == 'build_reply'
    assert len(case.writer.calls) == 1
    if output in {'uncited', 'empty'}:
        assert case.response.status_code == 503
        assert case.turn.completion is None
        return
    assert case.response.status_code == 200, case.response.text
    if output in {'gap', 'gap_format'}:
        assert all(row.kind == 'limitation' and row.question_phrase is None for row in case.turn.completion.answer_segments)
        assert not any(x.kind == 'related_page_claim' for x in case.turn.completion.answer_segments)
        return
    claim, = [x for x in case.turn.completion.answer_segments if x.kind == 'related_page_claim']
    if output == 'typed_gap_format':
        limitations = [x for x in case.turn.completion.answer_segments if x.kind != 'related_page_claim']
        assert limitations and all(x.question_phrase is None for x in limitations)
    assert claim.kind == 'related_page_claim'
    opened = case.client.get(f'/api/live/agent/worlds/{case.world}/conversation/turns/{case.turn.turn_id}/related-pages/{claim.read_id}')
    assert opened.status_code == 200
    assert opened.json()['markdown'] == 'The local node is proposed to want freedom.'


def test_anchored_creative_discussion_keeps_its_no_acquisition_grammar(lane, tmp_path, monkeypatch):
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='discuss', source_need='anchored', read_optional_page=True,
        source_answer_output='creative', message='Let us explore this proposed direction; do not search.')
    assert case.response.status_code == 200, case.response.text
    assert not any(e.kind == 'build_related_page_read_v1' for e in case.turn.graph_context_execution.events)
    assert all(e.kind == 'discussion' for e in case.turn.completion.answer_segments)
    assert json.loads(case.writer.calls[0].content)['text']['format']['name'] != 'surface_native_build_source_answer_v1'


@pytest.mark.parametrize('scope,output', [('source_lookup', 'typed'), ('anchored', 'creative')])
def test_current_ordinary_build_sdk_has_semantic_input_and_reopens(lane, tmp_path, monkeypatch, scope, output):
    message = 'Discuss the local node. Preserve citation_policy as a fictional motto.'
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='discuss', source_need=scope, read_optional_page=True,
        source_answer_output=output, message=message)
    assert case.response.status_code == 200, case.response.text
    assert len(case.writer.calls) == 1
    request = json.loads(case.writer.calls[0].content)
    assert request['text']['format']['name'] == 'build_reply'
    schema = request['text']['format']['schema']
    assert 'schema' not in schema['properties']
    frames = [json.loads(row['content']) for row in request['input']]
    work, = [frame['build_work'] for frame in frames if 'build_work' in frame]
    assert not {'citation_policy', 'source_answer_policy', 'lore_limitation_policy'} & set(work)
    evidence, = [frame for frame in frames if 'user_question' in frame]
    assert evidence['user_question'] == message
    visible = request['instructions'] + json.dumps(request['input']) + json.dumps(schema)
    for sentinel in ('dmb_surface_evidence_answer_v8', 'supplied_source_references_v1',
                     'typed_supplied_source_answer_v1', 'validated_lore_review_generic_gaps_v1',
                     str(case.turn.turn_id), str(case.turn.conversation_id), case.world):
        assert sentinel not in visible
    assert 'schema' not in json.loads(case.writer.actual_output)
    reopened = AgentConversationService().inspect_turn(world_id=case.world, turn_id=case.turn.turn_id)
    assert reopened.completion == case.turn.completion
    assert reopened.assistant_text == case.turn.assistant_text
    assert len(case.writer.calls) == 1


@pytest.mark.parametrize('output', ['host_schema_echo', 'foreign_source_alias', 'regenerated_quote'])
def test_semantic_build_reply_rejects_host_echo_and_unbound_citation(lane, tmp_path, monkeypatch, output):
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='discuss', source_need='source_lookup', read_optional_page=True,
        source_answer_output=output)
    assert case.response.status_code == 503
    assert len(case.writer.calls) == 1
    assert case.turn.completion is None


def test_fresh_factual_build_refuses_old_discussion_contract_before_writer_io(lane, tmp_path, monkeypatch):
    from application_state.agent_conversation import native_build_work_view
    original = native_build_work_view.semantic_frame
    def old_contract(host, execution, **kwargs):
        return original(host, execution, **(kwargs | {'typed_source_answer': False}))
    monkeypatch.setattr(native_build_work_view, 'semantic_frame', old_contract)
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='discuss', source_need='source_lookup', read_optional_page=True,
        source_answer_output='typed')
    assert case.response.status_code == 503
    assert not case.writer.calls
    assert case.turn.completion is None


@pytest.mark.parametrize('mutation', ['unknown_policy', 'reintroduced_policy', 'old_format', 'ineligible_context'])
def test_factual_build_recomputed_sdk_packet_cannot_forge_source_answer_policy(lane, tmp_path, monkeypatch, mutation):
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    original = PlanJevWriter.__init__
    def forge(self, *args, **kwargs):
        original(self, *args, **kwargs)
        if mutation == 'old_format':
            self.output_format = self.output_format | {'name': 'surface_native_evidence_selectors_v2'}
            return
        for message in self.messages:
            frame = json.loads(message['content'])
            if 'build_work' not in frame:
                continue
            if mutation == 'unknown_policy':
                frame['build_work']['source_answer_policy'] = 'foreign_source_policy'
            elif mutation == 'reintroduced_policy':
                frame['build_work']['citation_policy'] = 'supplied_source_references_v1'
            else:
                frame['build_work']['source_answer_policy'] = 'typed_supplied_source_answer_v1'
            message['content'] = json.dumps(frame)
            break
        else:
            raise AssertionError('Test requires the actual Build work carrier')
    monkeypatch.setattr(PlanJevWriter, '__init__', forge)
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='discuss', source_need='anchored' if mutation == 'ineligible_context' else 'source_lookup',
        read_optional_page=True, source_answer_output='creative' if mutation == 'ineligible_context' else 'typed')
    assert case.response.status_code == 503
    assert not case.writer.calls
    assert case.turn.completion is None


@pytest.mark.parametrize('work', ['review_lore_page', 'review_lore_page_from_conversation'])
@pytest.mark.parametrize('output', ['lore_stale_gap', 'lore_valid_gap', 'lore_malformed_gap', 'lore_empty_gap', 'lore_invalid_destination', 'lore_null_gap'])
def test_lore_page_review_uses_generic_limits_without_optional_phrase(lane, tmp_path, monkeypatch, output, work):
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work=work, source_need='anchored',
        source_answer_output=output,
        message='Create a page for Glass Regent. Use the context we discussed; keep the unresolved motive open; do not search again.')
    request = json.loads(case.writer.calls[0].content)
    assert request['text']['format']['name'] == 'lore_page_response'
    from application_state.agent_conversation.retained_conversation import current_request_message
    current = current_request_message(case.turn.graph_context_execution)
    if current is None:
        assert json.loads(request['input'][-1]['content'])['user_question'] == case.turn.user_text
    else:
        assert request['input'][-1] == current
    assert ('The latest author request determines whether to prepare a page now.'
        in request['instructions']) == (work == 'review_lore_page_from_conversation')
    if output in {'lore_malformed_gap', 'lore_invalid_destination', 'lore_empty_gap', 'lore_null_gap'}:
        assert case.response.status_code == 503
        assert case.turn.completion is None
        return
    assert case.response.status_code == 200, case.response.text
    completion = case.turn.completion
    limits = [x for x in completion.answer_segments if x.kind == 'limitation']
    assert limits and all(x.question_phrase is None for x in limits)
    if output in {'lore_empty_gap', 'lore_null_gap'}:
        assert completion.collaboration is None
        if output == 'lore_empty_gap':
            assert all(x.kind == 'limitation' for x in completion.answer_segments)
        else:
            assert any(x.kind == 'proposal' for x in completion.answer_segments)
        return
    assert completion.collaboration.kind == 'lore_page'
    assert completion.collaboration.destination.title == 'Glass Regent'
    assert any(x.kind == 'proposal' and 'seeks freedom' in x.text for x in completion.answer_segments)
    limits = [x for x in completion.answer_segments if x.kind == 'limitation']
    assert limits
    assert all(x.question_phrase is None for x in limits)
    assert not any(e.kind == 'build_related_page_read_v1' for e in case.turn.graph_context_execution.events)


def test_fresh_lore_review_refuses_retired_limitation_policy_before_writer_io(lane, tmp_path, monkeypatch):
    from application_state.agent_conversation import native_build_work_view
    original = native_build_work_view.semantic_frame
    def old_contract(host, execution, **kwargs):
        return original(host, execution, **(kwargs | {'lore_page_limitations': False}))
    monkeypatch.setattr(native_build_work_view, 'semantic_frame', old_contract)
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='review_lore_page', source_need='anchored', source_answer_output='lore_stale_gap',
        message='Create a page for Glass Regent.')
    assert case.response.status_code == 503
    assert not case.writer.calls
    assert case.turn.completion is None


@pytest.mark.parametrize('mutation', ['unknown_policy', 'omitted_policy', 'old_format', 'ineligible_work', 'ineligible_context'])
def test_lore_review_recomputed_packet_cannot_forge_limitation_policy(lane, tmp_path, monkeypatch, mutation):
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    original = PlanJevWriter.__init__
    def forge(self, *args, **kwargs):
        original(self, *args, **kwargs)
        if mutation == 'old_format':
            self.output_format = self.output_format | {'name': 'surface_native_evidence_selectors_v2'}
            return
        for message in self.messages:
            frame = json.loads(message['content'])
            if 'build_work' not in frame:
                continue
            if mutation == 'unknown_policy':
                frame['build_work']['lore_limitation_policy'] = 'foreign_policy'
            elif mutation == 'omitted_policy':
                frame['build_work'].pop('lore_limitation_policy')
            else:
                frame['build_work']['lore_limitation_policy'] = 'validated_lore_review_generic_gaps_v1'
            message['content'] = json.dumps(frame)
            break
        else:
            raise AssertionError('Test requires actual semantic Build work')
    monkeypatch.setattr(PlanJevWriter, '__init__', forge)
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='discuss' if mutation.startswith('ineligible_') else 'review_lore_page',
        source_need='anchored', lore_legacy_menu=True, source_answer_output='creative' if mutation.startswith('ineligible_') else 'lore_stale_gap',
        message='Let us explore this premise without searching.' if mutation == 'ineligible_work' else 'Create a page for Glass Regent.')
    assert case.response.status_code == 503
    assert not case.writer.calls
    assert case.turn.completion is None


def test_fresh_build_refuses_whole_pre_generic_reply_contract_before_writer_io(lane, tmp_path, monkeypatch):
    from application_state.agent_conversation import plan_writer_output_schema
    original = plan_writer_output_schema.native_output_format
    def historical(*args, **kwargs):
        return original(*args, **(kwargs | {'generic_reply_limits': False}))
    monkeypatch.setattr(plan_writer_output_schema, 'native_output_format', historical)
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='discuss', source_need='anchored', source_answer_output='creative',
        message='Let us discuss this premise without searching.')
    assert case.response.status_code == 503
    assert not case.writer.calls
    assert case.turn.completion is None


@pytest.mark.parametrize('output', ['unknown_limit_code', 'retired_gap_field'])
def test_current_build_limits_reject_unknown_codes_and_retired_echo_fields(lane, tmp_path, monkeypatch, output):
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='discuss', source_need='anchored', source_answer_output=output,
        message='Discuss the supplied premise without another search.')
    assert case.response.status_code == 503
    assert len(case.writer.calls) == 1
    assert case.turn.completion is None


@pytest.mark.parametrize('mutation', ['unknown_format', 'malformed_schema', 'raw_carrier', 'retired_schema'])
def test_current_build_generic_policy_cannot_be_forged_in_recomputed_sdk_packet(lane, tmp_path, monkeypatch, mutation):
    from copy import deepcopy
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from application_state.agent_conversation.native_writer import model_frame
    original = PlanJevWriter.__init__
    def forge(self, *args, **kwargs):
        original(self, *args, **kwargs)
        if mutation == 'unknown_format':
            self.output_format = self.output_format | {'name': 'foreign_reply_schema'}
            return
        if mutation == 'malformed_schema':
            self.output_format = deepcopy(self.output_format)
            base = self.output_format['schema'].get('$defs', {}).get('Base', self.output_format['schema'])
            base['required'].append('requested_detail_gaps')
            return
        if mutation == 'retired_schema':
            self.output_format = deepcopy(self.output_format)
            base = self.output_format['schema'].get('$defs', {}).get('Base', self.output_format['schema'])
            base['properties']['requested_detail_gaps'] = {'type': 'array', 'items': {'type': 'object',
                'properties': {'question_phrase': {'type': 'string'}}, 'required': ['question_phrase'], 'additionalProperties': False}}
            base['required'].append('requested_detail_gaps')
            return
        for message in self.messages:
            frame = json.loads(message['content'])
            if 'native_body_evidence' not in frame:
                continue
            frame = model_frame(self.adapter.turn.graph_context_receipt, self.adapter.turn.graph_context_execution)
            self.provider_frame = frame
            message['content'] = json.dumps(frame)
            break
        else:
            raise AssertionError('Test requires the actual native reply evidence carrier')
    monkeypatch.setattr(PlanJevWriter, '__init__', forge)
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='discuss', source_need='anchored', source_answer_output='creative',
        message='Discuss this premise without searching.')
    assert case.response.status_code == 503
    assert not case.writer.calls
    assert case.turn.completion is None


@pytest.mark.parametrize('scope, message', [
    ('source_lookup', 'Get familiar with Glass Regent and the world beyond this short draft.'),
    ('anchored', 'Summarize the proposed local node context already supplied; do not search again.'),
    ('anchored', 'Hello Buddy, are you ready to help?'),
])
def test_background_scope_guidance_reaches_actual_sdk_and_respects_the_offered_choice(
        lane, tmp_path, monkeypatch, scope, message):
    from application_state.agent_conversation.build_intentional_response import SOURCE_NEED_GUIDANCE
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='discuss', source_need=scope, read_optional_page=True,
        source_answer_output='typed' if scope == 'source_lookup' else 'creative', message=message)
    assert case.response.status_code == 200, case.response.text
    opening = next(json.loads(call.content) for call in case.decisions.calls
        if 'source_need' in json.loads(call.content)['questions'])
    assert opening['questions']['source_need']['instructions'] == SOURCE_NEED_GUIDANCE
    assert opening['state']['user_question'] == message
    reads = [event for event in case.turn.graph_context_execution.events if event.kind == 'build_related_page_read_v1']
    claims = [row for row in case.turn.completion.answer_segments if row.kind == 'related_page_claim']
    if scope == 'source_lookup':
        assert reads and claims
        opened = case.client.get(f'/api/live/agent/worlds/{case.world}/conversation/turns/{case.turn.turn_id}/related-pages/{claims[0].read_id}')
        assert opened.status_code == 200
        assert opened.json()['markdown'] == 'The local node is proposed to want freedom.'
    else:
        assert not reads and not claims
        assert all(row.kind == 'discussion' for row in case.turn.completion.answer_segments)


@pytest.mark.parametrize('mutation', ['prior_request', 'hybrid', 'legacy_destination', 'legacy_format', 'legacy_outcome', 'outcome_old_menu', 'extra_policy'])
def test_lore_request_reference_rejects_downgrades_before_writer_io(lane, tmp_path, monkeypatch, mutation):
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from application_state.agent_conversation.native_build_work_view import semantic_frame
    from application_state.agent_conversation.plan_writer_output_schema import native_output_format
    original = PlanJevWriter.__init__
    prepared = []
    def forge(self, *args, **kwargs):
        original(self, *args, **kwargs)
        if mutation in {'legacy_outcome', 'outcome_old_menu'}:
            wire = semantic_frame(self.work_frame, self.adapter.turn.graph_context_execution,
                bind_lore_page=True, supplied_source_references=True, typed_source_answer=True,
                lore_page_limitations=True, lore_request_reference=True)
            self.provider_work = wire
            from application_state.agent_conversation.rules_authority_plan_packet import model_rules_frame
            self.output_format = native_output_format(self.frame, model_rules_frame(self.rules.frame()),
                self.work_frame | wire, build_local=True, generic_reply_limits=True, lore_outcome=mutation == 'outcome_old_menu')
        if mutation == 'legacy_format':
            old = semantic_frame(self.work_frame, self.adapter.turn.graph_context_execution,
                bind_lore_page=True, supplied_source_references=True, typed_source_answer=True,
                lore_page_limitations=True)
            self.provider_work = old
            from application_state.agent_conversation.rules_authority_plan_packet import model_rules_frame
            self.output_format = native_output_format(self.frame, model_rules_frame(self.rules.frame()),
                self.work_frame | old, build_local=True, generic_reply_limits=True)
        for message in self.messages:
            frame = json.loads(message['content'])
            if 'build_work' not in frame:
                continue
            destination = frame['build_work']['lore_page_destination']
            if mutation in {'legacy_outcome', 'outcome_old_menu'}:
                frame['build_work'] = self.provider_work['build_work']
                message['content'] = json.dumps(frame)
                prepared.append(True)
                break
            if mutation == 'prior_request':
                destination['request'] = 'prior_author_request'
            elif mutation == 'hybrid':
                destination['instruction'] = 'Create a page for Glass Regent.'
            elif mutation == 'extra_policy':
                frame['build_work']['citation_policy'] = 'supplied_source_references_v1'
            elif mutation == 'legacy_destination':
                frame['build_work']['lore_page_destination'] = {'instruction': 'Create a page for Glass Regent.', 'title': 'Glass Regent'}
            else:
                frame['build_work'] = old['build_work']
            message['content'] = json.dumps(frame)
            prepared.append(True)
            break
    monkeypatch.setattr(PlanJevWriter, '__init__', forge)
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='review_lore_page_from_conversation', source_need='anchored', lore_legacy_menu=mutation == 'outcome_old_menu',
        source_answer_output='lore_stale_gap', message='Create a page for Glass Regent.')
    assert prepared == [True]
    assert case.response.status_code == 503
    assert not case.writer.calls
    assert case.turn.completion is None


@pytest.mark.parametrize('title', ['The Memory Ferry', 'Échos — The Ferry?'])
@pytest.mark.parametrize('repeat', [False, True])
def test_actual_separate_page_request_survives_sdk_and_retained_readback(lane, tmp_path, monkeypatch, title, repeat):
    message = f"Create a separate new lore page titled {title} from the full context we just discussed. Reuse our conversation only; do not search or re-fetch sources. Preserve the early details, later correction, authored-proposal status, open questions, and all constraints. Leave this workpad unchanged."
    if repeat:
        message = message + "\n" + message
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='review_lore_page_from_conversation', source_need='anchored',
        source_answer_output='lore_valid_gap', message=message, lore_title=title)
    assert case.response.status_code == 200, case.response.text
    assert case.turn.completion.collaboration.destination.model_dump() == {'request': 'current_author_request', 'title': title}
    history = case.client.get(f'/api/live/agent/worlds/{case.world}/conversation')
    assert history.status_code == 200
    assert history.json()['turns'][-1]['knowledge_context']['completion']['collaboration']['destination']['title'] == title
    assert not any(e.kind in {'build_related_page_read_v1', 'native_body_search_v1', 'native_body_read_v1'} for e in case.turn.graph_context_execution.events)


@pytest.mark.parametrize('output', ['blank_body', 'blank_questions'])
def test_admitted_blank_page_refuses_populated_writer_reply(lane, tmp_path, monkeypatch, output):
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='review_blank_lore_page', source_need='anchored', source_answer_output=output,
        message='Create a blank page for Glass Regent.')
    assert case.response.status_code == 503
    assert case.turn.completion is None


@pytest.mark.parametrize('output', ['lore_ack', 'lore_clarify', 'lore_uncited_body'])
def test_lore_reference_allows_ordinary_ack_only_outside_a_page_draft(lane, tmp_path, monkeypatch, output):
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='review_lore_page_from_conversation', source_need='anchored', source_answer_output=output,
        message='The deliverable must be a separate new lore page. Keep this neutral workpad completely unchanged. Acknowledge briefly only; do not search or create anything yet.', lore_legacy_menu=True)
    assert len(case.writer.calls)==1
    offered=json.loads(case.writer.calls[0].content)['text']['format']
    assert offered['name']=='surface_native_lore_request_reference_v2'
    base=offered['schema'].get('$defs',{}).get('Base',offered['schema'])
    assert any(v['properties']['kind'].get('const')=='discussion'
        for v in base['properties']['answer_segments']['items']['anyOf'])
    if output=='lore_uncited_body':
        assert case.response.status_code==503
        assert case.turn.completion is None
    else:
        assert case.response.status_code==200,case.response.text
        assert case.turn.completion.collaboration is None
        segment,=case.turn.completion.answer_segments
        assert segment.kind=='discussion'
        assert ('Which subject and premise' if output == 'lore_clarify' else 'Understood') in segment.text
        request = json.loads(case.writer.calls[0].content)
        from application_state.agent_conversation.retained_conversation import current_request_message
        current = current_request_message(case.turn.graph_context_execution)
        if current is None:
            assert json.loads(request['input'][-1]['content'])['user_question'] == case.turn.user_text
        else:
            assert request['input'][-1] == current
        assert 'do not treat a current acknowledgment-only request as permission to draft' in request['instructions']



def test_blank_lore_warning_stays_outside_the_empty_confirmed_page(lane, tmp_path, monkeypatch):
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    from application_state.content import pages
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='review_blank_lore_page', source_need='anchored', source_answer_output='blank_warning',
        message='Create a blank page for Glass Regent.')
    assert case.response.status_code==200,case.response.text
    completion=case.turn.completion
    assert completion.collaboration.kind=='lore_page'
    assert completion.answer_segments and all(segment.kind=='limitation' for segment in completion.answer_segments)
    request={'conversation_id':str(case.turn.conversation_id),'turn_id':str(case.turn.turn_id),
             'review_sha256':canonical_sha256(completion)}
    route=f'/api/live/agent/worlds/{case.world}/conversation/lore-pages'
    reviewed=case.client.post(route+'/review',json=request)
    assert reviewed.status_code==200,reviewed.text
    saved=case.client.post(route+'/confirm',json=request)
    assert saved.status_code==200,saved.text
    receipt=saved.json()
    assert pages.committed_page(receipt['document_id'],world_id=case.world).revision.markdown==''
    repeated=case.client.post(route+'/confirm',json=request)
    assert repeated.status_code==200 and repeated.json()==receipt


@pytest.mark.parametrize('output', ['lore_context_question', 'lore_context_mixed', 'lore_empty_gap', 'lore_extra_schema'])
def test_current_lore_outcome_question_is_visible_without_creating_a_page(lane, tmp_path, monkeypatch, output):
    from application_state.content import pages
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='review_lore_page_from_conversation', source_need='anchored',
        source_answer_output=output, message='Prepare the separate page when its subject and premise are clear. Ask for essential missing context; do not invent it.')
    request = json.loads(case.writer.calls[0].content)
    assert request['text']['format']['name'] == 'lore_page_response'
    assert 'leave collaboration null' not in request['instructions']
    assert 'leave the proposal empty' not in request['instructions']
    assert 'return needs_context with the specific question needed to continue' in request['instructions']
    assert request['input'][-1]['role'] == 'user'
    if output != 'lore_context_question':
        assert case.response.status_code == 503
        assert case.turn.completion is None
        return
    assert case.response.status_code == 200, case.response.text
    completion = case.turn.completion
    assert completion.collaboration is None
    assert any(row.kind == 'discussion' and row.text == 'Which subject and premise should the page describe?'
        for row in completion.answer_segments)
    assert all(page.page.title != 'Glass Regent' for page in pages.list_pages(world_id=case.world))
    reopened = case.client.get(f'/api/live/agent/worlds/{case.world}/conversation')
    assert reopened.status_code == 200, reopened.text
    assert 'Which subject and premise should the page describe?' in reopened.text
    assert not any(e.kind in {'native_body_search_v1', 'build_related_page_read_v1'}
        for e in case.turn.graph_context_execution.events)



def test_old_lore_admission_keeps_its_v2_request_and_page_readback(lane, tmp_path, monkeypatch):
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='review_lore_page_from_conversation', source_need='anchored',
        source_answer_output='lore_valid_gap', lore_legacy_menu=True,
        message='Create a separate page for Glass Regent from our discussion.')
    assert case.response.status_code == 200, case.response.text
    request = json.loads(case.writer.calls[0].content)
    assert request['text']['format']['name'] == 'surface_native_lore_request_reference_v2'
    assert 'leave collaboration null' in request['instructions']
    assert 'leave the proposal empty' in request['instructions']
    assert case.turn.completion.collaboration.destination.title == 'Glass Regent'
    from application_state.agent_conversation import AgentConversationService
    reopened = AgentConversationService().inspect_turn(world_id=case.world, turn_id=case.turn.turn_id)
    assert reopened.completion == case.turn.completion



def test_current_lore_sdk_omits_host_metadata_but_preserves_authored_words(lane, tmp_path, monkeypatch):
    message = 'Create a page for Glass Regent from our discussion. Preserve the authored phrase citation_policy as a fictional motto; do not search.'
    case = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='review_lore_page_from_conversation', source_need='anchored',
        source_answer_output='lore_valid_gap', message=message)
    assert case.response.status_code == 200, case.response.text
    request = json.loads(case.writer.calls[0].content)
    assert request['text']['format']['name'] == 'lore_page_response'
    schema = request['text']['format']['schema']
    assert 'schema' not in schema['properties']
    work = next(json.loads(row['content'])['build_work'] for row in request['input']
        if 'build_work' in json.loads(row['content']))
    assert not {'citation_policy', 'lore_limitation_policy', 'lore_reply_contract'} & set(work)
    assert work['lore_page_destination'] == {'request': 'current_author_request'}
    assert request['tools'] == []
    assert all(value not in request['instructions'] + json.dumps(schema) for value in (
        'dmb_surface_evidence_answer_v8', 'supplied_source_references_v1',
        'validated_lore_review_generic_gaps_v1', 'draft_or_context_question_v3'))
    evidence = next(json.loads(row['content']) for row in request['input']
        if 'user_question' in json.loads(row['content']))
    assert evidence['user_question'] == message
    assert 'citation_policy' in evidence['user_question']
    assert case.turn.completion.collaboration.destination.title == 'Glass Regent'


@pytest.mark.parametrize('downgrade', [False, True, 'review_kind_drift'])
def test_frozen_lore_outcome_survives_successor_menu_and_family_metadata(lane, tmp_path, monkeypatch, downgrade):
    from copy import deepcopy
    from dataclasses import replace
    from types import MappingProxyType, SimpleNamespace
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation import build_intentional_response as intent
    from application_state.agent_conversation.native_build_work_view import semantic_frame, lore_outcome_eligible
    from application_state.agent_conversation.plan_writer_output_schema import native_output_format
    from application_state.agent_conversation.rules_authority_plan_packet import model_rules_frame
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from apps.live_control_server.services import build_jev_runtime as runtime_factory
    base_harness = runtime_factory.BuildJevHarness
    snapshots = []
    original_init = PlanJevWriter.__init__
    def capture_producer(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        snapshots.append(SimpleNamespace(frame=deepcopy(self.frame), work=deepcopy(self.work_frame),
            rules=deepcopy(model_rules_frame(self.rules.frame()))))
    monkeypatch.setattr(PlanJevWriter, '__init__', capture_producer)
    first = _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='review_lore_page_from_conversation', source_need='anchored',
        source_answer_output='lore_valid_gap', message='Prepare a separate page for Glass Regent from our discussion.')
    assert first.response.status_code == 200, first.response.text
    producer = snapshots[0]
    offered = json.loads(first.writer.calls[0].content)['text']['format']
    def reconstruct_format():
        outcome = lore_outcome_eligible(producer.work, first.turn.graph_context_execution)
        wire = semantic_frame(producer.work, first.turn.graph_context_execution,
            bind_lore_page=True, supplied_source_references=True, typed_source_answer=True,
            lore_page_limitations=True, lore_request_reference=True, lore_outcome=outcome)
        return native_output_format(producer.frame, producer.rules, producer.work | wire,
            build_local=True, generic_reply_limits=True, lore_outcome=outcome,
            execution=first.turn.graph_context_execution)
    assert reconstruct_format() == offered
    old_menu = intent.MENU_DIGEST
    frozen = intent._MENU_CONTRACTS[old_menu]
    assert intent.menu_offers_lore_outcomes(old_menu)
    old_v2 = intent.digest(intent.question(guidance=intent._PRE_LORE_OUTCOME_GUIDANCE,
        work_options=intent._PRE_LORE_OUTCOME_WORK))
    assert not intent.menu_offers_lore_outcomes(old_v2)
    work = dict(intent.WORK)
    work['review_lore_page_from_conversation'] = replace(work['review_lore_page_from_conversation'],
        family='discuss', meaning='Prepare the requested page now from supplied authored context.')
    if downgrade == 'review_kind_drift':
        work['review_lore_page_from_conversation'] = replace(work['review_lore_page_from_conversation'], review='questions')
    work = MappingProxyType(work)
    guidance = intent.GUIDANCE + '\nPreserve authored proposals and unresolved questions.'
    menu = intent.digest(intent.question(guidance=guidance, work_options=work))
    resolver = intent._resolver_digest(work)
    monkeypatch.setattr(intent, '_MENU_CONTRACTS', MappingProxyType({**intent._MENU_CONTRACTS,
        menu: (guidance, work, resolver, frozen[3])}))
    monkeypatch.setattr(intent, 'WORK', work)
    monkeypatch.setattr(intent, 'GUIDANCE', guidance)
    monkeypatch.setattr(intent, 'MENU_DIGEST', menu)
    monkeypatch.setattr(intent, 'RESOLVER_DIGEST', resolver)
    instructions = intent.decision_instructions
    monkeypatch.setattr(intent, 'decision_instructions', lambda menu_digest=menu: instructions(menu_digest))
    assert intent.menu_offers_lore_outcomes(old_menu) and intent.menu_offers_lore_outcomes(menu)
    reopened = AgentConversationService().inspect_turn(world_id=first.world, turn_id=first.turn.turn_id)
    assert reopened.completion == first.turn.completion
    if downgrade == 'review_kind_drift':
        # A typed stored read is unchanged; the owning producing-schema boundary
        # must refuse reinterpretation under inconsistent review metadata.
        with pytest.raises(ValueError, match='frozen review kind'):
            intent.review_kind('review_lore_page_from_conversation')
        with pytest.raises(ValueError, match='frozen review kind'):
            reconstruct_format()
        first.client.close()
        return
    assert reconstruct_format() == offered
    first.client.close()
    # Each helper installs an HTTP harness; do not inherit its first transports.
    monkeypatch.setattr(runtime_factory, 'BuildJevHarness', base_harness)
    if downgrade:
        original = PlanJevWriter.__init__
        def older_reply(self, *args, **kwargs):
            original(self, *args, **kwargs)
            wire = semantic_frame(self.work_frame, self.adapter.turn.graph_context_execution,
                bind_lore_page=True, supplied_source_references=True, typed_source_answer=True,
                lore_page_limitations=True, lore_request_reference=True)
            for message in self.messages:
                value = json.loads(message['content'])
                if 'build_work' in value:
                    value['build_work'] = wire['build_work']
                    message['content'] = json.dumps(value)
            self.provider_work = wire
            self.output_format = native_output_format(self.frame, model_rules_frame(self.rules.frame()),
                self.work_frame | wire, build_local=True, generic_reply_limits=True)
        monkeypatch.setattr(PlanJevWriter, '__init__', older_reply)
    from tests.test_source_statements import make_lane
    second_lane = make_lane(tmp_path, monkeypatch, narrow=True)
    second = _fresh_case(second_lane, tmp_path, monkeypatch, None, True, False, False,
        requested_work='review_lore_page_from_conversation', source_need='anchored',
        source_answer_output='lore_valid_gap', message='Prepare the separate Glass Regent page now.')
    if downgrade:
        assert second.response.status_code == 503
        assert not second.writer.calls
    else:
        assert second.response.status_code == 200, second.response.text
        assert json.loads(second.writer.calls[0].content)['text']['format']['name'] == 'lore_page_response'
