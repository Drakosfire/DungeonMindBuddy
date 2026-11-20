"""Source-backed manual authoring through public atomic WK/Core composition."""

from dataclasses import asdict, replace
from datetime import UTC, datetime
from hashlib import sha256
import hmac
import json

from dungeonmind.domain.errors import DungeonMindError
from dungeonmind.domain.canonical import canonical_sha256
from fastapi import HTTPException

from dungeonmind.application.vnext import (
    get_native_source_publication_support,
    open_admitted_native_text,
    preview_native_source_publication_evidence,
    publish_governed_native_source_publication,
    recover_governed_native_source_publication,
)
from dungeonmind.contracts.vnext.native_source_publication import (
    GovernedNativeSourcePublicationV1,
    NativeSourcePublicationBasisV1,
)
from worldkeeper.application import contracts as wk
from worldkeeper.application.authority import PreparationEvidenceWitness
from worldkeeper.application.preparation import WorldChangePreparer
from worldkeeper.integrations.dungeonmind import compile_prepared_change_to_dungeonmind
from worldkeeper.integrations.dungeonmind.vnext_prepare import (
    DungeonMindVNextPreparationAuthority,
)

from application_state.source import service as sources
from application_state.content import pages
from apps.live_control_server import config
from apps.live_control_server.integrations.dungeonmind import (
    native_registry_source as native,
)
from apps.live_control_server.integrations.dungeonmind import (
    assertion_qualification as mapping,
)
from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import (
    get_native_world_source_status,
)
from apps.live_control_server.models.native_manual_knowledge import (
    ManualConfirmRequest,
    ManualContextRequest,
    ManualObject,
    ManualPlanContent,
    ManualPrepareRequest,
    ManualSource,
    SignedManualPlan,
)
from apps.live_control_server.models.native_graph_inspection import InspectionScope
from apps.live_control_server.services.agent_graph_auth import require_native_graph_gm
from apps.live_control_server.services.graph_object_authoring_prepare import (
    PREPARE_TTL,
    _prepare_binding_key,
    sign_publication_intent,
)
from apps.live_control_server.services.graph_run_registry import (
    get_extraction_run,
    load_reviewable_extraction_data,
)
from apps.live_control_server.services.hosted_native_graph_access import (
    require_explorer_access,
)
from apps.live_control_server.services.native_graph_inspection import (
    authoring_identities,
)
from apps.live_control_server.services.source_artifact_registry import (
    get_source_artifact,
)
from graph_memory.vnext.domain_runtime import GM_LABEL, resolve_dungeonbuddy_descriptors

TARGET = mapping.CONNECTED_PLACE_OPERATION_V7_TARGET


class ManualOutcomeUnknown(RuntimeError):
    code = "manual_publication_outcome_unknown"
    status_code = 503


class ManualRefused(ValueError):
    def __init__(self, code, *, status_code=409):
        self.code, self.status_code = code, status_code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise ManualRefused(code)


def _binding(principal, world, expected=None):
    require_native_graph_gm(principal)
    require_explorer_access(principal, world)
    bound = native.binding(world)
    if expected is not None:
        _require(
            (bound["native_world_id"], bound["binding_version"])
            == (expected.native_world_id, expected.binding_version),
            "manual_binding_changed",
        )
    return bound


