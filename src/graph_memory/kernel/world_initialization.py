"""Generic Kernel world initialization from a bound contribution plan (PR006D1)."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from graph_memory.kernel.contribution_diagnostics import build_contribution_integrity_report
from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.kernel.contribution_merge import merge_contribution_to_revision
from graph_memory.kernel.contribution_rebuild import rebuild_from_contributions
from graph_memory.kernel.contributions import (
    canonical_payload_sha256,
    compute_contribution_payload_sha256,
)
from graph_memory.kernel.world_graph import (
    load_current_world_graph,
    open_world_graph_head,
    publish_world_revision,
)
from graph_memory.kernel.world_initialization_models import (
    RECEIPT_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationError,
    WorldInitializationPlan,
    WorldInitializationReceipt,
    WorldInitializationResult,
    WorldInitializationState,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.union_supergraph.validate import validate_union_supergraph_store_payload
from graph_memory.world_supergraph import paths as world_paths
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    load_contribution_record,
)
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError
from graph_memory.world_supergraph.integrity import build_world_graph_integrity_report
from graph_memory.world_supergraph.storage import (
    load_world_graph_revision_manifest,
    try_open_world_graph_head,
)

UNION_SUPERGRAPH_SCHEMA = "dmb_union_supergraph_store_v0"
UNION_SUPERGRAPH_VERSION = "0.1"


def compute_initialization_plan_digest(plan: WorldInitializationPlan) -> str:
    """Hash the complete canonical initialization plan payload."""
    return canonical_payload_sha256(plan.model_dump(mode="json", by_alias=True))


def compute_initialization_attestation_digest(
    attestation: WorldInitializationApprovalAttestation,
) -> str:
    """Hash the complete canonical approval-attestation payload."""
    return canonical_payload_sha256(attestation.model_dump(mode="json", by_alias=True))


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def build_empty_technical_baseline_store(
    campaign_id: str,
    focus_session_id: str,
) -> UnionSupergraphStore:
    """Return a structurally valid empty World Supergraph baseline."""
    payload = {
        "schema": UNION_SUPERGRAPH_SCHEMA,
        "version": UNION_SUPERGRAPH_VERSION,
        "campaign_id": campaign_id,
        "focus_session_id": focus_session_id,
        "nodes": {},
        "edges": {},
        "evidence": {},
        "source_artifacts": {},
        "aliases": {},
        "assertion_support": {},
        "adjacency": {},
        "identity_decisions": [],
        "identity_redirects": [],
        "identity_merge_records": [],
        "diagnostics": {
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
    }
    validate_union_supergraph_store_payload(payload)
    return UnionSupergraphStore.model_validate(payload)


def read_initialization_receipt(
    root: Path,
    world_id: str,
) -> WorldInitializationReceipt | None:
    """Load the immutable initialization receipt for a world, if present."""
    path = world_paths.initialization_receipt_path(root, world_id)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return WorldInitializationReceipt.model_validate(payload)


def _attestation_matches(
    receipt: WorldInitializationReceipt,
    attestation: WorldInitializationApprovalAttestation,
) -> bool:
    recorded = receipt.approval_attestation
    return (
        recorded.bundle_id == attestation.bundle_id
        and recorded.bundle_digest == attestation.bundle_digest
        and recorded.approved_bundle_merge_sha == attestation.approved_bundle_merge_sha
    )


def _receipt_matches_plan(
    receipt: WorldInitializationReceipt,
    *,
    plan: WorldInitializationPlan,
    plan_digest: str,
) -> bool:
    return (
        receipt.world_id == plan.world_id
        and receipt.campaign_id == plan.campaign_id
        and receipt.focus_session_id == plan.focus_session_id
        and receipt.plan_digest == plan_digest
        and receipt.ordered_contributions == plan.ordered_contributions
        and _attestation_matches(receipt, plan.approval_attestation)
    )


def _revision_is_ancestor(
    root: Path,
    world_id: str,
    *,
    ancestor_revision_id: str,
    descendant_revision_id: str,
) -> bool:
    """Return True when ``ancestor`` is on the parent chain of ``descendant``."""
    if ancestor_revision_id == descendant_revision_id:
        return True
    seen: set[str] = set()
    current: str | None = descendant_revision_id
    while current is not None:
        if current in seen:
            raise WorldInitializationError(
                f"revision lineage cycle detected at {current!r}",
                state="inconsistent_lineage",
            )
        seen.add(current)
        if current == ancestor_revision_id:
            return True
        try:
            revision = load_world_graph_revision_manifest(root, world_id, current)
        except WorldGraphNotFoundError as exc:
            raise WorldInitializationError(
                f"missing revision while walking lineage: {current!r}",
                state="inconsistent_lineage",
            ) from exc
        current = revision.parent_revision_id
    return False


def classify_head_relative_to_initialization(
    root: Path,
    world_id: str,
    *,
    initial_head_revision_id: str,
    current_head_revision_id: str,
) -> WorldInitializationState:
    """Classify current head relative to the receipt's initial head."""
    if current_head_revision_id == initial_head_revision_id:
        return "active"
    if _revision_is_ancestor(
        root,
        world_id,
        ancestor_revision_id=initial_head_revision_id,
        descendant_revision_id=current_head_revision_id,
    ):
        return "active_head_advanced"
    return "inconsistent_lineage"


