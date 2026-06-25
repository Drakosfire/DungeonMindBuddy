"""Report CLI for the static preview graph UI prototype."""
from __future__ import annotations
from evals.graph_memory_layer import static_preview_graph_ui_prototype as p

def main() -> None:
    m=p.load_prototype_model(); c={x["key"]: x for x in m["coverage_cards"]}; pw=m["proposed_writes"]["summary"]
    print("Static Preview Graph UI Prototype v0")
    print(f"HTML: {p.PROTOTYPE_HTML_PATH}")
    print(f"Model: {p.PROTOTYPE_MODEL_PATH}")
    print(f"Status: {m['summary']['status']}")
    print(f"GM preview readiness: {m['summary']['gm_preview_readiness']}")
    print(f"Candidate nodes: {c['nodes']['candidate']} / {c['nodes']['gold']}")
    print(f"Candidate edges: {c['edges']['candidate']} / {c['edges']['gold']}")
    print(f"Candidate beats: {c['beats']['candidate']} / {c['beats']['gold']}")
    print(f"Proposed writes: {pw['pending_count']} pending")
    print("Boundary: static fixture prototype only")
if __name__ == "__main__": main()