def _source(selector, bound):
    """Join immutable APP owners; never register, admit, or rebuild an index."""
    root = config.artifact_data_root()
    # Scope metadata first. These public owners never select body/component bytes.
    page = pages.get_page(
        str(selector.document_id), world_id=selector.managed_world_id
    ).page
    _require(
        str(page.work_object_id) == str(selector.document_id)
        and page.world_id == selector.managed_world_id
        and page.campaign_id in (None, "", selector.managed_world_id)
        and page.status == "active"
        and page.current_revision_id is not None
        and page.object_revision == selector.document_revision,
        "manual_document_changed",
    )
    selected_run = get_extraction_run(str(selector.run_id))
    _require(
        str(selected_run.run_id) == str(selector.run_id)
        and selected_run.revision == selector.run_revision,
        "manual_run_changed",
    )
    _require(
        selected_run.source_domain == "worldbuilding"
        and selected_run.campaign_id in (None, "", selector.managed_world_id)
        and selected_run.session_id is None,
        "manual_run_source_mismatch",
    )
    selected_artifact = get_source_artifact(selected_run.source_artifact_id)
    _require(
        selected_artifact.world_id == selector.managed_world_id
        and selected_artifact.source_domain == "worldbuilding"
        and selected_artifact.workspace_document_id == str(selector.document_id)
        and selected_artifact.workspace_document_revision == selector.document_revision
        and selected_artifact.campaign_id == selected_run.campaign_id
        and selected_artifact.session_id is None,
        "manual_run_source_mismatch",
    )
    _require(
        native.read_repository().get_head(bound["native_world_id"]) is not None,
        "manual_head_missing",
    )
    # This public Page owner rechecks World/kind inside the same repeatable-read
    # transaction that loads its committed revision. No unscoped fallback.
    doc = pages.committed_page(
        str(selector.document_id), world_id=selector.managed_world_id
    )
    _require(
        doc.revision is not None
        and doc.page.object_revision == selector.document_revision,
        "manual_document_changed",
    )
    data = load_reviewable_extraction_data(root, str(selector.run_id))
    run, artifact = data.run, data.source_artifact
    _require(
        run == selected_run and artifact == selected_artifact,
        "manual_run_source_mismatch",
    )
    _require(doc.revision.content_sha256 == selector.body_sha256, "manual_body_changed")
    body = doc.revision.markdown.encode("utf-8")
    _require(
        data.source_bytes == body
        and sha256(body).hexdigest() == selector.body_sha256
        and artifact.content_sha256 == selector.body_sha256,
        "manual_body_changed",
    )
    expected_uuid = (
        selector.app_source_revision_id if isinstance(selector, ManualSource) else None
    )
    source = sources.get_source_markdown(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=selector.body_sha256,
        source_revision_id=expected_uuid,
    )
    _require(
        source is not None
        and source.markdown.encode("utf-8") == body
        and source.source_domain == "worldbuilding"
        and source.world_id == selector.managed_world_id
        and source.campaign_id == artifact.campaign_id
        and source.session_id is None
        and source.media_type == "text/markdown"
        and source.encoding == "utf-8",
        "manual_app_source_mismatch",
    )
    sealed = ManualSource(
        managed_world_id=selector.managed_world_id,
        native_world_id=bound["native_world_id"],
        binding_version=bound["binding_version"],
        document_id=selector.document_id,
        document_revision=selector.document_revision,
        body_sha256=selector.body_sha256,
        run_id=selector.run_id,
        run_revision=selector.run_revision,
        app_source_artifact_id=artifact.source_artifact_id,
        app_source_revision_id=source.source_revision_id,
        span_index_sha256=sha256(data.span_bytes).hexdigest(),
    )
    if isinstance(selector, ManualSource):
        _require(sealed == selector, "manual_source_coordinates_changed")
    admitted = get_native_world_source_status(
        root, str(selector.document_id), expected_revision=selector.document_revision
    )
    _require(admitted.state == "admitted", "manual_source_not_admitted")
    _require(
        (admitted.world_id, admitted.space_id, admitted.body_sha256)
        == (selector.managed_world_id, bound["native_world_id"], selector.body_sha256)
        and admitted.source_artifact_id
        and admitted.source_revision_id,
        "manual_admission_mismatch",
    )
    return sealed, body, data, admitted


def _access(repo, source):
    _require(repo.get_head(source.native_world_id) is not None, "manual_head_missing")
    coords, access = native.access_context(repo, source.native_world_id)
    return coords, access


def _catalog():
    return dict(
        kinds=dict(TARGET.buddy_to_dm_kind),
        predicates={
            label: {"term": term, "reverseEndpoints": reverse}
            for label in sorted(
                set(mapping._DIRECT_PREDICATE_MAP)
                | set(mapping._RENAME_PREDICATE_MAP)
                | set(mapping._REVERSE_ENDPOINT_PREDICATE_MAP)
                | set(TARGET.predicate_map_additions or {})
            )
            for term, reverse in [
                mapping.resolve_buddy_predicate_mapping_v4(label, target=TARGET)
            ]
        },
    )


