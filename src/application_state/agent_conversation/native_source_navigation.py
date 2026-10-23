"""Durable metadata navigation joins; no Core calls, bodies or citation grants."""
from __future__ import annotations

import re
from . import types as t
from .source_writer_output import strict_json


def origin_payload(event):
    try:
        return _origin_payload(event)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Native origin proof has malformed structured metadata") from exc


def _origin_payload(event):
    body = strict_json(event.origin_proof_json)
    if (not isinstance(body, dict) or set(body) != {
            "schema", "projection", "donor", "donor_sha256", "pin", "resolution", "revision"}
            or body["schema"] != "dmb_native_source_origin_proof_v1"
            or t._canonical_sha256(body) != event.origin_proof_sha256):
        raise ValueError("Native origin proof is not the exact structured producer proof")
    donor = t.ValidatedGraphOperationEventV3.model_validate(body["donor"])
    pin = t.GraphSourceScopeAnchorV2.model_validate(body["pin"])
    projection, resolution, revision = body["projection"], body["resolution"], body["revision"]
    artifact, evidence, snapshot = resolution["artifact"], resolution["evidence"], resolution["snapshot"]
    native_anchor = ("dm-source-anchor:v1:" + pin.anchor_id[len("source-anchor:v1:"):]
                     if pin.anchor_id.startswith("source-anchor:v1:") else pin.anchor_id)
    expected_scope = {"world_id": event.native_world_id, "campaign_id": None,
                      "admissibility": "gm", "scope_mode": "world_cross_campaign",
                      "focus": {"kind": "none", "session_id": None}}
    if (t._canonical_sha256(body["donor"]) != body["donor_sha256"]
            or pin not in donor.returned_source_pins
            or pin.evidence_ref_id not in donor.evidence_ref_ids
            or any(projection.get(k) != v or snapshot.get(k) != v for k, v in expected_scope.items())
            or projection.get("revision_pin") != donor.graph_revision
            or snapshot.get("revision_id") != donor.graph_revision
            or resolution.get("anchor_id") != native_anchor
            or resolution.get("can_open_source") is not True
            or resolution.get("evidence_ref_id") != pin.evidence_ref_id
            or evidence.get("evidence_ref_id") != pin.evidence_ref_id
            or artifact.get("status") != "active" or artifact.get("visibility") not in {"gm", "player"}
            or artifact.get("world_id") != event.native_world_id
            or artifact.get("source_domain") not in {"worldbuilding", "session_recap"}
            or evidence.get("source_domain") != artifact.get("source_domain")
            or not isinstance(revision.get("content_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", revision["content_sha256"])):
        raise ValueError("Native origin metadata differs from frozen source authority")
    for key, expected in (("source_artifact_id", pin.source_artifact_id),
                          ("source_revision_id", pin.source_revision_id)):
        if any(row.get(key) != expected for row in (resolution, evidence, revision)):
            raise ValueError("Native origin source identity differs across proof records")
    if artifact.get("source_artifact_id") != pin.source_artifact_id:
        raise ValueError("Native origin artifact identity differs")
    return body, donor, pin


def validate_navigation_events(execution):
    events = execution.events
    navs = [e for e in events if isinstance(e, t.NativeSourceNavigationAuthorizedV1)]
    if not navs:
        return
    if not isinstance(execution.policy, (t.PlanNativeSourceSectionsPolicyV1, t.PlayNativeSourceSectionsPolicyV1)):
        raise ValueError("Native source navigation requires its explicit frozen capability")
    scope = execution.policy.source_read_scope
    origins, pins, navigation_ids, source_keys = {}, {}, set(), set()
    pins.update((p.anchor_id, p) for p in scope.admitted_anchors)
    latest_provider, latest_outcome, writer_started = None, None, False
    for event in events:
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            latest_provider, latest_outcome = event.provider_attempt_id, None
            if (isinstance(event, t.PlanJevWriterAuthorizedV1)
                    or isinstance(execution.policy, t.PlanJevRetrievalPolicyV1)
                    and (event.provider, event.model, event.api_mode) == execution.policy.provider_roles.writer.identity()):
                writer_started = True
        elif isinstance(event, t.ProviderOutcomeEventV1) and event.provider_attempt_id == latest_provider:
            latest_outcome = event.outcome
        elif isinstance(event, t.ValidatedGraphOperationEventV3):
            origins[event.event_id] = event
        elif isinstance(event, t.SourceScopeExtensionEventV3):
            pins.update((p.anchor_id, p) for p in event.pins)
        elif isinstance(event, t.NativeSourceNavigationAuthorizedV1):
            body, donor, pin = origin_payload(event)
            # An immutable native revision cannot be re-admitted under a different
            # digest; exact repeats reuse the original authorization as well.
            source_key = (pin.source_artifact_id, pin.source_revision_id)
            if (writer_started or latest_provider != event.provider_attempt_id or latest_outcome != "response_received"
                    or origins.get(donor.event_id) != donor or pins.get(pin.anchor_id) != pin
                    or event.navigation_id in navigation_ids or source_key in source_keys
                    or event.context_receipt_sha256 != execution.context_receipt_sha256
                    or event.execution_policy_sha256 != execution.execution_policy_sha256
                    or event.world_id != scope.world_id or donor.graph_revision != scope.graph_revision):
                raise ValueError("Native navigation lacks an exact earlier acknowledged donor/scope")
            navigation_ids.add(event.navigation_id)
            source_keys.add(source_key)


def validate_navigation_receipt(receipt, execution):
    if execution is None:
        return
    navs = [e for e in execution.events if isinstance(e, t.NativeSourceNavigationAuthorizedV1)]
    if not navs:
        return
    if not isinstance(receipt, (t.PlanWorldGraphContextReceiptV1, t.PlayWorldGraphContextReceiptV1)):
        raise ValueError("Native source navigation requires a frozen Plan or native Play receipt")
    authority = receipt.graph_authority
    for event in navs:
        body, donor, _ = origin_payload(event)
        if (event.world_id != authority.managed_world_id
                or event.native_world_id != authority.native_world_id
                or event.binding_version != authority.binding_version
                or donor.graph_revision != authority.graph_revision
                or event.context_receipt_sha256 != receipt.context_receipt_sha256):
            raise ValueError("Native source navigation differs from managed/native World receipt")
