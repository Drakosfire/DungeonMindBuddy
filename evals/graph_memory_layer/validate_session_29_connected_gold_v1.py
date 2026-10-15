"""Offline integrity checker for the independently handcrafted Session29 reference.

Source content stays local. Supply --source-root to relocate the original Buddy
checkout; missing originals are an error, never silently skipped. This verifies
integrity and declared coverage, not automatic semantic entailment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

GOLD_PATH = Path(__file__).parent / 'examples/session_29_connected_gold_v1/gold.json'
PRIMARY_SHA256 = '4f963656828b553f7919ee00d3304725ddff892a13651b989f99b9b649933796'
CLASSES = {'source_assertion', 'attributed_observation', 'contextual_inference',
           'unresolved_hypothesis', 'operator_addition'}
STATUSES = {'occurred', 'intended', 'historical_report', 'contextual', 'clarification'}
# Independent semantic anchors: deleting a fact and its ledger reference must fail.
REQUIRED = {'vantage', 'house_owner', 'father', 'mireward_context', 'smoke_south',
            'smoke_fin', 'no_movement', 'psychic_ephanna', 'psychic_thrin',
            'psychic_location', 'compulsion', 'seed_bearer', 'seed_call',
            'resentment', 'children_carried', 'rescue_actual', 'children_context',
            'operator_children_origin', 'warehouse_identity', 'refugee_origin',
            'refugee_housing', 'edge_warehouse', 'safe_access', 'eldritch_intent',
            'arrows', 'firebolt', 'fire_initial', 'fire_use', 'fire_more',
            'greater_healing', 'healing', 'minor_healing', 'oil', 'creation',
            'flesh_source', 'control_lost', 'pull_gone', 'fort', 'edge_monster',
            'sleep_delivery', 'cures_ready', 'mist_cure', 'spraying',
            'mist_transfer', 'wall_repair', 'stays', 'bayou', 'wildlife',
            'physical_thrum', 'camp', 'seed_reappraisal', 'pippa_prior'}


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate(gold: dict, source_root: Path) -> list[str]:
    """Return all discovered errors without changing files or consulting services."""
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    def indexed(key: str) -> dict:
        rows = gold.get(key, [])
        ids = [r.get('id') for r in rows]
        require(all(isinstance(i, str) and i for i in ids), f'{key}: invalid ID')
        require(len(ids) == len(set(ids)), f'{key}: duplicate ID')
        return {r.get('id'): r for r in rows}

    require(gold.get('schema') == 'session_29_connected_gold_v1', 'wrong schema')
    sources, evidence, nodes, facts = (indexed(k) for k in ('sources', 'evidence', 'nodes', 'facts'))
    indexed('ambiguities')
    indexed('questions')
    texts: dict[str, str] = {}
    for sid, source in sources.items():
        relative = Path(source['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, f'{sid}: unsafe source path')
        if relative.is_absolute() or '..' in relative.parts:
            continue
        try:
            content = (source_root / relative).read_bytes()
            texts[sid] = content.decode('utf-8')
        except (OSError, UnicodeError) as exc:
            errors.append(f'{sid}: missing/unreadable original: {exc}')
            continue
        require(digest(content) == source['sha256'], f'{sid}: source hash mismatch')
        require(source.get('authority') in {'observed_session_recap', 'authored_dossier',
                                          'seed_reference', 'frozen_span_index'}, f'{sid}: source authority')
        require(source.get('independence_group') == sid, f'{sid}: independence group')
    require(sources.get('s29', {}).get('sha256') == PRIMARY_SHA256, 'primary immutable hash changed')
    span_index = {}
    if 'span_index' in texts:
        try:
            si = json.loads(texts['span_index'])
            require(si['content_sha256'] == PRIMARY_SHA256, 'span index content hash')
            span_index = {s['source_span_id']: s for s in si['spans']}
        except (ValueError, KeyError):
            errors.append('invalid frozen span index')
    for eid, item in evidence.items():
        sid = item.get('source')
        require(sid in sources and sid != 'span_index', f'{eid}: unknown evidence source')
        quote = item.get('quote', '')
        require(bool(quote), f'{eid}: empty quote')
        require(digest(quote.encode()) == item.get('quote_sha256'), f'{eid}: quote hash')
        text = texts.get(sid)
        if text is None:
            continue
        a, b = item.get('start'), item.get('end')
        if not (isinstance(a, int) and isinstance(b, int) and 0 <= a < b <= len(text)):
            errors.append(f'{eid}: invalid codepoint range')
            continue
        require(text[a:b] == quote, f'{eid}: literal quote/range mismatch')
        require(item.get('start_line') == text.count('\n', 0, a) + 1, f'{eid}: start line')
        require(item.get('end_line') == text.count('\n', 0, b - 1) + 1, f'{eid}: end line')
        if sid == 's29':
            ids = item.get('source_span_ids', [])
            require(bool(ids), f'{eid}: missing frozen span')
            for span_id in ids:
                span = span_index.get(span_id, {})
                require(bool(span) and span.get('start_line', 10**9) <= item['start_line']
                        and span.get('end_line', 0) >= item['end_line'], f'{eid}: wrong frozen span')
    for fid, fact in facts.items():
        require(fact.get('subject') in nodes and fact.get('object') in nodes, f'{fid}: dangling endpoint')
        require(bool(fact.get('predicate')) and bool(fact.get('description')), f'{fid}: empty assertion')
        provenance = fact.get('provenance')
        require(provenance in CLASSES, f'{fid}: invalid provenance')
        require(fact.get('status') in STATUSES, f'{fid}: invalid status')
        require(bool(fact.get('temporal_scope')) and bool(fact.get('confidence')), f'{fid}: missing scope/confidence')
        refs = fact.get('evidence', [])
        require(all(e in evidence for e in refs), f'{fid}: dangling evidence')
        if provenance == 'operator_addition':
            require(not refs, f'{fid}: operator assertion masquerading as quoted source')
            require(fact.get('attributes', {}).get('authority_ref') in gold.get('operator_authorities', []),
                    f'{fid}: missing operator authority')
        else:
            require(bool(refs), f'{fid}: assertion lacks evidence')
        if provenance == 'attributed_observation':
            require(fact.get('attributes', {}).get('attributed_to') in nodes, f'{fid}: missing attribution')
    require(REQUIRED <= facts.keys(), 'required semantic coverage dropped')
    require(set(gold.get('required_fact_ids', [])) == facts.keys(), 'required fact manifest drift')
    covered = set()
    ledger = gold.get('coverage', [])
    require([c.get('paragraph') for c in ledger] == list(range(1, 16)), 'paragraph coverage incomplete/order')
    for item in ledger:
        refs = item.get('required_facts', [])
        require(bool(refs) and all(f in facts for f in refs), f'{item.get("id")}: coverage dangling/empty')
        covered.update(refs)
        require(item.get('disposition') == 'represented', f'{item.get("id")}: missing disposition')
        if 's29' in texts:
            text = texts['s29']
            a, b = item['start'], item['end']
            require(digest(text[a:b].encode()) == item['sha256'], f'{item["id"]}: paragraph hash/range')
            require(item['start_line'] == text.count('\n', 0, a) + 1, f'{item["id"]}: paragraph line')
    for fid, fact in facts.items():
        if fact.get('temporal_scope', '').startswith('C2S29 paragraph'):
            require(fid in covered, f'{fid}: omitted from paragraph ledger')
    for ambiguity in gold.get('ambiguities', []):
        require(all(f in facts for f in ambiguity['facts']), f'{ambiguity["id"]}: ambiguity fact reference')
        require(all(e in evidence for e in ambiguity['evidence']), f'{ambiguity["id"]}: ambiguity evidence reference')
    for question in gold.get('questions', []):
        qid = question['id']
        path = question.get('expected_fact_path', [])
        require(bool(path) and all(f in facts for f in path), f'{qid}: question fact path')
        expected = {e for f in path if f in facts for e in facts[f]['evidence']}
        require(set(question.get('expected_evidence', [])) == expected, f'{qid}: question evidence mismatch')
        require(bool(question.get('failure_examples')), f'{qid}: no failure examples')
        for traversal in question.get('traversals', []):
            require(len(traversal) >= 3 and len(traversal) % 2 == 1, f'{qid}: malformed traversal')
            for n in range(1, len(traversal), 2):
                relation = facts.get(traversal[n], {})
                require(relation.get('subject') == traversal[n-1] and relation.get('object') == traversal[n+1],
                        f'{qid}: dangling/disconnected traversal')
    gap_facts = set()
    for gap in gold.get('native_mapping_gaps', []):
        for fid in gap['facts']:
            require(fid in facts and facts[fid]['predicate'] == gap['predicate'], 'mapping gap reference')
            gap_facts.add(fid)
    require(gap_facts == facts.keys(), 'mapping gap inventory incomplete')
    require(facts.get('eldritch_intent', {}).get('status') == 'intended', 'intended Eldritch Blast became performed')
    require(facts.get('operator_children_origin', {}).get('provenance') == 'operator_addition', 'operator child origin laundered')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path('/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy'))
    parser.add_argument('--gold', type=Path, default=GOLD_PATH)
    args = parser.parse_args()
    gold = json.loads(args.gold.read_text())
    errors = validate(gold, args.source_root)
    manifest_path = args.gold.parent / 'SOURCE_MANIFEST.json'
    try:
        manifest = json.loads(manifest_path.read_text())
        if manifest.get('sources') != gold.get('sources'):
            errors.append('source manifest differs from gold source inventory')
    except (OSError, ValueError) as exc:
        errors.append(f'missing/invalid source manifest: {exc}')
    for error in errors:
        print(f'ERROR: {error}')
    print(f'{len(gold["facts"])} facts, {len(gold["evidence"])} literal evidence ranges: {len(errors)} errors')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
