"""Tests for V0.2: DungeonBuddy contract pin and domain preservation proof.

Validates:
1. Exact DungeonMind provider artifact pin and aggregate matching.
2. Recomputation of provider aggregate according to the canonical algorithm.
3. Buddy-owned DomainContractDescriptor and SemanticProfileDescriptorV2 fixtures.
4. SemanticProfileRef and DomainContractRef canonical digest parity.
5. Current Buddy request semantics (campaign/world scope, GM/PLAYER visibility, session focus as presentation).
6. Knowledge preservation (world-global, campaign-scoped, visibility, standing, fictional-time).
7. Representative World object representation (Entity + TermRef/Literal/EntityRef assertions + alias).
8. Source classification and metadata mapping across 100% of KNOWN_SOURCE_DOMAINS.
9. Governed candidate/proposal representation without Kernel epistemic enum drift.
10. Acceptance artifact integrity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext import (
    Assertion,
    ContributionDisposition,
    DomainContractDescriptor,
    DomainContractRef,
    Entity,
    EvidenceRefV3,
    FocusRef,
    IdentityAlias,
    KnowledgeContribution,
    KnowledgeStanding,
    ProjectionRequest,
    ScopeBinding,
    ScopeSelector,
    SemanticProfileDescriptorV2,
    SourceArtifactV3,
    SourceRevisionV2,
    canonical_json,
    sha256,
)
from graph_memory.evidence.source_domain import KNOWN_SOURCE_DOMAINS

ROOT = Path(__file__).resolve().parents[1]
PROVIDER_BUNDLE_PATH = ROOT / "Docs/Contracts/dungeonmind/dm_vnext_contract_v1.json"
PIN_MANIFEST_PATH = ROOT / "Docs/Contracts/dungeonmind/dm_vnext_contract_pin_v1.json"
DOMAIN_CONTRACT_PATH = ROOT / "Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v1.json"
SEMANTIC_PROFILE_PATH = ROOT / "Docs/Contracts/vnext/dungeonbuddy_dnd5e_semantic_profile_v2.json"
PRESERVATION_FIXTURE_PATH = ROOT / "tests/fixtures/vnext/dungeonbuddy_domain_preservation_v1.json"
ACCEPTANCE_ARTIFACT_PATH = ROOT / "Docs/Contracts/vnext/dmb_v0_2_contract_acceptance_v1.json"

EXPECTED_PROVIDER_AGGREGATE = "fd04a9047b8ed79aaa5e710b2247ce1b2654c0e44e05d24fafb2adecb9e7b7ea"
EXPECTED_PROVIDER_COMMIT = "63ec810a02f18c4e25af228f6fdb19d99d12579e"
EXPECTED_BUDDY_BASE = "68a4abae9635211bc773d8480ec6ce46b10ada5e"
EXPECTED_REVIEWED_HEAD = "6293a1e635a74eaf3a80d87e931c236de583065f"
EXPECTED_ACCEPTED_V0_1_HEAD = "ba2ec6dc16137b57aab4ca7544f00eb4a5802a15"


@pytest.fixture(scope="module")
def bundle_data() -> dict:
    return json.loads(PROVIDER_BUNDLE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pin_manifest() -> dict:
    return json.loads(PIN_MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def domain_contract_data() -> dict:
    return json.loads(DOMAIN_CONTRACT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def semantic_profile_data() -> dict:
    return json.loads(SEMANTIC_PROFILE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def preservation_data() -> dict:
    return json.loads(PRESERVATION_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def acceptance_artifact() -> dict:
    return json.loads(ACCEPTANCE_ARTIFACT_PATH.read_text(encoding="utf-8"))


# --- §7 Exact provider pin proofs ---


def test_provider_bundle_exists_and_matches_exact_aggregate(bundle_data: dict, pin_manifest: dict) -> None:
    assert bundle_data["aggregate_sha256"] == EXPECTED_PROVIDER_AGGREGATE
    assert pin_manifest["provider_aggregate_sha256"] == EXPECTED_PROVIDER_AGGREGATE
    assert pin_manifest["provider_commit"] == EXPECTED_PROVIDER_COMMIT

    file_bytes = PROVIDER_BUNDLE_PATH.read_bytes()
    vendored_sha = hashlib.sha256(file_bytes).hexdigest()
    assert pin_manifest["vendored_bundle_sha256"] == vendored_sha


def test_provider_aggregate_recomputes_exactly(bundle_data: dict) -> None:
    """Proves the embedded aggregate matches recomputing sha256(canonical_json(bundle_without_aggregate))."""
    payload_without_aggregate = {k: v for k, v in bundle_data.items() if k != "aggregate_sha256"}
    recomputed = sha256(canonical_json(payload_without_aggregate))
    assert recomputed == EXPECTED_PROVIDER_AGGREGATE


def test_installed_vnext_contracts_importable() -> None:
    import dungeonmind.contracts.vnext as vnext
    from pydantic import BaseModel

    assert hasattr(vnext, "PUBLIC_CONTRACT_MODELS")
    assert len(vnext.PUBLIC_CONTRACT_MODELS) == 17
    # Verify core models are present in export
    assert issubclass(vnext.ProjectionRequest, BaseModel)
    assert issubclass(vnext.Assertion, BaseModel)


# --- §5 & §6 DomainContract and SemanticProfile fixtures ---


def test_domain_contract_descriptor_validates_and_matches_ref(domain_contract_data: dict, preservation_data: dict) -> None:
    desc = DomainContractDescriptor.model_validate(domain_contract_data)
    assert desc.domain_id == "dungeonbuddy.world"
    assert desc.scope_axes == ["dungeonbuddy.scope:campaign"]
    # Ensure session is NOT declared as scope axis
    assert "dungeonbuddy.scope:session" not in desc.scope_axes

    canonical_digest = sha256(canonical_json(desc.model_dump(mode="json")))
    ref_data = preservation_data["domain_contract_ref"]
    ref = DomainContractRef.model_validate(ref_data)
    assert ref.descriptor_sha256 == canonical_digest
    assert ref.domain_id == desc.domain_id
    assert ref.domain_revision == desc.domain_revision


def test_semantic_profile_descriptor_validates_and_matches_ref(semantic_profile_data: dict, preservation_data: dict) -> None:
    prof = SemanticProfileDescriptorV2.model_validate(semantic_profile_data)
    assert prof.profile_id == "dungeonbuddy.dnd5e"
    assert "dnd5e" in prof.term_namespaces
    assert "dungeonbuddy" in prof.term_namespaces
    assert len(prof.classification_terms) >= 2
    assert len(prof.predicates) >= 4

    canonical_digest = sha256(canonical_json(prof.model_dump(mode="json")))
    ref_data = preservation_data["semantic_profile_ref"]
    ref = SemanticProfileRef.model_validate(ref_data)
    assert ref.descriptor_sha256 == canonical_digest
    assert ref.profile_id == prof.profile_id
    assert ref.profile_revision == prof.profile_revision


# --- §4 & §8 Current Buddy request and context preservation ---


def map_buddy_to_projection_request(buddy_input: dict[str, Any]) -> ProjectionRequest:
    """Pure V0.2 test/helper mapping Buddy input parameters into generic ProjectionRequest.

    Rules:
    - world_id -> space_id (required, non-blank string)
    - scope_mode:
        * 'campaign' -> binds 'dungeonbuddy.scope:campaign' = campaign_id (required)
        * 'world' -> wildcard_axes=['dungeonbuddy.scope:campaign'], bindings=[]
        * unknown -> fails closed (raises ValueError)
    - role:
        * 'gm' -> audience_labels=['dungeonbuddy.visibility:gm', 'dungeonbuddy.visibility:player']
        * 'player' -> audience_labels=['dungeonbuddy.visibility:player']
        * unknown -> fails closed (raises ValueError)
    - focus:
        * if session_id is provided -> FocusRef(kind='dungeonbuddy.focus:session', id=session_id)
          plus FocusRef(kind='dungeonbuddy.focus:campaign', id=campaign_id) if campaign_id is provided
    - standing:
        * 'gm' defaults to [established, provisional]
        * 'player' defaults to [established]
        * if standing_selector provided, player requesting non-established fails closed
    """
    if not isinstance(buddy_input, dict):
        raise ValueError(f"buddy_input must be a dict, got {type(buddy_input)}")

    world_id = buddy_input.get("world_id")
    if not isinstance(world_id, str) or not world_id.strip():
        raise ValueError(f"world_id is required and must be non-blank, got {world_id!r}")
    space_id = world_id.strip()

    scope_mode = buddy_input.get("scope_mode")
    if scope_mode == "campaign":
        campaign_id = buddy_input.get("campaign_id")
        if not isinstance(campaign_id, str) or not campaign_id.strip():
            raise ValueError(f"campaign_id is required when scope_mode is 'campaign', got {campaign_id!r}")
        scope_selector = ScopeSelector(
            include_unscoped=True,
            bindings=[ScopeBinding(axis="dungeonbuddy.scope:campaign", value=campaign_id.strip())],
            wildcard_axes=[],
        )
    elif scope_mode == "world":
        scope_selector = ScopeSelector(
            include_unscoped=True,
            bindings=[],
            wildcard_axes=["dungeonbuddy.scope:campaign"],
        )
    else:
        raise ValueError(f"Unknown scope_mode: {scope_mode!r}. Must be 'campaign' or 'world'.")

    role = buddy_input.get("role")
    if not isinstance(role, str):
        raise ValueError(f"role is required and must be a string, got {role!r}")
    normalized_role = role.strip().lower()
    if normalized_role == "gm":
        audience_labels = [
            "dungeonbuddy.visibility:gm",
            "dungeonbuddy.visibility:player",
        ]
        default_standing = [KnowledgeStanding.ESTABLISHED, KnowledgeStanding.PROVISIONAL]
    elif normalized_role == "player":
        audience_labels = [
            "dungeonbuddy.visibility:player",
        ]
        default_standing = [KnowledgeStanding.ESTABLISHED]
    else:
        raise ValueError(f"Unknown role: {role!r}. Must be 'gm' or 'player'.")

    standing_selector: list[KnowledgeStanding]
    if "standing_selector" in buddy_input:
        raw_standings = buddy_input["standing_selector"]
        if not isinstance(raw_standings, list) or not raw_standings:
            raise ValueError("standing_selector must be a non-empty list of standing strings")
        parsed_standings = [KnowledgeStanding(s) for s in raw_standings]
        if normalized_role == "player" and any(st != KnowledgeStanding.ESTABLISHED for st in parsed_standings):
            raise ValueError("Player role cannot request non-established standing")
        standing_selector = parsed_standings
    else:
        standing_selector = default_standing

    focus: list[FocusRef] = []
    if buddy_input.get("session_id"):
        # Presentation focus: session-focused requests carry optional campaign and session focus refs
        if buddy_input.get("campaign_id"):
            focus.append(FocusRef(kind="dungeonbuddy.focus:campaign", id=str(buddy_input["campaign_id"]).strip()))
        focus.append(FocusRef(kind="dungeonbuddy.focus:session", id=str(buddy_input["session_id"]).strip()))

    return ProjectionRequest(
        space_id=space_id,
        scope_selector=scope_selector,
        audience_labels=audience_labels,
        standing_selector=standing_selector,
        focus=focus,
        domain_context=[],
    )


def test_buddy_input_executable_mapping_proof(preservation_data: dict) -> None:
    """Proves executable mapping from Buddy input parameters to vNext ProjectionRequest.

    Ensures that ProjectionRequests in the preservation fixture are not merely
    pre-authored static data, but are derived deterministically by the mapping helper.
    """
    for case in preservation_data["request_context_cases"]:
        mapped = map_buddy_to_projection_request(case["buddy_input"])
        expected = ProjectionRequest.model_validate(case["projection_request"])
        assert mapped == expected
        assert mapped.model_dump(mode="json", exclude_none=True) == case["projection_request"]


def test_unknown_scope_mode_fails_closed() -> None:
    """Proves that unknown scope modes fail closed with ValueError."""
    with pytest.raises(ValueError, match="Unknown scope_mode: 'galaxy'"):
        map_buddy_to_projection_request(
            {
                "world_id": "eldyrwild",
                "scope_mode": "galaxy",
                "role": "gm",
            }
        )


def test_campaign_scope_missing_campaign_id_fails_closed() -> None:
    """Proves that campaign scope mode without campaign_id fails closed with ValueError."""
    with pytest.raises(ValueError, match="campaign_id is required"):
        map_buddy_to_projection_request(
            {
                "world_id": "eldyrwild",
                "scope_mode": "campaign",
                "role": "gm",
            }
        )


def test_unknown_role_fails_closed() -> None:
    """Proves that unknown user roles fail closed with ValueError."""
    with pytest.raises(ValueError, match="Unknown role: 'spectator'"):
        map_buddy_to_projection_request(
            {
                "world_id": "eldyrwild",
                "scope_mode": "world",
                "role": "spectator",
            }
        )


def test_player_requesting_non_established_standing_fails_closed() -> None:
    """Proves that player role requesting provisional or retracted standing fails closed."""
    with pytest.raises(ValueError, match="Player role cannot request non-established standing"):
        map_buddy_to_projection_request(
            {
                "world_id": "eldyrwild",
                "scope_mode": "campaign",
                "campaign_id": "c1",
                "role": "player",
                "standing_selector": ["provisional"],
            }
        )


def test_missing_or_blank_world_id_fails_closed() -> None:
    """Proves that empty or whitespace-only world_id fails closed."""
    with pytest.raises(ValueError, match="world_id is required"):
        map_buddy_to_projection_request(
            {
                "world_id": "   ",
                "scope_mode": "world",
                "role": "gm",
            }
        )


def test_request_context_cases_validate_projection_contract(preservation_data: dict) -> None:
    cases = {c["case_id"]: c for c in preservation_data["request_context_cases"]}

    # Case 1: Campaign + GM
    c_gm = cases["campaign_gm"]["projection_request"]
    req_c_gm = ProjectionRequest.model_validate(c_gm)
    assert req_c_gm.space_id == preservation_data["world_id"]
    assert req_c_gm.scope_selector.include_unscoped is True
    assert len(req_c_gm.scope_selector.bindings) == 1
    assert req_c_gm.scope_selector.bindings[0].axis == "dungeonbuddy.scope:campaign"
    assert req_c_gm.scope_selector.bindings[0].value == "campaign-longmont"
    assert set(req_c_gm.audience_labels) == {"dungeonbuddy.visibility:player", "dungeonbuddy.visibility:gm"}

    # Case 2: Campaign + PLAYER
    c_p = cases["campaign_player"]["projection_request"]
    req_c_p = ProjectionRequest.model_validate(c_p)
    assert req_c_p.audience_labels == ["dungeonbuddy.visibility:player"]
    assert "dungeonbuddy.visibility:gm" not in req_c_p.audience_labels

    # Case 3: World/cross-campaign + GM
    w_gm = cases["world_gm"]["projection_request"]
    req_w_gm = ProjectionRequest.model_validate(w_gm)
    assert req_w_gm.scope_selector.include_unscoped is True
    assert req_w_gm.scope_selector.bindings == []
    assert req_w_gm.scope_selector.wildcard_axes == ["dungeonbuddy.scope:campaign"]

    # Case 4: Session-focused campaign request
    s_c = cases["session_focused_campaign_request"]["projection_request"]
    req_s_c = ProjectionRequest.model_validate(s_c)
    assert len(req_s_c.focus) == 2
    focus_kinds = {f.kind: f.id for f in req_s_c.focus}
    assert focus_kinds["dungeonbuddy.focus:session"] == "session-28"
    assert focus_kinds["dungeonbuddy.focus:campaign"] == "campaign-longmont"
    # Crucial: session is NOT in scope selector
    assert "dungeonbuddy.scope:session" not in [b.axis for b in req_s_c.scope_selector.bindings]
    assert "dungeonbuddy.scope:session" not in req_s_c.scope_selector.wildcard_axes

    # Case 5: Session-focused world request
    s_w = cases["session_focused_world_request"]["projection_request"]
    req_s_w = ProjectionRequest.model_validate(s_w)
    assert req_s_w.scope_selector.wildcard_axes == ["dungeonbuddy.scope:campaign"]
    assert len(req_s_w.focus) == 2


def test_invalid_scope_combinations_fail_validation() -> None:
    """Proves invalid scope combinations fail closed under generic contract."""
    with pytest.raises(ValidationError):
        # Bound and wildcarded on same axis must fail
        ProjectionRequest.model_validate(
            {
                "space_id": "eldyrwild",
                "scope_selector": {
                    "bindings": [{"axis": "dungeonbuddy.scope:campaign", "value": "c1"}],
                    "wildcard_axes": ["dungeonbuddy.scope:campaign"],
                },
            }
        )


# --- §4 & §8 Knowledge models preservation ---


def test_knowledge_assertions_validate_through_vnext(preservation_data: dict) -> None:
    assertions = [Assertion.model_validate(a) for a in preservation_data["assertions"]]
    assert len(assertions) == 6

    # 1. Unscoped/world-global assertion
    as_loc = next(a for a in assertions if a.assertion_id == "as:mireward-classification")
    assert as_loc.metadata.scope == []
    assert as_loc.metadata.visibility.kind == "public"
    assert as_loc.value.kind == "term_ref"
    assert as_loc.value.term == "dnd5e:location"

    # 2. Campaign-scoped assertion with fictional time
    as_npc = next(a for a in assertions if a.assertion_id == "as:brennan-classification")
    assert len(as_npc.metadata.scope) == 1
    assert as_npc.metadata.scope[0].axis == "dungeonbuddy.scope:campaign"
    assert as_npc.metadata.temporal_scope.kind == "domain_ref"
    assert as_npc.metadata.temporal_scope.schema_term == "dungeonbuddy.time:fictional_anchor_v1"
    assert as_npc.metadata.temporal_scope.payload["session_number"] == 28

    # 3. GM-only provisional assertion
    as_plan = next(a for a in assertions if a.assertion_id == "as:brennan-secret-plan")
    assert as_plan.metadata.visibility.kind == "labels_any"
    assert as_plan.metadata.visibility.labels == ["dungeonbuddy.visibility:gm"]
    assert as_plan.metadata.standing == KnowledgeStanding.PROVISIONAL

    # 4. Retracted rumor
    as_rumor = next(a for a in assertions if a.assertion_id == "as:brennan-retracted-rumor")
    assert as_rumor.metadata.standing == KnowledgeStanding.RETRACTED

    # 5. Relationship assertion (EntityRef)
    as_rel = next(a for a in assertions if a.assertion_id == "as:brennan-located-in-mireward")
    assert as_rel.value.kind == "entity_ref"
    assert as_rel.value.entity_id == "entity:loc:mireward"


def test_entities_and_aliases_validate(preservation_data: dict) -> None:
    entities = [Entity.model_validate(e) for e in preservation_data["entities"]]
    assert len(entities) == 2
    entity_ids = {e.entity_id for e in entities}
    assert "entity:npc:brennan-tallow" in entity_ids
    assert "entity:loc:mireward" in entity_ids

    aliases = [IdentityAlias.model_validate(a) for a in preservation_data["aliases"]]
    assert len(aliases) == 1
    alias = aliases[0]
    assert alias.alias_text == "Old Tallow"
    assert alias.entity_id == "entity:npc:brennan-tallow"
    assert len(alias.evidence_ref_ids) == 1


def test_sources_and_evidence_validate_without_generic_kernel_domain_fields(preservation_data: dict) -> None:
    sources = [SourceArtifactV3.model_validate(s) for s in preservation_data["sources"]]
    assert len(sources) == 1
    source = sources[0]
    assert source.source_classification == "dungeonbuddy.source:recap"
    # Campaign and session live in Buddy domain metadata, not generic Kernel fields
    assert len(source.domain_metadata) == 1
    meta = source.domain_metadata[0]
    assert meta.schema_term == "dungeonbuddy.source:context_v1"
    assert meta.payload["campaign_id"] == "campaign-longmont"
    assert meta.payload["session_id"] == "session-28"

    revisions = [SourceRevisionV2.model_validate(sr) for sr in preservation_data["source_revisions"]]
    assert len(revisions) == 1

    ev_list = [EvidenceRefV3.model_validate(ev) for ev in preservation_data["evidence"]]
    assert len(ev_list) == 1
    evidence = ev_list[0]
    assert evidence.can_open_source is True
    assert evidence.can_highlight_span is True


# --- §4.8 Source domain mapping 100% coverage ---


def test_source_domain_mapping_covers_exact_known_source_domains(preservation_data: dict) -> None:
    mapping = preservation_data["source_domain_mapping"]
    mapping_keys = set(mapping.keys())
    assert mapping_keys == set(KNOWN_SOURCE_DOMAINS)

    # Every mapped value must be a valid QualifiedTerm (prefix:name)
    for src_domain, qual_term in mapping.items():
        assert qual_term == f"dungeonbuddy.source:{src_domain}"


# --- §4.6 Governance candidate representation ---


def test_candidate_representation_through_contribution_and_disposition(preservation_data: dict) -> None:
    contrib = KnowledgeContribution.model_validate(preservation_data["candidate_contribution"])
    assert contrib.status == "provisional"
    assert len(contrib.items) == 1
    assert contrib.items[0].kind == "propose_assertion"
    assert contrib.items[0].item_id == "item:prop-brennan-ally"

    disp = ContributionDisposition.model_validate(preservation_data["candidate_disposition"])
    assert disp.item_id == "item:prop-brennan-ally"
    assert disp.disposition == "unresolved"
    assert disp.reason_code == "pending_gm_review"


# --- §9 Acceptance artifact integrity ---


def test_acceptance_artifact_integrity(
    acceptance_artifact: dict,
    preservation_data: dict,
    domain_contract_data: dict,
    semantic_profile_data: dict,
    pin_manifest: dict,
) -> None:
    """Fully seals the acceptance artifact against its canonical ground truths."""
    assert acceptance_artifact["schema"] == "dmb_v0_2_contract_acceptance_v1"
    assert acceptance_artifact["verification_disposition"] == "V0_2_DUNGEONBUDDY_DOMAIN_PROOF_ACCEPTED"
    assert acceptance_artifact["buddy_base_sha"] == EXPECTED_BUDDY_BASE
    assert acceptance_artifact["reviewed_implementation_head_sha"] == EXPECTED_REVIEWED_HEAD
    assert acceptance_artifact["dungeonmind_provider_merge_sha"] == EXPECTED_PROVIDER_COMMIT
    assert acceptance_artifact["dungeonmind_accepted_v0_1_head_sha"] == EXPECTED_ACCEPTED_V0_1_HEAD
    assert acceptance_artifact["dungeonmind_vnext_aggregate_sha256"] == EXPECTED_PROVIDER_AGGREGATE

    # Provider and pin manifest paths and digests
    assert acceptance_artifact["vendored_provider_bundle_path"] == "Docs/Contracts/dungeonmind/dm_vnext_contract_v1.json"
    assert acceptance_artifact["vendored_provider_bundle_sha256"] == pin_manifest["vendored_bundle_sha256"]
    assert acceptance_artifact["buddy_pin_manifest_path"] == "Docs/Contracts/dungeonmind/dm_vnext_contract_pin_v1.json"

    # DomainContract descriptor sealing
    domain_desc = acceptance_artifact["domain_contract_descriptor"]
    assert domain_desc["path"] == "Docs/Contracts/vnext/dungeonbuddy_world_domain_contract_v1.json"
    assert domain_desc["domain_id"] == "dungeonbuddy.world"
    assert domain_desc["domain_revision"] == "1"
    actual_domain_sha = sha256(canonical_json(domain_contract_data))
    assert domain_desc["canonical_sha256"] == actual_domain_sha

    # SemanticProfile descriptor sealing
    profile_desc = acceptance_artifact["semantic_profile_descriptor"]
    assert profile_desc["path"] == "Docs/Contracts/vnext/dungeonbuddy_dnd5e_semantic_profile_v2.json"
    assert profile_desc["profile_id"] == "dungeonbuddy.dnd5e"
    assert profile_desc["profile_revision"] == "1"
    actual_profile_sha = sha256(canonical_json(semantic_profile_data))
    assert profile_desc["canonical_sha256"] == actual_profile_sha

    # Preservation fixture sealing
    actual_preservation_sha = sha256(canonical_json(preservation_data))
    assert acceptance_artifact["preservation_fixture"]["path"] == "tests/fixtures/vnext/dungeonbuddy_domain_preservation_v1.json"
    assert acceptance_artifact["preservation_fixture"]["canonical_sha256"] == actual_preservation_sha

    # Source-domain mapping sealing
    source_map = acceptance_artifact["source_domain_mapping"]
    assert source_map["matches_known_source_domains"] is True
    assert source_map["covered_count"] == len(KNOWN_SOURCE_DOMAINS)
    assert source_map["domains"] == sorted(KNOWN_SOURCE_DOMAINS)
