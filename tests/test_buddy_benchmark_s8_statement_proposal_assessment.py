"""Provider-free negative controls for the independent assessment boundary."""

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from evals.buddy_benchmark import s8_statement_proposal_assessment as assessment
from graph_memory.extraction.qualified_statement_proposals import (
    INSTRUCTIONS,
    canonical,
    digest,
    parse,
    ProposalBatch,
)
from graph_memory.extraction.statement_source_catalog import catalog, CONTRACT


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
    unit = record["result"]["passages"]["p1"]["primary"][0]
    candidates = (
        [
            {
                "unit_id": unit["unit_id"],
                "start_byte": max(unit["start_byte"], extent["start_byte"]),
                "end_byte": min(unit["end_byte"], extent["end_byte"]),
            }
        ]
        if inside
        else []
    )
    record["review_eligibility"] = {
        "p1": {
            "status": "requires_explicit_clause_selection"
            if inside
            else "outside_registered_evidence",
            "candidate_extents": candidates,
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


def projected_schema(schema):
    from generationengine.utils.schema_utils import make_schema_strict

    frozen = json.loads(canonical(schema))
    frozen["properties"] = {
        key: frozen["properties"][key] for key in assessment.ROOT_ORDER
    }
    return make_schema_strict(frozen)


def example():
    text = "A heard a sound."
    request = {"operation_id": "operation", "source_sha256": "source"}
    packet = {
        "contract": CONTRACT,
        "logical_source": "local-source",
        "authority": {},
        "scope": {},
        "world_identity_context": {"entities": []},
        "output_schema": ProposalBatch.model_json_schema(),
    }
    packet["source_catalog"] = catalog(
        text, {key: packet[key] for key in ("logical_source", "authority", "scope")}
    )
    batch = {
        "contract": CONTRACT,
        "catalog_sha256": packet["source_catalog"]["catalog_sha256"],
        "mentions": [{"mention_id": "m1", "label": "A", "source_unit_ids": ["u1"]}],
        "proposals": [
            {
                "proposal_id": "p1",
                "source_unit_ids": ["u1"],
                "context_unit_ids": [],
                "meaning": "A heard a sound.",
                "mode": "narrator",
                "reporter_mention": None,
                "referent_mentions": ["m1"],
                "uncertainty": [],
                "qualifications": [{"key": "perception", "value": "heard"}],
                "episode": "e1",
                "unresolved": [],
            }
        ],
        "dispositions": [
            {
                "unit_id": "u1",
                "status": "proposed",
                "proposal_ids": ["p1"],
                "reason": "heard event",
            }
        ],
        "limitations": [],
    }
    raw = canonical(batch)
    wire = json.dumps(
        {
            "input": [{"role": "user", "content": canonical(packet)}],
            "instructions": INSTRUCTIONS,
            "model": "gpt-6-luna",
            "max_output_tokens": assessment.OUTPUT_RESERVE,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": assessment.SCHEMA_NAME,
                    "strict": True,
                    "schema": projected_schema(packet["output_schema"]),
                }
            },
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
        "result": parse(raw, packet["source_catalog"]),
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
    monkeypatch.setattr(
        assessment, "declared_sdk_inventory", lambda: {"verified": True}
    )
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
    "change",
    [
        None,
        "model",
        "input",
        "instructions",
        "capacity",
        "old_capacity",
        "no_instruction_change",
    ],
)
def test_instruction_contrast_changes_only_the_declared_instructions(change):
    old = {
        "model": "gpt-6-luna",
        "input": ["same source and names"],
        "instructions": "same instructions",
        "max_output_tokens": 128000,
    }
    historical_instructions = "frozen historical v4 instructions"
    current = old | {"instructions": historical_instructions}
    if change == "old_capacity":
        old["max_output_tokens"] = 8192
    elif change == "capacity":
        current["max_output_tokens"] = 8192
    elif change == "no_instruction_change":
        old["instructions"] = historical_instructions
    elif change:
        current[change] = "changed"
    if change:
        with pytest.raises(ValueError):
            assessment.instruction_contrast(
                canonical(current), canonical(old), historical_instructions
            )
    else:
        assessment.instruction_contrast(
            canonical(current), canonical(old), historical_instructions
        )


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


@pytest.mark.parametrize(
    "change",
    [None, "wrong_origin", "version", "dirty", "untracked", "missing", "symlink"],
)
def test_sdk_package_requires_actual_bytes_and_locked_version(tmp_path, change):
    root = tmp_path / "openai"
    root.mkdir()
    source = root / "__init__.py"
    source.write_text("accepted\n")
    expected = {"__init__.py": assessment.fixture.sha(source.read_bytes())}
    actual_root = root
    version = "locked"
    if change == "wrong_origin":
        actual_root = tmp_path / "other"
        actual_root.mkdir()
        (actual_root / "__init__.py").write_text("accepted\n")
    elif change == "version":
        version = "old"
    elif change == "dirty":
        source.write_text("changed\n")
    elif change == "untracked":
        (root / "extra.json").write_text("extra\n")
    elif change == "missing":
        source.unlink()
    elif change == "symlink":
        other = tmp_path / "elsewhere"
        other.write_text("accepted\n")
        source.unlink()
        source.symlink_to(other)
    if change:
        with pytest.raises(ValueError):
            assessment.verify_sdk_package(
                actual_root,
                expected,
                version=version,
                locked_version="locked",
                expected_root=root,
            )
    else:
        actual = assessment.verify_sdk_package(
            actual_root,
            expected,
            version=version,
            locked_version="locked",
            expected_root=root,
        )
        assert actual["files"] == 1 and actual["version"] == "locked"


def test_sdk_failure_precedes_database_capture(tmp_path, monkeypatch):
    touched = []
    monkeypatch.setattr(assessment, "declared_ge_inventory", lambda: {"verified": True})

    def reject():
        raise ValueError("wrong SDK import")

    monkeypatch.setattr(assessment, "declared_sdk_inventory", reject)
    monkeypatch.setattr(assessment, "capture", lambda root: touched.append(root))
    with pytest.raises(ValueError, match="wrong SDK import"):
        assessment.main(["--clone-root", str(tmp_path), "--source-receipt", "unused"])
    assert touched == [] and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "change",
    [
        None,
        "commitment",
        "extent",
        "text",
        "identity",
        "duplicate_source",
        "missing_unit",
        "policy",
    ],
)
def test_independent_catalog_reconstruction_rejects_forgery(change):
    _, _, text, packet = example()
    c = packet["source_catalog"]
    if change == "commitment":
        c["catalog_sha256"] = "0" * 64
    elif change == "extent":
        c["units"][0]["end_byte"] -= 1
    elif change == "text":
        c["units"][0]["text"] = "fabricated"
    elif change == "identity":
        c["source_identity"]["logical_source"] = "different"
    elif change == "duplicate_source":
        packet["source"] = text
    elif change == "missing_unit":
        c["units"] = []
    elif change == "policy":
        c["selector_policy"] = "other"
    if change:
        with pytest.raises(ValueError):
            assessment.verify_catalog(packet, text)
    else:
        assessment.verify_catalog(packet, text)