def context(body, principal):
    body = ManualContextRequest.model_validate(body.model_dump(mode="json"))
    bound = _binding(principal, body.managed_world_id)
    sealed, raw, data, admitted = _source(body, bound)
    repo = native.read_repository()
    coords, access = _access(repo, sealed)
    parsed = access.parsed
    domain, profile = resolve_dungeonbuddy_descriptors(
        domain_ref=parsed.domain_contract_ref, profile_ref=parsed.semantic_profile_ref
    )
    # Resolution is exact; a revision number alone never grants capabilities.
    from graph_memory.vnext.domain_runtime import dungeonbuddy_dnd5e_manual_profile

    manual = profile == dungeonbuddy_dnd5e_manual_profile()
    spans = []
    lines = raw.decode("utf-8").splitlines(keepends=True)
    for span in data.span_index.spans:
        _require(
            1 <= span.start_line <= span.end_line <= len(lines),
            "manual_span_index_invalid",
        )
        start = len("".join(lines[: span.start_line - 1]).encode("utf-8"))
        end = len("".join(lines[: span.end_line]).encode("utf-8"))
        spans.append(
            dict(
                sourceSpanRefId=span.source_span_id,
                startByte=start,
                endByte=end,
                sliceSha256=sha256(raw[start:end]).hexdigest(),
            )
        )
    final, _, _, final_admitted = _source(sealed, bound)
    _require(final == sealed and final_admitted == admitted, "manual_source_changed")
    final_head = repo.get_head(sealed.native_world_id)
    _require(
        final_head is not None
        and final_head.head_revision_id == parsed.revision_id
        and repo.open_native_source_view(sealed.native_world_id).epoch
        == coords["source_epoch"],
        "manual_authority_changed",
    )
    _binding(principal, body.managed_world_id, sealed)
    return dict(
        schema="dmb_native_manual_context_result_v1",
        source=sealed.model_dump(mode="json", by_alias=True),
        nativeSource=admitted.model_dump(mode="json"),
        parentRevisionId=parsed.revision_id,
        sourceAuthorityEpoch=coords["source_epoch"],
        domainContractRef=parsed.domain_contract_ref,
        semanticProfileRef=parsed.semantic_profile_ref,
        manualCapability=manual,
        transitionRequired=not manual,
        spans=spans,
        **_catalog(),
    )


def _witness(raw, data, witness):
    spans = [
        s
        for s in data.span_index.spans
        if s.source_span_id == witness.source_span_ref_id
    ]
    _require(len(spans) == 1, "manual_span_membership_invalid")
    span = spans[0]
    lines = raw.decode("utf-8").splitlines(keepends=True)
    _require(
        1 <= span.start_line <= span.end_line <= len(lines), "manual_span_index_invalid"
    )
    start = len("".join(lines[: span.start_line - 1]).encode("utf-8"))
    end = len("".join(lines[: span.end_line]).encode("utf-8"))
    _require(
        start <= witness.start_byte < witness.end_byte <= end,
        "manual_witness_outside_span",
    )
    selected = raw[witness.start_byte : witness.end_byte]
    try:
        selected.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ManualRefused("manual_witness_utf8_invalid") from exc
    _require(
        sha256(selected).hexdigest() == witness.slice_sha256,
        "manual_witness_digest_changed",
    )


def _basis(repo, body, admitted, access):
    w = body.witness
    matching = []
    for e in access.parsed.evidence_by_id.values():
        if (e.source_artifact_id, e.source_revision_id) != (
            admitted.source_artifact_id,
            admitted.source_revision_id,
        ):
            continue
        opened = open_admitted_native_text(access, e.evidence_ref_id)
        if opened.status != "available":
            continue
        if (opened.span_start_byte, opened.span_end_byte) == (w.start_byte, w.end_byte):
            _require(e.evidence_role == "support", "manual_context_interval_collision")
            ref = get_native_source_publication_support(
                repository=repo,
                space_id=body.source.native_world_id,
                source_revision_id=admitted.source_revision_id,
                span_id=e.source_span_ref_id,
            )
            _require(
                ref is not None and ref.proof.slice_sha256 == w.slice_sha256,
                "manual_support_mismatch",
            )
            matching.append(ref)
    _require(len(matching) <= 1, "manual_support_ambiguous")
    evidence = (
        dict(mode="existing_support", support=matching)
        if matching
        else dict(
            mode="new_intervals",
            spans=[
                dict(
                    client_ref="manual-witness",
                    evidence_role="support",
                    start_byte=w.start_byte,
                    end_byte=w.end_byte,
                    expected_slice_sha256=w.slice_sha256,
                )
            ],
        )
    )
    return NativeSourcePublicationBasisV1(
        space_id=body.source.native_world_id,
        publication_id=str(body.operation_id),
        original_admission_id=admitted.admission_id,
        source_artifact_id=admitted.source_artifact_id,
        source_revision_id=admitted.source_revision_id,
        expected_body_sha256=body.source.body_sha256,
        expected_parent_revision_id=body.expected_parent_revision_id,
        expected_source_authority_epoch=body.expected_source_authority_epoch,
        created_at=body.created_at,
        evidence=evidence,
    )


