"""World-scoped metadata discovery and exact saved-page materialization."""

import json
from hashlib import sha256
from uuid import uuid4
from application_state.agent_conversation.build_related_pages import (
    POLICY as POLICY,
    PagePointer,
    PageReference,
    RelatedPagesSelection,
    RelatedPageRead,
    RelatedPageClaim,
    should_read_page,
)
from apps.live_control_server.config import (
    repo_root,
    managed_world_data_root,
)
from .workspace_document_registry import (
    list_workspace_documents,
    get_workspace_document_snapshot,
)


def root():
    return managed_world_data_root(repo_root())


def discover(request):
    world_id = request.owner_scope.world_id
    primary = request.primary_work.object_id
    return [
        PagePointer(
            world_id=world_id,
            document_id=r.document_id,
            registry_revision=r.revision,
            title=r.title,
            visibility=r.visibility_state,
        ).model_dump(mode="json")
        for r in sorted(
            list_workspace_documents(root(), kind="worldbuilding_source"),
            key=lambda r: r.document_id,
        )
        if r.world_id == world_id
        and r.document_id != primary
        and r.status == "active"
        and r.content_status == "committed"
        and r.source_domain == "worldbuilding"
        and r.document_class
        and r.authority_state in {"draft", "reviewed", "canonical"}
        and r.visibility_state in {"internal", "player_safe"}
    ]


def materialize(pointer):
    page = PagePointer.model_validate(pointer)
    snapshot = get_workspace_document_snapshot(root(), str(page.document_id))
    r = snapshot.record
    if (
        r.world_id != page.world_id
        or r.document_id != str(page.document_id)
        or r.kind != "worldbuilding_source"
        or r.status != "active"
        or r.content_status != "committed"
        or r.revision != page.registry_revision
        or snapshot.loaded_revision != page.registry_revision
        or r.title != page.title
        or r.visibility_state != page.visibility
        or r.source_domain != "worldbuilding"
        or not r.document_class
        or r.authority_state not in {"draft", "reviewed", "canonical"}
        or snapshot.content_sha256 != sha256(snapshot.markdown.encode()).hexdigest()
    ):
        raise ValueError(
            "The selected saved authoring page changed or is unavailable; no newer page was substituted"
        )
    return {
        **page.model_dump(mode="json"),
        "content_sha256": snapshot.content_sha256,
        "markdown": snapshot.markdown,
    }


def select_pages(driver, prepared, response):
    from .agent_turn_service import _require_fresh_execution_append
    from .build_jev_driver import canonical, digest
    from application_state.agent_conversation import types as t

    a = driver._adapter
    policy = a._broker_execution().policy
    offered = getattr(policy, "related_page_catalog", [])
    questions = json.loads(prepared.body)["questions"]
    selected = sorted(
        [
            p.document_id
            for i, p in enumerate(offered)
            if should_read_page(p, questions[f"related_page_{i}"], response.answers[f"related_page_{i}"])
        ],
        key=str,
    )
    auth = next(
        e
        for e in a._broker_execution().events
        if isinstance(e, t.ProviderAttemptAuthorizedEventV3)
        and e.provider_attempt_id == a.last_provider_attempt_id
    )
    raw = canonical(response.model_dump(mode="json"))
    event = RelatedPagesSelection(
        event_id=uuid4(),
        sequence=len(a._broker_execution().events),
        controller_attempt_id=auth.provider_attempt_id,
        controller_envelope_sha256=auth.envelope_sha256,
        controller_response_sha256=digest(response.model_dump(mode="json")),
        document_ids=selected,
    )
    a.turn = _require_fresh_execution_append(
        a.fence.append(
            "record_build_related_pages",
            "event",
            event,
            producer_proof={
                "request_json": prepared.body.decode(),
                "response_json": raw,
            },
        )
    )
    return event


def acquire_selected_pages(a):
    from .agent_turn_service import _require_fresh_execution_append
    from application_state.agent_conversation.build_related_pages import (
        catalog,
        records,
    )

    offered = catalog(a._broker_execution().policy)
    if offered is None:
        return
    from application_state.agent_conversation.types import BuildReviewedActionSelectionV1
    if not offered and any(isinstance(e, BuildReviewedActionSelectionV1) for e in a._broker_execution().events):
        return
    selections = [
        e for e in a._broker_execution().events if isinstance(e, RelatedPagesSelection)
    ]
    if len(selections) != 1 or records(a._broker_execution()):
        raise ValueError("Related authoring reads require a fresh selected page wave")
    event = selections[0]
    selected = event.document_ids
    for pointer in offered:
        if pointer.document_id not in selected:
            continue
        actual = materialize(pointer)
        body = actual.pop("markdown")
        read = RelatedPageRead(
            event_id=uuid4(),
            sequence=len(a._broker_execution().events),
            read_id=uuid4(),
            selection_event_id=event.event_id,
            page=PageReference.model_validate(actual),
            markdown=body,
        )
        a.turn = _require_fresh_execution_append(
            a.fence.append(
                "record_build_related_pages",
                "event",
                read,
                materializer=lambda p=pointer: materialize(p),
            )
        )
        if a.context_capture is not None:
            a.context_capture.observe(
                {
                    "kind": "context_decision",
                    "action": "retrieved",
                    "item_ids": [
                        f"{read.page.title} · saved revision {read.page.registry_revision} · {read.read_id}"
                    ],
                    "reason_code": "question_relevance",
                    "policy_version": POLICY,
                }
            )


def open_page(service, world_id, turn_id, read_id):
    turn = service.inspect_turn(world_id=world_id, turn_id=turn_id)
    from application_state.agent_conversation.types import (
        Turn,
        BuildDraftContextCompletionV1, BuildIntentionalResponseCompletionV1,
    )
    from application_state.agent_conversation.rules_authority_reads import (
        MixedCompletedTurnV1,
    )

    if isinstance(turn, MixedCompletedTurnV1):
        if turn.base_projection.kind != "approved":
            raise ValueError("Related authored page lacks an approved base answer")
        turn = turn.base_projection.turn
    if turn.world_id != world_id or turn.turn_id != turn_id:
        raise ValueError("Related authoring read belongs to another World or turn")
    if (
        not isinstance(turn, Turn)
        or turn.status != "completed"
        or not isinstance(turn.completion, (BuildDraftContextCompletionV1, BuildIntentionalResponseCompletionV1))
    ):
        raise ValueError("Related page requires its completed authored answer")
    matches = [
        s
        for s in turn.completion.answer_segments
        if isinstance(s, RelatedPageClaim) and s.read_id == read_id
    ]
    rows = [
        e
        for e in turn.graph_context_execution.events
        if isinstance(e, RelatedPageRead) and e.read_id == read_id
    ]
    from application_state.agent_conversation.collaboration import ProposedConnectedPage
    proposed=getattr(turn.completion,"collaboration",None)
    review_match=isinstance(proposed,ProposedConnectedPage) and str(proposed.read_id)==str(read_id)
    if (
        not (matches or review_match)
        or len(rows) != 1
        or any(s.page != rows[0].page for s in matches)
        or rows[0].page.world_id != world_id
    ):
        raise ValueError("Related page differs from the completed answer's exact read")
    return {
        "schema": "dmb_agent_related_page_read_v1",
        "world_id": world_id,
        "turn_id": str(turn_id),
        "read_id": str(read_id),
        "page": rows[0].page.model_dump(mode="json"),
        "markdown": rows[0].markdown,
    }
