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
def _first_world_effect(*, reject=False, source_index=None, predicate="knows", node_type="character", reject_edge=False):
    from apps.live_control_server.models.extract_promote import FirstWorldNativeTarget
    from apps.live_control_server.services.first_world_graph import materialize_first_world_plan
    from graph_memory.candidate_graph_preview import (
        CandidateGraphPreview, CandidateNode, CandidateEdge, EvidenceRef,
        PreviewDiagnostics, SemanticState,
    )
    from graph_memory.worldbuilding_write_plan import WORLDBUILDING_EXTRACTION_PROFILE

    state = SemanticState("worldbuilding_draft", "candidate", "source_evidence",
                          "system_derived", "gm_private")
    evidence = (EvidenceRef(
        source_index.source_ref_id if source_index else "ref:one", "source",
        source_span_ref_id=source_index.spans[0].source_span_id if source_index else "span:one",
    ),)
    nodes = tuple(CandidateNode(
        node_id=identifier, label=label, node_type=node_type, description="Reviewed description",
        importance="high", semantic_state=state, evidence_refs=evidence,
        proposed_action="create", confidence="high", aliases=(label, label.upper(), "  "),
    ) for identifier, label in (("candidate:a", "Alice"), ("candidate:b", "Bob")))
    edge = CandidateEdge("edge:one", "candidate:a", "candidate:b", predicate, predicate,
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
        ), run_id="run", source_artifact_id="source", source_revision_id="sha256:" + (source_index.content_sha256 if source_index else "a" * 64),
        source_uri="repo://source", source_evidence_sha256="sha256:" + "b" * 64,
        extraction_profile=WORLDBUILDING_EXTRACTION_PROFILE, campaign_scope="world",
        workspace_document_id="document", workspace_document_revision="revision",
        dispositions=[
            {"assertion_id": node.node_id, "decision": "reject" if reject else "create_new"}
            for node in nodes
        ] + [{"assertion_id": edge.edge_id, "decision": "reject" if reject or reject_edge else "accept"}],
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


# B1 uses the installed public Core API. No allocator/planner or database fixture.
def _native_compilation_case(*, custom=False, reject=False, node_type="character", source_text=None, native_role="support"):
    from datetime import UTC, datetime
    from hashlib import sha256
    from dungeonmind.application.vnext import (
        initialize_empty_knowledge_space, publish_native_text_source_evidence,
    )
    from dungeonmind.application.vnext.builder import build_parsed_knowledge_revision
    from dungeonmind.application.vnext.materialization import decode_native_graph_payload
    from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
    from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldNativeSpanBinding
    from graph_memory.source_span import build_source_span_index_for_text
    from graph_memory.vnext.domain_runtime import (
        dungeonbuddy_world_domain_contract, dungeonbuddy_dnd5e_semantic_profile,
        dungeonbuddy_dnd5e_custom_predicate_profile, GM_LABEL,
    )

    # Deliberately UTF-8, CRLF, multiple paragraphs and no terminal newline.
    text = "Álice meets Bob beside the towér.\r\nThey remember the bridge.\r\n\r\nUnrelated paragraph."
    if source_text is not None:
        text = source_text
    digest = sha256(text.encode()).hexdigest()
    index = build_source_span_index_for_text(source_artifact_id="source", text=text, content_sha256=digest)
    effect = _first_world_effect(reject=reject, source_index=index,
                                predicate="knows" if custom else "located_in", node_type=node_type)
    now = datetime(2026, 11, 19, tzinfo=UTC)
    space = "world:" + "1" * 32
    domain = dungeonbuddy_world_domain_contract()
    profile = (dungeonbuddy_dnd5e_custom_predicate_profile() if custom
               else dungeonbuddy_dnd5e_semantic_profile())
    repo = InMemoryNativeSourceEvidenceRepository()
    initialize_empty_knowledge_space(repository=repo, space_id=space, initialization_id="compiler-genesis",
                                     created_at=now, domain_contract=domain, semantic_profile=profile)
    # Exact span index uses inclusive lines without the end-line separator.
    span = index.spans[0]
    raw_lines = text.splitlines(keepends=True)
    start = len("".join(raw_lines[:span.start_line - 1]).encode())
    end = len("".join(raw_lines[:span.end_line - 1]).encode()) + len(text.splitlines()[span.end_line - 1].encode())
    receipt = publish_native_text_source_evidence(
        repository=repo, domain_contract=domain, semantic_profile=profile,
        request=NativeTextSourceAdmissionV1(
            space_id=space, admission_id="compiler-source", expected_parent_revision_id=repo.get_head(space).head_revision_id,
            created_at=now, body_text=text, expected_body_sha256=digest,
            source_classification="dungeonbuddy.source:worldbuilding", authority="primary",
            visibility={"kind": "labels_any", "labels": [GM_LABEL]},
            origin={"namespace": "dungeonbuddy.source", "object_id": "source", "revision_id": "sha256:" + digest},
            spans=[dict(client_ref=span.source_span_id, evidence_role=native_role, start_byte=start, end_byte=end,
                        expected_slice_sha256=sha256(text.encode()[start:end]).hexdigest())],
        ),
    )
    stored = repo.get_revision(space, receipt.published_revision_id)
    parent = build_parsed_knowledge_revision(stored.revision, decoded_content=decode_native_graph_payload(stored.graph_payload))
    native = repo.open_native_source_view(space).get_native_text_source(
        source_artifact_id=receipt.source_artifact_id, source_revision_id=receipt.source_revision_id,
        span_id=receipt.bindings[0].span_id,
    )
    raw_id = (effect["accepted_proposals"] or effect["rejected_assertions"])[0]["evidence_ref_ids"][0]
    bindings = (FirstWorldNativeSpanBinding.from_proof(raw_id, native.span_proof, source_revision=native.source_revision),)
    return SimpleNamespace(effect=effect, text=text, index=index, repo=repo, parent=parent,
                           bindings=bindings, now=now, space=space, domain=domain, profile=profile,
                           admission=receipt, native=native)


