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
        authority=overrides.pop("authority", s.authority),
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


def test_checkpoint38_suffix_selection_is_planning_only(checkpoint38):
    s = checkpoint38
    prefix = json.loads(s.checkpoint_args["checkpoint38_report"].read_text())[
        "sessions"
    ]
    selected = driver._selected_suffix_entries(s.entries, len(prefix))
    assert [entry.ordinal for entry in selected] == list(range(39, 45))
    assert s.calls == [] and s.authority.binding_calls == []
    assert not s.output.exists()


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
    monkeypatch.setattr(driver, "CHECKPOINT_REPORT_SHA256", driver.replay._sha256_file(s.retained / "replay_report.json"))
    monkeypatch.setattr(driver, "CHECKPOINT_LEDGER_SHA256", driver.replay._sha256_file(s.retained / "replay_ledger.json"))
    with pytest.raises(driver.replay.ReplayStop):
        run(s, **s.checkpoint_args)
    assert s.calls == [] and not s.output.exists()


@pytest.mark.parametrize(
    "injection", ["authority", "seams", "readonly_authority", "binding_readonly"]
)
def test_checkpoint38_rejects_injected_execution_authority_before_any_call(
    checkpoint38, injection
):
    s = checkpoint38
    options = dict(s.checkpoint_args)
    if injection == "authority":
        options["authority"] = s.authority
    elif injection == "seams":
        options.update(authority=None, seams=driver.replay.ReplaySeams())
    elif injection == "readonly_authority":
        options.update(
            verify_checkpoint38_only=True,
            binding_decision_id=None,
            binding_decision_sha256=None,
        )
    elif injection == "binding_readonly":
        options["verify_checkpoint38_binding_only"] = True
    with pytest.raises(driver.replay.ReplayStop):
        run(s, **options)
    assert s.authority.genesis_calls == 1  # one call belongs to checkpoint38 fixture construction
    assert not s.calls and not s.output.exists()
    assert s.authority.binding_calls == []


@pytest.mark.parametrize("field", ["binding_decision_id", "binding_decision_sha256"])
def test_checkpoint38_requires_decision_pins(checkpoint38, field):
    args = {**checkpoint38.checkpoint_args, field: None}
    with pytest.raises(driver.replay.ReplayStop):
        run(checkpoint38, **{**args, "authority": None})
    assert not checkpoint38.calls


def test_checkpoint38_rejects_prepare_test_seam(checkpoint38):
    with pytest.raises(driver.replay.ReplayStop, match="production admission"):
        run(
            checkpoint38,
            **{**checkpoint38.checkpoint_args, "authority": None},
            seams=driver.replay.ReplaySeams(),
        )
    assert not checkpoint38.calls


def _checkpoint38_reviewed_context(decision_id="decision:reviewed"):
    import json

    from apps.live_control_server.models.extract_promote import (
        ReviewedCorpusNativeBindingV1,
    )
    from apps.live_control_server.models.world_graph_mutation_context import (
        REVIEWED_CORPUS_BINDING_REASON_PREFIX,
        reviewed_corpus_bindings_from_decisions,
    )
    from dungeonmind.contracts.identity import IdentityDecisionRecordV2
    from dungeonmind.domain.canonical import canonical_sha256

    reviewer_id = "reviewer:test-only"
    binding_payload = {
        "schema_version": "dmb_reviewed_corpus_native_binding_v1",
        "world_id": driver.replay.WORLD_ID,
        "parent_revision_id": driver.CHECKPOINT38_HEAD,
        "campaign_id": driver.CHECKPOINT38_S22_CAMPAIGN_ID,
        "candidate_sha256": driver.CHECKPOINT38_S22_CANDIDATE_SHA256,
        "candidate_node_id": driver.CHECKPOINT38_S22_CANDIDATE_NODE_ID,
        "corpus_ref_type": driver.CHECKPOINT38_S22_CORPUS_REF_TYPE,
        "corpus_ref_key": driver.CHECKPOINT38_S22_CORPUS_REF_KEY,
        "target_object_id": driver.CHECKPOINT38_S22_TARGET_OBJECT_ID,
        "target_sha256": "a" * 64,
        "evidence_sha256": "b" * 64,
        "decision_id": decision_id,
        "reviewer_id": reviewer_id,
        "sources": [
            {
                "source_artifact_id": "artifact:test",
                "source_revision_id": "sha256:test",
                "artifact_sha256": "c" * 64,
                "revision_sha256": "d" * 64,
            }
        ],
    }
    binding = ReviewedCorpusNativeBindingV1.model_validate(binding_payload)
    decision = IdentityDecisionRecordV2.model_validate(
        {
            "decision_id": binding.decision_id,
            "world_id": binding.world_id,
            "decision_kind": "human_override",
            "subject_object_ids": [binding.candidate_node_id],
            "target_object_ids": [binding.target_object_id],
            "actor": reviewer_id,
            "reason": REVIEWED_CORPUS_BINDING_REASON_PREFIX
            + json.dumps(binding_payload, separators=(",", ":")),
            "status": "active",
            "created_at": "2026-10-01T00:00:00Z",
        }
    )
    record = decision.model_dump(mode="json")
    bindings = reviewed_corpus_bindings_from_decisions(
        [record], world_id=binding.world_id, revision_id=binding.parent_revision_id
    )
    context = NS(
        world_id=driver.replay.WORLD_ID,
        revision_id=driver.CHECKPOINT38_HEAD,
        head_revision_id=driver.CHECKPOINT38_HEAD,
        reviewed_corpus_bindings=bindings,
        identity_ledger_records=(record,),
    )
    return context, canonical_sha256(decision.model_dump(mode="json"))


