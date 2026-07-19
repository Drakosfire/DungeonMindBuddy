"""Apply the approved C1 additive contribution bundle onto an existing world head.

Unlike ``world_graph_bootstrap`` (C2 init-only), this path requires an existing
``worldId=eldyrwild`` head and merges ordered contributions. The first
contribution supersedes the C2 Questionable Company roster so shared ``pc:*``
nodes become world-owned (``campaign_scope=null``).
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
from graph_memory.world_supergraph.contribution_store import load_contribution_index
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError

APPROVED_C1_BUNDLE_ID = "eldyrwild-longmont-c1-s1-s3-v1"
APPROVED_C1_BUNDLE_RELPATH = (
    "graph_data/approved_contribution_bundles/eldyrwild-longmont-c1-s1-s3-v1"
)
APPROVED_WORLD_ID = "eldyrwild"
APPROVED_CAMPAIGN_ID = "longmont-c1"
QC_ROSTER_CONTRIBUTION_ID = "contribution:33d7cdb0ff623f28"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class C1AdditiveApplyStatus(_Model):
    schema_: str = Field(default="dmb_c1_additive_apply_status_v1", alias="schema")
    world_id: str
    bundle_id: str
    head_present: bool
    head_revision_id: str | None = None
    already_applied: bool = False
    active_contribution_ids: list[str] = Field(default_factory=list)


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


def load_approved_c1_additive_bundle(repo: Path | None = None) -> _LoadedC1Bundle:
    bundle_dir = _bundle_dir(repo)
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        raise C1AdditiveApplyError(
            f"missing C1 additive bundle manifest at {manifest_path}",
            code="bundle_not_found",
            status_code=404,
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ordered = list(manifest.get("ordered_contribution_paths") or [])
    if not ordered:
        raise C1AdditiveApplyError(
            "C1 additive bundle manifest has no ordered_contribution_paths",
            code="invalid_bundle",
        )
    digest = _compute_digest(bundle_dir, ordered)
    expected = str(manifest.get("bundle_digest") or "")
    if expected and expected != digest:
        raise C1AdditiveApplyError(
            f"bundle digest mismatch: expected {expected}, got {digest}",
            code="bundle_digest_mismatch",
        )
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
    if contributions[0].supersedes_contribution_id != QC_ROSTER_CONTRIBUTION_ID:
        raise C1AdditiveApplyError(
            "first contribution must supersede the C2 QC roster contribution",
            code="invalid_bundle",
        )
    return _LoadedC1Bundle(
        bundle_dir=bundle_dir,
        manifest=manifest,
        contributions=contributions,
        digest=digest,
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
    expected_ids = [c.contribution_id for c in bundle.contributions]
    already = all(cid in index.active_contribution_ids for cid in expected_ids)
    return C1AdditiveApplyStatus(
        world_id=APPROVED_WORLD_ID,
        bundle_id=APPROVED_C1_BUNDLE_ID,
        head_present=True,
        head_revision_id=head.head_revision_id,
        already_applied=already,
        active_contribution_ids=list(index.active_contribution_ids),
    )


def apply_approved_c1_additive_bundle(
    *,
    actor: str,
    root: Path | None = None,
    repo: Path | None = None,
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
            applied_contribution_ids=[c.contribution_id for c in bundle.contributions],
            diagnostics=["already_applied"],
        )

    applied: list[str] = []
    superseded: list[str] = []
    diagnostics: list[str] = [f"actor:{actor.strip()}"]
    parent_revision_id = head.head_revision_id
    head_revision_id = head.head_revision_id

    first, *rest = bundle.contributions
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
    applied.append(first.contribution_id)
    superseded.append(QC_ROSTER_CONTRIBUTION_ID)
    diagnostics.extend(supersede_result.diagnostics or [])
    head_revision_id = supersede_result.revision_id or head_revision_id
    parent_revision_id = head_revision_id

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
