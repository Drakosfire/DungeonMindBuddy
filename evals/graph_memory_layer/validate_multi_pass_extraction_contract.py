from __future__ import annotations
from evals.graph_memory_layer.multi_pass_extraction_contract import *

def main() -> None:
    print("Graph Memory multi-pass extraction contract validation")
    validate_dependencies(); print("- session 23 recap ingest dependency: ready"); print("- session 23 candidate graph gold dependency: ready")
    c=load_contract(); validate_contract_manifest(c); print("- contract manifest: ready"); print("- pass order: ready"); print("- pass output schemas: ready")
    f=load_session_23_contract_fixture(); validate_pass_contracts(f)
    names=["source span selection","session beat extraction","named entity candidate extraction","unnamed-important concept extraction","relationship edge proposal","ignored/deferred detection","evidence alignment","candidate graph assembly","gold comparison report"]
    for name in names: print(f"- {name} pass: ready")
    o=load_session_23_expected_pass_outline(); validate_session_23_outline(o); print("- session 23 expected pass outline: ready")
    g=load_session_23_gold_comparison_contract(); validate_gold_comparison_contract(g); print("- gold comparison contract: ready")
    validate_safety_boundaries(c,f,o,g); print("- safety boundaries: ready")
    print("- no live extraction/LLM execution: ready"); print("- no graph write/approval/query/runtime leakage: ready"); print("- multi-pass extraction contract: ready")
if __name__ == "__main__": main()
