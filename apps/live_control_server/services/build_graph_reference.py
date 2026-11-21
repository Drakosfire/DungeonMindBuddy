"""Read current native Graph identity before accepting typed Build placement."""

from __future__ import annotations

from hashlib import sha256

from application_state.agent_conversation.authored_graph_references import (
    AuthoredGraphReferenceV1, native_references, object_selections,
)
from application_state.agent_conversation.plan_authoring import strict_json
from application_state.agent_conversation.types import BuildAuthoredReferencesCapturedV1
from application_state.build_proposal.graph_reference import BuildGraphReferencePlacement
from application_state.build_proposal.graph_reference_decision import (
    BuildGraphReferenceCandidate, BuildGraphReferenceDecision,
)
from application_state.build_proposal.graph_reference_review import BuildGraphReferencePrepare, BuildGraphReferenceReview
from application_state.build_proposal.prose_catalog import catalog_for_build_capability
from application_state.content.markdown_source_blocks import source_block_spans
from application_state.content.page_presentation import BlockBinding, PagePresentation, leading_yaml
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.config import managed_world_data_root
from apps.live_control_server.models.native_graph_inspection import InspectionPin, InspectionScope

from .agent_graph_auth import NativeGraphPrincipal
from .build_document_proposal import BuildComposeError, _source
from .native_graph_explorer import NativeGraphExplorerError, hosted_response_binding
from .native_graph_inspection import InspectionUnavailable, authoring_identities
from .workspace_document_registry import WorkspaceDocumentRegistryError, get_committed_page_snapshot


def _read_current_graph(world_id: str, principal: NativeGraphPrincipal):
    try:
        with hosted_response_binding(principal, world_id):
            return authoring_identities(InspectionScope(managed_world_id=world_id), principal)
    except (InspectionUnavailable, NativeGraphExplorerError) as error:
        raise ApplicationStateConflictError("The current Graph identity is unavailable") from error


def read_build_graph_reference_candidates(
    world_id: str, principal: NativeGraphPrincipal,
) -> tuple[BuildGraphReferenceCandidate, ...]:
    graph = _read_current_graph(world_id, principal)
    pin = InspectionPin.model_validate(graph["scope"])
    if pin.managed_world_id != world_id or pin.scope_mode != "world":
        raise ApplicationStateConflictError("The Graph nomination scope differs from the current World")
    return tuple(
        BuildGraphReferenceCandidate(
            reference=AuthoredGraphReferenceV1(
                managed_world_id=pin.managed_world_id,
                native_world_id=pin.native_world_id,
                binding_version=pin.binding_version,
                graph_revision=pin.revision_id,
                node_id=row["node_id"],
                label=row["label"],
            ),
            entity_kind=row["kind"],
            aliases=tuple(row.get("aliases", ())),
            summary=row.get("summary"),
        )
        for row in graph["identities"]
        if row["selectable"] is True and row["label"] != row["node_id"]
    )


def captured_build_graph_reference(execution) -> AuthoredGraphReferenceV1 | None:
    """Read an exact author selection from the admitted native action and its capture."""
    references = native_references(execution)
    selections = object_selections(references)
    if not selections:
        return None
    captures = [event for event in execution.events if isinstance(event, BuildAuthoredReferencesCapturedV1)]
    if len(captures) != 1 or captures[0].references != references:
        raise ApplicationStateConflictError("The selected Graph identity has no matching native author capture")
    if len(selections) != 1:
        raise ApplicationStateConflictError("Choose one existing Graph object for this reference")
    return selections[0]


def prepare_build_graph_reference_decision(execution, principal: NativeGraphPrincipal, *, title, dialogue):
    """Combine the admitted editor capture and current authorized Graph for Jev."""
    from application_state.agent_conversation.native_execution import NativeBuildActionV1

    action = execution.policy.action
    if not isinstance(action, NativeBuildActionV1) or action.intent.reviewed_step is not None:
        raise ApplicationStateConflictError("A Graph reference needs a fresh native Build action")
    capability = action.write_capability
    catalog = catalog_for_build_capability(capability)
    if catalog is None or capability.basis.visibility != "internal":
        raise ApplicationStateConflictError("A Graph reference needs the captured internal page")
    selected = captured_build_graph_reference(execution)
    candidates = read_build_graph_reference_candidates(capability.basis.world_id, principal)
    if selected is not None and all(item.reference != selected for item in candidates):
        raise ApplicationStateConflictError("The selected Graph identity changed. Choose it again.")
    return BuildGraphReferenceDecision(
        basis=capability.basis, catalog=catalog, candidates=candidates,
        question=action.intent.message, title=title, dialogue=dialogue, author_selected=selected,
    )


