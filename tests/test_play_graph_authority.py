"""Pure Play intent/source commitments; no APP admission, DB or SDK claims."""
import json
from hashlib import sha256
from uuid import UUID

import pytest

from application_state.agent_conversation.types import (
    PlayGraphIntentV1,
    PlaySourceFrameV1,
    PlaySourceLocatorV1,
    PlaySourcePayloadV1,
    source_entry,
)
from application_state.agent_conversation.play_graph_authority import (
    play_graph_intent_fingerprint,
    play_source_frame,
    validate_play_source_owner_join,
)
from application_state.agent_conversation.rules_authority_types import canonical_bytes, canonical_sha256
from application_state.agent_conversation.types import PlayContentBasis, PlayRunTurnContextReceiptV2

MOMENT = "# North\nThe prepared boardwalk 🦉 scene."
NOTE = "Saved 🦉 note."


def basis():
    return PlayRunTurnContextReceiptV2(world_id="world-one", run_id="run-one", run_revision=3,
        runbook_object_id="plan-one", runbook_object_revision=7,
        runbook_work_revision_id=UUID("00000000-0000-4000-8000-000000000001"), runbook_revision_n=2,
        runbook_content_sha256="a" * 64, beat_id="beat:north", scene_id="scene:boardwalk",
        edition_revision=0, edition_revision_id=None, content_sha256="a" * 64,
        scene_note=NOTE, scene_note_sha256=sha256(NOTE.encode()).hexdigest())


def payload(kind="current_moment", text=None, **locator_changes):
    b = basis()
    locator = dict(world_id=b.world_id, run_id=b.run_id, run_revision=b.run_revision,
        edition=PlayContentBasis(edition_revision=0, edition_revision_id=None, content_sha256=b.content_sha256),
        beat_id=b.beat_id, scene_id=b.scene_id)
    locator.update(locator_changes)
    return PlaySourcePayloadV1(source_kind=kind, locator=PlaySourceLocatorV1(**locator),
        text=text if text is not None else NOTE if kind == "scene_note" else MOMENT)


def intent_wire():
    return dict(schema="dmb_play_graph_intent_v1", world_id="world-one", client_thread_id="client-one",
        message="Discuss occupied space 🦉.", surface_id="play", surface_instance_id="play:run-one",
        client_work_state="saved_clean", primary_work=dict(kind="run", object_id="run-one", expected_revision=3,
            play_content_basis=dict(edition_revision=0, edition_revision_id=None, content_sha256="a" * 64)),
        play_graph_policy=dict(schema="dmb_play_graph_policy_v1", policy="native_play_world_v1"),
        play_target=dict(schema="dmb_submitted_play_target_v1", beat_id="beat:north", scene_id="scene:boardwalk", marker_grammar_version="v2"),
        graph_request=dict(mode="world", world_id="world-one", campaign_id=None, revision_pin=None, focus=dict(kind="none")),
        graph_selection=None)


def test_native_play_intent_is_explicit_and_fingerprints_only_original_submission():
    first = PlayGraphIntentV1.model_validate_json(json.dumps(intent_wire()))
    assert PlayGraphIntentV1.model_validate_json(first.model_dump_json(by_alias=True)) == first
    assert play_graph_intent_fingerprint(first) == canonical_sha256(first.model_dump(mode="json", by_alias=True, exclude={"client_thread_id"}))
    routed = intent_wire()
    routed["client_thread_id"] = "resolved-or-renewed-thread"
    assert play_graph_intent_fingerprint(PlayGraphIntentV1.model_validate_json(json.dumps(routed))) == play_graph_intent_fingerprint(first)
    changed = intent_wire()
    changed["play_target"]["scene_id"] = "scene:other"
    second = PlayGraphIntentV1.model_validate_json(json.dumps(changed))
    assert play_graph_intent_fingerprint(first) != play_graph_intent_fingerprint(second)
    assert first.message == "Discuss occupied space 🦉."


