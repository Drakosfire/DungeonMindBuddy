"""Offline paired transport replay; never dispatches a provider or writes a DB.

Inputs are digest-verified retained source/index/private events. This proves host
transport equivalence, not fresh-model semantic equivalence or billed token use.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def paired_replay(*, source: str, index: dict, events: list, baseline_ref: str) -> tuple[dict, dict]:
    from src.graph_memory.extraction import category_candidate_graph_extractor as current
    from src.graph_memory.extraction.recap_quote_integrity import validate_and_defer_nonliteral_recap_items
    sha = hashlib.sha256(source.encode()).hexdigest()
    assert index['content_sha256'] == sha
    outputs, request_hashes = {}, {}
    for item in events:
        e = item['record']
        if item['kind'] != 'raw_model_response': continue
        assert e['execution_binding']['source_sha256'] == sha
        name = e['pass_name']
        text = e['response']['text']
        assert hashlib.sha256(text.encode()).hexdigest() == e['response']['sha256']
        if name == 'actor_pass-normalized': outputs['actor_pass'] = json.loads(text)['parsed']
        elif name != 'actor_pass':
            outputs[name] = json.loads(text)
            request_hashes[name] = e['request']['user_prompt_sha256']
    assert set(outputs) == {'actor_pass','location_pass','collective_pass','object_pass','thread_pass','beat_pass','edge_pass'}
    old_source = subprocess.check_output(['git','show',f'{baseline_ref}:src/graph_memory/extraction/category_candidate_graph_extractor.py'],text=True)
    with tempfile.TemporaryDirectory() as folder:
        file = Path(folder)/'baseline_extractor.py'; file.write_text(old_source)
        spec = importlib.util.spec_from_file_location('_compact_baseline_extractor',file)
        old = importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
        from src.graph_memory.extraction.compact_evidence_context import CompactEvidenceContext
        from src.graph_memory.extraction.recap_source_authority import partition_recap_source_rows
        source_rows = current.source_packet_rows_from_span_index(index, source_text=source)
        admitted, _, _ = partition_recap_source_rows(source_rows, source)
        context = CompactEvidenceContext(admitted, source_sha256=sha)
        handles = {e['source_span_ref_id']:e['handle'] for e in context.record()['entries']}
        def encoded(value):
            value=deepcopy(value)
            def walk(item):
                if isinstance(item,dict):
                    if item.get('source_span_ref_id') in handles:
                        item['source_span_ref_id']=handles[item['source_span_ref_id']]
                    for child in item.values():walk(child)
                elif isinstance(item,list):
                    for child in item:walk(child)
            walk(value)
            return value
        results, prompts = {}, {}
        for label,module in [('baseline',old),('compact',current)]:
            class Replay:
                supports_actor_source_handles = True
                def run_pass(self, pass_name, **kw):
                    prompts.setdefault(label,{})[pass_name] = kw['user_content']
                    # Encode only explicit citations in the retained later-pass
                    # response fixture. No model-generated prose or quotes change.
                    parsed = (encoded(outputs[pass_name]) if label=='compact' and pass_name in {'beat_pass','edge_pass'}
                              else deepcopy(outputs[pass_name]))
                    return {'parsed':parsed,'raw_text':json.dumps(parsed),
                            'usage':{},'cost_usd':None,'elapsed_ms':0,'response_id':'offline-retained-replay'}
            options=module.CategoryGraphExtractionOptions(campaign_id='longmont-c2',session_id='session-30',
                session_number=30,source_span_index=index,source_text=source,
                source_artifact_id=index['source_artifact_id'],source_ref_id=index['source_ref_id'],
                model_id='deepseek/deepseek-v4.1-flash-1017')
            result=module.extract_category_candidate_graph(options,client=Replay())
            cleaned,diag=validate_and_defer_nonliteral_recap_items(result.candidate_graph,
                source_text=source,source_artifact_id=index['source_artifact_id'],source_sha256=sha,source_span_index=index)
            results[label]={'graph':cleaned,'quote_integrity':diag,'consolidation':result.consolidation_diagnostics}
    exact={p:hashlib.sha256(prompts['baseline'][p].encode()).hexdigest()==request_hashes[p] for p in ['beat_pass','edge_pass']}
    sizes={}
    try:
        import tiktoken
        encoding=tiktoken.get_encoding('o200k_base')
    except Exception: encoding=None
    for p in ['beat_pass','edge_pass']:
        sizes[p]={}
        for label in ['baseline','compact']:
            text=prompts[label][p]
            sizes[p][label]={'characters':len(text),'sha256':hashlib.sha256(text.encode()).hexdigest(),
                            'o200k_estimated_tokens':len(encoding.encode(text)) if encoding else None}
    report={'schema':'dmb_compact_evidence_offline_comparison_v1','source_sha256':sha,
            'baseline_ref':baseline_ref,'baseline_prompt_hash_matches_retained_request':exact,
            'canonical_candidate_equal':results['baseline']['graph']==results['compact']['graph'],
            'quote_integrity_equal':results['baseline']['quote_integrity']==results['compact']['quote_integrity'],
            'prompt_sizes':sizes,'model_calls':0,'compact_replay_uses_short_handles':True,'limits':'Retained outputs replayed, not generated again. Token estimates use o200k, not billed DeepSeek usage. Fresh model quality remains unproven.'}
    return report, results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--index',type=Path,required=True)
    p.add_argument('--events',type=Path,required=True);p.add_argument('--baseline-ref',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report,results=paired_replay(source=a.source.read_text(),index=json.loads(a.index.read_text()),
        events=json.loads(a.events.read_text()),baseline_ref=a.baseline_ref)
    a.output.write_text(json.dumps(report,indent=2))
    a.output.with_suffix('.details.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
