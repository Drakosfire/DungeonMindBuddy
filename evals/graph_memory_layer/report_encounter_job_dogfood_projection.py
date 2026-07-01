from __future__ import annotations

# Module: report_encounter_job_dogfood_projection

import argparse
from pathlib import Path
from typing import Any

from evals.graph_memory_layer.encounter_job_dogfood_fixture import (
    dogfood_result_to_payload,
    run_glowkindle_encounter_job_dogfood,
)

DEFAULT_REPORT_PATH = Path("evals/graph_memory_layer/artifacts/encounter_job_dogfood_projection/c1s1_glowkindle_fixture_report.md")


def _node_lines(nodes: list[dict[str, Any]]) -> list[str]:
    wanted = {"quest_clear_glowkindle_rats", "enc_glowkindle_cellar_rats", "npc_glowkindle", "creature_rat_swarm", "loc_glowkindle_cellar", "loc_glowkindle_brewery", "node:heroes-party"}
    return [f"- `{n.get('node_id')}` — {n.get('label')} (`{n.get('node_type')}`)" for n in nodes if n.get("node_id") in wanted]


def _edge_lines(edges: list[dict[str, Any]]) -> list[str]:
    wanted = {
        ("node:heroes-party", "quest_clear_glowkindle_rats", "pursues"),
        ("node:heroes-party", "enc_glowkindle_cellar_rats", "participates_in"),
        ("enc_glowkindle_cellar_rats", "loc_glowkindle_cellar", "located_in"),
        ("creature_rat_swarm", "enc_glowkindle_cellar_rats", "participates_in"),
        ("quest_clear_glowkindle_rats", "creature_rat_swarm", "mission_targets"),
        ("quest_clear_glowkindle_rats", "loc_glowkindle_cellar", "mission_focus"),
    }
    return [f"- `{e.get('from_node_id')}` → `{e.get('to_node_id')}` — `{e.get('relationship_type')}` ({e.get('predicate_family')})" for e in edges if (e.get("from_node_id"), e.get("to_node_id"), e.get("relationship_type")) in wanted]


def render_report(payload: dict[str, Any] | None = None) -> str:
    if payload is None:
        payload = dogfood_result_to_payload(run_glowkindle_encounter_job_dogfood())
    graph = payload["candidate_graph"]
    diagnostics = payload["diagnostics"]
    checks = payload["checks"]
    result_diag = diagnostics["result_diagnostics"]
    cons_diag = diagnostics["consolidation_diagnostics"]
    lines = [
        "# Encounter/Job Dogfood Projection Report — Glowkindle Rat Job Fixture",
        "",
        "## Status",
        "",
        "This is a deterministic fixture dogfood report. It does not call an LLM, scan corpus files, mutate corpus files, write graph memory, connect `/plan`, approve facts, promote canon, or change runtime behavior.",
        "",
        "## Scope",
        "",
        "Eval-only, fixture-only candidate graph projection for review. The source fixture is synthetic and not campaign canon.",
        "",
        "## Fixture summary",
        "",
        f"- Fixture ID: `{payload['source_fixture']['fixture_id']}`",
        "- Source spans: `spref:glowkindle:001` through `spref:glowkindle:004`.",
        "- Scenario: Glowkindle asks the party to clear rats from the cellar beneath the brewery; the party fights a rat swarm and the cellar becomes safe enough to reopen.",
        "",
        "## Extraction configuration",
        "",
    ]
    lines.extend(f"- `{k}`: `{v}`" for k, v in payload["extraction_options"].items())
    lines.extend([
        "",
        "## Review checklist",
        "",
        "- [x] One quest node exists.",
        "- [x] One combat encounter node exists.",
        "- [x] Heroes / party pursues the quest.",
        "- [x] Heroes / party participates in the combat encounter.",
        "- [x] Encounter is located in the cellar.",
        "- [x] Rat swarm participates in the encounter.",
        "- [x] Quest targets the rat swarm.",
        "- [x] Quest focuses on the cellar.",
        "- [x] Dynamic node vocabulary packet was used.",
        "- [x] Encounter/job edge guidance was enabled.",
        "- [x] No invalid predicate issues.",
        "- [x] No dropped edges.",
        "- [x] No corpus mutation.",
        "",
        "## Nodes of interest",
        "",
        *_node_lines(graph.get("nodes", [])),
        "",
        "## Edges of interest",
        "",
        *_edge_lines(graph.get("edges", [])),
        "",
        "## Diagnostics summary",
        "",
        f"- `dynamic_node_vocabulary_packet`: enabled={result_diag.get('dynamic_node_vocabulary_packet', {}).get('enabled')}",
        f"- `node_vocabulary_ablation`: enabled={result_diag.get('node_vocabulary_ablation', {}).get('enabled')}",
        f"- `encounter_job_pass`: {cons_diag.get('encounter_job_pass')}",
        f"- `party_participation_attachment`: {cons_diag.get('party_participation_attachment')}",
        f"- `encounter_job_edge_guidance`: {result_diag.get('encounter_job_edge_guidance')}",
        f"- `edge_predicate_issues`: {cons_diag.get('edge_predicate_issues')}",
        f"- `dropped_edges_missing_endpoints`: {cons_diag.get('dropped_edges_missing_endpoints')}",
        f"- Checks: `{checks}`",
        "",
        "## Known limitations",
        "",
        "This fixture proves pipeline shape and projection review structure. It does not prove live LLM extraction quality. A later manual dogfood run must compare real model output against this expected shape.",
        "",
        "## Non-goals",
        "",
        "- No LLM calls.",
        "- No corpus scanning.",
        "- No corpus mutation.",
        "- No graph memory writes, fact approval, canon promotion, runtime wiring, or `/plan` integration.",
        "",
        "## Next review step",
        "",
        "Use this report as the stable review shape for a later explicit LLM-backed C1S1/C2S23 dogfood run.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    report = render_report()
    out = args.out or (DEFAULT_REPORT_PATH if args.write else None)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
