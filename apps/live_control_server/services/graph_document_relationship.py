"""Saved-page selection adapter; governed Graph prepare/commit remain the only writer."""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.live_control_server.config import artifact_data_root
from .graph_document_source import GraphDocumentSource, resolve_graph_document_source
from .graph_object_authoring_prepare import GraphObjectAuthoringPrepareRequest, GraphObjectAuthoringError
from .workspace_document_registry import get_committed_page_snapshot
from apps.live_control_server.models.native_graph_inspection import InspectionScope
from .agent_graph_auth import NativeGraphPrincipal
from .native_graph_inspection import authoring_identities


class RelationshipEndpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    node_id: str | None
    label: str = Field(min_length=1)
    kind: str = Field(min_length=1)

    @model_validator(mode="after")
    def readable(self):
        if any(not value.strip() or value != value.strip() for value in (self.label, self.kind)) or self.node_id == "":
            raise ValueError("Choose a readable identity")
        return self


class DocumentRelationshipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    world_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,62}$")
    document_source: GraphDocumentSource
    quote: str = Field(min_length=1)
    source: RelationshipEndpoint
    target: RelationshipEndpoint
    predicate: str = Field(min_length=1)
    label: str = Field(min_length=1)
    context: str = Field(min_length=1)


def resolve_reviewed_passage(root: Path, request: DocumentRelationshipRequest):
    """Resolve the exact saved page and its unambiguous selected passage."""
    def refuse(message):
        raise GraphObjectAuthoringError(message, code="relationship_review_invalid", status_code=409)

    selector = request.document_source
    snapshot = get_committed_page_snapshot(root, selector.document_id)
    if (snapshot.record.world_id != request.world_id or snapshot.record.campaign_id != request.world_id
            or snapshot.record.kind != "worldbuilding_source" or snapshot.record.status != "active"
            or snapshot.record.content_status != "committed"
            or snapshot.record.document_id != selector.document_id
            or snapshot.record.revision != selector.revision
            or snapshot.loaded_revision != selector.revision
            or snapshot.content_sha256 != selector.content_sha256):
        refuse("The saved page changed or belongs to another World. Select the current saved passage again.")
    body = snapshot.markdown
    start = body.find(request.quote)
    if not request.quote.strip() or start < 0 or body.find(request.quote, start + 1) >= 0:
        refuse("Choose one exact, uniquely occurring saved passage.")
    quote_bytes = request.quote.encode("utf-8")
    start_byte = len(body[:start].encode("utf-8"))
    return snapshot, start, {
        "start_byte": start_byte,
        "end_byte": start_byte + len(quote_bytes),
        "expected_slice_sha256": sha256(quote_bytes).hexdigest(),
    }


def _validate_relationship_review(root: Path, request: DocumentRelationshipRequest, principal: NativeGraphPrincipal):
    """Resolve one exact occurrence and deliberate identities, without publishing."""
    root = artifact_data_root(root)

    def refuse(message):
        raise GraphObjectAuthoringError(message, code="relationship_review_invalid", status_code=409)

    snapshot, start, _span = resolve_reviewed_passage(root, request)
    body = snapshot.markdown
    if any(not value.strip() or value != value.strip() for value in (request.predicate, request.label, request.context)):
        refuse("Describe the relationship and its context before previewing.")
    if ((request.source.node_id and request.source.node_id == request.target.node_id)
            or not request.source.node_id and not request.target.node_id
            and request.source.label.casefold() == request.target.label.casefold()):
        refuse("Choose two different identities.")
    graph = authoring_identities(
        InspectionScope(managed_world_id=request.world_id, scope_mode="world"),
        principal,
    )
    nodes = graph["identities"]
    for endpoint in (request.source, request.target):
        if endpoint.node_id:
            matches = [n for n in nodes if n["node_id"] == endpoint.node_id]
            if len(matches) != 1 or not matches[0]["selectable"] or matches[0]["label"] != endpoint.label or matches[0]["kind"] != endpoint.kind:
                refuse("A selected identity changed or is outside this World. Review its identity again.")
        elif any(endpoint.label.casefold() in {n["label"].casefold(), *(a.casefold() for a in n["aliases"])} for n in nodes):
            refuse("That name or alias already exists. Choose the existing World identity.")
    return body, start