def _compile_and_bind(case):
    from apps.live_control_server.services.native_first_world_compilation import (
        compile_first_world_native_intent, bind_first_world_native_intent,
    )
    intent = compile_first_world_native_intent(case.effect, world_id="world", source_text=case.text, span_index=case.index)
    bound = bind_first_world_native_intent(intent, parent=case.parent, native_space_id=case.space,
                                         bindings=case.bindings, produced_at=case.now)
    return intent, bound


def _publish_compilation(case, bound):
    from dungeonmind.application.vnext.materialization import GovernedPublicationIdentity
    from dungeonmind.application.vnext.prospective_aliases import publish_prospective_alias_contribution

    return publish_prospective_alias_contribution(
        parent=case.parent, request=bound.request, dispositions=bound.dispositions,
        publication=GovernedPublicationIdentity(operation_ids=("compiler-reviewed-publication",),
                                                created_at=case.now, expected_parent_revision_id=case.parent.revision_id),
        publication_id="compiler-reviewed-publication", domain_contract=case.domain,
        semantic_profile=case.profile, repository=case.repo,
    )


@pytest.mark.parametrize("custom,node_type", [(False, "character"), (True, "character"), (False, "item")])
def test_native_compiler_public_kernel_publication_readback_and_exact_citation(custom, node_type):
    from dungeonmind.application.vnext.entity_reads import EntityReadService
    from dungeonmind.application.vnext.native_source_access import (
        open_native_text_source_access_context, open_admitted_native_text,
    )
    from graph_memory.vnext.domain_runtime import (
        DungeonBuddyVNextProjectionInput, build_dungeonbuddy_read_context, GM_LABEL, PLAYER_LABEL,
    )

    case = _native_compilation_case(custom=custom, node_type=node_type)
    intent, bound = _compile_and_bind(case)
    before_parent = case.parent.semantic_digest
    result = _publish_compilation(case, bound)
    # Exact retry is idempotent: the original parent and identical sealed packet.
    head = case.repo.get_head(case.space)
    assert _publish_compilation(case, bound) == result
    assert case.repo.get_head(case.space) == head
    context = open_native_text_source_access_context(
        repository=case.repo, space_id=case.space, revision_id=result.publication_receipt.published_revision_id,
        domain_contract=case.domain, audience_labels=[GM_LABEL, PLAYER_LABEL],
    )
    parsed = context.parsed
    assert len(parsed.entities_by_id) == 2
    assert len(parsed.assertions_by_id) == 7  # name, classification, reviewed summary x2 + directed edge
    assert len(parsed.aliases_by_id) == 2
    assert case.parent.semantic_digest == before_parent and not case.parent.entities_by_id
    read = build_dungeonbuddy_read_context(
        parsed_revision=parsed, projection_input=DungeonBuddyVNextProjectionInput(
            world_id=case.space, scope_mode="world", role="gm"), source_reader=context.source_view,
    )
    service = EntityReadService()
    listing = service.list_entities_with_support(read)
    assert len(listing.aliases) == 2
    assert {alias.alias_text for alias in listing.aliases} == {"Alice", "Bob"}
    all_assertions = tuple(parsed.assertions_by_id.values())
    assert sorted(a.value.value for a in all_assertions if a.predicate == "dnd5e:name") == ["Alice", "Bob"]
    assert [a.value.value for a in all_assertions if a.predicate == "dnd5e:summary"] == ["Reviewed description"] * 2
    classifications = {a.value.term for a in all_assertions if a.predicate == "dnd5e:classification"}
    assert classifications == {"dungeonbuddy:item" if node_type == "item" else "dnd5e:npc"}
    edge = next(a for a in all_assertions if a.value.kind == "entity_ref")
    assert edge.predicate == ("dungeonbuddy.custom:knows" if custom else "dnd5e:located_in")
    names = {a.subject_entity_id: a.value.value for a in all_assertions if a.predicate == "dnd5e:name"}
    assert names[edge.subject_entity_id] == "Alice" and names[edge.value.entity_id] == "Bob"
    assert all(not a.metadata.scope and a.metadata.epistemic_basis == "inferred"
               and a.metadata.standing == "established" and a.metadata.temporal_scope.kind == "unknown"
               for a in all_assertions)
    for entity in listing.listing.entities:
        complete = service.get_complete_entity(read, entity.entity_id)
        assert complete.found and complete.aliases and complete.evidence
    evidence_id = case.bindings[0].proof.evidence_ref_id
    opened = open_admitted_native_text(context, evidence_id)
    assert opened.status == "available" and opened.body_text.encode() == case.text.encode()
    assert opened.span_start_byte == case.bindings[0].proof.start_byte
    assert opened.span_end_byte == case.bindings[0].proof.end_byte
    assert opened.span_sha256 == case.bindings[0].proof.slice_sha256
    assert intent.sha256 == bound.intent_sha256
    assert {d.item_id for d in bound.dispositions} == {
        i.item_id for i in bound.request.contribution.items
    } | {a.item_id for a in bound.request.aliases}


