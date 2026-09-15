#!/usr/bin/env python3
"""Zero-model frozen 42-session two-arm acceptance replay.

Acceptance-only runner.  It consumes current post-genesis production code and a
read-only #715 notebook checkout.  It must not merge, rebase, or cherry-pick
the notebook, regenerate candidates, or call a model.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

ARMS = ("openai-gpt-5.4-mini", "deepseek-v4.1-flash")
ARM_DATABASE = {
    "openai-gpt-5.4-mini": "dmb_full_corpus_openai",
    "deepseek-v4.1-flash": "dmb_full_corpus_deepseek",
}
ARM_WORLD = {
    "openai-gpt-5.4-mini": "dogfood-frozen42-openai-v1",
    "deepseek-v4.1-flash": "dogfood-frozen42-deepseek-v1",
}
ALLOWED_REHEARSAL_DATABASES = frozenset(ARM_DATABASE.values())
REHEARSAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
REHEARSAL_PORT = 54329
LIVE_AUTHORITY_PORTS = frozenset({54330, 54331})
NOTEBOOK_HEAD = "820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed"
CANDIDATE_FROZEN_HEAD = "d6e2599bbabb9719bc92601f7bc1ad8b69411e98"
GENESIS_MERGE_SHA = "876123a3d197d426ce76e03a30f059093ba9b4f4"
MANIFEST_REL = "out/full_corpus_world_graph_ingestion/ACCEPTANCE_MANIFEST.json"
EXPERIMENT_CLAIM = (
    "two autoregressive, chronologically generated candidate arms, followed by "
    "zero-model governed replay into independently initialized Worlds."
)
EXPECTED_SESSION_COUNT = 42
GENESIS_CAMPAIGN = "longmont-c1"
GENESIS_ROSTER_KEY = "1"
GENESIS_ACTOR = "full-corpus-acceptance-genesis"
CANONICAL_PC_LABELS = frozenset({"Baergrom", "Bonogo", "Caelynn", "Ephanna", "Karsemine", "Stafl"})
CANONICAL_PC_OBJECT_IDS = (
    "node:baergrom",
    "node:bonogo",
    "node:caelynn",
    "node:ephanna",
    "node:karsemine",
    "node:stafl",
)
CANONICAL_PC_IDENTITY_KEYS = (
    "pc::baergrom",
    "pc::bonogo",
    "pc::caelynn",
    "pc::ephanna",
    "pc::karsemine",
    "pc::stafl",
)
MODEL_ENV_KEYS = ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "DUNGEONBUDDY_OPENROUTER")
FORBIDDEN_IMPORT_SUBSTRINGS = (
    "openai",
    "openrouter",
    "entity_extractor",
    "fact_extractor",
    "deepseek_category",
    "ingest_full_corpus",
    "category_graph_pass",
)
_SEAL_COMPARE_KEYS = (
    "campaign",
    "session",
    "candidate_sha256",
    "source_sha256",
    "source_artifact_id",
    "candidate_path",
    "source_path",
)
# Bounded Gate A discovery: none of these can be applied identically to the two
# rehearsal Worlds without new wiring or model calls.
SEMANTIC_BENCHMARK_DISCOVERY = {
    "inspected": [
        "evals/sentence_routing_retrieval_falsification",
        "apps/live_control_server/services/graph_gold_review.py",
        "tests/test_cutover_native_genesis_continuity.py",
    ],
    "selected": None,
    "verdict": "SEMANTIC MODEL SELECTION HOLD",
    "reason": (
        "no repository-owned deterministic continuity/query benchmark applies "
        "identically to these two rehearsal Worlds without new wiring or model calls"
    ),
}


class AcceptanceError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _digest_file(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def jobs() -> list[tuple[str, int]]:
    """Frozen 42-session corpus: C1 S1–17 + C2 S1–25.  Do not add S26/S27."""
    return [("longmont-c1", n) for n in range(1, 18)] + [("longmont-c2", n) for n in range(1, 26)]


def derived_world_id(arm: str) -> str:
    world_id = ARM_WORLD.get(arm)
    if world_id is None:
        raise AcceptanceError(f"unknown arm {arm!r}")
    return world_id


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip() or f"exit {completed.returncode}"
        raise AcceptanceError(f"git {' '.join(args)} failed in {root}: {detail}")
    return completed.stdout


def git_head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").strip()


def git_status_porcelain(root: Path) -> str:
    return _git(root, "status", "--porcelain")


def git_is_ancestor(root: Path, ancestor: str, head: str = "HEAD") -> bool:
    completed = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, head],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def _contained_file(root: Path, path: Path) -> Path:
    resolved_root = root.expanduser().resolve()
    resolved = path.expanduser().resolve()
    try:
        rel = resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise AcceptanceError(f"path is not contained in {resolved_root}: {path}") from exc
    if ".." in rel.parts:
        raise AcceptanceError(f"path is not contained in {resolved_root}: {path}")
    if not resolved.is_file():
        raise AcceptanceError(f"missing repository file: {rel.as_posix()}")
    return resolved


def _dsn_database(dsn: str) -> str:
    parsed = urlparse(dsn.strip())
    return unquote(parsed.path or "").lstrip("/").split("/")[0]


def assert_isolated_dsn(dsn: str) -> None:
    parsed = urlparse(dsn.strip())
    database = _dsn_database(dsn)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"postgres", "postgresql"} or not database:
        raise AcceptanceError("an isolated PostgreSQL DungeonMind DSN is required")
    if parsed.port in LIVE_AUTHORITY_PORTS:
        raise AcceptanceError(
            f"live authority port {parsed.port} is forbidden; rehearsal is loopback 127.0.0.1:{REHEARSAL_PORT}"
        )
    if host not in REHEARSAL_HOSTS:
        raise AcceptanceError("rehearsal DSN host must be loopback (127.0.0.1, localhost, or ::1)")
    if parsed.port != REHEARSAL_PORT:
        raise AcceptanceError(f"rehearsal DSN must use loopback port {REHEARSAL_PORT}")
    if database not in ALLOWED_REHEARSAL_DATABASES:
        raise AcceptanceError(
            "rehearsal database must be exactly dmb_full_corpus_openai or dmb_full_corpus_deepseek"
        )


def assert_arm_authority(arm: str, dsn: str) -> None:
    expected = ARM_DATABASE.get(arm)
    if expected is None:
        raise AcceptanceError(f"unknown arm {arm!r}")
    assert_isolated_dsn(dsn)
    database = _dsn_database(dsn)
    if database != expected:
        raise AcceptanceError(f"arm {arm} must use rehearsal database {expected}, not {database}")


def assert_notebook_checkout(notebook_root: Path) -> dict[str, str]:
    head = git_head(notebook_root)
    if head != NOTEBOOK_HEAD:
        raise AcceptanceError(
            f"notebook HEAD must be {NOTEBOOK_HEAD}, got {head}"
        )
    status = git_status_porcelain(notebook_root)
    if status.strip():
        raise AcceptanceError("notebook working tree is dirty")
    return {"notebook_head": head, "notebook_status": ""}


def assert_production_checkout(production_root: Path) -> dict[str, str]:
    head = git_head(production_root)
    if not git_is_ancestor(production_root, GENESIS_MERGE_SHA, head):
        raise AcceptanceError(
            f"production checkout {head} does not contain genesis merge {GENESIS_MERGE_SHA}"
        )
    return {"production_head": head, "genesis_predecessor_merge_sha": GENESIS_MERGE_SHA}


def manifest_path(notebook_root: Path) -> Path:
    return _contained_file(notebook_root, notebook_root / MANIFEST_REL)


def load_acceptance_manifest(notebook_root: Path) -> dict[str, Any]:
    path = manifest_path(notebook_root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("reviewed_notebook_head") != CANDIDATE_FROZEN_HEAD:
        raise AcceptanceError("acceptance manifest head does not match candidate freeze d6e2599")
    if payload.get("experiment_claim") != EXPERIMENT_CLAIM:
        raise AcceptanceError("acceptance manifest experiment claim drifted")
    if payload.get("corpus") != "frozen_42_session":
        raise AcceptanceError("acceptance manifest corpus is not the frozen 42-session set")
    return payload


def inspect_notebook_arm_rows(
    arm: str,
    *,
    notebook_root: Path,
    frozen_sessions: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if arm not in ARMS:
        raise AcceptanceError(f"unknown arm {arm!r}")
    if len(frozen_sessions) != EXPECTED_SESSION_COUNT:
        raise AcceptanceError(f"frozen 42-session seal mismatch for {arm}: frozen={len(frozen_sessions)}")
    expected_jobs = jobs()
    rows: list[dict[str, Any]] = []
    for exp, (campaign, session) in zip(frozen_sessions, expected_jobs, strict=True):
        if (exp.get("campaign"), int(exp.get("session") or 0)) != (campaign, session):
            raise AcceptanceError(f"frozen session order drifted for {arm}")
        if session in {26, 27}:
            raise AcceptanceError("C2 S26/S27 are outside the frozen experiment")
        candidate = _contained_file(notebook_root, notebook_root / str(exp["candidate_path"]))
        notebook_source = _contained_file(notebook_root, notebook_root / str(exp["source_path"]))
        try:
            graph = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AcceptanceError(f"unreadable candidate {candidate}") from exc
        if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
            raise AcceptanceError(f"invalid candidate graph {candidate}")
        artifact_ids = list(graph.get("source_artifact_ids") or [])
        if len(artifact_ids) != 1:
            raise AcceptanceError(f"candidate must have exactly one source artifact: {candidate}")
        rows.append(
            {
                "campaign": campaign,
                "session": session,
                "candidate_sha256": _digest_file(candidate),
                "source_sha256": _digest_file(notebook_source),
                "source_artifact_id": str(artifact_ids[0]),
                "candidate_path": Path(str(exp["candidate_path"])).as_posix(),
                "source_path": Path(str(exp["source_path"])).as_posix(),
            }
        )
    return rows


def verify_frozen_inputs(
    arm: str,
    *,
    notebook_root: Path,
    production_root: Path,
) -> dict[str, Any]:
    frozen = load_acceptance_manifest(notebook_root)
    arm_payload = (frozen.get("arms") or {}).get(arm)
    if not isinstance(arm_payload, dict):
        raise AcceptanceError(f"frozen acceptance manifest is missing arm {arm!r}")
    expected = list(arm_payload.get("sessions") or [])
    live = inspect_notebook_arm_rows(arm, notebook_root=notebook_root, frozen_sessions=expected)
    if len(live) != EXPECTED_SESSION_COUNT:
        raise AcceptanceError(f"frozen 42-session seal mismatch for {arm}: live={len(live)}")
    for got, exp in zip(live, expected, strict=True):
        for key in _SEAL_COMPARE_KEYS:
            if got.get(key) != exp.get(key):
                raise AcceptanceError(
                    f"frozen {key} drift for {got.get('campaign')}/session-{int(got.get('session') or 0):02d}: "
                    f"expected {exp.get(key)!r} live {got.get(key)!r}"
                )
        production_source = _contained_file(production_root, production_root / str(exp["source_path"]))
        production_digest = _digest_file(production_source)
        if production_digest != str(exp["source_sha256"]):
            raise AcceptanceError(
                f"current-main source hash mismatch for {exp.get('campaign')}/session-{int(exp.get('session') or 0):02d}"
            )
    return {
        "schema": "dmb_frozen_42_session_candidate_seal_v1",
        "arm": arm,
        "candidate_count": EXPECTED_SESSION_COUNT,
        "model_calls": 0,
        "notebook_head": NOTEBOOK_HEAD,
        "candidate_frozen_head": CANDIDATE_FROZEN_HEAD,
        "acceptance_manifest_sha256": _digest_file(manifest_path(notebook_root)),
        "experiment_claim": EXPERIMENT_CLAIM,
        "sessions": expected,
    }


def runner_owns_forbidden_imports(runner_path: Path | None = None) -> list[str]:
    path = runner_path or Path(__file__).resolve()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        for name in names:
            lowered = name.lower()
            if any(token in lowered for token in FORBIDDEN_IMPORT_SUBSTRINGS):
                found.append(name)
    return found


def register_verified_historical_recap(
    root: Path,
    *,
    campaign_id: str,
    session_id: str,
    recap_path: Path,
    expected_content_sha256: str,
    historical_source_artifact_id: str,
) -> Any:
    """Acceptance-only alias after freeze verification.  Not a product creator."""
    from apps.live_control_server.services.source_artifact_registry import (
        _upsert_source_artifact,
        create_recap_source_artifact,
        load_registered_source_artifact_text,
    )

    historical = (historical_source_artifact_id or "").strip()
    if not historical:
        raise AcceptanceError("frozen historical source_artifact_id is required")
    canonical = create_recap_source_artifact(
        root,
        campaign_id=campaign_id,
        session_id=session_id,
        recap_path=recap_path,
        expected_content_sha256=expected_content_sha256,
    )
    expected = expected_content_sha256.removeprefix("sha256:").strip().lower()
    if canonical.content_sha256 != expected:
        raise AcceptanceError("canonical recap digest does not match frozen source digest")
    if canonical.source_artifact_id == historical:
        return canonical
    _artifact, content = load_registered_source_artifact_text(root, canonical.source_artifact_id)
    aliased = canonical.model_copy(
        update={
            "source_artifact_id": historical,
            "lineage": {
                **dict(canonical.lineage or {}),
                "canonical_derived_source_artifact_id": canonical.source_artifact_id,
                "notebook_historical_source_artifact_id": historical,
                "acceptance_notebook": "pr715-frozen-42-session",
            },
        }
    )
    return _upsert_source_artifact(root, candidate=aliased, content=content)


def bind_artifact_world(artifact: Any, *, world_id: str) -> Any:
    """Acceptance-local World binding. Production recap creator stays world-neutral."""
    bound = str(world_id or "").strip()
    if not bound:
        raise AcceptanceError("world_id is required before source admission")
    current = str(getattr(artifact, "world_id", None) or "").strip()
    if current and current != bound:
        raise AcceptanceError(
            f"source artifact world_id {current!r} does not match derived world {bound!r}"
        )
    if hasattr(artifact, "model_copy"):
        return artifact.model_copy(update={"world_id": bound})
    return artifact


def inspect_authority_counts(dsn: str, world_id: str) -> dict[str, int]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        def count(sql_text: str, params: tuple = (world_id,)) -> int:
            row = conn.execute(sql_text, params).fetchone()
            return int(row[0])

        return {
            "heads": count("SELECT count(*) FROM dungeonmind.world_graph_heads WHERE world_id = %s"),
            "revisions": count("SELECT count(*) FROM dungeonmind.graph_revisions WHERE world_id = %s"),
            "receipts": count(
                "SELECT count(*) FROM dungeonmind.reviewed_world_initializations WHERE world_id = %s"
            ),
            "contributions": count(
                "SELECT count(*) FROM dungeonmind.graph_contributions WHERE world_id = %s"
            ),
            "artifacts": count("SELECT count(*) FROM dungeonmind.source_artifacts WHERE world_id = %s"),
            "revisions_src": count(
                "SELECT count(*) FROM dungeonmind.source_revisions r "
                "JOIN dungeonmind.source_artifacts a "
                "ON a.source_artifact_id = r.source_artifact_id "
                "WHERE a.world_id = %s"
            ),
            "adoptions": count(
                "SELECT count(*) FROM dungeonmind.existing_world_adoptions WHERE world_id = %s"
            ),
        }


def assert_pristine_authority(dsn: str, world_id: str) -> dict[str, int]:
    counts = inspect_authority_counts(dsn, world_id)
    dirty = {key: value for key, value in counts.items() if value}
    if dirty:
        raise AcceptanceError(f"rehearsal authority {world_id} is not pristine: {dirty}")
    return counts


def _endpoint_kinds(context: Any, candidate: Mapping[str, Any]) -> dict[str, str]:
    kinds = {oid: obj.kind for oid, obj in context.objects.items() if obj.kind}
    for node in candidate.get("nodes") or []:
        node_id = str(node.get("id") or node.get("node_id") or "")
        kind = str(node.get("type") or node.get("node_type") or node.get("kind") or "")
        if (node.get("corpus_ref") or {}).get("type") == "pc" or kind == "pc":
            kind = "player_character"
        elif kind == "character":
            kind = "npc"
        if node_id and kind:
            kinds[node_id] = kind
    return kinds


def _edge_rejection_reason(
    *,
    predicate: str,
    edge_id: str,
    subject_kind: str | None,
    target_kind: str | None,
) -> str | None:
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
        CURRENT_V5_TARGET,
        edge_has_reverse_direction_qualifier_v4,
        predicate_allowed_endpoints,
        resolve_buddy_predicate_mapping_v4,
    )

    mapping = resolve_buddy_predicate_mapping_v4(predicate)
    if mapping is None or not mapping[0]:
        return "unmapped_predicate"
    dm_predicate, reverse_endpoints = mapping
    if edge_id and edge_has_reverse_direction_qualifier_v4(buddy_predicate=predicate, edge_id=edge_id):
        return "reverse_direction_qualifier"
    allowed = predicate_allowed_endpoints(dm_predicate, CURRENT_V5_TARGET.world_object_loader())
    if allowed is None:
        return "vocabulary_missing_predicate"
    subject_kinds, object_kinds = allowed
    src_dm = CURRENT_V5_TARGET.buddy_to_dm_kind.get(subject_kind or "")
    tgt_dm = CURRENT_V5_TARGET.buddy_to_dm_kind.get(target_kind or "")
    admit_src, admit_tgt = (tgt_dm, src_dm) if reverse_endpoints else (src_dm, tgt_dm)
    if (
        admit_src is None
        or admit_tgt is None
        or admit_src not in subject_kinds
        or admit_tgt not in object_kinds
    ):
        return "endpoint_kind_not_admitted"
    return None


def accepted_proposals(package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Read v2 flat or v3 sliced sealed proposals. Never invent identity."""
    from graph_memory.extract_promote_proposal import contribution_slices_from_effect

    proposals: dict[str, dict[str, Any]] = {}
    for part in contribution_slices_from_effect(package.get("effect") or {}):
        for item in part.get("accepted_proposals") or []:
            if not isinstance(item, Mapping):
                continue
            assertion_id = str(item.get("assertion_id") or "")
            if assertion_id:
                proposals[assertion_id] = dict(item)
    return proposals