def relationship_request(root: Path, request: DocumentRelationshipRequest, principal: NativeGraphPrincipal) -> GraphObjectAuthoringPrepareRequest:
    """Build the classic request for a retained classic review."""
    root = artifact_data_root(root)
    body, start = _validate_relationship_review(root, request, principal)
    selector = request.document_source

    def refuse(message):
        raise GraphObjectAuthoringError(message, code="relationship_review_invalid", status_code=409)

    source = resolve_graph_document_source(root, selector, world_id=request.world_id, campaign_id=request.world_id)
    index = source.source_span_index
    first = body.count("\n", 0, start) + 1
    last = body.count("\n", 0, start + len(request.quote) - 1) + 1
    spans = [s for s in index["spans"] if s["start_line"] <= first and s["end_line"] >= last]
    if len(spans) != 1:
        refuse("Select a passage within one saved source block.")
    selection = {"selectionKind": "text_span", "selectedText": request.quote,
        "normalizedSelectedText": request.quote, "sourceSpanRefId": spans[0]["source_span_id"]}
    visibility = {"visibility": "gm_private", "revealState": "unrevealed"}
    shared = {"selection": selection, "visibility": visibility, "graphScopes": ["campaign_memory_graph"],
        "status": "staged_local", "provenancePreview": {"operatorNote": "Explicit saved-page relationship review"}}
    proposals = []
    def ref(endpoint, key):
        if endpoint.node_id:
            return {"refKind": "existing_graph_node", "nodeId": endpoint.node_id, "label": endpoint.label, "kind": endpoint.kind}
        proposals.append({**shared, "localProposalId": key, "proposalKind": "object",
            "objectRef": {"label": endpoint.label, "kind": endpoint.kind, "aliases": [], "summary": ""}})
        return {"refKind": "local_proposal", "localProposalId": key, "label": endpoint.label, "kind": endpoint.kind}
    from_ref, to_ref = ref(request.source, "source"), ref(request.target, "target")
    proposals.append({**shared, "localProposalId": "relationship", "proposalKind": "relationship",
        "sourceObjectRef": from_ref, "targetObjectRef": to_ref, "relationshipType": request.predicate,
        # The existing native writer retains labels and source evidence, not the
        # proposal summary. Keep reviewed temporal context in its durable label.
        "relationshipLabel": request.label + " — " + request.context, "summary": request.context, "direction": "directed"})
    return GraphObjectAuthoringPrepareRequest(worldId=request.world_id, campaignId=request.world_id,
        documentSource=selector, proposals=proposals)


def native_relationship_operation(request, source, target, *, predicate, evidence_ref_id):
    """Build the WorldKeeper operation for the reviewed relationship."""
    from worldkeeper.application import contracts as wk
    from apps.live_control_server.integrations.dungeonmind.native_registry_source import GM_LABEL

    return wk.CreateRelationship(
        client_op_id="relationship",
        source=source,
        predicate=predicate,
        target=target,
        metadata=wk.AssertionMetadata(
            scope=(),
            visibility=wk.Visibility("labels_any", (GM_LABEL,)),
            epistemic_basis="asserted",
            claim_mode="dungeonbuddy.claim:fact",
            standing="established",
            evidence_ref_ids=(evidence_ref_id,),
            temporal_scope=wk.TemporalScope(kind="unknown"),
            domain_metadata=(wk.DomainMetadata.from_json(
                "dungeonbuddy.domain_metadata:world_context_v1",
                {"relationship_label": request.label, "relationship_context": request.context},
            ),),
        ),
    )


def native_relationship_intent(
    request: DocumentRelationshipRequest,
    *,
    space_id: str,
    predicate: str,
    evidence_ref_id: str,
):
    """Translate the reviewed endpoints into one native change."""
    from dataclasses import replace
    from worldkeeper.application import contracts as wk

    operations = []
    refs = []
    for key, endpoint in (("source", request.source), ("target", request.target)):
        refs.append(wk.DurableObjectRef(endpoint.node_id) if endpoint.node_id else wk.ResultOf(key))
    relationship = native_relationship_operation(
        request, *refs, predicate=predicate, evidence_ref_id=evidence_ref_id,
    )
    identity_metadata = replace(relationship.metadata, domain_metadata=())
    for key, endpoint in (("source", request.source), ("target", request.target)):
        if endpoint.node_id:
            continue
        operations.append(wk.CreateObject(key, (
            wk.CreateFact(f"{key}.name", "dnd5e:name",
                          wk.LiteralFactValue(endpoint.label), identity_metadata),
            wk.CreateFact(f"{key}.kind", "dnd5e:classification",
                          wk.TermRefFactValue(f"dnd5e:{endpoint.kind}"), identity_metadata),
        )))
    operations.append(relationship)
    return wk.WorldChangeIntent(space_id, "dungeonbuddy.build.relationship", tuple(operations))