def test_native_compiler_real_source_withdrawal_removes_aliases_and_citation():
    from dungeonmind.application.vnext.entity_reads import EntityReadService
    from dungeonmind.application.vnext.native_source_access import (
        open_native_text_source_access_context, open_admitted_native_text,
    )
    from graph_memory.vnext.domain_runtime import DungeonBuddyVNextProjectionInput, build_dungeonbuddy_read_context, GM_LABEL

    case = _native_compilation_case()
    _, bound = _compile_and_bind(case)
    result = _publish_compilation(case, bound)
    case.repo.withdraw_native_source(space_id=case.space, source_artifact_id=case.admission.source_artifact_id,
                                     source_revision_id=case.admission.source_revision_id)
    context = open_native_text_source_access_context(
        repository=case.repo, space_id=case.space, revision_id=result.publication_receipt.published_revision_id,
        domain_contract=case.domain, audience_labels=[GM_LABEL],
    )
    read = build_dungeonbuddy_read_context(parsed_revision=context.parsed,
        projection_input=DungeonBuddyVNextProjectionInput(world_id=case.space, scope_mode="world", role="gm"),
        source_reader=context.source_view)
    assert not EntityReadService().list_entities_with_support(read).aliases
    assert open_admitted_native_text(context, case.bindings[0].proof.evidence_ref_id).status == "unavailable"