def _assertion_value(assertion: Mapping[str, Any]) -> dict[str, Any]:
    raw_value = assertion.get("value")
    if isinstance(raw_value, str) and raw_value:
        try:
            parsed = json.loads(raw_value)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    if isinstance(raw_value, dict):
        return raw_value
    return {}


def _buddy_kind(kind: str) -> str:
    cleaned = str(kind or "").strip()
    if cleaned in {"pc", "player_character"}:
        return "player_character"
    if cleaned == "character":
        return "npc"
    return cleaned


def _node_rejection_reason(assertion: Mapping[str, Any]) -> str | None:
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import CURRENT_V5_TARGET

    value = _assertion_value(assertion)
    buddy_kind = _buddy_kind(str(value.get("kind") or assertion.get("node_type") or ""))
    if not buddy_kind:
        return "unmapped_kind"
    if CURRENT_V5_TARGET.buddy_to_dm_kind.get(buddy_kind) is None:
        return "unmapped_kind"
    return None


def select_confirmable_assertions(
    review_items: list[Mapping[str, Any]],
    *,
    assertions: Mapping[str, Mapping[str, Any]],
    context: Any,
    candidate: Mapping[str, Any],
) -> tuple[list[str], dict[str, int], int]:
    """Apply current production qualification at the selection boundary."""
    selectable: list[str] = []
    rejected: dict[str, int] = {}
    published_edges = 0
    existing_ids = set(getattr(context, "objects", {}) or {})
    kinds = _endpoint_kinds(context, candidate)
    for item in review_items:
        if not item.get("selectable"):
            continue
        sid = str(item.get("slice_qualified_id") or "")
        kind = str(item.get("kind") or "").lower()
        assertion = assertions.get(item.get("assertion_id")) or {}
        if kind in {"edge", "relationship"}:
            raw_value = assertion.get("value")
            if isinstance(raw_value, str) and raw_value:
                try:
                    parsed_value = json.loads(raw_value)
                except ValueError:
                    parsed_value = {}
            elif isinstance(raw_value, dict):
                parsed_value = raw_value
            else:
                parsed_value = {}
            reason = _edge_rejection_reason(
                predicate=str(assertion.get("predicate") or ""),
                edge_id=str(parsed_value.get("edge_id") or ""),
                subject_kind=kinds.get(
                    str(assertion.get("subject_node_id") or assertion.get("subject_object_id") or "")
                ),
                target_kind=kinds.get(
                    str(assertion.get("target_node_id") or assertion.get("object_object_id") or "")
                ),
            )
            if reason is None:
                selectable.append(sid)
                published_edges += 1
            else:
                rejected[reason] = rejected.get(reason, 0) + 1
            continue
        oid = str(assertion.get("subject_node_id") or assertion.get("subject_object_id") or "")
        outcome = str(
            item.get("identity_outcome") or assertion.get("identity_resolution_outcome") or ""
        )
        if oid in existing_ids and outcome in {"created_new", "provisional_new", ""}:
            rejected["parent_binding_mismatch"] = rejected.get("parent_binding_mismatch", 0) + 1
            continue
        if outcome == "resolved_existing" and oid not in existing_ids:
            rejected["parent_binding_mismatch"] = rejected.get("parent_binding_mismatch", 0) + 1
            continue
        kind_reason = _node_rejection_reason(assertion)
        if kind_reason is not None:
            rejected[kind_reason] = rejected.get(kind_reason, 0) + 1
            continue
        selectable.append(sid)
    return selectable, rejected, published_edges


