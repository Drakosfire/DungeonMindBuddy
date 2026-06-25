from __future__ import annotations
from evals.graph_memory_layer.multi_pass_extraction_contract import *

def _examples(xs): return ", ".join(xs[:3])
def main() -> None:
    validate_all(); c=load_contract(); f=load_session_23_contract_fixture(); o=load_session_23_expected_pass_outline(); g=load_session_23_gold_comparison_contract()
    print("# Graph Memory Multi-Pass Extraction Contract v0 Report\n")
    print("## Summary\n\n| Field | Value |\n|---|---|")
    print(f"| Contract ID | {c['contract_id']} |\n| Target session | {c['target_session']} |\n| Source fixture | {c['source_fixture_id']} |\n| Gold fixture | {c['target_gold_fixture_id']} |\n| Execution mode | {c['execution_mode']} |\n| Pass count | {len(c['pass_order'])} |\n")
    print("## Pass Order\n\n| Order | Pass ID | Purpose | Output Schema |\n|---:|---|---|---|")
    for i,p in enumerate(f['passes'],1): print(f"| {i} | {p['pass_id']} | {p['purpose']} | {p['schema']} |")
    print("\n## Pass Gates\n\n| Pass ID | Hard Gates | Forbidden Outputs |\n|---|---:|---:|")
    for p in f['passes']: print(f"| {p['pass_id']} | {len(p['hard_gates'])} | {len(p['forbidden_outputs'])} |")
    print("\n## Session 23 Expected Concepts\n\n| Category | Count | Examples |\n|---|---:|---|")
    for k,v in o['required_concepts'].items(): print(f"| {k} | {len(v)} | {_examples(v)} |")
    print("\n## Gold Comparison Dimensions\n\n| Dimension | Type |\n|---|---|")
    for s in g['soft_scores']: print(f"| {s['dimension']} | {s['type']} |")
    print("\n## Hard Failure Categories\n\n| Issue Category | Reason |\n|---|---|")
    for h in g['hard_gates']: print(f"| {h['issue_category']} | {h['reason']} |")
    print("\n## Forbidden Claims\n\n| Claim | Reason |\n|---|---|")
    for claim in o['forbidden_claims']: print(f"| {claim} | Forbidden by contract-only safety boundary |")
    print("\n## Boundary Statement\n")
    for line in ["This PR defines the multi-pass extraction contract only.","It does not call an LLM.","It does not execute extraction.","It does not produce extractor output.","It does not write graph memory.","It does not approve writes.","It does not execute graph queries.","It does not scan or mutate corpus files.","It does not connect `/plan`.","It does not connect Agent Interaction.","It does not promote facts or canon.","It does not change runtime or production behavior."]: print(line)
if __name__ == "__main__": main()
