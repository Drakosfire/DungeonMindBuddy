"""Markdown report for the eval-only extractor harness fixture."""
from __future__ import annotations
from evals.graph_memory_layer import eval_only_extractor_harness as h

def _count_evidence(obj): return len(h._evidence_refs_from(obj))
def _rows(items):
    return "\n".join(f"| {a} | {b} |" for a,b in items)

def main() -> None:
    b=h.load_candidate_bundle(); m=h.load_harness_manifest(); r=h.compare_candidate_to_gold(b); g=b['assembled_candidate_graph']; resolved=h.resolve_candidate_evidence_refs(b)
    print("# Graph Memory Eval-Only Extractor Harness Fixture v0 Report\n")
    print("## Summary\n")
    print("| Field | Value |\n|---|---|")
    for a,bv in [("Harness ID",m['harness_id']),("Contract ID",m['contract_id']),("Candidate bundle",b['bundle_id']),("Gold fixture",b['gold_fixture_id']),("Execution mode",m['execution_mode'])]: print(f"| {a} | {bv} |")
    print("\n## Pass Output Summary\n\n| Pass | Schema | Candidate Count | Evidence Refs | Status |\n|---|---|---:|---:|---|")
    keys={'source_span_selection':'selected_spans','session_beat_extraction':'beat_candidates','named_entity_candidate_extraction':'candidates','unnamed_important_concept_extraction':'candidates','relationship_edge_proposal':'relationship_candidates','ignored_deferred_detection':'ignored_items','evidence_alignment':'alignment_entries'}
    for pid,p in b['passes'].items():
        cnt=len(p.get(keys.get(pid,''),[]));
        if pid=='ignored_deferred_detection': cnt+=len(p.get('deferred_items',[]))
        print(f"| {pid} | {p['schema']} | {cnt} | {_count_evidence(p)} | {p['status']} |")
    print("\n## Candidate Graph Summary\n\n| Metric | Count |\n|---|---:|")
    for k in ['nodes','edges','beats','proposed_writes','ignored_items','deferred_items']: print(f"| {k.replace('_',' ').title()} | {len(g[k])} |")
    print("\n## Gold Comparison Scores\n\n| Score | Value |\n|---|---:|")
    for k,v in r['scores'].items(): print(f"| {k} | {v} |")
    print("\n## Hard Failures\n\n| Issue | Detail |\n|---|---|")
    for x in r['hard_failures'] or [{'issue':'none','detail':'sample output has no hard failures'}]: print(f"| {x['issue']} | {x['detail']} |")
    print("\n## Soft Misses\n\n| Issue | Detail |\n|---|---|")
    for x in r['soft_misses'][:25]: print(f"| {x['issue']} | {x['detail']} |")
    print("\n## Missing Gold Coverage\n\n| Type | ID | Label |\n|---|---|---|")
    for typ in ['nodes','edges','beats','proposed_writes','ignored_items','deferred_items']:
        for x in r['coverage'][f'missing_gold_{typ}'][:10]: print(f"| {typ} | {x['id']} | {x['label']} |")
    print("\n## Extra Candidate Coverage\n\n| Type | ID | Label |\n|---|---|---|")
    any_extra=False
    for typ in ['nodes','edges','beats','proposed_writes','ignored_items','deferred_items']:
        for x in r['coverage'][f'extra_candidate_{typ}'][:10]: any_extra=True; print(f"| {typ} | {x['id']} | {x['label']} |")
    if not any_extra: print("| none | none | exact-ID subset sample |")
    print("\n## Evidence Resolution\n\n| Metric | Value |\n|---|---:|")
    print(f"| Evidence refs | {len(resolved)} |\n| Resolved | {sum(x.can_open_source for x in resolved)} |\n| Openable | {sum(x.can_open_source for x in resolved)} |\n| Highlightable | {sum(x.can_highlight_span for x in resolved)} |\n| Warnings | {sum(len(x.warnings) for x in resolved)} |")
    print("\n## Boundary Statement\n")
    print("This PR adds an eval-only extractor harness fixture.\nIt loads static, checked-in candidate output.\nIt does not call an LLM.\nIt does not execute a live extractor.\nIt does not generate output from recap text.\nIt does not write graph memory.\nIt does not approve writes.\nIt does not execute graph queries.\nIt does not scan or mutate corpus files.\nIt does not connect `/plan`.\nIt does not connect Agent Interaction.\nIt does not promote facts or canon.\nIt does not change runtime or production behavior.")
if __name__ == '__main__': main()