@pytest.mark.parametrize("damage", ["body", "index_digest", "span_bounds", "unknown_value", "metadata", "role", "source_identity", "conflicting_evidence", "rejected_endpoint"])
def test_native_compiler_refuses_damaged_reviewed_input_before_authority(damage):
    from copy import deepcopy
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldCompilationError
    from apps.live_control_server.services.native_first_world_compilation import compile_first_world_native_intent

    case = _native_compilation_case()
    effect, text, index = deepcopy(case.effect), case.text, case.index
    first = effect["accepted_proposals"][0]
    if damage == "body":
        text += "Changed"
    elif damage == "index_digest":
        index = replace(index, content_sha256="0" * 64)
    elif damage == "span_bounds":
        index = replace(index, spans=(replace(index.spans[0], end_line=100_000),))
    elif damage == "unknown_value":
        first["value"]["unreviewed"] = {"future": True}
    elif damage == "metadata":
        first["temporal_scope"] = {"kind": "timeless"}
    elif damage == "role":
        first["value"]["role"] = "location"
    elif damage == "source_identity":
        first["value"]["source_artifacts"][0]["content_sha256"] = "0" * 64
    elif damage == "conflicting_evidence":
        # The same reviewed ref is not allowed to name another source span.
        effect["accepted_proposals"][1]["value"]["evidence"][0]["source_span_ref_id"] = index.spans[1].source_span_id
        effect["accepted_proposals"][1]["value"]["evidence"][0]["locator"] = index.spans[1].source_span_id
    else:
        effect["decision_snapshot"][1]["decision"] = "reject"
        rejected = effect["accepted_proposals"].pop(1)
        rejected["acceptance_state"] = "rejected"
        rejected["identity_resolution_outcome"] = "rejected_by_operator"
        effect["rejected_assertions"].append(rejected)
        effect["node_id_map"].pop("candidate:b")
        effect["identity_outcome_snapshot"]["candidate:b"] = "rejected_by_operator"
    head, epoch = case.repo.get_head(case.space), case.repo.open_native_source_view(case.space).epoch
    with pytest.raises(FirstWorldCompilationError):
        compile_first_world_native_intent(effect, world_id="world", source_text=text, span_index=index)
    assert case.repo.get_head(case.space) == head
    assert case.repo.open_native_source_view(case.space).epoch == epoch


@pytest.mark.parametrize("damage", ["missing", "duplicate", "foreign", "interval", "slice", "revision", "evidence", "span", "space", "descriptor", "entities", "assertions", "aliases", "intent", "naive_time"])
def test_native_compiler_binder_refuses_foreign_or_corrupted_inputs(damage):
    from datetime import datetime
    from dungeonmind.application.vnext.frozen_json import FrozenDict
    from dungeonmind.application.vnext.records import ParsedEntity
    from apps.live_control_server.models.native_first_world_compilation import (
        FirstWorldCompilationError, FirstWorldNativeSpanBinding,
    )
    from apps.live_control_server.services.native_first_world_compilation import (
        compile_first_world_native_intent, bind_first_world_native_intent,
    )

    case = _native_compilation_case()
    intent = compile_first_world_native_intent(case.effect, world_id="world", source_text=case.text, span_index=case.index)
    parent, space, bindings, now = case.parent, case.space, case.bindings, case.now
    proof = bindings[0].proof
    if damage == "missing":
        bindings = ()
    elif damage == "duplicate":
        bindings *= 2
    elif damage == "foreign":
        bindings = (FirstWorldNativeSpanBinding.from_proof("not-reviewed", proof, source_revision=case.native.source_revision),)
    elif damage in {"interval", "slice", "revision", "evidence", "span"}:
        key, value = {"interval": ("end_byte", proof.end_byte + 1), "slice": ("slice_sha256", "0" * 64),
                      "revision": ("source_revision_id", "revision:foreign"), "evidence": ("evidence_ref_id", "evidence:foreign"),
                      "span": ("span_id", "span:foreign")}[damage]
        bindings = (FirstWorldNativeSpanBinding.from_proof(bindings[0].reviewed_evidence_ref_id,
                                                         proof.model_copy(update={key: value}), source_revision=case.native.source_revision),)
    elif damage == "space":
        space = "world:foreign"
    elif damage == "descriptor":
        parent = replace(parent, identity=replace(parent.identity,
                         domain_contract_ref=replace(parent.domain_contract_ref, descriptor_sha256="0" * 64)))
    elif damage in {"entities", "assertions", "aliases"}:
        # Binder must reject structural non-source-only data before interpreting it.
        parent = replace(parent, **{damage + "_by_id": FrozenDict({"foreign": ParsedEntity(entity_id="ent:foreign")})})
    elif damage == "intent":
        intent = replace(intent, sha256="0" * 64)
    else:
        now = datetime(2026, 11, 19)
    with pytest.raises(FirstWorldCompilationError):
        bind_first_world_native_intent(intent, parent=parent, native_space_id=space, bindings=bindings, produced_at=now)


