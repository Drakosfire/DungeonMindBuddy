import hashlib
import json
import statistics
from pathlib import Path

import tiktoken

from .context_capture import validate_context_packet
from application_state.agent_conversation.native_evidence_view import semantic_frame_in_request
from application_state.agent_conversation.types import canonical_sha256
from application_state.agent_conversation.native_writer import read_evidence_records

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
        ready = load(directory / 'context-ready.json')
        request = load(directory / 'context-request.json')
        packet = validate_context_packet(ready, request, load(directory / 'context-stop.json'))
        if packet['turn'].user_text != gold['question']:
            raise ValueError(f"Authorized writer question differs from oracle for {case}")
        payload = packet['payload']
        frame = semantic_frame_in_request(payload, legacy_schemas=())
        if frame is None or canonical_sha256(frame) != packet['authorization'].frame_sha256:
            raise ValueError(f"Serialized writer evidence differs from authorization for {case}")
        content = next(message['content'] for message in payload['input']
                       if semantic_frame_in_request({'input': [message]}, legacy_schemas=()) is not None)
        wire = bytes.fromhex(request['body_hex'])
        excerpts = frame['native_body_evidence']['excerpts']
        execution = packet['turn'].graph_context_execution
        writer_index = execution.events.index(packet['authorization'])
        prefix = execution.model_copy(update={'events': execution.events[:writer_index]})
        supports = read_evidence_records(prefix, frame)['body_excerpts']
        inventory = []
        for excerpt, support in zip(excerpts, supports, strict=True):
            handle = excerpt['excerpt_handle']
            selected = support.read.excerpt
            source = support.catalog.source
            if selected.text != excerpt['text']:
                raise ValueError(f"Serialized excerpt differs from its selected read for {case}/{handle}")
            target = dict(
                ref=source.evidence_ref_id, event=str(support.read.event_id),
                start=selected.section.byte_start, end=selected.section.byte_end,
                body_sha256=source.revision.content_sha256,
                excerpt_sha256=digest(selected.text.encode()))
            exact = [m for m in reopened.get((case, handle), [])
                     if all(m.get(key) == value for key, value in target.items())]
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
            if not item['witnesses']:
                raise ValueError(f"Gold item has no witnesses for {case}/{item['id']}")
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
            context_ready_ms=packet['request_to_ready_ms'],
            host_spans=ready['host_spans'], controller_received_calls=calls))
    return dict(schema='buddy_retrieval_score_v1', oracle_sha256=digest(oracle_path.read_bytes()), readback_sha256=digest(readback_path.read_bytes()),
        tokenizer='o200k_base', token_accounting='Estimated packet tokens. Section estimates omit outer keys and separators and are not additive.',
        supported=sum(r['supported'] for r in results), total=sum(r['total'] for r in results),
        median_packet_tokens=statistics.median(r['packet_tokens'] for r in results), cases=results)
