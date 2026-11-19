"""Current initializer mapping retains reviewed spans without compatibility paths."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind.first_world_typed_evidence import (
    map_first_world_typed_contribution,
)
from tests.test_worldbuilding_typed_extraction_evidence import fixture
from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
    ContributionMappingError,
)


def mapped(contribution, pairs):
    return map_first_world_typed_contribution(
        contribution,
        artifacts=[SimpleNamespace(source_artifact_id="source")],
        pair_to_dm=pairs,
        party_registry=False,
    )


def test_current_extraction_retains_all_spans():
    contribution, _store, pairs = fixture()
    result = mapped(contribution, pairs)
    assert result.schema_version == "dm_graph_contribution_v3"
    assert [ref.source_span_ref_id for ref in result.assertions[0].evidence_refs] == [
        "span:one",
        "span:two",
    ]
    assert all(
        ref.can_open_source and ref.can_highlight_span
        for ref in result.assertions[0].evidence_refs
    )
    assert mapped(contribution, pairs) == result


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_span_ref_id", None),
        ("source_artifact_id", "foreign"),
        ("source_domain", "session_recap"),
        ("source_revision_id", "sha256:" + "f" * 64),
        ("evidence_ref_id", "unclosed"),
    ],
)
def test_invalid_declared_bindings_cannot_be_inferred(field, value):
    contribution, _store, pairs = fixture()
    assertion = contribution.accepted_assertions[0]
    rows = [dict(row) for row in assertion.value["evidence"]]
    rows[0][field] = value
    assertion = assertion.model_copy(
        update={"value": {**assertion.value, "evidence": rows}}
    )
    with pytest.raises((ValueError, ContributionMappingError)):
        mapped(
            contribution.model_copy(update={"accepted_assertions": [assertion]}), pairs
        )


def test_source_commitment_includes_source_index_and_reviewed_quotes():
    from apps.live_control_server.services.first_world_graph_publication import (
        _source_evidence_commitment,
    )
    from graph_memory.source_span import build_source_span_index_for_text

    text = "A small bridge crosses the river."
    import hashlib

    index = build_source_span_index_for_text(
        source_artifact_id="source",
        text=text,
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )
    review = [
        SimpleNamespace(
            assertion_id="bridge",
            kind="object",
            evidence=[
                SimpleNamespace(
                    source_artifact_id="source",
                    source_span_ref_id=index.spans[0].source_span_id,
                    anchor_quotes=[text],
                ),
            ],
        )
    ]
    args = dict(source_prose=text, span_index=index, source_artifact_id="source")
    original = _source_evidence_commitment(review, **args)
    from apps.live_control_server.services.first_world_graph_publication import (
        ExtractPromoteError,
    )

    with pytest.raises(ExtractPromoteError):
        _source_evidence_commitment(
            review, **{**args, "source_prose": text + " Changed."}
        )
    assert original != _source_evidence_commitment(
        review, **{**args, "span_index": replace(index, spans=())}
    )
    other = [
        SimpleNamespace(
            assertion_id="bridge",
            kind="object",
            evidence=[
                SimpleNamespace(
                    source_artifact_id="source",
                    source_span_ref_id=index.spans[0].source_span_id,
                    anchor_quotes=["river"],
                ),
            ],
        )
    ]
    assert original != _source_evidence_commitment(other, **args)


def test_old_plan_models_require_fresh_review():
    from apps.live_control_server.models.extract_promote import FirstWorldGraphPlan
    from apps.live_control_server.models.recap_world_genesis import (
        RecapWorldGenesisPlan,
    )

    for model, schema in (
        (FirstWorldGraphPlan, "dmb_first_world_graph_plan_v2"),
        (RecapWorldGenesisPlan, "dmb_recap_world_genesis_plan_v1"),
    ):
        with pytest.raises(ValueError, match="out of date"):
            model.model_validate({"schema": schema})


def test_old_plan_cannot_reach_source_or_initialization(monkeypatch):
    from apps.live_control_server.services import (
        first_world_graph_publication as service,
    )

    monkeypatch.setattr(
        service.live_config,
        "world_graph_root",
        lambda: pytest.fail("stale plan touched authority"),
    )
    with pytest.raises(service.ExtractPromoteError) as error:
        service.confirm_first_world(
            SimpleNamespace(
                plan=SimpleNamespace(schema_="dmb_first_world_graph_plan_v2")
            )
        )
    assert error.value.code == "stale_review_plan"


def test_materialized_spans_must_match_the_verified_candidate():
    from apps.live_control_server.services.first_world_graph_publication import (
        _assert_materialized_evidence_matches_review,
        ExtractPromoteError,
    )

    contribution, _store, _pairs = fixture()
    assertion = contribution.accepted_assertions[0]
    review = [
        SimpleNamespace(
            assertion_id="candidate",
            evidence=[
                SimpleNamespace(
                    source_artifact_id="source", source_span_ref_id="span:one"
                ),
            ],
        )
    ]
    materialized = SimpleNamespace(
        effect={"candidate_effect_map": {"candidate": [assertion.assertion_id]}},
        contribution=contribution,
    )
    with pytest.raises(ExtractPromoteError):
        _assert_materialized_evidence_matches_review(materialized, review)


def test_registry_profile_cannot_drop_declared_extraction_evidence():
    contribution, _store, pairs = fixture()
    contribution = contribution.model_copy(update={"source_kind": "standing_context"})
    with pytest.raises(ValueError, match="discard"):
        map_first_world_typed_contribution(
            contribution,
            artifacts=[SimpleNamespace(source_artifact_id="source")],
            pair_to_dm=pairs,
            party_registry=True,
        )


# Use the actual first-World materializer, not an invented effect wire.
def _first_world_effect(*, reject=False):
    from apps.live_control_server.models.extract_promote import FirstWorldNativeTarget
    from apps.live_control_server.services.first_world_graph import materialize_first_world_plan
    from graph_memory.candidate_graph_preview import (
        CandidateGraphPreview, CandidateNode, CandidateEdge, EvidenceRef,
        PreviewDiagnostics, SemanticState,
    )
    from graph_memory.worldbuilding_write_plan import WORLDBUILDING_EXTRACTION_PROFILE

    state = SemanticState("worldbuilding_draft", "candidate", "source_evidence",
                          "system_derived", "gm_private")
    evidence = (EvidenceRef("ref:one", "source", source_span_ref_id="span:one"),)
    nodes = tuple(CandidateNode(
        node_id=identifier, label=label, node_type="character", description="Reviewed description",
        importance="high", semantic_state=state, evidence_refs=evidence,
        proposed_action="create", confidence="high", aliases=(label, label.upper(), "  "),
    ) for identifier, label in (("candidate:a", "Alice"), ("candidate:b", "Bob")))
    edge = CandidateEdge("edge:one", "candidate:a", "candidate:b", "knows", "knows",
                         state, evidence, "create", "high")
    preview = CandidateGraphPreview(
        schema="dmb_candidate_graph_preview_v0", version="0.1", preview_id="preview:one",
        campaign_id="world", session_id=None, source_artifact_ids=("source",), status="preview",
        nodes=nodes, edges=(edge,), beats=(), proposed_writes=(), ignored_items=(), deferred_items=(),
        diagnostics=PreviewDiagnostics(True, True, False, False, False, False,
                                       False, False, False, False, 0, 0, 0),
    )
    return materialize_first_world_plan(
        preview=preview, world_id="world", native_target=FirstWorldNativeTarget(
            native_world_id="world:" + "1" * 32, provisioning_id="provision:" + "2" * 32,
            binding_version=1,
        ), run_id="run", source_artifact_id="source", source_revision_id="sha256:" + "a" * 64,
        source_uri="repo://source", source_evidence_sha256="sha256:" + "b" * 64,
        extraction_profile=WORLDBUILDING_EXTRACTION_PROFILE, campaign_scope="world",
        workspace_document_id="document", workspace_document_revision="revision",
        dispositions=[
            {"assertion_id": node.node_id, "decision": "reject" if reject else "create_new"}
            for node in nodes
        ] + [{"assertion_id": edge.edge_id, "decision": "reject" if reject else "accept"}],
    ).effect


def test_native_inventory_accounts_for_actual_product_without_publication():
    import json
    from apps.live_control_server.services.native_first_world_effects import inventory_first_world_native_effects

    effect = _first_world_effect()
    result = inventory_first_world_native_effects(effect)
    assert result.status == "unsupported"
    assert result.inventory.reviewed_effect == effect
    assert result.inventory.accepted_graph_effect_count == 3
    assert {block.code for block in result.blockers} >= {
        "prospective_alias_target_unsupported", "native_evidence_binding_required",
        "metadata_translation_required", "summary_disposition_required", "predicate_mapping_required",
    }
    assert [alias.classic_published_aliases for alias in result.inventory.aliases] == [("Alice",), ("Bob",)]
    assert len(result.inventory.summaries) == 2
    assert all(json.loads(summary.reviewed_json) == "Reviewed description"
               and summary.classic_published_json == "null"
               and summary.native_disposition == "unresolved" for summary in result.inventory.summaries)
    def leaves(value, path=""):
        if isinstance(value, dict) and value:
            for key, child in value.items():
                yield from leaves(child, path + "/" + key.replace("~", "~0").replace("/", "~1"))
        elif isinstance(value, list) and value:
            for index, child in enumerate(value):
                yield from leaves(child, path + "/" + str(index))
        else:
            yield path or "/", json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert {field.field_path: field.reviewed_json for field in result.inventory.fields} == dict(leaves(effect))
    assert not hasattr(result, "operations")
    assert all(block.assertion_id and block.candidate_ids for block in result.blockers)


def test_native_inventory_rejections_are_audit_only():
    from apps.live_control_server.services.native_first_world_effects import inventory_first_world_native_effects

    effect = _first_world_effect(reject=True)
    result = inventory_first_world_native_effects(effect)
    assert result.status == "non_publishing"
    assert result.inventory.accepted_graph_effect_count == 0
    assert result.inventory.reviewed_effect == effect
    assert len(result.inventory.reviewed_effect["rejected_assertions"]) == 3
    assert not result.inventory.aliases


def test_native_inventory_unknown_fields_keep_every_value_and_pointer():
    from apps.live_control_server.services.native_first_world_effects import inventory_first_world_native_effects

    effect = _first_world_effect()
    effect["accepted_proposals"][0]["value"]["future~/field"] = {"nested": [True, 1, 1.0]}
    effect["accepted_proposals"][0]["value"]["evidence"][0]["future"] = "retained"
    result = inventory_first_world_native_effects(effect)
    assert result.inventory.reviewed_effect == effect
    blockers = {block.field_path for block in result.blockers if block.code == "unsupported_effect_field"}
    assert "/accepted_proposals/0/value/future~0~1field" in blockers
    assert "/accepted_proposals/0/value/evidence/0/future" in blockers
    fields = {field.field_path: field.reviewed_json for field in result.inventory.fields}
    prefix = "/accepted_proposals/0/value/future~0~1field/nested/"
    assert [fields[prefix + str(i)] for i in range(3)] == ["true", "1", "1.0"]


def test_native_inventory_is_immutable_and_order_sensitive():
    from dataclasses import FrozenInstanceError
    from copy import deepcopy
    from apps.live_control_server.services.native_first_world_effects import inventory_first_world_native_effects

    effect = _first_world_effect()
    result = inventory_first_world_native_effects(effect)
    original = deepcopy(effect)
    effect["accepted_proposals"].clear()
    result.inventory.reviewed_effect["accepted_proposals"].clear()
    assert result.inventory.reviewed_effect == original
    with pytest.raises(FrozenInstanceError):
        result.inventory.effect_sha256 = "changed"
    reordered = dict(reversed(list(original.items())))
    assert inventory_first_world_native_effects(reordered).inventory.effect_sha256 == result.inventory.effect_sha256
    reordered["accepted_proposals"][0]["value"]["aliases"].reverse()
    assert inventory_first_world_native_effects(reordered).inventory.effect_sha256 != result.inventory.effect_sha256


@pytest.mark.parametrize("damage", ["outer", "crosslink", "nonfinite", "cycle", "depth", "size", "count"])
def test_native_inventory_rejects_malformed_or_unbounded_packets(damage):
    from apps.live_control_server.services.native_first_world_effects import (
        FirstWorldEffectInputError, inventory_first_world_native_effects, MAX_EFFECT_BYTES,
    )
    effect = _first_world_effect()
    if damage == "outer":
        effect["unexpected"] = 1
    elif damage == "crosslink":
        effect["candidate_effect_map"]["candidate:a"] = ["missing"]
    elif damage == "nonfinite":
        effect["accepted_proposals"][0]["value"]["future"] = float("nan")
    elif damage == "cycle":
        effect["cycle"] = effect
    elif damage == "depth":
        nested = []
        effect["deep"] = nested
        for _ in range(35):
            child = []
            nested.append(child)
            nested = child
    elif damage == "count":
        effect["large"] = [None] * 50_001
    else:
        effect["large"] = "a" * (MAX_EFFECT_BYTES + 1)
    with pytest.raises(FirstWorldEffectInputError):
        inventory_first_world_native_effects(effect)


@pytest.mark.parametrize("kind", ["edge", "identity", "bind_existing", "defer"])
def test_native_inventory_zero_node_count_does_not_hide_effects(kind):
    from apps.live_control_server.services.native_first_world_effects import inventory_first_world_native_effects
    from graph_memory.worldbuilding_write_plan import WORLDBUILDING_IDENTITY_SNAPSHOT_SCHEMA

    effect = _first_world_effect(reject=True)
    if kind == "edge":
        row = effect["rejected_assertions"].pop()
        assert row["assertion_kind"] == "edge"
        row["acceptance_state"] = "accepted"
        effect["accepted_proposals"] = [row]
        effect["decision_snapshot"][-1]["decision"] = "accept"
        effect["identity_outcome_snapshot"]["edge:one"] = "accepted_by_operator"
    elif kind == "identity":
        effect["identity_authority"] = {
            "schema": WORLDBUILDING_IDENTITY_SNAPSHOT_SCHEMA, "decisions": [],
            "identity_redirects": {"old": "new"}, "alias_owners": {},
        }
    else:
        decision = effect["decision_snapshot"][0]
        identifier = effect["candidate_effect_map"][decision["assertion_id"]][0]
        effect["rejected_assertions"] = [row for row in effect["rejected_assertions"]
                                         if row["assertion_id"] != identifier]
        effect["candidate_effect_map"][decision["assertion_id"]] = []
        decision["decision"] = kind
        if kind == "bind_existing":
            decision["target_node_id"] = "existing"
            effect["node_id_map"][decision["assertion_id"]] = "existing"
            effect["identity_outcome_snapshot"][decision["assertion_id"]] = "human_override"
        else:
            effect["deferred_candidate_ids"] = [decision["assertion_id"]]
            effect["identity_outcome_snapshot"][decision["assertion_id"]] = "deferred_by_operator"
            from apps.live_control_server.models.world_graph_contribution_models import ContributionIdentityMention
            effect["unresolved_mentions"] = [ContributionIdentityMention(
                mention_id=decision["assertion_id"], label="Alice", object_kind="npc",
                aliases=["Alice"], evidence_ref_ids=["evidence:one"],
                identity_resolution_outcome="deferred_by_operator",
            ).model_dump(mode="json")]
    result = inventory_first_world_native_effects(effect)
    assert result.inventory.reviewed_effect == effect
    assert result.status == ("non_publishing" if kind == "defer" else "unsupported")


def test_native_inventory_never_calls_authority_or_provider(monkeypatch):
    from apps.live_control_server.services import first_world_graph as producer
    from apps.live_control_server.services.native_first_world_effects import inventory_first_world_native_effects

    effect = _first_world_effect()
    def forbidden(*args, **kwargs):
        pytest.fail("inventory touched external authority")
    for name in ("get_source_artifact", "get_world_container", "get_committed_page_snapshot"):
        monkeypatch.setattr(producer, name, forbidden)
    assert inventory_first_world_native_effects(effect).status == "unsupported"


@pytest.mark.parametrize("damage", ["identity", "outcome", "deferred", "mention", "shared"])
def test_native_inventory_rejects_contradictory_identity_accounting(damage):
    from apps.live_control_server.services.native_first_world_effects import (
        FirstWorldEffectInputError, inventory_first_world_native_effects,
    )
    effect = _first_world_effect(reject=True)
    if damage == "identity":
        effect["node_id_map"]["candidate:a"] = "claimed-created-identity"
    elif damage == "outcome":
        effect["identity_outcome_snapshot"]["candidate:a"] = "created_new"
    elif damage == "deferred":
        effect["deferred_candidate_ids"] = ["orphan"]
    elif damage == "mention":
        from apps.live_control_server.models.world_graph_contribution_models import ContributionIdentityMention
        effect["unresolved_mentions"] = [ContributionIdentityMention(
            mention_id="orphan", label="Orphan", object_kind="npc",
            identity_resolution_outcome="deferred_by_operator",
        ).model_dump(mode="json")]
    else:
        effect["candidate_effect_map"]["candidate:b"].extend(effect["candidate_effect_map"]["candidate:a"])
    with pytest.raises(FirstWorldEffectInputError):
        inventory_first_world_native_effects(effect)


@pytest.mark.parametrize("value", [True, 1, 1.0])
def test_native_inventory_digest_preserves_numeric_kinds(value):
    from apps.live_control_server.services.native_first_world_effects import inventory_first_world_native_effects
    effect = _first_world_effect()
    effect["accepted_proposals"][0]["value"]["future"] = value
    result = inventory_first_world_native_effects(effect)
    others = []
    for alternative in (True, 1, 1.0):
        if type(alternative) is type(value):
            continue
        effect["accepted_proposals"][0]["value"]["future"] = alternative
        others.append(inventory_first_world_native_effects(effect).inventory.effect_sha256)
    assert result.inventory.effect_sha256 not in others


def test_native_inventory_evidence_list_order_is_part_of_commitment():
    from copy import deepcopy
    from apps.live_control_server.services.native_first_world_effects import inventory_first_world_native_effects
    effect = _first_world_effect()
    evidence = effect["accepted_proposals"][0]["value"]["evidence"]
    evidence.append({**deepcopy(evidence[0]), "source_span_ref_id": "span:two"})
    original = inventory_first_world_native_effects(effect)
    evidence.reverse()
    reversed_result = inventory_first_world_native_effects(effect)
    assert original.inventory.effect_sha256 != reversed_result.inventory.effect_sha256
    assert original.inventory.reviewed_effect["accepted_proposals"][0]["value"]["evidence"][0]["source_span_ref_id"] == "span:one"



def test_native_inventory_rejected_candidate_cannot_lose_its_effect():
    from apps.live_control_server.services.native_first_world_effects import (
        FirstWorldEffectInputError, inventory_first_world_native_effects,
    )
    effect = _first_world_effect(reject=True)
    identifier = effect["candidate_effect_map"]["candidate:a"][0]
    effect["candidate_effect_map"]["candidate:a"] = []
    effect["rejected_assertions"] = [row for row in effect["rejected_assertions"]
                                     if row["assertion_id"] != identifier]
    with pytest.raises(FirstWorldEffectInputError, match="decision_has_no_effect"):
        inventory_first_world_native_effects(effect)


@pytest.mark.parametrize("duplicate", ["id", "mention"])
def test_native_inventory_rejects_duplicate_deferred_accounting(duplicate):
    from copy import deepcopy
    from apps.live_control_server.models.world_graph_contribution_models import ContributionIdentityMention
    from apps.live_control_server.services.native_first_world_effects import (
        FirstWorldEffectInputError, inventory_first_world_native_effects,
    )
    effect = _first_world_effect(reject=True)
    identifier = effect["candidate_effect_map"]["candidate:a"][0]
    effect["candidate_effect_map"]["candidate:a"] = []
    effect["rejected_assertions"] = [row for row in effect["rejected_assertions"]
                                     if row["assertion_id"] != identifier]
    effect["decision_snapshot"][0]["decision"] = "defer"
    effect["identity_outcome_snapshot"]["candidate:a"] = "deferred_by_operator"
    effect["deferred_candidate_ids"] = ["candidate:a"]
    effect["unresolved_mentions"] = [ContributionIdentityMention(
        mention_id="candidate:a", label="Alice", object_kind="npc", aliases=["Alice"],
        evidence_ref_ids=["evidence:one"], identity_resolution_outcome="deferred_by_operator",
    ).model_dump(mode="json")]
    assert inventory_first_world_native_effects(effect).status == "non_publishing"
    if duplicate == "id":
        effect["deferred_candidate_ids"].append("candidate:a")
    else:
        mention = deepcopy(effect["unresolved_mentions"][0])
        mention["aliases"] = ["Conflicting alias"]
        effect["unresolved_mentions"].append(mention)
    with pytest.raises(FirstWorldEffectInputError):
        inventory_first_world_native_effects(effect)
