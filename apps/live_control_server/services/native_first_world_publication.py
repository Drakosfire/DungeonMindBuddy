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
from dungeonmind.domain.errors import PersistenceIntegrityError

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
from apps.live_control_server.services.promotable_ingest_run import resolve_promotable_ingest_run
from apps.live_control_server.services.world_container_registry import (
    NativeGraphProvisioningRecord, get_world_container,
)
from graph_memory.vnext.domain_runtime import (
    DUNGEONBUDDY_DOMAIN_DIGEST, DUNGEONBUDDY_PROFILE_DIGEST,
    DUNGEONBUDDY_CUSTOM_PROFILE_DIGEST, dungeonbuddy_world_domain_contract,
    dungeonbuddy_dnd5e_semantic_profile, dungeonbuddy_dnd5e_custom_predicate_profile,
    resolve_dungeonbuddy_descriptors,
)
from graph_memory.worldbuilding_write_plan import WorldbuildingDispositionInput


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
    signed = decode_publication_intent(plan.token, allow_expired_recovery=allow_expired)
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
    return NativeFirstWorldPlan.model_validate({**public, "token": token})


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
        _command(repository, origin.publication_receipt)
        data = dict(proof=proof, source_revision=raw.source_revision, evidence_role=evidence.evidence_role,
            proof_authority_epoch=raw.authority_epoch, origin_kind=kind, origin_operation_id=operation,
            origin_receipt_sha256=canonical_sha256(origin.model_dump(mode="json")), introduced_revision_id=introduced)
        if key in by_interval and by_interval[key]["proof"] != proof:
            _refuse("native_first_world_ambiguous_evidence", "More than one exact native proof matches this review.")
        by_interval[key] = data
    return [NativeFirstWorldExistingBinding(reviewed_evidence_ref_id=r["reviewed_evidence_ref_id"], **by_interval[key])
            for r in intent.audit["source_requirements"]
            if (key := (r["start_byte"], r["end_byte"], r["slice_sha256"])) in by_interval]