def _prepare_extract_promote(*args: Any, **kwargs: Any) -> Any:
    from graph_memory.extract_promote_ops import prepare_extract_promote

    return prepare_extract_promote(*args, **kwargs)


def _load_mutation_context(world_id: str, *, database_url: str, revision_pin: str | None = None) -> Any:
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    return world_graph_writes.load_production_mutation_context(
        world_id, revision_pin=revision_pin, database_url=database_url
    )


def genesis_prepare(*, world_id: str, production_root: Path, dsn: str) -> Any:
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )
    from apps.live_control_server.models.recap_world_genesis import RecapWorldGenesisPrepareRequest
    from apps.live_control_server.services.recap_world_genesis import prepare_recap_world_genesis

    return prepare_recap_world_genesis(
        RecapWorldGenesisPrepareRequest(
            world_id=world_id,
            campaign_id=GENESIS_CAMPAIGN,
            baseline_roster_key=GENESIS_ROSTER_KEY,
            requested_by=GENESIS_ACTOR,
        ),
        repo=production_root,
        authority=DungeonMindWorldGraphInitializationAdapter(database_url=dsn),
    )


def genesis_confirm(*, plan: Any, production_root: Path, dsn: str) -> Any:
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )
    from apps.live_control_server.models.recap_world_genesis import RecapWorldGenesisConfirmRequest
    from apps.live_control_server.services.recap_world_genesis import confirm_recap_world_genesis

    return confirm_recap_world_genesis(
        RecapWorldGenesisConfirmRequest(plan=plan, confirming_principal=GENESIS_ACTOR),
        repo=production_root,
        authority=DungeonMindWorldGraphInitializationAdapter(database_url=dsn),
    )


