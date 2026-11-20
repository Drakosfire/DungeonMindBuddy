"""Bounded continuation of sealed C1S2 or checkpoint38; never initializes a World.

This command is not an automatic recovery engine. An incomplete output directory,
an ambiguous confirm, or an unexpected head is a STOP requiring steward review.
Only an already COMPLETE exact run may be repeated, read-only.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
from urllib.parse import unquote, urlparse

from evals.graph_memory_layer import (
    run_current_corpus_candidate_replay_acceptance as replay,
)

GENESIS = "rev:77fdd25fc46a0dc896a65b679f7dd68f"
PREFIX_HEAD = "rev:43435e3a237b2e1e5836368b61619895"
PREFIX_CHILDREN = ("rev:4afce1b08776882caf359b35f9bbafa7", PREFIX_HEAD)
GENESIS_ASSERTION_IDS = (
    "assertion:1d2f6746c99facd6",
    "assertion:1d4bbe45be45be61",
    "assertion:5b239f777885125e",
    "assertion:6430c3767d00276e",
    "assertion:8e8108af162f4d05",
    "assertion:d9f496190ccf85fa",
)
GENESIS_CONTRIBUTION_ID = "contribution:d474e4091cdf24f8"
GENESIS_CONTRIBUTION_SHA256 = (
    "70d597237dcb3644e9a35c9f87a04c1d0d022426962770cccea165371e804362"
)
CHECKPOINT_REPORT_SHA256 = (
    "55206aeb0384b661d1fdeee7981b27a73138b1df11908185b50a8dbaaa807632"
)
CHECKPOINT_LEDGER_SHA256 = (
    "e018212987fd967632874aec2c477ad6aa4fc617aecdbce78110bd4103f4abcd"
)
CHECKPOINT38_HEAD = "rev:dfe5ad1c967a365d3f7748b38faa1a9c"
CHECKPOINT38_REPORT_SHA256 = (
    "a6ca378e8055862e41c003808c10a5cf04710d5afd5576a05806636bfe3696d2"
)
CHECKPOINT38_S22_ORDINAL = 39
CHECKPOINT38_S22_CAMPAIGN_ID = "longmont-c2"
CHECKPOINT38_S22_SESSION_ID = "session-22"
CHECKPOINT38_S22_CANDIDATE_SHA256 = (
    "143e1f9df81a85e47037651ecb70c7b12bc3347dc220a6964f1a1a66f500e726"
)
CHECKPOINT38_S22_CANDIDATE_NODE_ID = "node:thrin-branchborn"
CHECKPOINT38_S22_CORPUS_REF_TYPE = "npc"
CHECKPOINT38_S22_CORPUS_REF_KEY = "thrin_branchborn"
CHECKPOINT38_S22_TARGET_OBJECT_ID = "npc_thrin"
CHECKPOINT38_PRIVATE_ROOT = Path(
    "/home/drakosfire/.local/state/dungeonmindbuddy/recovery/full-corpus-20261008"
)
EXECUTION_PACKET_SCHEMA = "dmb_checkpoint38_six_session_execution_v1"
MIN_BACKUP_FREE_BYTES = 2 * 1024**3


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise replay.ReplayStop(message, boundary="retained_prefix_integrity")


def _source_token(row: dict[str, Any]) -> str:
    # The original accepted replay ledger seals the token in source_admission;
    # continuation rows also record it at top level. Do not rewrite the prefix.
    return str(
        row.get("source_revision_id")
        or (row.get("source_admission") or {}).get("buddy_source_revision_id")
        or ""
    )


def _checkpoint(root: Path, entries: tuple[Any, ...]) -> list[dict[str, Any]]:
    report_path, ledger_path = root / "replay_report.json", root / "replay_ledger.json"
    _require(
        replay._sha256_file(report_path) == CHECKPOINT_REPORT_SHA256,
        "retained report digest mismatch",
    )
    _require(
        replay._sha256_file(ledger_path) == CHECKPOINT_LEDGER_SHA256,
        "retained ledger digest mismatch",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))["sessions"]
    _require(
        report["replay_acceptance"] == "HOLD"
        and report["last_good_head"] == PREFIX_HEAD,
        "wrong retained disposition/head",
    )
    _require(
        report["genesis_d0"] == GENESIS and report["graph_writes"] == 3,
        "wrong retained genesis/write count",
    )
    _require(
        report["replay_ledger"] == ledger and len(ledger) == 2,
        "retained prefix is not exactly two entries",
    )
    parent = GENESIS
    for entry, row, child in zip(entries[:2], ledger, PREFIX_CHILDREN, strict=True):
        _require(
            (row["campaign_id"], row["session_id"]) == entry.key,
            "retained manifest prefix differs",
        )
        _require(
            row["sealed_parent_revision"] == parent
            and row["receipt_child_revision"] == child,
            "retained lineage differs",
        )
        parent = child
    return copy.deepcopy(ledger)


def _checkpoint38(
    path: Path, original_prefix: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Accept one sealed STOP, not an arbitrary caller-selected resume point."""
    _require(
        replay._sha256_file(path) == CHECKPOINT38_REPORT_SHA256,
        "checkpoint38 report digest mismatch",
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = report["sessions"]
    _require(
        report["status"] == "STOP"
        and report["new_confirms"] == 36
        and report["last_good_head"] == CHECKPOINT38_HEAD
        and report["terminal_head"] is None
        and report["stop"]["actual_head"] == CHECKPOINT38_HEAD
        and report["stop"]["head_read_error"] is None,
        "wrong checkpoint38 STOP disposition",
    )
    _require(
        len(rows) == 38 and rows[:2] == original_prefix,
        "checkpoint38 original prefix/coverage differs",
    )
    parent = GENESIS
    for ordinal, row in enumerate(rows, 1):
        _require(
            row["ordinal"] == ordinal and row["sealed_parent_revision"] == parent,
            "checkpoint38 lineage/ordinal differs",
        )
        parent = row["receipt_child_revision"]
    _require(parent == CHECKPOINT38_HEAD, "checkpoint38 terminal lineage differs")
    return copy.deepcopy(rows)


def _selected_suffix_entries(
    entries: tuple[Any, ...], prefix_count: int
) -> tuple[Any, ...]:
    """Pure planning helper; selecting entries does not authorize their execution."""
    return tuple(entries[prefix_count:])


def _execution_packet(
    path: Path,
    *,
    manifest: Any,
    originals: tuple[Any, ...],
    source_head: str,
    decision_id: str,
    decision_sha256: str,
    output: Path,
    accepted_root: Path,
    retained_root: Path,
    checkpoint38_report: Path,
    target: tuple[str, int, str],
) -> tuple[dict[str, Any], str]:
    """Validate every frozen input before claiming an output or touching the DB."""
    try:
        raw = path.read_bytes()
        packet = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise replay.ReplayStop(
            "execution packet unavailable or invalid", boundary="execution_authority"
        ) from exc
    _require(isinstance(packet, dict), "execution packet must be an object")
    expected_keys = {
        "schema",
        "world_id",
        "checkpoint_head",
        "checkpoint_report_sha256",
        "manifest_digest",
        "source_head",
        "binding_decision_id",
        "binding_decision_sha256",
        "output",
        "accepted_root",
        "retained_root",
        "checkpoint38_report",
        "target",
        "suffix",
    }
    _require(set(packet) == expected_keys, "execution packet fields differ")
    expected = {
        "schema": EXECUTION_PACKET_SCHEMA,
        "world_id": replay.WORLD_ID,
        "checkpoint_head": CHECKPOINT38_HEAD,
        "checkpoint_report_sha256": CHECKPOINT38_REPORT_SHA256,
        "manifest_digest": manifest.digest,
        "source_head": source_head,
        "binding_decision_id": decision_id,
        "binding_decision_sha256": decision_sha256,
        "output": str(output),
        "accepted_root": str(accepted_root.resolve()),
        "retained_root": str(retained_root.resolve()),
        "checkpoint38_report": str(checkpoint38_report.resolve()),
        "target": {"host": target[0], "port": target[1], "database": target[2]},
    }
    _require(
        all(packet[key] == value for key, value in expected.items()),
        "execution packet authority/input pin differs",
    )
    rows = packet["suffix"]
    _require(
        isinstance(rows, list) and len(rows) == 6,
        "execution packet must seal six sessions",
    )
    for ordinal, (row, entry, original) in enumerate(
        zip(rows, manifest.entries[38:], originals[38:], strict=True), start=39
    ):
        _require(
            isinstance(row, dict)
            and set(row)
            == {
                "ordinal",
                "campaign_id",
                "session_id",
                "source_artifact_id",
                "source_revision_id",
                "original_sha256",
                "candidate_digest",
                "candidate_file_sha256",
            },
            "execution packet suffix fields differ",
        )
        candidate = replay._resolve_candidate_path(
            original.candidate_locator, accepted_root
        )
        _require(
            type(row["ordinal"]) is int
            and row["ordinal"] == ordinal == entry.ordinal
            and row["campaign_id"] == entry.campaign_id
            and row["session_id"] == entry.session_id
            and row["source_artifact_id"] == entry.source_artifact_id
            and row["source_revision_id"] == original.source_revision_id
            and row["original_sha256"] == entry.original_sha256
            and row["candidate_digest"] == original.candidate_digest,
            "execution packet suffix identity differs",
        )
        _require(
            isinstance(row["candidate_file_sha256"], str)
            and len(row["candidate_file_sha256"]) == 64
            and all(c in "0123456789abcdef" for c in row["candidate_file_sha256"]),
            "execution packet candidate file digest invalid",
        )
        _require(
            replay._sha256_file(candidate) == row["candidate_file_sha256"],
            "execution packet candidate file differs",
        )
    return packet, hashlib.sha256(raw).hexdigest()


def _backup_before_confirm(dsn: str, output: Path, authority: Any) -> dict[str, str]:
    """Take a new complete custom-format dump; never overwrite a prior artifact."""
    backup = output / "checkpoint38-before.dump"
    _require(not backup.exists(), "checkpoint38 backup path already claimed")
    parsed = urlparse(dsn)
    _require(
        bool(parsed.username and parsed.password),
        "checkpoint38 backup requires explicit database credentials",
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    env["PGPASSWORD"] = unquote(parsed.password)
    command = [
        "pg_dump",
        "--format=custom",
        "--no-password",
        "--host",
        parsed.hostname or "",
        "--port",
        str(parsed.port or 0),
        "--username",
        unquote(parsed.username),
        "--dbname",
        parsed.path.lstrip("/"),
        "--file",
        str(backup),
    ]
    try:
        _require(
            shutil.disk_usage(output).free >= MIN_BACKUP_FREE_BYTES,
            "insufficient free space before checkpoint38 backup",
        )
        backup.touch(mode=0o600, exist_ok=False)
        result = subprocess.run(command, env=env, capture_output=True, check=False)
        _require(
            result.returncode == 0,
            f"checkpoint38 pg_dump failed (exit {result.returncode})",
        )
        _require(backup.stat().st_size > 0, "checkpoint38 backup empty")
        verify = subprocess.run(
            ["pg_restore", "--list", str(backup)], capture_output=True, check=False
        )
        _require(
            verify.returncode == 0 and bool(verify.stdout),
            f"checkpoint38 backup archive invalid (exit {verify.returncode})",
        )
        _require(
            authority.head() == CHECKPOINT38_HEAD,
            "checkpoint38 head moved during backup",
        )
    except OSError as exc:
        raise replay.ReplayStop(
            "checkpoint38 backup failed", boundary="backup"
        ) from exc
    return {"path": str(backup), "sha256": replay._sha256_file(backup)}


class _Authority:
    """Thin read-only verification over existing typed Core repositories."""

    def __init__(self, dsn: str, bundle: Any | None = None):
        if bundle is None:
            from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
                build_direct_world_graph_read_services,
            )

            bundle = build_direct_world_graph_read_services(dsn, replay.WORLD_ID).bundle
        self.bundle = bundle

    def head(self) -> str:
        head = self.bundle.world_graph.get_head(replay.WORLD_ID)
        _require(head is not None, "retained head missing")
        return head.head_revision_id

    def genesis(self) -> None:
        receipt = self.bundle.reviewed_world_initializations.get_for_world(
            replay.WORLD_ID
        )
        stored = self.bundle.world_graph.get_revision(replay.WORLD_ID, GENESIS)
        _require(
            receipt is not None and stored is not None,
            "genesis receipt/revision missing",
        )
        _require(receipt.published_revision_id == GENESIS, "genesis receipt differs")
        _require(stored.revision.parent_revision_id is None, "genesis has a parent")
        _require(
            receipt.published_graph_payload_sha256
            == stored.revision.graph_payload_sha256,
            "genesis payload differs",
        )
        _require(
            receipt.source_plan_sha256
            == "344965c8b972f05b6e6158eeef3a57e86ab9824f5db21117c50ee114f9764376",
            "genesis plan differs",
        )
        contribution = self.bundle.contributions.get(
            replay.WORLD_ID, receipt.reviewed_contribution_id
        )
        _require(contribution is not None, "genesis contribution missing")
        from dungeonmind.contracts.contribution_review_v2 import (
            contribution_v2_payload_sha256,
        )

        _require(
            receipt.reviewed_contribution_id == GENESIS_CONTRIBUTION_ID,
            "genesis contribution identity differs",
        )
        _require(
            receipt.reviewed_contribution_sha256 == GENESIS_CONTRIBUTION_SHA256,
            "retained genesis contribution digest differs",
        )
        _require(
            contribution_v2_payload_sha256(contribution) == GENESIS_CONTRIBUTION_SHA256,
            "genesis contribution differs",
        )
        _require(
            tuple(receipt.accepted_assertion_ids) == GENESIS_ASSERTION_IDS,
            "genesis assertion identities differ",
        )
        artifact = self.bundle.sources.get_artifact(
            "artifact:party-registry:longmont-c1"
        )
        revision = self.bundle.sources.get_revision(
            "sha256:f0f49045df06f7baf61aa9c43f3739d16483eeb20ac8ed1bbf29f8209474af25"
        )
        _require(
            artifact is not None and revision is not None, "genesis source pair missing"
        )
        _require(
            revision.source_artifact_id == artifact.source_artifact_id,
            "genesis source binding differs",
        )
        _require(
            revision.content_sha256
            == "f0f49045df06f7baf61aa9c43f3739d16483eeb20ac8ed1bbf29f8209474af25",
            "genesis source bytes differ",
        )

    def publication(self, entry: Any, row: dict[str, Any]) -> dict[str, Any]:
        from dungeonmind.contracts.contribution_review_v2 import (
            contribution_v2_payload_sha256,
        )

        _require(
            (row["campaign_id"], row["session_id"]) == entry.key,
            "publication manifest identity differs",
        )
        _require(
            row["source_artifact_id"] == entry.source_artifact_id,
            "publication source differs",
        )
        review = self.bundle.contribution_reviews.get_for_plan(
            replay.WORLD_ID, row["proposal_id"]
        )
        _require(review is not None, "finalized review missing")
        record = review.record
        _require(
            record.plan_ref.source_plan_sha256 == row["proposal_digest"],
            "review command digest differs",
        )
        publication = self.bundle.finalized_review_publications.get_for_review(
            replay.WORLD_ID, record.review_id
        )
        _require(publication is not None, "publication receipt missing")
        _require(
            publication.expected_parent_revision_id == row["sealed_parent_revision"],
            "publication parent differs",
        )
        _require(
            publication.published_revision_id == row["receipt_child_revision"],
            "publication child differs",
        )
        contribution = self.bundle.contributions.get(
            replay.WORLD_ID, publication.reviewed_contribution_id
        )
        _require(contribution is not None, "reviewed contribution missing")
        _require(
            contribution == review.reviewed_contribution,
            "review/ledger contribution differs",
        )
        _require(
            contribution_v2_payload_sha256(contribution)
            == publication.reviewed_contribution_sha256,
            "contribution bytes differ",
        )
        _require(
            contribution.source_artifact_id == entry.source_artifact_id,
            "reviewed contribution source differs",
        )
        stored = self.bundle.world_graph.get_revision(
            replay.WORLD_ID, publication.published_revision_id
        )
        parent = self.bundle.world_graph.get_revision(
            replay.WORLD_ID, publication.expected_parent_revision_id
        )
        _require(
            stored is not None and parent is not None, "publication revision missing"
        )
        _require(
            stored.revision.parent_revision_id
            == publication.expected_parent_revision_id,
            "revision parent differs",
        )
        _require(
            stored.revision.graph_payload_sha256 == publication.graph_payload_sha256,
            "revision payload differs",
        )
        _require(
            parent.revision.graph_payload_sha256
            == publication.parent_graph_payload_sha256,
            "parent payload differs",
        )
        self.source(entry, _source_token(row))
        return {
            "review_id": publication.review_id,
            "operation_id": publication.operation_id,
            "reviewed_contribution_id": publication.reviewed_contribution_id,
            "reviewed_contribution_sha256": publication.reviewed_contribution_sha256,
            "graph_payload_sha256": publication.graph_payload_sha256,
        }

    def source(self, entry: Any, token: str) -> None:
        from dungeonmind.contracts.evidence import SourceDomain, SourceStatus
        from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
            catalog_aware_source_revision_ids,
        )

        artifact = self.bundle.sources.get_artifact(entry.source_artifact_id)
        _require(
            artifact is not None and artifact.world_id == replay.WORLD_ID,
            "source World differs",
        )
        _require(
            artifact.campaign_id == entry.campaign_id
            and artifact.session_id == entry.session_id,
            "source campaign/session differs",
        )
        _require(artifact.status == SourceStatus.ACTIVE, "source inactive")
        _require(
            artifact.source_domain == SourceDomain.SESSION_RECAP
            and artifact.source_domain_key == "session_recap",
            "source domain differs",
        )
        source_pair = (entry.source_artifact_id, token)
        resolved = catalog_aware_source_revision_ids(
            self.bundle.sources, replay.WORLD_ID, {source_pair}
        )
        revision = self.bundle.sources.get_revision(resolved[source_pair])
        _require(
            revision is not None
            and revision.source_artifact_id == entry.source_artifact_id,
            "source revision binding differs",
        )
        _require(
            revision.content_sha256 == entry.original_sha256,
            "source revision bytes differ",
        )

    def checkpoint38_binding(
        self,
        entry: Any,
        original: Any,
        decision_id: str,
        decision_sha256: str,
        dsn: str,
    ) -> None:
        """Verify the reviewed S22 carrier through the production authority loader.

        This is a read-only preflight. The production confirm path and Core's
        transaction fence remain responsible for revalidating publication-time
        authority; decision CLI pins alone never authorize a write.
        """
        _require(
            entry.ordinal == CHECKPOINT38_S22_ORDINAL
            and entry.campaign_id == CHECKPOINT38_S22_CAMPAIGN_ID
            and entry.session_id == CHECKPOINT38_S22_SESSION_ID
            and original.candidate_digest == CHECKPOINT38_S22_CANDIDATE_SHA256,
            "checkpoint38 first suffix candidate differs",
        )
        _require(
            isinstance(decision_id, str)
            and bool(decision_id.strip())
            and decision_id == decision_id.strip(),
            "checkpoint38 reviewed decision id is missing or padded",
        )
        _require(
            isinstance(decision_sha256, str)
            and len(decision_sha256) == 64
            and all(char in "0123456789abcdef" for char in decision_sha256),
            "checkpoint38 reviewed decision digest is invalid",
        )

        from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
            load_production_mutation_context,
        )
        from dungeonmind.contracts.identity import IdentityDecisionRecordV2
        from dungeonmind.domain.canonical import canonical_sha256

        try:
            context = load_production_mutation_context(
                replay.WORLD_ID,
                revision_pin=CHECKPOINT38_HEAD,
                database_url=dsn,
            )
        except Exception as exc:
            raise replay.ReplayStop(
                "checkpoint38 reviewed binding authority could not be loaded",
                boundary="checkpoint38_binding",
            ) from exc

        _require(
            context.world_id == replay.WORLD_ID
            and context.revision_id == CHECKPOINT38_HEAD
            and context.head_revision_id == CHECKPOINT38_HEAD,
            "checkpoint38 mutation context is not pinned to the current parent",
        )
        candidate_bindings = [
            binding
            for binding in context.reviewed_corpus_bindings
            if binding.campaign_id == CHECKPOINT38_S22_CAMPAIGN_ID
            and binding.candidate_sha256 == original.candidate_digest
        ]
        _require(
            len(candidate_bindings) == 1,
            "checkpoint38 candidate does not have exactly one reviewed binding",
        )
        binding = candidate_bindings[0]
        _require(
            binding.world_id == replay.WORLD_ID
            and binding.parent_revision_id == CHECKPOINT38_HEAD
            and binding.campaign_id == entry.campaign_id
            and binding.candidate_sha256 == original.candidate_digest
            and binding.candidate_node_id == CHECKPOINT38_S22_CANDIDATE_NODE_ID
            and binding.corpus_ref_type == CHECKPOINT38_S22_CORPUS_REF_TYPE
            and binding.corpus_ref_key == CHECKPOINT38_S22_CORPUS_REF_KEY
            and binding.target_object_id == CHECKPOINT38_S22_TARGET_OBJECT_ID
            and binding.decision_id == decision_id,
            "checkpoint38 reviewed binding differs from the frozen S22 identity",
        )

        decisions = [
            record
            for record in context.identity_ledger_records
            if record.get("decision_id") == decision_id
        ]
        _require(
            len(decisions) == 1,
            "checkpoint38 reviewed binding does not resolve one ledger decision",
        )
        try:
            decision = IdentityDecisionRecordV2.model_validate(decisions[0])
        except Exception as exc:
            raise replay.ReplayStop(
                "checkpoint38 identity decision is not a typed v2 record",
                boundary="checkpoint38_binding",
            ) from exc
        _require(
            decision.status.value == "active"
            and decision.decision_kind.value == "human_override"
            and decision.world_id == replay.WORLD_ID
            and decision.subject_object_ids == [CHECKPOINT38_S22_CANDIDATE_NODE_ID]
            and decision.target_object_ids == [binding.target_object_id]
            and decision.actor == binding.reviewer_id,
            "checkpoint38 ledger decision does not match the active human review",
        )
        _require(
            canonical_sha256(decision.model_dump(mode="json")) == decision_sha256,
            "checkpoint38 active decision digest differs from its exact pin",
        )

    def require_unclaimed(self, entry: Any, dsn: str) -> None:
        """Reject any persisted suffix contribution, including an orphan, read-only.

        Core's contribution/review ports have no source enumeration method.
        This bounded negative check does not admit or reconstruct authority.
        """
        import psycopg

        with psycopg.connect(
            dsn, options="-c default_transaction_read_only=on"
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM dungeonmind.graph_contributions "
                    "WHERE world_id = %s AND payload->>'source_artifact_id' = %s LIMIT 1",
                    (replay.WORLD_ID, entry.source_artifact_id),
                )
                _require(
                    cursor.fetchone() is None,
                    "suffix source has unaccounted contribution",
                )


