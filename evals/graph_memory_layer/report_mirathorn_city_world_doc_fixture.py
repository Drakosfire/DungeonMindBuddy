from __future__ import annotations

from .mirathorn_city_world_doc_fixture import *


def _clip(s: str, n: int = 110) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def main() -> int:
    manifest = load_manifest()
    validate_manifest(manifest)
    source = load_source_doc(manifest)
    refs = parse_source_span_seed_refs()
    resolved = resolve_source_span_seed_refs()
    print("# Mirathorn City World Doc Fixture Report\n")
    print("## Summary\n\n| Metric | Value |\n|---|---|")
    rows = [
        ("Fixture ID", FIXTURE_ID),
        ("Source doc path", SOURCE_DOC_REL),
        ("Source line count", len(source.splitlines())),
        ("Source span refs", len(refs)),
        ("Resolved span refs", len(resolved)),
    ]
    for k, v in rows:
        print(f"| {k} | {v} |")
    by = {r.source_anchor_id: r for r in resolved}
    seed = load_source_span_seed_refs()
    print("\n## Source Span Seeds\n\n| Anchor | Lines | Expected Phrase | Snippet Preview |\n|---|---|---|---|")
    for ref in seed["source_span_refs"]:
        ev = by[ref["source_anchor_id"]]
        print(f"| {ref['source_anchor_id']} | {ev.start_line}-{ev.end_line} | {ref['expected_phrase']} | {_clip(ev.preview_snippet)} |")
    print("\n## Boundary Statement\n")
    for line in [
        "This is a worldbuilding doc snapshot fixture for Graph Memory.",
        "It does not call an LLM.",
        "It does not run the live planner.",
        "It does not write corpus files.",
        "It does not mutate canonical corpus.",
        "It does not extract entities.",
        "It does not infer relationships.",
        "It does not produce a candidate graph.",
        "It does not produce a gold graph.",
        "It does not promote facts or canon.",
        "It does not connect `/plan`.",
        "It does not connect Agent Interaction.",
        "It does not change runtime behavior.",
    ]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