def _receipt_summary(receipt: Any) -> dict[str, Any]:
    payload = receipt.model_dump(mode="json") if hasattr(receipt, "model_dump") else dict(receipt)
    return {
        "world_id": payload.get("world_id"),
        "source_domain_key": payload.get("source_domain_key"),
        "source_revision_id": payload.get("source_revision_id"),
        "published_revision_id": payload.get("published_revision_id"),
        "parent_revision_id": payload.get("parent_revision_id"),
        "pc_object_ids": list(payload.get("pc_object_ids") or []),
        "outcome": payload.get("outcome"),
        "confirmed_by": payload.get("confirmed_by"),
    }


def run_genesis(*, arm: str, dsn: str, production_root: Path) -> dict[str, Any]:
    world_id = derived_world_id(arm)
    before = assert_pristine_authority(dsn, world_id)
    plan = genesis_prepare(world_id=world_id, production_root=production_root, dsn=dsn)
    after_prepare = inspect_authority_counts(dsn, world_id)
    if after_prepare != before:
        raise AcceptanceError("genesis prepare was not inert")
    if tuple(plan.pc_object_ids) != CANONICAL_PC_OBJECT_IDS:
        raise AcceptanceError("genesis PC object IDs drifted from the canonical C1 roster")
    if tuple(plan.pc_identity_keys) != CANONICAL_PC_IDENTITY_KEYS:
        raise AcceptanceError("genesis PC identity keys drifted from the canonical C1 roster")
    receipt = genesis_confirm(plan=plan, production_root=production_root, dsn=dsn)
    if receipt.parent_revision_id is not None:
        raise AcceptanceError("genesis D0 parent_revision_id must be null")
    if receipt.source_domain_key != "party_registry":
        raise AcceptanceError("genesis source_domain_key must be party_registry")
    d0 = receipt.published_revision_id
    context = _load_mutation_context(world_id, database_url=dsn, revision_pin=d0)
    if set(receipt.pc_object_ids) != set(CANONICAL_PC_OBJECT_IDS):
        raise AcceptanceError("native genesis receipt is missing the six canonical PCs")
    missing = set(CANONICAL_PC_OBJECT_IDS) - set(context.objects)
    if missing:
        raise AcceptanceError(f"native D0 is missing canonical PCs: {sorted(missing)}")
    if context.revision_id != d0 or context.head_revision_id != d0:
        raise AcceptanceError("native mutation context head is not exact D0")
    return {
        "arm": arm,
        "world_id": world_id,
        "prepare_inert": True,
        "pristine_before": before,
        "plan": {
            "plan_id": plan.plan_id,
            "source_revision_id": plan.source_revision_id,
            "pc_object_ids": list(plan.pc_object_ids),
            "pc_identity_keys": list(plan.pc_identity_keys),
            "canonical_pc_labels": sorted(CANONICAL_PC_LABELS),
            "baseline_roster_key": plan.baseline_roster_key,
        },
        "receipt": _receipt_summary(receipt),
        "d0": d0,
    }


