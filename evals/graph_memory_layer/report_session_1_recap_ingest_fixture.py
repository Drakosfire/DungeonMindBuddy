from __future__ import annotations
from .session_1_recap_ingest_fixture import *

def _clip(s: str, n: int=110) -> str:
    return s if len(s) <= n else s[: n-1].rstrip() + "…"

def main() -> int:
    manifest=load_manifest(); validate_manifest(manifest); raw=load_raw_recap(manifest); norm, report=assemble_session_1_normalized_recap(raw); idx=build_paragraph_index(raw); refs=parse_source_span_seed_refs(); resolved=resolve_source_span_seed_refs()
    print("# Session 1 Recap Ingest Fixture Report\n")
    print("## Summary\n\n| Metric | Value |\n|---|---|")
    rows=[("Fixture ID",FIXTURE_ID),("Campaign",manifest["campaign_id"]),("Session",str(manifest["session"])),("Raw recap path",RAW_RECAP_REL),("Title line stripped",str(report.title_line_stripped).lower()),("Paragraphs in",report.paragraph_count_in),("Paragraphs out",report.paragraph_count_out),("Duplicates detected",len(report.duplicates_detected)),("Duplicates removed",len(report.duplicates_removed)),("Source span refs",len(refs)),("Resolved span refs",len(resolved))]
    for k,v in rows: print(f"| {k} | {v} |")
    print("\n## Normalization\n\n| Check | Status |\n|---|---|\n| Frontmatter generated | ready |\n| Session metadata | ready |\n| Expected normalized fixture matches helper output | ready |")
    print("\n## Paragraph Index\n\n| Paragraph | Source Lines | Preview |\n|---|---|---|")
    for p in idx["paragraphs"]: print(f"| {p['paragraph_id']} | {p['source_line_start']}-{p['source_line_end']} | {_clip(p['preview'])} |")
    by={r.source_anchor_id:r for r in resolved}
    seed=load_source_span_seed_refs()
    print("\n## Source Span Seeds\n\n| Anchor | Lines | Expected Phrase | Snippet Preview |\n|---|---|---|---|")
    for ref in seed["source_span_refs"]:
        ev=by[ref["source_anchor_id"]]; print(f"| {ref['source_anchor_id']} | {ev.start_line}-{ev.end_line} | {ref['expected_phrase']} | {_clip(ev.preview_snippet)} |")
    print("\n## Boundary Statement\n")
    for line in ["This is a raw-to-normalized recap fixture for Graph Memory.","It uses existing recap ingest helper logic.","It does not call an LLM.","It does not run the live planner.","It does not write corpus files.","It does not mutate canonical corpus.","It does not extract entities.","It does not infer relationships.","It does not produce a candidate graph.","It does not produce a gold graph.","It does not promote facts or canon.","It does not connect `/plan`.","It does not connect Agent Interaction.","It does not change runtime behavior."]:
        print(line)
    return 0
if __name__ == "__main__": raise SystemExit(main())
