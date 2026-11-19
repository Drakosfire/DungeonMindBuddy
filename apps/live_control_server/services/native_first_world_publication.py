"""Native first-World orchestration over exact public Core operations.

Read-only review and immutable receipt recovery are deliberately separate from
current-source qualification. No stage may refresh a parent or invent a proof.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from dungeonmind.application.vnext.authority import verify_stored_revision
from dungeonmind.application.vnext.builder import build_parsed_knowledge_revision
from dungeonmind.application.vnext.materialization import decode_native_graph_payload
from dungeonmind.application.vnext.publication import get_publication_receipt
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext.domain import DomainContractRef
from dungeonmind.contracts.vnext.native_source import MAX_NATIVE_TEXT_SPANS
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.domain.errors import DungeonMindError, PersistenceIntegrityError, PersistenceUnavailableError

from apps.live_control_server import config
from apps.live_control_server.integrations.dungeonmind import native_world_source_admission as source_owner
from apps.live_control_server.models.native_first_world_compilation import FirstWorldNativeIntent
from apps.live_control_server.models.native_first_world_publication import (
    NATIVE_ENVELOPE_SCHEMA, NativeFirstWorldPlan, NativeFirstWorldPlanDraft,
    NativeFirstWorldPlanContent, NativeFirstWorldPrepareRequest, NativeFirstWorldSourceStage,
    NativeFirstWorldExistingBinding,
)
from apps.live_control_server.models.world_graph_contributions import compute_contribution_payload_sha256
from apps.live_control_server.services import first_world_graph_publication as legacy
from apps.live_control_server.services.extract_promote import ExtractPromoteError, _load_worldbuilding_publication_input
from apps.live_control_server.services.first_world_graph import (
    first_world_native_target, cross_check_workspace_lineage, materialize_first_world_plan,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    PREPARE_TTL, sign_publication_intent, decode_publication_intent,
)
from apps.live_control_server.services.native_first_world_compilation import compile_first_world_native_intent
from apps.live_control_server.services.promotable_ingest_run import PromotableIngestRunError, resolve_promotable_ingest_run
from apps.live_control_server.services.world_container_registry import (
    NativeGraphProvisioningRecord, get_world_container,
)
from graph_memory.vnext.domain_runtime import (
    DUNGEONBUDDY_DOMAIN_DIGEST, DUNGEONBUDDY_PROFILE_DIGEST,
    DUNGEONBUDDY_CUSTOM_PROFILE_DIGEST, dungeonbuddy_world_domain_contract,
    dungeonbuddy_dnd5e_semantic_profile, dungeonbuddy_dnd5e_custom_predicate_profile,
    resolve_dungeonbuddy_descriptors,
)
from graph_memory.worldbuilding_write_plan import WorldbuildingDispositionInput, WorldbuildingWritePlanError


def _refuse(code, message, *, status=409):
    raise ExtractPromoteError(message, code=code, status_code=status)


def _require(condition, code, message):
    if not condition:
        _refuse(code, message)


def _time(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        _refuse("native_first_world_invalid_time", "The reviewed timestamp has no timezone.")
    return result


def _authorize(authorize_world, world_id):
    if authorize_world is not None:
        authorize_world(world_id)


def _domain_ref():
    descriptor = dungeonbuddy_world_domain_contract()
    return DomainContractRef(domain_id=descriptor.domain_id, domain_revision=descriptor.domain_revision,
                             descriptor_sha256=DUNGEONBUDDY_DOMAIN_DIGEST)


def _profile_ref(custom=False):
    descriptor = dungeonbuddy_dnd5e_custom_predicate_profile() if custom else dungeonbuddy_dnd5e_semantic_profile()
    return SemanticProfileRef(profile_id=descriptor.profile_id, profile_revision=descriptor.profile_revision,
                              descriptor_sha256=DUNGEONBUDDY_CUSTOM_PROFILE_DIGEST if custom else DUNGEONBUDDY_PROFILE_DIGEST)


def _repository():
    # The existing owner supplies the configured adapter; there is no default DB.
    return source_owner._repository()


def _parsed(repository, space, revision_id):
    stored = repository.get_revision(space, revision_id)
    if stored is None:
        raise PersistenceIntegrityError("native first-World revision is missing")
    verify_stored_revision(stored)
    if stored.revision.space_id != space or stored.revision.revision_id != revision_id:
        raise PersistenceIntegrityError("native first-World revision identity drift")
    return build_parsed_knowledge_revision(stored.revision,
              decoded_content=decode_native_graph_payload(stored.graph_payload))


def _source_only(parsed):
    _require(not parsed.entities_by_id and not parsed.assertions_by_id and not parsed.aliases_by_id
             and parsed.migration_origin_ref is None, "world_already_initialized",
             "This native World already contains semantic Graph state.")
    domain, profile = resolve_dungeonbuddy_descriptors(domain_ref=parsed.domain_contract_ref,
                                                      profile_ref=parsed.semantic_profile_ref)
    _require(domain.domain_revision == "2" and profile.profile_revision in {"1", "2"},
             "native_first_world_profile_unsupported", "This native World has an unsupported first-World profile.")
    return domain, profile


def _history(repository, space, current, ancestor, *, source_only=False):
    seen = set()
    while True:
        if current in seen:
            raise PersistenceIntegrityError("native first-World ancestry cycle")
        seen.add(current)
        parsed = _parsed(repository, space, current)
        if source_only:
            _source_only(parsed)
        if current == ancestor:
            return parsed
        if parsed.parent_revision_id is None:
            raise PersistenceIntegrityError("native first-World head does not descend from its receipt")
        current = parsed.parent_revision_id


def _verify_genesis(repository, stage, space, head):
    receipt = get_publication_receipt(space, stage.genesis_initialization_id, repository=repository)
    if receipt is None:
        raise PersistenceIntegrityError("native first-World owner genesis receipt is missing")
    root = _history(repository, space, head, receipt.published_revision_id, source_only=True)
    if (root.parent_revision_id is not None or root.evidence_by_id
            or root.operation_ids != (stage.genesis_initialization_id,)
            or root.created_at != _time(stage.genesis_created_at)
            or root.domain_contract_ref.descriptor_sha256 != DUNGEONBUDDY_DOMAIN_DIGEST
            or root.semantic_profile_ref.descriptor_sha256 != DUNGEONBUDDY_PROFILE_DIGEST):
        raise PersistenceIntegrityError("native first-World owner genesis drift")
    return receipt


def _classic_state(space):
    # Read-only historical boundary. Never call preflight/initialize here.
    from apps.live_control_server.ports.world_graph_initialization_access import get_world_graph_initialization_authority
    return get_world_graph_initialization_authority(world_root=config.world_graph_root()).probe(space)


def _reservation(world_id, target, *, require_provisioning=False):
    record = get_world_container(world_id)
    binding = record.native_graph_binding
    _require(binding is not None and binding.native_world_id == target.native_world_id
             and binding.binding_version == target.binding_version
             and binding.provisioning_id == target.provisioning_id,
             "native_graph_binding_changed", "The World reservation changed after review.")
    if require_provisioning:
        _require(isinstance(binding, NativeGraphProvisioningRecord), "world_already_initialized",
                 "This World is no longer awaiting its first Graph publication.")
    return record


def decode_native_plan(plan: NativeFirstWorldPlan, *, principal_subject=None, allow_expired=True):
    """Signature/scope verification only; no run, source, receipt or database reads."""
    plan = NativeFirstWorldPlan.model_validate(plan.model_dump(mode="json", by_alias=True))
    from apps.live_control_server.services.graph_object_authoring_prepare import GraphObjectAuthoringError
    try:
        signed = decode_publication_intent(plan.token, allow_expired_recovery=allow_expired)
    except GraphObjectAuthoringError as exc:
        raise ExtractPromoteError(str(exc), code=exc.code, status_code=exc.status_code) from exc
    body = plan.model_dump(mode="json", by_alias=True, exclude={"token"})
    _require(signed.get("schema") == NATIVE_ENVELOPE_SCHEMA and signed.get("plan") == body
             and signed.get("expires_at") == plan.expires_at,
             "native_first_world_plan_invalid", "The request does not match its signed review.")
    without_digest = {k: v for k, v in body.items() if k != "planDigest"}
    _require(plan.plan_digest == "sha256:" + canonical_sha256(without_digest),
             "native_first_world_plan_invalid", "The reviewed plan commitment changed.")
    if principal_subject is not None:
        _require(principal_subject == plan.prepared_by, "native_first_world_principal_changed",
                 "The confirming principal does not match this review.")
    return plan


def _source_binding_matches(snapshot_binding, target, world_id, source_root):
    _require(snapshot_binding.managed_world_id == world_id
             and snapshot_binding.native_world_id == target.native_world_id
             and snapshot_binding.binding_version == target.binding_version
             and snapshot_binding.provisioning_id == target.provisioning_id
             and snapshot_binding.source_root_relpath == source_root,
             "native_graph_binding_changed", "The source no longer belongs to the reviewed reservation.")


def prepare_native_first_world(request: NativeFirstWorldPrepareRequest, *, principal_subject,
                               authorize_world=None, repository=None, now=None):
    """Read-only even when the source KnowledgeSpace does not yet exist."""
    _require(type(principal_subject) is str and bool(principal_subject.strip()),
             "native_first_world_principal_missing", "A current confirming principal is required.")
    resolved = resolve_promotable_ingest_run(request.run_id, root=config.repo_root())
    world = resolved.world_id or ""
    _authorize(authorize_world, world)
    data = _load_worldbuilding_publication_input(resolved, allow_gazetteer=False)
    target = first_world_native_target(config.repo_root(), world)
    record = _reservation(world, target, require_provisioning=True)
    lineage = cross_check_workspace_lineage(config.repo_root(), source_artifact_id=resolved.source_artifact_id,
                                           expected_world_id=world)
    source = source_owner._load_exact_snapshot(config.repo_root(), lineage.workspace_document_id,
                                               int(lineage.workspace_document_revision), lineage.content_sha256)
    snapshot, body, digest, admission_id, source_binding = source
    _source_binding_matches(source_binding, target, world, record.source_root_relpath)
    _require(data.source_prose.encode("utf-8") == body,
             "native_first_world_source_changed", "The reviewed extraction and committed document differ.")
    evidence_commitment = legacy._source_evidence_commitment(data.reviewed_assertions,
        source_prose=data.source_prose, span_index=data.span_index, source_artifact_id=resolved.source_artifact_id)
    materialized = materialize_first_world_plan(preview=data.preview, world_id=world, native_target=target,
        run_id=resolved.run_id, source_artifact_id=lineage.source_artifact_id,
        source_revision_id=lineage.source_revision_id, source_uri=resolved.sealed_source_uri,
        source_evidence_sha256=evidence_commitment, extraction_profile=data.profile_id,
        campaign_scope=lineage.campaign_scope, workspace_document_id=lineage.workspace_document_id,
        workspace_document_revision=lineage.workspace_document_revision,
        dispositions=[WorldbuildingDispositionInput(assertion_id=d.assertion_id, decision=d.decision,
                                                    target_node_id=None) for d in request.decisions])
    legacy._assert_materialized_evidence_matches_review(materialized, data.reviewed_assertions)
    intent = compile_first_world_native_intent(materialized.effect, world_id=world,
                                               source_text=data.source_prose, span_index=data.span_index)
    span_ids = {r["source_span_ref_id"] for r in intent.audit["source_requirements"]}
    _require(len(span_ids) <= MAX_NATIVE_TEXT_SPANS, "native_first_world_span_limit",
             "This review exceeds the supported exact-source span limit.")
    repo = repository if repository is not None else _repository()
    view = repo.open_native_source_view(target.native_world_id)
    epoch = view.epoch
    classic = _classic_state(target.native_world_id)
    _require(classic.state == "uninitialized", "native_first_world_historical_initialization",
             "This reservation has historical Graph state; it cannot be initialized again.")
    head = repo.get_head(target.native_world_id)
    parsed = _parsed(repo, target.native_world_id, head.head_revision_id) if head is not None else None
    if parsed is not None:
        _source_only(parsed)
    prior = repo.get_native_source_admission_receipt(target.native_world_id, admission_id)
    if prior is not None:
        _require(head is not None, "native_first_world_source_integrity", "Admission exists without its native head.")
        source_owner._verify_receipt_and_source(repository=repo, snapshot=snapshot, body_bytes=body,
            body_sha256=digest, admission_id=admission_id, receipt=prior,
            native_world_id=target.native_world_id, root=config.repo_root(), sealed_world_binding=source_binding)
    stamp = now if now is not None else datetime.now(UTC)
    _require(stamp.utcoffset() is not None, "native_first_world_invalid_time", "Preparation requires a timezone.")
    nonce = uuid4().hex
    operation = source_owner._stable_id("dmb-native-first-world", target.native_world_id, target.provisioning_id)
    _require(repo.get_prospective_publication(target.native_world_id, operation) is None,
             "native_first_world_reservation_claimed", "This reservation already has a publication; recover its original request.")
    _verify_source_events(repo, target.native_world_id, head)
    stage = NativeFirstWorldSourceStage(admission_state="admitted" if prior else "absent",
        admission_id=admission_id, admission_receipt_sha256=canonical_sha256(prior.model_dump(mode="json")) if prior else None,
        native_source_artifact_id=prior.source_artifact_id if prior else None,
        native_source_revision_id=prior.source_revision_id if prior else None,
        whole_document_evidence_ref_id=prior.bindings[0].evidence_ref_id if prior else None,
        document_id=snapshot.record.document_id, source_root_relpath=record.source_root_relpath,
        document_revision=snapshot.loaded_revision, document_updated_at=snapshot.record.updated_at,
        body_sha256=digest, origin=source_owner._origin(snapshot),
        genesis_initialization_id=source_owner._stable_id("dmb-world-genesis", target.native_world_id),
        genesis_created_at=record.created_at,
        head_revision_id=parsed.revision_id if parsed else None,
        head_profile_ref=SemanticProfileRef(profile_id=parsed.semantic_profile_ref.profile_id,
            profile_revision=parsed.semantic_profile_ref.profile_revision,
            descriptor_sha256=parsed.semantic_profile_ref.descriptor_sha256) if parsed else None,
        source_authority_epoch=epoch, extension_id=operation + ":evidence:" + nonce,
        profile_transition_id=operation + ":profile:" + nonce,
        existing_bindings=_existing_bindings(repo, parsed, prior, intent, view) if prior is not None else [])
    if head is not None:
        _verify_genesis(repo, stage, target.native_world_id, head.head_revision_id)
    custom = intent.audit["required_profile_revision"] == "2" or (parsed is not None and parsed.semantic_profile_ref.profile_revision == "2")
    draft = NativeFirstWorldPlanDraft(plan_id="native-first-world-plan:" + uuid4().hex,
        decision_digest=materialized.decision_digest, source_evidence_sha256=evidence_commitment,
        world_id=world, native_target=target, run_id=resolved.run_id, run_revision=resolved.data.run.revision,
        source_artifact_id=lineage.source_artifact_id, source_revision_id=lineage.source_revision_id,
        workspace_document_id=lineage.workspace_document_id, workspace_document_revision=lineage.workspace_document_revision,
        campaign_scope=world, extraction_profile=data.profile_id, accepted_assertion_ids=materialized.accepted_assertion_ids,
        rejected_assertion_ids=materialized.rejected_assertion_ids, contribution_id=materialized.contribution.contribution_id,
        contribution_payload_sha256=compute_contribution_payload_sha256(materialized.contribution),
        reviewed_effect=materialized.effect, summary=materialized.summary, confirmable=materialized.confirmable,
        diagnostics=materialized.diagnostics, compiler_intent_json=intent.canonical_json,
        compiler_intent_sha256=intent.sha256, domain_contract_ref=_domain_ref(), target_profile_ref=_profile_ref(custom),
        source_stage=stage, publication_id=operation, prepared_by=principal_subject,
        created_at=stamp.isoformat(), expires_at=(stamp + PREPARE_TTL).isoformat())
    body = draft.model_dump(mode="json", by_alias=True)
    content = NativeFirstWorldPlanContent.model_validate({**body, "planDigest": "sha256:" + canonical_sha256(body)})
    public = content.model_dump(mode="json", by_alias=True)
    token = sign_publication_intent({"schema": NATIVE_ENVELOPE_SCHEMA, "expires_at": content.expires_at, "plan": public})
    _authorize(authorize_world, world)
    _reservation(world, target, require_provisioning=True)
    # This is a captured observation, never a refresh. A changed state invalidates review.
    _require(repo.get_head(target.native_world_id) == head, "native_first_world_parent_changed",
             "The native parent changed while review was prepared.")
    _require(repo.open_native_source_view(target.native_world_id).epoch == epoch,
             "native_first_world_source_changed", "Source authority changed during review preparation.")
    latest = source_owner._load_exact_snapshot(config.repo_root(), stage.document_id, stage.document_revision, stage.body_sha256)
    _source_binding_matches(latest[4], target, world, stage.source_root_relpath)
    _require(latest[0].record.updated_at == stage.document_updated_at,
             "native_first_world_source_changed", "The source metadata changed during review preparation.")
    _require(resolve_promotable_ingest_run(request.run_id, root=config.repo_root()).data.run.revision == draft.run_revision,
             "native_first_world_run_changed", "The extraction changed during review preparation.")
    plan = NativeFirstWorldPlan.model_validate({**public, "token": token})
    from apps.live_control_server.models.native_first_world_publication import (
        NATIVE_CONFIRM_SCHEMA, NativeFirstWorldConfirmRequest,
    )
    from apps.live_control_server.services.hosted_auth import MAX_WORLD_SCOPE_BODY_BYTES
    envelope = NativeFirstWorldConfirmRequest(schema=NATIVE_CONFIRM_SCHEMA, plan=plan)
    _require(len(envelope.model_dump_json(by_alias=True).encode("utf-8")) <= MAX_WORLD_SCOPE_BODY_BYTES,
             "native_first_world_confirmation_too_large",
             "This exact review exceeds the supported confirmation size. Review a smaller source group.")
    return plan


def _intent(plan):
    """Rebuild the sealed pure intent without consulting today's candidate run."""
    from graph_memory.source_span import source_span_index_from_dict
    original = FirstWorldNativeIntent(plan.compiler_intent_json, plan.compiler_intent_sha256)
    audit = original.audit
    rebuilt = compile_first_world_native_intent(audit["reviewed_effect"], world_id=plan.world_id,
        source_text=audit["source_text"], span_index=source_span_index_from_dict(audit["source_span_index"]))
    _require(rebuilt == original and audit["reviewed_effect"] == plan.reviewed_effect
             and audit["source_body_sha256"] == plan.source_stage.body_sha256
             and audit["policy"] == plan.policy,
             "native_first_world_plan_invalid", "The sealed compiler intent changed.")
    _require([r["assertion_id"] for r in audit["reviewed_effect"]["accepted_proposals"]] == plan.accepted_assertion_ids
             and [r["assertion_id"] for r in audit["reviewed_effect"]["rejected_assertions"]] == plan.rejected_assertion_ids,
             "native_first_world_plan_invalid", "The reviewed assertion inventory changed.")
    return rebuilt