def test_native_compiler_all_rejected_is_nonpublishing_and_cannot_bind():
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldCompilationError
    from apps.live_control_server.services.native_first_world_compilation import (
        compile_first_world_native_intent, bind_first_world_native_intent,
    )

    case = _native_compilation_case(reject=True)
    intent = compile_first_world_native_intent(case.effect, world_id="world", source_text=case.text, span_index=case.index)
    assert not intent.publishing
    assert not intent.audit["nodes"] and not intent.audit["edges"]
    assert intent.audit["reviewed_effect"]["rejected_assertions"] == case.effect["rejected_assertions"]
    with pytest.raises(FirstWorldCompilationError, match="non_publishing_intent"):
        bind_first_world_native_intent(intent, parent=case.parent, native_space_id=case.space,
                                      bindings=(), produced_at=case.now)


def test_native_compiler_custom_profile_transition_is_explicit_and_not_performed():
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldCompilationError
    from apps.live_control_server.services.native_first_world_compilation import (
        compile_first_world_native_intent, bind_first_world_native_intent,
    )

    case = _native_compilation_case()
    effect = _first_world_effect(source_index=case.index, predicate="knows")
    intent = compile_first_world_native_intent(effect, world_id="world", source_text=case.text, span_index=case.index)
    head = case.repo.get_head(case.space)
    with pytest.raises(FirstWorldCompilationError, match="profile_transition_required"):
        bind_first_world_native_intent(intent, parent=case.parent, native_space_id=case.space,
                                      bindings=case.bindings, produced_at=case.now)
    assert case.repo.get_head(case.space) == head and case.parent.semantic_profile_ref.profile_revision == "1"


def test_native_compiler_sealed_models_and_returned_public_models_are_independent():
    from dataclasses import FrozenInstanceError
    from apps.live_control_server.services.native_first_world_compilation import bind_first_world_native_intent

    case = _native_compilation_case()
    intent, bound = _compile_and_bind(case)
    original = bound.request.model_dump(mode="json")
    case.effect["accepted_proposals"].clear()
    intent.audit["reviewed_effect"].clear()
    bound.request.contribution.items.clear()
    bound.request.aliases[0].evidence_ref_ids.clear()
    bound.dispositions[0].disposition = "rejected"
    case.bindings[0].proof.end_byte += 1
    case.bindings[0].source_revision.content_sha256 = "0" * 64
    assert bound.request.model_dump(mode="json") == original
    assert all(d.disposition == "accepted" for d in bound.dispositions)
    assert bind_first_world_native_intent(intent, parent=case.parent, native_space_id=case.space,
                                         bindings=case.bindings, produced_at=case.now) == bound
    with pytest.raises(FrozenInstanceError):
        intent.sha256 = "0" * 64
    with pytest.raises(FrozenInstanceError):
        bound.request_json = "{}"
    # The complete reviewed input, not merely an adjacent digest, is in Core's request.
    assert bound.request.contribution.diagnostics[0].payload["reviewed_effect"] == intent.audit["reviewed_effect"]


def test_native_compiler_rejected_intent_is_committed_inside_kernel_request():
    from copy import deepcopy
    from apps.live_control_server.services.native_first_world_compilation import (
        compile_first_world_native_intent, bind_first_world_native_intent,
    )
    from dungeonmind.application.vnext.errors import KnowledgePublicationIdempotencyConflictError

    case = _native_compilation_case()
    effect = _first_world_effect(source_index=case.index, predicate="located_in", reject_edge=True)
    changed = deepcopy(effect)
    changed["rejected_assertions"][0]["label"] = "Different rejected proposal"
    packets = []
    for raw in (effect, changed):
        intent = compile_first_world_native_intent(raw, world_id="world", source_text=case.text, span_index=case.index)
        bound = bind_first_world_native_intent(intent, parent=case.parent, native_space_id=case.space,
                                              bindings=case.bindings, produced_at=case.now)
        assert bound.request.contribution.diagnostics[0].payload["reviewed_effect"] == raw
        assert not any(i.kind == "create_assertion" and i.value.kind == "entity_ref"
                       for i in bound.request.contribution.items)
        packets.append((intent, bound))
    assert packets[0][0].sha256 != packets[1][0].sha256
    assert packets[0][1].request_sha256 != packets[1][1].request_sha256
    _publish_compilation(case, packets[0][1])
    head = case.repo.get_head(case.space)
    with pytest.raises(KnowledgePublicationIdempotencyConflictError):
        _publish_compilation(case, packets[1][1])
    assert case.repo.get_head(case.space) == head


