"""Shadow-verify Buddy Threat hydration through DungeonMind — proof matrix."""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind_dnd.contracts.mechanics_resources import (
    STATBLOCKS_MEDIA_TYPE,
    STATBLOCKS_PROVIDER_ID,
    STATBLOCKS_RESOURCE_SCHEMA,
    DndMechanicsResourceEnvelope,
    DndMechanicsResourceRef,
)
from dungeonmind_dnd.domain.errors import DndWorldObjectMechanicsHydrationError
from fastapi.testclient import TestClient
from graph_memory.projection.world_projection import WorldGraphProjectionNodeView
from graph_memory.union_supergraph.statblock_binding import (
    CONTRACT,
    CONTRACT_VERSION,
    PROVIDER,
    ThreatStatblockBindingV1,
    compute_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
)

import graph_memory.kernel as kernel
from apps.live_control_server.integrations.dungeonmind_kernel.config import (
    dungeonmind_threat_shadow_enabled,
)
from apps.live_control_server.integrations.dungeonmind_kernel.threat_hydration_shadow import (
    AuthorityExactRevisionReplayResolver,
    run_dungeonmind_threat_hydration_shadow,
)
from apps.live_control_server.integrations.dungeonmind_kernel.world_object_conformance_bridge import (
    _load_exact_buddy_revision_bridge_source,
    convert_buddy_definition_digest,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    verify_exact_revision_mechanics_integrity,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    ExactRevisionResourceV1,
)
from apps.live_control_server.main import create_app
from apps.live_control_server.models.threat_query_hydration import (
    ThreatBindingHydrationV1,
    ThreatQueryHydrationHitV1,
    ThreatQueryHydrationRequestV1,
    ThreatQueryHydrationResponseV1,
)
from apps.live_control_server.services.threat_query_hydration import (
    query_threats_with_hydration,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)

WORLD_ID = "shadow-test-world"
CAMPAIGN_ID = "longmont-c2"
THREAT_ID = "threat:shadow-synthetic"
STATBLOCK_ID = "sb_000001"
STATBLOCK_REV = "rev_000002"

_EXACT_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures/statblocks/v1/exact-revision-response.json"
)
_EXACT_FIXTURE_PAYLOAD = json.loads(_EXACT_FIXTURE_PATH.read_text(encoding="utf-8"))
_FIXTURE_DIGEST = _EXACT_FIXTURE_PAYLOAD["definition_digest"]
_FIXTURE_BARE = _FIXTURE_DIGEST.removeprefix("sha256:")

_CONTRIBUTION_SEQ = 0


@pytest.fixture
def seeded_root(tmp_path: Path) -> Path:
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:shadow-baseline"],
    )
    return tmp_path


def _exact_revision() -> ExactRevisionResourceV1:
    return ExactRevisionResourceV1.model_validate(copy.deepcopy(_EXACT_FIXTURE_PAYLOAD))


def _binding(
    *,
    threat_node_id: str = THREAT_ID,
    statblock_id: str = STATBLOCK_ID,
    revision_id: str = STATBLOCK_REV,
    digest: str = _FIXTURE_DIGEST,
    role: str = "primary",
    phase_key: str | None = None,
    variant_label: str | None = None,
) -> dict[str, str | None]:
    return {
        "schema": "dmb_threat_statblock_binding_v1",
        "binding_id": compute_binding_id(
            threat_node_id=threat_node_id,
            provider=PROVIDER,
            statblock_id=statblock_id,
            revision_id=revision_id,
            contract=CONTRACT,
            contract_version=CONTRACT_VERSION,
            definition_digest=digest,
            role=role,
            phase_key=phase_key,
            variant_label=variant_label,
        ),
        "provider": PROVIDER,
        "statblock_id": statblock_id,
        "revision_id": revision_id,
        "contract": CONTRACT,
        "contract_version": CONTRACT_VERSION,
        "definition_digest": digest,
        "role": role,
        "phase_key": phase_key,
        "variant_label": variant_label,
    }


def _resource_value(*, resource_id: str = STATBLOCK_ID) -> dict[str, object]:
    return {
        "kind": "external_resource",
        "role": "statblock",
        "external_resource": {
            "schema": "dmb_external_resource_v1",
            "provider": PROVIDER,
            "resource_type": "statblock",
            "resource_id": resource_id,
            "contract": CONTRACT,
            "contract_version": CONTRACT_VERSION,
        },
    }