@pytest.mark.parametrize("change", ["old_schema", "surface", "work", "edition", "graph_none", "foreign_world", "focus", "policy", "target", "resolved_state"])
def test_native_play_intent_rejects_other_protocols_and_unpinned_or_resolved_inputs(change):
    value = intent_wire()
    if change == "old_schema": value["schema"] = "dmb_agent_submitted_turn_intent_v1"
    if change == "surface": value["surface_id"] = "plan"
    if change == "work": value["primary_work"]["kind"] = "combat"
    if change == "edition": value["primary_work"]["play_content_basis"] = None
    if change == "graph_none": value["graph_request"] = dict(mode="none")
    if change == "foreign_world": value["graph_request"]["world_id"] = "other"
    if change == "focus": value["graph_request"]["focus"] = dict(kind="session", session_id="other")
    if change == "policy": value["play_graph_policy"]["policy"] = "auto_plan_world"
    if change == "target": value["play_target"]["scene_id"] = "beat:wrong"
    if change == "resolved_state": value["graph_authority"] = dict(native_world_id="not-operator-input")
    with pytest.raises(ValueError):
        PlayGraphIntentV1.model_validate_json(json.dumps(value))


def test_manifest_is_deterministic_sorted_exact_and_unicode_codepoint_bounded():
    moment, note = payload(), payload("scene_note")
    first = play_source_frame((moment, note))
    assert play_source_frame((note, moment)) == first
    assert PlaySourceFrameV1.model_validate_json(first.model_dump_json(by_alias=True)) == first
    assert len(canonical_bytes(first)) <= 65536
    entry = source_entry(note)
    assert entry.text_codepoints == len(NOTE)
    assert entry.text_utf8_bytes == len(NOTE.encode()) > entry.text_codepoints
    assert entry.payload_sha256 == canonical_sha256(note)
    assert entry.source_id == "play-source:" + entry.payload_sha256
    validate_play_source_owner_join(first, basis(), owner_resolved_current_moment_text=MOMENT)


def test_empty_frame_exposes_no_source_and_does_not_invent_missing_text():
    frame = play_source_frame(())
    assert frame.manifest.entries == () and frame.sources == ()
    validate_play_source_owner_join(frame, basis(), owner_resolved_current_moment_text=None)
    with pytest.raises(ValueError, match="independent source owner"):
        validate_play_source_owner_join(play_source_frame((payload(),)), basis(), owner_resolved_current_moment_text=None)


@pytest.mark.parametrize("change", ["world", "run", "revision", "edition", "beat", "scene", "note", "moment"])
def test_owner_join_requires_exact_independently_resolved_owner_and_body(change):
    updates = {}
    if change == "world": updates["world_id"] = "other"
    if change == "run": updates["run_id"] = "other"
    if change == "revision": updates["run_revision"] = 4
    if change == "edition": updates["edition"] = PlayContentBasis(edition_revision=1,
        edition_revision_id=UUID("00000000-0000-4000-8000-000000000002"), content_sha256="b" * 64)
    if change == "beat": updates["beat_id"] = "beat:other"
    if change == "scene": updates["scene_id"] = "scene:other"
    source = payload("scene_note" if change == "note" else "current_moment",
        text="Other body" if change in {"note", "moment"} else None, **updates)
    with pytest.raises(ValueError):
        validate_play_source_owner_join(play_source_frame((source,)), basis(), owner_resolved_current_moment_text=MOMENT)


@pytest.mark.parametrize("change", ["text", "payload_digest", "text_digest", "byte_count", "seal", "unknown", "order"])
def test_frame_rejects_self_inconsistent_wire_materials(change):
    frame = play_source_frame((payload(), payload("scene_note")))
    wire = frame.model_dump(mode="json", by_alias=True)
    if change == "text": wire["sources"][0]["text"] += "changed"
    if change == "payload_digest":
        wire["manifest"]["entries"][0]["payload_sha256"] = "0" * 64
        wire["manifest"]["entries"][0]["source_id"] = "play-source:" + "0" * 64
    if change == "text_digest": wire["manifest"]["entries"][0]["text_sha256"] = "0" * 64
    if change == "byte_count": wire["manifest"]["entries"][0]["text_utf8_bytes"] += 1
    if change == "seal": wire["manifest"]["manifest_sha256"] = "0" * 64
    if change == "unknown": wire["sources"][0]["source_uri"] = "file:/private"
    if change == "order": wire["sources"].reverse()
    if change != "seal":
        wire["manifest"]["manifest_sha256"] = canonical_sha256({key: value for key, value in wire["manifest"].items() if key != "manifest_sha256"})
    with pytest.raises(ValueError):
        PlaySourceFrameV1.model_validate_json(json.dumps(wire))