@pytest.mark.parametrize("aliases,expected", [
    ([" Alice ", "alice", "ALICE", "  ", "Alice"], [" Alice ", "alice"]),
    ([], ["Alice"]),
])
def test_native_compiler_alias_mapping_matches_classic_first_surviving_spelling(aliases, expected):
    from apps.live_control_server.services.native_first_world_compilation import compile_first_world_native_intent

    case = _native_compilation_case()
    case.effect["accepted_proposals"][0]["value"]["aliases"] = aliases
    intent = compile_first_world_native_intent(case.effect, world_id="world", source_text=case.text, span_index=case.index)
    assert intent.audit["nodes"][0]["aliases"] == expected
    assert intent.audit["reviewed_effect"]["accepted_proposals"][0]["value"]["aliases"] == aliases


@pytest.mark.parametrize("field,value,row_index", [
    ("dm_kind", "dnd5e:location", 0),
    ("label", "Contradictory inner label", 0),
    ("dm_predicate", "dungeonbuddy:allied_with", 2),
    ("edge_id", "edge:unrelated", 2),
    ("extract_edge_id", "edge:unrelated", 2),
])
def test_native_compiler_refuses_conflicting_accepted_value_operands(field, value, row_index):
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldCompilationError
    from apps.live_control_server.services.native_first_world_compilation import compile_first_world_native_intent

    case = _native_compilation_case()
    case.effect["accepted_proposals"][row_index]["value"][field] = value
    with pytest.raises(FirstWorldCompilationError):
        compile_first_world_native_intent(case.effect, world_id="world", source_text=case.text, span_index=case.index)


def test_native_compiler_and_binder_do_not_perform_io(monkeypatch):
    import builtins
    import socket
    from pathlib import Path
    import httpx

    case = _native_compilation_case()
    def forbidden(*_args, **_kwargs):
        pytest.fail("pure compiler touched I/O")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    monkeypatch.setattr(case.repo, "get_revision", forbidden)
    monkeypatch.setattr(case.repo, "get_head", forbidden)
    monkeypatch.setattr(case.repo, "publish_revision", forbidden)
    monkeypatch.setattr(case.repo, "open_native_source_view", forbidden)
    intent, bound = _compile_and_bind(case)
    assert intent.publishing and bound.request.aliases


def test_native_compiler_rejects_matching_cited_prefix_with_changed_uncited_body():
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldCompilationError
    from apps.live_control_server.services.native_first_world_compilation import (
        compile_first_world_native_intent, bind_first_world_native_intent,
    )

    reviewed = _native_compilation_case()
    different = _native_compilation_case(source_text=reviewed.text.replace(
        "Unrelated paragraph.", "An entirely different uncited tail."))
    reviewed_proof, other_proof = reviewed.bindings[0].proof, different.bindings[0].proof
    assert (reviewed_proof.start_byte, reviewed_proof.end_byte, reviewed_proof.slice_sha256) == (
        other_proof.start_byte, other_proof.end_byte, other_proof.slice_sha256)
    assert reviewed.native.source_revision.content_sha256 != different.native.source_revision.content_sha256
    intent = compile_first_world_native_intent(reviewed.effect, world_id="world",
                                             source_text=reviewed.text, span_index=reviewed.index)
    with pytest.raises(FirstWorldCompilationError):
        bind_first_world_native_intent(intent, parent=different.parent, native_space_id=different.space,
                                      bindings=different.bindings, produced_at=different.now)


@pytest.mark.parametrize("field,value", [
    ("source_artifact_id", "artifact:unrelated"),
    ("source_revision_id", "revision:unrelated"),
    ("content_sha256", "0" * 64),
])
def test_native_compiler_rejects_source_revision_metadata_not_bound_to_parent_and_body(field, value):
    from apps.live_control_server.models.native_first_world_compilation import (
        FirstWorldCompilationError, FirstWorldNativeSpanBinding,
    )
    from apps.live_control_server.services.native_first_world_compilation import (
        compile_first_world_native_intent, bind_first_world_native_intent,
    )

    case = _native_compilation_case()
    intent = compile_first_world_native_intent(case.effect, world_id="world", source_text=case.text, span_index=case.index)
    foreign = case.native.source_revision.model_copy(update={field: value})
    binding = FirstWorldNativeSpanBinding.from_proof(case.bindings[0].reviewed_evidence_ref_id,
                                                  case.bindings[0].proof, source_revision=foreign)
    with pytest.raises(FirstWorldCompilationError):
        bind_first_world_native_intent(intent, parent=case.parent, native_space_id=case.space,
                                      bindings=(binding,), produced_at=case.now)


