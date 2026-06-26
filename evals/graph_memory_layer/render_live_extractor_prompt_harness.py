from __future__ import annotations
import argparse
from pathlib import Path
from evals.graph_memory_layer.live_extractor_prompt_harness import write_prompt_packet

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode',choices=['one_shot','two_shot','three_shot'],required=True); ap.add_argument('--run-bundle',required=True); ap.add_argument('--source-recap',required=True); ap.add_argument('--out',required=True); ap.add_argument('--allow-overwrite',action='store_true')
    a=ap.parse_args(); m=write_prompt_packet(a.mode,Path(a.run_bundle),Path(a.source_recap),Path(a.out),allow_overwrite=a.allow_overwrite)
    print(f"rendered live extractor prompt packet: {m['mode']} -> {a.out}")
if __name__=='__main__': main()
