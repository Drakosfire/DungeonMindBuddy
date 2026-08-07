"""Non-authoritative DungeonMind Threat hydration shadow.

Runs after the authoritative Buddy Threat query/hydration response is already
determined. Replays exact successful provider observations through the #518
bridge + pinned DungeonMind v3 hydrate path. Never calls the provider, never
writes, never alters HTTP output.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from dungeonmind.application.graph_snapshot import UnionGraphV3SnapshotReader
from dungeonmind.contracts.projection import Admissibility
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind_dnd.application.world_object_mechanics import (
    hydrate_world_object_mechanics,
)
from dungeonmind_dnd.contracts.mechanics_resources import (
    STATBLOCKS_MEDIA_TYPE,
    STATBLOCKS_PROVIDER_ID,
    STATBLOCKS_RESOURCE_SCHEMA,
    DndMechanicsResourceEnvelope,
    DndMechanicsResourceRef,
)
from dungeonmind_dnd.domain.errors import DndWorldObjectMechanicsHydrationError

from apps.live_control_server.integrations.dungeonmind_kernel.world_object_conformance_bridge import (
    BridgedStatblockAttachment,
    DungeonMindThreatConformanceBridgeResult,
    ThreatConformanceBridgeError,
    _bridge_buddy_threat_revision,
    _ExactBuddyRevisionBridgeSource,
    _load_exact_buddy_revision_bridge_source,
    _v3_graph_reader,
    convert_buddy_definition_digest,
    map_buddy_threat_object_id,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    ExactRevisionResourceV1,
)
from apps.live_control_server.models.threat_query_hydration import (
    ThreatBindingHydrationV1,
    ThreatQueryHydrationHitV1,
    ThreatQueryHydrationRequestV1,
    ThreatQueryHydrationResponseV1,
)

logger = logging.getLogger(__name__)

_SHADOW_EVENT = "dungeonmind_threat_hydration_shadow"
_OBSERVATION_SCHEMA = "dmb_dungeonmind_threat_hydration_shadow_v1"
_EXPLICIT_THREAT_KIND = "threat"

ShadowVerdict = Literal[
    "full_match",
    "structural_match",
    "inconclusive",
    "mismatch",
    "not_eligible",
    "shadow_error",
]

ShadowReasonCode = Literal[
    "source_object_kind_not_shadow_eligible",
    "bridge_source_integrity_failure",
    "bridge_object_missing",
    "bridge_failure",
    "binding_cardinality_mismatch",
    "source_binding_missing_from_bridge",
    "unexpected_bridge_attachment",
    "role_mismatch",
    "phase_key_mismatch",
    "variant_label_mismatch",
    "resource_provider_mismatch",
    "resource_id_mismatch",
    "resource_revision_mismatch",
    "resource_schema_mismatch",
    "resource_digest_mismatch",
    "authority_mechanics_not_requested",
    "authority_no_binding",
    "authority_unavailable",
    "authority_exact_revision_missing",
    "authority_integrity_failure",
    "authority_partial",
    "canonical_definition_invalid_json",
    "canonical_definition_not_object",
    "canonical_definition_digest_mismatch",
    "dungeonmind_hydration_failure",
    "dungeonmind_resource_request_mismatch",
    "dungeonmind_resolver_call_count_mismatch",
    "dungeonmind_payload_mismatch",
    "unexpected_shadow_exception",
]


@dataclass
class AuthorityExactRevisionReplayResolver:
    """In-memory DungeonMind resolver that replays one authority observation."""

    expected_ref: DndMechanicsResourceRef
    revision: ExactRevisionResourceV1
    call_count: int = 0
    requested_refs: list[DndMechanicsResourceRef] = field(default_factory=list)

    def resolve(self, resource_ref: DndMechanicsResourceRef) -> DndMechanicsResourceEnvelope:
        self.call_count += 1
        self.requested_refs.append(resource_ref)
        payload = _decode_canonical_definition(self.revision)
        return DndMechanicsResourceEnvelope(
            resource_ref=self.expected_ref,
            mechanics_payload=payload,
        )


@dataclass(frozen=True)
class ShadowBindingResult:
    source_binding_id: str | None
    target_binding_id: str | None
    target_attachment_id: str | None
    authority_hydration_status: str | None
    structural_status: str
    shadow_hydration_status: str | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class DungeonMindThreatHydrationShadowObservation:
    schema: str
    world_id: str
    campaign_id: str
    revision_id: str
    threat_node_id: str
    source_kind: str | None
    verdict: ShadowVerdict
    reason_codes: tuple[str, ...]
    authority_mechanics_disposition: str | None
    authority_binding_count: int
    authority_available_binding_count: int
    bridge_attachment_count: int
    bridge_generic_binding_count: int
    shadow_hydrated_binding_count: int
    binding_results: tuple[ShadowBindingResult, ...]
    elapsed_ms: int
    dungeonmind_hydration_reason: str | None = None


def _decode_canonical_definition(revision: ExactRevisionResourceV1) -> dict[str, Any]:
    try:
        payload = json.loads(revision.canonical_definition)
    except (TypeError, ValueError) as exc:
        raise ThreatConformanceBridgeError(
            "malformed_definition_digest",
            "canonical_definition is not valid JSON",
        ) from exc
    if not isinstance(payload, dict):
        raise ThreatConformanceBridgeError(
            "malformed_definition_digest",
            "canonical_definition JSON value is not an object",
        )
    return payload


def _authority_status_reason(status: str) -> str | None:
    mapping = {
        "unavailable": "authority_unavailable",
        "exact_revision_missing": "authority_exact_revision_missing",
        "integrity_failure": "authority_integrity_failure",
        "not_requested": "authority_mechanics_not_requested",
    }
    return mapping.get(status)


def _compare_resource_identity(
    authority: ThreatBindingHydrationV1,
    attachment: BridgedStatblockAttachment,
) -> list[str]:
    reasons: list[str] = []
    ref = attachment.attachment.binding.resource_ref
    if authority.provider != "dungeonmind" or ref.provider_id != STATBLOCKS_PROVIDER_ID:
        reasons.append("resource_provider_mismatch")
    if authority.statblock_id != ref.resource_id:
        reasons.append("resource_id_mismatch")
    if authority.revision_id != ref.resource_revision:
        reasons.append("resource_revision_mismatch")
    expected_schema = STATBLOCKS_RESOURCE_SCHEMA
    if authority.binding is not None:
        expected_schema = (
            f"{authority.binding.contract}.{authority.binding.contract_version}"
        )
    if ref.resource_schema != expected_schema:
        reasons.append("resource_schema_mismatch")
    if authority.definition_digest:
        try:
            expected_digest = convert_buddy_definition_digest(authority.definition_digest)
        except ThreatConformanceBridgeError:
            reasons.append("resource_digest_mismatch")
        else:
            if ref.payload_sha256 != expected_digest:
                reasons.append("resource_digest_mismatch")
    elif ref.payload_sha256:
        reasons.append("resource_digest_mismatch")
    if ref.media_type != STATBLOCKS_MEDIA_TYPE:
        reasons.append("resource_schema_mismatch")
    if ref.ruleset_id != "dnd5e":
        reasons.append("resource_schema_mismatch")
    return reasons


def _compare_role_metadata(
    authority: ThreatBindingHydrationV1,
    attachment: BridgedStatblockAttachment,
) -> list[str]:
    reasons: list[str] = []
    source = authority.binding
    target = attachment.attachment
    if source is None:
        return reasons
    if source.role != target.role:
        reasons.append("role_mismatch")
    if source.phase_key != target.phase_key:
        reasons.append("phase_key_mismatch")
    if source.variant_label != target.variant_label:
        reasons.append("variant_label_mismatch")
    return reasons


def _hydrate_available_binding(
    *,
    authority: ThreatBindingHydrationV1,
    attachment: BridgedStatblockAttachment,
    bridge_result: DungeonMindThreatConformanceBridgeResult,
    graph_reader: UnionGraphV3SnapshotReader,
) -> tuple[str, list[str], str | None]:
    """Return (shadow_hydration_status, reason_codes, dungeonmind_reason)."""
    assert authority.revision is not None
    expected_ref = attachment.attachment.binding.resource_ref
    revision = authority.revision

    try:
        payload = _decode_canonical_definition(revision)
    except ThreatConformanceBridgeError:
        raw = revision.canonical_definition
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return "failed", ["canonical_definition_invalid_json"], None
        if not isinstance(parsed, dict):
            return "failed", ["canonical_definition_not_object"], None
        return "failed", ["canonical_definition_invalid_json"], None

    try:
        expected_digest = convert_buddy_definition_digest(revision.definition_digest)
    except ThreatConformanceBridgeError:
        return "failed", ["resource_digest_mismatch"], None

    if canonical_sha256(payload) != expected_digest:
        return "failed", ["canonical_definition_digest_mismatch"], None

    resolver = AuthorityExactRevisionReplayResolver(
        expected_ref=expected_ref,
        revision=revision,
    )
    try:
        hydration = hydrate_world_object_mechanics(
            attachment.attachment.binding,
            admissibility=Admissibility.GM,
            graph_revision=bridge_result.target_revision,
            graph_reader=graph_reader,
            resource_resolver=resolver,
        )
    except DndWorldObjectMechanicsHydrationError as exc:
        dm_reason = None
        if isinstance(exc.details, dict):
            raw_reason = exc.details.get("reason")
            if isinstance(raw_reason, str) and raw_reason:
                dm_reason = raw_reason
        return "failed", ["dungeonmind_hydration_failure"], dm_reason
    except Exception:  # noqa: BLE001
        return "failed", ["dungeonmind_hydration_failure"], None

    reasons: list[str] = []
    if resolver.call_count != 1:
        reasons.append("dungeonmind_resolver_call_count_mismatch")
    if not resolver.requested_refs or resolver.requested_refs[0] != expected_ref:
        reasons.append("dungeonmind_resource_request_mismatch")
    if hydration.mechanics_payload != payload:
        reasons.append("dungeonmind_payload_mismatch")
    if hydration.binding.binding_id != attachment.target_binding_id:
        reasons.append("dungeonmind_hydration_failure")
    if reasons:
        return "failed", reasons, None
    return "hydrated", [], None


def _shadow_eligible_threat(
    *,
    hit: ThreatQueryHydrationHitV1,
    request: ThreatQueryHydrationRequestV1,
    response: ThreatQueryHydrationResponseV1,
    source: _ExactBuddyRevisionBridgeSource,
    started: float,
) -> DungeonMindThreatHydrationShadowObservation:
    threat_node_id = hit.threat.node_id
    reason_codes: list[str] = []
    binding_results: list[ShadowBindingResult] = []
    dm_reason: str | None = None
    bridge_attachment_count = 0
    bridge_generic_binding_count = 0
    shadow_hydrated = 0

    authority_bindings = list(hit.bindings)
    available = [
        b
        for b in authority_bindings
        if b.hydration_status == "available" and b.revision is not None
    ]
    typed_authority = [b for b in authority_bindings if b.binding_id]

    try:
        bridge_result = _bridge_buddy_threat_revision(
            source_world_id=response.world_id,
            source_revision=source.manifest,
            source_store=source.store,
            threat_node_id=threat_node_id,
            campaign_id=response.campaign_id,
        )
    except ThreatConformanceBridgeError as exc:
        mapped = {
            "source_threat_missing": "bridge_object_missing",
            "source_revision_integrity_failure": "bridge_source_integrity_failure",
            "exact_revision_missing": "bridge_source_integrity_failure",
        }.get(exc.reason, "bridge_failure")
        reason_codes.append(mapped)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        # Authority returned this hit; bridge cannot — comparable disagreement.
        verdict: ShadowVerdict = "mismatch"
        if any(
            b.hydration_status
            in {"unavailable", "exact_revision_missing", "integrity_failure"}
            for b in authority_bindings
        ) and not available:
            # No successful authority observation; do not claim parity either way.
            verdict = "inconclusive"
            for b in authority_bindings:
                status_reason = _authority_status_reason(b.hydration_status)
                if status_reason and status_reason not in reason_codes:
                    reason_codes.append(status_reason)
        return DungeonMindThreatHydrationShadowObservation(
            schema=_OBSERVATION_SCHEMA,
            world_id=response.world_id,
            campaign_id=response.campaign_id,
            revision_id=response.revision_id,
            threat_node_id=threat_node_id,
            source_kind=hit.threat.kind,
            verdict=verdict,
            reason_codes=tuple(reason_codes),
            authority_mechanics_disposition=hit.mechanics_disposition,
            authority_binding_count=len(authority_bindings),
            authority_available_binding_count=len(available),
            bridge_attachment_count=0,
            bridge_generic_binding_count=0,
            shadow_hydrated_binding_count=0,
            binding_results=tuple(binding_results),
            elapsed_ms=elapsed_ms,
        )

    bridge_attachment_count = len(bridge_result.attachments)
    bridge_generic_binding_count = len(
        {item.target_binding_id for item in bridge_result.attachments}
    )
    attachments_by_source = {
        item.source_binding_id: item for item in bridge_result.attachments
    }

    structural_ok = True
    if len(typed_authority) != bridge_attachment_count:
        structural_ok = False
        reason_codes.append("binding_cardinality_mismatch")

    for authority in typed_authority:
        assert authority.binding_id is not None
        attachment = attachments_by_source.get(authority.binding_id)
        if attachment is None:
            structural_ok = False
            reason_codes.append("source_binding_missing_from_bridge")
            binding_results.append(
                ShadowBindingResult(
                    source_binding_id=authority.binding_id,
                    target_binding_id=None,
                    target_attachment_id=None,
                    authority_hydration_status=authority.hydration_status,
                    structural_status="missing",
                    shadow_hydration_status=None,
                    reason_codes=("source_binding_missing_from_bridge",),
                )
            )
            continue

        local_reasons = _compare_role_metadata(authority, attachment)
        local_reasons.extend(_compare_resource_identity(authority, attachment))
        if local_reasons:
            structural_ok = False
            reason_codes.extend(
                code for code in local_reasons if code not in reason_codes
            )
            binding_results.append(
                ShadowBindingResult(
                    source_binding_id=authority.binding_id,
                    target_binding_id=attachment.target_binding_id,
                    target_attachment_id=attachment.target_attachment_id,
                    authority_hydration_status=authority.hydration_status,
                    structural_status="mismatch",
                    shadow_hydration_status=None,
                    reason_codes=tuple(local_reasons),
                )
            )
        else:
            binding_results.append(
                ShadowBindingResult(
                    source_binding_id=authority.binding_id,
                    target_binding_id=attachment.target_binding_id,
                    target_attachment_id=attachment.target_attachment_id,
                    authority_hydration_status=authority.hydration_status,
                    structural_status="match",
                    shadow_hydration_status=None,
                    reason_codes=(),
                )
            )

    for attachment in bridge_result.attachments:
        if not any(b.binding_id == attachment.source_binding_id for b in typed_authority):
            structural_ok = False
            if "unexpected_bridge_attachment" not in reason_codes:
                reason_codes.append("unexpected_bridge_attachment")
            binding_results.append(
                ShadowBindingResult(
                    source_binding_id=attachment.source_binding_id,
                    target_binding_id=attachment.target_binding_id,
                    target_attachment_id=attachment.target_attachment_id,
                    authority_hydration_status=None,
                    structural_status="unexpected",
                    shadow_hydration_status=None,
                    reason_codes=("unexpected_bridge_attachment",),
                )
            )

    # Expected object identity check (informational; mismatch if diverges).
    try:
        expected_object_id = map_buddy_threat_object_id(threat_node_id)
    except ThreatConformanceBridgeError:
        structural_ok = False
        reason_codes.append("bridge_failure")
    else:
        if bridge_result.target_object_id != expected_object_id:
            structural_ok = False
            reason_codes.append("bridge_failure")
        if bridge_result.target_object_kind != "dnd5e:threat":
            structural_ok = False
            reason_codes.append("bridge_failure")
        if bridge_result.source_revision_id != response.revision_id:
            structural_ok = False
            reason_codes.append("bridge_failure")

    if not structural_ok:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return DungeonMindThreatHydrationShadowObservation(
            schema=_OBSERVATION_SCHEMA,
            world_id=response.world_id,
            campaign_id=response.campaign_id,
            revision_id=response.revision_id,
            threat_node_id=threat_node_id,
            source_kind=hit.threat.kind,
            verdict="mismatch",
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            authority_mechanics_disposition=hit.mechanics_disposition,
            authority_binding_count=len(authority_bindings),
            authority_available_binding_count=len(available),
            bridge_attachment_count=bridge_attachment_count,
            bridge_generic_binding_count=bridge_generic_binding_count,
            shadow_hydrated_binding_count=0,
            binding_results=tuple(binding_results),
            elapsed_ms=elapsed_ms,
        )

    if not request.include_mechanics:
        reason_codes.append("authority_mechanics_not_requested")
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return DungeonMindThreatHydrationShadowObservation(
            schema=_OBSERVATION_SCHEMA,
            world_id=response.world_id,
            campaign_id=response.campaign_id,
            revision_id=response.revision_id,
            threat_node_id=threat_node_id,
            source_kind=hit.threat.kind,
            verdict="structural_match",
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            authority_mechanics_disposition=hit.mechanics_disposition,
            authority_binding_count=len(authority_bindings),
            authority_available_binding_count=len(available),
            bridge_attachment_count=bridge_attachment_count,
            bridge_generic_binding_count=bridge_generic_binding_count,
            shadow_hydrated_binding_count=0,
            binding_results=tuple(binding_results),
            elapsed_ms=elapsed_ms,
        )

    if not authority_bindings:
        reason_codes.append("authority_no_binding")
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return DungeonMindThreatHydrationShadowObservation(
            schema=_OBSERVATION_SCHEMA,
            world_id=response.world_id,
            campaign_id=response.campaign_id,
            revision_id=response.revision_id,
            threat_node_id=threat_node_id,
            source_kind=hit.threat.kind,
            verdict="structural_match",
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            authority_mechanics_disposition=hit.mechanics_disposition,
            authority_binding_count=0,
            authority_available_binding_count=0,
            bridge_attachment_count=bridge_attachment_count,
            bridge_generic_binding_count=bridge_generic_binding_count,
            shadow_hydrated_binding_count=0,
            binding_results=tuple(binding_results),
            elapsed_ms=elapsed_ms,
        )

    if not available:
        for b in authority_bindings:
            status_reason = _authority_status_reason(b.hydration_status)
            if status_reason and status_reason not in reason_codes:
                reason_codes.append(status_reason)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return DungeonMindThreatHydrationShadowObservation(
            schema=_OBSERVATION_SCHEMA,
            world_id=response.world_id,
            campaign_id=response.campaign_id,
            revision_id=response.revision_id,
            threat_node_id=threat_node_id,
            source_kind=hit.threat.kind,
            verdict="inconclusive",
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            authority_mechanics_disposition=hit.mechanics_disposition,
            authority_binding_count=len(authority_bindings),
            authority_available_binding_count=0,
            bridge_attachment_count=bridge_attachment_count,
            bridge_generic_binding_count=bridge_generic_binding_count,
            shadow_hydrated_binding_count=0,
            binding_results=tuple(binding_results),
            elapsed_ms=elapsed_ms,
        )

    graph_reader = _v3_graph_reader()
    hydration_failed = False
    updated_binding_results: list[ShadowBindingResult] = []
    matched_available_ids = {b.binding_id for b in available}

    for prior in binding_results:
        if prior.source_binding_id not in matched_available_ids:
            updated_binding_results.append(prior)
            continue
        authority = next(
            b for b in available if b.binding_id == prior.source_binding_id
        )
        attachment = attachments_by_source[prior.source_binding_id]  # type: ignore[index]
        status, hydrate_reasons, local_dm_reason = _hydrate_available_binding(
            authority=authority,
            attachment=attachment,
            bridge_result=bridge_result,
            graph_reader=graph_reader,
        )
        if local_dm_reason and dm_reason is None:
            dm_reason = local_dm_reason
        if status == "hydrated":
            shadow_hydrated += 1
            updated_binding_results.append(
                ShadowBindingResult(
                    source_binding_id=prior.source_binding_id,
                    target_binding_id=prior.target_binding_id,
                    target_attachment_id=prior.target_attachment_id,
                    authority_hydration_status=prior.authority_hydration_status,
                    structural_status=prior.structural_status,
                    shadow_hydration_status="hydrated",
                    reason_codes=(),
                )
            )
        else:
            hydration_failed = True
            for code in hydrate_reasons:
                if code not in reason_codes:
                    reason_codes.append(code)
            updated_binding_results.append(
                ShadowBindingResult(
                    source_binding_id=prior.source_binding_id,
                    target_binding_id=prior.target_binding_id,
                    target_attachment_id=prior.target_attachment_id,
                    authority_hydration_status=prior.authority_hydration_status,
                    structural_status=prior.structural_status,
                    shadow_hydration_status="failed",
                    reason_codes=tuple(hydrate_reasons),
                )
            )

    binding_results = updated_binding_results
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    if hydration_failed:
        return DungeonMindThreatHydrationShadowObservation(
            schema=_OBSERVATION_SCHEMA,
            world_id=response.world_id,
            campaign_id=response.campaign_id,
            revision_id=response.revision_id,
            threat_node_id=threat_node_id,
            source_kind=hit.threat.kind,
            verdict="mismatch",
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            authority_mechanics_disposition=hit.mechanics_disposition,
            authority_binding_count=len(authority_bindings),
            authority_available_binding_count=len(available),
            bridge_attachment_count=bridge_attachment_count,
            bridge_generic_binding_count=bridge_generic_binding_count,
            shadow_hydrated_binding_count=shadow_hydrated,
            binding_results=tuple(binding_results),
            elapsed_ms=elapsed_ms,
            dungeonmind_hydration_reason=dm_reason,
        )

    if len(available) != len(authority_bindings):
        reason_codes.append("authority_partial")
        for b in authority_bindings:
            if b.hydration_status != "available":
                status_reason = _authority_status_reason(b.hydration_status)
                if status_reason and status_reason not in reason_codes:
                    reason_codes.append(status_reason)
        return DungeonMindThreatHydrationShadowObservation(
            schema=_OBSERVATION_SCHEMA,
            world_id=response.world_id,
            campaign_id=response.campaign_id,
            revision_id=response.revision_id,
            threat_node_id=threat_node_id,
            source_kind=hit.threat.kind,
            verdict="inconclusive",
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            authority_mechanics_disposition=hit.mechanics_disposition,
            authority_binding_count=len(authority_bindings),
            authority_available_binding_count=len(available),
            bridge_attachment_count=bridge_attachment_count,
            bridge_generic_binding_count=bridge_generic_binding_count,
            shadow_hydrated_binding_count=shadow_hydrated,
            binding_results=tuple(binding_results),
            elapsed_ms=elapsed_ms,
            dungeonmind_hydration_reason=dm_reason,
        )

    return DungeonMindThreatHydrationShadowObservation(
        schema=_OBSERVATION_SCHEMA,
        world_id=response.world_id,
        campaign_id=response.campaign_id,
        revision_id=response.revision_id,
        threat_node_id=threat_node_id,
        source_kind=hit.threat.kind,
        verdict="full_match",
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        authority_mechanics_disposition=hit.mechanics_disposition,
        authority_binding_count=len(authority_bindings),
        authority_available_binding_count=len(available),
        bridge_attachment_count=bridge_attachment_count,
        bridge_generic_binding_count=bridge_generic_binding_count,
        shadow_hydrated_binding_count=shadow_hydrated,
        binding_results=tuple(binding_results),
        elapsed_ms=elapsed_ms,
        dungeonmind_hydration_reason=dm_reason,
    )


def _observation_for_not_eligible(
    *,
    hit: ThreatQueryHydrationHitV1,
    response: ThreatQueryHydrationResponseV1,
    started: float,
) -> DungeonMindThreatHydrationShadowObservation:
    return DungeonMindThreatHydrationShadowObservation(
        schema=_OBSERVATION_SCHEMA,
        world_id=response.world_id,
        campaign_id=response.campaign_id,
        revision_id=response.revision_id,
        threat_node_id=hit.threat.node_id,
        source_kind=hit.threat.kind,
        verdict="not_eligible",
        reason_codes=("source_object_kind_not_shadow_eligible",),
        authority_mechanics_disposition=hit.mechanics_disposition,
        authority_binding_count=len(hit.bindings),
        authority_available_binding_count=sum(
            1 for b in hit.bindings if b.hydration_status == "available"
        ),
        bridge_attachment_count=0,
        bridge_generic_binding_count=0,
        shadow_hydrated_binding_count=0,
        binding_results=(),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )


def _observation_shadow_error(
    *,
    threat_node_id: str,
    source_kind: str | None,
    response: ThreatQueryHydrationResponseV1,
    hit: ThreatQueryHydrationHitV1 | None,
    reason: str,
    started: float,
) -> DungeonMindThreatHydrationShadowObservation:
    return DungeonMindThreatHydrationShadowObservation(
        schema=_OBSERVATION_SCHEMA,
        world_id=response.world_id,
        campaign_id=response.campaign_id,
        revision_id=response.revision_id,
        threat_node_id=threat_node_id,
        source_kind=source_kind,
        verdict="shadow_error",
        reason_codes=(reason,),
        authority_mechanics_disposition=(
            hit.mechanics_disposition if hit is not None else None
        ),
        authority_binding_count=len(hit.bindings) if hit is not None else 0,
        authority_available_binding_count=(
            sum(1 for b in hit.bindings if b.hydration_status == "available")
            if hit is not None
            else 0
        ),
        bridge_attachment_count=0,
        bridge_generic_binding_count=0,
        shadow_hydrated_binding_count=0,
        binding_results=(),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )


def _log_observation(observation: DungeonMindThreatHydrationShadowObservation) -> None:
    payload = {
        "event": _SHADOW_EVENT,
        "schema": observation.schema,
        "world_id": observation.world_id,
        "campaign_id": observation.campaign_id,
        "revision_id": observation.revision_id,
        "threat_node_id": observation.threat_node_id,
        "source_kind": observation.source_kind,
        "verdict": observation.verdict,
        "reason_codes": list(observation.reason_codes),
        "authority_mechanics_disposition": observation.authority_mechanics_disposition,
        "authority_binding_count": observation.authority_binding_count,
        "authority_available_binding_count": observation.authority_available_binding_count,
        "bridge_attachment_count": observation.bridge_attachment_count,
        "bridge_generic_binding_count": observation.bridge_generic_binding_count,
        "shadow_hydrated_binding_count": observation.shadow_hydrated_binding_count,
        "elapsed_ms": observation.elapsed_ms,
        "dungeonmind_hydration_reason": observation.dungeonmind_hydration_reason,
        "binding_results": [
            {
                "source_binding_id": item.source_binding_id,
                "target_binding_id": item.target_binding_id,
                "target_attachment_id": item.target_attachment_id,
                "authority_hydration_status": item.authority_hydration_status,
                "structural_status": item.structural_status,
                "shadow_hydration_status": item.shadow_hydration_status,
                "reason_codes": list(item.reason_codes),
            }
            for item in observation.binding_results
        ],
    }
    message = "%s verdict=%s threat_node_id=%s revision_id=%s reasons=%s"
    args = (
        _SHADOW_EVENT,
        observation.verdict,
        observation.threat_node_id,
        observation.revision_id,
        list(observation.reason_codes),
    )
    if observation.verdict == "mismatch":
        logger.warning(message + " observation=%s", *args, payload)
    elif observation.verdict == "shadow_error":
        logger.warning(message + " observation=%s", *args, payload)
    else:
        logger.info(message + " observation=%s", *args, payload)


def shadow_threat_hit(
    *,
    hit: ThreatQueryHydrationHitV1,
    request: ThreatQueryHydrationRequestV1,
    response: ThreatQueryHydrationResponseV1,
    source: _ExactBuddyRevisionBridgeSource,
) -> DungeonMindThreatHydrationShadowObservation:
    """Compare one authoritative hit. Package-internal; used by tests."""
    started = time.perf_counter()
    if (hit.threat.kind or "") != _EXPLICIT_THREAT_KIND:
        return _observation_for_not_eligible(
            hit=hit, response=response, started=started
        )
    return _shadow_eligible_threat(
        hit=hit,
        request=request,
        response=response,
        source=source,
        started=started,
    )


def run_dungeonmind_threat_hydration_shadow(
    *,
    request: ThreatQueryHydrationRequestV1,
    authoritative_response: ThreatQueryHydrationResponseV1,
    root: Path,
) -> list[DungeonMindThreatHydrationShadowObservation]:
    """Post-response shadow entrypoint. Never raises into framework task handling."""
    observations: list[DungeonMindThreatHydrationShadowObservation] = []
    try:
        observations = list(
            _run_shadow_contained(
                request=request,
                authoritative_response=authoritative_response,
                root=root,
            )
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "%s verdict=shadow_error reason=unexpected_shadow_exception world_id=%s revision_id=%s",
            _SHADOW_EVENT,
            authoritative_response.world_id,
            authoritative_response.revision_id,
        )
        started = time.perf_counter()
        for hit in authoritative_response.hits:
            obs = _observation_shadow_error(
                threat_node_id=hit.threat.node_id,
                source_kind=hit.threat.kind,
                response=authoritative_response,
                hit=hit,
                reason="unexpected_shadow_exception",
                started=started,
            )
            _log_observation(obs)
            observations.append(obs)
    return observations


def _run_shadow_contained(
    *,
    request: ThreatQueryHydrationRequestV1,
    authoritative_response: ThreatQueryHydrationResponseV1,
    root: Path,
) -> list[DungeonMindThreatHydrationShadowObservation]:
    observations: list[DungeonMindThreatHydrationShadowObservation] = []
    started_load = time.perf_counter()
    try:
        source = _load_exact_buddy_revision_bridge_source(
            root=root,
            world_id=authoritative_response.world_id,
            revision_id=authoritative_response.revision_id,
        )
    except ThreatConformanceBridgeError:
        for hit in authoritative_response.hits:
            obs = _observation_shadow_error(
                threat_node_id=hit.threat.node_id,
                source_kind=hit.threat.kind,
                response=authoritative_response,
                hit=hit,
                reason="bridge_source_integrity_failure",
                started=started_load,
            )
            _log_observation(obs)
            observations.append(obs)
        return observations

    for hit in authoritative_response.hits:
        hit_started = time.perf_counter()
        try:
            observation = shadow_threat_hit(
                hit=hit,
                request=request,
                response=authoritative_response,
                source=source,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "%s verdict=shadow_error threat_node_id=%s",
                _SHADOW_EVENT,
                hit.threat.node_id,
            )
            observation = _observation_shadow_error(
                threat_node_id=hit.threat.node_id,
                source_kind=hit.threat.kind,
                response=authoritative_response,
                hit=hit,
                reason="unexpected_shadow_exception",
                started=hit_started,
            )
        _log_observation(observation)
        observations.append(observation)
    return observations


__all__ = [
    "AuthorityExactRevisionReplayResolver",
    "DungeonMindThreatHydrationShadowObservation",
    "ShadowBindingResult",
    "run_dungeonmind_threat_hydration_shadow",
    "shadow_threat_hit",
]