@pytest.mark.parametrize(
    "change",
    [
        None,
        "handle",
        "materialization",
        "mention_passage",
        "missing_accounting",
        "wrong_accounting",
        "semantic_credit",
        "factive",
    ],
)
def test_independent_materialization_and_accounting(change):
    record, _, text, packet = example()
    result = record["result"]
    if change == "handle":
        result["batch"]["proposals"][0]["source_unit_ids"] = ["unknown"]
    elif change == "materialization":
        result["passages"]["p1"]["primary"][0] = {"text": "truncated"}
    elif change == "mention_passage":
        result["mention_passages"]["m1"] = []
    elif change == "missing_accounting":
        result["batch"]["dispositions"] = []
    elif change == "wrong_accounting":
        result["batch"]["dispositions"][0]["proposal_ids"] = []
    elif change == "semantic_credit":
        result["coverage"]["semantic_completeness"] = "established"
    elif change == "factive":
        result["embedded_content_factive"] = True
    if change:
        with pytest.raises(ValueError):
            assessment.verify_materialization(result, packet, text)
    else:
        assessment.verify_materialization(result, packet, text)


def test_physical_partition_preserves_unicode_line_endings_and_intervening_sentence():
    _, _, _, packet = example()
    text = " \r\nFirst é. Intervening sentence. Last 🦉.\r\n\t\r\nSecond\u2028line.\r"
    packet["source_catalog"] = catalog(
        text, {key: packet[key] for key in ("logical_source", "authority", "scope")}
    )
    units = assessment.verify_catalog(packet, text)
    assert len(units) == 2
    assert "Intervening sentence." in units["u1"]["text"]
    assert "\u2028" in units["u2"]["text"]