def _ledger_row(
    entry: Any, original: Any, digest: str, result: dict[str, Any]
) -> dict[str, Any]:
    return {
        "ordinal": entry.ordinal,
        "campaign_id": entry.campaign_id,
        "session_id": entry.session_id,
        "candidate_digest": digest,
        "predecessor_candidate_digest": original.candidate_digest,
        "candidate_locator": original.candidate_locator,
        "source_artifact_id": entry.source_artifact_id,
        "source_revision_id": original.source_revision_id,
        "sealed_parent_revision": result["parent_revision_id"],
        "receipt_child_revision": result["child_revision_id"],
        "proposal_id": result["proposal_id"],
        "proposal_digest": result["proposal_digest"],
    }


def run_continuation(
    *,
    accepted_root: Path,
    retained_root: Path,
    output: Path,
    dsn: str,
    repo_root: Path | None = None,
    authority: Any | None = None,
    seams: replay.ReplaySeams | None = None,
    require_clean: bool = True,
    checkpoint38_report: Path | None = None,
    binding_decision_id: str | None = None,
    binding_decision_sha256: str | None = None,
    verify_checkpoint38_only: bool = False,
    verify_checkpoint38_binding_only: bool = False,
    execute_checkpoint38: bool = False,
    execution_packet: Path | None = None,
) -> dict[str, Any]:
    _require(
        not execute_checkpoint38 or checkpoint38_report is not None,
        "checkpoint38 execution requires sealed report",
    )
    _require(
        (execution_packet is not None) == execute_checkpoint38,
        "checkpoint38 execution requires explicit mode and packet",
    )
    _require(
        not execute_checkpoint38
        or not (verify_checkpoint38_only or verify_checkpoint38_binding_only),
        "checkpoint38 execution and read-only modes differ",
    )
    if checkpoint38_report is not None:
        _require(
            authority is None,
            "checkpoint38 forbids injected authority; use the production authority",
        )
        _require(
            seams is None,
            "checkpoint38 forbids injected replay seams; use production admission",
        )
    checkpoint38 = checkpoint38_report is not None
    target = replay.assert_runtime_dsn(dsn)
    root = (repo_root or replay.REPO_ROOT).resolve()
    if require_clean:
        _require(replay.git_worktree_clean(root), "continuation checkout dirty")
    manifest, originals = replay.load_accepted_cohort(
        artifact_root=accepted_root, repo_root=root
    )
    prefix = _checkpoint(retained_root, manifest.entries)
    _require(
        not verify_checkpoint38_only or checkpoint38,
        "read-only checkpoint38 verification requires sealed report",
    )
    _require(
        not verify_checkpoint38_binding_only or checkpoint38,
        "read-only binding verification requires sealed checkpoint38 report",
    )
    _require(
        not (verify_checkpoint38_only and verify_checkpoint38_binding_only),
        "checkpoint38 verification modes are mutually exclusive",
    )
    if verify_checkpoint38_only:
        _require(
            not binding_decision_id and not binding_decision_sha256,
            "prefix-only verification does not accept an unverified carrier",
        )
    else:
        _require(
            checkpoint38 == bool(binding_decision_id) == bool(binding_decision_sha256),
            "checkpoint38 requires exact binding decision identity/digest",
        )
    if checkpoint38:
        if not verify_checkpoint38_only:
            _require(
                len(binding_decision_sha256 or "") == 64
                and all(c in "0123456789abcdef" for c in binding_decision_sha256 or ""),
                "binding decision digest invalid",
            )
        prefix = _checkpoint38(checkpoint38_report, prefix)
    prefix_count = len(prefix)
    prefix_head = CHECKPOINT38_HEAD if checkpoint38 else PREFIX_HEAD
    suffix_entries = _selected_suffix_entries(manifest.entries, prefix_count)
    suffix_originals = originals[prefix_count:]
    authority = authority or _Authority(dsn)
    authority.genesis()
    for entry, row, original in zip(
        manifest.entries[:prefix_count], prefix, originals[:prefix_count], strict=True
    ):
        _require(
            row["candidate_digest"] == original.candidate_digest,
            "prefix candidate digest differs",
        )
        _require(
            _source_token(row) == original.source_revision_id,
            "prefix source token differs",
        )
        proof = authority.publication(entry, row)
        if checkpoint38 and entry.ordinal > 2:
            _require(
                row.get("durable_proof") == proof, "checkpoint38 durable proof differs"
            )
    # The failed next session (S3 or C2S22) already admitted its source before STOP.
    # Verify it read-only; it is not a receipt for an accepted contribution.
    authority.source(
        manifest.entries[prefix_count], originals[prefix_count].source_revision_id
    )
    command = {
        "world": replay.WORLD_ID,
        "manifest_digest": manifest.digest,
        "retained_report_sha256": CHECKPOINT_REPORT_SHA256,
        "retained_ledger_sha256": CHECKPOINT_LEDGER_SHA256,
        "source_head": replay.git_head(root),
        "prefix_head": prefix_head,
    }
    if checkpoint38:
        command.update(
            checkpoint38_report_sha256=CHECKPOINT38_REPORT_SHA256,
            binding_decision_id=binding_decision_id,
            binding_decision_sha256=binding_decision_sha256,
        )
    output = output.resolve()
    packet = None
    if execute_checkpoint38:
        _require(
            output.parent == CHECKPOINT38_PRIVATE_ROOT
            and output.name != "continuation-run-01",
            "checkpoint38 output must be new under the private recovery root",
        )
        packet, packet_sha256 = _execution_packet(
            execution_packet,
            manifest=manifest,
            originals=originals,
            source_head=command["source_head"],
            decision_id=binding_decision_id,
            decision_sha256=binding_decision_sha256,
            output=output,
            accepted_root=accepted_root,
            retained_root=retained_root,
            checkpoint38_report=checkpoint38_report,
            target=target,
        )
        command["execution_packet_sha256"] = packet_sha256
    command_digest = replay._digest_obj(command)
    if verify_checkpoint38_only:
        _require(
            authority.head() == prefix_head, "retained head moved before verification"
        )
        for entry in suffix_entries:
            authority.require_unclaimed(entry, dsn)
        return {
            "status": "PREFIX_VERIFIED_READ_ONLY",
            "command": command,
            "command_digest": command_digest,
            "sessions": prefix,
            "new_confirms": 0,
            "last_good_head": prefix_head,
            "execution_held": True,
            "binding_verified": False,
            "full_selected_world_ready": False,
        }
    if verify_checkpoint38_binding_only:
        _require(
            authority.head() == prefix_head,
            "retained head moved before binding verification",
        )
        for entry in suffix_entries:
            authority.require_unclaimed(entry, dsn)
        authority.checkpoint38_binding(
            manifest.entries[CHECKPOINT38_S22_ORDINAL - 1],
            originals[CHECKPOINT38_S22_ORDINAL - 1],
            binding_decision_id,
            binding_decision_sha256,
            dsn,
        )
        return {
            "status": "CHECKPOINT38_BINDING_VERIFIED_READ_ONLY",
            "command": command,
            "command_digest": command_digest,
            "sessions": prefix,
            "new_confirms": 0,
            "last_good_head": prefix_head,
            "terminal_head": None,
            "execution_held": True,
            "binding_verified": True,
            "full_selected_world_ready": False,
        }
    if output.exists():
        path = output / "continuation_report.json"
        _require(
            path.is_file(), "output already claimed without completion proof; STOP"
        )
        prior = json.loads(path.read_text(encoding="utf-8"))
        _require(
            prior["command_digest"] == command_digest, "existing run command differs"
        )
        _require(
            prior["status"] == "COMPLETE", "incomplete run cannot automatically restart"
        )
        if checkpoint38:
            backup = prior.get("prewrite_backup") or {}
            backup_path = output / "checkpoint38-before.dump"
            _require(
                backup.get("path") == str(backup_path)
                and isinstance(backup.get("sha256"), str)
                and backup_path.is_file()
                and replay._sha256_file(backup_path) == backup["sha256"],
                "completed checkpoint38 backup missing or changed",
            )
        rows = prior["sessions"]
        _require(
            len(rows) == 44 and rows[:prefix_count] == prefix,
            "completed ledger coverage differs",
        )
        parent = GENESIS
        for entry, row, original in zip(manifest.entries, rows, originals, strict=True):
            _require(
                row["sealed_parent_revision"] == parent, "completed lineage differs"
            )
            _require(
                row["candidate_digest"] == original.candidate_digest,
                "completed candidate differs",
            )
            _require(
                _source_token(row) == original.source_revision_id,
                "completed source token differs",
            )
            proof = authority.publication(entry, row)
            if entry.ordinal > 2:
                _require(
                    row.get("durable_proof") == proof,
                    "completed durable contribution identity differs",
                )
            parent = row["receipt_child_revision"]
        _require(prior["terminal_head"] == parent, "completed terminal differs")
        return {**prior, "disposition": "ALREADY_COMPLETE_VERIFIED_READ_ONLY"}
    _require(authority.head() == prefix_head, "retained head moved before continuation")
    if checkpoint38:
        for entry in suffix_entries:
            authority.require_unclaimed(entry, dsn)
        authority.checkpoint38_binding(
            manifest.entries[38],
            originals[38],
            binding_decision_id,
            binding_decision_sha256,
            dsn,
        )
        _require(
            execute_checkpoint38,
            "checkpoint38 requires explicit six-session execution mode and packet",
        )
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report: dict[str, Any] = {
        "command": command,
        "command_digest": command_digest,
        "status": "RUNNING",
        "sessions": prefix,
        "new_confirms": 0,
        "last_good_head": prefix_head,
        "terminal_head": None,
        "model_calls": 0,
        "full_selected_world_ready": False,
    }
    if checkpoint38:
        report["execution_packet_sha256"] = command["execution_packet_sha256"]
    replay._write_json(output / "continuation_report.json", report)
    seams = seams or replay.ReplaySeams()
    parent = prefix_head
    try:
        if checkpoint38:
            report["prewrite_backup"] = _backup_before_confirm(dsn, output, authority)
            replay._write_json(output / "continuation_report.json", report)
            for entry in suffix_entries:
                authority.require_unclaimed(entry, dsn)
            authority.checkpoint38_binding(
                manifest.entries[38],
                originals[38],
                binding_decision_id,
                binding_decision_sha256,
                dsn,
            )
        for entry, original in zip(suffix_entries, suffix_originals, strict=True):
            if checkpoint38:
                _require(
                    replay._sha256_file(execution_packet)
                    == command["execution_packet_sha256"],
                    "execution packet changed during continuation",
                )
            _require(
                authority.head() == parent,
                "expected parent moved before source/prepare",
            )
            if checkpoint38:
                authority.require_unclaimed(entry, dsn)
            candidate_path = replay._resolve_candidate_path(
                original.candidate_locator, accepted_root
            )
            if checkpoint38:
                _require(
                    replay._sha256_file(candidate_path)
                    == packet["suffix"][entry.ordinal - 39]["candidate_file_sha256"],
                    "candidate file changed during continuation",
                )
            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            from apps.live_control_server.services.candidate_graph_admission import (
                canonical_candidate_digest,
            )

            digest = canonical_candidate_digest(candidate)
            _require(
                digest == original.candidate_digest, "candidate drift before operation"
            )
            replay.verify_entry_source_bytes(root, entry)
            artifact = replay._load_canonical_source_artifact(
                repo_root=root, entry=entry, seams=seams
            )
            result = replay._admit_and_confirm(
                repo_root=root,
                dsn=dsn,
                entry=entry,
                candidate_graph=candidate,
                source_artifact=artifact,
                source_uri=artifact.uri,
                source_revision_id=original.source_revision_id,
                prior_head=parent,
                seams=seams,
            )
            _require(
                candidate == json.loads(candidate_path.read_text(encoding="utf-8")),
                "candidate mutated",
            )
            if checkpoint38:
                _require(
                    replay._sha256_file(candidate_path)
                    == packet["suffix"][entry.ordinal - 39]["candidate_file_sha256"],
                    "candidate file changed during confirm",
                )
            row = _ledger_row(entry, original, digest, result)
            _require(row["sealed_parent_revision"] == parent, "confirm parent differs")
            row["durable_proof"] = authority.publication(entry, row)
            _require(
                authority.head() == row["receipt_child_revision"],
                "head differs after confirm; STOP",
            )
            parent = row["receipt_child_revision"]
            report["sessions"].append(row)
            report["new_confirms"] += 1
            report["last_good_head"] = parent
            replay._write_json(output / "continuation_report.json", report)
        if checkpoint38:
            _require(
                replay._sha256_file(execution_packet)
                == command["execution_packet_sha256"],
                "execution packet changed during continuation",
            )
            _require(
                replay._sha256_file(output / "checkpoint38-before.dump")
                == report["prewrite_backup"]["sha256"],
                "checkpoint38 backup changed during continuation",
            )
        report["status"] = "COMPLETE"
        report["terminal_head"] = parent
    except Exception as exc:
        report["status"] = "STOP"
        actual_head = None
        head_error = None
        try:
            actual_head = authority.head()
        except Exception as read_error:
            head_error = type(read_error).__name__
        report["stop"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "actual_head": actual_head,
            "head_read_error": head_error,
            "last_verified_head": report["last_good_head"],
            "warning": "inflight publication may have committed; preserve and reconcile, no automatic retry",
        }
    finally:
        replay._write_json(output / "continuation_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted-root", type=Path, required=True)
    parser.add_argument("--retained-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dsn", required=True)
    parser.add_argument("--checkpoint38-report", type=Path)
    parser.add_argument("--binding-decision-id")
    parser.add_argument("--binding-decision-sha256")
    parser.add_argument("--verify-checkpoint38-only", action="store_true")
    parser.add_argument("--verify-checkpoint38-binding-only", action="store_true")
    parser.add_argument("--execute-checkpoint38", action="store_true")
    parser.add_argument("--execution-packet", type=Path)
    args = parser.parse_args()
    report = run_continuation(
        accepted_root=args.accepted_root,
        retained_root=args.retained_root,
        output=args.output,
        dsn=args.dsn,
        checkpoint38_report=args.checkpoint38_report,
        binding_decision_id=args.binding_decision_id,
        binding_decision_sha256=args.binding_decision_sha256,
        verify_checkpoint38_only=args.verify_checkpoint38_only,
        verify_checkpoint38_binding_only=args.verify_checkpoint38_binding_only,
        execute_checkpoint38=args.execute_checkpoint38,
        execution_packet=args.execution_packet,
    )
    print(
        json.dumps(
            {
                key: report.get(key)
                for key in (
                    "status",
                    "disposition",
                    "new_confirms",
                    "last_good_head",
                    "terminal_head",
                    "stop",
                )
            },
            sort_keys=True,
        )
    )
    return (
        0
        if report["status"]
        in {
            "COMPLETE",
            "PREFIX_VERIFIED_READ_ONLY",
            "CHECKPOINT38_BINDING_VERIFIED_READ_ONLY",
        }
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
