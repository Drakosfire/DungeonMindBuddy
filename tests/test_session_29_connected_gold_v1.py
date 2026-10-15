"""Damage the reference, not an extractor implementation.

Structural negative cases run everywhere. Original-source positive/range/hash
cases run against the private local corpus when present; the CLI never skips it.
"""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'evals/graph_memory_layer/validate_session_29_connected_gold_v1.py'
spec = importlib.util.spec_from_file_location('s29_gold_validator', MODULE)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
ROOT = Path('/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy')


class Session29GoldTests(unittest.TestCase):
    def setUp(self):
        self.gold = json.loads(validator.GOLD_PATH.read_text())

    def errors(self):
        return '\n'.join(validator.validate(self.gold, ROOT))

    def test_exact_originals_pass(self):
        if not (ROOT / self.gold['sources'][0]['path']).exists():
            self.skipTest('private original corpus unavailable; run CLI with --source-root')
        self.assertEqual(validator.validate(self.gold, ROOT), [])

    def test_wrong_original_hash(self):
        self.gold['sources'][0]['sha256'] = '0' * 64
        self.assertIn('primary immutable hash changed', self.errors())

    def test_literal_offset_corruption(self):
        if not (ROOT / self.gold['sources'][0]['path']).exists():
            self.skipTest('private original corpus unavailable')
        self.gold['evidence'][0]['start'] += 1
        self.assertIn('literal quote/range mismatch', self.errors())

    def test_wrong_source(self):
        self.gold['evidence'][0]['source'] = 'made_up_source'
        self.assertIn('unknown evidence source', self.errors())

    def test_wrong_quote_hash(self):
        self.gold['evidence'][0]['quote_sha256'] = '0' * 64
        self.assertIn('quote hash', self.errors())

    def test_dangling_endpoint(self):
        self.gold['facts'][0]['object'] = 'missing'
        self.assertIn('dangling endpoint', self.errors())

    def test_duplicate_identity(self):
        self.gold['nodes'].append(copy.deepcopy(self.gold['nodes'][0]))
        self.assertIn('nodes: duplicate ID', self.errors())

    def test_unsupported_provenance(self):
        self.gold['facts'][0]['provenance'] = 'model_guess'
        self.assertIn('invalid provenance', self.errors())

    def test_operator_laundering(self):
        fact = next(f for f in self.gold['facts'] if f['id'] == 'operator_children_origin')
        fact['provenance'] = 'source_assertion'
        fact['evidence'] = [self.gold['evidence'][0]['id']]
        self.assertIn('operator child origin laundered', self.errors())

    def test_missing_attribution(self):
        fact = next(f for f in self.gold['facts'] if f['provenance'] == 'attributed_observation')
        fact['attributes'].pop('attributed_to')
        self.assertIn('missing attribution', self.errors())

    def test_dropped_coverage_even_if_all_references_removed(self):
        target = 'children_carried'
        self.gold['facts'] = [f for f in self.gold['facts'] if f['id'] != target]
        self.gold['required_fact_ids'].remove(target)
        for c in self.gold['coverage']:
            c['required_facts'] = [f for f in c['required_facts'] if f != target]
        self.assertIn('required semantic coverage dropped', self.errors())

    def test_missing_paragraph(self):
        self.gold['coverage'].pop(4)
        self.assertIn('paragraph coverage incomplete', self.errors())

    def test_damaged_benchmark_path(self):
        self.gold['questions'][0]['traversals'][0][2] = 'lysandra'
        self.assertIn('dangling/disconnected traversal', self.errors())

    def test_missing_evidence_reference(self):
        self.gold['facts'][0]['evidence'] = ['missing_evidence']
        self.assertIn('dangling evidence', self.errors())

    def test_plan_cannot_become_performed(self):
        next(f for f in self.gold['facts'] if f['id'] == 'eldritch_intent')['status'] = 'occurred'
        self.assertIn('intended Eldritch Blast became performed', self.errors())

    def test_generic_default_node_kind_rejected(self):
        next(n for n in self.gold['nodes'] if n['id'] == 'lysandro_house')['kind'] = 'entity'
        self.assertIn('unclassified/generic node kind', self.errors())
        self.assertIn('required domain kind changed', self.errors())

    def test_spell_cannot_be_lumped_into_generic_item(self):
        next(n for n in self.gold['nodes'] if n['id'] == 'eldritch_blast')['kind'] = 'item_type'
        self.assertIn('required domain kind changed', self.errors())

    def test_literal_cannot_also_have_entity_endpoint(self):
        fact = next(f for f in self.gold['facts'] if f['id'] == 'den_size')
        fact['object'] = 'flesh_den'
        self.assertIn('require exactly one node or literal object', self.errors())

    def test_dimension_value_must_be_typed_and_measured(self):
        fact = next(f for f in self.gold['facts'] if f['id'] == 'den_size')
        fact['object_value']['unit'] = 'meters'
        self.assertIn('invalid dimension literal', self.errors())

    def test_removed_value_is_not_an_extractable_entity(self):
        self.gold['nodes'].append({'id': 'north', 'kind': 'region', 'type_rationale': 'guess'})
        self.assertIn('literal value promoted to entity', self.errors())

    def test_undocumented_kind_uncertainty_rejected(self):
        self.gold['unresolved_kind_decisions'][0]['reason'] = ''
        self.assertIn('undocumented kind uncertainty', self.errors())

    def test_possessive_home_relation_cannot_be_weakened(self):
        fact = next(f for f in self.gold['facts'] if f['id'] == 'house_owner')
        fact['predicate'] = 'associated_with'
        self.assertIn('house possessive relationship weakened', self.errors())

    def test_narrator_descriptions_not_thrin_testimony(self):
        for fid in ('shoulder', 'understand', 'storm_worse'):
            with self.subTest(fact=fid):
                fact = next(f for f in self.gold['facts'] if f['id'] == fid)
                fact['provenance'] = 'attributed_observation'
                fact['attributes']['attributed_to'] = 'thrin'
                self.assertIn('narrator assertion misattributed', self.errors())
                fact['provenance'] = 'source_assertion'
                fact['attributes'].pop('attributed_to')

    def test_scout_proposal_not_automatically_performed(self):
        next(f for f in self.gold['facts'] if f['id'] == 'scout_plan')['status'] = 'occurred'
        self.assertIn('scouting stages collapsed', self.errors())

    def test_camp_decision_does_not_prove_arrival(self):
        next(f for f in self.gold['facts'] if f['id'] == 'edge_arrival_intent')['status'] = 'occurred'
        self.assertIn('camp decision/arrival stages collapsed', self.errors())

    def test_fire_bolt_use_requires_spell_and_encounter(self):
        fact = next(f for f in self.gold['facts'] if f['id'] == 'firebolt')
        fact['attributes'].pop('spell_ref')
        self.assertIn('Fire Bolt identity/use disconnected', self.errors())

    def test_missing_originals_fail_instead_of_skip(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = validator.validate(self.gold, Path(directory))
        self.assertTrue(any('missing/unreadable original' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