def _binding_value(binding: dict[str, str | None]) -> dict[str, object]:
    return {
        "edge_id": edge_id_from_binding_id(str(binding["binding_id"])),
        "direction": "outbound",
        "threat_statblock_binding": binding,
    }


def _contribution(*assertions: Any, campaign_scope: str = CAMPAIGN_ID):
    global _CONTRIBUTION_SEQ
    _CONTRIBUTION_SEQ += 1
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:shadow",
        source_revision_id=f"shadow-{_CONTRIBUTION_SEQ}-{len(assertions)}",
        campaign_scope=campaign_scope,
        accepted_assertions=list(assertions),
    )


def _publish_threat_node(
    root: Path,
    *,
    threat_node_id: str = THREAT_ID,
    kind: str = "threat",
    role: str = "threat",
    label: str = "Shadow Threat",
) -> str:
    threat = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=threat_node_id,
        label=label,
        campaign_scope=CAMPAIGN_ID,
        value={
            "kind": kind,
            "role": role,
            "source_domains": ["manual_seed"],
        },
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(threat)
    )
    assert result.published and result.revision_id
    return result.revision_id


def _publish_bindings(
    root: Path,
    bindings: list[dict[str, str | None]],
    *,
    threat_node_id: str = THREAT_ID,
    campaign_scope: str = CAMPAIGN_ID,
) -> str:
    assertions = []
    seen_resources: set[str] = set()
    for binding in bindings:
        resource_id = str(binding["statblock_id"])
        if resource_id not in seen_resources:
            assertions.append(
                kernel.build_assertion(
                    assertion_kind="node",
                    acceptance_state="accepted",
                    subject_node_id=external_statblock_node_id(resource_id),
                    label=f"External {resource_id}",
                    campaign_scope=campaign_scope,
                    value=_resource_value(resource_id=resource_id),
                )
            )
            seen_resources.add(resource_id)
        assertions.append(
            kernel.build_assertion(
                assertion_kind="edge",
                acceptance_state="accepted",
                subject_node_id=threat_node_id,
                target_node_id=external_statblock_node_id(resource_id),
                predicate="uses_statblock",
                campaign_scope=campaign_scope,
                value=_binding_value(binding),
            )
        )
    result = kernel.merge_contribution_to_revision(
        root,
        world_id=WORLD_ID,
        contribution=_contribution(*assertions, campaign_scope=campaign_scope),
    )
    assert result.published and result.revision_id
    return result.revision_id


def _threat_view(
    *,
    node_id: str = THREAT_ID,
    kind: str = "threat",
    role: str = "threat",
    label: str = "Shadow Threat",
) -> WorldGraphProjectionNodeView:
    return WorldGraphProjectionNodeView(
        node_id=node_id,
        label=label,
        kind=kind,
        role=role,
        aliases=[],
        summary=f"summary for {label}",
    )


def _auth_binding(
    binding_dict: dict[str, str | None],
    *,
    hydration_status: str = "available",
    revision: ExactRevisionResourceV1 | None = None,
    threat_node_id: str = THREAT_ID,
) -> ThreatBindingHydrationV1:
    model = ThreatStatblockBindingV1.model_validate(binding_dict)
    return ThreatBindingHydrationV1(
        relationship_edge_id=edge_id_from_binding_id(model.binding_id),
        binding_id=model.binding_id,
        binding_role=model.role,
        threat_node_id=threat_node_id,
        resource_node_id=external_statblock_node_id(model.statblock_id),
        provider="dungeonmind",
        statblock_id=model.statblock_id,
        revision_id=model.revision_id,
        definition_digest=model.definition_digest,
        hydration_status=hydration_status,  # type: ignore[arg-type]
        binding=model,
        revision=revision if hydration_status == "available" else None,
        message=None if hydration_status == "available" else hydration_status,
    )


def _request(*, include_mechanics: bool = True) -> ThreatQueryHydrationRequestV1:
    return ThreatQueryHydrationRequestV1.model_validate(
        {
            "schema": "dmb_threat_query_hydration_request_v1",
            "world_id": WORLD_ID,
            "campaign_id": CAMPAIGN_ID,
            "scope_mode": "campaign",
            "revision_pin": "rev:unused-pin",
            "query_text": "Shadow Threat",
            "include_mechanics": include_mechanics,
        }
    )


