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


@pytest.fixture
def checkpoint38(setup, monkeypatch):
    s = setup
    full = run(s)
    report = copy.deepcopy(full)
    report.update(
        status="STOP",
        new_confirms=36,
        sessions=full["sessions"][:38],
        last_good_head="rev:synthetic-38",
        terminal_head=None,
        stop={"actual_head": "rev:synthetic-38", "head_read_error": None},
    )
    for ordinal, row in enumerate(report["sessions"], 1):
        row["ordinal"] = ordinal
    # Keep the original first two rows exact, including their ordinal fields.
    ledger = s.retained / "replay_ledger.json"
    old = json.loads(ledger.read_text())
    for ordinal, row in enumerate(old["sessions"], 1):
        row["ordinal"] = ordinal
    ledger.write_text(json.dumps(old))
    old_report = s.retained / "replay_report.json"
    obj = json.loads(old_report.read_text())
    obj["replay_ledger"] = old["sessions"]
    old_report.write_text(json.dumps(obj))
    monkeypatch.setattr(
        driver, "CHECKPOINT_LEDGER_SHA256", driver.replay._sha256_file(ledger)
    )
    monkeypatch.setattr(
        driver, "CHECKPOINT_REPORT_SHA256", driver.replay._sha256_file(old_report)
    )
    path = s.root / "sealed38.json"
    path.write_text(json.dumps(report))
    monkeypatch.setattr(
        driver, "CHECKPOINT38_REPORT_SHA256", driver.replay._sha256_file(path)
    )
    monkeypatch.setattr(driver, "CHECKPOINT38_HEAD", "rev:synthetic-38")
    s.authority.current = "rev:synthetic-38"
    s.authority.verified.clear()
    s.calls.clear()
    s.output = s.root / "suffix39"
    s.authority.unclaimed = []
    s.authority.require_unclaimed = lambda entry, dsn: s.authority.unclaimed.append(
        entry.ordinal
    )
    s.authority.binding_calls = []
    s.authority.checkpoint38_binding = lambda *args: s.authority.binding_calls.append(
        args
    )
    s.checkpoint_args = dict(
        checkpoint38_report=path,
        binding_decision_id="decision:reviewed",
        binding_decision_sha256="a" * 64,
    )
    return s


def test_checkpoint38_only_six_suffix_confirms(checkpoint38):
    s = checkpoint38
    prefix = json.loads(s.checkpoint_args["checkpoint38_report"].read_text())[
        "sessions"
    ]
    result = run(s, **s.checkpoint_args)
    assert result["status"] == "COMPLETE"
    assert result["new_confirms"] == 6
    assert s.calls == list(range(39, 45))
    assert result["sessions"][:38] == prefix
    assert s.authority.verified[:38] == list(range(1, 39))
    assert s.authority.unclaimed == list(range(39, 45))
    assert len(s.authority.binding_calls) == 1
    assert result["command"]["binding_decision_sha256"] == "a" * 64


@pytest.mark.parametrize(
    "change",
    [
        "bytes",
        "count",
        "status",
        "head",
        "actual_head",
        "ordinal",
        "parent",
        "source",
        "candidate",
        "proof",
        "proposal",
    ],
)
def test_checkpoint38_altered_prefix_is_zero_write(checkpoint38, monkeypatch, change):
    s = checkpoint38
    path = s.checkpoint_args["checkpoint38_report"]
    obj = json.loads(path.read_text())
    if change == "count":
        obj["sessions"].pop()
    elif change == "status":
        obj["status"] = "COMPLETE"
    elif change == "head":
        obj["last_good_head"] = "rev:other"
    elif change == "actual_head":
        obj["stop"]["actual_head"] = None
    elif change == "ordinal":
        obj["sessions"][10]["ordinal"] = 90
    elif change == "parent":
        obj["sessions"][10]["sealed_parent_revision"] = "rev:other"
    elif change == "source":
        obj["sessions"][10]["source_revision_id"] = "sha256:other"
    elif change == "candidate":
        obj["sessions"][10]["candidate_digest"] = "other"
    elif change == "proof":
        obj["sessions"][10]["durable_proof"] = {}
    elif change == "proposal":
        obj["sessions"][10]["proposal_digest"] = "other"
    else:
        obj["extra"] = "tampered"
    path.write_text(json.dumps(obj))
    # Re-seal synthetic artifacts except the digest test to prove semantic guards too.
    if change != "bytes":
        monkeypatch.setattr(
            driver, "CHECKPOINT38_REPORT_SHA256", driver.replay._sha256_file(path)
        )
    with pytest.raises(driver.replay.ReplayStop):
        run(s, **s.checkpoint_args)
    assert s.calls == [] and not s.output.exists()


