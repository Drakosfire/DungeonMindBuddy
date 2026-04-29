"""Split Stage B — discourse state (B1) + deterministic routing from discourse (B2)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SLICE = _REPO / "evals" / "sentence_routing_retrieval_falsification"
_DISCOURSE_SMOKE = _SLICE / "gold" / "scenario_discourse_smoke.json"


def test_discourse_reducer_maps_explicit_pc_to_manifest_slug() -> None:
    from evals.sentence_routing_retrieval_falsification.discourse_reducer import routes_from_discourse_rows
    from evals.sentence_routing_retrieval_falsification.discourse_schema import DiscourseRow

    row = DiscourseRow(
        unit_id="u1",
        discourse_mode="explicit_pc",
        direct_pc_slugs=["pc_alice"],
        rationale="Alice acts.",
    )
    manifest = [
        {
            "slug": "pc_alice",
            "path": "evals/sentence_routing_retrieval_falsification/README.md",
            "subject_class": "pc",
            "label": "Alice",
        },
        {
            "slug": "npc_x",
            "path": "evals/sentence_routing_retrieval_falsification/fixtures/mini_recap.md",
            "subject_class": "npc",
            "label": "X",
        },
    ]
    out = routes_from_discourse_rows([row], manifest_jsonable=manifest)
    routes = out.get("routes") or []
    assert len(routes) == 1
    assert routes[0]["unit_id"] == "u1"
    assert routes[0]["assigned_hubs"] == ["pc_alice"]
    assert routes[0]["routing_diagnostic_bucket"] is None


def test_discourse_reducer_party_expansion_requires_session_roster() -> None:
    from evals.sentence_routing_retrieval_falsification.discourse_reducer import routes_from_discourse_rows
    from evals.sentence_routing_retrieval_falsification.discourse_schema import DiscourseRow

    row = DiscourseRow(
        unit_id="u-party",
        discourse_mode="explicit_party",
        collective_actor="the_party",
        party_expansion_allowed=True,
        rationale="The party advances.",
    )
    manifest = [
        {"slug": "pc_alice", "path": "x.md", "subject_class": "pc", "label": "Alice"},
        {"slug": "pc_bob", "path": "y.md", "subject_class": "pc", "label": "Bob"},
    ]

    no_roster = routes_from_discourse_rows([row], manifest_jsonable=manifest)
    assert no_roster["routes"][0]["assigned_hubs"] == []

    with_roster = routes_from_discourse_rows(
        [row],
        manifest_jsonable=manifest,
        session_pc_roster_slugs=["pc_alice", "pc_bob"],
    )
    assert with_roster["routes"][0]["assigned_hubs"] == ["the_party"]


def test_collect_discourse_content_violations_matches_expect() -> None:
    from evals.sentence_routing_retrieval_falsification.discourse_schema import DiscourseRow
    from evals.sentence_routing_retrieval_falsification.grader import (
        collect_discourse_content_violations,
        discourse_content_unit_failure_events,
    )

    rows = [
        DiscourseRow(
            unit_id="u-smoke-01",
            discourse_mode="explicit_pc",
            direct_pc_slugs=["pc_alice"],
            rationale="ok",
        ),
        DiscourseRow(
            unit_id="u-smoke-02",
            discourse_mode="true_empty",
            rationale="",
        ),
    ]
    raw = json.loads(_DISCOURSE_SMOKE.read_text(encoding="utf-8"))
    gd = raw["gold_discourse"]
    viol = collect_discourse_content_violations(rows, gd)
    assert viol == []

    rows[0].direct_pc_slugs = []
    rows[1].discourse_mode = "explicit_party"
    viol = collect_discourse_content_violations(rows, gd)
    assert "B1-CONTENT: 'u-smoke-01' direct_pc_slugs want ['pc_alice'] got []" in viol
    events = discourse_content_unit_failure_events(viol)
    assert events["by_bucket"]["b1_content_direct_pc_slugs_mismatch"] == {
        "count": 1,
        "unit_ids": ["u-smoke-01"],
    }
    assert events["by_bucket"]["b1_content_discourse_mode_mismatch"] == {
        "count": 1,
        "unit_ids": ["u-smoke-02"],
    }
    assert events["distinct_failure_unit_ids"] == ["u-smoke-01", "u-smoke-02"]


def test_grade_routes_from_fixture_discourse_passes_smoke_scenario() -> None:
    from evals.sentence_routing_retrieval_falsification.discourse_reducer import routes_from_discourse_rows
    from evals.sentence_routing_retrieval_falsification.discourse_schema import parse_discourse_envelope
    from evals.sentence_routing_retrieval_falsification.route_schema import HubManifestEntry, manifest_slug_set
    from evals.sentence_routing_retrieval_falsification.step2_route_run import (
        ROUTING_PROMPT_BASE_ID,
        grade_sentence_hub_routes_payload,
        _load_sentence_units,
    )

    raw = json.loads(_DISCOURSE_SMOKE.read_text(encoding="utf-8"))
    inp = dict(raw.get("input") or {})
    manifest_objs = [HubManifestEntry.model_validate(x) for x in inp.get("hub_manifest") or []]
    manifest_jsonable = [m.model_dump(exclude_none=True) for m in manifest_objs]
    manifest_slugs = manifest_slug_set(manifest_objs)
    units_json = _load_sentence_units(raw, _REPO, None)
    gold_routing = dict(raw.get("gold_routing") or {})

    discourse_dict = dict(raw["fixture_discourse"])
    routes_body = routes_from_discourse_rows(
        parse_discourse_envelope(discourse_dict).discourse,
        manifest_jsonable=manifest_jsonable,
    )

    passed, viol, telem, _ = grade_sentence_hub_routes_payload(
        routes_body=routes_body,
        raw=raw,
        scenario_path=_DISCOURSE_SMOKE,
        corpus_root=_REPO,
        units_json=units_json,
        manifest_jsonable=manifest_jsonable,
        manifest_slugs=manifest_slugs,
        gold_routing=gold_routing,
        routing_prompt_id=ROUTING_PROMPT_BASE_ID,
    )
    assert passed, viol
    sb = telem["stage_b_unit_breakdown"]
    assert sb.get("wire_strict_parse_ok") is True
    assert sb.get("routing_prompt_id") == ROUTING_PROMPT_BASE_ID


def test_b2_delta_attributes_missing_expected_hub_to_b1_state() -> None:
    from evals.sentence_routing_retrieval_falsification.discourse_schema import DiscourseRow
    from evals.sentence_routing_retrieval_falsification.step2b_route_from_discourse_run import (
        build_b2_delta_telemetry,
    )

    rows = [
        DiscourseRow(
            unit_id="u1",
            discourse_mode="true_empty",
            rationale="",
        )
    ]
    delta = build_b2_delta_telemetry(
        discourse_rows=rows,
        routes_out=[{"unit_id": "u1", "assigned_hubs": []}],
        manifest_pc_slugs={"pc_alice"},
        session_pc_roster_slugs=["pc_alice"],
        gold_routing={"must_route": [{"unit_id": "u1", "expected_hubs": ["pc_alice"]}]},
    )
    counts = delta["gold_failure_attribution_counts"]
    assert counts["b1_state_missing_expected_hub"] == 1
    assert counts["b2_reducer_missing_expected_hub"] == 0


def test_step2a_no_llm_passes_discourse_smoke() -> None:
    cmd = [
        sys.executable,
        "-m",
        "evals.sentence_routing_retrieval_falsification.step2a_discourse_run",
        "--scenario-json",
        str(_DISCOURSE_SMOKE),
        "--corpus-root",
        str(_REPO),
        "--no-llm",
        "--no-writes",
    ]
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_step2a_sidecar_includes_b1_content_failure_events() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        HubManifestEntry,
        manifest_slug_set,
        validate_hub_manifest,
    )
    from evals.sentence_routing_retrieval_falsification.step2_route_run import _load_sentence_units
    from evals.sentence_routing_retrieval_falsification.step2a_discourse_run import (
        run_discourse_once,
    )

    raw = json.loads(_DISCOURSE_SMOKE.read_text(encoding="utf-8"))
    broken = json.loads(json.dumps(raw))
    broken["fixture_discourse"]["discourse"][0]["direct_pc_slugs"] = []
    inp = dict(broken.get("input") or {})
    manifest_raw = list(inp.get("hub_manifest") or [])
    assert not validate_hub_manifest(manifest_raw, corpus_root=_REPO, validate_paths=True)
    manifest_objs = [HubManifestEntry.model_validate(x) for x in manifest_raw]
    manifest_jsonable = [m.model_dump(exclude_none=True) for m in manifest_objs]
    units_json = _load_sentence_units(broken, _REPO, None)

    passed, sidecar, _cost, written = run_discourse_once(
        raw=broken,
        scenario_path=_DISCOURSE_SMOKE,
        corpus_root=_REPO,
        units_json=units_json,
        manifest_jsonable=manifest_jsonable,
        manifest_slugs=manifest_slug_set(manifest_objs),
        model="fixture",
        no_llm=True,
        no_writes=True,
    )
    assert not passed
    assert written is None
    bd = sidecar["telemetry"]["stage_b1_unit_breakdown"]
    assert bd["content_failure_events"]["by_bucket"][
        "b1_content_direct_pc_slugs_mismatch"
    ] == {
        "count": 1,
        "unit_ids": ["u-smoke-01"],
    }


def test_step2b_passes_discourse_smoke_fixture() -> None:
    cmd = [
        sys.executable,
        "-m",
        "evals.sentence_routing_retrieval_falsification.step2b_route_from_discourse_run",
        "--scenario-json",
        str(_DISCOURSE_SMOKE),
        "--corpus-root",
        str(_REPO),
        "--no-writes",
    ]
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_step2b_accepts_b1_sidecar_discourse_envelope(tmp_path: Path) -> None:
    raw = json.loads(_DISCOURSE_SMOKE.read_text(encoding="utf-8"))
    sidecar = {
        "discourse_envelope": raw["fixture_discourse"],
        "schema": raw.get("schema"),
        "scenario_id": raw.get("scenario_id"),
    }
    p = tmp_path / "b1.json"
    p.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "evals.sentence_routing_retrieval_falsification.step2b_route_from_discourse_run",
        "--scenario-json",
        str(_DISCOURSE_SMOKE),
        "--corpus-root",
        str(_REPO),
        "--discourse-json",
        str(p),
        "--no-writes",
    ]
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_split_pipeline_no_llm_passes_discourse_smoke_no_writes() -> None:
    cmd = [
        sys.executable,
        "-m",
        "evals.sentence_routing_retrieval_falsification.step2_discourse_pipeline_run",
        "--scenario-json",
        str(_DISCOURSE_SMOKE),
        "--corpus-root",
        str(_REPO),
        "--n",
        "2",
        "--no-llm",
        "--no-writes",
    ]
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