def _operations(body, evidence, principal):
    op = body.operation
    ids = tuple(e.evidence_ref_id for e in evidence)

    def metadata(payload):
        return wk.AssertionMetadata(
            scope=(),
            visibility=wk.Visibility("labels_any", (GM_LABEL,)),
            epistemic_basis="asserted",
            claim_mode="dungeonbuddy.claim:fact",
            standing="established",
            evidence_ref_ids=ids,
            temporal_scope=wk.TemporalScope(kind="unknown"),
            domain_metadata=(
                wk.DomainMetadata.from_json(
                    "dungeonbuddy.domain_metadata:world_context_v1", payload
                ),
            ),
        )

    if isinstance(op, ManualObject):
        _require(op.object_kind in TARGET.buddy_to_dm_kind, "manual_kind_unsupported")
        role = (op.role.strip() if op.role is not None else "") or op.object_kind
        meta = metadata(dict(role=role))
        facts = [
            wk.CreateFact(
                "classification",
                "dnd5e:classification",
                wk.TermRefFactValue(TARGET.buddy_to_dm_kind[op.object_kind]),
                meta,
            ),
            wk.CreateFact(
                "name", "dnd5e:name", wk.LiteralFactValue(op.name.strip()), meta
            ),
        ]
        if op.description is not None and op.description.strip():
            facts.append(
                wk.CreateFact(
                    "summary",
                    "dnd5e:summary",
                    wk.LiteralFactValue(op.description.strip()),
                    meta,
                )
            )
        aliases = [a.strip() for a in op.aliases if a.strip()] or [op.name.strip()]
        # Preserve producer spellings; exact duplicates need no duplicate identity record.
        aliases = list(dict.fromkeys(aliases))
        return (wk.CreateObject("object", tuple(facts)),), aliases
    allowed = _catalog()["predicates"]
    _require(op.predicate in allowed, "manual_predicate_unsupported")
    rows = authoring_identities(
        InspectionScope(
            managed_world_id=body.source.managed_world_id, scope_mode="world"
        ),
        principal,
    )["identities"]
    for endpoint in (op.source, op.target):
        found = [r for r in rows if r["node_id"] == endpoint.entity_id]
        _require(
            len(found) == 1
            and found[0]["selectable"]
            and (found[0]["label"], found[0]["kind"])
            == (endpoint.name, endpoint.object_kind),
            "manual_endpoint_changed",
        )
    reason = mapping.edge_endpoint_kind_admission_reason(
        buddy_predicate=op.predicate,
        from_buddy_kind=op.source.object_kind,
        to_buddy_kind=op.target.object_kind,
        target=TARGET,
        vocabulary=TARGET.world_object_loader(),
    )
    _require(reason is None, "manual_endpoint_kind_unsupported")
    term, reverse = mapping.resolve_buddy_predicate_mapping_v4(
        op.predicate, target=TARGET
    )
    a, z = (op.target, op.source) if reverse else (op.source, op.target)
    meta = metadata(
        dict(
            relationship_label=(op.label or "").strip(),
            relationship_context=(op.description or "").strip(),
        )
    )
    return (
        wk.CreateRelationship(
            "relationship",
            wk.DurableObjectRef(a.entity_id),
            term,
            wk.DurableObjectRef(z.entity_id),
            meta,
        ),
    ), []