def _response(
    *,
    revision_id: str,
    hits: list[ThreatQueryHydrationHitV1],
) -> ThreatQueryHydrationResponseV1:
    return ThreatQueryHydrationResponseV1(
        schema="dmb_threat_query_hydration_response_v1",
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        scope_mode="campaign",
        revision_id=revision_id,
        query_text="Shadow Threat",
        result_label="threat_query_hydration_ok",
        hits=hits,
        diagnostics=[],
    )


def _hit(
    *,
    bindings: list[ThreatBindingHydrationV1],
    threat: WorldGraphProjectionNodeView | None = None,
    disposition: str | None = None,
) -> ThreatQueryHydrationHitV1:
    node = threat or _threat_view()
    if disposition is None:
        if not bindings:
            disposition = "no_binding"
        elif all(b.hydration_status == "available" for b in bindings):
            disposition = "hydrated"
        elif all(b.hydration_status == "not_requested" for b in bindings):
            disposition = "not_requested"
        else:
            disposition = "partial"
    return ThreatQueryHydrationHitV1(
        threat=node,
        match_reasons=["exact_label"],
        relationships=[],
        bindings=bindings,
        mechanics_disposition=disposition,  # type: ignore[arg-type]
    )


def test_flag_enable_only_exact_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DUNGEONMIND_THREAT_HYDRATION_SHADOW_ENABLED", raising=False)
    assert dungeonmind_threat_shadow_enabled() is False
    for value in ("0", "true", "TRUE", "yes", "on", "", "11", " 1"):
        monkeypatch.setenv("DUNGEONMIND_THREAT_HYDRATION_SHADOW_ENABLED", value)
        assert dungeonmind_threat_shadow_enabled() is False
    monkeypatch.setenv("DUNGEONMIND_THREAT_HYDRATION_SHADOW_ENABLED", "1")
    assert dungeonmind_threat_shadow_enabled() is True


def test_real_fixture_digest_equivalence() -> None:
    revision = _exact_revision()
    verify_exact_revision_mechanics_integrity(revision)
    payload = json.loads(revision.canonical_definition)
    assert isinstance(payload, dict)
    assert canonical_sha256(payload) == revision.definition_digest.removeprefix("sha256:")
    assert canonical_sha256(payload) == convert_buddy_definition_digest(
        revision.definition_digest
    )
    ref = DndMechanicsResourceRef(
        ruleset_id="dnd5e",
        provider_id=STATBLOCKS_PROVIDER_ID,
        resource_id=revision.statblock_id,
        resource_revision=revision.revision_id,
        resource_schema=STATBLOCKS_RESOURCE_SCHEMA,
        media_type=STATBLOCKS_MEDIA_TYPE,
        payload_sha256=convert_buddy_definition_digest(revision.definition_digest),
    )
    envelope = DndMechanicsResourceEnvelope(
        resource_ref=ref,
        mechanics_payload=payload,
    )
    assert envelope.resource_ref.payload_sha256 == _FIXTURE_BARE
    resolver = AuthorityExactRevisionReplayResolver(
        expected_ref=ref,
        revision=revision,
    )
    assert resolver.resolve(ref).mechanics_payload == payload
    assert resolver.call_count == 1