def test_native_compiler_source_revision_binding_is_required_sealed_and_copy_on_read():
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldNativeSpanBinding

    case = _native_compilation_case()
    original = case.native.source_revision.model_dump(mode="json")
    binding = FirstWorldNativeSpanBinding.from_proof(case.bindings[0].reviewed_evidence_ref_id,
                                                  case.bindings[0].proof, source_revision=case.native.source_revision)
    case.native.source_revision.content_sha256 = "0" * 64
    binding.source_revision.source_artifact_id = "artifact:changed-copy"
    assert binding.source_revision.model_dump(mode="json") == original
    with pytest.raises(TypeError, match="source_revision"):
        FirstWorldNativeSpanBinding.from_proof(binding.reviewed_evidence_ref_id, binding.proof)


def test_native_compiler_rejects_swapped_candidate_subjects_before_publication():
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldCompilationError
    from apps.live_control_server.services.native_first_world_compilation import compile_first_world_native_intent

    case = _native_compilation_case()
    first, second = case.effect["accepted_proposals"][:2]
    first["subject_node_id"], second["subject_node_id"] = second["subject_node_id"], first["subject_node_id"]
    head = case.repo.get_head(case.space)
    with pytest.raises(FirstWorldCompilationError, match="node_subject_candidate_mismatch"):
        compile_first_world_native_intent(case.effect, world_id="world", source_text=case.text, span_index=case.index)
    assert case.repo.get_head(case.space) == head
    assert not case.parent.entities_by_id


def test_native_compiler_allows_exact_native_proof_dedup_for_distinct_reviewed_refs():
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldNativeSpanBinding

    case = _native_compilation_case()
    second = case.effect["accepted_proposals"][1]
    second["evidence_ref_ids"] = ["reviewed:second-reference"]
    second["value"]["evidence"][0]["evidence_ref_id"] = "reviewed:second-reference"
    case.bindings += (FirstWorldNativeSpanBinding.from_proof(
        "reviewed:second-reference", case.native.span_proof, source_revision=case.native.source_revision),)
    _, bound = _compile_and_bind(case)
    result = _publish_compilation(case, bound)
    payload = case.repo.get_revision(case.space, result.publication_receipt.published_revision_id).graph_payload
    assert len(payload["entities"]) == 2
    assert len(payload["aliases"]) == 2
    assert len(payload["evidence"]) == 1
    assert all(a["metadata"]["evidence_ref_ids"] == [case.native.span_proof.evidence_ref_id]
               for a in payload["assertions"])


def test_native_compiler_gm_source_remains_unavailable_to_player_after_publication():
    from dungeonmind.application.vnext.entity_reads import EntityReadService
    from dungeonmind.application.vnext.native_source_access import (
        open_native_text_source_access_context, open_admitted_native_text,
    )
    from graph_memory.vnext.domain_runtime import (
        DungeonBuddyVNextProjectionInput, build_dungeonbuddy_read_context, PLAYER_LABEL,
    )

    case = _native_compilation_case()
    # Even a player-labelled assertion does not authorize its GM-only source.
    case.effect["accepted_proposals"][0]["visibility"] = "player"
    _, bound = _compile_and_bind(case)
    result = _publish_compilation(case, bound)
    context = open_native_text_source_access_context(
        repository=case.repo, space_id=case.space,
        revision_id=result.publication_receipt.published_revision_id,
        domain_contract=case.domain, audience_labels=[PLAYER_LABEL],
    )
    read = build_dungeonbuddy_read_context(
        parsed_revision=context.parsed,
        projection_input=DungeonBuddyVNextProjectionInput(world_id=case.space, scope_mode="world", role="player"),
        source_reader=context.source_view,
    )
    listing = EntityReadService().list_entities_with_support(read)
    assert not listing.aliases and not listing.listing.entities
    assert open_admitted_native_text(context, case.native.span_proof.evidence_ref_id).status == "unavailable"