def native_relationship_evidence_request(
    root: Path, request: DocumentRelationshipRequest, *, admission, context, operation_id, created_at
):
    """Bind one exact saved passage to its admitted native source."""
    from dungeonmind.contracts.vnext.native_source import NativeSourceEvidenceExtensionV1

    snapshot, _, span = resolve_reviewed_passage(root, request)
    if (
        admission.state != "admitted"
        or admission.document_id != snapshot.record.document_id
        or admission.world_id != request.world_id
        or admission.space_id != context["space_id"]
        or admission.body_sha256 != snapshot.content_sha256
    ):
        raise GraphObjectAuthoringError(
            "The reviewed page does not match its native source admission.",
            code="relationship_source_unavailable",
            status_code=409,
        )
    return NativeSourceEvidenceExtensionV1(
        space_id=admission.space_id,
        extension_id=operation_id,
        original_admission_id=admission.admission_id,
        source_artifact_id=admission.source_artifact_id,
        source_revision_id=admission.source_revision_id,
        expected_body_sha256=admission.body_sha256,
        expected_parent_revision_id=context["revision_id"],
        expected_source_authority_epoch=context["source_epoch"],
        created_at=created_at,
        spans=[{"client_ref": "relationship", "evidence_role": "support", **span}],
    )


def prepare_native_relationship(
    request: DocumentRelationshipRequest,
    *,
    repository,
    context,
    operation_id: str,
    predicate: str,
    evidence_ref_id: str,
    prepared_at,
    preview_evidence=None,
):
    """Prepare the reviewed change against the graph head after evidence admission."""
    from apps.live_control_server.integrations.dungeonmind import native_registry_source
    from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer

    space_id = context["space_id"]
    parent_id = context["revision_id"]
    domain, profile = native_registry_source.descriptors(repository, space_id, parent_id)
    desired = native_relationship_intent(
        request, space_id=space_id, predicate=predicate, evidence_ref_id=evidence_ref_id,
    )
    from dataclasses import replace
    from worldkeeper.application.authority import PreparationEvidenceWitness
    from worldkeeper.application.preparation import WorldChangePreparer
    from worldkeeper.integrations.dungeonmind.vnext_prepare import (
        DungeonMindVNextPreparationAuthority,
    )

    class PreviewAuthority(DungeonMindVNextPreparationAuthority):
        def read_current_space(self, space_id):
            witness = super().read_current_space(space_id)
            if witness is None or preview_evidence is None:
                return witness
            evidence = PreparationEvidenceWitness(
                evidence_ref_id=preview_evidence.evidence_ref_id,
                source_artifact_id=preview_evidence.source_artifact_id,
                source_revision_id=preview_evidence.source_revision_id,
                evidence_role=preview_evidence.evidence_role,
                locator=None, uri=None, source_locator=None, line_ref=None,
                source_span_ref_id=preview_evidence.source_span_ref_id,
            )
            return replace(witness, evidence_witnesses=(*witness.evidence_witnesses, evidence))

    prepared = WorldChangePreparer(
        authority=PreviewAuthority(repository), domain_contract=domain,
        semantic_profile=profile, clock=lambda: prepared_at,
        prepared_id_factory=lambda: operation_id,
    ).prepare_change(desired)
    try:
        registry_standing_consumer.verify_prepared_parent(prepared, context)
    except ValueError as exc:
        raise GraphObjectAuthoringError(
            "The native graph changed during relationship preparation. Review the change again.",
            code="relationship_review_invalid",
            status_code=409,
        ) from exc
    if prepared.prepared_operations != desired.operations:
        raise GraphObjectAuthoringError(
            "The native graph changed during relationship preparation. Review the change again.",
            code="relationship_review_invalid",
            status_code=409,
        )
    return prepared


def seal_native_relationship_review(request, prepared, *, binding, principal, extension):
    """Seal the exact prepared change for the operator who reviewed it."""
    from datetime import timedelta
    from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer
    from .graph_object_authoring_prepare import sign_publication_intent

    encoded = {"change": registry_standing_consumer.encode_prepared(prepared),
               "extension": extension.model_dump(mode="json")}
    return {
        "prepared": encoded,
        "confirm_token": sign_publication_intent({
            "purpose": "native_document_relationship",
            "principal": principal.subject,
            "binding": binding,
            "request_digest": registry_standing_consumer.digest(request.model_dump(mode="json")),
            "prepared_digest": registry_standing_consumer.digest(encoded),
            "expires_at": (prepared.prepared_at + timedelta(hours=1)).isoformat(),
        }),
    }


