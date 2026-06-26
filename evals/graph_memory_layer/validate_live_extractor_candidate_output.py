from __future__ import annotations
import argparse,json
from pathlib import Path
from evals.graph_memory_layer import live_extractor_prompt_harness as h
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--run-bundle',required=True); ap.add_argument('--source-recap',required=True); ap.add_argument('--candidate-output',required=True); a=ap.parse_args()
    v=h.verify_run_bundle_and_source(Path(a.run_bundle),Path(a.source_recap)); allowed={r['source_span_ref_id'] for r in h.source_packet_rows(v)}
    report=h.validate_candidate_output(json.loads(Path(a.candidate_output).read_text()), allowed); print(json.dumps(report,indent=2,sort_keys=True))