def _command(repository, receipt):
    """Read and verify immutable publication correspondence, never current access."""
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
    verified = get_publication_receipt(receipt.space_id, receipt.publication_id, repository=repository)
    if verified != receipt:
        raise PersistenceIntegrityError("native first-World publication receipt drift")
    stored = repository.get_revision(receipt.space_id, receipt.published_revision_id)
    if stored is None:
        raise PersistenceIntegrityError("native first-World publication revision missing")
    verify_stored_revision(stored)
    revision = stored.revision
    return PublishKnowledgeRevisionCommand(space_id=revision.space_id,
        parent_revision_id=revision.parent_revision_id, expected_parent_revision_id=revision.parent_revision_id,
        operation_ids=revision.operation_ids, created_at=revision.created_at,
        graph_schema=revision.graph_schema, graph_payload=stored.graph_payload,
        domain_contract_ref=revision.domain_contract_ref, semantic_profile_ref=revision.semantic_profile_ref,
        migration_origin_ref=revision.migration_origin_ref)


def _source_records(repository, plan, receipt):
    """Immutable metadata/origin qualification. Withdrawal does not erase history."""
    view = repository.open_native_source_view(plan.native_target.native_world_id)
    metadata = view.get_native_metadata_snapshot(artifact_ids=[receipt.source_artifact_id],
                                                revision_ids=[receipt.source_revision_id])
    artifact = metadata.provenance.get_artifact(receipt.source_artifact_id)
    revision = metadata.provenance.get_revision(receipt.source_revision_id)
    if (artifact is None or revision is None
            or revision.source_artifact_id != receipt.source_artifact_id
            or revision.content_sha256 != plan.source_stage.body_sha256
            or revision.body_storage != "dm_native_utf8_body_v1"
            or artifact.source_classification != source_owner.SOURCE_CLASSIFICATION
            or artifact.authority != "primary"
            or metadata.get_origin(receipt.source_artifact_id, receipt.source_revision_id) != plan.source_stage.origin):
        raise PersistenceIntegrityError("native first-World immutable source association drift")
    # Current active/retracted status is intentionally not an acceptance test for
    # an already committed Graph. Ordinary source reads still enforce it.
    return artifact, revision