def test_duplicate_or_unsupplied_kind_cannot_become_more_source_authority():
    with pytest.raises(ValueError):
        play_source_frame((payload(), payload()))
    two_moments = play_source_frame((payload(), payload(text="Other")))
    with pytest.raises(ValueError):
        validate_play_source_owner_join(two_moments, basis(), owner_resolved_current_moment_text=MOMENT)
    wire = payload().model_dump(mode="json", by_alias=True)
    wire["source_kind"] = "closing_reflections"
    with pytest.raises(ValueError):
        PlaySourcePayloadV1.model_validate_json(json.dumps(wire))


@pytest.mark.parametrize("text", [" ", "🦉" * 8193, "\x01" * 10000])
def test_oversized_or_blank_sources_fail_without_truncation(text):
    with pytest.raises(ValueError):
        payload(text=text)


def test_combined_frame_utf8_budget_is_independent_of_individual_payload_budgets():
    text = "x" * 32000
    moment, note = payload(text=text), payload("scene_note", text=text)
    assert len(canonical_bytes(moment)) < 49152 and len(canonical_bytes(note)) < 49152
    with pytest.raises(ValueError, match="frame exceeds"):
        play_source_frame((moment, note))


# Pure ledger tests reuse the existing source accounting fixtures so that the
# new wire identity exercises the same source/provider invariants as Plan.
def native_execution(**policy_changes):
    from tests.test_settled_source_read_accounting import fixture_execution
    from application_state.agent_conversation.types import (
        NativePlayGraphPolicyV1,
        PlayWorldGraphExecutionV1,
    )
    from application_state.agent_conversation.play_graph_authority import (
        play_graph_execution_policy_digest,
    )
    original = fixture_execution()
    values = original.policy.model_dump(mode="json", by_alias=True)
    values.update(dict(policy_version="play_world_graph_execution_v1", max_provider_attempts=4,
        max_graph_operations=32, max_total_provider_input_tokens=4096,
        max_total_provider_output_tokens=1024) | policy_changes)
    policy = NativePlayGraphPolicyV1.model_validate_json(json.dumps(values))
    return PlayWorldGraphExecutionV1(context_receipt_sha256=original.context_receipt_sha256,
        execution_policy_sha256=play_graph_execution_policy_digest(original.context_receipt_sha256, policy),
        policy=policy, events=[])


def native_events(execution, events):
    return type(execution).model_validate_json(json.dumps(execution.model_dump(mode="json", by_alias=True)
        | {"events": [event.model_dump(mode="json", by_alias=True) for event in events]}))


def native_provider(sequence=0, **changes):
    from uuid import uuid4
    from application_state.agent_conversation.types import ProviderAttemptAuthorizedEventV3
    return ProviderAttemptAuthorizedEventV3(event_id=uuid4(), sequence=sequence,
        kind="provider_attempt_authorized_v3", provider_attempt_id=uuid4(),
        envelope_sha256="c" * 64, serializer_version="canonical-json-utf8-v1",
        provider="synthetic", model="synthetic", api_mode="synthetic", tool_schema_sha256="d" * 64,
        input_accounting_kind="exact_token_count", input_estimator="synthetic", input_tokens=12,
        output_token_reserve=10, included_assertion_ids=[], included_relationship_ids=[],
        included_evidence_ref_ids=[], included_graph_event_ids=[], included_source_read_event_ids=[],
        **changes)