def test_context_only_disposition_is_not_primary_extraction():
    record, _, _, packet = example()
    text = "A heard.\n\nB spoke."
    packet["source_catalog"] = catalog(
        text, {key: packet[key] for key in ("logical_source", "authority", "scope")}
    )
    batch = json.loads(record["raw_output"])
    batch["catalog_sha256"] = packet["source_catalog"]["catalog_sha256"]
    batch["proposals"][0]["context_unit_ids"] = ["u2"]
    batch["dispositions"].append(
        {
            "unit_id": "u2",
            "status": "skipped",
            "proposal_ids": [],
            "reason": "context only",
        }
    )
    result = parse(canonical(batch), packet["source_catalog"])
    assessment.verify_materialization(result, packet, text)
    result["batch"]["dispositions"][1].update(status="proposed", proposal_ids=["p1"])
    with pytest.raises(ValueError):
        assessment.verify_materialization(result, packet, text)


@pytest.mark.parametrize("change", [None, "names", "source", "scope", "extra"])
def test_protocol_contrast_preserves_source_and_authority(change):
    _, _, text, packet = example()
    old = {
        key: deepcopy(packet[key])
        for key in ("logical_source", "authority", "scope", "world_identity_context")
    }
    old.update(source=text, output_schema={"v1": True})
    if change == "names":
        packet["world_identity_context"] = {"entities": ["different"]}
    elif change == "source":
        old["source"] = "different"
    elif change == "scope":
        packet["scope"] = {"other": True}
    elif change == "extra":
        packet["extra"] = True
    if change:
        with pytest.raises(ValueError):
            assessment.verify_protocol_contrast(packet, old)
    else:
        assessment.verify_protocol_contrast(packet, old)


@pytest.mark.parametrize(
    "change", ["extent", "text", "unit_digest", "ordinal", "split_nonblank"]
)
def test_rehashed_catalog_cannot_forge_physical_partition(change):
    _, _, text, packet = example()
    c = packet["source_catalog"]
    if change == "extent":
        c["units"][0]["start_byte"] = 1
    elif change == "text":
        c["units"][0]["text"] = "invented"
    elif change == "unit_digest":
        c["units"][0]["sha256"] = "0" * 64
    elif change == "ordinal":
        c["units"][0]["unit_id"] = "foreign"
    else:
        c["units"] = [
            {
                "unit_id": f"u{i + 1}",
                "start_byte": a,
                "end_byte": b,
                "sha256": assessment.fixture.sha(text.encode()[a:b]),
                "text": text[a:b],
            }
            for i, (a, b) in enumerate([(0, 2), (2, len(text))])
        ]
    c["catalog_sha256"] = digest(
        {key: value for key, value in c.items() if key != "catalog_sha256"}
    )
    with pytest.raises(ValueError, match="descriptor or partition|partition count"):
        assessment.verify_catalog(packet, text)


@pytest.mark.parametrize(
    "change", [None, "missing", "name", "strict", "schema", "root", "open_object"]
)
def test_actual_native_schema_guard(change):
    import json

    record, _, _, packet = example()
    body = json.loads(record["wire"])
    if change == "missing":
        del body["text"]
    elif change in {"name", "strict", "schema"}:
        body["text"]["format"][change] = "forged"
    elif change in {"root", "open_object"}:
        if change == "root":
            packet["output_schema"]["type"] = "array"
        else:
            packet["output_schema"]["$defs"]["Qualification"]["type"] = "string"
    if change:
        with pytest.raises(ValueError):
            assessment.verify_native_schema(body, packet)
    else:
        assessment.verify_native_schema(body, packet)