def _admission_request(plan, parent_id):
    from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
    from graph_memory.vnext.domain_runtime import GM_LABEL
    stage = plan.source_stage
    intent = _intent(plan)
    return NativeTextSourceAdmissionV1(space_id=plan.native_target.native_world_id,
        admission_id=stage.admission_id, expected_parent_revision_id=parent_id,
        created_at=_time(stage.document_updated_at), body_text=intent.audit["source_text"],
        expected_body_sha256=stage.body_sha256, source_classification=source_owner.SOURCE_CLASSIFICATION,
        authority="primary", visibility={"kind": "labels_all", "labels": [GM_LABEL]}, origin=stage.origin,
        spans=[{"client_ref": source_owner.WHOLE_DOCUMENT_SPAN_REF, "evidence_role": "context",
                "start_byte": 0, "end_byte": len(intent.audit["source_text"].encode("utf-8")),
                "expected_slice_sha256": stage.body_sha256}])


def _verify_admission(repository, plan, receipt):
    """Verify the retained original operation without opening a withdrawn source."""
    from dungeonmind.application.vnext.native_source_admission import native_source_command_sha256
    stage, space = plan.source_stage, plan.native_target.native_world_id
    if (receipt.space_id != space or receipt.admission_id != stage.admission_id
            or receipt.origin != stage.origin or len(receipt.bindings) != 1
            or receipt.bindings[0].client_ref != source_owner.WHOLE_DOCUMENT_SPAN_REF):
        raise PersistenceIntegrityError("native first-World admission identity drift")
    command = _command(repository, receipt.publication_receipt)
    _source_records(repository, plan, receipt)
    if stage.admission_state == "admitted":
        if (canonical_sha256(receipt.model_dump(mode="json")) != stage.admission_receipt_sha256
                or receipt.source_artifact_id != stage.native_source_artifact_id
                or receipt.source_revision_id != stage.native_source_revision_id
                or receipt.bindings[0].evidence_ref_id != stage.whole_document_evidence_ref_id):
            raise PersistenceIntegrityError("native first-World sealed admission changed")
    else:
        genesis = get_publication_receipt(space, stage.genesis_initialization_id, repository=repository)
        parent = stage.head_revision_id if stage.head_revision_id is not None else (
            genesis.published_revision_id if genesis is not None else None)
        if parent is None or command.expected_parent_revision_id != parent:
            raise PersistenceIntegrityError("native first-World source admission parent drift")
        request = _admission_request(plan, parent)
        domain, profile = resolve_dungeonbuddy_descriptors(domain_ref=command.domain_contract_ref,
                                                          profile_ref=command.semantic_profile_ref)
        if native_source_command_sha256(request=request, command=command,
                domain_contract=domain, semantic_profile=profile) != receipt.command_sha256:
            raise PersistenceIntegrityError("native first-World original source command drift")
    _verify_genesis(repository, stage, space, receipt.published_revision_id)
    return receipt