def test_matrix_a_one_threat_one_available_binding(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    binding = _binding()
    revision_id = _publish_bindings(seeded_root, [binding])
    exact = _exact_revision()
    response = _response(
        revision_id=revision_id,
        hits=[_hit(bindings=[_auth_binding(binding, revision=exact)])],
    )
    observations = run_dungeonmind_threat_hydration_shadow(
        request=_request(),
        authoritative_response=response,
        root=seeded_root,
    )
    assert len(observations) == 1
    obs = observations[0]
    assert obs.verdict == "full_match"
    assert obs.bridge_attachment_count == 1
    assert obs.shadow_hydrated_binding_count == 1
    assert obs.bridge_generic_binding_count == 1


def test_matrix_b_zero_bindings(seeded_root: Path) -> None:
    revision_id = _publish_threat_node(seeded_root)
    response = _response(revision_id=revision_id, hits=[_hit(bindings=[])])
    observations = run_dungeonmind_threat_hydration_shadow(
        request=_request(),
        authoritative_response=response,
        root=seeded_root,
    )
    assert observations[0].verdict == "structural_match"
    assert "authority_no_binding" in observations[0].reason_codes
    assert observations[0].bridge_attachment_count == 0


def test_matrix_c_primary_and_alternate_same_resource(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    primary = _binding(role="primary")
    alternate = _binding(role="alternate")
    revision_id = _publish_bindings(seeded_root, [primary, alternate])
    exact = _exact_revision()
    response = _response(
        revision_id=revision_id,
        hits=[
            _hit(
                bindings=[
                    _auth_binding(primary, revision=exact),
                    _auth_binding(alternate, revision=exact),
                ]
            )
        ],
    )
    obs = run_dungeonmind_threat_hydration_shadow(
        request=_request(),
        authoritative_response=response,
        root=seeded_root,
    )[0]
    assert obs.verdict == "full_match"
    assert obs.authority_binding_count == 2
    assert obs.bridge_attachment_count == 2
    assert obs.bridge_generic_binding_count == 1
    assert obs.shadow_hydrated_binding_count == 2


def test_matrix_d_two_phases(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    bloodied = _binding(role="phase", phase_key="bloodied")
    enraged = _binding(role="phase", phase_key="enraged")
    revision_id = _publish_bindings(seeded_root, [bloodied, enraged])
    exact = _exact_revision()
    response = _response(
        revision_id=revision_id,
        hits=[
            _hit(
                bindings=[
                    _auth_binding(bloodied, revision=exact),
                    _auth_binding(enraged, revision=exact),
                ]
            )
        ],
    )
    obs = run_dungeonmind_threat_hydration_shadow(
        request=_request(),
        authoritative_response=response,
        root=seeded_root,
    )[0]
    assert obs.verdict == "full_match"
    phases = {
        br.source_binding_id: next(
            b for b in (bloodied, enraged) if b["binding_id"] == br.source_binding_id
        )["phase_key"]
        for br in obs.binding_results
    }
    assert set(phases.values()) == {"bloodied", "enraged"}


def test_matrix_e_exact_string_grammar(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    spaced = _binding(role="phase", phase_key=" enraged ", variant_label="")
    night = _binding(role="encounter_variant", variant_label=" night raid ")
    revision_id = _publish_bindings(seeded_root, [spaced, night])
    exact = _exact_revision()
    response = _response(
        revision_id=revision_id,
        hits=[
            _hit(
                bindings=[
                    _auth_binding(spaced, revision=exact),
                    _auth_binding(night, revision=exact),
                ]
            )
        ],
    )
    obs = run_dungeonmind_threat_hydration_shadow(
        request=_request(),
        authoritative_response=response,
        root=seeded_root,
    )[0]
    assert obs.verdict == "full_match"
    by_id = {b["binding_id"]: b for b in (spaced, night)}
    for item in obs.binding_results:
        source = by_id[item.source_binding_id]
        assert source["phase_key"] in {None, " enraged "}
        assert source["variant_label"] in {"", " night raid "}


def test_matrix_f_include_mechanics_false(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    binding = _binding()
    revision_id = _publish_bindings(seeded_root, [binding])
    response = _response(
        revision_id=revision_id,
        hits=[
            _hit(
                bindings=[
                    _auth_binding(binding, hydration_status="not_requested"),
                ],
                disposition="not_requested",
            )
        ],
    )
    obs = run_dungeonmind_threat_hydration_shadow(
        request=_request(include_mechanics=False),
        authoritative_response=response,
        root=seeded_root,
    )[0]
    assert obs.verdict == "structural_match"
    assert "authority_mechanics_not_requested" in obs.reason_codes
    assert obs.shadow_hydrated_binding_count == 0


def test_matrix_g_downstream_unavailable(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    binding = _binding()
    revision_id = _publish_bindings(seeded_root, [binding])
    response = _response(
        revision_id=revision_id,
        hits=[
            _hit(
                bindings=[_auth_binding(binding, hydration_status="unavailable")],
                disposition="unavailable",
            )
        ],
    )
    obs = run_dungeonmind_threat_hydration_shadow(
        request=_request(),
        authoritative_response=response,
        root=seeded_root,
    )[0]
    assert obs.verdict == "inconclusive"
    assert "authority_unavailable" in obs.reason_codes
    assert obs.verdict != "full_match"


def test_matrix_h_exact_revision_missing(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    binding = _binding()
    revision_id = _publish_bindings(seeded_root, [binding])
    response = _response(
        revision_id=revision_id,
        hits=[
            _hit(
                bindings=[
                    _auth_binding(binding, hydration_status="exact_revision_missing")
                ],
                disposition="unavailable",
            )
        ],
    )
    obs = run_dungeonmind_threat_hydration_shadow(
        request=_request(),
        authoritative_response=response,
        root=seeded_root,
    )[0]
    assert obs.verdict == "inconclusive"
    assert "authority_exact_revision_missing" in obs.reason_codes


def test_matrix_i_authority_integrity_failure_no_false_match(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    binding = _binding()
    revision_id = _publish_bindings(seeded_root, [binding])
    response = _response(
        revision_id=revision_id,
        hits=[
            _hit(
                bindings=[
                    _auth_binding(binding, hydration_status="integrity_failure")
                ],
                disposition="integrity_failure",
            )
        ],
    )
    obs = run_dungeonmind_threat_hydration_shadow(
        request=_request(),
        authoritative_response=response,
        root=seeded_root,
    )[0]
    assert obs.verdict == "inconclusive"
    assert obs.verdict != "full_match"
    assert "authority_integrity_failure" in obs.reason_codes


def test_matrix_j_available_but_dungeonmind_rejects(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    binding = _binding()
    revision_id = _publish_bindings(seeded_root, [binding])
    exact = _exact_revision()
    response = _response(
        revision_id=revision_id,
        hits=[_hit(bindings=[_auth_binding(binding, revision=exact)])],
    )
    with patch(
        "apps.live_control_server.integrations.dungeonmind_kernel.threat_hydration_shadow.hydrate_world_object_mechanics",
        side_effect=DndWorldObjectMechanicsHydrationError(
            details={"reason": "resource_payload_digest_mismatch"}
        ),
    ):
        obs = run_dungeonmind_threat_hydration_shadow(
            request=_request(),
            authoritative_response=response,
            root=seeded_root,
        )[0]
    assert obs.verdict == "mismatch"
    assert "dungeonmind_hydration_failure" in obs.reason_codes
    assert obs.dungeonmind_hydration_reason == "resource_payload_digest_mismatch"


def test_matrix_k_non_explicit_compatibility_hit(seeded_root: Path) -> None:
    revision_id = _publish_threat_node(
        seeded_root, threat_node_id="npc:compat", kind="npc", role="antagonist"
    )
    response = _response(
        revision_id=revision_id,
        hits=[
            _hit(
                bindings=[],
                threat=_threat_view(
                    node_id="npc:compat", kind="npc", role="antagonist", label="Compat"
                ),
                disposition="no_binding",
            )
        ],
    )
    obs = run_dungeonmind_threat_hydration_shadow(
        request=_request(),
        authoritative_response=response,
        root=seeded_root,
    )[0]
    assert obs.verdict == "not_eligible"
    assert "source_object_kind_not_shadow_eligible" in obs.reason_codes


def test_matrix_l_pinned_r1_ignores_newer_head(seeded_root: Path) -> None:
    _publish_threat_node(seeded_root)
    binding_a = _binding(role="primary", variant_label="rev-a")
    revision_a = _publish_bindings(seeded_root, [binding_a])
    binding_b = _binding(role="alternate", variant_label="rev-b")
    edge_only = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=THREAT_ID,
        target_node_id=external_statblock_node_id(STATBLOCK_ID),
        predicate="uses_statblock",
        campaign_scope=CAMPAIGN_ID,
        value=_binding_value(binding_b),
    )
    result_b = kernel.merge_contribution_to_revision(
        seeded_root, world_id=WORLD_ID, contribution=_contribution(edge_only)
    )
    assert result_b.published and result_b.revision_id
    exact = _exact_revision()
    response = _response(
        revision_id=revision_a,
        hits=[_hit(bindings=[_auth_binding(binding_a, revision=exact)])],
    )
    obs = run_dungeonmind_threat_hydration_shadow(
        request=_request(),
        authoritative_response=response,
        root=seeded_root,
    )[0]
    assert obs.verdict == "full_match"
    assert obs.revision_id == revision_a
    assert obs.bridge_attachment_count == 1
    assert obs.binding_results[0].source_binding_id == binding_a["binding_id"]


def test_matrix_m_several_threats_one_graph_load(seeded_root: Path) -> None:
    t1 = "threat:shadow-a"
    t2 = "threat:shadow-b"
    _publish_threat_node(seeded_root, threat_node_id=t1, label="A")
    _publish_threat_node(seeded_root, threat_node_id=t2, label="B")
    b1 = _binding(threat_node_id=t1)
    b2 = _binding(threat_node_id=t2)
    # Publish both resource+edges. Second publish can reuse resource.
    _publish_bindings(seeded_root, [b1], threat_node_id=t1)
    revision_id = _publish_bindings(seeded_root, [b2], threat_node_id=t2)
    exact = _exact_revision()
    response = _response(
        revision_id=revision_id,
        hits=[
            _hit(
                bindings=[_auth_binding(b1, revision=exact, threat_node_id=t1)],
                threat=_threat_view(node_id=t1, label="A"),
            ),
            _hit(
                bindings=[_auth_binding(b2, revision=exact, threat_node_id=t2)],
                threat=_threat_view(node_id=t2, label="B"),
            ),
        ],
    )
    with patch(
        "apps.live_control_server.integrations.dungeonmind_kernel.threat_hydration_shadow._load_exact_buddy_revision_bridge_source",
        wraps=_load_exact_buddy_revision_bridge_source,
    ) as load_spy:
        observations = run_dungeonmind_threat_hydration_shadow(
            request=_request(),
            authoritative_response=response,
            root=seeded_root,
        )
    assert load_spy.call_count == 1
    assert len(observations) == 2
    assert {o.threat_node_id for o in observations} == {t1, t2}
    assert all(o.verdict == "full_match" for o in observations)


def test_matrix_n_shadow_runner_crash_contained(
    seeded_root: Path, caplog: pytest.LogCaptureFixture
) -> None:
    revision_id = _publish_threat_node(seeded_root)
    response = _response(revision_id=revision_id, hits=[_hit(bindings=[])])
    with (
        patch(
            "apps.live_control_server.integrations.dungeonmind_kernel.threat_hydration_shadow.shadow_threat_hit",
            side_effect=RuntimeError("boom-secret-payload"),
        ),
        caplog.at_level(logging.WARNING),
    ):
        observations = run_dungeonmind_threat_hydration_shadow(
            request=_request(),
            authoritative_response=response,
            root=seeded_root,
        )
    assert len(observations) == 1
    assert observations[0].verdict == "shadow_error"
    assert "unexpected_shadow_exception" in observations[0].reason_codes
    joined = "\n".join(record.getMessage() for record in caplog.records)
    assert "unexpected_shadow_exception" in joined
    assert "boom-secret-payload" not in joined
    assert "RuntimeError" not in joined
    assert "Traceback" not in joined


def test_world_scope_campaign_lens_does_not_false_mismatch(
    seeded_root: Path,
) -> None:
    """Projection campaign lens != store.campaign_id must not false-mismatch."""
    _publish_threat_node(seeded_root)
    binding = _binding()
    revision_id = _publish_bindings(seeded_root, [binding])
    exact = _exact_revision()
    source = _load_exact_buddy_revision_bridge_source(
        root=seeded_root, world_id=WORLD_ID, revision_id=revision_id
    )
    assert source.store.campaign_id == CAMPAIGN_ID
    assert CAMPAIGN_ID != "campaign_lens"

    response = ThreatQueryHydrationResponseV1(
        schema="dmb_threat_query_hydration_response_v1",
        world_id=WORLD_ID,
        campaign_id="campaign_lens",
        scope_mode="world",
        revision_id=revision_id,
        query_text="Shadow Threat",
        result_label="threat_query_hydration_ok",
        hits=[_hit(bindings=[_auth_binding(binding, revision=exact)])],
        diagnostics=[],
    )
    request = ThreatQueryHydrationRequestV1.model_validate(
        {
            "schema": "dmb_threat_query_hydration_request_v1",
            "world_id": WORLD_ID,
            "campaign_id": "campaign_lens",
            "scope_mode": "world",
            "revision_pin": revision_id,
            "query_text": "Shadow Threat",
            "include_mechanics": True,
        }
    )
    observations = run_dungeonmind_threat_hydration_shadow(
        request=request,
        authoritative_response=response,
        root=seeded_root,
    )
    assert len(observations) == 1
    obs = observations[0]
    assert obs.verdict == "full_match"
    assert "bridge_failure" not in obs.reason_codes
    assert obs.campaign_id == "campaign_lens"


def test_admitted_edges_ignore_out_of_scope_raw_store_binding(
    seeded_root: Path,
) -> None:
    """Authority-admitted edge set is the bridge selection boundary."""
    _publish_threat_node(seeded_root)
    admitted = _binding(role="primary", statblock_id="sb_000001")
    foreign = _binding(
        role="alternate",
        statblock_id="sb_000002",
        revision_id="rev_000003",
    )
    _publish_bindings(seeded_root, [admitted], campaign_scope=CAMPAIGN_ID)
    revision_id = _publish_bindings(
        seeded_root, [foreign], campaign_scope="campaign_other"
    )
    exact = _exact_revision()
    # Authority only admitted the in-scope binding (projection filtered the other).
    response = _response(
        revision_id=revision_id,
        hits=[_hit(bindings=[_auth_binding(admitted, revision=exact)])],
    )
    observations = run_dungeonmind_threat_hydration_shadow(
        request=_request(),
        authoritative_response=response,
        root=seeded_root,
    )
    assert len(observations) == 1
    obs = observations[0]
    assert obs.verdict == "full_match"
    assert obs.authority_binding_count == 1
    assert obs.bridge_attachment_count == 1
    assert "binding_cardinality_mismatch" not in obs.reason_codes
    assert {br.source_binding_id for br in obs.binding_results} == {
        admitted["binding_id"]
    }


def test_product_output_invariant_enabled_vs_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    client = TestClient(app)
    fake = ThreatQueryHydrationResponseV1(
        schema="dmb_threat_query_hydration_response_v1",
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        scope_mode="campaign",
        revision_id="rev:pin",
        query_text="Shadow",
        result_label="threat_query_hydration_empty",
        hits=[],
        diagnostics=[],
    )
    body = {
        "schema": "dmb_threat_query_hydration_request_v1",
        "worldId": WORLD_ID,
        "campaignId": CAMPAIGN_ID,
        "revisionPin": "rev:pin",
        "queryText": "Shadow",
    }
    with patch(
        "apps.live_control_server.routes.threat_query_hydration.query_threats_with_hydration",
        return_value=fake,
    ):
        monkeypatch.delenv("DUNGEONMIND_THREAT_HYDRATION_SHADOW_ENABLED", raising=False)
        disabled = client.post("/api/live/threats/query-hydration", json=body)
        monkeypatch.setenv("DUNGEONMIND_THREAT_HYDRATION_SHADOW_ENABLED", "1")
        with patch(
            "apps.live_control_server.routes.threat_query_hydration.run_dungeonmind_threat_hydration_shadow"
        ) as shadow_spy:
            enabled = client.post("/api/live/threats/query-hydration", json=body)
            assert shadow_spy.call_count == 1
    assert disabled.status_code == 200
    assert enabled.status_code == 200
    assert disabled.json() == enabled.json()


def test_route_error_does_not_schedule_shadow(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.live_control_server.services.threat_query_hydration import (
        ThreatQueryHydrationError,
    )

    app = create_app()
    client = TestClient(app)
    monkeypatch.setenv("DUNGEONMIND_THREAT_HYDRATION_SHADOW_ENABLED", "1")
    with (
        patch(
            "apps.live_control_server.routes.threat_query_hydration.query_threats_with_hydration",
            side_effect=ThreatQueryHydrationError(
                "graph down",
                result_label="threat_query_hydration_unavailable",
                status_code=503,
            ),
        ),
        patch(
            "apps.live_control_server.routes.threat_query_hydration.run_dungeonmind_threat_hydration_shadow"
        ) as shadow_spy,
    ):
        response = client.post(
            "/api/live/threats/query-hydration",
            json={
                "schema": "dmb_threat_query_hydration_request_v1",
                "worldId": WORLD_ID,
                "campaignId": CAMPAIGN_ID,
                "revisionPin": "rev:pin",
                "queryText": "Shadow",
            },
        )
    assert response.status_code == 503
    shadow_spy.assert_not_called()


def test_authority_provider_call_count_unchanged_when_shadow_runs(
    seeded_root: Path,
) -> None:
    """Shadow must not invoke DungeonMindStatblockV1Client.get_exact_revision."""
    from graph_memory.projection.world_projection import (
        WorldGraphProjection,
        WorldGraphProjectionFocus,
        WorldGraphProjectionRelationshipView,
        WorldGraphProjectionSnapshot,
        WorldGraphProjectionSummary,
        WorldGraphProjectionTrustBoundary,
        WorldGraphQueryContext,
    )

    _publish_threat_node(seeded_root)
    binding = _binding()
    revision_id = _publish_bindings(seeded_root, [binding])
    model = ThreatStatblockBindingV1.model_validate(binding)
    threat = _threat_view()
    resource = WorldGraphProjectionNodeView(
        node_id=external_statblock_node_id(STATBLOCK_ID),
        label="statblock",
        kind="external_resource",
        role="statblock",
        external_resource={
            "schema": "dmb_external_resource_v1",
            "provider": PROVIDER,
            "resource_type": "statblock",
            "resource_id": STATBLOCK_ID,
            "contract": CONTRACT,
            "contract_version": CONTRACT_VERSION,
        },
    )
    rel = WorldGraphProjectionRelationshipView(
        edge_id=edge_id_from_binding_id(model.binding_id),
        source_node_id=THREAT_ID,
        target_node_id=resource.node_id,
        predicate="uses_statblock",
        label="uses_statblock",
        direction="outgoing",
        threat_statblock_binding=model,
    )
    snapshot = WorldGraphProjectionSnapshot(
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        revision_id=revision_id,
        head_revision_id=revision_id,
        is_head=True,
        focus=WorldGraphProjectionFocus(kind="none"),
        admissibility="gm",
        scope_mode="campaign",
    )
    proj = WorldGraphProjection(
        schema="dmb_world_graph_projection_v1",
        snapshot=snapshot,
        summary=WorldGraphProjectionSummary(
            node_count=2,
            relationship_count=1,
            attribute_count=0,
            evidence_count=0,
            source_artifact_count=0,
        ),
        nodes=[threat, resource],
        relationships=[rel],
        trust_boundary=WorldGraphProjectionTrustBoundary(),
        query_context=WorldGraphQueryContext(
            snapshot=snapshot,
            revision_id=revision_id,
            query_text="Shadow Threat",
            matched_node_ids=[THREAT_ID],
            match_reasons={THREAT_ID: ["exact_label"]},
            nodes=[threat],
            relationships=[rel],
        ),
    )
    exact = _exact_revision()
    client = MagicMock()
    client.get_exact_revision.return_value = exact
    request = _request()
    request = request.model_copy(update={"revision_pin": revision_id})
    authority = query_threats_with_hydration(
        request,
        root=seeded_root,
        project_fn=lambda *_a, **_k: proj,
        client=client,
    )
    authority_calls = client.get_exact_revision.call_count
    assert authority_calls == 1

    with patch(
        "apps.live_control_server.integrations.dungeonmind_statblocks.client.DungeonMindStatblockV1Client"
    ) as client_cls:
        observations = run_dungeonmind_threat_hydration_shadow(
            request=request,
            authoritative_response=authority,
            root=seeded_root,
        )
        client_cls.assert_not_called()

    assert client.get_exact_revision.call_count == authority_calls
    assert observations[0].verdict == "full_match"


def test_public_bridge_still_source_id_only() -> None:
    import inspect

    from apps.live_control_server.integrations import dungeonmind_kernel as pkg

    assert "bridge_buddy_threat_revision" not in pkg.__all__
    params = set(inspect.signature(pkg.bridge_exact_buddy_threat).parameters)
    assert {"root", "world_id", "revision_id", "threat_node_id"}.issubset(params)
    assert "source_store" not in params
    assert "source_revision" not in params
