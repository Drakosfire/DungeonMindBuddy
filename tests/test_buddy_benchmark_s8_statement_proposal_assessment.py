"""Provider-free negative controls for the independent assessment boundary."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from evals.buddy_benchmark import s8_statement_proposal_assessment as assessment
from graph_memory.extraction.qualified_statement_proposals import (
    INSTRUCTIONS,
    canonical,
    digest,
    parse,
)


def source(monkeypatch, start=0, end=6172):
    body = "x" * 6172
    monkeypatch.setattr(
        assessment.fixture, "BODY_SHA", assessment.fixture.sha(body.encode())
    )
    return SimpleNamespace(
        status="available",
        body_text=body,
        span_start_byte=start,
        span_end_byte=end,
        span_sha256=assessment.fixture.sha(body[start:end].encode()),
    )


def test_whole_body_available_is_not_whole_span_authority(monkeypatch):
    opened = source(monkeypatch, 4868, 4939)
    with pytest.raises(ValueError, match="whole-source admission missing"):
        assessment.assert_whole_source(opened)


def test_whole_source_exact_identity(monkeypatch):
    opened = source(monkeypatch)
    assessment.assert_whole_source(opened)
    opened.body_text = "different"
    with pytest.raises(ValueError, match="body differs"):
        assessment.assert_whole_source(opened)


def test_authorized_body_inspection_does_not_require_full_evidence_extent(monkeypatch):
    opened = source(monkeypatch, 4868, 4939)
    extent = assessment.assert_source_inspection(opened)
    assert extent["start_byte"] == 4868 and extent["end_byte"] == 4939
    opened.span_sha256 = "wrong"
    with pytest.raises(ValueError, match="anchor differs"):
        assessment.assert_source_inspection(opened)


@pytest.mark.parametrize("inside", [True, False])
def test_eligibility_cannot_promote_inspection_to_evidence(inside):
    record, _, _, _ = example()
    extent = {"start_byte": 0 if inside else 100, "end_byte": 100 if inside else 120}
    match = record["result"]["locations"]["p1"]["matches"][0]
    eligibility = "eligible_for_review" if inside else "outside_registered_evidence"
    record["review_eligibility"] = {
        "p1": {
            "status": eligibility,
            "matches": [{**match, "eligibility": eligibility}],
            "semantic_acceptance": "not_established",
        }
    }
    assessment.verify_eligibility(record, extent)
    record["review_eligibility"]["p1"]["semantic_acceptance"] = "accepted"
    with pytest.raises(ValueError):
        assessment.verify_eligibility(record, extent)


def rows(schema="20261029_0092"):
    return {
        "application_state.schema_migrations": [
            {"sha256": schema, "keys": {"version_num": schema}}
        ],
        "agent.turn": [{"sha256": "old", "keys": {}}],
    }


def test_exact_migration_and_one_operation():
    before = rows()
    migrated = rows(assessment.END) | {assessment.TABLE: []}
    assessment.app_conservation(before, migrated, migrated=True)
    after = deepcopy(migrated)
    after[assessment.TABLE] = [
        {
            "sha256": "new",
            "keys": {"operation_id": "operation", "world_id": assessment.fixture.WORLD},
        }
    ]
    assessment.app_conservation(migrated, after, operation="operation")


@pytest.mark.parametrize(
    "change",
    [
        "old_row",
        "second_operation",
        "unexpected_table",
        "missing_table",
        "old_operation_removed",
    ],
)
def test_app_conservation_rejects_unleased_changes(change):
    before = rows(assessment.END) | {
        assessment.TABLE: [{"sha256": "prior", "keys": {}}]
    }
    after = deepcopy(before)
    after[assessment.TABLE].append(
        {
            "sha256": "new",
            "keys": {"operation_id": "operation", "world_id": assessment.fixture.WORLD},
        }
    )
    if change == "old_row":
        after["agent.turn"][0]["sha256"] = "changed"
    elif change == "second_operation":
        after[assessment.TABLE].append({"sha256": "another", "keys": {}})
    elif change == "unexpected_table":
        after["unleased"] = []
    elif change == "missing_table":
        del after["agent.turn"]
    else:
        after[assessment.TABLE].pop(0)
    with pytest.raises(ValueError):
        assessment.app_conservation(before, after, operation="operation")


def example():
    text = "A heard a sound."
    request = {"operation_id": "operation", "source_sha256": "source"}
    packet = {"source": text, "world_identity_context": {"entities": []}}
    batch = {
        "mentions": [{"mention_id": "m1", "label": "A", "quote": "A"}],
        "proposals": [
            {
                "proposal_id": "p1",
                "quote": text,
                "meaning": "A heard a sound.",
                "mode": "narrator",
                "reporter_mention": None,
                "referent_mentions": ["m1"],
                "uncertainty": [],
                "qualifications": {"perception": "heard"},
                "episode": "e1",
                "context_quotes": [],
                "unresolved": [],
            }
        ],
        "limitations": [],
    }
    raw = canonical(batch)
    wire = canonical(
        {
            "input": [{"role": "user", "content": canonical(packet)}],
            "instructions": INSTRUCTIONS,
            "model": "gpt-6-luna",
            "max_output_tokens": assessment.OUTPUT_RESERVE,
        }
    )
    record = {
        "intent": request,
        "operation_id": "operation",
        "owner": "local_operator",
        "intent_digest": digest(request),
        "input": packet,
        "reviews": [],
        "wire": wire,
        "wire_digest": assessment.fixture.sha(wire.encode()),
        "lifecycle": [{"outcome": "sending"}, {"outcome": "response_received"}],
        "state": "completed",
        "failure": None,
        "raw_output": raw,
        "result": parse(raw, text),
    }
    return record, request, text, packet


def test_actual_completed_output_is_independently_reparsed():
    assessment.verify_record(*example())


@pytest.mark.parametrize(
    "change", [None, "other_operation", "other_world", "missing_identity"]
)
def test_added_row_must_be_exact_authorized_operation(change):
    before = rows(assessment.END) | {assessment.TABLE: []}
    after = deepcopy(before)
    keys = {
        "operation_id": "authorized-operation",
        "world_id": assessment.fixture.WORLD,
    }
    if change == "other_operation":
        keys["operation_id"] = "other-operation"
    elif change == "other_world":
        keys["world_id"] = "other-world"
    elif change == "missing_identity":
        keys = {}
    after[assessment.TABLE] = [{"sha256": "new", "keys": keys}]
    if change:
        with pytest.raises(ValueError, match="authorized operation/World"):
            assessment.app_conservation(before, after, operation="authorized-operation")
    else:
        assessment.app_conservation(before, after, operation="authorized-operation")


@pytest.mark.parametrize(
    "change", [None, "missing", "operation_id", "world_id", "owner", "payload"]
)
def test_readback_binds_exact_actual_stored_row(change):
    record, _, _, _ = example()
    row = {
        "operation_id": record["operation_id"],
        "owner": record["owner"],
        "world_id": assessment.fixture.WORLD,
        "payload": deepcopy(record),
    }
    if change == "missing":
        row = None
    elif change == "payload":
        row["payload"]["raw_output"] = "changed"
    elif change:
        row[change] = "different"
    if change:
        with pytest.raises(ValueError):
            assessment.verify_stored_operation(row, record)
    else:
        # Eligibility is host-derived, never another stored publication fact.
        assessment.verify_stored_operation(row, record | {"review_eligibility": {}})


@pytest.mark.parametrize(
    "change",
    [
        "owner",
        "request",
        "input",
        "wire_hash",
        "wire_input",
        "wire_tools",
        "wire_capacity",
        "no_response",
        "parsed_result",
        "raw_output",
        "reviews",
        "unknown_as_completed",
    ],
)
def test_completion_cannot_be_inferred_from_http_success(change):
    record, request, text, packet = example()
    if change == "owner":
        record["owner"] = "other"
    elif change == "request":
        record["intent"] = request | {"extra": True}
    elif change == "input":
        record["input"] = {"source": "different"}
    elif change == "wire_hash":
        record["wire_digest"] = "bad"
    elif change in {"wire_input", "wire_tools", "wire_capacity"}:
        import json

        body = json.loads(record["wire"])
        if change == "wire_capacity":
            body["max_output_tokens"] = 8192
        else:
            body["input" if change == "wire_input" else "tools"] = ["changed"]
        record["wire"] = canonical(body)
        record["wire_digest"] = assessment.fixture.sha(record["wire"].encode())
    elif change == "no_response":
        record["lifecycle"] = []
    elif change == "parsed_result":
        record["result"]["batch"]["proposals"] = []
    elif change == "raw_output":
        record["raw_output"] = "invalid JSON"
    elif change == "reviews":
        record["reviews"] = [{"selection": "unleased"}]
    else:
        record["lifecycle"][-1]["outcome"] = "outcome_unknown"
    with pytest.raises(ValueError):
        assessment.verify_record(record, request, text, packet)


def test_failed_output_remains_failure():
    record, request, text, packet = example()
    record.update(state="failed", failure="malformed", raw_output="bad", result=None)
    assessment.verify_record(record, request, text, packet)


@pytest.mark.parametrize("key", ["native", "files", "prior_evidence"])
def test_read_only_state_and_old_evidence_preserved(key):
    before = {"native": "a", "files": "b", "prior_evidence": "c"}
    with pytest.raises(ValueError, match="read-only state changed"):
        assessment.unchanged(before, before | {key: "changed"})


def test_provider_switch_never_bypasses_preflight(tmp_path, monkeypatch):
    monkeypatch.setattr(assessment, "declared_ge_inventory", lambda: {"verified": True})
    with pytest.raises(FileNotFoundError):
        assessment.main(
            [
                "--clone-root",
                str(tmp_path),
                "--source-receipt",
                str(tmp_path / "receipt"),
                "--provider",
                "--apply",
                "--preflight-sha256",
                "unrecorded",
            ]
        )


@pytest.mark.parametrize("change", [None, "dirty", "untracked", "missing", "symlink"])
def test_runtime_pin_checks_actual_bytes_including_untracked(tmp_path, change):
    import subprocess

    for folder in ("src", "apps/live_control_server"):
        path = tmp_path / folder
        path.mkdir(parents=True)
        (path / "module.py").write_text("accepted\n")

    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args])

    git("init", "--initial-branch=codex/test")
    git("add", ".")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        "fixture",
    )
    ref = git("rev-parse", "HEAD").decode().strip()
    target = tmp_path / "src/module.py"
    if change == "dirty":
        target.write_text("different\n")
    elif change == "untracked":
        (tmp_path / "src/extra.py").write_text("extra\n")
    elif change == "missing":
        target.unlink()
    elif change == "symlink":
        target.unlink()
        target.symlink_to(tmp_path / "apps/live_control_server/module.py")
    if change:
        with pytest.raises(ValueError):
            assessment.runtime_inventory(tmp_path, ref)
    else:
        result = assessment.runtime_inventory(tmp_path, ref)
        assert all(row["files"] == 1 for row in result.values())


def test_sdk_observer_forwards_exact_arguments_results_and_counts(monkeypatch):
    import asyncio
    from openai.resources.responses.responses import AsyncResponses

    response = SimpleNamespace(model_dump=lambda **kwargs: {"id": "actual"})
    received = []

    async def original(self, *args, **kwargs):
        received.append((self, args, kwargs))
        return response

    monkeypatch.setattr(AsyncResponses, "create", original)
    owner, value = object(), object()
    with assessment.observe_sdk() as observed:
        result = asyncio.run(AsyncResponses.create(owner, value, model="unchanged"))
        assert result is response
        assert received == [(owner, (value,), {"model": "unchanged"})]
        assert observed == {
            "sdk_entries": 1,
            "responses": [{"id": "actual"}],
            "errors": [],
        }
        # Reading the observation cannot itself add dispatches.
        assert deepcopy(observed) == observed
    assert AsyncResponses.create is original


def test_sdk_observer_preserves_exception(monkeypatch):
    import asyncio
    from openai.resources.responses.responses import AsyncResponses

    error = RuntimeError("diagnostic")

    async def original(self, **kwargs):
        raise error

    monkeypatch.setattr(AsyncResponses, "create", original)
    with assessment.observe_sdk() as observed:
        with pytest.raises(RuntimeError) as raised:
            asyncio.run(AsyncResponses.create(object()))
        assert raised.value is error
        assert observed == {
            "sdk_entries": 1,
            "responses": [],
            "errors": ["RuntimeError"],
        }


@pytest.mark.parametrize(
    "change", [None, "different_text", "two_messages", "incomplete", "extra_entry"]
)
def test_sdk_output_binding_is_independent_of_stored_result(change):
    record, _, _, _ = example()
    message = {
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": record["raw_output"]}],
    }
    observed = {
        "sdk_entries": 1,
        "responses": [{"status": "completed", "output": [message]}],
        "errors": [],
    }
    if change == "different_text":
        message["content"][0]["text"] = "different"
    elif change == "two_messages":
        observed["responses"][0]["output"].append(deepcopy(message))
    elif change == "incomplete":
        observed["responses"][0]["status"] = "incomplete"
    elif change == "extra_entry":
        observed["sdk_entries"] = 2
    if change:
        with pytest.raises(ValueError):
            assessment.verify_sdk_output(record, observed)
    else:
        assessment.verify_sdk_output(record, observed)


@pytest.mark.parametrize(
    "change", [None, "model", "input", "instructions", "capacity", "old_capacity"]
)
def test_capacity_contrast_changes_only_the_named_execution_parameter(change):
    old = {
        "model": "gpt-6-luna",
        "input": ["same source and names"],
        "instructions": "same instructions",
        "max_output_tokens": 8192,
    }
    current = old | {"max_output_tokens": 128000}
    if change == "old_capacity":
        old["max_output_tokens"] = 9000
    elif change == "capacity":
        current["max_output_tokens"] = 8192
    elif change:
        current[change] = "changed"
    if change:
        with pytest.raises(ValueError):
            assessment.capacity_contrast(canonical(current), canonical(old))
    else:
        assessment.capacity_contrast(canonical(current), canonical(old))


def test_v3_does_not_offer_a_migration_command(tmp_path):
    with pytest.raises(SystemExit):
        assessment.main(
            ["--clone-root", str(tmp_path), "--source-receipt", "unused", "--migrate"]
        )


@pytest.mark.parametrize(
    "change", [None, "wrong_origin", "dirty", "untracked", "missing", "symlink"]
)
def test_generationengine_guard_checks_origin_and_every_package_byte(tmp_path, change):
    import shutil
    import subprocess

    repository = tmp_path / "repository"
    package = repository / "src/generationengine"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("accepted\n")
    (package / "provider-data.json").write_text('{"accepted":true}\n')

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repository), *args])

    git("init", "--initial-branch=codex/test")
    git("add", ".")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        "fixture",
    )
    ref = git("rev-parse", "HEAD").decode().strip()
    expected_root = tmp_path / "immutable"
    actual_root = expected_root
    shutil.copytree(package, actual_root / "generationengine")
    selected = actual_root / "generationengine/__init__.py"
    if change == "wrong_origin":
        actual_root = tmp_path / "site-packages"
        shutil.copytree(package, actual_root / "generationengine")
    elif change == "dirty":
        selected.write_text("old implementation\n")
    elif change == "untracked":
        (selected.parent / "extra.json").write_text("untracked\n")
    elif change == "missing":
        selected.unlink()
    elif change == "symlink":
        selected.unlink()
        selected.symlink_to(package / "__init__.py")
    if change:
        with pytest.raises(ValueError):
            assessment.verify_ge_import(
                actual_root, repository=repository, ref=ref, expected_root=expected_root
            )
    else:
        result = assessment.verify_ge_import(
            actual_root, repository=repository, ref=ref, expected_root=expected_root
        )
        assert result["files"] == 2 and result["ref"] == ref


def test_ge_failure_precedes_any_action_or_database_capture(tmp_path, monkeypatch):
    touched = []

    def reject():
        raise ValueError("wrong GE import")

    monkeypatch.setattr(assessment, "declared_ge_inventory", reject)
    monkeypatch.setattr(assessment, "capture", lambda root: touched.append(root))
    with pytest.raises(ValueError, match="wrong GE import"):
        assessment.main(["--clone-root", str(tmp_path), "--source-receipt", "unused"])
    assert touched == [] and list(tmp_path.iterdir()) == []
