"""Installed public WK/Core composition; no Buddy manual API or serving proof."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from dungeonmind.application.vnext import (
    build_parsed_knowledge_revision,
    get_native_source_publication_support,
    initialize_empty_knowledge_space,
    open_admitted_native_text,
    open_native_text_source_access_context,
    preview_native_source_publication_evidence,
    publish_governed_native_source_publication,
    publish_native_source_evidence_extension,
    publish_native_text_source_evidence,
    recover_governed_native_source_publication,
    recover_native_source_evidence_extension,
)
from dungeonmind.application.vnext.alias_search import AliasSearchReadService
from dungeonmind.application.vnext.entity_reads import EntityReadService
from dungeonmind.application.vnext.errors import (
    KnowledgePublicationIdempotencyConflictError,
    NativeTextSourceAdmissionIntegrityError,
)
from dungeonmind.application.vnext.materialization import decode_native_graph_payload
from dungeonmind.application.vnext.search import SearchReadService
from dungeonmind.contracts.vnext.native_source import (
    NativeSourceEvidenceExtensionV1,
    NativeTextSourceAdmissionV1,
)
from dungeonmind.contracts.vnext.native_source_publication import (
    GovernedNativeSourcePublicationV1,
    NativeSourcePublicationBasisV1,
)
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.infrastructure.memory.vnext_sources import (
    InMemoryNativeSourceEvidenceRepository,
)
from worldkeeper.application import contracts as wk
from worldkeeper.application.authority import PreparationEvidenceWitness
from worldkeeper.application.preparation import WorldChangePreparer
from worldkeeper.integrations.dungeonmind import compile_prepared_change_to_dungeonmind
from worldkeeper.integrations.dungeonmind.vnext_prepare import (
    DungeonMindVNextPreparationAuthority,
)

from apps.live_control_server.integrations.dungeonmind import (
    assertion_qualification as mapping,
)
from graph_memory.vnext.domain_runtime import (
    CAMPAIGN_SCOPE_AXIS,
    GM_LABEL,
    DungeonBuddyVNextProjectionInput,
    build_dungeonbuddy_read_context,
    dungeonbuddy_dnd5e_manual_profile,
    dungeonbuddy_world_domain_contract,
)

NOW = datetime(2026, 11, 20, tzinfo=UTC)
BODY = "A🐉 Elderwyld exact witness\r\nÉ sworn description.\r\n"
RAW = BODY.encode("utf-8")
TARGET = mapping.CONNECTED_PLACE_OPERATION_V7_TARGET
LABELS = sorted(
    set(mapping._DIRECT_PREDICATE_MAP)
    | set(mapping._RENAME_PREDICATE_MAP)
    | set(mapping._REVERSE_ENDPOINT_PREDICATE_MAP)
    | set(TARGET.predicate_map_additions or {})
)


def setup(repository=None):
    repo = (
        repository
        if repository is not None
        else InMemoryNativeSourceEvidenceRepository()
    )
    domain, profile = (
        dungeonbuddy_world_domain_contract(),
        dungeonbuddy_dnd5e_manual_profile(),
    )
    space = "space:governed-adoption"
    genesis = initialize_empty_knowledge_space(
        repository=repo,
        space_id=space,
        initialization_id="genesis:adoption",
        created_at=NOW,
        domain_contract=domain,
        semantic_profile=profile,
    )
    root = publish_native_text_source_evidence(
        repository=repo,
        domain_contract=domain,
        semantic_profile=profile,
        request=NativeTextSourceAdmissionV1(
            space_id=space,
            admission_id="admission:adoption",
            expected_parent_revision_id=genesis.published_revision_id,
            created_at=NOW,
            body_text=BODY,
            expected_body_sha256=sha256(RAW).hexdigest(),
            source_classification="dungeonbuddy.source:worldbuilding",
            authority="primary",
            visibility={"kind": "labels_any", "labels": [GM_LABEL]},
            spans=[
                dict(
                    client_ref="opening",
                    evidence_role="support",
                    start_byte=0,
                    end_byte=1,
                    expected_slice_sha256=sha256(RAW[:1]).hexdigest(),
                )
            ],
        ),
    )
    return SimpleNamespace(
        repo=repo, domain=domain, profile=profile, space=space, root=root
    )


def basis(c, mode, operation, *, ref=None):
    if mode == "new_intervals":
        evidence = dict(
            mode=mode,
            spans=[
                dict(
                    client_ref="selected",
                    evidence_role="support",
                    start_byte=1,
                    end_byte=len(RAW),
                    expected_slice_sha256=sha256(RAW[1:]).hexdigest(),
                )
            ],
        )
    else:
        # Only exact source/span coordinates survive. No caller-supplied introduction receipt.
        ref = ref or get_native_source_publication_support(
            repository=c.repo,
            space_id=c.space,
            source_revision_id=c.root.source_revision_id,
            span_id=c.root.bindings[0].span_id,
        )
        evidence = dict(mode=mode, support=[ref])
    return NativeSourcePublicationBasisV1(
        space_id=c.space,
        publication_id=operation,
        original_admission_id=c.root.admission_id,
        source_artifact_id=c.root.source_artifact_id,
        source_revision_id=c.root.source_revision_id,
        expected_body_sha256=sha256(RAW).hexdigest(),
        expected_parent_revision_id=c.repo.get_head(c.space).head_revision_id,
        expected_source_authority_epoch=c.repo.open_native_source_view(c.space).epoch,
        created_at=NOW + timedelta(minutes=1),
        evidence=evidence,
    )


def metadata(evidence, *, label="reviewed fact"):
    return wk.AssertionMetadata(
        scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, "campaign:alpha"),),
        visibility=wk.Visibility("labels_any", (GM_LABEL,)),
        epistemic_basis="asserted",
        claim_mode="dungeonbuddy.claim:fact",
        standing="established",
        evidence_ref_ids=tuple(e.evidence_ref_id for e in evidence),
        temporal_scope=wk.TemporalScope(kind="unknown"),
        domain_metadata=(
            wk.DomainMetadata.from_json(
                "dungeonbuddy.domain_metadata:world_context_v1",
                {"context_type": "manual_review", "description": label},
            ),
        ),
    )


def request(c, b):
    evidence = preview_native_source_publication_evidence(
        repository=c.repo,
        request=b,
        domain_contract=c.domain,
        semantic_profile=c.profile,
        audience_labels=(GM_LABEL,),
    )
    kinds = list(TARGET.buddy_to_dm_kind)
    operations = []
    for kind in kinds:
        meta = metadata(evidence, label=f"Description {kind} 🐉\r\nexact")
        operations.append(
            wk.CreateObject(
                kind,
                (
                    wk.CreateFact(
                        kind + ":kind",
                        "dnd5e:classification",
                        wk.TermRefFactValue(TARGET.buddy_to_dm_kind[kind]),
                        meta,
                    ),
                    wk.CreateFact(
                        kind + ":name",
                        "dnd5e:name",
                        wk.LiteralFactValue("Name " + kind),
                        meta,
                    ),
                    wk.CreateFact(
                        kind + ":summary",
                        "dnd5e:summary",
                        wk.LiteralFactValue(f"Description {kind} 🐉\r\nexact"),
                        meta,
                    ),
                ),
            )
        )
    vocabulary = TARGET.world_object_loader()
    for label in LABELS:
        pair = next(
            (a, z)
            for a in kinds
            for z in kinds
            if mapping.edge_endpoint_kind_admission_reason(
                buddy_predicate=label,
                from_buddy_kind=a,
                to_buddy_kind=z,
                target=TARGET,
                vocabulary=vocabulary,
            )
            is None
        )
        if label == "belongs_to":
            # Nonidentical IDs/kinds make an omitted or double reversal observable.
            pair = ("creature", "npc")
            assert (
                mapping.edge_endpoint_kind_admission_reason(
                    buddy_predicate=label,
                    from_buddy_kind=pair[0],
                    to_buddy_kind=pair[1],
                    target=TARGET,
                    vocabulary=vocabulary,
                )
                is None
            )
        term, reverse = mapping.resolve_buddy_predicate_mapping_v4(label, target=TARGET)
        a, z = pair[::-1] if reverse else pair
        operations.append(
            wk.CreateRelationship(
                "edge:" + label,
                wk.ResultOf(a),
                term,
                wk.ResultOf(z),
                metadata(evidence, label="Directed " + label),
            )
        )

    class PreviewAuthority(DungeonMindVNextPreparationAuthority):
        def read_current_space(self, space):
            current = super().read_current_space(space)
            if b.evidence.mode != "new_intervals":
                return current
            # Public WK evidence witness from public Core preview, not invented durable IDs.
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
        authority=PreviewAuthority(c.repo),
        domain_contract=c.domain,
        semantic_profile=c.profile,
        clock=lambda: b.created_at,
        prepared_id_factory=lambda: b.publication_id,
    ).prepare_change(
        wk.WorldChangeIntent(
            c.space, "Buddy installed manual capability proof", tuple(operations)
        )
    )
    assert prepared.prepared_operations == tuple(operations)
    plan = compile_prepared_change_to_dungeonmind(prepared)
    aliases = [
        dict(
            item_id="alias:" + kind,
            alias_id=b.publication_id + ":alias:" + kind,
            entity={"kind": "result_of", "client_op_id": kind},
            alias_text="Alias " + kind,
            evidence_ref_ids=[e.evidence_ref_id for e in evidence],
            standing="established",
        )
        for kind in kinds
    ]
    return GovernedNativeSourcePublicationV1.model_validate(
        {
            **b.model_dump(mode="json"),
            "schema_version": "dm_governed_native_source_publication_v1",
            "contribution": plan.prospective_contribution.model_dump(mode="json"),
            "aliases": aliases,
            "dispositions": [
                *[d.model_dump(mode="json") for d in plan.dispositions],
                *[dict(item_id=a["item_id"], disposition="accepted") for a in aliases],
            ],
        }
    )


def publish(c, r):
    return publish_governed_native_source_publication(
        repository=c.repo,
        request=r,
        domain_contract=c.domain,
        semantic_profile=c.profile,
        audience_labels=(GM_LABEL,),
    )


def recover(c, r, repository=None):
    return recover_governed_native_source_publication(
        repository=repository or c.repo,
        request=r,
        domain_contract=c.domain,
        semantic_profile=c.profile,
    )


def state(c):
    return (
        c.repo.get_head(c.space),
        tuple(c.repo.head_events(c.space)),
        c.repo.open_native_source_view(c.space).epoch,
    )


def context(c, revision, *, role="gm", campaign="campaign:alpha"):
    stored = c.repo.get_revision(c.space, revision)
    parsed = build_parsed_knowledge_revision(
        revision=stored.revision,
        decoded_content=decode_native_graph_payload(stored.graph_payload),
    )
    return build_dungeonbuddy_read_context(
        parsed_revision=parsed,
        projection_input=DungeonBuddyVNextProjectionInput(
            world_id=c.space,
            revision_id=revision,
            scope_mode="campaign",
            campaign_id=campaign,
            role=role,
        ),
        source_reader=c.repo.open_native_source_view(c.space),
    )


def exercise(c, mode):
    before = state(c)
    parent_evidence = decode_native_graph_payload(
        c.repo.get_revision(c.space, before[0].head_revision_id).graph_payload
    ).evidence
    r = request(c, basis(c, mode, "publication:matrix"))
    assert state(c) == before  # Core preview + public WK preparation never write.
    receipt = publish(c, r)
    assert len(LABELS) == 45 and len(TARGET.buddy_to_dm_kind) == 13
    matrix = {}
    vocabulary = TARGET.world_object_loader()
    for label in LABELS:
        term, reverse = mapping.resolve_buddy_predicate_mapping_v4(label, target=TARGET)
        assert reverse is (label == "belongs_to")
        matrix[label] = dict(
            term=term,
            reverse=reverse,
            allowed_pairs=[
                (a, b)
                for a in TARGET.buddy_to_dm_kind
                for b in TARGET.buddy_to_dm_kind
                if mapping.edge_endpoint_kind_admission_reason(
                    buddy_predicate=label,
                    from_buddy_kind=a,
                    to_buddy_kind=b,
                    target=TARGET,
                    vocabulary=vocabulary,
                )
                is None
            ],
        )
    assert (
        canonical_sha256(matrix)
        == "0ac3bb2a41df5ddf129acd3f267bed46940a94676d62d2a028ea65b191a8b371"
    )
    assert len(c.repo.head_events(c.space)) == len(before[1]) + 1
    assert receipt.source_authority_epoch_after == before[2] + int(
        mode == "new_intervals"
    )
    assert len(receipt.result_bindings) == 13 + 39 + 45
    results = {v.client_op_id: v.durable_id for v in receipt.result_bindings}
    revision = receipt.publication_receipt.published_revision_id
    content = decode_native_graph_payload(
        c.repo.get_revision(c.space, revision).graph_payload
    )
    if mode == "existing_support":
        assert content.evidence == parent_evidence
        assert not receipt.proofs and not receipt.bindings
    else:
        assert len(content.evidence) == len(parent_evidence) + 1
        assert all(e in content.evidence for e in parent_evidence)
    entities = {e.entity_id for e in content.entities}
    assertions = {a.assertion_id: a for a in content.assertions}
    assert {results[k] for k in TARGET.buddy_to_dm_kind} == entities
    for kind, term in TARGET.buddy_to_dm_kind.items():
        assert assertions[results[kind + ":kind"]].value.term == term
        assert assertions[results[kind + ":name"]].value.value == "Name " + kind
        assert (
            assertions[results[kind + ":summary"]].value.value
            == f"Description {kind} 🐉\r\nexact"
        )
        assert assertions[results[kind + ":summary"]].subject_entity_id == results[kind]
    for op in r.contribution.items:
        if op.kind != "create_assertion":
            continue
        actual = assertions[results[op.client_op_id]]
        assert actual.metadata == op.metadata
        assert actual.subject_entity_id == results[op.subject.client_op_id]
        if op.value.kind == "entity_ref":
            assert actual.value.entity_id == results[op.value.entity.client_op_id]
            assert actual.predicate == op.predicate
    reversed_edge = assertions[results["edge:belongs_to"]]
    assert reversed_edge.predicate == "dnd5e:owns"
    assert reversed_edge.subject_entity_id == results["npc"]
    assert reversed_edge.value.entity_id == results["creature"]
    assert results["npc"] != results["creature"]
    gm = context(c, revision)
    batch = EntityReadService().get_complete_entities(gm, list(entities))
    assert len(batch) == 13 and all(x.found for x in batch)
    assert sum(len(x.aliases) for x in batch) == 13
    assert {
        h.entity.entity_id
        for h in SearchReadService().search_entities(gm, "Name", limit=100).hits
    } == entities
    assert {
        h.alias.entity_id
        for h in AliasSearchReadService().search_aliases(gm, "Alias", limit=100).hits
    } == entities
    player = context(c, revision, role="player")
    assert not AliasSearchReadService().search_aliases(player, "Alias", limit=100).hits
    assert not SearchReadService().search_entities(player, "Name", limit=100).hits
    assert (
        not SearchReadService()
        .search_entities(context(c, revision, campaign="campaign:foreign"), "Name")
        .hits
    )
    selected = r.contribution.items[1].metadata.evidence_ref_ids[0]
    access = open_native_text_source_access_context(
        repository=c.repo,
        space_id=c.space,
        revision_id=revision,
        domain_contract=c.domain,
        audience_labels=(GM_LABEL,),
    )
    opened = open_admitted_native_text(access, selected)
    start, end = (1, len(RAW)) if mode == "new_intervals" else (0, 1)
    assert opened.status == "available" and opened.body_text == BODY
    assert (opened.span_start_byte, opened.span_end_byte, opened.span_sha256) == (
        start,
        end,
        sha256(RAW[start:end]).hexdigest(),
    )
    assert opened.body_text.encode()[start:end] == RAW[start:end]
    assert publish(c, r) == receipt and recover(c, r) == receipt
    assert len(c.repo.head_events(c.space)) == len(before[1]) + 1
    with pytest.raises(KnowledgePublicationIdempotencyConflictError):
        recover(
            c, r.model_copy(update={"created_at": r.created_at + timedelta(seconds=1)})
        )
    return r, receipt


@pytest.mark.parametrize("mode", ["new_intervals", "existing_support"])
def test_installed_wk_core_full_manual_matrix(mode):
    exercise(setup(), mode)


class MetadataOnly:
    """Public read allowlist; neither current source authority nor write fallback."""

    def __init__(self, repository):
        self.repository = repository

    def __getattr__(self, name):
        assert name in {
            "get_revision",
            "get_publication_receipt",
            "get_native_source_publication_source",
            "get_native_source_publication_receipt",
            "get_native_source_publication_extension_receipt",
        }, name
        return getattr(self.repository, name)


@pytest.mark.parametrize("mode", ["new_intervals", "existing_support"])
def test_metadata_recovery_after_descendant_and_withdrawal(mode):
    c = setup()
    r, receipt = exercise(c, mode)
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand

    child = c.repo.get_revision(
        c.space, receipt.publication_receipt.published_revision_id
    )
    c.repo.publish_revision(
        PublishKnowledgeRevisionCommand(
            space_id=c.space,
            parent_revision_id=child.revision.revision_id,
            expected_parent_revision_id=child.revision.revision_id,
            operation_ids=["descendant:actual"],
            graph_schema=child.revision.graph_schema,
            graph_payload=child.graph_payload,
            domain_contract_ref=child.revision.domain_contract_ref,
            semantic_profile_ref=child.revision.semantic_profile_ref,
            migration_origin_ref=child.revision.migration_origin_ref,
            created_at=NOW + timedelta(minutes=2),
        )
    )
    c.repo.withdraw_native_source(
        space_id=c.space,
        source_artifact_id=c.root.source_artifact_id,
        source_revision_id=c.root.source_revision_id,
    )
    before = state(c)
    assert recover(c, r, MetadataOnly(c.repo)) == receipt
    assert state(c) == before
    assert (
        not AliasSearchReadService()
        .search_aliases(context(c, child.revision.revision_id), "Alias")
        .hits
    )
    with pytest.raises(NativeTextSourceAdmissionIntegrityError):
        publish(c, r)
    assert state(c) == before


def exercise_all_origin_lookup(c, reopen=None):
    extension = NativeSourceEvidenceExtensionV1(
        space_id=c.space,
        extension_id="old:extension",
        original_admission_id=c.root.admission_id,
        source_artifact_id=c.root.source_artifact_id,
        source_revision_id=c.root.source_revision_id,
        expected_body_sha256=sha256(RAW).hexdigest(),
        expected_parent_revision_id=c.repo.get_head(c.space).head_revision_id,
        expected_source_authority_epoch=c.repo.open_native_source_view(c.space).epoch,
        created_at=NOW,
        spans=[
            dict(
                client_ref="old",
                evidence_role="support",
                start_byte=0,
                end_byte=5,
                expected_slice_sha256=sha256(RAW[:5]).hexdigest(),
            )
        ],
    )
    old = publish_native_source_evidence_extension(
        repository=c.repo,
        request=extension,
        domain_contract=c.domain,
        semantic_profile=c.profile,
        audience_labels=(GM_LABEL,),
    )
    new = publish(c, request(c, basis(c, "new_intervals", "new:publication")))
    if reopen is not None:
        c.repo = reopen()
    for span, kind in (
        (c.root.bindings[0].span_id, "admission"),
        (old.proofs[0].span_id, "extension"),
        (new.proofs[0].span_id, "publication"),
    ):
        ref = get_native_source_publication_support(
            repository=c.repo,
            space_id=c.space,
            source_revision_id=c.root.source_revision_id,
            span_id=span,
        )
        assert ref.introducing_kind == kind and ref.proof.span_id == span
        before = state(c)
        r = request(c, basis(c, "existing_support", "reuse:" + kind, ref=ref))
        result = publish(c, r)
        assert not result.proofs and not result.bindings
        assert result.source_authority_epoch_after == before[2]
        assert recover(c, r, MetadataOnly(c.repo)) == result
    assert (
        get_native_source_publication_support(
            repository=c.repo,
            space_id=c.space,
            source_revision_id=c.root.source_revision_id,
            span_id="missing",
        )
        is None
    )
    c.repo.withdraw_native_source(
        space_id=c.space,
        source_artifact_id=c.root.source_artifact_id,
        source_revision_id=c.root.source_revision_id,
    )
    before = state(c)
    assert (
        recover_native_source_evidence_extension(
            repository=c.repo,
            request=extension,
            domain_contract=c.domain,
            semantic_profile=c.profile,
        )
        == old
    )
    assert state(c) == before


def test_bounded_lookup_all_three_origins_and_old_recovery():
    exercise_all_origin_lookup(setup())


@pytest.mark.parametrize("mode", ["new_intervals", "existing_support"])
def test_destructive_intent_refused_and_rejected_intent_sealed(mode):
    c = setup()
    r = request(c, basis(c, mode, "refusal:operation"))
    wire = r.model_dump(mode="json")
    wire["contribution"]["items"].append(
        dict(
            kind="retract_assertion",
            item_id="remove",
            target_assertion_id="foreign:assertion",
        )
    )
    wire["dispositions"].append(dict(item_id="remove", disposition="accepted"))
    before = state(c)
    with pytest.raises(ValidationError, match="create-only"):
        GovernedNativeSourcePublicationV1.model_validate(wire)
    assert state(c) == before
    wire["dispositions"][-1]["disposition"] = "rejected"
    rejected = GovernedNativeSourcePublicationV1.model_validate(wire)
    receipt = publish(c, rejected)
    wire["contribution"]["items"][-1]["target_assertion_id"] = "different:rejected"
    with pytest.raises(KnowledgePublicationIdempotencyConflictError):
        recover(c, GovernedNativeSourcePublicationV1.model_validate(wire))
    assert recover(c, rejected) == receipt


def test_lookup_metadata_does_not_authorize_source_or_context_role():
    c = setup()
    b = basis(c, "existing_support", "private:refusal")
    before = state(c)
    with pytest.raises(NativeTextSourceAdmissionIntegrityError):
        preview_native_source_publication_evidence(
            repository=c.repo,
            request=b,
            domain_contract=c.domain,
            semantic_profile=c.profile,
            audience_labels=(),
        )
    # A real CONTEXT introduction cannot be selected as SUPPORT, even with exact proof metadata.
    extension = NativeSourceEvidenceExtensionV1(
        space_id=c.space,
        extension_id="context:extension",
        original_admission_id=c.root.admission_id,
        source_artifact_id=c.root.source_artifact_id,
        source_revision_id=c.root.source_revision_id,
        expected_body_sha256=sha256(RAW).hexdigest(),
        expected_parent_revision_id=before[0].head_revision_id,
        expected_source_authority_epoch=before[2],
        created_at=NOW,
        spans=[
            dict(
                client_ref="context",
                evidence_role="context",
                start_byte=0,
                end_byte=5,
                expected_slice_sha256=sha256(RAW[:5]).hexdigest(),
            )
        ],
    )
    receipt = publish_native_source_evidence_extension(
        repository=c.repo,
        request=extension,
        domain_contract=c.domain,
        semantic_profile=c.profile,
        audience_labels=(GM_LABEL,),
    )
    assert (
        get_native_source_publication_support(
            repository=c.repo,
            space_id=c.space,
            source_revision_id=c.root.source_revision_id,
            span_id=receipt.proofs[0].span_id,
        )
        is None
    )


def installed_core_identity():
    import importlib.metadata
    import json
    import sys
    from pathlib import Path

    distribution = importlib.metadata.distribution("dungeonmind")
    provenance = json.loads(distribution.read_text("direct_url.json"))
    package = Path(distribution.locate_file("dungeonmind")).resolve()
    modules = {
        name: str(Path(module.__file__).resolve())
        for name, module in list(sys.modules.items())
        if name.startswith("dungeonmind.") and getattr(module, "__file__", None)
    }
    assert not provenance.get("dir_info", {}).get("editable", False)
    assert all(Path(path).is_relative_to(package) for path in modules.values())
    return dict(
        commit=provenance["vcs_info"]["commit_id"],
        package=str(package),
        modules=modules,
    )


def test_exact_installed_package_not_checkout_overlay():
    import importlib.metadata
    import json
    import tomllib
    from pathlib import Path

    project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
    expected = project["tool"]["uv"]["sources"]["dungeonmind"]["rev"]
    assert installed_core_identity()["commit"] == expected
    wk_url = json.loads(
        importlib.metadata.distribution("worldkeeper").read_text("direct_url.json")
    )
    assert wk_url["vcs_info"]["commit_id"] == "ef9c50f2d6aa89a35e9408f83fc4d0ba47825ca2"


@pytest.fixture
def sql_repository(monkeypatch, record_property):
    """Only a uniquely owned 32903 DB; migration scripts are never runtime imports."""
    import json
    import os
    import subprocess
    from pathlib import Path
    from uuid import uuid4

    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    from alembic import command
    from alembic.config import Config
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase,
        PostgresNativeSourceEvidenceRepository,
    )

    admin = os.environ.get("DMB_NATIVE_RECAP_TEST_ADMIN_DSN", "")
    assert admin, (
        "Owning SQL proof requires the isolated test service; no skip or live fallback"
    )
    params = conninfo_to_dict(admin)
    assert (
        params["host"] in {"localhost", "127.0.0.1", "::1"}
        and params["port"] == "32903"
    )
    core_root = Path(os.environ["DMB_NATIVE_RECAP_TEST_CORE_ROOT"]).resolve()
    migration = (
        core_root / "migrations/versions/0023_governed_native_source_publications.py"
    )
    assert migration.is_file(), "Core239 migration tree is not ready"
    before = installed_core_identity()
    migration_sha = sha256(migration.read_bytes()).hexdigest()
    migration_tree = {
        str(p.relative_to(core_root)): sha256(p.read_bytes()).hexdigest()
        for p in sorted((core_root / "migrations").rglob("*.py"))
    }
    migration_head = subprocess.check_output(
        ["git", "-C", str(core_root), "rev-parse", "HEAD"], text=True
    ).strip()
    name = "v10_buddy_source_pub_" + uuid4().hex[:12]
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    dsn = make_conninfo(admin, dbname=name)
    # Alembic reads a URL; the repository consumes the same isolated database.
    from sqlalchemy import URL

    url = URL.create(
        "postgresql",
        username=params.get("user"),
        password=params.get("password"),
        host=params["host"],
        port=32903,
        database=name,
    ).render_as_string(hide_password=False)
    lifecycle = dict(
        name=name,
        port=32903,
        created=True,
        dropped=False,
        installed_before=before,
        migration_head=migration_head,
        migration_sha256=migration_sha,
    )
    try:
        monkeypatch.setenv("DUNGEONMIND_DATABASE_URL", url)
        cfg = Config()
        cfg.set_main_option("script_location", str(core_root / "migrations"))
        command.upgrade(cfg, "head")
        assert installed_core_identity()["commit"] == before["commit"]
        database = PostgresDatabase(dsn)
        yield PostgresNativeSourceEvidenceRepository(database), database
    finally:
        # No forced termination: unresolved active use prevents cleanup and is retained as failure.
        with psycopg.connect(admin, autocommit=True) as conn:
            active = conn.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname=%s", (name,)
            ).fetchone()[0]
            lifecycle["connections_before_drop"] = active
            assert active == 0, "Fixture database still in use; do not delete it"
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
            lifecycle["dropped"] = True
        after = installed_core_identity()
        assert (
            after["commit"] == before["commit"]
            and after["package"] == before["package"]
        )
        assert all(after["modules"].get(k) == v for k, v in before["modules"].items())
        assert sha256(migration.read_bytes()).hexdigest() == migration_sha
        assert {
            str(p.relative_to(core_root)): sha256(p.read_bytes()).hexdigest()
            for p in sorted((core_root / "migrations").rglob("*.py"))
        } == migration_tree
        lifecycle["migration_tree_sha256"] = canonical_sha256(migration_tree)
        lifecycle["migration_head_after"] = subprocess.check_output(
            ["git", "-C", str(core_root), "rev-parse", "HEAD"], text=True
        ).strip()
        lifecycle["installed_after"] = after
        record_property("sql_lifecycle", json.dumps(lifecycle, sort_keys=True))
        print(
            "ADOPTION_SQL_LIFECYCLE",
            json.dumps(
                {k: v for k, v in lifecycle.items() if not k.startswith("installed_")},
                sort_keys=True,
            ),
        )


@pytest.mark.parametrize("mode", ["new_intervals", "existing_support"])
def test_sql_installed_composition_reopen_recovery(sql_repository, mode):
    from dungeonmind.infrastructure.postgres import (
        PostgresNativeSourceEvidenceRepository,
    )

    repo, database = sql_repository
    c = setup(repo)
    r, receipt = exercise(c, mode)
    c.repo = PostgresNativeSourceEvidenceRepository(database)
    assert recover(c, r, MetadataOnly(c.repo)) == receipt
    ref_span = (
        receipt.proofs[0].span_id
        if mode == "new_intervals"
        else c.root.bindings[0].span_id
    )
    ref = get_native_source_publication_support(
        repository=c.repo,
        space_id=c.space,
        source_revision_id=c.root.source_revision_id,
        span_id=ref_span,
    )
    assert ref.introducing_kind == (
        "publication" if mode == "new_intervals" else "admission"
    )
    reuse = request(c, basis(c, "existing_support", "sql:reuse", ref=ref))
    reused = publish(c, reuse)
    assert (
        not reused.proofs
        and reused.source_authority_epoch_after == receipt.source_authority_epoch_after
    )
    c.repo.withdraw_native_source(
        space_id=c.space,
        source_artifact_id=c.root.source_artifact_id,
        source_revision_id=c.root.source_revision_id,
    )
    before = state(c)
    assert recover(c, r, MetadataOnly(c.repo)) == receipt
    assert recover(c, reuse, MetadataOnly(c.repo)) == reused
    assert state(c) == before
    with pytest.raises(NativeTextSourceAdmissionIntegrityError):
        publish(c, reuse)
    assert state(c) == before


@pytest.mark.parametrize("mode", ["new_intervals", "existing_support"])
def test_sql_complete_rollback(sql_repository, mode, monkeypatch):
    repo, database = sql_repository
    c = setup(repo)
    r = request(c, basis(c, mode, "sql:rollback"))
    tables = (
        "knowledge_revisions",
        "knowledge_head_events",
        "knowledge_publication_receipts",
        "knowledge_native_source_publications",
        "knowledge_native_source_spans",
    )

    def counts():
        from psycopg import sql

        with database.transaction() as conn:
            return {
                table: conn.execute(
                    sql.SQL("SELECT count(*) AS n FROM dungeonmind.{}").format(
                        sql.Identifier(table)
                    )
                ).fetchone()["n"]
                for table in tables
            }

    before, rows = state(c), counts()
    fired = []

    def fail():
        fired.append(True)
        raise RuntimeError("actual composed receipt insertion fault")

    with monkeypatch.context() as patch:
        patch.setattr(repo, "_after_native_receipt_insert", fail)
        with pytest.raises(RuntimeError, match="actual composed receipt"):
            publish(c, r)
    assert fired and state(c) == before and counts() == rows
    assert recover(c, r) is None
    receipt = publish(c, r)
    assert recover(c, r) == receipt


def test_sql_reopened_bounded_lookup_all_origins_and_old_recovery(sql_repository):
    from dungeonmind.infrastructure.postgres import (
        PostgresNativeSourceEvidenceRepository,
    )

    repo, database = sql_repository
    exercise_all_origin_lookup(
        setup(repo), reopen=lambda: PostgresNativeSourceEvidenceRepository(database)
    )


@pytest.mark.parametrize("mode", ["new_intervals", "existing_support"])
@pytest.mark.parametrize("empty", [True, False])
def test_optional_aliases_and_complete_rejected_intent(mode, empty):
    c = setup()
    r = request(c, basis(c, mode, "optional:aliases"))
    if empty:
        alias_ids = {a.item_id for a in r.aliases}
        r.aliases = []
        r.dispositions = [d for d in r.dispositions if d.item_id not in alias_ids]
    else:
        for decision in r.dispositions:
            if decision.item_id.startswith("alias:"):
                decision.disposition = "rejected"
    receipt = publish(c, r)
    child = c.repo.get_revision(
        c.space, receipt.publication_receipt.published_revision_id
    )
    assert not decode_native_graph_payload(child.graph_payload).aliases
    assert recover(c, r) == receipt
    if not empty:
        before = state(c)
        r.aliases[0].alias_text = "changed rejected alias intent"
        with pytest.raises(KnowledgePublicationIdempotencyConflictError):
            recover(c, r)
        assert state(c) == before
