from evals.old_bath_house.compare import CHECKS, PHASES, compare, summarize
from evals.old_bath_house.isolation import source_fixture_digest


def record(run_id, *, timing=10, **overrides):
    return {
        "run_id": run_id,
        "track": "pinned-assets",
        "fixture_digest": "fixture-v1",
        "conditions": "fresh-browser-context",
        "checks": dict.fromkeys(CHECKS, True),
        "timings_ms": dict.fromkeys(PHASES["pinned-assets"], timing),
        **overrides,
    }


def test_rejected_correctness_run_does_not_enter_performance_distribution():
    invalid = record("invalid", timing=1, checks=dict.fromkeys(CHECKS, False))
    valid = record("valid", timing=10)
    baseline = summarize([invalid, valid])
    candidate = summarize([record("candidate", timing=12)])
    report, = compare(baseline, candidate)
    assert report["baseline"]["accepted_runs"] == 1
    assert "invalid" in report["baseline"]["rejected"]
    assert report["median_delta_ms"]["combat_start"] == 2
    assert report["candidate"]["phases_ms"]["combat_start"]["p95"] is None


def test_logical_fixture_identity_ignores_buddy_release():
    original = {"runtime": {"source": "before"}, "worldId": "elderwyld"}
    candidate = {**original, "runtime": {"source": "after"}}
    assert source_fixture_digest(original, ["capture"]) == source_fixture_digest(candidate, ["capture"])
    assert source_fixture_digest(original, ["capture"]) != source_fixture_digest(candidate, ["changed"])


def test_runtime_state_is_copied_and_symlinks_are_refused(tmp_path):
    import pytest

    from evals.old_bath_house.run import STATE_DIRECTORIES, copy_runtime_state

    fixture = tmp_path / "fixture"
    for directory in STATE_DIRECTORIES:
        (fixture / directory).mkdir(parents=True)
    artifact = fixture / "artifacts" / "saved.json"
    artifact.write_text("source bytes")
    copied = tmp_path / "copy"
    copy_runtime_state(fixture, copied)
    (copied / "artifacts" / artifact.name).write_text("running bytes")
    assert artifact.read_text() == "source bytes"
    (fixture / "sessions" / "link").symlink_to(artifact)
    with pytest.raises(ValueError, match="symlink"):
        copy_runtime_state(fixture, tmp_path / "second-copy")
    assert not (tmp_path / "second-copy").exists()