def _verify_source_events(repository, space, head):
    previous = None
    for event in repository.head_events(space):
        _require(event.event_kind == "publish", "native_first_world_history_unsupported",
                 "This reservation has rollback history and cannot be treated as pristine.")
        if event.space_id != space or event.previous_revision_id != previous:
            raise PersistenceIntegrityError("native first-World head event chain drift")
        parsed = _parsed(repository, space, event.target_revision_id)
        _source_only(parsed)
        if parsed.parent_revision_id != previous:
            raise PersistenceIntegrityError("native first-World published ancestry drift")
        previous = event.target_revision_id
    if previous != (head.head_revision_id if head is not None else None):
        raise PersistenceIntegrityError("native first-World head/event correspondence drift")


def _introduced_at(repository, parent, evidence_id):
    current = parent
    seen = set()
    while current.parent_revision_id is not None:
        if current.revision_id in seen:
            raise PersistenceIntegrityError("native first-World proof ancestry cycle")
        seen.add(current.revision_id)
        preceding = _parsed(repository, parent.space_id, current.parent_revision_id)
        if evidence_id not in preceding.evidence_by_id:
            break
        current = preceding
    if len(current.operation_ids) != 1:
        raise PersistenceIntegrityError("native first-World proof has ambiguous producer")
    return current.revision_id, current.operation_ids[0]