def test_native_play_ledger_is_not_a_plan_subtype_and_uses_its_own_policy_digest():
    from application_state.agent_conversation.types import PlanWorldGraphExecutionV2, graph_execution_policy_digest_v3
    execution = native_execution()
    assert not isinstance(execution, PlanWorldGraphExecutionV2)
    encoded = execution.model_dump_json(by_alias=True)
    assert type(execution).model_validate_json(encoded).model_dump_json(by_alias=True) == encoded
    assert execution.execution_policy_sha256 != graph_execution_policy_digest_v3(execution.context_receipt_sha256, execution.policy)
    wire = execution.model_dump(mode="json", by_alias=True)
    wire["schema"] = "dmb_agent_plan_world_graph_execution_v3"
    with pytest.raises(ValueError):
        type(execution).model_validate_json(json.dumps(wire))


@pytest.mark.parametrize("field", ["max_provider_attempts", "max_graph_operations", "max_total_provider_input_tokens", "max_total_provider_output_tokens"])
def test_native_play_cannot_inherit_uncapped_policy(field):
    with pytest.raises(ValueError):
        native_execution(**{field: None})


def test_native_play_source_receipt_settles_but_cannot_overbook():
    from tests.test_settled_source_read_accounting import authorization, receipt
    execution = native_execution()
    first = authorization(execution)
    done = receipt(first)
    next_read = authorization(execution, 2, count=1)
    assert len(native_events(execution, [first, done, next_read]).events) == 3
    with pytest.raises(ValueError, match="character budget"):
        native_events(execution, [first, authorization(execution, 1, count=1)])


@pytest.mark.parametrize("change", ["sequence", "world", "revision", "session", "scope_hash", "policy_hash", "pin", "characters", "duplicate_call", "missing_authorization", "receipt_pin", "duplicate_receipt"])
def test_native_play_enforces_shared_source_ledger_invariants(change):
    from uuid import uuid4
    from tests.test_settled_source_read_accounting import authorization, receipt
    execution = native_execution()
    auth = authorization(execution, count=1)
    done = receipt(auth)
    fields = {"sequence": ("sequence", 1), "world": ("world_id", "other"),
        "revision": ("graph_revision", "other"), "session": ("retrieval_session_id", "other"),
        "scope_hash": ("context_receipt_sha256", "f" * 64), "policy_hash": ("execution_policy_sha256", "f" * 64),
        "characters": ("max_chars", 12001)}
    events = [auth, done]
    if change in fields:
        field, value = fields[change]
        events[0] = auth.model_copy(update={field: value})
    if change == "pin":
        events[0] = auth.model_copy(update={"anchors": [auth.anchors[0].model_copy(update={"source_revision_id": "forged"})]})
    if change == "duplicate_call":
        events = [auth, auth.model_copy(update={"sequence": 1, "event_id": uuid4()})]
    if change == "missing_authorization": events = [done.model_copy(update={"sequence": 0})]
    if change == "receipt_pin":
        events[1] = done.model_copy(update={"receipts": [done.receipts[0].model_copy(update={"source_revision_id": "other"})]})
    if change == "duplicate_receipt":
        events.append(done.model_copy(update={"sequence": 2, "event_id": uuid4()}))
    with pytest.raises(ValueError):
        native_events(execution, events)


def test_native_play_provider_observation_and_completion_state_machine_remains_required():
    from uuid import uuid4
    from application_state.agent_conversation.types import ProviderOutcomeEventV1, CompletionBindingEventV1
    from tests.test_settled_source_read_accounting import authorization
    execution = native_execution()
    auth = native_provider()
    def outcome(sequence, value):
        return ProviderOutcomeEventV1(event_id=uuid4(), sequence=sequence, kind="provider_outcome",
            provider_attempt_id=auth.provider_attempt_id, outcome=value)
    complete = CompletionBindingEventV1(event_id=uuid4(), sequence=3, kind="completion_binding",
        provider_attempt_id=auth.provider_attempt_id, completion_sha256="e" * 64, claim_graph_event_ids={})
    assert len(native_events(execution, [auth, outcome(1,"sdk_entered"), outcome(2,"response_received"), complete]).events) == 4
    with pytest.raises(ValueError): native_events(execution, [auth, outcome(1,"response_received")])
    with pytest.raises(ValueError): native_events(execution, [auth, complete.model_copy(update={"sequence": 1})])
    with pytest.raises(ValueError): native_events(execution, [auth, outcome(1,"outcome_unknown"), authorization(execution, 2, count=1)])
    with pytest.raises(ValueError): native_events(execution, [auth, native_provider(1)])


