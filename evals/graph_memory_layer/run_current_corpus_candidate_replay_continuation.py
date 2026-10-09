"""Bounded continuation of sealed C1S2 or checkpoint38; never initializes a World.

This command is not an automatic recovery engine. An incomplete output directory,
an ambiguous confirm, or an unexpected head is a STOP requiring steward review.
Only an already COMPLETE exact run may be repeated, read-only.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

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
        """Held boundary: no unaccepted carrier schema/API is integrated here.

        Decision pins are command integrity, not admission authority. A later
        reviewed producer + Core transaction fence must replace this gate and
        reprove the exact decision/source basis. No caller can enable it.
        """
        # RAKE's producer alone is insufficient: its final source/decision
        # check is outside Core's publication transaction. No caller flag or
        # injected callback may activate real suffix writes under this source.
        _require(False, "checkpoint38 publication fence not accepted; execution held")

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
) -> dict[str, Any]:
    replay.assert_runtime_dsn(dsn)
    root = (repo_root or replay.REPO_ROOT).resolve()
    if require_clean:
        _require(replay.git_worktree_clean(root), "continuation checkout dirty")
    manifest, originals = replay.load_accepted_cohort(
        artifact_root=accepted_root, repo_root=root
    )
    prefix = _checkpoint(retained_root, manifest.entries)
    checkpoint38 = checkpoint38_report is not None
    _require(
        not verify_checkpoint38_only or checkpoint38,
        "read-only checkpoint38 verification requires sealed report",
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
    command_digest = replay._digest_obj(command)
    if verify_checkpoint38_only:
        _require(
            seams is None,
            "checkpoint38 requires production admission, no injected seams",
        )
        _require(
            authority.head() == prefix_head, "retained head moved before verification"
        )
        for entry in manifest.entries[prefix_count:]:
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
    output = output.resolve()
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
        _require(
            seams is None,
            "checkpoint38 requires production admission, no injected seams",
        )
        for entry in manifest.entries[prefix_count:]:
            authority.require_unclaimed(entry, dsn)
        authority.checkpoint38_binding(
            manifest.entries[38],
            originals[38],
            binding_decision_id,
            binding_decision_sha256,
            dsn,
        )
    output.mkdir(parents=True, exist_ok=False)
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
    replay._write_json(output / "continuation_report.json", report)
    seams = seams or replay.ReplaySeams()
    parent = prefix_head
    try:
        for entry, original in zip(
            manifest.entries[prefix_count:], originals[prefix_count:], strict=True
        ):
            _require(
                authority.head() == parent,
                "expected parent moved before source/prepare",
            )
            candidate_path = replay._resolve_candidate_path(
                original.candidate_locator, accepted_root
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
    return 0 if report["status"] in {"COMPLETE", "PREFIX_VERIFIED_READ_ONLY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