@pytest.mark.parametrize(
    "change",
    [
        None,
        "lost",
        "invented",
        "duplicate",
        "blank_key",
        "blank_value",
        "null_reported",
        "unknown_reporter",
        "unknown_referent",
    ],
)
def test_wire_qualifications_materialize_losslessly(change):
    import json

    record, _, _, _ = example()
    raw = json.loads(record["raw_output"])
    host = deepcopy(record["result"]["batch"])
    p = raw["proposals"][0]
    if change == "lost":
        host["proposals"][0]["qualifications"] = {}
    elif change == "invented":
        host["proposals"][0]["qualifications"]["extra"] = "invented"
    elif change == "duplicate":
        p["qualifications"].append(deepcopy(p["qualifications"][0]))
    elif change == "blank_key":
        p["qualifications"][0]["key"] = " "
    elif change == "blank_value":
        p["qualifications"][0]["value"] = " "
    elif change == "null_reported":
        p["mode"] = "reported"
    elif change == "unknown_reporter":
        p["reporter_mention"] = "unknown"
    elif change == "unknown_referent":
        p["referent_mentions"] = ["unknown"]
    if change:
        with pytest.raises(ValueError):
            assessment.verify_qualification_materialization(raw, host)
    else:
        assessment.verify_qualification_materialization(raw, host)


def test_actual_native_schema_rejects_reported_null_without_local_validator():
    import json
    import jsonschema

    record, _, _, packet = example()
    schema = assessment.verify_native_schema(json.loads(record["wire"]), packet)
    raw = json.loads(record["raw_output"])
    raw["proposals"][0]["mode"] = "reported"
    assert not jsonschema.Draft202012Validator(schema).is_valid(raw)
    raw["proposals"][0]["reporter_mention"] = "m1"
    assert jsonschema.Draft202012Validator(schema).is_valid(raw)


@pytest.mark.parametrize("change", [None, "catalog", "names", "schema", "contract"])
def test_v5_source_catalog_and_authority_remain_exact(change):
    _, _, _, packet = example()
    old = deepcopy(packet)
    old.update(contract="qualified_source_handles_v2", output_schema={"v2": True})
    if change == "catalog":
        packet["source_catalog"]["units"][0]["text"] = "changed"
    elif change == "names":
        packet["world_identity_context"] = {"entities": ["changed"]}
    elif change == "schema":
        old["output_schema"] = packet["output_schema"]
    elif change == "contract":
        packet["contract"] = "old"
    if change:
        with pytest.raises(ValueError):
            assessment.verify_v5_contrast(packet, old)
    else:
        assessment.verify_v5_contrast(packet, old)


@pytest.mark.parametrize(
    "change",
    [None, "merge", "reopen", "run_pin", "provider", "old_state", "old_identity"],
)
def test_delivery_proof_is_a_pinned_read_only_prerequisite(tmp_path, change):
    import json

    reviewed = "0eecfce3be2940cc207e74213d3b0c2d6bc17876"
    delivery = {
        "merge": assessment.BASE,
        "reviewed_head": reviewed,
        "retained_state_identical": True,
        "ready": 200,
        "schema": assessment.END,
    }
    reopen = {
        "merge": assessment.BASE,
        "reviewed_head": reviewed,
        "all_retained_state_identical": True,
        "ordinary_plan_reopen": True,
        "new_private_village_image_loaded": True,
        "original_run_plan_pin_not_updated": True,
        "communication_choice_and_four_notes_reflection_preserved": True,
    }
    replay = {
        "runtime_head": reviewed,
        "read_only_connections": True,
        "provider_schema_calls": 0,
        "provider_calls": 0,
        "current_renderer_calls": 0,
        "historical_parser_calls": 0,
        "provider_budget_calls": 0,
        "all_app_native_files_prior_evidence_v6_unchanged": True,
        "operations": [
            {"operation_id": key, "state": "failed", "exact_read_replay": True}
            for key in sorted(assessment.RETAINED_OPERATIONS)
        ],
    }
    if change == "merge":
        delivery["merge"] = "other"
    elif change == "reopen":
        reopen["ordinary_plan_reopen"] = False
    elif change == "run_pin":
        reopen["original_run_plan_pin_not_updated"] = False
    elif change == "provider":
        replay["provider_budget_calls"] = 1
    elif change == "old_state":
        replay["operations"][0]["state"] = "completed"
    elif change == "old_identity":
        replay["operations"][0]["operation_id"] = "other"
    for name, value in (
        ("delivery-proof", delivery),
        ("ordinary-reopen-proof", reopen),
        ("actual-five-failure-replay", replay),
    ):
        (tmp_path / (name + ".json")).write_text(json.dumps(value))
    if change:
        with pytest.raises(ValueError):
            assessment.declared_delivery_proof(tmp_path)
    else:
        assert len(assessment.declared_delivery_proof(tmp_path)) == 3


