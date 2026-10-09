"""Synthetic one-run retained-prefix continuation boundary proofs."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from evals.graph_memory_layer import (
    run_current_corpus_candidate_replay_continuation as driver,
)


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "repo"
    root.mkdir()
    accepted = root / "accepted"
    accepted.mkdir()
    retained = root / "retained"
    retained.mkdir()
    entries, originals = [], []
    for index in range(1, 45):
        candidate = {"nodes": [{"node_id": f"synthetic-{index}"}], "edges": []}
        path = accepted / f"candidate-{index}.json"
        path.write_text(json.dumps(candidate))
        digest = driver.replay._digest_obj(candidate)
        entries.append(
            NS(
                ordinal=index,
                campaign_id="synthetic",
                session_id=f"session-{index}",
                key=("synthetic", f"session-{index}"),
                source_artifact_id=f"artifact:{index}",
                original_sha256=f"{index:064x}",
            )
        )
        originals.append(
            NS(
                candidate_locator=path.name,
                candidate_digest=digest,
                source_revision_id=f"sha256:{index:064x}",
            )
        )
    entries = tuple(entries)
    manifest = NS(entries=entries, digest=driver.replay.ACCEPTED_MANIFEST_DIGEST)
    prefix = []
    parent = driver.GENESIS
    for entry, original, child in zip(
        entries[:2], originals[:2], driver.PREFIX_CHILDREN, strict=True
    ):
        prefix.append(
            {
                "campaign_id": entry.campaign_id,
                "session_id": entry.session_id,
                "source_artifact_id": entry.source_artifact_id,
                "source_admission": {
                    "buddy_source_revision_id": original.source_revision_id
                },
                "candidate_digest": original.candidate_digest,
                "proposal_id": f"proposal:{entry.ordinal}",
                "proposal_digest": f"{entry.ordinal:064x}",
                "sealed_parent_revision": parent,
                "receipt_child_revision": child,
            }
        )
        parent = child
    ledger = retained / "replay_ledger.json"
    report = retained / "replay_report.json"
    ledger.write_text(json.dumps({"sessions": prefix}))
    report.write_text(
        json.dumps(
            {
                "replay_acceptance": "HOLD",
                "last_good_head": driver.PREFIX_HEAD,
                "genesis_d0": driver.GENESIS,
                "graph_writes": 3,
                "replay_ledger": prefix,
            }
        )
    )
    monkeypatch.setattr(
        driver, "CHECKPOINT_LEDGER_SHA256", driver.replay._sha256_file(ledger)
    )
    monkeypatch.setattr(
        driver, "CHECKPOINT_REPORT_SHA256", driver.replay._sha256_file(report)
    )
    monkeypatch.setattr(
        driver.replay,
        "load_accepted_cohort",
        lambda **kwargs: (manifest, tuple(originals)),
    )
    monkeypatch.setattr(driver.replay, "git_worktree_clean", lambda _: True)
    monkeypatch.setattr(driver.replay, "git_head", lambda _: "approved-source")
    monkeypatch.setattr(driver.replay, "verify_entry_source_bytes", lambda *args: None)
    monkeypatch.setattr(
        driver.replay,
        "_load_canonical_source_artifact",
        lambda **kwargs: NS(uri=f"repo://synthetic/{kwargs['entry'].ordinal}"),
    )

    class Authority:
        current = driver.PREFIX_HEAD
        proofs = {}
        genesis_calls = 0
        verified = []
        missing = set()
        source_bad = False

        def head(self):
            return self.current

        def genesis(self):
            self.genesis_calls += 1

        def source(self, entry, token):
            driver._require(not self.source_bad, "source pre-admission mismatch")
            driver._require(
                token == originals[entry.ordinal - 1].source_revision_id,
                "source token differs",
            )

        def publication(self, entry, row):
            self.verified.append(entry.ordinal)
            driver._require(
                entry.ordinal not in self.missing, "missing durable receipt"
            )
            driver._require(
                row["proposal_digest"] == f"{entry.ordinal:064x}",
                "durable command mismatch",
            )
            driver._require(
                row["source_artifact_id"] == entry.source_artifact_id,
                "durable source mismatch",
            )
            driver._require(
                driver._source_token(row)
                == originals[entry.ordinal - 1].source_revision_id,
                "source bytes mismatch",
            )
            return {"review_id": f"review:{entry.ordinal}"}

    authority = Authority()
    calls = []

    def confirm(**kwargs):
        index = kwargs["entry"].ordinal
        driver._require(authority.current == kwargs["prior_head"], "parent race")
        calls.append(index)
        prior = authority.current
        authority.current = f"rev:synthetic-{index}"
        return {
            "parent_revision_id": prior,
            "child_revision_id": authority.current,
            "proposal_id": f"proposal:{index}",
            "proposal_digest": f"{index:064x}",
        }

    monkeypatch.setattr(driver.replay, "_admit_and_confirm", confirm)
    return NS(
        root=root,
        accepted=accepted,
        retained=retained,
        entries=entries,
        originals=originals,
        authority=authority,
        calls=calls,
        confirm=confirm,
        output=root / "continuation",
    )


def run(s, **overrides):
    args = dict(
        accepted_root=s.accepted,
        retained_root=s.retained,
        output=s.output,
        dsn="postgresql://x:y@127.0.0.1:54362/dmb_current_corpus_replay_v1",
        repo_root=s.root,
        authority=s.authority,
    )
    return driver.run_continuation(**{**args, **overrides})


def test_only_suffix_executes_and_prefix_stays_exact(setup):
    prefix = json.loads((setup.retained / "replay_ledger.json").read_text())["sessions"]
    result = run(setup)
    assert result["status"] == "COMPLETE"
    assert setup.calls == list(range(3, 45))
    assert result["new_confirms"] == 42
    assert result["sessions"][:2] == prefix
    assert setup.authority.verified[:2] == [1, 2]
    assert result["model_calls"] == 0
    assert not result["full_selected_world_ready"]


def test_exact_completed_repeat_is_read_only(setup):
    first = run(setup)
    calls = setup.calls.copy()
    setup.authority.current = "rev:unrelated-descendant"
    second = run(setup)
    assert second["disposition"] == "ALREADY_COMPLETE_VERIFIED_READ_ONLY"
    assert second["terminal_head"] == first["terminal_head"]
    assert setup.calls == calls


@pytest.mark.parametrize("mutation", ["command", "source", "candidate", "receipt"])
def test_completed_mismatch_is_rejected_without_new_confirm(setup, mutation):
    run(setup)
    path = setup.output / "continuation_report.json"
    obj = json.loads(path.read_text())
    if mutation == "command":
        obj["command_digest"] = "changed"
    elif mutation == "source":
        obj["sessions"][2]["source_revision_id"] = "sha256:changed"
    elif mutation == "candidate":
        obj["sessions"][2]["candidate_digest"] = "changed"
    else:
        setup.authority.missing.add(3)
    path.write_text(json.dumps(obj))
    prior = setup.calls.copy()
    with pytest.raises(driver.replay.ReplayStop):
        run(setup)
    assert setup.calls == prior


def test_drifted_checkpoint_blocks_before_any_suffix(setup):
    (setup.retained / "replay_ledger.json").write_text("{}")
    with pytest.raises(driver.replay.ReplayStop, match="digest"):
        run(setup)
    assert setup.calls == []
    assert not setup.output.exists()


def test_prefix_receipt_missing_blocks_before_source_or_output(setup):
    setup.authority.missing.add(2)
    with pytest.raises(driver.replay.ReplayStop, match="receipt"):
        run(setup)
    assert setup.calls == []
    assert not setup.output.exists()


def test_failed_session3_existing_source_is_verified_before_any_write(setup):
    setup.authority.source_bad = True
    with pytest.raises(driver.replay.ReplayStop, match="source"):
        run(setup)
    assert setup.calls == []
    assert not setup.output.exists()


def test_parent_moved_before_first_suffix_is_rejected(setup):
    setup.authority.current = "rev:other"
    with pytest.raises(driver.replay.ReplayStop, match="moved"):
        run(setup)
    assert setup.calls == []


def test_prepare_confirm_race_is_stop_without_confirm(setup, monkeypatch):
    def raced(**kwargs):
        setup.authority.current = "rev:other"
        return setup.confirm(**kwargs)

    monkeypatch.setattr(driver.replay, "_admit_and_confirm", raced)
    result = run(setup)
    assert result["status"] == "STOP"
    assert result["stop"]["actual_head"] == "rev:other"
    assert setup.calls == []


def test_lost_response_after_commit_preserves_actual_head_and_forbids_restart(
    setup, monkeypatch
):
    def lost(**kwargs):
        setup.confirm(**kwargs)
        raise RuntimeError("synthetic response lost")

    monkeypatch.setattr(driver.replay, "_admit_and_confirm", lost)
    result = run(setup)
    assert result["status"] == "STOP"
    assert result["new_confirms"] == 0
    assert result["last_good_head"] == driver.PREFIX_HEAD
    assert result["stop"]["actual_head"] == "rev:synthetic-3"
    with pytest.raises(driver.replay.ReplayStop, match="incomplete"):
        run(setup)
    assert setup.calls == [3]


def test_stop_after_verified_partial_suffix_keeps_prior_receipts(setup, monkeypatch):
    def partial(**kwargs):
        if kwargs["entry"].ordinal == 4:
            raise driver.replay.ReplayStop(
                "synthetic known failure", boundary="dungeonmind_write"
            )
        return setup.confirm(**kwargs)

    monkeypatch.setattr(driver.replay, "_admit_and_confirm", partial)
    result = run(setup)
    assert result["status"] == "STOP"
    assert result["new_confirms"] == 1
    assert len(result["sessions"]) == 3
    assert setup.calls == [3]
    assert result["last_good_head"] == "rev:synthetic-3"


def test_invalid_dsn_never_reaches_prefix_authority(setup):
    with pytest.raises(driver.replay.ReplayStop) as e:
        run(setup, dsn="postgresql://x:y@127.0.0.1:54330/dmb_current_corpus_replay_v1")
    assert e.value.boundary == "runtime_guard"
    assert setup.authority.genesis_calls == 0


def test_no_automatic_claim_of_foreign_output_directory(setup):
    setup.output.mkdir()
    with pytest.raises(driver.replay.ReplayStop, match="claimed"):
        run(setup)
    assert setup.calls == []


def test_candidate_drift_during_suffix_is_stop(setup):
    (setup.accepted / "candidate-3.json").write_text(json.dumps({"nodes": []}))
    result = run(setup)
    assert result["status"] == "STOP"
    assert setup.calls == []


def test_native_source_token_nested_prefix_is_not_rewritten():
    row = {"source_admission": {"buddy_source_revision_id": "sha256:abc"}}
    before = copy.deepcopy(row)
    assert driver._source_token(row) == "sha256:abc"
    assert row == before


def test_original_stop_survives_head_probe_outage(setup, monkeypatch):
    def unavailable_head():
        raise ConnectionError("synthetic head unavailable")

    def failed(**kwargs):
        setup.authority.head = unavailable_head
        raise RuntimeError("original synthetic confirm failure")

    monkeypatch.setattr(driver.replay, "_admit_and_confirm", failed)
    result = run(setup)
    assert result["status"] == "STOP"
    assert result["stop"]["message"] == "original synthetic confirm failure"
    assert result["stop"]["actual_head"] is None
    assert result["stop"]["head_read_error"] == "ConnectionError"
    assert (
        json.loads((setup.output / "continuation_report.json").read_text())["stop"]
        == result["stop"]
    )


@pytest.mark.parametrize("tamper", ["assertion_ids", "contribution_digest"])
def test_genesis_authority_rejects_self_consistent_wrong_roster(tamper, monkeypatch):
    receipt = NS(
        published_revision_id=driver.GENESIS,
        published_graph_payload_sha256="payload",
        source_plan_sha256="344965c8b972f05b6e6158eeef3a57e86ab9824f5db21117c50ee114f9764376",
        reviewed_contribution_id=driver.GENESIS_CONTRIBUTION_ID,
        reviewed_contribution_sha256=driver.GENESIS_CONTRIBUTION_SHA256,
        accepted_assertion_ids=list(driver.GENESIS_ASSERTION_IDS),
    )
    contribution = NS()
    if tamper == "assertion_ids":
        receipt.accepted_assertion_ids[0] = "assertion:other"
    else:
        receipt.reviewed_contribution_sha256 = "changed-consistently"
    monkeypatch.setattr(
        "dungeonmind.contracts.contribution_review_v2.contribution_v2_payload_sha256",
        lambda c: receipt.reviewed_contribution_sha256,
    )
    bundle = NS(
        reviewed_world_initializations=NS(get_for_world=lambda _: receipt),
        world_graph=NS(
            get_revision=lambda *args: NS(
                revision=NS(parent_revision_id=None, graph_payload_sha256="payload")
            )
        ),
        contributions=NS(get=lambda *args: contribution),
    )
    with pytest.raises(driver.replay.ReplayStop, match="genesis"):
        driver._Authority("unused", bundle).genesis()


@pytest.mark.parametrize(
    "tamper",
    [
        None,
        "world",
        "campaign",
        "session",
        "status",
        "domain",
        "key",
        "binding",
        "bytes",
    ],
)
def test_production_source_verifier_checks_actual_repo_bindings(monkeypatch, tamper):
    entry = NS(
        source_artifact_id="artifact:synthetic",
        campaign_id="synthetic",
        session_id="session-3",
        original_sha256="a" * 64,
    )
    artifact = NS(
        world_id=driver.replay.WORLD_ID,
        campaign_id="synthetic",
        session_id="session-3",
        status="active",
        source_domain="session_recap",
        source_domain_key="session_recap",
    )
    revision = NS(
        source_artifact_id=entry.source_artifact_id,
        content_sha256=entry.original_sha256,
    )
    if tamper == "world":
        artifact.world_id = "other"
    elif tamper == "campaign":
        artifact.campaign_id = "other"
    elif tamper == "session":
        artifact.session_id = "other"
    elif tamper == "status":
        artifact.status = "retired"
    elif tamper == "domain":
        artifact.source_domain = "other"
    elif tamper == "key":
        artifact.source_domain_key = "other"
    elif tamper == "binding":
        revision.source_artifact_id = "other"
    elif tamper == "bytes":
        revision.content_sha256 = "b" * 64
    monkeypatch.setattr(
        "apps.live_control_server.integrations.dungeonmind.world_graph_writes.catalog_aware_source_revision_ids",
        lambda sources, world, pairs: {next(iter(pairs)): "resolved-revision"},
    )
    sources = NS(get_artifact=lambda _: artifact, get_revision=lambda _: revision)
    authority = driver._Authority("unused", NS(sources=sources))
    if tamper is None:
        authority.source(entry, "sha256:" + entry.original_sha256)
    else:
        with pytest.raises(driver.replay.ReplayStop):
            authority.source(entry, "sha256:" + entry.original_sha256)
