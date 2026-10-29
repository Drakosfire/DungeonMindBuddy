"""No retained databases: test actual public Core/WK in disposable memory."""

from copy import deepcopy
import json

import pytest
from tests.test_source_statements import lane as native_lane
from evals.buddy_benchmark import q01_native_fixture_proof as proof


@pytest.fixture
def lane(tmp_path, monkeypatch):
    return native_lane.__wrapped__(tmp_path, monkeypatch)


def inputs(lane):
    body = ("## Recap\n" + proof.QUOTE + "\n").encode()
    start = len("## Recap\n".encode())
    pins = proof.validate_source(
        body, proof.sha(body), start, start + len(proof.QUOTE.encode())
    )
    binding = {
        "managed_world_id": lane.world.world_id,
        "native_world_id": lane.world.world_id,
        "binding_version": 3,
    }
    return body, pins, binding


def test_actual_source_identity_statement_and_readback(lane):
    body, pins, binding = inputs(lane)
    saved = {}
    result = proof.execute_native_proof(
        lane.repo,
        body,
        pins,
        binding,
        lambda name, value: saved.update({name: deepcopy(value)}),
        initial_head=lane.repo.get_head(lane.world.world_id).head_revision_id,
    )
    assert result["evaluation"]["counts"]["fail"] == 0
    assert result["evaluation"]["counts"]["unassessed"] == 1  # recovery not executed
    assert all(result["prior_graph_preserved"].values())
    assert result["final_entities"] == result["baseline_entities"] + 2
    assert result["final_assertions"] == result["baseline_assertions"] + 3
    assert (
        saved["reviewed-statement-payload"]
        == saved["statement-prepared"]["envelope"]["payload"]
    )
    assert saved["reviewed-statement-payload"]["meaning"] == proof.QUOTE
    assert "body_text" not in saved["source-request"]
    assert result["full_system_ingestion_verified"] is False


def test_stale_head_refuses_before_any_call(lane):
    body, pins, binding = inputs(lane)
    before = lane.repo.get_head(lane.world.world_id)
    with pytest.raises(ValueError, match="head changed"):
        proof.execute_native_proof(
            lane.repo,
            body,
            pins,
            binding,
            lambda *_: pytest.fail("checkpoint before head guard"),
            initial_head="wrong-head",
        )
    assert lane.repo.get_head(lane.world.world_id) == before


def test_actual_profile_one_parent_is_not_silently_changed(tmp_path, monkeypatch):
    from tests import test_source_statements as fixtures
    from graph_memory.vnext.domain_runtime import dungeonbuddy_dnd5e_semantic_profile

    monkeypatch.setattr(
        fixtures,
        "dungeonbuddy_dnd5e_custom_predicate_profile",
        dungeonbuddy_dnd5e_semantic_profile,
    )
    current = native_lane.__wrapped__(tmp_path, monkeypatch)
    body, pins, binding = inputs(current)
    before = current.repo.get_head(current.world.world_id)
    with pytest.raises(ValueError, match="governed descriptor transition"):
        proof.execute_native_proof(
            current.repo,
            body,
            pins,
            binding,
            lambda *_: pytest.fail(
                "source checkpoint created despite missing capability"
            ),
            initial_head=before.head_revision_id,
        )
    assert current.repo.get_head(current.world.world_id) == before


def test_payload_drift_refuses_before_statement_confirmation(lane, monkeypatch):
    from apps.live_control_server.services import source_statements

    body, pins, binding = inputs(lane)
    original = source_statements.prepare

    def wrong_meaning(*args, **kwargs):
        result = original(*args, **kwargs)
        result["envelope"]["payload"]["meaning"] = (
            "The meat came from the Abyss because of the Academy."
        )
        return result

    monkeypatch.setattr(source_statements, "prepare", wrong_meaning)
    monkeypatch.setattr(
        source_statements,
        "confirm",
        lambda *_: pytest.fail("unreviewed payload confirmed"),
    )
    saved = {}
    with pytest.raises(ValueError, match="frozen review"):
        proof.execute_native_proof(
            lane.repo,
            body,
            pins,
            binding,
            lambda n, v: saved.update({n: v}),
            initial_head=lane.repo.get_head(lane.world.world_id).head_revision_id,
        )
    assert "source-receipt" in saved and "identity-result" in saved
    assert "statement-result" not in saved
    assert saved["reviewed-statement-payload"]["meaning"] == proof.QUOTE


@pytest.mark.parametrize(
    "field,value",
    [
        ("database", "primary"),
        ("system_identifier", "other-server"),
        ("server_address", "172.17.0.6/32"),
        ("server_port", 54330),
    ],
)
def test_connected_guard_checks_live_identity(field, value):
    identity = {
        "database": proof.DATABASE,
        "system_identifier": proof.SYSTEM_ID,
        "server_address": "172.17.0.5/32",
        "server_port": 5432,
    }
    proof.validate_connected(identity, proof.DATABASE)
    identity[field] = value
    with pytest.raises(ValueError):
        proof.validate_connected(identity, proof.DATABASE)