def test_native_play_budget_and_build_event_capabilities_are_closed():
    from uuid import uuid4
    execution = native_execution(max_total_provider_input_tokens=1)
    with pytest.raises(ValueError, match="token budget"):
        native_events(execution, [native_provider()])
    wire = native_execution().model_dump(mode="json", by_alias=True)
    wire["events"] = [dict(kind="build_jev_action_selection_v1", event_id=str(uuid4()), sequence=0)]
    with pytest.raises(ValueError): type(execution).model_validate_json(json.dumps(wire))
    wire["events"] = []
    wire["policy"]["provider_roles"] = {"controller": {}, "writer": {}}
    with pytest.raises(ValueError): type(execution).model_validate_json(json.dumps(wire))


@pytest.mark.parametrize("change", [None, "origin", "pins", "world", "revision", "session", "policy_hash", "rebind"])
def test_native_play_dynamic_extensions_require_their_exact_prior_graph_origin(change):
    from uuid import uuid4
    from application_state.agent_conversation.types import (
        GraphSourceScopeAnchorV2, ValidatedGraphOperationEventV3, SourceScopeExtensionEventV3)
    execution = native_execution()
    scope = execution.policy.source_read_scope
    pin = GraphSourceScopeAnchorV2(anchor_id="new-anchor", evidence_ref_id="new-evidence",
        source_artifact_id="artifact-two", source_revision_id="source-two")
    if change == "rebind": pin = scope.admitted_anchors[0].model_copy(update={"source_revision_id": "forged"})
    origin = ValidatedGraphOperationEventV3(event_id=uuid4(), sequence=0,
        kind="validated_graph_operation_v3", operation_id=uuid4(), operation="expand_graph_retrieval",
        request_arguments_sha256="a" * 64, graph_revision=scope.graph_revision,
        result_packet_sha256="b" * 64, assertion_ids=[], relationship_ids=[],
        evidence_ref_ids=[pin.evidence_ref_id], evidence_sufficiency_status="sufficient",
        coverage_status="complete", truncated=False, source_opened=False, returned_source_pins=[pin])
    extension = SourceScopeExtensionEventV3(event_id=uuid4(), sequence=1,
        kind="source_scope_extension_v3", origin_graph_event_id=origin.event_id,
        context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256, world_id=scope.world_id,
        native_world_id="native-world", binding_version=1, campaign_id=None,
        graph_revision=scope.graph_revision, retrieval_session_id=scope.retrieval_session_id, pins=[pin])
    fields = {"origin": ("origin_graph_event_id", uuid4()), "world": ("world_id", "other"),
        "revision": ("graph_revision", "other"), "session": ("retrieval_session_id", "other"),
        "policy_hash": ("execution_policy_sha256", "f" * 64),
        "pins": ("pins", [pin.model_copy(update={"source_revision_id": "forged"})])}
    if change in fields:
        field, value = fields[change]
        extension = extension.model_copy(update={field: value})
    if change is None:
        assert len(native_events(execution, [origin, extension]).events) == 2
    else:
        with pytest.raises(ValueError): native_events(execution, [origin, extension])


@pytest.mark.parametrize("change", ["campaign", "count", "accounting"])
def test_native_play_policy_cannot_change_scope_or_budget_mode(change):
    from application_state.agent_conversation.types import (
        NativePlayGraphPolicyV1,
    )
    wire = native_execution().policy.model_dump(mode="json", by_alias=True)
    if change == "campaign": wire["source_read_scope"]["campaign_id"] = "foreign-campaign"
    if change == "count": wire["max_provider_attempts"] = 65
    if change == "accounting": wire["source_read_accounting"] = "reservation_only"
    with pytest.raises(ValueError): NativePlayGraphPolicyV1.model_validate_json(json.dumps(wire))
