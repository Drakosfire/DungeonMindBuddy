from __future__ import annotations
import argparse,json
from pathlib import Path
from evals.graph_memory_layer import live_extractor_prompt_harness as h
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--candidate-output',required=True); a=ap.parse_args()
    report=h.validate_candidate_output(json.loads(Path(a.candidate_output).read_text()))
    print('# Live Extractor Candidate Output Report')
    for k,v in report['candidate_class_counts'].items(): print(f'- {k}: {v}')
    print('- evidence alignment: validate with --run-bundle/--source-recap command')