@pytest.mark.parametrize("forgery", ["edge_as_node", "node_as_edge"])
def test_native_compiler_rejects_assertions_impersonating_another_reviewed_decision_kind(forgery):
    from copy import deepcopy
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldCompilationError
    from apps.live_control_server.services.native_first_world_compilation import compile_first_world_native_intent

    case = _native_compilation_case()
    node, edge = case.effect["accepted_proposals"][0], case.effect["accepted_proposals"][2]
    if forgery == "edge_as_node":
        edge.update(assertion_kind="node", subject_node_id=None, target_node_id=None,
                    predicate=None, label="Forged node", value=deepcopy(node["value"]),
                    identity_resolution_outcome="created_new")
    else:
        node.update(assertion_kind="edge", subject_node_id="candidate:b", target_node_id="candidate:b",
                    predicate=edge["predicate"], value=deepcopy(edge["value"]),
                    identity_resolution_outcome="accepted_by_operator")
        node["value"].update(edge_id="edge:candidate:b:located_in:candidate:b", extract_edge_id="candidate:a")
    head = case.repo.get_head(case.space)
    with pytest.raises(FirstWorldCompilationError, match="assertion_owner_decision_mismatch"):
        compile_first_world_native_intent(case.effect, world_id="world", source_text=case.text, span_index=case.index)
    assert case.repo.get_head(case.space) == head


def test_native_compiler_rejects_duplicate_reviewed_decisions():
    from copy import deepcopy
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldCompilationError
    from apps.live_control_server.services.native_first_world_compilation import compile_first_world_native_intent

    case = _native_compilation_case()
    case.effect["decision_snapshot"].append(deepcopy(case.effect["decision_snapshot"][0]))
    with pytest.raises(FirstWorldCompilationError):
        compile_first_world_native_intent(case.effect, world_id="world", source_text=case.text, span_index=case.index)


def test_native_compiler_invalid_binding_reference_has_a_typed_refusal():
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldCompilationError
    from apps.live_control_server.services.native_first_world_compilation import bind_first_world_native_intent

    case = _native_compilation_case()
    intent, _ = _compile_and_bind(case)
    bad = replace(case.bindings[0], reviewed_evidence_ref_id=[])
    with pytest.raises(FirstWorldCompilationError, match="invalid_reviewed_evidence_ref"):
        bind_first_world_native_intent(intent, parent=case.parent, native_space_id=case.space,
                                      bindings=(bad,), produced_at=case.now)


def test_native_compiler_preserves_local_source_reference_correlations_in_request_identity():
    from copy import deepcopy
    from apps.live_control_server.services.native_first_world_compilation import (
        compile_first_world_native_intent, bind_first_world_native_intent,
    )
    case = _native_compilation_case()
    case.effect["accepted_proposals"][0]["value"]["evidence"][0]["source_ref_id"] = "candidate-local:Alice"
    case.effect["accepted_proposals"][1]["value"]["evidence"][0]["source_ref_id"] = "candidate-local:Bob"
    changed = deepcopy(case.effect)
    changed["accepted_proposals"][0]["value"]["evidence"][0]["source_ref_id"] = "candidate-local:changed"
    packets = []
    for raw in (case.effect, changed):
        intent = compile_first_world_native_intent(raw, world_id="world", source_text=case.text, span_index=case.index)
        assert intent.audit["reviewed_effect"] == raw
        bound = bind_first_world_native_intent(intent, parent=case.parent, native_space_id=case.space,
                                              bindings=case.bindings, produced_at=case.now)
        assert bound.request.contribution.diagnostics[0].payload["reviewed_effect"] == raw
        packets.append(bound)
    assert packets[0].intent_sha256 != packets[1].intent_sha256
    assert packets[0].request_sha256 != packets[1].request_sha256
    _publish_compilation(case, packets[0])


@pytest.mark.parametrize("role", ["context", "support"])
def test_native_compiler_preserves_actual_parent_evidence_role_through_public_publication(role):
    case = _native_compilation_case(native_role=role)
    _, bound = _compile_and_bind(case)
    result = _publish_compilation(case, bound)
    payload = case.repo.get_revision(case.space, result.publication_receipt.published_revision_id).graph_payload
    assert [row["evidence_role"] for row in payload["evidence"]] == [role]
    assert len(payload["entities"]) == 2 and len(payload["aliases"]) == 2


def test_native_compiler_never_uses_contradiction_as_positive_reviewed_support():
    from apps.live_control_server.models.native_first_world_compilation import FirstWorldCompilationError
    case = _native_compilation_case(native_role="contradiction")
    head = case.repo.get_head(case.space)
    with pytest.raises(FirstWorldCompilationError, match="native_evidence_mismatch"):
        _compile_and_bind(case)
    assert case.repo.get_head(case.space) == head