def _existing_bindings(repository, parent, root, intent, view):
    """Resolve only actual source proofs; current access is checked separately."""
    required = {(r["start_byte"], r["end_byte"], r["slice_sha256"]) for r in intent.audit["source_requirements"]}
    by_interval = {}
    introducing_rows = {}
    for evidence in parent.evidence_by_id.values():
        if (evidence.source_artifact_id, evidence.source_revision_id) != (root.source_artifact_id, root.source_revision_id):
            continue
        if not evidence.source_span_ref_id:
            raise PersistenceIntegrityError("native first-World source evidence has no span")
        raw = view.get_native_text_source(source_artifact_id=root.source_artifact_id,
            source_revision_id=root.source_revision_id, span_id=evidence.source_span_ref_id)
        if raw is None or raw.span_proof.evidence_ref_id != evidence.evidence_ref_id:
            raise PersistenceIntegrityError("native first-World parent proof is missing")
        proof = raw.span_proof
        key = (proof.start_byte, proof.end_byte, proof.slice_sha256)
        if key not in required:
            continue
        _require(evidence.evidence_role in {"support", "context"}, "native_first_world_evidence_role",
                 "The exact existing interval is not supporting or contextual evidence.")
        if (raw.source_artifact.source_artifact_id != root.source_artifact_id
                or raw.source_revision.source_artifact_id != root.source_artifact_id
                or raw.source_revision.source_revision_id != root.source_revision_id
                or raw.source_revision.content_sha256 != intent.audit["source_body_sha256"]
                or raw.body_bytes != intent.audit["source_text"].encode("utf-8")):
            raise PersistenceIntegrityError("native first-World exact source body drift")
        introduced, operation = _introduced_at(repository, parent, evidence.evidence_ref_id)
        if operation == root.admission_id:
            if not any(b.evidence_ref_id == proof.evidence_ref_id and b.span_id == proof.span_id for b in root.bindings):
                raise PersistenceIntegrityError("native first-World original proof binding drift")
            origin, kind = root, "admission"
        else:
            origin = repository.get_native_source_evidence_extension_receipt(parent.space_id, operation)
            kind = "extension"
            if (origin is None or origin.original_admission_id != root.admission_id
                    or origin.original_admission_sha256 != canonical_sha256(root.model_dump(mode="json"))
                    or proof not in origin.proofs):
                raise PersistenceIntegrityError("native first-World existing extension lineage drift")
        if (origin.publication_receipt.published_revision_id != introduced
                or raw.authority_epoch != origin.source_authority_epoch
                or proof.source_revision_id != root.source_revision_id):
            raise PersistenceIntegrityError("native first-World proof producer identity drift")
        if introduced not in introducing_rows:
            _command(repository, origin.publication_receipt)
            introducing_rows[introduced] = _parsed(repository, parent.space_id, introduced).evidence_by_id
        original = introducing_rows[introduced].get(evidence.evidence_ref_id)
        if original is None or original != evidence:
            raise PersistenceIntegrityError("native first-World original evidence role or metadata changed")
        data = dict(proof=proof, source_revision=raw.source_revision, evidence_role=evidence.evidence_role,
            proof_authority_epoch=raw.authority_epoch, origin_kind=kind, origin_operation_id=operation,
            origin_receipt_sha256=canonical_sha256(origin.model_dump(mode="json")), introduced_revision_id=introduced)
        if key in by_interval and by_interval[key]["proof"] != proof:
            _refuse("native_first_world_ambiguous_evidence", "More than one exact native proof matches this review.")
        by_interval[key] = data
    return [NativeFirstWorldExistingBinding(reviewed_evidence_ref_id=r["reviewed_evidence_ref_id"], **by_interval[key])
            for r in intent.audit["source_requirements"]
            if (key := (r["start_byte"], r["end_byte"], r["slice_sha256"])) in by_interval]


def _stage_fresh(repository, plan, expected_parent, expected_epoch):
    """Before an unapplied write only; never called by immutable recovery."""
    space, stage = plan.native_target.native_world_id, plan.source_stage
    head = repository.get_head(space)
    _require((head.head_revision_id if head else None) == expected_parent,
             "native_first_world_parent_changed", "The exact reviewed native stage parent changed.")
    _verify_source_events(repository, space, head)
    _require(repository.open_native_source_view(space).epoch == expected_epoch,
             "native_first_world_source_changed", "Source authority changed before an unapplied stage.")
    _reservation(plan.world_id, plan.native_target, require_provisioning=True)
    snapshot, body, digest, admission_id, binding = source_owner._load_exact_snapshot(
        config.repo_root(), stage.document_id, stage.document_revision, stage.body_sha256)
    _source_binding_matches(binding, plan.native_target, plan.world_id, stage.source_root_relpath)
    _require(body == _intent(plan).audit["source_text"].encode("utf-8")
             and digest == stage.body_sha256 and admission_id == stage.admission_id
             and snapshot.record.updated_at == stage.document_updated_at,
             "native_first_world_source_changed", "The sealed source changed before an unapplied stage.")


def _stage_genesis(repository, plan, recovery_only):
    from dungeonmind.application.vnext.initialization import initialize_empty_knowledge_space
    stage, space = plan.source_stage, plan.native_target.native_world_id
    receipt = get_publication_receipt(space, stage.genesis_initialization_id, repository=repository)
    if receipt is None:
        if recovery_only or stage.head_revision_id is not None:
            raise PersistenceIntegrityError("native first-World stage genesis receipt missing")
        _stage_fresh(repository, plan, None, stage.source_authority_epoch)
        receipt = initialize_empty_knowledge_space(repository=repository, space_id=space,
            initialization_id=stage.genesis_initialization_id, created_at=_time(stage.genesis_created_at),
            domain_contract=dungeonbuddy_world_domain_contract(), semantic_profile=dungeonbuddy_dnd5e_semantic_profile())
    _verify_genesis(repository, stage, space, receipt.published_revision_id)
    # A pre-existing source-only parent is an observed pin, not a refreshed head.
    parent_id = stage.head_revision_id or receipt.published_revision_id
    _history(repository, space, parent_id, receipt.published_revision_id, source_only=True)
    return parent_id


def _stage_admission(repository, plan, parent_id, recovery_only):
    from dungeonmind.application.vnext.native_source_admission import publish_native_text_source_evidence
    stage, space = plan.source_stage, plan.native_target.native_world_id
    receipt = repository.get_native_source_admission_receipt(space, stage.admission_id)
    if receipt is None:
        if recovery_only or stage.admission_state == "admitted":
            raise PersistenceIntegrityError("native first-World sealed admission receipt missing")
        _stage_fresh(repository, plan, parent_id, stage.source_authority_epoch)
        parent = _parsed(repository, space, parent_id)
        domain, profile = _source_only(parent)
        receipt = publish_native_text_source_evidence(repository=repository,
            request=_admission_request(plan, parent_id), domain_contract=domain, semantic_profile=profile)
    _verify_admission(repository, plan, receipt)
    if stage.admission_state == "admitted":
        _history(repository, space, parent_id, receipt.published_revision_id, source_only=True)
        return receipt, parent_id, stage.source_authority_epoch
    return receipt, receipt.published_revision_id, receipt.source_authority_epoch


def _stage_missing_intervals(plan, actual_bindings):
    """One caller reference per missing exact interval; never duplicate registration."""
    existing = {b.reviewed_evidence_ref_id for b in actual_bindings}
    missing = {}
    for requirement in _intent(plan).audit["source_requirements"]:
        if requirement["reviewed_evidence_ref_id"] not in existing:
            key = (requirement["start_byte"], requirement["end_byte"], requirement["slice_sha256"])
            missing.setdefault(key, requirement)
    return tuple(missing[key] for key in sorted(missing))


def _stage_extension_request(plan, admission, parent_id, epoch, missing):
    from dungeonmind.contracts.vnext.native_source import NativeSourceEvidenceExtensionV1
    return NativeSourceEvidenceExtensionV1(space_id=plan.native_target.native_world_id,
        extension_id=plan.source_stage.extension_id, original_admission_id=admission.admission_id,
        source_artifact_id=admission.source_artifact_id, source_revision_id=admission.source_revision_id,
        expected_body_sha256=plan.source_stage.body_sha256, expected_parent_revision_id=parent_id,
        expected_source_authority_epoch=epoch, created_at=_time(plan.created_at),
        spans=[dict(client_ref=r["source_span_ref_id"], evidence_role="support", start_byte=r["start_byte"],
                    end_byte=r["end_byte"], expected_slice_sha256=r["slice_sha256"]) for r in missing])