def inspect_world_initialization_state(
    root: Path,
    *,
    world_id: str,
    plan: WorldInitializationPlan,
    plan_digest: str | None = None,
) -> WorldInitializationState:
    """Classify whether initialization may proceed for the attested plan."""
    if world_id != plan.world_id:
        return "blocked_existing_world"
    world_dir = world_paths.world_dir(root, world_id)
    if not world_dir.exists():
        return "ready"

    receipt = read_initialization_receipt(root, world_id)
    if receipt is None:
        return "blocked_existing_world"
    plan_digest = plan_digest or compute_initialization_plan_digest(plan)
    if not _receipt_matches_plan(receipt, plan=plan, plan_digest=plan_digest):
        return "blocked_existing_world"

    head = try_open_world_graph_head(root, world_id)
    if head is None:
        return "blocked_existing_world"
    try:
        return classify_head_relative_to_initialization(
            root,
            world_id,
            initial_head_revision_id=receipt.initial_head_revision_id,
            current_head_revision_id=head.head_revision_id,
        )
    except WorldInitializationError as exc:
        if exc.state == "inconsistent_lineage":
            return "inconsistent_lineage"
        raise


@contextmanager
def _world_init_promotion_lock(root: Path) -> Iterator[None]:
    lock_path = world_paths.world_init_lock_path(root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _baseline_operation_id(world_id: str, bundle_id: str) -> str:
    return f"world-init:{world_id}:{bundle_id}:empty-baseline"


def _bind_contributions_to_plan(
    plan: WorldInitializationPlan,
    contributions: list[GraphContribution],
    *,
    diagnostics: list[str],
 ) -> str:
    if not plan.ordered_contributions:
        raise WorldInitializationError(
            "initialization plan ordered_contributions must be non-empty",
            state="error",
            diagnostics=diagnostics,
        )
    if not contributions:
        raise WorldInitializationError(
            "contribution list must be non-empty",
            state="error",
            diagnostics=diagnostics,
        )
    actual_ids = [item.contribution_id for item in contributions]
    expected_ids = plan.ordered_contribution_ids
    if len(set(expected_ids)) != len(expected_ids):
        raise WorldInitializationError(
            "initialization plan contains duplicate contribution IDs",
            state="error",
            diagnostics=diagnostics,
        )
    if actual_ids != expected_ids:
        raise WorldInitializationError(
            "contribution list is not bound to plan.ordered_contributions",
            state="error",
            diagnostics=[
                *diagnostics,
                f"expected_ids={expected_ids}",
                f"actual_ids={actual_ids}",
            ],
        )
    for expected, contribution in zip(plan.ordered_contributions, contributions):
        if contribution.world_id != plan.world_id:
            raise WorldInitializationError(
                "contribution world_id does not match plan.world_id: "
                f"{contribution.contribution_id}",
                state="error",
                diagnostics=diagnostics,
            )
        if contribution.identity_decision_ids:
            raise WorldInitializationError(
                "identity decision references are unsupported by PR006D1: "
                f"{contribution.contribution_id}",
                state="error",
                diagnostics=diagnostics,
            )
        actual_digest = compute_contribution_payload_sha256(contribution)
        if actual_digest != expected.payload_sha256:
            raise WorldInitializationError(
                "contribution payload digest does not match initialization plan: "
                f"{contribution.contribution_id}",
                state="error",
                diagnostics=[
                    *diagnostics,
                    f"expected_payload_sha256={expected.payload_sha256}",
                    f"actual_payload_sha256={actual_digest}",
                ],
            )
    return compute_initialization_plan_digest(plan)


def _verify_initialized_world(
    root: Path,
    *,
    plan: WorldInitializationPlan,
    baseline_revision_id: str,
    diagnostics: list[str],
) -> tuple[int, list[str], bool, bool, bool]:
    head, _revision, store = load_current_world_graph(root, plan.world_id)
    index = load_contribution_index(root, plan.world_id)

    if index.baseline_revision_id != baseline_revision_id:
        raise WorldInitializationError(
            "baseline_revision_id does not match empty baseline",
            state="error",
            diagnostics=diagnostics,
        )
    if list(index.active_contribution_ids) != plan.ordered_contribution_ids:
        raise WorldInitializationError(
            "active contribution ids do not match initialization plan",
            state="error",
            diagnostics=diagnostics,
        )

    ledger_records = [
        load_contribution_record(root, plan.world_id, item.contribution_id)
        for item in plan.ordered_contributions
    ]
    for expected, record in zip(plan.ordered_contributions, ledger_records):
        actual_digest = compute_contribution_payload_sha256(record)
        if actual_digest != expected.payload_sha256:
            raise WorldInitializationError(
                "persisted contribution payload digest does not match "
                f"initialization plan: {record.contribution_id}",
                state="error",
                diagnostics=diagnostics,
            )

    rebuild = rebuild_from_contributions(root, world_id=plan.world_id, publish=False)
    rebuild_equivalent = "rebuild_equivalent_to_head" in rebuild.diagnostics
    if not rebuild_equivalent:
        raise WorldInitializationError(
            "rebuild_from_contributions is not equivalent to head",
            state="error",
            diagnostics=[*diagnostics, *rebuild.diagnostics],
        )

    contribution_health = build_contribution_integrity_report(
        root,
        world_id=plan.world_id,
        check_rebuild=True,
    )
    contribution_integrity_ok = contribution_health.rebuild_equivalent_to_head is True
    if not contribution_integrity_ok:
        raise WorldInitializationError(
            "contribution integrity rebuild check failed",
            state="error",
            diagnostics=[*diagnostics, *contribution_health.diagnostics],
        )
    if contribution_health.unsupported_assertion_ids:
        raise WorldInitializationError(
            "accepted assertions lack resolvable support/evidence",
            state="error",
            diagnostics=[
                *diagnostics,
                f"unsupported={contribution_health.unsupported_assertion_ids}",
            ],
        )

    world_health = build_world_graph_integrity_report(
        root,
        plan.world_id,
        persist=False,
    )
    world_integrity_ok = world_health.load_ok and world_health.validation_ok
    if not world_integrity_ok:
        raise WorldInitializationError(
            "world integrity check failed",
            state="error",
            diagnostics=[*diagnostics, *world_health.errors],
        )

    source_domains = {
        *store.source_domains,
        *(domain for node in store.nodes.values() for domain in node.source_domains),
        *(domain for edge in store.edges.values() for domain in edge.source_domains),
        *(evidence.source_domain for evidence in store.evidence.values()),
        *(artifact.source_domain for artifact in store.source_artifacts.values()),
    }
    for record in ledger_records:
        for assertion in record.accepted_assertions:
            assertion_domains = assertion.value.get("source_domains", [])
            if isinstance(assertion_domains, list):
                source_domains.update(
                    domain
                    for domain in assertion_domains
                    if isinstance(domain, str)
                )
    source_domains = sorted(source_domains)
    accepted_assertion_count = sum(
        len(record.accepted_assertions) for record in ledger_records
    )
    _ = head
    return (
        accepted_assertion_count,
        source_domains,
        rebuild_equivalent,
        world_integrity_ok,
        contribution_integrity_ok,
    )


def _build_receipt(
    root: Path,
    *,
    plan: WorldInitializationPlan,
    actor: str,
    baseline_revision_id: str,
    diagnostics: list[str],
) -> WorldInitializationReceipt:
    head, _revision, store = load_current_world_graph(root, plan.world_id)
    (
        accepted_assertion_count,
        source_domains,
        rebuild_equivalent,
        world_integrity_ok,
        contribution_integrity_ok,
    ) = _verify_initialized_world(
        root,
        plan=plan,
        baseline_revision_id=baseline_revision_id,
        diagnostics=diagnostics,
    )
    return WorldInitializationReceipt(
        schema=RECEIPT_SCHEMA,
        world_id=plan.world_id,
        campaign_id=plan.campaign_id,
        focus_session_id=plan.focus_session_id,
        actor=actor,
        baseline_revision_id=baseline_revision_id,
        initial_head_revision_id=head.head_revision_id,
        plan_digest=compute_initialization_plan_digest(plan),
        ordered_contributions=list(plan.ordered_contributions),
        identity_decision_ids=[],
        node_count=len(store.nodes),
        edge_count=len(store.edges),
        accepted_assertion_count=accepted_assertion_count,
        assertion_support_count=len(store.assertion_support),
        evidence_count=len(store.evidence),
        source_artifact_count=len(store.source_artifacts),
        source_domains=source_domains,
        rebuild_equivalent=rebuild_equivalent,
        world_integrity_ok=world_integrity_ok,
        contribution_integrity_ok=contribution_integrity_ok,
        plan_binding_verified=True,
        approval_attestation=plan.approval_attestation,
        created_at=_utc_now_iso(),
    )


def _write_initialization_receipt(
    root: Path,
    *,
    world_id: str,
    receipt: WorldInitializationReceipt,
) -> None:
    path = world_paths.initialization_receipt_path(root, world_id)
    _atomic_write_json(path, receipt.model_dump(mode="json", by_alias=True))


def _cleanup_staging(staging_root: Path) -> None:
    if staging_root.exists():
        shutil.rmtree(staging_root)


def _best_effort_diagnostic(diagnostics: list[str], message: str) -> None:
    try:
        diagnostics.append(message)
    except Exception:
        # The publication result must not become a failure after promotion
        # merely because diagnostic bookkeeping is unavailable.
        pass


def _stage_and_build_world(
    root: Path,
    *,
    plan: WorldInitializationPlan,
    contributions: list[GraphContribution],
    diagnostics: list[str],
) -> tuple[Path, Path, str]:
    run_id = uuid.uuid4().hex
    staging_root = world_paths.staging_run_dir(root, plan.world_id, run_id)
    staged_world = world_paths.staged_world_dir(staging_root, plan.world_id)
    if staging_root.exists():
        raise WorldInitializationError(
            f"staging directory already exists: {staging_root}",
            state="error",
            diagnostics=diagnostics,
        )

    staging_root.mkdir(parents=True, exist_ok=False)
    try:
        baseline = build_empty_technical_baseline_store(
            plan.campaign_id,
            plan.focus_session_id,
        )
        baseline_result = publish_world_revision(
            staging_root,
            plan.world_id,
            baseline,
            operation_ids=[
                _baseline_operation_id(
                    plan.world_id,
                    plan.approval_attestation.bundle_id,
                )
            ],
            expected_parent_revision_id=None,
        )
        baseline_revision_id = baseline_result.revision.revision_id
        diagnostics.append(f"published_empty_baseline:{baseline_revision_id}")

        parent_revision_id = baseline_revision_id
        plan_digest = compute_initialization_plan_digest(plan)
        attestation_digest = compute_initialization_attestation_digest(
            plan.approval_attestation
        )
        for contribution in contributions:
            merge_result = merge_contribution_to_revision(
                staging_root,
                world_id=plan.world_id,
                contribution=contribution,
                expected_parent_revision_id=parent_revision_id,
                initialization_contribution_ids=plan.ordered_contribution_ids,
                initialization_plan_digest=plan_digest,
                initialization_attestation_digest=attestation_digest,
            )
            if not merge_result.published or merge_result.revision_id is None:
                raise WorldInitializationError(
                    f"contribution merge did not publish: {contribution.contribution_id}",
                    state="error",
                    diagnostics=[*diagnostics, *merge_result.diagnostics],
                )
            parent_revision_id = merge_result.revision_id
            diagnostics.append(
                f"merged_contribution:{contribution.contribution_id}:{parent_revision_id}"
            )

        _verify_initialized_world(
            staging_root,
            plan=plan,
            baseline_revision_id=baseline_revision_id,
            diagnostics=diagnostics,
        )
        return staging_root, staged_world, baseline_revision_id
    except Exception:
        _cleanup_staging(staging_root)
        raise


def _promote_staged_world(
    root: Path,
    *,
    world_id: str,
    staged_world: Path,
    diagnostics: list[str],
) -> None:
    target_world = world_paths.world_dir(root, world_id)
    if target_world.exists():
        raise WorldInitializationError(
            f"production world already exists: {target_world}",
            state="blocked_existing_world",
            diagnostics=diagnostics,
        )

    committed = False
    try:
        with _world_init_promotion_lock(root):
            if target_world.exists():
                raise WorldInitializationError(
                    f"production world appeared during promotion: {target_world}",
                    state="blocked_existing_world",
                    diagnostics=diagnostics,
                )
            target_world.parent.mkdir(parents=True, exist_ok=True)
            os.rename(staged_world, target_world)
            committed = True
    except Exception:
        if not committed:
            raise


def initialize_world_from_contributions(
    root: Path,
    *,
    plan: WorldInitializationPlan,
    contributions: list[GraphContribution],
    actor: str,
) -> WorldInitializationResult:
    """Initialize a world from a plan-bound contribution list with atomic promotion.

    Universal Kernel invariants enforced here: empty structural baseline,
    ordered merge, rebuild/integrity proof, plan↔contribution binding, atomic
    promotion, and revision-lineage classification. Application acceptance
    policy (exact node counts, forbidden legacy IDs, bundle certification)
    belongs outside this API.
    """
    diagnostics: list[str] = []
    world_paths.assert_safe_world_id(plan.world_id)
    plan_digest = _bind_contributions_to_plan(
        plan, contributions, diagnostics=diagnostics
    )

    existing_state = inspect_world_initialization_state(
        root,
        world_id=plan.world_id,
        plan=plan,
        plan_digest=plan_digest,
    )
    if existing_state == "active":
        receipt = read_initialization_receipt(root, plan.world_id)
        head = open_world_graph_head(root, plan.world_id)
        diagnostics.append("idempotent_noop:world_already_initialized")
        return WorldInitializationResult(
            published=False,
            state="active",
            baseline_revision_id=receipt.baseline_revision_id if receipt else None,
            initial_head_revision_id=(
                receipt.initial_head_revision_id if receipt else None
            ),
            current_head_revision_id=head.head_revision_id,
            receipt=receipt,
            diagnostics=diagnostics,
        )
    if existing_state == "active_head_advanced":
        receipt = read_initialization_receipt(root, plan.world_id)
        head = open_world_graph_head(root, plan.world_id)
        diagnostics.append("idempotent_noop:head_advanced_past_initial")
        return WorldInitializationResult(
            published=False,
            state="active_head_advanced",
            baseline_revision_id=receipt.baseline_revision_id if receipt else None,
            initial_head_revision_id=(
                receipt.initial_head_revision_id if receipt else None
            ),
            current_head_revision_id=head.head_revision_id,
            receipt=receipt,
            diagnostics=diagnostics,
        )
    if existing_state == "inconsistent_lineage":
        raise WorldInitializationError(
            f"world {plan.world_id!r} head is not a descendant of the initialized head",
            state="inconsistent_lineage",
            diagnostics=diagnostics,
        )
    if existing_state == "blocked_existing_world":
        raise WorldInitializationError(
            f"world {plan.world_id!r} exists without a matching initialization receipt",
            state="blocked_existing_world",
            diagnostics=diagnostics,
        )

    staging_root: Path | None = None
    try:
        staging_root, staged_world, baseline_revision_id = _stage_and_build_world(
            root,
            plan=plan,
            contributions=contributions,
            diagnostics=diagnostics,
        )

        receipt = _build_receipt(
            staging_root,
            plan=plan,
            actor=actor,
            baseline_revision_id=baseline_revision_id,
            diagnostics=diagnostics,
        )
        _write_initialization_receipt(
            staging_root, world_id=plan.world_id, receipt=receipt
        )

        _promote_staged_world(
            root,
            world_id=plan.world_id,
            staged_world=staged_world,
            diagnostics=diagnostics,
        )
    except WorldInitializationError:
        if staging_root is not None:
            _cleanup_staging(staging_root)
        raise
    except Exception as exc:
        if staging_root is not None:
            _cleanup_staging(staging_root)
        raise WorldInitializationError(
            f"world initialization failed: {exc}",
            state="error",
            diagnostics=diagnostics,
        ) from exc

    # os.rename above is the irreversible commit point. Nothing below may
    # turn a successfully published world into an error response.
    try:
        _cleanup_staging(staging_root)
    except Exception as exc:
        try:
            _best_effort_diagnostic(
                diagnostics,
                f"post_promotion_cleanup_failed:{type(exc).__name__}:{exc}",
            )
        except Exception:
            pass
    try:
        _best_effort_diagnostic(diagnostics, "initialization_complete")
    except Exception:
        pass
    return WorldInitializationResult(
        published=True,
        state="active",
        baseline_revision_id=baseline_revision_id,
        initial_head_revision_id=receipt.initial_head_revision_id,
        current_head_revision_id=receipt.initial_head_revision_id,
        receipt=receipt,
        diagnostics=diagnostics,
    )