def sanitize_candidate_for_load(
    candidate: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    """Drop frozen nodes that current production load validation rejects.

    Digest proof stays on the original file bytes. This only rewrites the
    in-memory payload so `prepare_extract_promote` can consume DeepSeek graphs
    that contain duplicate node IDs or node_types outside NODE_TYPES.
    """
    from graph_memory.candidate_graph_preview import NODE_TYPES

    payload = json.loads(json.dumps(candidate))
    rejections: dict[str, int] = {}
    kept_nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node in payload.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("node_id") or node.get("id") or "")
        node_type = str(node.get("node_type") or node.get("kind") or "")
        if not node_id:
            rejections["missing_node_id"] = rejections.get("missing_node_id", 0) + 1
            continue
        if node_id in seen:
            rejections["duplicate_node_id"] = rejections.get("duplicate_node_id", 0) + 1
            continue
        if node_type not in NODE_TYPES:
            rejections["invalid_node_type"] = rejections.get("invalid_node_type", 0) + 1
            continue
        seen.add(node_id)
        kept_nodes.append(node)
    payload["nodes"] = kept_nodes
    kept_ids = {
        str(node.get("node_id") or node.get("id") or "") for node in kept_nodes
    }

    kept_edges: list[dict[str, Any]] = []
    for edge in payload.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("from_node_id") or edge.get("source") or "")
        tgt = str(edge.get("to_node_id") or edge.get("target") or "")
        if src not in kept_ids or tgt not in kept_ids:
            rejections["missing_edge_endpoint"] = rejections.get("missing_edge_endpoint", 0) + 1
            continue
        kept_edges.append(edge)
    payload["edges"] = kept_edges

    for beat in payload.get("beats") or []:
        if not isinstance(beat, dict):
            continue
        for key in ("involved_node_ids", "unresolved_thread_node_ids"):
            original = list(beat.get(key) or [])
            kept = [item for item in original if str(item) in kept_ids]
            dropped = len(original) - len(kept)
            if dropped:
                rejections["missing_beat_node"] = rejections.get("missing_beat_node", 0) + dropped
            beat[key] = kept

    write_targets = kept_ids | {
        str(edge.get("edge_id") or "") for edge in kept_edges
    } | {
        str(beat.get("beat_id") or "") for beat in (payload.get("beats") or []) if isinstance(beat, dict)
    }
    kept_writes: list[dict[str, Any]] = []
    for write in payload.get("proposed_writes") or []:
        if not isinstance(write, dict):
            continue
        target_id = str(write.get("target_id") or "")
        if target_id and target_id not in write_targets:
            rejections["missing_write_target"] = rejections.get("missing_write_target", 0) + 1
            continue
        kept_writes.append(write)
    payload["proposed_writes"] = kept_writes
    return payload, rejections


