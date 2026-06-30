from __future__ import annotations

import json
from dataclasses import asdict

from .mirathorn_city_world_doc_fixture import *

READY = [
    "manifest",
    "world doc source snapshot",
    "explicit path boundary",
    "source span seed refs",
    "source evidence openability",
    "source evidence highlightability",
    "expected phrase checks",
    "no heading-only evidence refs",
    "no full source leakage",
    "no absolute path leakage",
    "no corpus mutation",
    "no graph output",
    "no extraction/LLM output",
    "no adapter/plan/agent/runtime leakage",
    "mirathorn city world doc fixture",
]


def validate_all() -> None:
    manifest = load_manifest()
    validate_manifest(manifest)
    source = load_source_doc(manifest)
    assert source.strip() and "Mirathorn" in source
    seed = load_source_span_seed_refs()
    assert seed["schema"] == SOURCE_SPAN_SEED_SCHEMA and seed["version"] == "0.1"
    refs = seed["source_span_refs"]
    assert len(refs) >= seed["expected"]["total_refs_min"] >= 22
    anchors = [r["source_anchor_id"] for r in refs]
    assert len(anchors) == len(set(anchors))
    resolved = resolve_source_span_seed_refs()
    assert len(resolved) == len(refs)
    by_anchor = {r["source_anchor_id"]: r for r in refs}
    for ev in resolved:
        assert ev.can_open_source and ev.can_highlight_span and ev.preview_snippet and not ev.warnings
        assert not ev.preview_snippet.strip().startswith("#")
        assert len(ev.preview_snippet) <= 240
        assert by_anchor[ev.source_anchor_id]["expected_phrase"] in ev.preview_snippet
    serialized = json.dumps([asdict(r) for r in resolved], ensure_ascii=False)
    assert source not in serialized and str(repo_root()) not in serialized
    text = json.dumps(seed) + serialized
    for token in (
        '"nodes"',
        '"edges"',
        '"proposed_writes"',
        "gold_graph",
        "llm_generated",
        '"approved"',
        '"promoted"',
        "/plan",
        "agent_interaction",
        "runtime_ui",
        "query_execution",
        "corpus_mutation",
    ):
        assert token not in text


def main() -> int:
    validate_all()
    print("Graph Memory Mirathorn city world doc fixture validation")
    for item in READY:
        print(f"- {item}: ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