def _stage_verify_extension(repository, plan, admission, request, receipt, parent):
    """Reconstruct the exact evidence-only command from real receipt allocations.

    This is immutable verification, not Core's current-access extension replay.
    It neither allocates identifiers nor asks a planner to manufacture a proof.
    """
    from dungeonmind.application.vnext.materialization import encode_native_graph_payload
    from dungeonmind.application.vnext.native_source_extension import extension_intent
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
    from dungeonmind.contracts.vnext.native_source import NativeSourceEvidenceExtensionReceiptV1
    from dungeonmind.contracts.vnext.source import EvidenceRefV3

    receipt = NativeSourceEvidenceExtensionReceiptV1.model_validate(receipt.model_dump(mode="json"))
    domain, profile = _source_only(parent)
    if (receipt.space_id != request.space_id or receipt.extension_id != request.extension_id
            or receipt.original_admission_id != admission.admission_id
            or receipt.original_admission_sha256 != canonical_sha256(admission.model_dump(mode="json"))
            or receipt.source_artifact_id != admission.source_artifact_id
            or receipt.source_revision_id != admission.source_revision_id or receipt.origin != admission.origin
            or receipt.intent_sha256 != extension_intent(request, domain, profile)
            or receipt.source_authority_epoch != request.expected_source_authority_epoch + 1
            or len(receipt.bindings) != len(request.spans)):
        raise PersistenceIntegrityError("native first-World extension receipt changed")
    stored_parent = repository.get_revision(parent.space_id, parent.revision_id)
    if stored_parent is None:
        raise PersistenceIntegrityError("native first-World extension parent missing")
    decoded = decode_native_graph_payload(stored_parent.graph_payload)
    evidence = {e.evidence_ref_id: e for e in decoded.evidence}
    for span, binding, proof in zip(request.spans, receipt.bindings, receipt.proofs, strict=True):
        if (binding.client_ref != span.client_ref or proof.source_revision_id != request.source_revision_id
                or (proof.start_byte, proof.end_byte, proof.slice_sha256) !=
                   (span.start_byte, span.end_byte, span.expected_slice_sha256)
                or proof.evidence_ref_id in evidence):
            raise PersistenceIntegrityError("native first-World extension proof changed")
        evidence[proof.evidence_ref_id] = EvidenceRefV3(evidence_ref_id=proof.evidence_ref_id,
            source_artifact_id=request.source_artifact_id, source_revision_id=request.source_revision_id,
            evidence_role=span.evidence_role, can_open_source=True, can_highlight_span=True,
            source_span_ref_id=proof.span_id, domain_metadata=span.domain_metadata)
    expected = PublishKnowledgeRevisionCommand(space_id=parent.space_id,
        parent_revision_id=parent.revision_id, expected_parent_revision_id=parent.revision_id,
        operation_ids=[request.extension_id], graph_schema=parent.graph_schema,
        graph_payload=encode_native_graph_payload(entities={}, assertions={}, aliases={}, evidence=evidence),
        domain_contract_ref=plan.domain_contract_ref,
        semantic_profile_ref=SemanticProfileRef(profile_id=parent.semantic_profile_ref.profile_id,
            profile_revision=parent.semantic_profile_ref.profile_revision,
            descriptor_sha256=parent.semantic_profile_ref.descriptor_sha256),
        migration_origin_ref=None, created_at=request.created_at)
    actual = _command(repository, receipt.publication_receipt)
    if canonical_sha256(actual.model_dump(mode="json")) != canonical_sha256(expected.model_dump(mode="json")):
        raise PersistenceIntegrityError("native first-World extension command changed")
    _history(repository, parent.space_id, receipt.publication_receipt.published_revision_id,
             admission.published_revision_id, source_only=True)
    return receipt


def _stage_extension(repository, plan, admission, parent_id, epoch, actual_bindings, recovery_only):
    from dungeonmind.application.vnext.native_source_extension import publish_native_source_evidence_extension
    from graph_memory.vnext.domain_runtime import GM_LABEL

    missing = _stage_missing_intervals(plan, actual_bindings)
    receipt = repository.get_native_source_evidence_extension_receipt(
        plan.native_target.native_world_id, plan.source_stage.extension_id)
    if not missing:
        if receipt is not None or get_publication_receipt(plan.native_target.native_world_id,
                plan.source_stage.extension_id, repository=repository) is not None:
            raise PersistenceIntegrityError("native first-World unexpected evidence extension")
        return parent_id, epoch
    parent = _parsed(repository, plan.native_target.native_world_id, parent_id)
    request = _stage_extension_request(plan, admission, parent_id, epoch, missing)
    if receipt is None:
        if recovery_only:
            raise PersistenceIntegrityError("native first-World extension receipt missing")
        _stage_fresh(repository, plan, parent_id, epoch)
        domain, profile = _source_only(parent)
        receipt = publish_native_source_evidence_extension(repository=repository, request=request,
            domain_contract=domain, semantic_profile=profile, audience_labels=[GM_LABEL])
    receipt = _stage_verify_extension(repository, plan, admission, request, receipt, parent)
    return receipt.publication_receipt.published_revision_id, receipt.source_authority_epoch


def _stage_profile(repository, plan, parent_id, epoch, recovery_only):
    from dungeonmind.application.vnext.profile_transition import transition_knowledge_semantic_profile
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
    from dungeonmind.contracts.vnext.profile_transition import KnowledgeProfileTransitionV1

    space, stage = plan.native_target.native_world_id, plan.source_stage
    parent = _parsed(repository, space, parent_id)
    domain, current_profile = _source_only(parent)
    current_ref = SemanticProfileRef(profile_id=parent.semantic_profile_ref.profile_id,
        profile_revision=parent.semantic_profile_ref.profile_revision,
        descriptor_sha256=parent.semantic_profile_ref.descriptor_sha256)
    receipt = get_publication_receipt(space, stage.profile_transition_id, repository=repository)
    if current_ref == plan.target_profile_ref:
        if receipt is not None:
            raise PersistenceIntegrityError("native first-World unexpected profile transition")
        return parent_id
    if current_ref != _profile_ref(False) or plan.target_profile_ref != _profile_ref(True):
        raise PersistenceIntegrityError("native first-World non-additive profile stage")
    request = KnowledgeProfileTransitionV1(space_id=space, publication_id=stage.profile_transition_id,
        expected_parent_revision_id=parent_id, created_at=_time(plan.created_at),
        domain_contract_ref=plan.domain_contract_ref, from_profile_ref=current_ref,
        to_profile_ref=plan.target_profile_ref)
    if receipt is None:
        if recovery_only:
            raise PersistenceIntegrityError("native first-World profile receipt missing")
        _stage_fresh(repository, plan, parent_id, epoch)
        receipt = transition_knowledge_semantic_profile(repository=repository, request=request,
            domain_contract=domain, current_profile=current_profile,
            target_profile=dungeonbuddy_dnd5e_custom_predicate_profile())
    stored = repository.get_revision(space, parent_id)
    if stored is None:
        raise PersistenceIntegrityError("native first-World profile parent missing")
    expected = PublishKnowledgeRevisionCommand(space_id=space, parent_revision_id=parent_id,
        expected_parent_revision_id=parent_id, operation_ids=[stage.profile_transition_id],
        graph_schema=parent.graph_schema, graph_payload=stored.graph_payload,
        domain_contract_ref=plan.domain_contract_ref, semantic_profile_ref=plan.target_profile_ref,
        migration_origin_ref=None, created_at=request.created_at)
    actual = _command(repository, receipt)
    if canonical_sha256(actual.model_dump(mode="json")) != canonical_sha256(expected.model_dump(mode="json")):
        raise PersistenceIntegrityError("native first-World profile command changed")
    return receipt.published_revision_id


