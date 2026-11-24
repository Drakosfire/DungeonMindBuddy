"""Derive the scripted frozen-placement HTTP diagnostic in a disposable checkout.

This is a bounded owner test, not a live-model cohort or deployment proof.
The fixture is embedded in the generated test after checking its caller-supplied
file digest. Run only with the separately owned App-clone fixture.
"""
from hashlib import sha256
import json
from pathlib import Path


def generate(source, output, fixture_path, *, expected_fixture_sha256, related_page_vote="read"):
    source, output, fixture_path = map(Path, (source, output, fixture_path))
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("Witness must be a new file separate from its owner")
    if not isinstance(related_page_vote, str) or related_page_vote not in {"read", "skip"}:
        raise ValueError("Related-page vote must be read or skip")
    raw = fixture_path.read_bytes()
    if (not isinstance(expected_fixture_sha256, str) or len(expected_fixture_sha256) != 64
            or sha256(raw).hexdigest() != expected_fixture_sha256):
        raise ValueError("Frozen fixture file differs from its pin")
    data = json.loads(raw)
    if (not isinstance(data, dict) or data.get("schema") != "negative_retrieval_cases_v1"
            or data.get("split") != "development"):
        raise ValueError("Expected the frozen development fixture")
    if not isinstance(data.get("cases"), list):
        raise ValueError("Expected a fixture case list")
    matches = [row for row in data["cases"] if isinstance(row, dict) and row.get("id") == "dev-placement"]
    if len(matches) != 1:
        raise ValueError("Expected exactly one placement case")
    fixture = matches[0]
    history, related = fixture.get("history"), fixture.get("related_pages")
    if (not isinstance(fixture.get("page"), str) or not fixture["page"].strip()
            or not isinstance(fixture.get("request"), str) or not fixture["request"].strip()
            or not isinstance(history, list) or len(history) != 2 or any(not isinstance(row, dict) for row in history)
            or [row.get("role") for row in history] != ["user", "assistant"]
            or any(not isinstance(row.get("content"), str) or not row["content"].strip() for row in history)
            or not isinstance(related, list) or len(related) != 1 or not isinstance(related[0], dict)
            or any(not isinstance(related[0].get(key), str) or not related[0][key].strip()
                   for key in ("label", "title", "body"))):
        raise ValueError("Frozen placement fixture shape changed")
    text = source.read_text()

    def replace_once(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError("Build owner fixture anchor changed")
        text = text.replace(old, new, 1)

    replace_once("    world = lane.world.world_id\n", "    world = lane.world.world_id\n    frozen_fixture = FROZEN_FIXTURE\n")
    replace_once("    source = get_workspace_document_snapshot(tmp_path, page.document_id)\n", """    save_page(tmp_path, page.document_id, frozen_fixture['page'])
    source = get_workspace_document_snapshot(tmp_path, page.document_id)
    assert source.markdown == frozen_fixture['page']
""")
    replace_once("        conversation = _new(service,world)\n", """        conversation = _new(service,world)
        from tests.test_agent_conversation_world_retry import _submission
        from application_state.agent_conversation.types import TurnResult
        submitted = _submission(world, conversation.conversation_id, uuid4(), user_text=frozen_fixture['history'][0]['content'])
        accepted = service.accept_turn(submitted)
        running = service.begin_turn(world, conversation.conversation_id, accepted.turn_id, expected_revision=accepted.revision)
        service.complete_turn(TurnResult(world_id=world, conversation_id=conversation.conversation_id,
            turn_id=accepted.turn_id, expected_revision=running.revision, assistant_text=frozen_fixture['history'][1]['content']))
        dialogue = service.list_build_dialogue(world, conversation.conversation_id)
        assert dialogue[0]['user'] == frozen_fixture['history'][0]['content'] and dialogue[0]['assistant'] == frozen_fixture['history'][1]['content']
""")
    replace_once("        text = image_markdown + 'An unsaved orchid possibility. Never a played fact. 🌸'\n",
                 "        text = frozen_fixture['page']\n")
    replace_once("            assert history.json()['turns'][0]['knowledge_context']['completion']==context['completion']\n",
                 "            assert next(row for row in history.json()['turns'] if row['turn_id']==str(turn.turn_id))['knowledge_context']['completion']==context['completion']\n")
    replace_once("        assert context['completion']['action_id']==str(record.action_id)\n", """        assert context['completion']['action_id']==str(record.action_id)
        from application_state.build_proposal.review import BuildProposalReviewService, BuildReviewCommand
        review_service = BuildProposalReviewService()
        opened = review_service.execute(world, record.action_id, BuildReviewCommand(operation='open', expected_revision=0))
        moved = review_service.execute(world, record.action_id, BuildReviewCommand(
            operation='move', expected_revision=opened.revision, placement_caret=opened.placement_caret + 3))
        assert review_service.get(world, record.action_id) == moved
        assert moved.placement_caret == opened.placement_caret + 3
        prepared = review_service.execute(world, record.action_id, BuildReviewCommand(
            operation='prepare', expected_revision=moved.revision, apply_id=uuid4(),
            after_editor_sha256='a' * 64, after_draft_sha256='b' * 64))
        assert prepared.apply.placement_caret == moved.placement_caret
        assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
        FROZEN_STATE['moved'] = True
        print('negative_retrieval_frozen_proposal_moved_unchanged_page: true')
""")
    replace_once('title="Optional lore", kind="worldbuilding_source", source_domain="worldbuilding",',
                 'title=frozen_fixture["related_pages"][0]["title"], kind="worldbuilding_source", source_domain="worldbuilding",')
    replace_once('save_page(tmp_path, optional_page.document_id, "This unrelated lore should remain unread.")',
                 'save_page(tmp_path, optional_page.document_id, frozen_fixture["related_pages"][0]["body"])')
    if related_page_vote == "skip":
        replace_once('else "read" if read_optional_page and name.startswith("related_page_")',
                     'else "skip" if read_optional_page and name.startswith("related_page_")')
    replace_once('    class Decisions(httpx2.AsyncBaseTransport):\n', """    from apps.live_control_server.services.workspace_document_registry import list_workspace_documents, update_workspace_document_metadata
    from apps.live_control_server.services import build_related_pages
    from evals.negative_retrieval.fixture_sources import inspect_related_pages
    from unittest.mock import patch
    other = [row for row in list_workspace_documents(tmp_path, kind='worldbuilding_source')
             if row.world_id == world and row.document_id not in {page.document_id, optional_page.document_id}]
    assert len(other) == 1 and other[0].title == 'Test Source'
    update_workspace_document_metadata(tmp_path, other[0].document_id, document_class=None, expected_revision=other[0].revision)
    fixture_request = SimpleNamespace(owner_scope=SimpleNamespace(world_id=world), primary_work=SimpleNamespace(object_id=page.document_id))
    # Fixture verification is outside the measured product-turn probe.
    with patch.object(build_related_pages, 'discover', build_related_pages.discover.__wrapped__), patch.object(build_related_pages, 'materialize', build_related_pages.materialize.__wrapped__):
        fixture_before = inspect_related_pages(fixture_request, frozen_fixture)
    FROZEN_STATE.update(request=fixture_request, before=fixture_before)
    print('negative_retrieval_frozen_inventory_before: verified')
    class Decisions(httpx2.AsyncBaseTransport):
""")
    test = """
from evals.negative_retrieval.owned_db_fixture import application_state_dsn
FROZEN_STATE = {}

def test_negative_retrieval_frozen_placement_http(lane, tmp_path, monkeypatch):
    from evals.negative_retrieval.related_page_probe import observe_related_page_owners
    fixture = FROZEN_FIXTURE
    with observe_related_page_owners() as records:
        _fresh_case(lane, tmp_path, monkeypatch, None, True, False, True,
            message=fixture['request'], requested_work='write_current_page', source_need='anchored',
            read_optional_page=True, proposal_markdown=fixture['history'][1]['content'])
    from evals.negative_retrieval.fixture_sources import inspect_related_pages
    after = inspect_related_pages(FROZEN_STATE['request'], fixture)
    assert after == FROZEN_STATE['before']
    assert FROZEN_STATE.get('moved') is True
    print('negative_retrieval_frozen_inventory_after: verified')
    print('negative_retrieval_frozen_placement_probe:', records)
    assert not records, 'Frozen placement case has a zero discovery and materialization budget'
"""
    output.write_text(text + "\nFROZEN_FIXTURE = " + repr(fixture) + "\n" + test)