def _install_valid_checkpoint38_binding(monkeypatch, s):
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    entry = s.entries[driver.CHECKPOINT38_S22_ORDINAL - 1]
    original = s.originals[driver.CHECKPOINT38_S22_ORDINAL - 1]
    entry.campaign_id = driver.CHECKPOINT38_S22_CAMPAIGN_ID
    entry.session_id = driver.CHECKPOINT38_S22_SESSION_ID
    entry.key = (entry.campaign_id, entry.session_id)
    entry.source_artifact_id = "artifact:recap:longmont-c2:session-22:06c978131f31"
    entry.original_sha256 = "06c978131f31e6ec85ff6286fe550f07bd2a3c5972c86bf29533079aebbf7083"
    original.candidate_digest = driver.CHECKPOINT38_S22_CANDIDATE_SHA256
    original.source_revision_id = (
        "sha256:06c978131f31e6ec85ff6286fe550f07bd2a3c5972c86bf29533079aebbf7083"
    )
    context, decision_sha256 = _checkpoint38_reviewed_context()
    loader_calls = []

    def load_context(world_id, *, revision_pin, database_url):
        loader_calls.append((world_id, revision_pin, database_url))
        return context

    monkeypatch.setattr(
        world_graph_writes, "load_production_mutation_context", load_context
    )
    gate = driver._Authority("unused", NS())
    s.authority.checkpoint38_binding = gate.checkpoint38_binding
    monkeypatch.setattr(driver, "_Authority", lambda _dsn: s.authority)
    s.checkpoint_args["binding_decision_id"] = "decision:reviewed"
    s.checkpoint_args["binding_decision_sha256"] = decision_sha256
    return loader_calls


def test_checkpoint38_binding_uses_exact_production_mutation_context(monkeypatch):
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    context, decision_sha256 = _checkpoint38_reviewed_context()
    calls = []

    def load_context(world_id, *, revision_pin, database_url):
        calls.append((world_id, revision_pin, database_url))
        return context

    monkeypatch.setattr(
        world_graph_writes, "load_production_mutation_context", load_context
    )
    authority = driver._Authority("unused", NS())
    assert (
        authority.checkpoint38_binding(
            NS(
                ordinal=driver.CHECKPOINT38_S22_ORDINAL,
                campaign_id=driver.CHECKPOINT38_S22_CAMPAIGN_ID,
                session_id=driver.CHECKPOINT38_S22_SESSION_ID,
            ),
            NS(candidate_digest=driver.CHECKPOINT38_S22_CANDIDATE_SHA256),
            "decision:reviewed",
            decision_sha256,
            "postgresql://test-dsn",
        )
        is None
    )
    assert calls == [
        (
            driver.replay.WORLD_ID,
            driver.CHECKPOINT38_HEAD,
            "postgresql://test-dsn",
        )
    ]


def test_checkpoint38_binding_only_verification_returns_before_output_or_confirm(
    checkpoint38, monkeypatch
):
    s = checkpoint38
    loader_calls = _install_valid_checkpoint38_binding(monkeypatch, s)
    report = run(
        s,
        **{
            **s.checkpoint_args,
            "authority": None,
            "verify_checkpoint38_binding_only": True,
        },
    )
    assert report["status"] == "CHECKPOINT38_BINDING_VERIFIED_READ_ONLY"
    assert report["binding_verified"] and report["execution_held"]
    assert report["new_confirms"] == 0
    assert len(report["sessions"]) == 38
    assert s.authority.unclaimed == list(range(39, 45))
    assert loader_calls == [
        (
            driver.replay.WORLD_ID,
            driver.CHECKPOINT38_HEAD,
            "postgresql://x:y@127.0.0.1:54362/dmb_current_corpus_replay_v1",
        )
    ]
    assert s.calls == [] and not s.output.exists()


def test_checkpoint38_valid_binding_still_holds_all_suffix_writes(
    checkpoint38, monkeypatch
):
    s = checkpoint38
    loader_calls = _install_valid_checkpoint38_binding(monkeypatch, s)
    with pytest.raises(
        driver.replay.ReplayStop, match="six-session execution authority contract"
    ):
        run(s, **{**s.checkpoint_args, "authority": None})
    assert len(loader_calls) == 1
    assert s.calls == [] and not s.output.exists()