def publish_session(
    *,
    dsn: str,
    world_id: str,
    seal: Mapping[str, Any],
    expected_parent: str,
    notebook_root: Path,
    production_root: Path,
) -> dict[str, Any]:
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )
    from apps.live_control_server.ports.world_graph_source_admission import WorldGraphSourceAdmissionRequest

    candidate_file = _contained_file(notebook_root, notebook_root / str(seal["candidate_path"]))
    recap = _contained_file(production_root, production_root / str(seal["source_path"]))
    if _digest_file(candidate_file) != str(seal["candidate_sha256"]):
        raise AcceptanceError("candidate digest drift at publication")
    if _digest_file(recap) != str(seal["source_sha256"]):
        raise AcceptanceError("source digest drift at publication")
    original_candidate = json.loads(candidate_file.read_text(encoding="utf-8"))
    candidate, load_rejections = sanitize_candidate_for_load(original_candidate)
    context = _load_mutation_context(world_id, database_url=dsn)
    if context.revision_id != expected_parent or context.head_revision_id != expected_parent:
        raise AcceptanceError("chronology drift: current authority head does not equal receipt parent")
    artifact_ids = list(candidate.get("source_artifact_ids") or [])
    if len(artifact_ids) != 1:
        raise AcceptanceError("candidate must have exactly one source artifact")
    if str(artifact_ids[0]) != str(seal["source_artifact_id"]):
        raise AcceptanceError("candidate artifact identity drift")
    artifact = register_verified_historical_recap(
        production_root,
        campaign_id=str(seal["campaign"]),
        session_id=f"session-{int(seal['session'])}",
        recap_path=recap,
        expected_content_sha256=str(seal["source_sha256"]),
        historical_source_artifact_id=str(seal["source_artifact_id"]),
    )
    artifact = bind_artifact_world(artifact, world_id=world_id)
    admitted = DungeonMindWorldGraphSourceAdmissionAdapter(database_url=dsn).prove_or_admit(
        WorldGraphSourceAdmissionRequest(
            world_id=world_id,
            campaign_id=str(seal["campaign"]),
            source_artifact=artifact,
            source_revision_token=f"sha256:{seal['source_sha256']}",
            source_uri=artifact.uri,
        )
    )
    prepared = _prepare_extract_promote(
        candidate_graph=candidate,
        source_uri=artifact.uri,
        source_revision_id=f"sha256:{seal['source_sha256']}",
        prepared_by=GENESIS_ACTOR,
        world_id=world_id,
        source_artifact_id=artifact.source_artifact_id,
        campaign_scope=str(seal["campaign"]),
        repo_root=production_root,
        mutation_context=context,
    )
    if str(getattr(prepared, "parent_revision_id", "") or "") not in {"", expected_parent}:
        if str(prepared.parent_revision_id) != expected_parent:
            raise AcceptanceError("prepared package parent is not the expected parent")
    package = world_graph_writes.bind_identity_ledger_to_package(prepared.review_package, context)
    assertions = accepted_proposals(package)
    selectable, rejected, published_edges = select_confirmable_assertions(
        prepared.review_items,
        assertions=assertions,
        context=context,
        candidate=candidate,
    )
    if not selectable:
        raise AcceptanceError("governed preparation produced no publishable assertions")
    request = type("ConfirmRequest", (), {"review_package": package, "assertion_ids": selectable})()
    confirmed = world_graph_writes.confirm_extract_promote_via_dungeonmind(
        request,
        database_url=dsn,
        confirming_principal=GENESIS_ACTOR,
        assertion_ids=tuple(selectable),
        repo_root=production_root,
    )
    child = str(confirmed.get("committed_revision_id") or "")
    parent = str(confirmed.get("parent_revision_id") or "")
    if not child:
        raise AcceptanceError("governed confirmation returned no child revision")
    if parent != expected_parent:
        raise AcceptanceError("committed child parent_revision_id does not equal expected parent")
    return {
        "parent_world_revision": expected_parent,
        "child_world_revision": child,
        "source_admission": {
            "source_artifact_id": admitted.source_artifact_id,
            "source_revision_id": admitted.source_revision_id,
            "content_sha256": admitted.content_sha256,
        },
        "candidate_nodes": len(original_candidate.get("nodes") or []),
        "candidate_relationships": len(original_candidate.get("edges") or []),
        "published_relationships": published_edges,
        "relationship_rejections": rejected,
        "candidate_load_rejections": load_rejections,
        "accepted_assertion_count": len(selectable),
        "model_calls": 0,
        "publication_mode": "governed_extract_promote",
    }