@pytest.mark.parametrize(
    "failure", ["head", "receipt", "source", "decision", "unclaimed"]
)
def test_checkpoint38_authority_failure_before_output(checkpoint38, failure):
    s = checkpoint38
    if failure == "head":
        s.authority.current = "rev:moved"
    elif failure == "receipt":
        s.authority.missing.add(30)
    elif failure == "source":
        s.authority.source_bad = True
    else:

        def reject(*args):
            raise driver.replay.ReplayStop("changed authority", boundary="test")

        if failure == "decision":
            s.authority.checkpoint38_binding = reject
        else:
            s.authority.require_unclaimed = reject
    with pytest.raises(driver.replay.ReplayStop):
        run(s, **s.checkpoint_args)
    assert not s.calls and not s.output.exists()


@pytest.mark.parametrize("field", ["binding_decision_id", "binding_decision_sha256"])
def test_checkpoint38_requires_decision_pins(checkpoint38, field):
    args = {**checkpoint38.checkpoint_args, field: None}
    with pytest.raises(driver.replay.ReplayStop):
        run(checkpoint38, **args)
    assert not checkpoint38.calls


def test_checkpoint38_rejects_prepare_test_seam(checkpoint38):
    with pytest.raises(driver.replay.ReplayStop, match="production admission"):
        run(
            checkpoint38,
            **checkpoint38.checkpoint_args,
            seams=driver.replay.ReplaySeams(),
        )
    assert not checkpoint38.calls


def test_checkpoint38_complete_repeat_read_only(checkpoint38):
    s = checkpoint38
    first = run(s, **s.checkpoint_args)
    before = list(s.calls)
    s.authority.current = "rev:descendant"
    second = run(s, **s.checkpoint_args)
    assert second["disposition"] == "ALREADY_COMPLETE_VERIFIED_READ_ONLY"
    assert s.calls == before and second["terminal_head"] == first["terminal_head"]
    with pytest.raises(driver.replay.ReplayStop, match="command differs"):
        run(s, **{**s.checkpoint_args, "binding_decision_sha256": "b" * 64})


def test_checkpoint38_stop_is_terminal(checkpoint38, monkeypatch):
    s = checkpoint38

    def fail(**kwargs):
        raise RuntimeError("ambiguous response loss")

    monkeypatch.setattr(driver.replay, "_admit_and_confirm", fail)
    result = run(s, **s.checkpoint_args)
    assert (
        result["status"] == "STOP"
        and result["stop"]["actual_head"] == "rev:synthetic-38"
    )
    with pytest.raises(driver.replay.ReplayStop, match="cannot automatically restart"):
        run(s, **s.checkpoint_args)


def test_checkpoint38_pending_publication_contract_cannot_write():
    authority = driver._Authority("unused", NS())
    with pytest.raises(
        driver.replay.ReplayStop, match="publication fence not accepted"
    ):
        authority.checkpoint38_binding(
            NS(), NS(), "decision:reviewed", "a" * 64, "unused"
        )


@pytest.mark.parametrize("claimed", [False, True])
def test_checkpoint38_negative_contribution_probe_is_read_only(monkeypatch, claimed):
    from contextlib import nullcontext

    calls = []

    class Cursor:
        def execute(self, query, params):
            calls.append((query, params))

        def fetchone(self):
            return (1,) if claimed else None

    def connect(dsn, **kwargs):
        assert kwargs == {"options": "-c default_transaction_read_only=on"}
        return nullcontext(NS(cursor=lambda: nullcontext(Cursor())))

    monkeypatch.setattr("psycopg.connect", connect)
    authority = driver._Authority("unused", NS())
    if claimed:
        with pytest.raises(driver.replay.ReplayStop, match="unaccounted"):
            authority.require_unclaimed(NS(source_artifact_id="artifact:22"), "unused")
    else:
        authority.require_unclaimed(NS(source_artifact_id="artifact:22"), "unused")
    assert len(calls) == 1 and calls[0][0].startswith("SELECT 1")
    assert calls[0][1] == (driver.replay.WORLD_ID, "artifact:22")


def test_checkpoint38_verification_does_not_claim_output_or_check_carrier(checkpoint38):
    s = checkpoint38
    result = run(
        s,
        checkpoint38_report=s.checkpoint_args["checkpoint38_report"],
        verify_checkpoint38_only=True,
    )
    assert result["status"] == "PREFIX_VERIFIED_READ_ONLY"
    assert result["execution_held"] and not result["binding_verified"]
    assert len(result["sessions"]) == 38
    assert not s.calls and not s.output.exists() and not s.authority.binding_calls


def test_readonly_mode_requires_checkpoint38(setup):
    with pytest.raises(driver.replay.ReplayStop, match="requires sealed report"):
        run(setup, verify_checkpoint38_only=True)
    assert not setup.calls


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