@pytest.mark.parametrize(
    "drift",
    [
        "world",
        "revision",
        "head",
        "missing_binding",
        "duplicate_binding",
        "wrong_binding_target",
        "wrong_binding_campaign",
        "wrong_binding_parent",
        "wrong_binding_node",
        "wrong_binding_ref_type",
        "wrong_binding_ref_key",
        "wrong_candidate",
        "wrong_decision_id",
        "duplicate_decision",
        "inactive_decision",
        "wrong_decision_kind",
        "wrong_actor",
        "wrong_subject",
        "wrong_target",
        "wrong_decision_digest",
        "uppercase_digest",
        "padded_digest",
        "missing_digest",
        "padded_decision_id",
        "whitespace_decision_id",
        "loader_error",
    ],
)
def test_checkpoint38_binding_fails_closed_on_authority_or_pin_drift(
    monkeypatch, drift
):
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    decision_id = "decision:reviewed"
    if drift == "padded_decision_id":
        decision_id = " decision:reviewed "
    elif drift == "whitespace_decision_id":
        decision_id = "   "
    context, decision_sha256 = _checkpoint38_reviewed_context(decision_id)
    binding = context.reviewed_corpus_bindings[0]
    record = dict(context.identity_ledger_records[0])
    candidate_digest = driver.CHECKPOINT38_S22_CANDIDATE_SHA256

    if drift == "world":
        context.world_id = "another-world"
    elif drift == "revision":
        context.revision_id = "rev:other"
    elif drift == "head":
        context.head_revision_id = "rev:other"
    elif drift == "missing_binding":
        context.reviewed_corpus_bindings = ()
    elif drift == "duplicate_binding":
        context.reviewed_corpus_bindings = (binding, binding)
    elif drift == "wrong_binding_target":
        context.reviewed_corpus_bindings = (
            binding.model_copy(update={"target_object_id": "npc:other"}),
        )
    elif drift == "wrong_binding_campaign":
        context.reviewed_corpus_bindings = (
            binding.model_copy(update={"campaign_id": "longmont-c1"}),
        )
    elif drift == "wrong_binding_parent":
        context.reviewed_corpus_bindings = (
            binding.model_copy(update={"parent_revision_id": "rev:other"}),
        )
    elif drift == "wrong_binding_node":
        context.reviewed_corpus_bindings = (
            binding.model_copy(update={"candidate_node_id": "node:other"}),
        )
    elif drift == "wrong_binding_ref_type":
        context.reviewed_corpus_bindings = (
            binding.model_copy(update={"corpus_ref_type": "location"}),
        )
    elif drift == "wrong_binding_ref_key":
        context.reviewed_corpus_bindings = (
            binding.model_copy(update={"corpus_ref_key": "other-npc"}),
        )
    elif drift == "wrong_candidate":
        candidate_digest = "e" * 64
    elif drift == "wrong_decision_id":
        decision_id = "decision:other"
    elif drift == "duplicate_decision":
        context.identity_ledger_records = (
            record,
            dict(record),
        )
    elif drift == "inactive_decision":
        record["status"] = "superseded"
        context.identity_ledger_records = (record,)
    elif drift == "wrong_decision_kind":
        record["decision_kind"] = "alias_add"
        context.identity_ledger_records = (record,)
    elif drift == "wrong_actor":
        record["actor"] = "another-reviewer"
        context.identity_ledger_records = (record,)
    elif drift == "wrong_subject":
        record["subject_object_ids"] = ["node:other"]
        context.identity_ledger_records = (record,)
    elif drift == "wrong_target":
        record["target_object_ids"] = ["npc:other"]
        context.identity_ledger_records = (record,)
    elif drift == "wrong_decision_digest":
        decision_sha256 = "f" * 64
    elif drift == "uppercase_digest":
        decision_sha256 = decision_sha256.upper()
    elif drift == "padded_digest":
        decision_sha256 += " "
    elif drift == "missing_digest":
        decision_sha256 = None

    def load_context(*args, **kwargs):
        if drift == "loader_error":
            raise RuntimeError("authority unavailable")
        return context

    monkeypatch.setattr(
        world_graph_writes, "load_production_mutation_context", load_context
    )
    authority = driver._Authority("unused", NS())
    with pytest.raises(driver.replay.ReplayStop):
        authority.checkpoint38_binding(
            NS(
                ordinal=driver.CHECKPOINT38_S22_ORDINAL,
                campaign_id=driver.CHECKPOINT38_S22_CAMPAIGN_ID,
                session_id=driver.CHECKPOINT38_S22_SESSION_ID,
            ),
            NS(candidate_digest=candidate_digest),
            decision_id,
            decision_sha256,
            "postgresql://test-dsn",
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


def test_checkpoint38_report_verification_is_read_only_local_evidence(checkpoint38):
    s = checkpoint38
    rows = driver._checkpoint38(
        s.checkpoint_args["checkpoint38_report"],
        json.loads((s.retained / "replay_ledger.json").read_text())["sessions"],
    )
    assert len(rows) == 38
    assert rows[-1]["receipt_child_revision"] == driver.CHECKPOINT38_HEAD
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