def confirm_native_relationship(root, request, encoded, token, principal):
    from dungeonmind.application.vnext import publish_native_source_evidence_extension
    from dungeonmind.contracts.vnext.native_source import GovernedNativeSourceEvidenceExtensionV1
    from worldkeeper.integrations.dungeonmind.vnext_prepare import compile_prepared_change_to_dungeonmind

    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer as transport
    from .agent_graph_auth import require_native_graph_gm
    from .graph_object_authoring_prepare import decode_publication_intent

    require_native_graph_gm(principal)
    signed = decode_publication_intent(token, allow_expired_recovery=True)
    bound = native.binding(request.world_id)
    if (
        signed.get("purpose") != "native_document_relationship"
        or signed.get("principal") != principal.subject
        or signed.get("binding") != bound
        or signed.get("request_digest") != transport.digest(request.model_dump(mode="json"))
        or signed.get("prepared_digest") != transport.digest(encoded)
    ):
        raise GraphObjectAuthoringError(
            "The relationship confirmation differs from the saved review.",
            code="confirmation_invalid", status_code=409,
        )
    prepared = transport.decode_prepared(encoded["change"])
    space = bound["native_world_id"]
    operation_id = prepared.dungeonmind_publication_id
    repository = native.repository()
    if repository.get_publication_receipt(space, operation_id) is None:
        decode_publication_intent(token)
        resolve_reviewed_passage(root, request)
        context, access = native.access_context(repository, space)
        transport.verify_prepared_parent(prepared, context)
    plan = compile_prepared_change_to_dungeonmind(prepared)
    extension = GovernedNativeSourceEvidenceExtensionV1.model_validate({
        **encoded["extension"],
        "contribution": plan.prospective_contribution,
        "dispositions": list(plan.dispositions),
    })
    receipt = publish_native_source_evidence_extension(
        repository=repository, request=extension, domain_contract=plan.domain_contract,
        semantic_profile=plan.semantic_profile,
        audience_labels=(native.GM_LABEL, native.PLAYER_LABEL),
    )
    return {
        "child_revision_id": receipt.publication_receipt.published_revision_id,
        "dungeonmind_publication_id": receipt.extension_id,
    }


def prepare_reviewed_native_relationship(
    root: Path, request: DocumentRelationshipRequest, principal: NativeGraphPrincipal, *,
    operation_id: str,
):
    from datetime import UTC, datetime

    from dungeonmind.application.vnext import preview_native_source_evidence_extension
    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import (
        NativeWorldSourceAdmissionError,
        get_native_world_source_status,
    )
    from .agent_graph_auth import require_native_graph_gm
    from .native_graph_explorer import NativeGraphExplorerError, _native_predicate

    require_native_graph_gm(principal)
    root = artifact_data_root(root)
    body, start = _validate_relationship_review(root, request, principal)
    from .graph_document_source import build_source_span_index_for_text, source_span_index_to_dict

    digest = request.document_source.content_sha256
    index = source_span_index_to_dict(build_source_span_index_for_text(
        source_artifact_id=f"sha256:{digest}", content_sha256=digest, text=body,
    ))
    first = body.count("\n", 0, start) + 1
    last = body.count("\n", 0, start + len(request.quote) - 1) + 1
    if sum(span["start_line"] <= first and span["end_line"] >= last for span in index["spans"]) != 1:
        raise GraphObjectAuthoringError(
            "Select a passage within one saved source block.",
            code="relationship_review_invalid", status_code=409,
        )
    bound = native.binding(request.world_id)
    space = bound["native_world_id"]
    repo = native.repository()
    head = repo.get_head(space)
    if head is None:
        raise GraphObjectAuthoringError(
            "The native World has no graph head.",
            code="relationship_review_invalid", status_code=409,
        )
    _, profile = native.descriptors(repo, space, head.head_revision_id)
    try:
        predicate = _native_predicate(request.predicate, profile)
        selector = request.document_source
        admission = get_native_world_source_status(
            root, selector.document_id, expected_revision=selector.revision,
        )
    except NativeGraphExplorerError as exc:
        raise GraphObjectAuthoringError(str(exc), code=exc.code, status_code=exc.status) from exc
    except NativeWorldSourceAdmissionError as exc:
        raise GraphObjectAuthoringError(
            str(exc), code=exc.code, status_code=exc.status_code,
        ) from exc
    context, _ = native.access_context(repo, space)
    now = datetime.now(UTC)
    extension = native_relationship_evidence_request(
        root, request, admission=admission, context=context,
        operation_id=operation_id, created_at=now,
    )
    domain, profile = native.descriptors(repo, space, context["revision_id"])
    evidence, = preview_native_source_evidence_extension(
        repository=repo, request=extension, domain_contract=domain, semantic_profile=profile,
        audience_labels=(native.GM_LABEL, native.PLAYER_LABEL),
    )
    prepared = prepare_native_relationship(
        request, repository=repo, context=context, operation_id=operation_id,
        predicate=predicate, evidence_ref_id=evidence.evidence_ref_id, prepared_at=now, preview_evidence=evidence,
    )
    if native.binding(request.world_id) != bound:
        raise GraphObjectAuthoringError(
            "The World binding changed during relationship preparation.",
            code="relationship_review_invalid", status_code=409,
        )
    return seal_native_relationship_review(request, prepared, binding=bound, principal=principal, extension=extension)
