"""V6.1 executable proof for the Buddy-owned vNext domain runtime seam."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dungeonmind.application.vnext import (
    InMemoryKnowledgeSourceReader,
    build_parsed_knowledge_revision,
)
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext import (
    Assertion,
    DomainContractRef,
    Entity,
    EvidenceRefV3,
    IdentityAlias,
    KnowledgeRevision,
    ProjectionRequest,
    SourceArtifactV3,
    SourceRevisionV2,
)
from dungeonmind.domain.canonical import canonical_sha256
from graph_memory.vnext import (
    DUNGEONBUDDY_DOMAIN_DIGEST,
    DUNGEONBUDDY_POLICY_ID,
    DUNGEONBUDDY_PROFILE_DIGEST,
    DungeonBuddyVNextProjectionInput,
    build_dungeonbuddy_projection_request,
    build_dungeonbuddy_read_context,
    dungeonbuddy_dnd5e_custom_predicate_profile,
    dungeonbuddy_dnd5e_semantic_profile,
    dungeonbuddy_world_domain_contract,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    ROOT / "tests/fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json"
)
DOMAIN_PATH = ROOT / "Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v2.json"
PROFILE_PATH = ROOT / "Docs/Contracts/vnext/dungeonbuddy_dnd5e_semantic_profile_v2.json"
CUSTOM_PROFILE_PATH = ROOT / "Docs/Contracts/vnext/dungeonbuddy_dnd5e_semantic_profile_v3.json"


@pytest.fixture(scope="module")
def preservation() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _input(data: dict) -> DungeonBuddyVNextProjectionInput:
    return DungeonBuddyVNextProjectionInput(**data)


def test_runtime_descriptors_match_checked_in_canonical_identity() -> None:
    runtime_domain = dungeonbuddy_world_domain_contract()
    runtime_profile = dungeonbuddy_dnd5e_semantic_profile()
    checked_domain = json.loads(DOMAIN_PATH.read_text(encoding="utf-8"))
    checked_profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

    assert runtime_domain.model_dump(mode="json") == checked_domain
    assert runtime_profile.model_dump(mode="json") == checked_profile
    assert canonical_sha256(runtime_domain.model_dump(mode="json")) == (
        DUNGEONBUDDY_DOMAIN_DIGEST
    )
    assert canonical_sha256(runtime_profile.model_dump(mode="json")) == (
        DUNGEONBUDDY_PROFILE_DIGEST
    )
    assert runtime_domain.domain_revision == "2"
    assert runtime_domain.admission_policy_id == DUNGEONBUDDY_POLICY_ID


def test_custom_profile_is_a_distinct_immutable_opt_in_revision() -> None:
    profile = dungeonbuddy_dnd5e_custom_predicate_profile()
    checked = json.loads(CUSTOM_PROFILE_PATH.read_text(encoding="utf-8"))
    assert profile.model_dump(mode="json") == checked
    assert profile.profile_revision == "2"
    assert profile.schema_version == "dm_semantic_profile_v3"
    assert profile.open_predicate_namespaces[0].namespace == "dungeonbuddy.custom"
    assert profile.open_predicate_namespaces[0].allowed_value_kinds == ["entity_ref"]
    assert dungeonbuddy_dnd5e_semantic_profile().profile_revision == "1"


def test_custom_predicate_read_admission_uses_exact_pinned_v3_profile(preservation: dict) -> None:
    new_preservation = copy.deepcopy(preservation)
    profile = dungeonbuddy_dnd5e_custom_predicate_profile()
    new_preservation["semantic_profile_ref"]["profile_revision"] = profile.profile_revision
    new_preservation["semantic_profile_ref"]["descriptor_sha256"] = canonical_sha256(
        profile.model_dump(mode="json")
    )
    relationship = next(
        item for item in new_preservation["assertions"] if item["predicate"] == "dnd5e:located_in"
    )
    for assertion_id, predicate, value in (
        ("as:custom-works-at", "dungeonbuddy.custom:works_at", relationship["value"]),
        ("as:unscoped-works-at", "dungeonbuddy:works_at", relationship["value"]),
        ("as:wrong-kind", "dungeonbuddy.custom:has_motto", {"kind": "literal", "value": "A"}),
    ):
        item = copy.deepcopy(relationship)
        item.update(assertion_id=assertion_id, predicate=predicate, value=value)
        new_preservation["assertions"].append(item)

    context, result = _admission(
        new_preservation,
        DungeonBuddyVNextProjectionInput(world_id="eldyrwild", scope_mode="world", role="gm"),
    )
    admitted = set(result.admitted_assertion_ids)
    assert context.semantic_profile.schema_version == "dm_semantic_profile_v3"
    assert "as:custom-works-at" in admitted
    assert "as:unscoped-works-at" not in admitted
    assert "as:wrong-kind" not in admitted


def test_mapper_preserves_all_accepted_request_cases(preservation: dict) -> None:
    for case in preservation["request_context_cases"]:
        request = build_dungeonbuddy_projection_request(_input(case["buddy_input"]))
        assert request == ProjectionRequest.model_validate(case["projection_request"])


@pytest.mark.parametrize(
    "projection_input",
    [
        DungeonBuddyVNextProjectionInput(world_id="", scope_mode="world", role="gm"),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="campaign", role="gm"
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="unknown", role="gm"  # type: ignore[arg-type]
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="world", role="GM"  # type: ignore[arg-type]
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="world", role=" player "  # type: ignore[arg-type]
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="world", role="gm", campaign_id="campaign", session_id=""
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world",
            scope_mode="campaign",
            role="gm",
            campaign_id=" ",
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world", scope_mode="world", role="gm", revision_id=" "
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world",
            scope_mode="world",
            role="player",
            standing_selector=("provisional",),
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world",
            scope_mode="world",
            role="player",
            standing_selector=("retracted",),
        ),
        DungeonBuddyVNextProjectionInput(
            world_id="world",
            scope_mode="world",
            role="gm",
            standing_selector=("retracted",),
        ),
    ],
)
def test_mapper_rejects_invalid_or_unauthorized_inputs(
    projection_input: DungeonBuddyVNextProjectionInput,
) -> None:
    with pytest.raises(ValueError):
        build_dungeonbuddy_projection_request(projection_input)


def test_mapper_preserves_exact_identifier_bytes_and_revision() -> None:
    request = build_dungeonbuddy_projection_request(
        DungeonBuddyVNextProjectionInput(
            world_id=" World Exact ",
            scope_mode="campaign",
            role="gm",
            campaign_id=" Campaign Exact ",
            session_id=" Session Exact ",
            revision_id=" Revision Exact ",
            standing_selector=("established",),
        )
    )
    assert request.space_id == " World Exact "
    assert request.revision_id == " Revision Exact "
    assert request.scope_selector.bindings[0].value == " Campaign Exact "
    assert request.focus[0].id == " Campaign Exact "
    assert request.focus[1].id == " Session Exact "
    assert request.standing_selector == ["established"]


def _runtime_witness(preservation: dict):
    assertions = copy.deepcopy(preservation["assertions"])
    other_campaign = copy.deepcopy(assertions[2])
    other_campaign["assertion_id"] = "as:brennan-name-other-campaign"
    other_campaign["metadata"]["scope"][0]["value"] = "campaign-other"
    assertions.append(other_campaign)

    revision = KnowledgeRevision(
        space_id=preservation["space_id"],
        revision_id="rev:v6-1-witness",
        created_at=datetime(2026, 9, 24, tzinfo=UTC),
        operation_ids=["op:v6-1-witness"],
        graph_schema="dungeonbuddy.test:v6_1",
        graph_payload_sha256="1" * 64,
        domain_contract_ref=DomainContractRef.model_validate(
            preservation["domain_contract_ref"]
        ),
        semantic_profile_ref=SemanticProfileRef.model_validate(
            preservation["semantic_profile_ref"]
        ),
    )
    parsed = build_parsed_knowledge_revision(
        revision,
        entities=[Entity.model_validate(item) for item in preservation["entities"]],
        assertions=[Assertion.model_validate(item) for item in assertions],
        aliases=[
            IdentityAlias.model_validate(item) for item in preservation["aliases"]
        ],
        evidence=[
            EvidenceRefV3.model_validate(item) for item in preservation["evidence"]
        ],
    )
    reader = InMemoryKnowledgeSourceReader(
        artifacts={
            item["source_artifact_id"]: SourceArtifactV3.model_validate(item)
            for item in preservation["sources"]
        },
        revisions={
            item["source_revision_id"]: SourceRevisionV2.model_validate(item)
            for item in preservation["source_revisions"]
        },
    )
    return parsed, reader


def _admission(preservation: dict, projection_input: DungeonBuddyVNextProjectionInput):
    parsed, reader = _runtime_witness(preservation)
    context = build_dungeonbuddy_read_context(
        parsed_revision=parsed,
        projection_input=projection_input,
        source_reader=reader,
    )
    from dungeonmind.application.vnext.admission import AlwaysAdmitPolicy

    assert type(context.domain_policy) is AlwaysAdmitPolicy
    result = context.admit_candidates(tuple(parsed.assertions_by_id))
    return context, result


def test_campaign_gm_admission_preserves_expected_semantics(preservation: dict) -> None:
    context, result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            role="gm",
        ),
    )
    assert set(result.admitted_assertion_ids) == {
        "as:mireward-classification",
        "as:brennan-classification",
        "as:brennan-name",
        "as:brennan-secret-plan",
        "as:brennan-located-in-mireward",
    }
    assert "as:brennan-retracted-rumor" not in result.admitted_assertion_ids
    assert "as:brennan-name-other-campaign" not in result.admitted_assertion_ids
    assert result.work.policy_evaluations == len(result.admitted_assertion_ids)
    assert context.domain_policy.policy_id == context.domain_contract.admission_policy_id


def test_campaign_player_cannot_recover_generic_rejections(preservation: dict) -> None:
    _context, result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            role="player",
        ),
    )
    admitted = set(result.admitted_assertion_ids)
    assert "as:mireward-classification" in admitted
    assert "as:brennan-classification" in admitted
    assert "as:brennan-name" in admitted
    assert "as:brennan-secret-plan" not in admitted
    assert "as:brennan-retracted-rumor" not in admitted
    assert "as:brennan-name-other-campaign" not in admitted
    assert result.work.policy_evaluations == len(admitted)


def test_world_gm_wildcard_admits_campaign_scoped_assertions(preservation: dict) -> None:
    _context, result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild", scope_mode="world", role="gm"
        ),
    )
    assert "as:brennan-name" in result.admitted_assertion_ids
    assert "as:brennan-name-other-campaign" in result.admitted_assertion_ids


def test_session_focus_is_preserved_without_changing_admission(preservation: dict) -> None:
    base, base_result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            role="gm",
        ),
    )
    focused, focused_result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            session_id="session-28",
            role="gm",
        ),
    )
    assert focused_result.admitted_assertion_ids == base_result.admitted_assertion_ids
    assert [(item.kind, item.id) for item in focused.request.focus] == [
        ("dungeonbuddy.focus:campaign", "campaign-longmont"),
        ("dungeonbuddy.focus:session", "session-28"),
    ]
    assert base.request.focus == []


def test_missing_source_is_rejected_before_buddy_policy(preservation: dict) -> None:
    parsed, _reader = _runtime_witness(preservation)
    context = build_dungeonbuddy_read_context(
        parsed_revision=parsed,
        projection_input=DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            role="gm",
        ),
        source_reader=InMemoryKnowledgeSourceReader(),
    )
    result = context.admit_candidates(["as:brennan-name"])
    assert result.admitted_assertion_ids == ()
    assert result.excluded[0].reason == "source_missing"
    assert result.work.policy_evaluations == 0


def test_corrected_evidence_and_source_metadata_pass_unchanged(preservation: dict) -> None:
    assert preservation["evidence"][0]["domain_metadata"][0] == {
        "schema": "dungeonbuddy.domain_metadata:world_context_v1",
        "payload": {"context_type": "arrival_scene"},
    }
    assert preservation["sources"][0]["domain_metadata"][0]["schema"] == (
        "dungeonbuddy.source:context_v1"
    )
    _context, result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild",
            scope_mode="campaign",
            campaign_id="campaign-longmont",
            role="gm",
        ),
    )
    assert "as:brennan-name" in result.admitted_assertion_ids


def test_context_request_is_a_real_projection_request(preservation: dict) -> None:
    context, _result = _admission(
        preservation,
        DungeonBuddyVNextProjectionInput(
            world_id="eldyrwild", scope_mode="world", role="gm"
        ),
    )
    assert isinstance(context.request, ProjectionRequest)


# Revision-4 declaration capability: public WK/Core, no product/source authority.
def _manual_profile():
    from graph_memory.vnext.domain_runtime import dungeonbuddy_dnd5e_manual_profile

    return dungeonbuddy_dnd5e_manual_profile()


def _manual_catalog():
    from apps.live_control_server.integrations.dungeonmind import assertion_qualification as c

    target = c.CONNECTED_PLACE_OPERATION_V7_TARGET
    labels = sorted(
        set(c._DIRECT_PREDICATE_MAP)
        | set(c._RENAME_PREDICATE_MAP)
        | set(c._REVERSE_ENDPOINT_PREDICATE_MAP)
        | set(target.predicate_map_additions or {})
    )
    return c, target, labels


def test_manual_profile_canonical_additive_and_detached() -> None:
    from graph_memory.vnext.domain_runtime import (
        DUNGEONBUDDY_MANUAL_PROFILE_DIGEST,
        dungeonbuddy_dnd5e_observation_profile,
    )

    profile = _manual_profile()
    raw = profile.model_dump(mode="json")
    checked = json.loads((ROOT / "Docs/Contracts/vnext/dungeonbuddy_dnd5e_manual_semantic_profile_v4.json").read_text())
    assert raw == checked
    assert canonical_sha256(raw) == DUNGEONBUDDY_MANUAL_PROFILE_DIGEST
    assert profile.profile_revision == "4"
    old = dungeonbuddy_dnd5e_observation_profile().model_dump(mode="json")
    assert all(p in raw["predicates"] for p in old["predicates"])
    assert set(old["classification_terms"]) <= set(raw["classification_terms"])
    assert raw["open_predicate_namespaces"] == old["open_predicate_namespaces"]
    profile.predicates.clear()
    assert _manual_profile().model_dump(mode="json") == checked
    assert dungeonbuddy_dnd5e_semantic_profile().profile_revision == "1"


def test_manual_profile_closed_catalog_direction_and_endpoint_matrix() -> None:
    c, target, labels = _manual_catalog()
    profile = _manual_profile()
    declarations = {p.term: p for p in profile.predicates}
    assert len(labels) == 45
    assert len(declarations) == len(profile.predicates)
    assert set(target.buddy_to_dm_kind.values()) <= set(profile.classification_terms)
    vocabulary = target.world_object_loader()
    matrix = {}
    for label in labels:
        term, reverse = c.resolve_buddy_predicate_mapping_v4(label, target=target)
        assert declarations[term].allowed_value_kinds == ["entity_ref"]
        expected_reverse = label == "belongs_to"
        assert reverse is expected_reverse
        allowed = [(a, b) for a in target.buddy_to_dm_kind for b in target.buddy_to_dm_kind
                   if c.edge_endpoint_kind_admission_reason(
                       buddy_predicate=label, from_buddy_kind=a, to_buddy_kind=b,
                       target=target, vocabulary=vocabulary) is None]
        assert allowed, label
        matrix[label] = {"term": term, "reverse": reverse, "allowed_pairs": allowed}
    assert canonical_sha256(matrix) == "0ac3bb2a41df5ddf129acd3f267bed46940a94676d62d2a028ea65b191a8b371"
    assert c.resolve_buddy_predicate_mapping_v4("not_a_manual_predicate", target=target) is None
    assert "dnd5e:not_a_manual_predicate" not in declarations
    assert c.edge_endpoint_kind_admission_reason(
        buddy_predicate="owns", from_buddy_kind="creature", to_buddy_kind="npc",
        target=target, vocabulary=vocabulary) is not None
    assert c.edge_endpoint_kind_admission_reason(
        buddy_predicate="belongs_to", from_buddy_kind="creature", to_buddy_kind="npc",
        target=target, vocabulary=vocabulary) is None


def test_manual_profile_exact_ref_resolution() -> None:
    from graph_memory.vnext.domain_runtime import (
        DungeonBuddyDescriptorError, resolve_dungeonbuddy_descriptors,
    )

    domain = dungeonbuddy_world_domain_contract()
    profile = _manual_profile()
    domain_ref = DomainContractRef(domain_id=domain.domain_id, domain_revision=domain.domain_revision,
                                   descriptor_sha256=canonical_sha256(domain.model_dump(mode="json")))
    ref = SemanticProfileRef(profile_id=profile.profile_id, profile_revision="4",
                             descriptor_sha256=canonical_sha256(profile.model_dump(mode="json")))
    assert resolve_dungeonbuddy_descriptors(domain_ref=domain_ref, profile_ref=ref)[1] == profile
    for change in ({"descriptor_sha256": "0" * 64}, {"profile_revision": "999"}):
        with pytest.raises(DungeonBuddyDescriptorError):
            resolve_dungeonbuddy_descriptors(domain_ref=domain_ref, profile_ref=ref.model_copy(update=change))


def _manual_wk(profile):
    from dungeonmind.application.vnext import initialize_empty_knowledge_space
    from dungeonmind.infrastructure.memory.vnext_knowledge import InMemoryKnowledgeRevisionRepository
    from worldkeeper.integrations.dungeonmind import DungeonMindWorldKeeperRuntime

    repository = InMemoryKnowledgeRevisionRepository()
    domain = dungeonbuddy_world_domain_contract()
    now = datetime(2026, 11, 19, tzinfo=UTC)
    initialize_empty_knowledge_space(repository=repository, space_id="manual-profile-proof",
                                     initialization_id="manual-profile-genesis", created_at=now,
                                     domain_contract=domain, semantic_profile=profile)
    runtime = DungeonMindWorldKeeperRuntime(repository=repository, domain_contract=domain,
                                           semantic_profile=profile, clock=lambda: now,
                                           prepared_id_factory=lambda: "manual-profile-operation")
    return repository, runtime


def _manual_ops(kind_terms, predicate="dnd5e:owns"):
    from worldkeeper.application import contracts as wk

    meta = wk.AssertionMetadata(scope=(), visibility=wk.Visibility("labels_any", ("dungeonbuddy.visibility:gm",)),
                                epistemic_basis="asserted", claim_mode="dungeonbuddy.claim:fact",
                                standing="established", temporal_scope=wk.TemporalScope(kind="unknown"),
                                evidence_ref_ids=())
    objects = tuple(wk.CreateObject(f"kind-{i}", (
        wk.CreateFact(f"classification-{i}", "dnd5e:classification", wk.TermRefFactValue(term), meta),
    )) for i, term in enumerate(kind_terms))
    return objects + (wk.CreateRelationship("manual-edge", wk.ResultOf("kind-0"), predicate,
                                            wk.ResultOf("kind-1"), meta),)


def test_manual_profile_public_wk_prepare_all_kinds_and_core_commit() -> None:
    from worldkeeper.application import contracts as wk

    _, target, _ = _manual_catalog()
    repo, runtime = _manual_wk(_manual_profile())
    before = repo.get_head("manual-profile-proof")
    prepared = runtime.prepare_change(wk.WorldChangeIntent("manual-profile-proof", "manual catalog declaration proof",
                                                          _manual_ops(tuple(target.buddy_to_dm_kind.values()))))
    assert repo.get_head("manual-profile-proof") == before
    result = runtime.commit_prepared_change(prepared, confirmed_by="declaration-proof")
    assert len(result.object_results) == 13
    assert len(result.assertion_results) == 14
    from dungeonmind.application.vnext.admission import semantic_profile_passes
    from dungeonmind.application.vnext.materialization import decode_native_graph_payload

    child = repo.get_revision("manual-profile-proof", result.child_revision_id)
    parsed = build_parsed_knowledge_revision(child.revision,
        decoded_content=decode_native_graph_payload(child.graph_payload))
    classifications = [a for a in parsed.assertions_by_id.values() if a.predicate == "dnd5e:classification"]
    assert {a.value.term for a in classifications} == set(target.buddy_to_dm_kind.values())
    assert all(semantic_profile_passes(a, semantic_profile=_manual_profile()) is None
               for a in parsed.assertions_by_id.values())
    assert repo.get_head("manual-profile-proof") != before


def test_manual_profile_public_wk_refusal_zero_mutation() -> None:
    from worldkeeper.application import contracts as wk
    from worldkeeper.application.preparation import InvalidWorldChange

    repo, runtime = _manual_wk(_manual_profile())
    before = repo.get_head("manual-profile-proof")
    ops = _manual_ops(("dnd5e:npc", "dnd5e:location"))
    from dataclasses import replace

    bad = (*ops[:-1], replace(ops[-1], source=wk.ResultOf("missing")))
    with pytest.raises(InvalidWorldChange, match="result_of_missing_create_object"):
        runtime.prepare_change(wk.WorldChangeIntent("manual-profile-proof", "refusal proof", bad))
    assert repo.get_head("manual-profile-proof") == before


def test_manual_profile_semantic_gate_is_distinct_from_wk_structure() -> None:
    from dungeonmind.application.vnext.admission import semantic_profile_passes
    from dungeonmind.contracts.vnext.domain import AssertionMetadata, EntityRefValue, TermRefValue

    meta = AssertionMetadata(visibility={"kind": "labels_any", "labels": ["dungeonbuddy.visibility:gm"]},
                             epistemic_basis="asserted", claim_mode="dungeonbuddy.claim:fact",
                             standing="established", temporal_scope={"kind": "unknown"})
    c, target, labels = _manual_catalog()
    new = _manual_profile()
    old = dungeonbuddy_dnd5e_semantic_profile()
    for label in labels:
        term, _ = c.resolve_buddy_predicate_mapping_v4(label, target=target)
        assertion = Assertion(assertion_id="edge", subject_entity_id="left", predicate=term,
                              value=EntityRefValue(entity_id="right"), metadata=meta)
        assert semantic_profile_passes(assertion, semantic_profile=new) is None
        if term != "dnd5e:located_in":
            assert semantic_profile_passes(assertion, semantic_profile=old) == "semantic_profile"
    for term in target.buddy_to_dm_kind.values():
        assertion = Assertion(assertion_id="kind", subject_entity_id="left", predicate="dnd5e:classification",
                              value=TermRefValue(term=term), metadata=meta)
        # Core's structural predicate/value-kind gate does NOT enforce classification membership.
        assert semantic_profile_passes(assertion, semantic_profile=old) is None
        assert semantic_profile_passes(assertion, semantic_profile=new) is None
    unknown = assertion.model_copy(update={"predicate": "dnd5e:unknown_manual"})
    assert semantic_profile_passes(unknown, semantic_profile=new) == "semantic_profile"


def test_manual_profile_wk_exact_descriptor_refusal() -> None:
    from worldkeeper.application import contracts as wk
    from worldkeeper.application.preparation import InvalidWorldChange
    from worldkeeper.integrations.dungeonmind import DungeonMindWorldKeeperRuntime

    repo, _ = _manual_wk(_manual_profile())
    before = repo.get_head("manual-profile-proof")
    runtime = DungeonMindWorldKeeperRuntime(repository=repo,
        domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_semantic_profile(),
        clock=lambda: datetime(2026, 11, 19, tzinfo=UTC))
    with pytest.raises(InvalidWorldChange, match="semantic_profile_mismatch"):
        runtime.prepare_change(wk.WorldChangeIntent("manual-profile-proof", "wrong profile",
                                                   _manual_ops(("dnd5e:npc", "dnd5e:location"))))
    assert repo.get_head("manual-profile-proof") == before


@pytest.mark.parametrize("revision,observation,precedence", [
    ("1", False, False), ("2", False, True), ("3", True, True), ("4", True, True),
])
def test_exact_profile_predicate_capability_matrix(revision, observation, precedence):
    from graph_memory.vnext.domain_runtime import (
        dungeonbuddy_dnd5e_observation_profile, dungeonbuddy_publication_capabilities,
    )

    profiles = {"1": dungeonbuddy_dnd5e_semantic_profile, "2": dungeonbuddy_dnd5e_custom_predicate_profile,
                "3": dungeonbuddy_dnd5e_observation_profile, "4": _manual_profile}
    domain = dungeonbuddy_world_domain_contract()
    profile = profiles[revision]()
    kwargs = dict(domain_ref=DomainContractRef(domain_id=domain.domain_id,
        domain_revision=domain.domain_revision, descriptor_sha256=canonical_sha256(domain.model_dump(mode="json"))),
        profile_ref=SemanticProfileRef(profile_id=profile.profile_id, profile_revision=revision,
            descriptor_sha256=canonical_sha256(profile.model_dump(mode="json"))))
    capabilities = dungeonbuddy_publication_capabilities(**kwargs)
    assert capabilities.reviewed_source_observation is observation
    assert capabilities.source_precedence is precedence
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        capabilities.source_precedence = False



@pytest.mark.parametrize("change", [{"descriptor_sha256": "0" * 64}, {"profile_revision": "999"},
                                    {"profile_id": "foreign.profile"}])
def test_profile_capability_rejects_unverified_references(change):
    from graph_memory.vnext.domain_runtime import DungeonBuddyDescriptorError, dungeonbuddy_publication_capabilities

    domain = dungeonbuddy_world_domain_contract()
    profile = _manual_profile()
    domain_ref = DomainContractRef(domain_id=domain.domain_id, domain_revision=domain.domain_revision,
                                  descriptor_sha256=canonical_sha256(domain.model_dump(mode="json")))
    profile_ref = SemanticProfileRef(profile_id=profile.profile_id, profile_revision="4",
                                    descriptor_sha256=canonical_sha256(profile.model_dump(mode="json")))
    with pytest.raises(DungeonBuddyDescriptorError):
        dungeonbuddy_publication_capabilities(domain_ref=domain_ref,
            profile_ref=profile_ref.model_copy(update=change))
    with pytest.raises(DungeonBuddyDescriptorError):
        dungeonbuddy_publication_capabilities(domain_ref=domain_ref.model_copy(update={"descriptor_sha256": "0" * 64}),
            profile_ref=profile_ref)