def _compose(repo, body, basis, domain, profile, principal):
    evidence = preview_native_source_publication_evidence(
        repository=repo,
        request=basis,
        domain_contract=domain,
        semantic_profile=profile,
        audience_labels=(GM_LABEL,),
    )
    operations, alias_texts = _operations(body, evidence, principal)

    class PreviewAuthority(DungeonMindVNextPreparationAuthority):
        def read_current_space(self, space):
            current = super().read_current_space(space)
            if basis.evidence.mode != "new_intervals":
                return current
            witnesses = tuple(
                PreparationEvidenceWitness(
                    evidence_ref_id=e.evidence_ref_id,
                    source_artifact_id=e.source_artifact_id,
                    source_revision_id=e.source_revision_id,
                    evidence_role=e.evidence_role,
                    locator=None,
                    uri=None,
                    source_locator=None,
                    line_ref=None,
                    source_span_ref_id=e.source_span_ref_id,
                )
                for e in evidence
            )
            return replace(
                current, evidence_witnesses=(*current.evidence_witnesses, *witnesses)
            )

    prepared = WorldChangePreparer(
        authority=PreviewAuthority(repo),
        domain_contract=domain,
        semantic_profile=profile,
        clock=lambda: body.created_at,
        prepared_id_factory=lambda: str(body.operation_id),
    ).prepare_change(
        wk.WorldChangeIntent(
            body.source.native_world_id, "Reviewed manual knowledge", operations
        )
    )
    _require(
        prepared.prepared_operations == operations, "manual_preparation_incomplete"
    )
    compiled = compile_prepared_change_to_dungeonmind(prepared)
    aliases = [
        dict(
            item_id=f"alias:{i}",
            alias_id=f"{body.operation_id}:alias:{i}",
            entity=dict(kind="result_of", client_op_id="object"),
            alias_text=text,
            evidence_ref_ids=[e.evidence_ref_id for e in evidence],
            standing="established",
        )
        for i, text in enumerate(alias_texts)
    ]
    from fastapi.encoders import jsonable_encoder
    from dungeonmind.contracts.vnext.domain import DomainMetadataEntry

    prepared_json = json.dumps(
        jsonable_encoder(prepared), sort_keys=True, separators=(",", ":")
    )
    original = DomainMetadataEntry(
        schema_term="dungeonbuddy.domain_metadata:world_context_v1",
        payload={
            "manual_review_sha256": canonical_sha256(
                body.model_dump(mode="json", by_alias=True)
            ),
            "prepared_by": principal.subject,
            "prepared_change_sha256": sha256(prepared_json.encode()).hexdigest(),
        },
    )
    contribution = compiled.prospective_contribution.model_copy(
        update={
            "diagnostics": [*compiled.prospective_contribution.diagnostics, original]
        }
    )
    publication = GovernedNativeSourcePublicationV1.model_validate(
        {
            **basis.model_dump(mode="json"),
            "schema_version": "dm_governed_native_source_publication_v1",
            "contribution": contribution.model_dump(mode="json"),
            "aliases": aliases,
            "dispositions": [
                *[d.model_dump(mode="json") for d in compiled.dispositions],
                *[dict(item_id=a["item_id"], disposition="accepted") for a in aliases],
            ],
        }
    )
    return publication, prepared_json


def prepare(body, principal):
    body = ManualPrepareRequest.model_validate(body.model_dump(mode="json"))
    bound = _binding(principal, body.source.managed_world_id, body.source)
    _prepare_binding_key()
    _require(
        body.created_at <= datetime.now(UTC) <= body.created_at + PREPARE_TTL,
        "manual_review_expired",
    )
    source, raw, data, admitted = _source(body.source, bound)
    repo = native.read_repository()
    _witness(raw, data, body.witness)
    coords, access = _access(repo, source)
    _require(
        access.parsed.revision_id == body.expected_parent_revision_id,
        "manual_parent_stale",
    )
    _require(
        coords["source_epoch"] == body.expected_source_authority_epoch,
        "manual_source_authority_stale",
    )
    domain, profile = resolve_dungeonbuddy_descriptors(
        domain_ref=access.parsed.domain_contract_ref,
        profile_ref=access.parsed.semantic_profile_ref,
    )
    from graph_memory.vnext.domain_runtime import dungeonbuddy_dnd5e_manual_profile

    _require(
        profile == dungeonbuddy_dnd5e_manual_profile(),
        "manual_profile_transition_required",
    )
    basis = _basis(repo, body, admitted, access)
    publication, prepared_json = _compose(repo, body, basis, domain, profile, principal)
    _source(body.source, bound)
    final_head = repo.get_head(source.native_world_id)
    _require(
        final_head is not None
        and final_head.head_revision_id == body.expected_parent_revision_id
        and repo.open_native_source_view(source.native_world_id).epoch
        == body.expected_source_authority_epoch,
        "manual_authority_changed",
    )
    _binding(principal, source.managed_world_id, source)
    plan = ManualPlanContent(
        review=body,
        publication=publication,
        prepared_change_json=prepared_json,
        domain_contract_ref=asdict(access.parsed.domain_contract_ref),
        semantic_profile_ref=asdict(access.parsed.semantic_profile_ref),
        prepared_by=principal.subject,
        expires_at=body.created_at + PREPARE_TTL,
    )
    return {
        "plan": SignedManualPlan(
            **plan.model_dump(),
            token=sign_publication_intent(plan.model_dump(mode="json", by_alias=True)),
        ).model_dump(mode="json", by_alias=True)
    }


