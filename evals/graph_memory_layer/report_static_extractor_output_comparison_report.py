"""Print the deterministic static extractor output comparison report."""
from __future__ import annotations
from evals.graph_memory_layer import static_extractor_output_comparison_report as r


def main() -> None:
    print(r.build_static_report_markdown(r.build_static_report_json()), end="")

if __name__ == "__main__": main()
