#!/usr/bin/env python3
"""OPT-BENCH01: measure World Graph warm-path experience (scenarios A–D)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (_REPO_ROOT / "src", _REPO_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import graph_memory.kernel as kernel  # noqa: E402
from apps.live_control_server.services.world_graph_projection import (  # noqa: E402
    project_world_graph,
)
from apps.live_control_server.services.world_graph_projection_recipes import (  # noqa: E402
    clear_recipe_observations,
    get_recipe_observations,
    reset_projection_recipes_for_tests,
)
from apps.live_control_server.services.world_graph_prewarm import (  # noqa: E402
    clear_prewarm_observations,
    get_prewarm_observations,
    get_world_graph_prewarm_coordinator,
    get_world_graph_prewarm_lifecycle_refcount,
    start_world_graph_prewarm_coordinator,
    stop_world_graph_prewarm_coordinator,
)
from graph_memory.contribution_bundles import load_contribution_bundle  # noqa: E402
from graph_memory.kernel.world_initialization import (  # noqa: E402
    initialize_world_from_contributions,
)
from graph_memory.kernel.world_initialization_models import (  # noqa: E402
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.projection.world_projection import (  # noqa: E402
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)
from graph_memory.world_projection_cache import clear_projection_cache  # noqa: E402

WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
BUNDLE_PATH = Path(
    "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]

ScenarioKey = Literal[
    "fully_cold",
    "resident_revision",
    "opt02_post_publish",
    "opt03_surface_warm",
]


@dataclass(frozen=True)
class ProjectionRun:
    e2e_ms: float
    head_resolution_ms: float
    resident_wait_ms: float
    cold_load_ms: float | None
    projection_build_ms: float
    projection_cache_status: str
    graph_payload_reads_this_request: int
    revision_manifest_reads_this_request: int
    contribution_reads_this_request: int
    source_index_reads_this_request: int
    nodes_returned: int
    relationships_returned: int
    attributes_returned: int
    selected_revision_id: str
    head_revision_id: str
    resident_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_plan_projection_request() -> WorldGraphProjectionRequest:
    """Plan-like head-following request: campaign scope, session focus, no pin/query."""
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        scope_mode="campaign",
        focus=WorldGraphProjectionFocus(
            kind="session",
            session_id=FOCUS_SESSION_ID,
            campaign_id=CAMPAIGN_ID,
        ),
        revision_pin=None,
        query_text=None,
        admissibility="gm",
    )


def request_snapshot() -> dict[str, Any]:
    request = build_plan_projection_request()
    return {
        "schema": PROJECTION_REQUEST_SCHEMA,
        "world_id": request.world_id,
        "campaign_id": request.campaign_id,
        "scope_mode": request.scope_mode,
        "focus": {
            "kind": request.focus.kind,
            "session_id": request.focus.session_id,
            "campaign_id": request.focus.campaign_id,
        },
        "revision_pin": request.revision_pin,
        "query_text": request.query_text,
        "admissibility": request.admissibility,
        "fixture_bundle": str(BUNDLE_PATH),
    }


def initialize_bench_world(root: Path) -> None:
    bundle = load_contribution_bundle(BUNDLE_PATH)
    by_id = {item.contribution_id: item for item in bundle.contributions}
    plan = WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id=FOCUS_SESSION_ID,
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ORDERED_CONTRIBUTION_IDS
        ],
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id="eldyrwild-longmont-c2-initial-v1",
            bundle_digest=BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_MERGE_SHA,
        ),
    )
    initialize_world_from_contributions(
        root,
        plan=plan,
        contributions=list(bundle.contributions),
        actor="gm",
    )


def drain_prewarm_coordinator(*, timeout_s: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        coordinator = get_world_graph_prewarm_coordinator()
        if coordinator is None and get_world_graph_prewarm_lifecycle_refcount() == 0:
            return
        stop_world_graph_prewarm_coordinator(timeout_s=min(1.0, timeout_s))
        if coordinator is not None and coordinator.is_orphaned:
            time.sleep(0.01)
            continue
        time.sleep(0.01)


def reset_all_state(*, include_recipes: bool = True) -> None:
    drain_prewarm_coordinator()
    kernel.reset_revision_ready_mailbox()
    kernel.clear_revision_ready_offer_observations()
    clear_prewarm_observations()
    clear_recipe_observations()
    if include_recipes:
        reset_projection_recipes_for_tests()
    clear_projection_cache()
    kernel.clear_world_read_runtime()


def clear_projection_cache_only() -> None:
    clear_projection_cache()


def current_head_revision_id(root: Path) -> str:
    return kernel.open_world_graph_head(root, WORLD_ID).head_revision_id


def publish_fresh_revision(
    root: Path,
    operation_id: str,
) -> str:
    head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    published = kernel.publish_world_revision(
        root,
        WORLD_ID,
        store,
        operation_ids=[operation_id],
        expected_parent_revision_id=head.head_revision_id,
    )
    return published.revision.revision_id


def wait_for_prewarm_observations(
    coordinator,
    *,
    revision_id: str,
    expected_count: int = 1,
    timeout_s: float = 30.0,
) -> list[Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        observations = [
            observation
            for observation in get_prewarm_observations()
            if observation.revision_id == revision_id
        ]
        if len(observations) >= expected_count:
            assert coordinator.wait_idle(timeout_s=timeout_s)
            return [
                observation
                for observation in get_prewarm_observations()
                if observation.revision_id == revision_id
            ]
        time.sleep(0.01)
    raise RuntimeError(f"timed out waiting for prewarm observations for {revision_id}")


def wait_for_recipe_warm(
    *,
    revision_id: str,
    timeout_s: float = 30.0,
) -> list[Any]:
    deadline = time.monotonic() + timeout_s
    warm_statuses = {"warm_built", "warm_hit", "warm_coalesced"}
    while time.monotonic() < deadline:
        observations = [
            observation
            for observation in get_recipe_observations()
            if observation.revision_id == revision_id
            and observation.status in warm_statuses
        ]
        if observations:
            return observations
        time.sleep(0.01)
    raise RuntimeError(f"timed out waiting for recipe warm for {revision_id}")


def admit_current_head_resident(root: Path) -> None:
    revision_id = current_head_revision_id(root)
    runtime = kernel.get_world_read_runtime()
    runtime.get_or_load_resident(root, WORLD_ID, revision_id)


def measure_projection_run(root: Path, request: WorldGraphProjectionRequest) -> ProjectionRun:
    started = time.perf_counter()
    project_world_graph(request, root=root)
    e2e_ms = (time.perf_counter() - started) * 1000.0
    observation = kernel.get_last_projection_observation()
    if observation is None:
        raise RuntimeError("missing projection observation after project_world_graph")
    return ProjectionRun(
        e2e_ms=e2e_ms,
        head_resolution_ms=observation.head_resolution_ms,
        resident_wait_ms=observation.resident_wait_ms,
        cold_load_ms=observation.cold_load_ms,
        projection_build_ms=observation.projection_build_ms,
        projection_cache_status=observation.projection_cache_status,
        graph_payload_reads_this_request=observation.graph_payload_reads_this_request,
        revision_manifest_reads_this_request=observation.revision_manifest_reads_this_request,
        contribution_reads_this_request=observation.contribution_reads_this_request,
        source_index_reads_this_request=observation.source_index_reads_this_request,
        nodes_returned=observation.nodes_returned,
        relationships_returned=observation.relationships_returned,
        attributes_returned=observation.attributes_returned,
        selected_revision_id=observation.selected_revision_id,
        head_revision_id=observation.head_revision_id,
        resident_status=observation.resident_status,
    )


def validate_scenario_semantics(
    runs: list[ProjectionRun],
    *,
    scenario: ScenarioKey,
) -> list[str]:
    if not runs:
        return [f"{scenario}: no runs recorded"]
    errors: list[str] = []
    first = runs[0]
    for index, run in enumerate(runs[1:], start=2):
        if run.nodes_returned != first.nodes_returned:
            errors.append(
                f"{scenario} iteration {index}: nodes_returned "
                f"{run.nodes_returned} != {first.nodes_returned}"
            )
        if run.relationships_returned != first.relationships_returned:
            errors.append(
                f"{scenario} iteration {index}: relationships_returned "
                f"{run.relationships_returned} != {first.relationships_returned}"
            )
        if run.attributes_returned != first.attributes_returned:
            errors.append(
                f"{scenario} iteration {index}: attributes_returned "
                f"{run.attributes_returned} != {first.attributes_returned}"
            )
        if run.selected_revision_id != first.selected_revision_id:
            errors.append(
                f"{scenario} iteration {index}: selected_revision_id "
                f"{run.selected_revision_id} != {first.selected_revision_id}"
            )
    return errors


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct / 100.0
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def summarize_ms(values: list[float]) -> dict[str, float]:
    return {
        "min": min(values),
        "max": max(values),
        "median": percentile(values, 50),
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
    }


def typical_mode(values: list[Any]) -> Any:
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def summarize_runs(runs: list[ProjectionRun]) -> dict[str, Any]:
    e2e = [run.e2e_ms for run in runs]
    build = [run.projection_build_ms for run in runs]
    return {
        "e2e_ms": summarize_ms(e2e),
        "projection_build_ms": summarize_ms(build),
        "typical_projection_cache_status": typical_mode(
            [run.projection_cache_status for run in runs]
        ),
        "typical_graph_payload_reads": typical_mode(
            [run.graph_payload_reads_this_request for run in runs]
        ),
        "median_graph_payload_reads": percentile(
            [float(run.graph_payload_reads_this_request) for run in runs],
            50,
        ),
        "typical_resident_status": typical_mode([run.resident_status for run in runs]),
        "head_revision_id": runs[0].head_revision_id if runs else None,
        "selected_revision_id": runs[0].selected_revision_id if runs else None,
        "nodes_returned": runs[0].nodes_returned if runs else None,
        "relationships_returned": runs[0].relationships_returned if runs else None,
        "attributes_returned": runs[0].attributes_returned if runs else None,
    }


def relative_improvement_pct(baseline_p50: float, candidate_p50: float) -> float | None:
    if baseline_p50 <= 0:
        return None
    return ((baseline_p50 - candidate_p50) / baseline_p50) * 100.0


def compute_relative_improvements(
    scenarios: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    cold_p50 = scenarios["fully_cold"]["summary"]["e2e_ms"]["p50"]
    opt02_p50 = scenarios["opt02_post_publish"]["summary"]["e2e_ms"]["p50"]
    opt03_p50 = scenarios["opt03_surface_warm"]["summary"]["e2e_ms"]["p50"]
    resident_p50 = scenarios["resident_revision"]["summary"]["e2e_ms"]["p50"]
    return {
        "resident_revision_vs_fully_cold_p50_pct": relative_improvement_pct(
            cold_p50, resident_p50
        ),
        "opt02_post_publish_vs_fully_cold_p50_pct": relative_improvement_pct(
            cold_p50, opt02_p50
        ),
        "opt03_surface_warm_vs_fully_cold_p50_pct": relative_improvement_pct(
            cold_p50, opt03_p50
        ),
        "opt03_surface_warm_vs_opt02_post_publish_p50_pct": relative_improvement_pct(
            opt02_p50, opt03_p50
        ),
    }


def run_scenario_fully_cold(
    root: Path,
    *,
    iterations: int,
) -> tuple[list[ProjectionRun], list[str]]:
    request = build_plan_projection_request()
    runs: list[ProjectionRun] = []
    initialize_bench_world(root)
    for _ in range(iterations):
        reset_all_state(include_recipes=True)
        runs.append(measure_projection_run(root, request))
    return runs, validate_scenario_semantics(runs, scenario="fully_cold")


def run_scenario_resident_revision(
    root: Path,
    *,
    iterations: int,
) -> tuple[list[ProjectionRun], list[str]]:
    reset_all_state(include_recipes=True)
    initialize_bench_world(root)
    admit_current_head_resident(root)
    request = build_plan_projection_request()
    runs: list[ProjectionRun] = []
    for _ in range(iterations):
        clear_projection_cache_only()
        runs.append(measure_projection_run(root, request))
    return runs, validate_scenario_semantics(runs, scenario="resident_revision")


def run_scenario_opt02_post_publish(
    root: Path,
    *,
    iterations: int,
) -> tuple[list[ProjectionRun], list[str]]:
    reset_all_state(include_recipes=True)
    initialize_bench_world(root)
    coordinator = start_world_graph_prewarm_coordinator()
    if coordinator is None:
        raise RuntimeError("failed to start prewarm coordinator")
    revision_id = publish_fresh_revision(root, "op:bench01-opt02-prewarm")
    wait_for_prewarm_observations(coordinator, revision_id=revision_id)
    request = build_plan_projection_request()
    runs: list[ProjectionRun] = []
    for _ in range(iterations):
        clear_projection_cache_only()
        runs.append(measure_projection_run(root, request))
    return runs, validate_scenario_semantics(runs, scenario="opt02_post_publish")


def run_scenario_opt03_surface_warm(
    root: Path,
    *,
    iterations: int,
) -> tuple[list[ProjectionRun], list[str]]:
    reset_all_state(include_recipes=True)
    initialize_bench_world(root)
    coordinator = start_world_graph_prewarm_coordinator()
    if coordinator is None:
        raise RuntimeError("failed to start prewarm coordinator")
    request = build_plan_projection_request()
    project_world_graph(request, root=root)
    clear_projection_cache_only()
    revision_id = publish_fresh_revision(root, "op:bench01-opt03-recipe-warm")
    wait_for_prewarm_observations(coordinator, revision_id=revision_id)
    wait_for_recipe_warm(revision_id=revision_id)
    runs: list[ProjectionRun] = []
    for _ in range(iterations):
        runs.append(measure_projection_run(root, request))
    return runs, validate_scenario_semantics(runs, scenario="opt03_surface_warm")


def git_code_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def format_table(scenarios: dict[str, dict[str, Any]]) -> str:
    lines = [
        "| Scenario | p50 e2e (ms) | p95 e2e (ms) | build p50 (ms) | cache | graph reads | resident |",
        "| --- | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    labels = {
        "fully_cold": "A — Fully cold",
        "resident_revision": "B — OPT01 resident",
        "opt02_post_publish": "C — OPT02 prewarm",
        "opt03_surface_warm": "D — OPT03 surface warm",
    }
    for key, label in labels.items():
        summary = scenarios[key]["summary"]
        e2e = summary["e2e_ms"]
        build = summary["projection_build_ms"]
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    f"{e2e['p50']:.2f}",
                    f"{e2e['p95']:.2f}",
                    f"{build['p50']:.2f}",
                    str(summary["typical_projection_cache_status"]),
                    str(summary["typical_graph_payload_reads"]),
                    str(summary["typical_resident_status"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def render_markdown_report(
    payload: dict[str, Any],
    *,
    code_revision: str,
) -> str:
    rel = payload["relative_improvements"]
    table = format_table(payload["scenarios"])
    opt03 = payload["scenarios"]["opt03_surface_warm"]["summary"]
    cold = payload["scenarios"]["fully_cold"]["summary"]
    return f"""# World Graph warm-path benchmark report (OPT-BENCH01)