def confirm(body, principal):
    body = ManualConfirmRequest.model_validate(body.model_dump(mode="json"))
    plan = body.plan
    source = plan.review.source
    bound = _binding(principal, source.managed_world_id, source)
    content = ManualPlanContent.model_validate(plan.model_dump(exclude={"token"}))
    _require(
        hmac.compare_digest(
            plan.token,
            sign_publication_intent(content.model_dump(mode="json", by_alias=True)),
        ),
        "manual_signature_invalid",
    )
    _require(plan.prepared_by == principal.subject, "manual_principal_changed")
    domain, profile = resolve_dungeonbuddy_descriptors(
        domain_ref=plan.domain_contract_ref, profile_ref=plan.semantic_profile_ref
    )
    repo = native.repository()
    recovered = recover_governed_native_source_publication(
        repository=repo,
        request=plan.publication,
        domain_contract=domain,
        semantic_profile=profile,
    )
    if recovered is not None:
        _binding(principal, source.managed_world_id, source)
        return dict(
            schema="dmb_native_manual_receipt_v1",
            recovered=True,
            receipt=recovered.model_dump(mode="json"),
        )
    _require(datetime.now(UTC) <= plan.expires_at, "manual_review_expired")
    _, raw, data, _ = _source(source, bound)
    _witness(raw, data, plan.review.witness)
    # Reconstruct preparation against exact original fences, including endpoint admission.
    fresh = prepare(plan.review, principal)
    _require(
        fresh["plan"] == plan.model_dump(mode="json", by_alias=True),
        "manual_preparation_changed",
    )

    class Guarded:
        denied = None

        def __getattr__(self, name):
            if self.denied is not None:
                raise self.denied
            return getattr(repo, name)

        def publish_governed_native_source_publication(self, **kwargs):
            try:
                _binding(principal, source.managed_world_id, source)
            except Exception as exc:
                self.denied = exc
                raise
            return repo.publish_governed_native_source_publication(**kwargs)

    guarded = Guarded()
    try:
        receipt = publish_governed_native_source_publication(
            repository=guarded,
            request=plan.publication,
            domain_contract=domain,
            semantic_profile=profile,
            audience_labels=(GM_LABEL,),
        )
    except Exception as exc:
        if guarded.denied is not None:
            raise guarded.denied from None
        if isinstance(exc, (DungeonMindError, HTTPException, ManualRefused)):
            raise
        # An actual writer transport failure may have committed. Resolve only
        # through privileged immutable proof after checking current host authority.
        _binding(principal, source.managed_world_id, source)
        recovered = recover_governed_native_source_publication(
            repository=repo,
            request=plan.publication,
            domain_contract=domain,
            semantic_profile=profile,
        )
        if recovered is None:
            raise ManualOutcomeUnknown("Retry the retained exact packet") from exc
        _binding(principal, source.managed_world_id, source)
        return dict(
            schema="dmb_native_manual_receipt_v1",
            recovered=True,
            receipt=recovered.model_dump(mode="json"),
        )
    _binding(principal, source.managed_world_id, source)
    return dict(
        schema="dmb_native_manual_receipt_v1",
        recovered=False,
        receipt=receipt.model_dump(mode="json"),
    )
