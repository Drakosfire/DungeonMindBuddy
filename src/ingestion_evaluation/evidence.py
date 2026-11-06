"""Independent retained receipt checks; these never alter or repair product output."""
from .runner import digest


def inspect_quotes(graph, index, source, diagnostics, pass_names):
    from graph_memory.anchor_quotes import normalize_for_match

    lines = source.splitlines()
    raw_frames = {s['source_span_id']: '\n'.join(lines[s['start_line'] - 1:s['end_line']]) for s in index['spans']}
    frames = {key: value.strip() for key, value in raw_frames.items()}
    result = {'quote_strings': 0, 'occurrence_matches': 0, 'bindings_checked': 0,
              'normalized_quote_differences': [], 'issues': []}
    for category in ('nodes', 'edges', 'beats'):
        for number, item in enumerate(graph.get(category, [])):
            for ref in item.get('evidence_refs', []):
                frame = frames.get(ref.get('source_span_ref_id'))
                selector = f'/{category}/{number}'
                quotes = ref.get('anchor_quotes', [])
                verified_quotes = set()
                for match in ref.get('anchor_quote_matches', []):
                    result['occurrence_matches'] += 1
                    start, end = match.get('char_start'), match.get('char_end')
                    text, quote = match.get('match_text'), match.get('quote')
                    if (frame is None or type(start) is not int or type(end) is not int
                            or not 0 <= start < end <= len(frame)
                            or frame[start:end] != text):
                        result['issues'].append({'selector': selector, 'reason': 'coordinate_mismatch'})
                        continue
                    if (not isinstance(quote, str) or not quote.strip()
                            or normalize_for_match(text) != normalize_for_match(quote)):
                        result['issues'].append({'selector': selector, 'reason': 'anchor_normalization_mismatch'})
                        continue
                    if quote not in quotes:
                        result['issues'].append({'selector': selector, 'reason': 'unadvertised_quote_receipt'})
                        continue
                    verified_quotes.add(quote)
                    if text != quote:
                        result['normalized_quote_differences'].append(
                            {'selector': selector, 'authored_quote': quote, 'source_text': text})
                for quote in quotes:
                    result['quote_strings'] += 1
                    if not isinstance(quote, str) or quote not in verified_quotes:
                        result['issues'].append({'selector': selector, 'reason': 'unverified_anchor_quote'})
    bindings = diagnostics.get('canonical_quote_bindings', [])
    entries = diagnostics.get('compact_evidence_context', {}).get('entries', [])
    eligible = {entry['source_span_ref_id']: entry for entry in entries}
    if bindings:
        if not eligible or len(eligible) != len(entries):
            result['issues'].append({'reason': 'missing_or_duplicate_eligible_frames'})
        for sid, entry in eligible.items():
            if raw_frames.get(sid) != entry['text'] or digest(entry['text'].encode()) != entry['text_sha256']:
                result['issues'].append({'reason': 'raw_eligible_frame_mismatch', 'span': sid})
    for binding in bindings:
        result['bindings_checked'] += 1
        quote = binding.get('quote')
        target, nominated = binding.get('canonical_span_ref_id'), binding.get('nominated_span_ref_id')
        hits = []
        if isinstance(quote, str) and quote:
            for sid in eligible:
                frame = frames.get(sid, '')
                start = 0
                while (position := frame.find(quote, start)) >= 0:
                    hits.append(sid)
                    start = position + 1
        if target == nominated or target not in eligible or nominated not in eligible or hits != [target] or binding.get('source_sha256') != index['content_sha256'] or binding.get('pass_name') not in pass_names:
            result['issues'].append({'reason': 'canonical_binding_unproven', 'binding': binding})
    return result
