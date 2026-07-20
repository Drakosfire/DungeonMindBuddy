"""Apply the approved C1 additive contribution bundle onto an existing world head.

Unlike ``world_graph_bootstrap`` (C2 init-only), this path requires an existing
``worldId=eldyrwild`` head and merges ordered contributions. The first
contribution supersedes the C2 Questionable Company roster so shared ``pc:*``
nodes become world-owned (``campaign_scope=null``).

Partial apply is detected via ``get_c1_additive_apply_status``; blind
retries raise ``partial_apply_detected`` unless ``resume_from_contribution_id``
matches the next pending bundle contribution.

Authority for the locked package lives in this service (bundle id, digest,
world, campaign, apply mode, ordered contribution IDs, required nodes, and
source domains) — not in optional self-declared manifest fields alone.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

import graph_memory.kernel as kernel
from apps.live_control_server.config import repo_root, world_graph_root
from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.kernel.contributions import contribution_source_payload
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    load_contribution_record,
)
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError

APPROVED_C1_BUNDLE_ID = "eldyrwild-longmont-c1-s1-s3-v1"
APPROVED_C1_BUNDLE_DIGEST = (
    "a1c69790bfd372b21e2ef6ae8bbe04b3f7fde341200a3ffb2068b49b4cc50df4"
)
APPROVED_C1_BUNDLE_RELPATH = (
    "graph_data/approved_contribution_bundles/eldyrwild-longmont-c1-s1-s3-v1"
)
APPROVED_WORLD_ID = "eldyrwild"
APPROVED_CAMPAIGN_ID = "longmont-c1"
APPROVED_APPLY_MODE = "additive_merge_onto_existing_head"
QC_ROSTER_CONTRIBUTION_ID = "contribution:33d7cdb0ff623f28"
APPROVED_ORDERED_CONTRIBUTION_IDS: tuple[str, ...] = (
    "contribution:b978465948b6923a",
    "contribution:c426972739dcc766",
    "contribution:6cabb0aff854ce86",
    "contribution:516aa36afa3139e7",
    "contribution:2ce41b7c841cdd7d",
)
APPROVED_ORDERED_CONTRIBUTION_PATHS: tuple[str, ...] = (
    "contributions/000-pc-world-ownership-supersede.json",
    "contributions/001-heroes-party-roster.json",
    "contributions/002-session-1-stonebridge-glowkindle.json",
    "contributions/003-session-2-stonebridge-aftermath.json",
    "contributions/004-session-3-stone-bridge-flood.json",
)
EXPECTED_SOURCE_DOMAINS = frozenset({"manual_seed"})
REQUIRED_NODE_IDS = frozenset(
    {
        "pc:baergrom",
        "pc:bonogo",
        "pc:caelynn",
        "pc:ephanna",
        "pc:karsemine",
        "pc:stafl",
        "party:heroes-party",
        "location:stonebridge",
        "location:stone-bridge-span",
        "event:longmont-c1:session-1:glowkindle-rats",
        "event:longmont-c1:session-2:stonebridge-aftermath",
        "event:longmont-c1:session-3:stone-bridge-flood",
        "npc:grishna",
        "npc:pippa",
        "location:wizards-tower-brewing-co",
    }
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class C1AdditiveApplyStatus(_Model):
    schema_: str = Field(default="dmb_c1_additive_apply_status_v1", alias="schema")
    world_id: str
    bundle_id: str
    head_present: bool
    head_revision_id: str | None = None
    already_applied: bool = False
    partial_applied: bool = False
    expected_contribution_ids: list[str] = Field(default_factory=list)
    applied_contribution_ids: list[str] = Field(default_factory=list)
    pending_contribution_ids: list[str] = Field(default_factory=list)
    active_contribution_ids: list[str] = Field(default_factory=list)
    qc_roster_superseded: bool = False


class C1AdditiveApplyResult(_Model):
    schema_: str = Field(default="dmb_c1_additive_apply_result_v1", alias="schema")
    world_id: str
    bundle_id: str
    bundle_digest: str
    actor: str
    published: bool
    parent_revision_id: str | None = None
    head_revision_id: str | None = None
    applied_contribution_ids: list[str] = Field(default_factory=list)
    superseded_contribution_ids: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class _LoadedC1Bundle:
    bundle_dir: Path
    manifest: dict[str, Any]
    contributions: list[GraphContribution]
    digest: str


class C1AdditiveApplyError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _bundle_dir(repo: Path | None = None) -> Path:
    root = (repo or repo_root()).resolve()
    return root / APPROVED_C1_BUNDLE_RELPATH


def _compute_digest(bundle_dir: Path, ordered_paths: list[str]) -> str:
    digest = hashlib.sha256()
    for rel in ordered_paths:
        digest.update((bundle_dir / rel).read_bytes())
    return digest.hexdigest()


def _collect_source_domains(contributions: list[GraphContribution]) -> set[str]:
    domains: set[str] = set()
    for contribution in contributions:
        for assertion in contribution.accepted_assertions:
            value = assertion.value if isinstance(assertion.value, dict) else {}
            for domain in value.get("source_domains") or []:
                if isinstance(domain, str) and domain.strip():
                    domains.add(domain.strip())
            for artifact in value.get("source_artifacts") or []:
                if not isinstance(artifact, dict):
                    continue
                domain = artifact.get("source_domain")
                if isinstance(domain, str) and domain.strip():
                    domains.add(domain.strip())
    return domains


def _collect_node_ids(contributions: list[GraphContribution]) -> set[str]:
    return {
        assertion.subject_node_id
        for contribution in contributions
        for assertion in contribution.accepted_assertions
        if assertion.assertion_kind == "node" and assertion.subject_node_id
    }


def _authority_errors(
    *,
    manifest: dict[str, Any],
    ordered_paths: list[str],
    contributions: list[GraphContribution],
    digest: str,
) -> list[str]:
    errors: list[str] = []
    if manifest.get("bundle_id") != APPROVED_C1_BUNDLE_ID:
        errors.append("bundle_id does not match the locked C1 additive package")
    if digest != APPROVED_C1_BUNDLE_DIGEST:
        errors.append("bundle digest does not match the locked C1 additive package")
    declared_digest = str(manifest.get("bundle_digest") or "").strip()
    if not declared_digest:
        errors.append("manifest bundle_digest is required and must match the locked package")
    elif declared_digest != APPROVED_C1_BUNDLE_DIGEST:
        errors.append("manifest bundle_digest does not match the locked C1 additive package")
    if manifest.get("world_id") != APPROVED_WORLD_ID:
        errors.append("world_id does not match the locked C1 additive package")
    if manifest.get("primary_campaign_scope") != APPROVED_CAMPAIGN_ID:
        errors.append("primary_campaign_scope does not match the locked C1 additive package")
    if manifest.get("apply_mode") != APPROVED_APPLY_MODE:
        errors.append("apply_mode does not match the locked C1 additive package")
    if ordered_paths != list(APPROVED_ORDERED_CONTRIBUTION_PATHS):
        errors.append("ordered_contribution_paths do not match the locked C1 additive package")
    observed_ids = [c.contribution_id for c in contributions]
    if observed_ids != list(APPROVED_ORDERED_CONTRIBUTION_IDS):
        errors.append("ordered contribution IDs do not match the locked C1 additive package")
    if contributions and contributions[0].supersedes_contribution_id != QC_ROSTER_CONTRIBUTION_ID:
        errors.append("first contribution must supersede the C2 QC roster contribution")
    observed_domains = _collect_source_domains(contributions)
    if observed_domains != EXPECTED_SOURCE_DOMAINS:
        errors.append("source domains do not match the locked C1 additive package")
    observed_nodes = _collect_node_ids(contributions)
    if not REQUIRED_NODE_IDS.issubset(observed_nodes):
        errors.append("required node set is missing from the locked C1 additive package")
    return errors


def load_approved_c1_additive_bundle(repo: Path | None = None) -> _LoadedC1Bundle:
    bundle_dir = _bundle_dir(repo)
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        raise C1AdditiveApplyError(
            f"missing C1 additive bundle manifest at {manifest_path}",
            code="bundle_not_found",
            status_code=404,
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise C1AdditiveApplyError(
            f"invalid C1 additive bundle manifest: {exc}",
            code="invalid_bundle",
        ) from exc
    if not isinstance(manifest, dict):
        raise C1AdditiveApplyError(
            "C1 additive bundle manifest must be a JSON object",
            code="invalid_bundle",
        )
    ordered = list(manifest.get("ordered_contribution_paths") or [])
    if not ordered:
        raise C1AdditiveApplyError(
            "C1 additive bundle manifest has no ordered_contribution_paths",
            code="invalid_bundle",
        )
    digest = _compute_digest(bundle_dir, ordered)
    contributions: list[GraphContribution] = []
    for rel in ordered:
        path = bundle_dir / rel
        try:
            contributions.append(
                GraphContribution.model_validate(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            )
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise C1AdditiveApplyError(
                f"invalid contribution at {rel}: {exc}",
                code="invalid_bundle",
            ) from exc
    errors = _authority_errors(
        manifest=manifest,
        ordered_paths=ordered,
        contributions=contributions,
        digest=digest,
    )
    if errors:
        raise C1AdditiveApplyError(
            "C1 additive bundle failed locked-package authority: " + "; ".join(errors),
            code="invalid_bundle",
        )
    return _LoadedC1Bundle(
        bundle_dir=bundle_dir,
        manifest=manifest,
        contributions=contributions,
        digest=digest,
    )


def _semantic_contribution_payload(contribution: GraphContribution) -> dict[str, Any]:
    """Lifecycle-neutral payload with Kernel-rewritten assertion IDs removed.

    Merge/supersede may recompute ``assertion_id`` values; semantic content
    (subjects, predicates, values, scopes, provenance) must still match the
    locked package.
    """
    payload = contribution_source_payload(contribution)
    for key in ("accepted_assertions", "candidate_assertions", "rejected_assertions"):
        for assertion in payload.get(key) or []:
            if isinstance(assertion, dict):
                assertion.pop("assertion_id", None)
                assertion.pop("contribution_id", None)
    return payload


def _verify_applied_prefix_payloads(
    *,
    world_root: Path,
    bundle: _LoadedC1Bundle,
    applied_ids: list[str],
) -> None:
    by_id = {c.contribution_id: c for c in bundle.contributions}
    for contribution_id in applied_ids:
        expected = by_id[contribution_id]
        try:
            stored = load_contribution_record(
                world_root, APPROVED_WORLD_ID, contribution_id
            )
        except FileNotFoundError as exc:
            raise C1AdditiveApplyError(
                f"applied contribution {contribution_id!r} is missing from the ledger",
                code="partial_apply_corrupt",
                status_code=409,
            ) from exc
        if _semantic_contribution_payload(expected) != _semantic_contribution_payload(
            stored
        ):
            raise C1AdditiveApplyError(
                f"applied contribution {contribution_id!r} payload does not match "
                "the locked C1 additive package",
                code="partial_apply_corrupt",
                status_code=409,
            )


def _bundle_apply_progress(
    *,
    world_root: Path,
    bundle: _LoadedC1Bundle,
    active_contribution_ids: list[str],
    superseded_contribution_ids: list[str],
) -> tuple[list[str], list[str], list[str], bool, bool, bool]:
    """Return exact ordered-prefix progress for the locked C1 sequence.

    Applied IDs must be an exact prefix of the locked contribution order.
    Any out-of-order / non-prefix active membership fails closed.
    When any prefix step is present, the QC roster must already be superseded
    and inactive.
    """
    expected_ids = [c.contribution_id for c in bundle.contributions]
    active = set(active_contribution_ids)
    superseded = set(superseded_contribution_ids)

    applied: list[str] = []
    for contribution_id in expected_ids:
        if contribution_id in active:
            applied.append(contribution_id)
        else:
            break
    pending = expected_ids[len(applied) :]
    non_prefix = [cid for cid in pending if cid in active]
    if non_prefix:
        raise C1AdditiveApplyError(
            "C1 additive apply progress is not an exact ordered prefix; "
            f"unexpected active contribution(s): {non_prefix!r}",
            code="partial_apply_corrupt",
            status_code=409,
        )

    qc_roster_superseded = (
        QC_ROSTER_CONTRIBUTION_ID in superseded
        and QC_ROSTER_CONTRIBUTION_ID not in active
    )
    if applied:
        if not qc_roster_superseded:
            raise C1AdditiveApplyError(
                "C1 additive prefix is present but the C2 QC roster was not "
                "superseded / remains active",
                code="partial_apply_corrupt",
                status_code=409,
            )
        _verify_applied_prefix_payloads(
            world_root=world_root,
            bundle=bundle,
            applied_ids=applied,
        )

    already_applied = not pending
    partial_applied = bool(applied) and bool(pending)
    return (
        expected_ids,
        applied,
        pending,
        already_applied,
        partial_applied,
        qc_roster_superseded,
    )


def get_c1_additive_apply_status(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> C1AdditiveApplyStatus:
    world_root = (root or world_graph_root()).resolve()
    bundle = load_approved_c1_additive_bundle(repo)
    try:
        head, _revision, _store = kernel.open_current_world_graph(
            world_root, APPROVED_WORLD_ID
        )
    except WorldGraphNotFoundError:
        return C1AdditiveApplyStatus(
            world_id=APPROVED_WORLD_ID,
            bundle_id=APPROVED_C1_BUNDLE_ID,
            head_present=False,
        )
    index = load_contribution_index(world_root, APPROVED_WORLD_ID)
    (
        expected_ids,
        applied_ids,
        pending_ids,
        already_applied,
        partial_applied,
        qc_roster_superseded,
    ) = _bundle_apply_progress(
        world_root=world_root,
        bundle=bundle,
        active_contribution_ids=list(index.active_contribution_ids),
        superseded_contribution_ids=list(index.superseded_contribution_ids),
    )
    return C1AdditiveApplyStatus(
        world_id=APPROVED_WORLD_ID,
        bundle_id=APPROVED_C1_BUNDLE_ID,
        head_present=True,
        head_revision_id=head.head_revision_id,
        already_applied=already_applied,
        partial_applied=partial_applied,
        expected_contribution_ids=expected_ids,
        applied_contribution_ids=applied_ids,
        pending_contribution_ids=pending_ids,
        active_contribution_ids=list(index.active_contribution_ids),
        qc_roster_superseded=qc_roster_superseded,
    )


def apply_approved_c1_additive_bundle(
    *,
    actor: str,
    root: Path | None = None,
    repo: Path | None = None,
    resume_from_contribution_id: str | None = None,
) -> C1AdditiveApplyResult:
    if not (actor or "").strip():
        raise C1AdditiveApplyError("actor is required", code="invalid_actor")
    world_root = (root or world_graph_root()).resolve()
    bundle = load_approved_c1_additive_bundle(repo)
    try:
        head, _revision, _store = kernel.open_current_world_graph(
            world_root, APPROVED_WORLD_ID
        )
    except WorldGraphNotFoundError as exc:
        raise C1AdditiveApplyError(
            "world head missing; activate the C2 bootstrap before applying C1 additive",
            code="world_graph_unavailable",
            status_code=409,
        ) from exc

    status = get_c1_additive_apply_status(root=world_root, repo=repo)
    if status.already_applied:
        return C1AdditiveApplyResult(
            world_id=APPROVED_WORLD_ID,
            bundle_id=APPROVED_C1_BUNDLE_ID,
            bundle_digest=bundle.digest,
            actor=actor.strip(),
            published=False,
            parent_revision_id=head.head_revision_id,
            head_revision_id=head.head_revision_id,
            applied_contribution_ids=list(status.applied_contribution_ids),
            diagnostics=["already_applied"],
        )

    resume_from = (resume_from_contribution_id or "").strip() or None
    if status.partial_applied:
        if not resume_from:
            raise C1AdditiveApplyError(
                "partial C1 additive apply detected; pass resume_from_contribution_id "
                f"starting at {status.pending_contribution_ids[0]!r}",
                code="partial_apply_detected",
                status_code=409,
            )
        if resume_from != status.pending_contribution_ids[0]:
            raise C1AdditiveApplyError(
                "resume_from_contribution_id must match the next pending bundle step "
                f"({status.pending_contribution_ids[0]!r})",
                code="invalid_resume_step",
                status_code=409,
            )
    elif resume_from:
        raise C1AdditiveApplyError(
            "resume_from_contribution_id requires partial bundle progress",
            code="invalid_resume_step",
            status_code=409,
        )

    applied: list[str] = list(status.applied_contribution_ids)
    superseded: list[str] = []
    diagnostics: list[str] = [f"actor:{actor.strip()}"]
    parent_revision_id = head.head_revision_id
    head_revision_id = head.head_revision_id

    pending_ids = (
        status.pending_contribution_ids
        if status.partial_applied
        else [c.contribution_id for c in bundle.contributions]
    )
    contributions_to_apply = [
        contribution
        for contribution in bundle.contributions
        if contribution.contribution_id in set(pending_ids)
    ]
    # Preserve locked order even if pending_ids is a set-filtered subset.
    pending_order = {cid: index for index, cid in enumerate(pending_ids)}
    contributions_to_apply.sort(
        key=lambda contribution: pending_order[contribution.contribution_id]
    )

    if (
        contributions_to_apply
        and contributions_to_apply[0].contribution_id == bundle.contributions[0].contribution_id
    ):
        first = contributions_to_apply[0]
        rest = contributions_to_apply[1:]
        supersede_result = kernel.supersede_graph_contribution(
            world_root,
            world_id=APPROVED_WORLD_ID,
            new_contribution=first,
            superseded_contribution_id=QC_ROSTER_CONTRIBUTION_ID,
            expected_parent_revision_id=parent_revision_id,
        )
        if not supersede_result.published:
            raise C1AdditiveApplyError(
                "PC world-ownership supersede did not publish: "
                + "; ".join(supersede_result.diagnostics or ["unknown"]),
                code="supersede_failed",
                status_code=409,
            )
        if first.contribution_id not in applied:
            applied.append(first.contribution_id)
        superseded.append(QC_ROSTER_CONTRIBUTION_ID)
        diagnostics.extend(supersede_result.diagnostics or [])
        head_revision_id = supersede_result.revision_id or head_revision_id
        parent_revision_id = head_revision_id
        contributions_to_apply = rest
    else:
        rest = contributions_to_apply

    for contribution in rest:
        merge_result = kernel.merge_contribution_to_revision(
            world_root,
            world_id=APPROVED_WORLD_ID,
            contribution=contribution,
            expected_parent_revision_id=parent_revision_id,
        )
        if not merge_result.published and contribution.contribution_id not in (
            merge_result.contribution_ids or []
        ):
            # Idempotent re-merge may leave published=False with diagnostics.
            if "already_active" not in " ".join(merge_result.diagnostics or []):
                raise C1AdditiveApplyError(
                    f"merge failed for {contribution.contribution_id}: "
                    + "; ".join(merge_result.diagnostics or ["unknown"]),
                    code="merge_failed",
                    status_code=409,
                )
        applied.append(contribution.contribution_id)
        diagnostics.extend(merge_result.diagnostics or [])
        if merge_result.revision_id:
            head_revision_id = merge_result.revision_id
            parent_revision_id = head_revision_id

    return C1AdditiveApplyResult(
        world_id=APPROVED_WORLD_ID,
        bundle_id=APPROVED_C1_BUNDLE_ID,
        bundle_digest=bundle.digest,
        actor=actor.strip(),
        published=True,
        parent_revision_id=head.head_revision_id,
        head_revision_id=head_revision_id,
        applied_contribution_ids=applied,
        superseded_contribution_ids=superseded,
        diagnostics=diagnostics,
    )