class BuildGraphReferenceDriver:
    """The second Build decision has its own mode-bound provider envelope."""

    def __init__(self, adapter, decision: BuildGraphReferenceDecision):
        from .build_jev_driver import digest
        from .build_jev_transitions import DecisionIntent, DecisionQuestion

        self.adapter = adapter
        self.decision = decision
        request = decision.request()
        self.step = DecisionIntent(
            request_id="graph-reference:" + digest(request.state), phase="select", state=request.state,
            questions=tuple(DecisionQuestion(name=q.name, kind="choice", question=q.question, options=q.options)
                            for q in request.questions),
        )
        self.projection = None
        self.completed = None

    def stage(self):
        from .build_jev_driver import DriverDecisionProjection, canonical, wire_questions

        adapter = self.adapter
        self.projection = DriverDecisionProjection(
            canonical(self.step.state), canonical(wire_questions(self.step)), self.step.request_id,
            len(adapter._broker_execution().events), str(adapter.last_provider_attempt_id), (), (), (),
            host_phase="graph_reference",
        )
        return self.projection

    def authorize(self, prepared):
        from .build_jev_dispatch import prepared_driver_view

        adapter = self.adapter
        projection = self.projection
        if (projection.event_sequence != len(adapter._broker_execution().events)
                or projection.prior_provider_attempt_id != str(adapter.last_provider_attempt_id)):
            return False
        view = prepared_driver_view(prepared, projection, accounting=adapter._build_jev_accounting)
        return adapter.authorize_native_build_decision(
            prepared, view, projection, graph_reference_decision=self.decision,
        )

    def accept_decision(self, model, answers, *, actual_response):
        from .build_jev_driver import canonical

        adapter = self.adapter
        turn = adapter.fence.turn
        self.completed = adapter.service.complete_build_graph_reference_turn(
            world_id=turn.world_id, conversation_id=turn.conversation_id, turn_id=turn.turn_id,
            expected_revision=turn.revision, provider_attempt_id=adapter.last_provider_attempt_id,
            decision=self.decision, request_json=adapter._prepared_build_decision.body.decode(),
            response_json=canonical(actual_response.model_dump(mode="json")),
            authorize_placement=lambda review: authorize_graph_reference_save(review, adapter.native_query_context.principal),
        )
        adapter.turn = self.completed


def require_current_build_graph_reference(
    placement: BuildGraphReferencePlacement, principal: NativeGraphPrincipal,
) -> None:
    reference = placement.reference
    graph = _read_current_graph(placement.basis.world_id, principal)
    expected = InspectionPin(
        managed_world_id=reference.managed_world_id,
        native_world_id=reference.native_world_id,
        binding_version=reference.binding_version,
        revision_id=reference.graph_revision,
    )
    if graph["scope"] != expected.model_dump(mode="json"):
        raise ApplicationStateConflictError("The selected Graph identity belongs to a different or changed Graph")
    matches = [row for row in graph["identities"] if row["node_id"] == reference.node_id]
    if (len(matches) != 1 or not matches[0]["selectable"]
            or matches[0]["kind"] != placement.entity_kind or matches[0]["label"] != reference.label):
        raise ApplicationStateConflictError("The selected Graph identity or classification changed")


def _ids(editor_json):
    return [block.get("attrs", {}).get("pageBlockId") for block in strict_json(editor_json)["content"]]


def _expected_layout(source, command, committed_markdown, prefix):
    before_ids = _ids(command.editor_json)
    if source.page_presentation is None:
        if any(before_ids):
            raise ApplicationStateConflictError("The captured Graph placement differs from the saved page identities")
        return None
    if (any(item.kind != "block" for item in source.page_presentation.items)
            or [item.id for item in source.page_presentation.items] != before_ids):
        raise ApplicationStateConflictError("The captured Graph placement differs from the saved page identities")
    offset = len(prefix.encode("utf-8"))
    encoded = committed_markdown.encode("utf-8")
    after_ids = _ids(command.after_editor_json)
    spans = source_block_spans(command.after_draft_markdown)
    bindings = [BlockBinding(
        id=identity, byte_start=start + offset, byte_end=end + offset,
        sha256=sha256(encoded[start + offset:end + offset]).hexdigest(),
    ) for identity, (start, end) in zip(after_ids, spans, strict=True)]
    return PagePresentation(markdown_sha256=sha256(encoded).hexdigest(), items=bindings).checked(
        committed_markdown,
    ).fingerprint()


def authorize_graph_reference_prepare(
    review: BuildGraphReferenceReview, command: BuildGraphReferencePrepare, principal: NativeGraphPrincipal,
) -> None:
    source = authorize_graph_reference_save(review, principal)
    prefix = leading_yaml(source.markdown)
    after_markdown = prefix + command.after_draft_markdown
    if (source.markdown[len(prefix):] != command.draft_markdown
            or sha256(after_markdown.encode("utf-8")).hexdigest() != command.apply.content_sha256):
        raise ApplicationStateConflictError("The Graph reference prepare differs from the exact saved source")
    if _expected_layout(source, command, after_markdown, prefix) != command.apply.presentation_sha256:
        raise ApplicationStateConflictError("The Graph reference prepare differs from the exact page identities")


def authorize_graph_reference_save(review: BuildGraphReferenceReview, principal: NativeGraphPrincipal):
    try:
        source = _source(review.placement)
    except (BuildComposeError, WorkspaceDocumentRegistryError) as error:
        raise ApplicationStateConflictError("The saved page changed before Graph reference placement") from error
    require_current_build_graph_reference(review.placement, principal)
    return source


def observe_graph_reference_save(review: BuildGraphReferenceReview) -> int:
    basis = review.placement.basis
    try:
        snapshot = get_committed_page_snapshot(managed_world_data_root(), basis.document_id)
    except WorkspaceDocumentRegistryError as error:
        raise ApplicationStateConflictError("The saved Graph reference page is unavailable") from error
    record = snapshot.record
    receipt = review.apply
    if (receipt is None or record.document_id != basis.document_id or record.world_id != basis.world_id
            or record.status != "active" or record.content_status != "committed"
            or record.kind != "worldbuilding_source" or record.source_domain != "worldbuilding"
            or record.visibility_state != basis.visibility or snapshot.loaded_revision != basis.registry_revision + 1
            or record.revision != snapshot.loaded_revision or snapshot.content_sha256 != receipt.content_sha256
            or sha256(snapshot.markdown.encode("utf-8")).hexdigest() != receipt.content_sha256
            or snapshot.page_presentation_sha256 != receipt.presentation_sha256):
        raise ApplicationStateConflictError("The saved Graph reference does not match the prepared insertion")
    return snapshot.loaded_revision
