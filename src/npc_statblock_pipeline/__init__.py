"""NPC statblock upgrade pipeline — corpus-policy-driven, benchmark-agnostic.

Benchmarks (e.g. ``evals/lysandra_vertical_slice``) load JSON policy + gold and call
these functions; nothing here reads slice-specific paths on disk.
"""

from __future__ import annotations

from src.npc_statblock_pipeline.canonical_intent import (
    IntentClassification,
    IntentMode,
    PowerAxis,
    build_extracted_section_span,
    build_selection_reason,
    classify_intent,
    detail_for_cli_stdout,
    parse_challenge_rating_from_statblock,
    read_paths_from_tool_trace,
    run_step2_all,
    run_step2_canonical_gates,
    run_step2_intent_fixture_gates,
    run_step2_planner_bridge,
    select_canonical_statblock_relpath,
    statblock_trace_reads_matching_policy,
)

__all__ = [
    "IntentClassification",
    "IntentMode",
    "PowerAxis",
    "build_extracted_section_span",
    "build_selection_reason",
    "classify_intent",
    "detail_for_cli_stdout",
    "parse_challenge_rating_from_statblock",
    "read_paths_from_tool_trace",
    "run_step2_all",
    "run_step2_canonical_gates",
    "run_step2_intent_fixture_gates",
    "run_step2_planner_bridge",
    "select_canonical_statblock_relpath",
    "statblock_trace_reads_matching_policy",
]