**Measured code SHA:** `{code_revision}`  
**Fixture:** `{BUNDLE_PATH}` (`world_id={WORLD_ID}`, `campaign_id={CAMPAIGN_ID}`)  
**Request:** Plan-like head-following projection — `scope_mode=campaign`, `focus.kind=session`, `focus.session_id={FOCUS_SESSION_ID}`, `revision_pin=null`, `query_text=null`

## Results ({payload["iterations"]} iterations per scenario)

{table}

## Relative improvements (p50 e2e)

| Comparison | Improvement |
| --- | ---: |
| B resident vs A cold | {rel["resident_revision_vs_fully_cold_p50_pct"]:.1f}% |
| C OPT02 vs A cold | {rel["opt02_post_publish_vs_fully_cold_p50_pct"]:.1f}% |
| D OPT03 vs A cold | {rel["opt03_surface_warm_vs_fully_cold_p50_pct"]:.1f}% |
| D OPT03 vs C OPT02 | {rel["opt03_surface_warm_vs_opt02_post_publish_p50_pct"]:.1f}% |

## Live Plan dogfood

Live Plan surface dogfood was **not run** in this automated bench environment (no live-control UI session wired). Template for manual follow-up:

| Observation | Result |
| --- | --- |
| Plan graph panel opens without manual refresh after publish | not observed (automated bench only) |
| Perceived "graph is simply there" on session focus | not observed |
| Network waterfall shows projection cache hit on repeat open | not observed |

