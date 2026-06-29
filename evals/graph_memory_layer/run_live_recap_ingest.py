"""CLI for explicit-input live recap ingest run bundles."""
from __future__ import annotations
import argparse
from pathlib import Path
from evals.graph_memory_layer import live_recap_ingest_run_bundle as l

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--campaign-id',required=True); p.add_argument('--session-id',required=True); p.add_argument('--input',required=True); p.add_argument('--out',required=True)
    p.add_argument('--source-label'); p.add_argument('--operator-note'); p.add_argument('--allow-overwrite',action='store_true'); p.add_argument('--allow-corpus-input',action='store_true')
    a=p.parse_args()
    b=l.build_bundle(campaign_id=a.campaign_id,session_id=a.session_id,input_path=Path(a.input),source_label=a.source_label,operator_note=a.operator_note,allow_corpus_input=a.allow_corpus_input)
    l.write_run_bundle(b,Path(a.out),allow_overwrite=a.allow_overwrite)
    print(f"Live recap ingest run bundle written: {a.out}")
if __name__=='__main__': main()
