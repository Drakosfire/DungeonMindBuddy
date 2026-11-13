import hashlib
import json
import statistics
from pathlib import Path

import tiktoken

def digest(value):
    return hashlib.sha256(value).hexdigest()

def load(path):
    return json.loads(path.read_text())

def score(oracle_path, readback_path, manifest, base):
    oracle_path, readback_path = Path(oracle_path), Path(readback_path)
    oracle = load(oracle_path)
    if oracle.get("schema") != "buddy_retrieval_oracle_v1":
        raise ValueError("Unsupported retrieval oracle")
    cases = {case["id"]: case for case in manifest["cases"]}
    if cases.keys() != oracle["cases"].keys():
        raise ValueError("Oracle and capture case IDs differ")
    reopened = {(row['question'], row['handle']): row['matches']
                for row in map(json.loads, readback_path.read_text().splitlines())}
    encoder = tiktoken.get_encoding('o200k_base')
    results = []
    for case, gold in oracle['cases'].items():
        directory = base / cases[case]["capture_dir"]
        if load(directory / "request.json")["message"] != gold["question"]:
            raise ValueError(f"Captured question differs from oracle for {case}")
        wire = bytes.fromhex(load(directory / 'context-request.json')['body_hex'])
        content = json.loads(wire)['input'][-1]['content']
        frame = json.loads(content)
        excerpts = frame['native_body_evidence']['excerpts']
        inventory = []
        for excerpt in excerpts:
            handle = excerpt['excerpt_handle']
            exact = [m for m in reopened.get((case, handle), [])
                     if m['excerpt_sha256'] == digest(excerpt['text'].encode())]
            inventory.append(dict(handle=handle, source=excerpt['source_name'],
                                  text_tokens=len(encoder.encode_ordinary(excerpt['text'])),
                                  reopened_targets=exact))
        items = []
        seen_spans = {}
        duplicate_tokens = 0
        ambiguous_tokens = 0
        for excerpt, record in zip(excerpts, inventory, strict=True):
            raw = excerpt["text"].encode()
            coordinates = {(m["body_sha256"], m["start"], m["end"])
                           for m in record["reopened_targets"]}
            if len(coordinates) != 1:
                ambiguous_tokens += record["text_tokens"]
                continue
            source, start, end = coordinates.pop()
            if end - start != len(raw):
                raise ValueError(f"Citation extent differs for {case}/{record['handle']}")
            prior = seen_spans.setdefault(source, [])
            for first, last in prior:
                lo, hi = max(start, first), min(end, last)
                if lo < hi:
                    duplicate_tokens += len(encoder.encode_ordinary(raw[lo-start:hi-start].decode()))
            merged = []
            for first, last in sorted([*prior, (start, end)]):
                if merged and first <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(last, merged[-1][1]))
                else:
                    merged.append((first, last))
            seen_spans[source] = merged
        gold_lines = {}
        for item in gold['items']:
            witnesses = []
            for witness in item['witnesses']:
                present = [e['excerpt_handle'] for e in excerpts if witness['text'] in e['text']]
                verified = [row['handle'] for row in inventory if row['handle'] in present
                            and any(m['body_sha256'] == witness['source_sha256'] for m in row['reopened_targets'])]
                if verified:
                    gold_lines[witness["source_sha256"], witness["line"]] = witness["text"]
                witnesses.append(dict(session=witness['session'], line=witness['line'],
                                      present_handles=present, verified_handles=verified))
            status = ('supported' if all(w['verified_handles'] for w in witnesses)
                      else 'citation_unverified' if all(w['present_handles'] for w in witnesses)
                      else 'missing_from_final_packet')
            items.append(dict(id=item['id'], status=status, witnesses=witnesses))
        ready = load(directory / 'context-ready.json')
        trace = load(directory / 'context-trace.json')['body']['attempts']
        calls = [o for attempt in trace for o in attempt['observations']
                 if o['kind']=='provider_call' and o.get('provider')=='typesafe' and o.get('outcome')=='response_received']
        results.append(dict(case=case, supported=sum(i['status']=='supported' for i in items),
            total=len(items), items=items, excerpts=inventory, wire_bytes=len(wire), wire_sha256=digest(wire),
            excerpt_text_tokens=sum(e["text_tokens"] for e in inventory),
            unique_gold_witness_tokens=sum(len(encoder.encode_ordinary(t)) for t in gold_lines.values()),
            duplicate_source_span_tokens_estimate=duplicate_tokens,
            ambiguous_source_span_tokens=ambiguous_tokens,
            erroneous_context_tokens=None,
            packet_tokens=len(encoder.encode_ordinary(content)), section_tokens={k:len(encoder.encode_ordinary(json.dumps(v,ensure_ascii=False,separators=(',',':')))) for k,v in frame.items()},
            graph_assertions=len((frame.get('native_assertions') or {}).get('assertions',[])),
            context_ready_ms=(ready['ready_monotonic_ns']-ready['request_started_monotonic_ns'])/1e6,
            host_spans=ready['host_spans'], controller_received_calls=calls))
    return dict(schema='buddy_retrieval_score_v1', oracle_sha256=digest(oracle_path.read_bytes()), readback_sha256=digest(readback_path.read_bytes()),
        tokenizer='o200k_base', token_accounting='Estimated packet tokens. Section estimates omit outer keys and separators and are not additive.',
        supported=sum(r['supported'] for r in results), total=sum(r['total'] for r in results),
        median_packet_tokens=statistics.median(r['packet_tokens'] for r in results), cases=results)