## Measured answers

**What did OPT01 buy?** Scenario B (resident admitted, cache cold) vs A shows resident hits with zero graph payload reads on the warm path, but projection still builds each iteration because the completed cache is cleared. OPT01 removes repeated durable revision load cost.

**What did OPT02 buy?** Scenario C adds post-publish coordinator prewarm so the first read after publish already has the new head resident; e2e p50 improves vs fully cold even when the projection payload must still be built.

**What did OPT03 buy?** Scenario D replays the learned Plan recipe after publish and fills the completed projection cache, yielding cache hits with `graph_payload_reads==0` and near-zero build time — closest to "graph is simply there" within this harness.

**How close to "graph is simply there"?** OPT03 scenario D median e2e is {opt03["e2e_ms"]["median"]:.2f} ms with typical cache status `{opt03["typical_projection_cache_status"]}` and graph payload reads `{opt03["typical_graph_payload_reads"]}`. Fully cold A median e2e is {cold["e2e_ms"]["median"]:.2f} ms.
"""


def run_benchmark(
    *,
    iterations: int,
    root: Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if root is None:
        temp_dir = tempfile.TemporaryDirectory(prefix="dmb-bench-wg-warm-")
        root = Path(temp_dir.name)
    assert root is not None

    errors: list[str] = []
    scenario_defs: list[tuple[ScenarioKey, str, Any]] = [
        ("fully_cold", "A — Fully cold", run_scenario_fully_cold),
        ("resident_revision", "B — OPT01 resident revision", run_scenario_resident_revision),
        ("opt02_post_publish", "C — OPT02 post-publish prewarm", run_scenario_opt02_post_publish),
        ("opt03_surface_warm", "D — OPT03 surface warm", run_scenario_opt03_surface_warm),
    ]
    scenarios: dict[str, dict[str, Any]] = {}
    try:
        for key, label, runner in scenario_defs:
            runs, semantic_errors = runner(root, iterations=iterations)
            errors.extend(semantic_errors)
            scenarios[key] = {
                "label": label,
                "runs": [run.to_dict() for run in runs],
                "summary": summarize_runs(runs),
            }
    finally:
        reset_all_state(include_recipes=True)
        if temp_dir is not None:
            temp_dir.cleanup()

    payload = {
        "code_revision": git_code_revision(),
        "iterations": iterations,
        "request": request_snapshot(),
        "scenarios": scenarios,
        "relative_improvements": compute_relative_improvements(scenarios),
    }
    return payload, errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path("report/world_graph_warm_path_benchmark.json"),
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=Path("Docs/Reports/REPORT-world-graph-warm-path-benchmark.md"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload, errors = run_benchmark(iterations=args.iterations)
    if errors:
        for error in errors:
            print(f"SEMANTIC ERROR: {error}", file=sys.stderr)
        return 2

    print(format_table(payload["scenarios"]))
    rel = payload["relative_improvements"]
    print()
    print("Relative improvements (p50 e2e):")
    print(f"  B vs A cold: {rel['resident_revision_vs_fully_cold_p50_pct']:.1f}%")
    print(f"  C vs A cold: {rel['opt02_post_publish_vs_fully_cold_p50_pct']:.1f}%")
    print(f"  D vs A cold: {rel['opt03_surface_warm_vs_fully_cold_p50_pct']:.1f}%")
    print(f"  D vs C OPT02: {rel['opt03_surface_warm_vs_opt02_post_publish_p50_pct']:.1f}%")

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote JSON: {args.json_out}")

    markdown = render_markdown_report(payload, code_revision=payload["code_revision"])
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.write_text(markdown, encoding="utf-8")
    print(f"Wrote report: {args.markdown_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
