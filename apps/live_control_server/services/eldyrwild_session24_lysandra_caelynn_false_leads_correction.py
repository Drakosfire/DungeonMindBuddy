"""Governed one-off apply for Session-24 Lysandra→Caelynn false-leads correction.

Loads exactly one checked-in GraphContribution (contradiction without replacement),
proves eligible-parent preconditions against adjudication/continuity/source-seal
authority, and delegates publication to
``graph_memory.kernel.contradict_edge_assertion_support``.

Callers cannot inject a different correction artifact, target IDs, or
replacement semantics.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

import graph_memory.kernel as kernel
from apps.live_control_server.config import (
    live_world_graph_root,
    repo_root,
    world_graph_root,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_continuity_v1 import (
    analyze_relationship_adjudication_continuity_v1,
    prove_revision_is_anchor_or_descendant_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_REVISION_ID,
    ELDYRWILD_WORLD_ID,
)
from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    load_contribution_record,
)
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError

APPROVED_CORRECTION_RELPATH = (
    "graph_data/approved_graph_corrections/eldyrwild/"
    "session24-lysandra-caelynn-false-leads-v1.json"
)
SOURCE_SEAL_RELPATH = (
    "tests/fixtures/dungeonmind_kernel/"
    "eldyrwild_relationship_residual_source_seals_v1.json"
)
ADJUDICATION_RELPATH = (
    "tests/fixtures/dungeonmind_kernel/"
    "eldyrwild_relationship_residual_adjudication_v1.json"
)

WORLD_ID = ELDYRWILD_WORLD_ID
CAMPAIGN_ID = "longmont-c2"
ANCHOR_REVISION_ID = ELDYRWILD_REVISION_ID
# Eligible parent P = formal R_current after #549 / Session-24 C₂ live exit.
ELIGIBLE_PARENT_REVISION_ID = "rev:b8dfc063bc13a4fb297e83f5f9b313d9"
R_CURRENT_REVISION_ID = ELIGIBLE_PARENT_REVISION_ID
POST_LYSANDRA_REVISION_ID = "rev:b90646fb5b135988bd7842cde858c96e"
ELIGIBLE_PARENT_PAYLOAD_SHA256 = (
    "4539afb0e25ccca42f4a2ec479ab470f7c14cf31803f6caa581e0d03a1f0c776"
)

TARGET_EDGE_ID = "edge:npc_lysandra:leads:pc:caelynn"
TARGET_SOURCE_NODE_ID = "npc_lysandra"
TARGET_TARGET_NODE_ID = "pc:caelynn"
TARGET_PREDICATE = "leads"
TARGET_ASSERTION_ID = "assertion:fed9280859610fd0"

# Historical adjudication candidates; live A(X) must be a non-empty subset.
HISTORICAL_ADJUDICATED_SUPPORT_IDS = frozenset(
    {
        "contribution:fe483d91c47590a1",
        "contribution:a01be11c6967afd9",
    }
)

# Exact live A(X) sealed into C₃ at BUILD capture (subset of historical).
LOCKED_TARGET_CONTRIBUTION_IDS = frozenset({"contribution:fe483d91c47590a1"})

LOCKED_CORRECTION_CONTRIBUTION_ID = "contribution:222c55dadacfa67f"
LOCKED_CORRECTION_DIGEST = (
    "c053c3c640bdc56f5e46ba8772ba59ca30aef8e6471d3e949a1e8d469feb088b"
)
LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256 = (
    "96a874b4d1b29274f38b616318379ebae9c8af62729ba7f053005c1b13dc05e1"
)
LOCKED_CORRECTION_RAW_ARTIFACT_SHA256 = (
    "2c2c8a6809e3909ece077d4453e4ed6c501ef8339e85c4ae02cba187530d7aae"
)
LOCKED_SOURCE_ARTIFACT_ID = (
    "graph-native:eldyrwild-correction:session24-lysandra-caelynn-false-leads-v1"
)
LOCKED_SOURCE_REVISION_ID = (
    "correction:eldyrwild:session24-lysandra-caelynn-false-leads-v1"
)

LOCKED_EVIDENCE_REF_ID = (
    "evidence:artifact:recap:longmont-c2:session-24:session-24:recap:paragraph:008"
)
LOCKED_SOURCE_ARTIFACT_URI_ID = "artifact:recap:longmont-c2:session-24"
LOCKED_ARTIFACT_CONTENT_SHA256 = (
    "603c1590da3aca71d90c8b69abed59368219d5dc1e3d1adf83db1bf854b5cc95"
)
LOCKED_SOURCE_SPAN_REF_ID = "session-24:recap:paragraph:008"
LOCKED_EXCERPT_SHA256 = (
    "2ab9becf0e06d95c3fed34563a1ad2aadbb71667dbdcadeb64dd403406635d32"
)

# Predecessor correction authorities that must remain coherent on P / Q₃.
C1_CORRECTION_CONTRIBUTION_ID = "contribution:4c65f668dc95ef4f"
C1_CORRECTION_SOURCE_PAYLOAD_SHA256 = (
    "78d4d7118c3ba71ed0f930157bcd2343c675ccab8544580ff0aa506aa9ec0c5d"
)
C2_CORRECTION_CONTRIBUTION_ID = "contribution:6c13bc0f8edf4377"
C2_CORRECTION_SOURCE_PAYLOAD_SHA256 = (
    "b48de88cad19a21360c103d86edd3de17818249c72f6146daf7e04e076747e6d"
)
C2_TARGET_EDGE_ID = "edge:item-001:located_in:pc:karsemine"
C2_TARGET_ASSERTION_ID = "assertion:d27dd4e9041147bc"

EligibilityState = Literal[
    "eligible", "already_applied", "ineligible", "integrity_failure"
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Session24LysandraCaelynnFalseLeadsCorrectionStatus(_Model):
    schema_: str = Field(
        default=(
            "dmb_eldyrwild_session24_lysandra_caelynn_false_leads_correction_status_v1"
        ),
        alias="schema",
    )
    world_id: str
    campaign_id: str
    head_revision_id: str | None = None
    eligibility: EligibilityState
    reason: str | None = None
    target_edge_id: str = TARGET_EDGE_ID
    target_assertion_id: str = TARGET_ASSERTION_ID
    locked_target_contribution_ids: list[str] = Field(
        default_factory=lambda: sorted(LOCKED_TARGET_CONTRIBUTION_IDS)
    )
    correction_contribution_id: str = LOCKED_CORRECTION_CONTRIBUTION_ID
    correction_source_payload_sha256: str = LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    correction_raw_artifact_sha256: str = LOCKED_CORRECTION_RAW_ARTIFACT_SHA256
    continuity_state: str | None = None
    source_grounding_verified: bool | None = None
    durable_shape_verified: bool | None = None
    diagnostics: list[str] = Field(default_factory=list)


class Session24LysandraCaelynnFalseLeadsCorrectionResult(_Model):
    schema_: str = Field(
        default=(
            "dmb_eldyrwild_session24_lysandra_caelynn_false_leads_correction_result_v1"
        ),
        alias="schema",
    )
    world_id: str
    expected_parent_revision_id: str
    parent_revision_id: str | None = None
    revision_id: str | None = None
    published: bool
    eligibility: EligibilityState | None = None
    correction_contribution_id: str = LOCKED_CORRECTION_CONTRIBUTION_ID
    failure_code: str | None = None
    failure_message: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    kernel_result: dict[str, Any] | None = None


class Session24LysandraCaelynnFalseLeadsCorrectionError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _correction_path(repo: Path | None = None) -> Path:
    return (repo or repo_root()).resolve() / APPROVED_CORRECTION_RELPATH


def _source_seal_path(repo: Path | None = None) -> Path:
    return (repo or repo_root()).resolve() / SOURCE_SEAL_RELPATH


def _adjudication_path(repo: Path | None = None) -> Path:
    return (repo or repo_root()).resolve() / ADJUDICATION_RELPATH


def _resolve_root(root: Path | None) -> Path:
    return (root or world_graph_root()).resolve()


def _is_canonical_live_root(resolved: Path) -> bool:
    return resolved == live_world_graph_root().resolve()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _status(
    *,
    eligibility: EligibilityState,
    reason: str | None,
    diagnostics: list[str],
    head_revision_id: str | None = None,
    continuity_state: str | None = None,
    source_grounding_verified: bool | None = None,
    durable_shape_verified: bool | None = None,
) -> Session24LysandraCaelynnFalseLeadsCorrectionStatus:
    return Session24LysandraCaelynnFalseLeadsCorrectionStatus(
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        head_revision_id=head_revision_id,
        eligibility=eligibility,
        reason=reason,
        continuity_state=continuity_state,
        source_grounding_verified=source_grounding_verified,
        durable_shape_verified=durable_shape_verified,
        diagnostics=diagnostics,
    )


def load_approved_session24_lysandra_caelynn_false_leads_correction(
    *,
    repo: Path | None = None,
) -> GraphContribution:
    """Load and seal-check the locked approved contradiction contribution."""
    path = _correction_path(repo)
    if not path.is_file():
        raise Session24LysandraCaelynnFalseLeadsCorrectionError(
            f"approved correction artifact missing: {path}",
            code="correction_artifact_missing",
            status_code=500,
        )
    raw = path.read_bytes()
    raw_sha = _sha256_bytes(raw)
    try:
        payload = json.loads(raw.decode("utf-8"))
        contribution = GraphContribution.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 - surface as integrity failure
        raise Session24LysandraCaelynnFalseLeadsCorrectionError(
            f"approved correction artifact failed to validate: {exc}",
            code="correction_artifact_invalid",
            status_code=500,
        ) from exc

    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    correction_digest = kernel.compute_correction_digest(
        contribution.assertion_corrections
    )
    errors: list[str] = []
    if raw_sha != LOCKED_CORRECTION_RAW_ARTIFACT_SHA256:
        errors.append("raw artifact sha256 mismatch vs locked authority")
    if contribution.contribution_id != LOCKED_CORRECTION_CONTRIBUTION_ID:
        errors.append("contribution_id mismatch vs locked authority")
    if digest != LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256:
        errors.append("source-payload digest mismatch vs locked authority")
    if correction_digest != LOCKED_CORRECTION_DIGEST:
        errors.append("correction digest mismatch vs locked authority")
    if contribution.world_id != WORLD_ID:
        errors.append("world_id mismatch")
    if contribution.source_kind != "graph_review_authored_assertion":
        errors.append("source_kind mismatch")
    if contribution.authored_by != "gm":
        errors.append("authored_by mismatch")
    if contribution.source_artifact_id != LOCKED_SOURCE_ARTIFACT_ID:
        errors.append("source_artifact_id mismatch")
    if contribution.source_revision_id != LOCKED_SOURCE_REVISION_ID:
        errors.append("source_revision_id mismatch")
    if contribution.campaign_scope != CAMPAIGN_ID:
        errors.append("campaign_scope mismatch")
    if contribution.accepted_assertions:
        errors.append("contradiction must not carry accepted assertions")
    if contribution.candidate_assertions or contribution.rejected_assertions:
        errors.append("correction must not carry candidate/rejected assertions")
    if contribution.unresolved_mentions or contribution.identity_decision_ids:
        errors.append("correction must not carry unresolved/identity extras")
    if contribution.supersedes_contribution_id is not None:
        errors.append("correction must not supersede a contribution")
    if not contribution.assertion_corrections:
        errors.append("assertion_corrections must be non-empty")
    else:
        declared: list[str] = []
        for link in contribution.assertion_corrections:
            if link.correction_kind != "contradicts":
                errors.append("every correction_kind must be contradicts")
            if link.replacement_assertion_id is not None:
                errors.append("replacement_assertion_id must be null")
            if link.target_assertion_id != TARGET_ASSERTION_ID:
                errors.append("target_assertion_id mismatch")
            declared.append(link.target_contribution_id)
        if len(declared) != len(set(declared)):
            errors.append("duplicate target_contribution_id links")
        if set(declared) != LOCKED_TARGET_CONTRIBUTION_IDS:
            errors.append("declared target contribution IDs mismatch locked A(X)")
    if errors:
        raise Session24LysandraCaelynnFalseLeadsCorrectionError(
            "approved correction artifact integrity failure: " + "; ".join(errors),
            code="integrity_failure",
            status_code=400,
        )
    return contribution


def _verify_source_seals(*, repo: Path | None = None) -> tuple[bool, list[str]]:
    path = _source_seal_path(repo)
    if not path.is_file():
        return False, ["source_seal_fixture_missing"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False, ["source_seal_fixture_unreadable"]
    rows = payload.get("seals") or payload.get("rows") or payload
    if isinstance(payload, dict) and "edges" in payload:
        rows = payload["edges"]
    if not isinstance(rows, list):
        # Fixture shape: top-level list or {seals: [...]}
        if isinstance(payload, dict):
            for key in ("source_seals", "residual_source_seals", "items"):
                if isinstance(payload.get(key), list):
                    rows = payload[key]
                    break
        if not isinstance(rows, list):
            return False, ["source_seal_fixture_shape"]
    row = next(
        (
            r
            for r in rows
            if isinstance(r, dict) and r.get("edge_id") == TARGET_EDGE_ID
        ),
        None,
    )
    if row is None:
        return False, ["source_seal_row_missing"]
    diagnostics: list[str] = []
    checks = [
        ("primary_evidence_ref_id", LOCKED_EVIDENCE_REF_ID),
        ("source_artifact_id", LOCKED_SOURCE_ARTIFACT_URI_ID),
        ("artifact_content_sha256", LOCKED_ARTIFACT_CONTENT_SHA256),
        ("source_span_ref_id", LOCKED_SOURCE_SPAN_REF_ID),
        ("excerpt_sha256", LOCKED_EXCERPT_SHA256),
    ]
    for key, expected in checks:
        if row.get(key) != expected:
            diagnostics.append(f"source_seal_mismatch:{key}")
    return (not diagnostics), diagnostics or ["source_seals_verified"]


def _verify_adjudication(*, repo: Path | None = None) -> tuple[bool, list[str]]:
    path = _adjudication_path(repo)
    if not path.is_file():
        return False, ["adjudication_fixture_missing"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False, ["adjudication_fixture_unreadable"]
    rows = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return False, ["adjudication_fixture_shape"]
    row = next(
        (
            r
            for r in rows
            if isinstance(r, dict) and r.get("edge_id") == TARGET_EDGE_ID
        ),
        None,
    )
    if row is None:
        return False, ["adjudication_row_missing"]
    diagnostics: list[str] = []
    if row.get("disposition") != "SOURCE_CORRECTION_REQUIRED":
        diagnostics.append("adjudication_disposition_mismatch")
    if row.get("reason_code") != "PREDICATE_MISAPPLIED":
        diagnostics.append("adjudication_reason_mismatch")
    if row.get("responsible_repo") != "DungeonMindBuddy":
        diagnostics.append("adjudication_responsible_repo_mismatch")
    if row.get("next_action") != "AUTHOR_BUDDY_SOURCE_CORRECTION":
        diagnostics.append("adjudication_next_action_mismatch")
    if row.get("requires_source_mutation") is not True:
        diagnostics.append("adjudication_requires_source_mutation_mismatch")
    supporting_assertions = set(row.get("supporting_assertion_ids") or [])
    if TARGET_ASSERTION_ID not in supporting_assertions:
        diagnostics.append("adjudication_assertion_mismatch")
    supporting_contributions = set(row.get("supporting_contribution_ids") or [])
    if supporting_contributions != HISTORICAL_ADJUDICATED_SUPPORT_IDS:
        diagnostics.append("adjudication_support_ids_mismatch")
    return (not diagnostics), diagnostics or ["adjudication_verified"]


def _verify_predecessor_correction_authorities(
    *,
    root: Path,
    store: Any,
) -> tuple[bool, list[str]]:
    """Require C₁ and C₂ revision-bound digests remain coherent on the parent."""
    diagnostics: list[str] = []
    digests = store.contribution_source_payload_sha256 or {}
    if digests.get(C1_CORRECTION_CONTRIBUTION_ID) != C1_CORRECTION_SOURCE_PAYLOAD_SHA256:
        diagnostics.append("c1_revision_digest_mismatch_or_missing")
    if digests.get(C2_CORRECTION_CONTRIBUTION_ID) != C2_CORRECTION_SOURCE_PAYLOAD_SHA256:
        diagnostics.append("c2_revision_digest_mismatch_or_missing")

    c2_support = store.assertion_support.get(C2_TARGET_ASSERTION_ID)
    if not isinstance(c2_support, dict):
        diagnostics.append("c2_target_support_missing")
    else:
        if c2_support.get("support_state") != "contradicted":
            diagnostics.append("c2_target_not_contradicted")
        if list(c2_support.get("active_contribution_ids") or []):
            diagnostics.append("c2_target_active_support_nonempty")
        if C2_TARGET_EDGE_ID not in store.edges:
            diagnostics.append("c2_target_edge_missing")

    # Prefer the owning status seams when available; fall back to digest shape.
    try:
        from apps.live_control_server.services.eldyrwild_lysandra_threat_direction_correction import (
            get_lysandra_threat_direction_correction_status,
        )
        from apps.live_control_server.services.eldyrwild_session24_cube_karsemine_false_location_correction import (
            get_session24_cube_karsemine_false_location_correction_status,
        )

        c1 = get_lysandra_threat_direction_correction_status(root=root)
        c2 = get_session24_cube_karsemine_false_location_correction_status(root=root)
        if c1.eligibility != "already_applied":
            diagnostics.append(f"c1_status_{c1.eligibility}")
        if c2.eligibility != "already_applied":
            diagnostics.append(f"c2_status_{c2.eligibility}")
    except Exception as exc:  # noqa: BLE001 - surface as integrity failure
        diagnostics.append(f"predecessor_status_probe_failed:{type(exc).__name__}")

    return (not diagnostics), diagnostics or ["predecessor_corrections_coherent"]


def _support_shape_suggests_applied(store: Any) -> bool:
    support = store.assertion_support.get(TARGET_ASSERTION_ID)
    if not isinstance(support, dict):
        return False
    if support.get("support_state") != "contradicted":
        return False
    if list(support.get("active_contribution_ids") or []):
        return False
    contradicted = set(support.get("contradicted_contribution_ids") or [])
    if not LOCKED_TARGET_CONTRIBUTION_IDS.issubset(contradicted):
        return False
    edge = store.edges.get(TARGET_EDGE_ID)
    if edge is None:
        return False
    return (
        edge.source_node_id == TARGET_SOURCE_NODE_ID
        and edge.target_node_id == TARGET_TARGET_NODE_ID
        and edge.predicate == TARGET_PREDICATE
    )


def _manifest_entry(store: Any, contribution_id: str) -> Any | None:
    for entry in store.contribution_replay_manifest or []:
        cid = getattr(entry, "contribution_id", None)
        if cid is None and isinstance(entry, dict):
            cid = entry.get("contribution_id")
        if cid == contribution_id:
            return entry
    return None


def _revision_bound_correction_authority(
    *,
    root: Path,
    store: Any,
) -> tuple[bool, list[str]]:
    """Exact revision-bound + mutable-ledger proof that C is active authority."""
    diagnostics: list[str] = []
    digests = store.contribution_source_payload_sha256 or {}
    bound = digests.get(LOCKED_CORRECTION_CONTRIBUTION_ID)
    if bound != LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256:
        diagnostics.append("revision_digest_mismatch_or_missing")
        return False, diagnostics

    entry = _manifest_entry(store, LOCKED_CORRECTION_CONTRIBUTION_ID)
    if entry is None:
        diagnostics.append("replay_manifest_missing_C")
        return False, diagnostics
    status = getattr(entry, "status", None)
    if status is None and isinstance(entry, dict):
        status = entry.get("status")
    digest = getattr(entry, "source_payload_sha256", None)
    if digest is None and isinstance(entry, dict):
        digest = entry.get("source_payload_sha256")
    if status != "active":
        diagnostics.append("replay_manifest_C_not_active")
        return False, diagnostics
    if digest != LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256:
        diagnostics.append("replay_manifest_C_digest_mismatch")
        return False, diagnostics

    try:
        ledger = load_contribution_record(
            root, WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
        )
    except FileNotFoundError:
        diagnostics.append("mutable_C_ledger_missing")
        return False, diagnostics
    if ledger.contribution_id != LOCKED_CORRECTION_CONTRIBUTION_ID:
        diagnostics.append("mutable_C_id_mismatch")
        return False, diagnostics
    ledger_digest = kernel.compute_contribution_source_payload_sha256(ledger)
    if ledger_digest != LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256:
        diagnostics.append("mutable_C_digest_mismatch")
        return False, diagnostics
    if ledger.status != "active":
        diagnostics.append("mutable_C_not_active")
        return False, diagnostics

    # Mutable contribution index is a distinct authority store from revision
    # digests / replay manifest / ledger. already_applied requires coherence.
    index = load_contribution_index(root, WORLD_ID)
    all_ids = set(index.all_contribution_ids)
    active_ids = set(index.active_contribution_ids)
    superseded_ids = set(index.superseded_contribution_ids)
    retracted_ids = set(index.retracted_contribution_ids)
    failed_ids = set(index.failed_contribution_ids)
    if LOCKED_CORRECTION_CONTRIBUTION_ID not in all_ids:
        diagnostics.append("mutable_C_index_missing_from_all")
    if LOCKED_CORRECTION_CONTRIBUTION_ID not in active_ids:
        diagnostics.append("mutable_C_index_not_active")
    if LOCKED_CORRECTION_CONTRIBUTION_ID in superseded_ids:
        diagnostics.append("mutable_C_index_superseded")
    if LOCKED_CORRECTION_CONTRIBUTION_ID in retracted_ids:
        diagnostics.append("mutable_C_index_retracted")
    if LOCKED_CORRECTION_CONTRIBUTION_ID in failed_ids:
        diagnostics.append("mutable_C_index_failed")
    if any(d.startswith("mutable_C_index_") for d in diagnostics):
        return False, diagnostics

    if not _support_shape_suggests_applied(store):
        diagnostics.append("support_shape_incomplete")
        return False, diagnostics

    return True, ["revision_bound_C_authority"]


def _classify_applied_state(
    *,
    root: Path,
    store: Any,
    head_revision_id: str,
) -> Session24LysandraCaelynnFalseLeadsCorrectionStatus | None:
    authority_ok, auth_diag = _revision_bound_correction_authority(
        root=root, store=store
    )
    if authority_ok:
        return _status(
            eligibility="already_applied",
            reason="exact approved correction already revision-bound on head",
            diagnostics=["already_applied", *auth_diag],
            head_revision_id=head_revision_id,
        )

    shape = _support_shape_suggests_applied(store)
    digests = store.contribution_source_payload_sha256 or {}
    bound = digests.get(LOCKED_CORRECTION_CONTRIBUTION_ID)
    if shape or bound is not None:
        return _status(
            eligibility="integrity_failure",
            reason=(
                "correction-shaped support or C digest present without exact "
                "revision-bound C authority"
            ),
            diagnostics=["integrity_failure", *auth_diag],
            head_revision_id=head_revision_id,
        )
    return None


def _mutable_c_source_digest_collision(
    *,
    root: Path,
) -> tuple[bool, list[str]]:
    """True when an unbound mutable C ledger exists with a non-locked digest.

    Contribution IDs are stable across some source-payload fields (e.g.
    ``produced_at``). An unbound ledger row for locked C with different source
    bytes must fail closed before eligibility or publish; otherwise the Kernel
    writer would atomically overwrite the conflicting durable record before any
    revision-bound digest protects C.
    """
    try:
        ledger = load_contribution_record(
            root, WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
        )
    except FileNotFoundError:
        return False, []
    if ledger.contribution_id != LOCKED_CORRECTION_CONTRIBUTION_ID:
        return True, ["mutable_C_id_mismatch"]
    ledger_digest = kernel.compute_contribution_source_payload_sha256(ledger)
    if ledger_digest == LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256:
        return False, []
    return True, [
        "mutable_C_source_digest_collision",
        f"observed_digest={ledger_digest}",
    ]


def _preflight(
    *,
    root: Path,
    contribution: GraphContribution,
    expected_parent_revision_id: str | None,
    repo: Path | None = None,
) -> Session24LysandraCaelynnFalseLeadsCorrectionStatus:
    try:
        head, revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    except WorldGraphNotFoundError as exc:
        return _status(
            eligibility="ineligible",
            reason=f"world missing: {exc}",
            diagnostics=["world_missing"],
        )

    head_revision_id = head.head_revision_id
    if not head_revision_id:
        return _status(
            eligibility="ineligible",
            reason="Eldyrwild head revision is blank",
            diagnostics=["blank_head"],
        )

    # Exact-head fence before already_applied so stale expected parents cannot
    # masquerade as successful retries.
    if expected_parent_revision_id and expected_parent_revision_id != head_revision_id:
        return _status(
            eligibility="ineligible",
            reason=(
                f"expected parent {expected_parent_revision_id!r} is stale; "
                f"current head is {head_revision_id!r}"
            ),
            diagnostics=["stale_expected_parent"],
            head_revision_id=head_revision_id,
        )

    applied = _classify_applied_state(
        root=root, store=store, head_revision_id=head_revision_id
    )
    if applied is not None:
        return applied

    # Fail closed on same-ID / different-source mutable C before eligibility.
    collision, collision_diag = _mutable_c_source_digest_collision(root=root)
    if collision:
        return _status(
            eligibility="integrity_failure",
            reason=(
                "mutable ledger already contains locked C contribution_id with a "
                "different source-payload digest; refusing overwrite"
            ),
            diagnostics=["integrity_failure", *collision_diag],
            head_revision_id=head_revision_id,
        )

    parent_for_proof = expected_parent_revision_id or head_revision_id

    # Fresh application is locked to exact eligible parent P.
    if parent_for_proof != ELIGIBLE_PARENT_REVISION_ID:
        return _status(
            eligibility="ineligible",
            reason=(
                f"fresh application requires exact eligible parent "
                f"{ELIGIBLE_PARENT_REVISION_ID!r}; got {parent_for_proof!r}"
            ),
            diagnostics=["not_exact_eligible_parent"],
            head_revision_id=head_revision_id,
        )
    if revision.graph_payload_sha256 != ELIGIBLE_PARENT_PAYLOAD_SHA256:
        return _status(
            eligibility="integrity_failure",
            reason=(
                "eligible parent payload SHA256 mismatch vs locked P authority"
            ),
            diagnostics=["eligible_parent_payload_mismatch"],
            head_revision_id=head_revision_id,
        )

    seals_ok, seal_diag = _verify_source_seals(repo=repo)
    if not seals_ok:
        return _status(
            eligibility="integrity_failure",
            reason="source seal authority mismatch for target edge",
            diagnostics=["integrity_failure", *seal_diag],
            head_revision_id=head_revision_id,
        )

    adj_ok, adj_diag = _verify_adjudication(repo=repo)
    if not adj_ok:
        return _status(
            eligibility="integrity_failure",
            reason="immutable adjudication finding mismatch for target edge",
            diagnostics=["integrity_failure", *adj_diag],
            head_revision_id=head_revision_id,
        )

    ok, diagnostic, detail = prove_revision_is_anchor_or_descendant_v1(
        root=root,
        world_id=WORLD_ID,
        requested_revision_id=parent_for_proof,
        anchor_revision_id=ANCHOR_REVISION_ID,
        anchor_world_id=WORLD_ID,
    )
    if not ok:
        return _status(
            eligibility="ineligible",
            reason=detail or "parent is not adjudication anchor or descendant",
            diagnostics=[
                "ancestry_unproven",
                *([str(diagnostic)] if diagnostic else []),
            ],
            head_revision_id=head_revision_id,
        )

    lys_ok, lys_diag, lys_detail = prove_revision_is_anchor_or_descendant_v1(
        root=root,
        world_id=WORLD_ID,
        requested_revision_id=parent_for_proof,
        anchor_revision_id=POST_LYSANDRA_REVISION_ID,
        anchor_world_id=WORLD_ID,
    )
    if not lys_ok:
        return _status(
            eligibility="ineligible",
            reason=lys_detail
            or "parent is not post-Lysandra baseline or a proven descendant",
            diagnostics=[
                "post_lysandra_ancestry_unproven",
                *([str(lys_diag)] if lys_diag else []),
            ],
            head_revision_id=head_revision_id,
        )

    r_ok, r_diag, r_detail = prove_revision_is_anchor_or_descendant_v1(
        root=root,
        world_id=WORLD_ID,
        requested_revision_id=parent_for_proof,
        anchor_revision_id=R_CURRENT_REVISION_ID,
        anchor_world_id=WORLD_ID,
    )
    if not r_ok:
        return _status(
            eligibility="ineligible",
            reason=r_detail
            or "parent is not R_current or a proven descendant of R_current",
            diagnostics=[
                "r_current_ancestry_unproven",
                *([str(r_diag)] if r_diag else []),
            ],
            head_revision_id=head_revision_id,
        )

    pred_ok, pred_diag = _verify_predecessor_correction_authorities(
        root=root, store=store
    )
    if not pred_ok:
        return _status(
            eligibility="integrity_failure",
            reason=(
                "predecessor C₁/C₂ correction authority is incoherent on parent; "
                "refusing to publish C₃"
            ),
            diagnostics=["integrity_failure", *pred_diag],
            head_revision_id=head_revision_id,
        )

    continuity = analyze_relationship_adjudication_continuity_v1(
        root=root,
        world_id=WORLD_ID,
        revision_id=parent_for_proof,
    )
    row = next(
        (r for r in continuity.rows if r.edge_id == TARGET_EDGE_ID),
        None,
    )
    if row is None:
        return _status(
            eligibility="ineligible",
            reason="target edge missing from continuity report",
            diagnostics=["continuity_row_missing"],
            head_revision_id=head_revision_id,
        )
    if row.continuity_state not in {"ANCHOR", "CARRIED_FORWARD"}:
        return _status(
            eligibility="ineligible",
            reason=(
                f"target continuity_state is {row.continuity_state!r}, "
                "expected ANCHOR or CARRIED_FORWARD"
            ),
            diagnostics=["continuity_inactive", row.continuity_state],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=row.source_grounding_verified,
            durable_shape_verified=row.durable_shape_verified,
        )
    if not row.source_grounding_verified or not row.durable_shape_verified:
        return _status(
            eligibility="ineligible",
            reason="target source grounding or durable shape not verified",
            diagnostics=["continuity_unverified"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=row.source_grounding_verified,
            durable_shape_verified=row.durable_shape_verified,
        )

    support = store.assertion_support.get(TARGET_ASSERTION_ID)
    if not isinstance(support, dict) or support.get("support_state") != "supported":
        return _status(
            eligibility="ineligible",
            reason="target assertion support is not currently supported",
            diagnostics=["target_support_not_supported"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )
    if support.get("assertion_kind") != "edge":
        return _status(
            eligibility="ineligible",
            reason="target assertion_kind is not edge",
            diagnostics=["target_not_edge_assertion"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )
    if support.get("graph_object_id") != TARGET_EDGE_ID:
        return _status(
            eligibility="ineligible",
            reason="target assertion graph_object_id drifted from X",
            diagnostics=["target_graph_object_drift"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )

    active_ids = set(support.get("active_contribution_ids") or [])
    if not active_ids:
        return _status(
            eligibility="ineligible",
            reason="target assertion has no active supporting contributions",
            diagnostics=["target_support_empty"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )
    if not active_ids.issubset(HISTORICAL_ADJUDICATED_SUPPORT_IDS):
        return _status(
            eligibility="ineligible",
            reason=(
                "active support includes contribution IDs outside the historically "
                "adjudicated set; requires re-adjudication"
            ),
            diagnostics=["active_support_outside_historical"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )
    if active_ids != LOCKED_TARGET_CONTRIBUTION_IDS:
        return _status(
            eligibility="ineligible",
            reason=(
                "active support set does not exactly match locked A(X) sealed into C; "
                f"got {sorted(active_ids)!r}"
            ),
            diagnostics=["active_support_mismatch_locked_c"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )

    for cid in sorted(LOCKED_TARGET_CONTRIBUTION_IDS):
        try:
            target_contribution = load_contribution_record(root, WORLD_ID, cid)
        except FileNotFoundError:
            return _status(
                eligibility="ineligible",
                reason=f"target contribution missing: {cid}",
                diagnostics=["target_contribution_missing", cid],
                head_revision_id=head_revision_id,
                continuity_state=row.continuity_state,
                source_grounding_verified=True,
                durable_shape_verified=True,
            )
        if target_contribution.status != "active":
            return _status(
                eligibility="ineligible",
                reason=(
                    f"target contribution {cid} status is "
                    f"{target_contribution.status!r}, expected active"
                ),
                diagnostics=["target_contribution_inactive", cid],
                head_revision_id=head_revision_id,
                continuity_state=row.continuity_state,
                source_grounding_verified=True,
                durable_shape_verified=True,
            )
        target_assertion = next(
            (
                a
                for a in target_contribution.accepted_assertions
                if a.assertion_id == TARGET_ASSERTION_ID
            ),
            None,
        )
        if target_assertion is None or target_assertion.assertion_kind != "edge":
            return _status(
                eligibility="ineligible",
                reason=(
                    f"target contribution {cid} missing accepted edge assertion "
                    f"{TARGET_ASSERTION_ID}"
                ),
                diagnostics=["target_assertion_missing", cid],
                head_revision_id=head_revision_id,
                continuity_state=row.continuity_state,
                source_grounding_verified=True,
                durable_shape_verified=True,
            )

    live_edge = store.edges.get(TARGET_EDGE_ID)
    if live_edge is None:
        return _status(
            eligibility="ineligible",
            reason=f"live defective edge missing: {TARGET_EDGE_ID}",
            diagnostics=["live_edge_missing"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )
    if (
        live_edge.source_node_id != TARGET_SOURCE_NODE_ID
        or live_edge.target_node_id != TARGET_TARGET_NODE_ID
        or live_edge.predicate != TARGET_PREDICATE
    ):
        return _status(
            eligibility="ineligible",
            reason=(
                "live defective edge shape drifted: "
                f"{live_edge.source_node_id} --{live_edge.predicate}--> "
                f"{live_edge.target_node_id}"
            ),
            diagnostics=["live_edge_shape_drift"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )

    eff = analyze_relationship_effective_conformance_v1(
        root=root,
        world_id=WORLD_ID,
        revision_id=parent_for_proof,
    )
    if TARGET_EDGE_ID not in eff.remaining_residual_edge_ids:
        return _status(
            eligibility="ineligible",
            reason="target edge is not in the parent's effective residual set",
            diagnostics=["target_not_effective_residual"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )

    _ = contribution  # seal-checked; Kernel revalidates on apply
    return _status(
        eligibility="eligible",
        reason=(
            "parent is eligible for the locked Session-24 Lysandra→Caelynn "
            "false-leads contradiction"
        ),
        diagnostics=["eligible", *seal_diag, *adj_diag, *pred_diag],
        head_revision_id=head_revision_id,
        continuity_state=row.continuity_state,
        source_grounding_verified=True,
        durable_shape_verified=True,
    )


def get_session24_lysandra_caelynn_false_leads_correction_status(
    *,
    root: Path | None = None,
    expected_parent_revision_id: str | None = None,
    repo: Path | None = None,
) -> Session24LysandraCaelynnFalseLeadsCorrectionStatus:
    """Read-only eligibility/status against the locked correction artifact."""
    try:
        contribution = load_approved_session24_lysandra_caelynn_false_leads_correction(
            repo=repo
        )
    except Session24LysandraCaelynnFalseLeadsCorrectionError as exc:
        if exc.code in {
            "integrity_failure",
            "correction_artifact_invalid",
            "correction_artifact_missing",
            "correction_artifact_tampered",
        }:
            return _status(
                eligibility="integrity_failure",
                reason=str(exc),
                diagnostics=["integrity_failure", exc.code],
            )
        raise
    return _preflight(
        root=_resolve_root(root),
        contribution=contribution,
        expected_parent_revision_id=expected_parent_revision_id,
        repo=repo,
    )


def apply_session24_lysandra_caelynn_false_leads_correction(
    *,
    expected_parent_revision_id: str,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> Session24LysandraCaelynnFalseLeadsCorrectionResult:
    """Apply the locked contradiction to an exact eligible Eldyrwild parent."""
    if not expected_parent_revision_id or not expected_parent_revision_id.strip():
        raise Session24LysandraCaelynnFalseLeadsCorrectionError(
            "expected_parent_revision_id is required",
            code="expected_parent_required",
        )
    expected = expected_parent_revision_id.strip()
    world_root = _resolve_root(root)
    if _is_canonical_live_root(world_root) and not allow_live_world:
        raise Session24LysandraCaelynnFalseLeadsCorrectionError(
            "canonical live world root requires allow_live_world=True",
            code="live_world_opt_in_required",
        )

    contribution = load_approved_session24_lysandra_caelynn_false_leads_correction(
        repo=repo
    )

    try:
        head_probe, _, _ = kernel.open_current_world_graph(world_root, WORLD_ID)
    except WorldGraphNotFoundError as exc:
        raise Session24LysandraCaelynnFalseLeadsCorrectionError(
            f"world missing: {exc}",
            code="ineligible_parent",
        ) from exc
    if head_probe.head_revision_id != expected:
        raise Session24LysandraCaelynnFalseLeadsCorrectionError(
            (
                f"expected parent {expected!r} is stale; "
                f"current head is {head_probe.head_revision_id!r}"
            ),
            code="stale_expected_parent",
        )

    status = _preflight(
        root=world_root,
        contribution=contribution,
        expected_parent_revision_id=expected,
        repo=repo,
    )
    if status.eligibility == "already_applied":
        return Session24LysandraCaelynnFalseLeadsCorrectionResult(
            world_id=WORLD_ID,
            expected_parent_revision_id=expected,
            parent_revision_id=expected,
            revision_id=status.head_revision_id,
            published=False,
            eligibility="already_applied",
            diagnostics=[*status.diagnostics, "already_applied_noop"],
        )
    if status.eligibility == "integrity_failure":
        raise Session24LysandraCaelynnFalseLeadsCorrectionError(
            status.reason or "integrity failure",
            code="integrity_failure",
        )
    if status.eligibility != "eligible":
        raise Session24LysandraCaelynnFalseLeadsCorrectionError(
            status.reason
            or "parent is ineligible for Session-24 Lysandra→Caelynn false-leads correction",
            code="ineligible_parent",
        )

    head_now, _, _ = kernel.open_current_world_graph(world_root, WORLD_ID)
    if head_now.head_revision_id != expected:
        raise Session24LysandraCaelynnFalseLeadsCorrectionError(
            (
                f"expected parent {expected!r} is stale; "
                f"current head is {head_now.head_revision_id!r}"
            ),
            code="stale_expected_parent",
        )

    try:
        merge = kernel.contradict_edge_assertion_support(
            world_root,
            world_id=WORLD_ID,
            contribution=contribution,
            expected_parent_revision_id=expected,
        )
    except ValueError as exc:
        raise Session24LysandraCaelynnFalseLeadsCorrectionError(
            str(exc),
            code="kernel_rejected",
        ) from exc

    return Session24LysandraCaelynnFalseLeadsCorrectionResult(
        world_id=WORLD_ID,
        expected_parent_revision_id=expected,
        parent_revision_id=merge.parent_revision_id,
        revision_id=merge.revision_id or status.head_revision_id,
        published=bool(merge.published),
        eligibility=status.eligibility,
        failure_code=merge.failure_code,
        failure_message=merge.failure_message,
        diagnostics=[*status.diagnostics, *list(merge.diagnostics or [])],
        kernel_result=merge.model_dump(mode="json", by_alias=True),
    )