@pytest.mark.parametrize("change", ["hash", "span", "duplicate"])
def test_exact_source_guard(change):
    body = ("Recap\n" + proof.QUOTE + "\n").encode()
    start = len(b"Recap\n")
    if change == "hash":
        with pytest.raises(ValueError, match="body changed"):
            proof.validate_source(body, "0" * 64, start, start + len(proof.QUOTE))
    elif change == "span":
        with pytest.raises(ValueError, match="clause changed"):
            proof.validate_source(
                body, proof.sha(body), start + 1, start + len(proof.QUOTE)
            )
    else:
        body += proof.QUOTE.encode()
        with pytest.raises(ValueError, match="ambiguous"):
            proof.validate_source(
                body, proof.sha(body), start, start + len(proof.QUOTE)
            )


def inventory(rows):
    hashes = [r[0] for r in rows]
    return {
        "count": len(rows),
        "sha256": proof.digest(hashes),
        "row_hashes": hashes,
        "owners": dict(rows),
    }


def allowed_tables():
    before = {name: inventory([]) for name in proof.APPENDS}
    after = {
        name: inventory([(name + str(i), proof.WORLD) for i in range(count)])
        for name, count in proof.APPENDS.items()
    }
    before["dungeonmind.knowledge_heads"] = inventory(
        [("old-head", proof.WORLD), ("other-world-head", "other")]
    )
    after["dungeonmind.knowledge_heads"] = inventory(
        [("new-head", proof.WORLD), ("other-world-head", "other")]
    )
    before["dungeonmind.knowledge_native_source_authority"] = inventory(
        [("epoch-before", None)]
    )
    after["dungeonmind.knowledge_native_source_authority"] = inventory(
        [("epoch-after", None)]
    )
    before["dungeonmind.graph_revisions"] = after["dungeonmind.graph_revisions"] = (
        inventory([("immutable-classic", proof.WORLD)])
    )
    return before, after


def test_precise_allowed_table_deltas():
    before, after = allowed_tables()
    assert proof.conservation(before, after)["passed"]


@pytest.mark.parametrize(
    "change",
    ["other_world", "prior_revision", "classic", "missing_append", "extra_append"],
)
def test_unrelated_or_missing_delta_refused(change):
    before, after = allowed_tables()
    if change == "other_world":
        after["dungeonmind.knowledge_heads"] = inventory(
            [("new-head", proof.WORLD), ("wrong-head", "other")]
        )
    elif change == "prior_revision":
        before["dungeonmind.knowledge_revisions"] = inventory(
            [("old-revision", proof.WORLD)]
        )
    elif change == "classic":
        after["dungeonmind.graph_revisions"] = inventory(
            [("mutated-classic", proof.WORLD)]
        )
    elif change == "missing_append":
        after["dungeonmind.knowledge_revisions"] = inventory([])
    else:
        after["dungeonmind.knowledge_revisions"]["row_hashes"].append("extra")
    assert not proof.conservation(before, after)["passed"]


def test_cli_defaults_readonly_and_preserves_original_incident(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "working"
    root.mkdir()
    state = {"statement_kernel_available": False}
    monkeypatch.setattr(proof, "preflight", lambda _: deepcopy(state))
    monkeypatch.setattr(
        proof, "execute_native_proof", lambda *_: pytest.fail("default command wrote")
    )
    monkeypatch.setattr(
        proof.subprocess,
        "run",
        lambda *_a, **_k: pytest.fail("default command took a snapshot"),
    )
    proof.main(["--clone-root", str(root)])
    first = json.loads(capsys.readouterr().out)
    assert first["mode"] == "read_only_preflight" and first["apply_ready"] is False
    evidence = tmp_path / "native-review-context-v2/q01-fullworld-v1"
    original = (evidence / "preflight.json").read_bytes()
    (evidence / "source-request.json").write_text("{}")
    state["new_observation"] = True
    proof.main(["--clone-root", str(root)])
    second = json.loads(capsys.readouterr().out)
    assert second["prior_apply_checkpoint"] is True and second["apply_ready"] is False
    assert (evidence / "preflight.json").read_bytes() == original


@pytest.mark.parametrize("unavailable", [True, False])
def test_apply_stops_before_snapshot_for_missing_capability_or_stale_pins(
    tmp_path, monkeypatch, unavailable
):
    root = tmp_path / "working"
    root.mkdir()
    evidence = tmp_path / "native-review-context-v2/q01-fullworld-v1"
    evidence.mkdir(parents=True)
    state = {"statement_kernel_available": not unavailable}
    (evidence / "preflight.json").write_text(json.dumps(state))
    monkeypatch.setattr(proof, "preflight", lambda _: deepcopy(state))
    monkeypatch.setattr(
        proof,
        "retained_inputs",
        lambda *_: pytest.fail("snapshot inputs loaded after failed guard"),
    )
    monkeypatch.setattr(
        proof.subprocess,
        "run",
        lambda *_a, **_k: pytest.fail("snapshot executed after failed guard"),
    )
    with pytest.raises(
        ValueError, match="lacks statement kernel" if unavailable else "pins changed"
    ):
        proof.main(
            ["--clone-root", str(root), "--apply", "--preflight-sha256", "wrong-pins"]
        )
    assert not (evidence / "native-before.dump").exists()
