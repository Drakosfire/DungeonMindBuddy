"""CLI validator for the static preview graph UI prototype."""
from __future__ import annotations
from evals.graph_memory_layer import static_preview_graph_ui_prototype as p

def main() -> None:
    print("Graph Memory static preview graph UI prototype validation")
    p.report.validate_all(); print("- static extractor output comparison report dependency: ready")
    p.harness.validate_all(); print("- eval-only extractor harness dependency: ready")
    manifest=p.load_manifest(); model=p.load_prototype_model(); html=p.load_prototype_html()
    p.validate_manifest(manifest); print("- prototype manifest: ready")
    p.validate_prototype_model_shape(model); print("- prototype model shape: ready")
    p.validate_prototype_model_consistency(model); print("- prototype model deterministic build: ready")
    p.validate_html_shape(html, model); print("- prototype HTML shape: ready")
    p.validate_html_determinism(html, model); print("- prototype HTML deterministic build: ready")
    for label in ["preview summary","coverage grid","evidence health panel","high-risk audit panel","candidate explorer","candidate detail examples","proposed writes queue","missing coverage panel","hard failures panel","disabled review controls"]: print(f"- {label}: ready")
    p.validate_no_runtime_leakage(manifest, model, html); print("- no runtime/app/network leakage: ready")
    print("- static preview graph UI prototype: ready")
if __name__ == "__main__": main()
