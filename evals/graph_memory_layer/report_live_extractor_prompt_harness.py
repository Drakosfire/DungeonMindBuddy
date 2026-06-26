from evals.graph_memory_layer import live_extractor_prompt_harness as h
if __name__=='__main__':
    h.validate_all(); m=h.load_manifest(); p=h.load_sample_packet_manifest()
    print('\n'.join(['# Live Extractor Prompt Harness Report','- prompt pack readiness: ready','- source/run-bundle verification readiness: ready','- one-shot prompt mode: ready','- two-shot prompt mode: ready',f"- expected candidate output schema: {p['output_contract']['target']}",'- benchmark comparison readiness: manual candidate JSON can be class-counted and evidence-checked','- blocked: graph writes, approval persistence, query execution, runtime retrieval, /plan, Agent Interaction, corpus scan/mutation, production extraction, production UI']))