def resolve_native_first_world_stages(repository, plan, *, recovery_only=False):
    """Return the exact source-only parent and real B1 proof bindings.

    The caller verifies the signed plan and current principal before entering.
    Recovery reads immutable records (including retracted records), never current
    access helpers, run/document loaders, repository writes or fresh head selection.
    """
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldNativeSpanBinding

    plan = NativeFirstWorldPlan.model_validate(plan.model_dump(mode="json", by_alias=True))
    intent = _intent(plan)
    _require(plan.domain_contract_ref == _domain_ref()
             and plan.target_profile_ref in (_profile_ref(False), _profile_ref(True))
             and (intent.audit["required_profile_revision"] != "2" or plan.target_profile_ref == _profile_ref(True)),
             "native_first_world_profile_unsupported", "The signed stage descriptors do not match the compiler policy.")
    parent_id = _stage_genesis(repository, plan, recovery_only)
    admission, parent_id, epoch = _stage_admission(repository, plan, parent_id, recovery_only)
    parent = _parsed(repository, plan.native_target.native_world_id, parent_id)
    actual = _existing_bindings(repository, parent, admission, intent,
                               repository.open_native_source_view(parent.space_id))
    if plan.source_stage.admission_state == "admitted" and actual != plan.source_stage.existing_bindings:
        raise PersistenceIntegrityError("native first-World sealed existing proof changed")
    parent_id, epoch = _stage_extension(repository, plan, admission, parent_id, epoch, actual, recovery_only)
    parent_id = _stage_profile(repository, plan, parent_id, epoch, recovery_only)
    parent = _parsed(repository, plan.native_target.native_world_id, parent_id)
    _source_only(parent)
    bindings = _existing_bindings(repository, parent, admission, intent,
                                 repository.open_native_source_view(parent.space_id))
    if {b.reviewed_evidence_ref_id for b in bindings} != {
            r["reviewed_evidence_ref_id"] for r in intent.audit["source_requirements"]}:
        raise PersistenceIntegrityError("native first-World source binding inventory incomplete")
    if not recovery_only:
        _stage_fresh(repository, plan, parent_id, epoch)
    return parent, tuple(FirstWorldNativeSpanBinding.from_proof(b.reviewed_evidence_ref_id,
        b.proof, source_revision=b.source_revision) for b in bindings)


class _NativeFirstWorldWriteRefused(PersistenceIntegrityError):
    """Preserve current authorization refusals through Core's recovery catch."""

    def __init__(self, failure):
        super().__init__("native first-World pre-write guard refused publication")
        self.failure = failure


class _NativeFirstWorldGuardedRepository:
    def __init__(self, repository, before_write):
        self._repository, self._before_write = repository, before_write

    def __getattr__(self, name):
        member = getattr(self._repository, name)
        if not callable(member) or name.startswith(("get_", "open_")) or name == "head_events":
            return member
        if not name.startswith("publish"):
            raise PersistenceIntegrityError("unexpected native first-World repository mutation")

        def guarded(*args, **kwargs):
            try:
                self._before_write(name)
            except Exception as exc:
                raise _NativeFirstWorldWriteRefused(exc) from exc
            return member(*args, **kwargs)
        return guarded


def _validate_unapplied_review(plan):
    """Rebuild today's exact frozen review before any uncommitted graph work."""
    resolved = resolve_promotable_ingest_run(plan.run_id, root=config.repo_root())
    _require(resolved.world_id == plan.world_id and resolved.data.run.revision == plan.run_revision,
             "native_first_world_run_changed", "The extraction changed after review.")
    data = _load_worldbuilding_publication_input(resolved, allow_gazetteer=False)
    lineage = cross_check_workspace_lineage(config.repo_root(), source_artifact_id=resolved.source_artifact_id,
                                           expected_world_id=plan.world_id)
    _require(lineage.source_artifact_id == plan.source_artifact_id
             and lineage.source_revision_id == plan.source_revision_id
             and lineage.workspace_document_id == plan.workspace_document_id
             and lineage.workspace_document_revision == plan.workspace_document_revision,
             "native_first_world_source_changed", "The source lineage changed after review.")
    commitment = legacy._source_evidence_commitment(data.reviewed_assertions,
        source_prose=data.source_prose, span_index=data.span_index, source_artifact_id=plan.source_artifact_id)
    decisions = [WorldbuildingDispositionInput(assertion_id=row["assertion_id"], decision=row["decision"],
                    target_node_id=row.get("target_node_id")) for row in plan.reviewed_effect["decision_snapshot"]]
    materialized = materialize_first_world_plan(preview=data.preview, world_id=plan.world_id,
        native_target=plan.native_target, run_id=plan.run_id, source_artifact_id=plan.source_artifact_id,
        source_revision_id=plan.source_revision_id, source_uri=resolved.sealed_source_uri,
        source_evidence_sha256=commitment, extraction_profile=data.profile_id, campaign_scope=plan.campaign_scope,
        workspace_document_id=plan.workspace_document_id, workspace_document_revision=plan.workspace_document_revision,
        dispositions=decisions)
    legacy._assert_materialized_evidence_matches_review(materialized, data.reviewed_assertions)
    intent = compile_first_world_native_intent(materialized.effect, world_id=plan.world_id,
        source_text=data.source_prose, span_index=data.span_index)
    _require(commitment == plan.source_evidence_sha256 and materialized.effect == plan.reviewed_effect
             and materialized.decision_digest == plan.decision_digest
             and materialized.contribution.contribution_id == plan.contribution_id
             and compute_contribution_payload_sha256(materialized.contribution) == plan.contribution_payload_sha256
             and intent == _intent(plan),
             "native_first_world_review_changed", "The exact reviewed effects changed before publication.")