def _model_credentials_present() -> list[str]:
    return [key for key in MODEL_ENV_KEYS if os.environ.get(key)]


def run_arm(
    *,
    arm: str,
    dsn: str,
    notebook_root: Path,
    production_root: Path,
    output: Path,
) -> dict[str, Any]:
    assert_arm_authority(arm, dsn)
    notebook = assert_notebook_checkout(notebook_root)
    production = assert_production_checkout(production_root)
    seal = verify_frozen_inputs(arm, notebook_root=notebook_root, production_root=production_root)
    world_id = derived_world_id(arm)
    _write(output / "SEAL.json", seal)
    genesis = run_genesis(arm=arm, dsn=dsn, production_root=production_root)
    parent = str(genesis["d0"])
    receipts: list[dict[str, Any]] = []
    for row in seal["sessions"]:
        start = time.perf_counter()
        receipt = {
            **row,
            **publish_session(
                dsn=dsn,
                world_id=world_id,
                seal=row,
                expected_parent=parent,
                notebook_root=notebook_root,
                production_root=production_root,
            ),
            "arm": arm,
            "world_id": world_id,
            "wall_seconds": round(time.perf_counter() - start, 3),
            "errors": [],
        }
        if int(row["session"]) == 1 and row["campaign"] == "longmont-c1":
            if receipt["parent_world_revision"] != genesis["d0"]:
                raise AcceptanceError("C1 S1 is not an ordinary child of D0")
        parent = receipt["child_world_revision"]
        receipts.append(receipt)
        _write(output / "receipts" / f"{row['campaign']}-session-{int(row['session']):02d}.json", receipt)
    terminal = _load_mutation_context(world_id, database_url=dsn)
    if terminal.head_revision_id != parent or terminal.revision_id != parent:
        raise AcceptanceError("native terminal head is not the final receipt child")
    manifest = {
        "schema": "dmb_frozen_42_session_acceptance_arm_v1",
        "generated_at": _now(),
        "arm": arm,
        "database": ARM_DATABASE[arm],
        "world_id": world_id,
        "model_calls": 0,
        "candidate_generation": "frozen",
        "candidate_regeneration": False,
        "notebook_head": notebook["notebook_head"],
        "production_head": production["production_head"],
        "genesis_predecessor_merge_sha": production["genesis_predecessor_merge_sha"],
        "candidate_frozen_head": CANDIDATE_FROZEN_HEAD,
        "acceptance_manifest_sha256": seal["acceptance_manifest_sha256"],
        "genesis": genesis,
        "d0": genesis["d0"],
        "c1_s1_parent": receipts[0]["parent_world_revision"] if receipts else None,
        "c1_s1_child": receipts[0]["child_world_revision"] if receipts else None,
        "baseline_revision": genesis["d0"],
        "terminal_revision": parent,
        "receipt_count": len(receipts),
        "experiment_claim": EXPERIMENT_CLAIM,
        "semantic_benchmark": SEMANTIC_BENCHMARK_DISCOVERY,
        "model_credentials_present": _model_credentials_present(),
        "receipts": receipts,
    }
    _write(output / "MANIFEST.json", manifest)
    return manifest


