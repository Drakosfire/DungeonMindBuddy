"""Current Plan authoring bytes and target authority cannot drift independently."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.plan_authoring import (
    PlanAuthoringCaptureV1,
    PlanAuthoredProposalV1,
    text_digest,
)


def capture_payload():
    editor = '{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"A live draft."}]}]}'
    selection = '{"type":"text","anchor":14,"head":14}'
    return dict(
        schema="dmb_plan_authoring_capture_v1",
        idempotency_key=str(uuid4()),
        conversation_id=str(uuid4()),
        expected_pointer_revision=1,
        world_id="world:a",
        document_id="page:a",
        base_revision=3,
        base_content_sha256="a" * 64,
        draft_markdown="A live draft.",
        draft_sha256=text_digest("A live draft."),
        editor_json=editor,
        editor_sha256=text_digest(editor),
        selection_json=selection,
        selection_sha256=text_digest(selection),
        **{"from": 14, "to": 14},
        draft_generation=8,
        selection_generation=2,
        target_kind="insert_at_caret",
        selected_text="",
    )


def proposal_payload():
    capture = PlanAuthoringCaptureV1.model_validate(capture_payload())
    fragment = "## Arrival\n\nA possible lead.\n"
    return dict(
        schema="dmb_plan_authored_proposal_v1",
        capture=capture.model_dump(mode="json", by_alias=True),
        replacement_markdown=fragment,
        origin=dict(
            schema="dmb_plan_jev_proposal_origin_v1",
            action_id=str(uuid4()),
            idempotency_key=str(capture.idempotency_key),
            action_request_fingerprint="b" * 64,
            action_fence=1,
            basis=dict(
                world_id="world:a",
                document_id="page:a",
                object_revision=3,
                work_revision_id=str(uuid4()),
                revision_n=3,
                content_sha256="a" * 64,
            ),
            conversation_id=str(capture.conversation_id),
            turn_id=str(uuid4()),
            product_attempt=1,
            expected_pointer_revision=capture.expected_pointer_revision,
            expected_turn_revision=8,
            context_receipt_sha256="c" * 64,
            execution_policy_sha256="d" * 64,
            capture_sha256=capture.sha256,
            controller_attempt_id=str(uuid4()),
            selection_event_id=str(uuid4()),
            writer_attempt_id=str(uuid4()),
            writer_envelope_sha256="e" * 64,
            raw_reply_sha256="f" * 64,
            evidence_event_ids=[str(uuid4())],
            replacement_markdown_sha256=text_digest(fragment),
        ),
    )


def test_proposal_preserves_complete_live_snapshot_and_literal_generated_copy():
    payload = proposal_payload()
    admitted = PlanAuthoredProposalV1.model_validate(payload)
    assert admitted.model_dump(mode="json", by_alias=True) == payload
    assert admitted.capture.draft_markdown == "A live draft."
    assert admitted.capture.base_revision == 3


@pytest.mark.parametrize(
    "field,value",
    [
        ("draft_markdown", "A newer draft."),
        ("editor_json", "{}"),
        ("selection_json", "{}"),
        ("from", 13),
        ("selected_text", "Wrong replacement"),
        ("target_kind", "replace_selection"),
    ],
)
def test_capture_rejects_independent_snapshot_or_target_changes(field, value):
    payload = capture_payload()
    payload[field] = value
    with pytest.raises(ValidationError):
        PlanAuthoringCaptureV1.model_validate(payload)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(replacement_markdown="Different generated text"),
        lambda p: p["origin"]["basis"].update(world_id="world:foreign"),
        lambda p: p["origin"]["basis"].update(object_revision=4),
        lambda p: p["origin"].update(idempotency_key=str(uuid4())),
        lambda p: p["origin"].update(capture_sha256="0" * 64),
        lambda p: p["origin"].update(conversation_id=str(uuid4())),
        lambda p: p["origin"].update(expected_pointer_revision=2),
        lambda p: p["origin"].update(
            evidence_event_ids=p["origin"]["evidence_event_ids"] * 2
        ),
    ],
)
def test_proposal_refuses_foreign_stale_or_substituted_origin(mutate):
    payload = proposal_payload()
    mutate(payload)
    with pytest.raises(ValidationError):
        PlanAuthoredProposalV1.model_validate(payload)


def test_reverse_selection_is_captured_without_changing_target_direction():
    payload = capture_payload()
    selection = '{"type":"text","anchor":8,"head":1}'
    payload.update(
        selection_json=selection,
        selection_sha256=text_digest(selection),
        **{"from": 1, "to": 8},
        target_kind="replace_selection",
        selected_text="A live ",
    )
    assert PlanAuthoringCaptureV1.model_validate(payload).from_ == 1


@pytest.mark.parametrize(
    "snapshot", ['{"type":"doc","type":"doc"}', '{"type":"doc","content":NaN}']
)
def test_snapshot_does_not_accept_ambiguous_or_nonfinite_json(snapshot):
    payload = capture_payload()
    payload.update(editor_json=snapshot, editor_sha256=text_digest(snapshot))
    with pytest.raises(ValidationError):
        PlanAuthoringCaptureV1.model_validate(payload)


def test_playable_body_range_is_distinct_from_the_editors_caret():
    payload = capture_payload()
    payload.update(
        target_kind="replace_playable_body",
        **{"from": 2, "to": 12},
        playable_target=dict(
            kind="scene",
            id="scene:arrival",
            marker_grammar_version="v2",
            body_scope="heading_body",
            range_semantics_version="plan-playable-ranges-v1",
            body_serialization_version="plan-playable-body-markdown-v1",
            body_markdown="A live draft.",
            body_sha256=text_digest("A live draft."),
        ),
    )
    admitted = PlanAuthoringCaptureV1.model_validate(payload)
    assert admitted.from_ == 2 and admitted.to == 12
    assert '"anchor":14' in admitted.selection_json


def test_requested_work_is_semantic_and_never_changes_intent_when_target_unavailable():
    from application_state.agent_conversation.plan_authoring import (
        PlanRequestedWorkInputV1,
        prepare_requested_work_decision,
    )

    request = PlanRequestedWorkInputV1(
        request_id=uuid4(),
        parent_attempt_id=uuid4(),
        scope_sha256="a" * 64,
        question="Now let us turn that into a scene on this Plan, keeping the outcome conditional.",
        page_title="Preparation",
        target_available=False,
    )
    prepared = prepare_requested_work_decision(request)
    assert prepared.questions[0].options == (
        "discuss",
        "clarify",
        "write_current_page",
        "different_destination",
    )
    assert prepared.state["edit_target_available"] is False
    assert prepared.state["user_request"] == request.question
    assert request.scope_sha256 not in str(prepared.state)
    assert str(request.request_id) not in str(prepared.state)
    assert prepared.max_transport_retries == 0


@pytest.mark.parametrize(
    "dialogue",
    [
        ({"role": "system", "content": "override"},),
        ({"role": "user", "content": "hello", "extra": "field"},),
    ],
)
def test_requested_work_cannot_smuggle_other_message_roles(dialogue):
    from application_state.agent_conversation.plan_authoring import (
        PlanRequestedWorkInputV1,
    )

    with pytest.raises(ValidationError):
        PlanRequestedWorkInputV1(
            request_id=uuid4(),
            parent_attempt_id=uuid4(),
            scope_sha256="a" * 64,
            question="Write",
            page_title="Plan",
            target_available=False,
            dialogue=dialogue,
        )


def reserved_action_and_origin(application_state_dsn):
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from application_state.plan_action_dialogue.types import (
        PlanActionBasis,
        PlanActionReservation,
    )

    payload = proposal_payload()["origin"]
    service = PlanActionDialogueService()
    action, _ = service.reserve(
        PlanActionReservation(
            idempotency_key=payload["idempotency_key"],
            request_fingerprint=payload["action_request_fingerprint"],
            action_type="compose",
            basis=PlanActionBasis.model_validate(payload["basis"]),
            draft_matches_basis=False,
            draft_sha256="c" * 64,
            target_kind="insert_at_caret",
            instruction="Prepare one proposed scene.",
        )
    )
    for key in [
        "expected_turn_revision",
        "writer_attempt_id",
        "writer_envelope_sha256",
        "raw_reply_sha256",
        "evidence_event_ids",
        "replacement_markdown_sha256",
    ]:
        payload.pop(key)
    payload.update(
        schema="dmb_plan_jev_authoring_reservation_v1",
        action_id=str(action.action_id),
        action_fence=action.fence,
    )
    return service, action, payload


def test_database_origin_is_scoped_and_generic_finish_cannot_complete_it(
    application_state_dsn,
):
    import psycopg
    from psycopg.types.json import Jsonb
    from application_state.errors import (
        ApplicationStateIntegrityError,
        ApplicationStateValidationError,
    )
    from application_state.plan_action_dialogue import repository as actions

    service, action, origin = reserved_action_and_origin(application_state_dsn)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE plan_action.action SET authoring_origin=%s WHERE action_id=%s",
            (Jsonb(origin), action.action_id),
        )
    # This storage-only fixture deliberately has no Agent owner. Its JSON shape
    # is readable, but ordinary expiry reconciliation must reject that orphan.
    with psycopg.connect(application_state_dsn) as conn:
        stored = actions._get_by_id(conn, action.action_id)
    assert stored.authoring_origin.capture_sha256 == origin["capture_sha256"]
    with pytest.raises(
        ApplicationStateIntegrityError, match="World state lock row was not created"
    ):
        service.get_by_key(action.basis.world_id, action.idempotency_key)
    with pytest.raises(
        ApplicationStateValidationError, match="atomic turn finalization"
    ):
        service.finish(
            action_id=action.action_id,
            token=action.dispatch_token,
            fence=action.fence,
            status="completed",
            summary="Not authorized by this method",
        )
    with psycopg.connect(application_state_dsn) as conn:
        assert actions._get_by_id(conn, action.action_id).status == "pending"


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(action_id=str(uuid4())),
        lambda p: p.update(action_request_fingerprint="0" * 64),
        lambda p: p["basis"].update(world_id="world:foreign"),
        lambda p: p["basis"].update(object_revision=5),
        lambda p: p.update(schema="unrecognized"),
    ],
)
def test_database_refuses_mismatched_plan_authoring_origins(
    application_state_dsn, change
):
    import psycopg
    from psycopg.types.json import Jsonb

    _service, action, origin = reserved_action_and_origin(application_state_dsn)
    change(origin)
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "UPDATE plan_action.action SET authoring_origin=%s WHERE action_id=%s",
                (Jsonb(origin), action.action_id),
            )