def _native_source_status(repository, plan, revision_id, evidence_id):
    from dungeonmind.application.vnext.native_source_access import (
        open_native_text_source_access_context, open_admitted_native_text,
    )
    from graph_memory.vnext.domain_runtime import GM_LABEL
    try:
        context = open_native_text_source_access_context(repository=repository,
            space_id=plan.native_target.native_world_id, revision_id=revision_id,
            domain_contract=dungeonbuddy_world_domain_contract(), audience_labels=[GM_LABEL])
        result = open_admitted_native_text(context, evidence_id)
        return "available" if result.status == "available" else "unavailable"
    except PersistenceIntegrityError:
        raise
    except Exception:
        return "unknown"


def confirm_native_first_world(request, *, principal_subject, authorize_world=None, repository=None):
    """Receipt-first confirmation; immutable recovery never reloads current runs."""
    from dungeonmind.application.vnext.materialization import GovernedPublicationIdentity
    from dungeonmind.application.vnext.prospective import get_prospective_publication
    from dungeonmind.application.vnext.prospective_aliases import publish_prospective_alias_contribution
    from apps.live_control_server.models.native_first_world_publication import (
        NativeFirstWorldConfirmRequest, NativeFirstWorldConfirmReceipt,
    )
    from apps.live_control_server.services.native_first_world_compilation import bind_first_world_native_intent
    from apps.live_control_server.services.world_graph_binding import (
        _NativeFirstWorldReadOnlyRepository, activate_native_first_world, WorldGraphBindingError,
    )

    _require(type(principal_subject) is str and bool(principal_subject.strip()),
             "native_first_world_principal_missing", "A current confirming principal is required.")
    request = NativeFirstWorldConfirmRequest.model_validate(request.model_dump(mode="json", by_alias=True))
    plan = decode_native_plan(request.plan, principal_subject=principal_subject)
    _authorize(authorize_world, plan.world_id)
    _reservation(plan.world_id, plan.native_target)
    _require(plan.confirmable and bool(plan.accepted_assertion_ids),
             "empty_first_world_contribution", "This review has no accepted assertions to publish.")
    repo = repository if repository is not None else _repository()
    prior = get_prospective_publication(plan.native_target.native_world_id, plan.publication_id, repository=repo)
    recovered = prior is not None
    graph_parent = None
    if recovered:
        selected = _NativeFirstWorldReadOnlyRepository(repo)
    else:
        decode_native_plan(plan, principal_subject=principal_subject, allow_expired=False)
        _reservation(plan.world_id, plan.native_target, require_provisioning=True)
        _validate_unapplied_review(plan)

        def before_write(operation):
            _authorize(authorize_world, plan.world_id)
            _reservation(plan.world_id, plan.native_target, require_provisioning=True)
            _validate_unapplied_review(plan)
            if operation == "publish_prospective_publication":
                admission = repo.get_native_source_admission_receipt(
                    plan.native_target.native_world_id, plan.source_stage.admission_id)
                extension = repo.get_native_source_evidence_extension_receipt(
                    plan.native_target.native_world_id, plan.source_stage.extension_id)
                if admission is None:
                    raise PersistenceIntegrityError("native first-World pre-graph admission missing")
                epoch = (extension.source_authority_epoch if extension is not None else
                         plan.source_stage.source_authority_epoch if plan.source_stage.admission_state == "admitted"
                         else admission.source_authority_epoch)
                if graph_parent is None:
                    raise PersistenceIntegrityError("native first-World resolved graph parent missing")
                _stage_fresh(repo, plan, graph_parent, epoch)
                view = repo.open_native_source_view(plan.native_target.native_world_id)
                records = _source_records(repo, plan, admission)
                _require(records[0].status == "active" and view.epoch == epoch,
                         "native_first_world_source_changed", "The source was withdrawn before graph publication.")
        selected = _NativeFirstWorldGuardedRepository(repo, before_write)
    try:
        parent, bindings = resolve_native_first_world_stages(selected, plan, recovery_only=recovered)
        graph_parent = parent.revision_id
        compilation = bind_first_world_native_intent(_intent(plan), parent=parent,
            native_space_id=plan.native_target.native_world_id, bindings=bindings, produced_at=_time(plan.created_at))
        domain, profile = resolve_dungeonbuddy_descriptors(domain_ref=plan.domain_contract_ref,
                                                          profile_ref=plan.target_profile_ref)
        publication = publish_prospective_alias_contribution(parent=parent, request=compilation.request,
            dispositions=compilation.dispositions, publication=GovernedPublicationIdentity(
                (plan.publication_id,), _time(plan.created_at), parent.revision_id),
            publication_id=plan.publication_id, domain_contract=domain, semantic_profile=profile, repository=selected)
    except _NativeFirstWorldWriteRefused as exc:
        raise exc.failure from exc
    except (DungeonMindError, ExtractPromoteError, PromotableIngestRunError,
            WorldbuildingWritePlanError, source_owner.NativeWorldSourceAdmissionError):
        raise
    except Exception as exc:
        from apps.live_control_server.models.native_first_world_compilation import FirstWorldCompilationError
        if isinstance(exc, FirstWorldCompilationError):
            raise
        raise ExtractPromoteError(
            "A native publication stage may have committed. Retain and retry this exact reviewed request.",
            code="native_first_world_outcome_unknown", status_code=503,
        ) from exc
    receipt = publication.publication_receipt
    _authorize(authorize_world, plan.world_id)
    warnings = []
    try:
        activate_native_first_world(plan.world_id, plan=plan, repository=repo,
            principal_subject=principal_subject, authorize_world=authorize_world)
        activation = "active"
    except (WorldGraphBindingError, PersistenceUnavailableError):
        activation = "pending"
        warnings.append("Graph publication is committed. Retry this exact request to finish World activation.")
    source_status = _native_source_status(repo, plan, receipt.published_revision_id, bindings[0].proof.evidence_ref_id)
    _authorize(authorize_world, plan.world_id)
    return NativeFirstWorldConfirmReceipt(outcome="activation_pending" if activation == "pending" else
        "already_initialized" if recovered else "initialized", world_id=plan.world_id,
        plan_id=plan.plan_id, plan_digest=plan.plan_digest, decision_digest=plan.decision_digest,
        source_artifact_id=plan.source_artifact_id, source_revision_id=plan.source_revision_id,
        contribution_id=plan.contribution_id, native_contribution_id=compilation.request.contribution.contribution_id,
        native_world_id=plan.native_target.native_world_id, publication_id=plan.publication_id,
        committed_revision_id=receipt.published_revision_id, applied_assertion_count=len(plan.accepted_assertion_ids),
        accepted_assertion_ids=plan.accepted_assertion_ids, rejected_assertion_ids=plan.rejected_assertion_ids,
        native_publication=publication, activation_status=activation, source_status=source_status,
        recovered=recovered, warnings=warnings)