def verify_inputs(*, notebook_root: Path, production_root: Path, arm: str | None = None) -> dict[str, Any]:
    notebook = assert_notebook_checkout(notebook_root)
    production = assert_production_checkout(production_root)
    arms = ARMS if arm is None else (arm,)
    seals = {
        name: verify_frozen_inputs(name, notebook_root=notebook_root, production_root=production_root)
        for name in arms
    }
    return {
        "notebook": notebook,
        "production": production,
        "forbidden_imports": runner_owns_forbidden_imports(),
        "semantic_benchmark": SEMANTIC_BENCHMARK_DISCOVERY,
        "seals": seals,
        "model_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook-root", type=Path, required=True)
    parser.add_argument("--production-root", type=Path, default=ROOT)
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--dsn", default=os.environ.get("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"))
    parser.add_argument("--verify-inputs", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "out" / "frozen_42_session_acceptance")
    args = parser.parse_args()
    notebook_root = args.notebook_root.expanduser().resolve()
    production_root = args.production_root.expanduser().resolve()
    if args.verify_inputs and not args.run:
        print(json.dumps(verify_inputs(notebook_root=notebook_root, production_root=production_root, arm=args.arm), indent=2, default=str))
        return 0
    if not args.run:
        raise SystemExit("specify --verify-inputs or --run")
    if not args.arm or not args.dsn:
        raise SystemExit("--arm and --dsn are required for --run")
    present = _model_credentials_present()
    if present:
        raise AcceptanceError(f"model credentials must be removed before replay: {present}")
    result = run_arm(
        arm=args.arm,
        dsn=args.dsn,
        notebook_root=notebook_root,
        production_root=production_root,
        output=args.output / args.arm,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