def test_reprojected_native_schema_cannot_hide_missing_reporter_dependency():
    import json

    record, _, _, packet = example()
    packet["output_schema"]["$defs"]["ReportedStatement"]["properties"][
        "reporter_mention"
    ] = {"type": ["string", "null"]}
    body = json.loads(record["wire"])
    body["text"]["format"]["schema"] = projected_schema(packet["output_schema"])
    with pytest.raises(ValueError, match="permits reported/null"):
        assessment.verify_native_schema(body, packet)


def test_multiple_unicode_qualifications_survive_without_other_batch_changes():
    import json

    record, _, _, _ = example()
    raw = json.loads(record["raw_output"])
    host = deepcopy(record["result"]["batch"])
    raw["proposals"][0]["qualifications"].append(
        {"key": "uncertainty", "value": "é🦉 remains unknown"}
    )
    host["proposals"][0]["qualifications"]["uncertainty"] = "é🦉 remains unknown"
    assessment.verify_qualification_materialization(raw, host)
    host["proposals"][0]["meaning"] = "different interpretation"
    with pytest.raises(ValueError, match="materialization differs"):
        assessment.verify_qualification_materialization(raw, host)


@pytest.mark.parametrize(
    "change",
    [
        None,
        "only_properties",
        "required_sequence",
        "nested_order",
        "nested_value",
        "input",
        "instructions",
        "budget",
        "extra_field",
    ],
)
def test_order_only_wire_contrast_preserves_every_other_value_and_order(change):
    record, _, _, packet = example()
    current = json.loads(record["wire"])
    prior = deepcopy(current)
    schema = prior["text"]["format"]["schema"]
    schema["properties"] = {
        key: schema["properties"][key] for key in sorted(assessment.ROOT_ORDER)
    }
    schema["required"] = sorted(assessment.ROOT_ORDER)
    if change == "only_properties":
        current["text"]["format"]["schema"]["properties"] = deepcopy(
            schema["properties"]
        )
    elif change == "required_sequence":
        current["text"]["format"]["schema"]["required"].reverse()
    elif change == "nested_order":
        node = current["text"]["format"]["schema"]["$defs"]["ReportedStatement"][
            "properties"
        ]
        current["text"]["format"]["schema"]["$defs"]["ReportedStatement"][
            "properties"
        ] = dict(reversed(list(node.items())))
    elif change == "nested_value":
        current["text"]["format"]["schema"]["$defs"]["ReportedStatement"]["properties"][
            "reporter_mention"
        ]["minLength"] = 2
    elif change == "input":
        current["input"] = []
    elif change == "instructions":
        current["instructions"] = "different"
    elif change == "budget":
        current["max_output_tokens"] = 1
    elif change == "extra_field":
        current["extra"] = True
    if change:
        with pytest.raises(ValueError):
            assessment.verify_order_only_contrast(
                json.dumps(current), json.dumps(prior)
            )
    else:
        assessment.verify_order_only_contrast(json.dumps(current), json.dumps(prior))
        assessment.verify_native_schema(current, packet)


def test_native_property_order_only_change_cannot_pass_dict_equality():
    record, _, _, packet = example()
    body = json.loads(record["wire"])
    altered = deepcopy(body)
    props = altered["text"]["format"]["schema"]["properties"]
    altered["text"]["format"]["schema"]["properties"] = dict(
        reversed(list(props.items()))
    )
    assert altered == body
    with pytest.raises(ValueError, match="actual native root order"):
        assessment.verify_native_schema(altered, packet)


@pytest.mark.parametrize("change", ["reverse", "duplicate", "missing", "foreign"])
def test_frozen_required_array_controls_independent_projection(change):
    record, _, _, packet = example()
    order = packet["output_schema"]["required"]
    if change == "reverse":
        order.reverse()
    elif change == "duplicate":
        order.append(order[0])
    elif change == "missing":
        order.pop()
    else:
        order[0] = "foreign"
    with pytest.raises(ValueError, match="frozen declared root order"):
        assessment.verify_native_schema(json.loads(record["wire"]), packet)


def test_v6_wire_reference_refuses_changed_historical_artifact(tmp_path):
    root = tmp_path / "clone"
    case = tmp_path / "native-review-context-v2/s8-qualified-proposals-v6"
    case.mkdir(parents=True)
    (case / "operation.json").write_text('{"wire":"fabricated"}')
    with pytest.raises(ValueError, match="original v6 operation artifact differs"):
        assessment.v6_wire_reference(root)
