import { describe, expect, it } from 'vitest';
import type { NativeAssertion, NativeGraphEntity } from '../api/nativeGraphInspection';
import { assertionStatus, buildNodeExplorer, compactNodeLabel, sourceContexts } from './graphNodeExplorer';
const labels = new Map([['lys', 'Lysandra'], ['father', 'Lysandro'], ['guard', 'City guard'], ['cult', 'Cultists']]);
function assertion(id: string, subject = 'lys', predicate = 'dungeonbuddy.custom:works_with', value: NativeAssertion['value'] = {kind:'entity_ref',entity_id:'guard'}): NativeAssertion {
 return {assertion_id:id,subject_entity_id:subject,predicate,value,metadata:{scope:[{axis:'dungeonbuddy.scope:campaign',value:'longmont-c2'}],visibility:{kind:'labels_any',labels:['gm']},epistemic_basis:'asserted',claim_mode:'dungeonbuddy.claim:fact',standing:'provisional',evidence_ref_ids:['ev:1'],temporal_scope:{kind:'domain_ref',schema:'dungeonbuddy.time:fictional_anchor_v1',payload:{episode:'session-22',qualified:true}},domain_metadata:[]}};
}
function detail(assertions: NativeAssertion[]): NativeGraphEntity {
 return {schema:'dmb_native_graph_entity_v1',scope:{managed_world_id:'elderwyld',scope_mode:'world',campaign_id:null,native_world_id:'elderwyld',binding_version:3,revision_id:'r1'},entity:{found:true,assertions,evidence:[{evidence_ref_id:'ev:1',evidence_role:'support'}],completeness:{status:'complete',reason:null}}};
}
describe('readable node explorer model',()=>{
 it('chooses one exact recorded label without canonicalizing or mutating names',()=>{
  const node={id:'lys',name:'Multiple recorded names',kind:'person',presentation:{recorded_names:['Captain Lysandra','Lesandra','Captain Lysandra Ironveil','Lysandra'],classification_terms:[]}};
  expect(compactNodeLabel(node)).toBe('Lysandra');
  expect(node.presentation.recorded_names).toHaveLength(4);
  expect(compactNodeLabel({...node,name:'Lesandra'})).toBe('Lesandra');
  expect(compactNodeLabel({id:'x',name:'Unnamed object',kind:'person'})).toBe('Unnamed object');
 });
 it('uses directional predicates and distinguishes assertions from connected objects',()=>{
  const m=buildNodeExplorer(detail([assertion('1'),assertion('2','lys','dungeonbuddy.custom:member_of'),assertion('3','cult','dungeonbuddy.custom:threatens',{kind:'entity_ref',entity_id:'lys'})]),'lys',labels);
  expect(m.relationshipRecordCount).toBe(3);expect(m.distinctNeighborCount).toBe(2);
  expect(m.groups.flatMap(g=>g.rows.map(r=>r.text))).toEqual(['Member of City guard','Works with City guard','Threatened by Cultists']);
  expect(m.commonStatus).toBe('fact · asserted · provisional');
 });
 it('coalesces only same-evidence inverse family assertions and retains both records',()=>{
  const child=assertion('1','lys','dungeonbuddy.custom:child_of',{kind:'entity_ref',entity_id:'father'});
  const parent=assertion('2','father','dungeonbuddy.custom:parent_of',{kind:'entity_ref',entity_id:'lys'});
  const m=buildNodeExplorer(detail([parent,child]),'lys',labels);
  expect(m.groups[0]!.rows).toHaveLength(1);expect(m.groups[0]!.rows[0]!.text).toBe('Child of Lysandro');
  expect(m.groups[0]!.rows[0]!.assertions.map(a=>a.assertion_id)).toEqual(['1','2']);
  expect(m.relationshipRecordCount).toBe(2);expect(m.distinctNeighborCount).toBe(1);
  parent.metadata.evidence_ref_ids=['ev:2'];
  expect(buildNodeExplorer(detail([parent,child]),'lys',labels).groups[0]!.rows).toHaveLength(2);
  parent.metadata.evidence_ref_ids=['ev:1'];parent.metadata.standing='disputed';
  expect(buildNodeExplorer(detail([parent,child]),'lys',labels).groups[0]!.rows).toHaveLength(2);
  expect(buildNodeExplorer(detail([parent,child]),'lys',labels).commonStatus).toBeNull();
 });
 it('does not coalesce absent evidence or repeated same-direction assertions',()=>{
  const a=assertion('a','lys','dungeonbuddy.custom:child_of',{kind:'entity_ref',entity_id:'father'});
  const b=assertion('b','father','dungeonbuddy.custom:parent_of',{kind:'entity_ref',entity_id:'lys'});
  a.metadata.evidence_ref_ids=[];b.metadata.evidence_ref_ids=[];
  expect(buildNodeExplorer(detail([a,b]),'lys',labels).groups[0]!.rows).toHaveLength(2);
  expect(buildNodeExplorer(detail([a,{...a,assertion_id:'c'}]),'lys',labels).groups[0]!.rows).toHaveLength(2);
 });
 it('preserves names, classifications, summaries, unfamiliar literal records and missing references',()=>{
  const items=[assertion('1','lys','dnd5e:name',{kind:'literal',value:'Lysandra'}),assertion('2','lys','dnd5e:classification',{kind:'term_ref',term:'dungeonbuddy:character'}),assertion('3','lys','dungeonbuddy:summary',{kind:'literal',value:'Lieutenant Lysandra now.'}),assertion('4','lys','other:name',{kind:'literal',value:{unknown:true}}),assertion('5','lys','other:works_with',{kind:'entity_ref',entity_id:'missing'})];
  const m=buildNodeExplorer(detail(items),'lys',labels);
  expect(m.recordedNames).toEqual(['Lysandra']);expect(m.identityAssertions).toHaveLength(2);
  expect(m.summaries[0]!.text).toBe('Lieutenant Lysandra now.');
  expect(m.otherRecords[0]!.text).toBe('other:name: {"unknown":true}');
  expect(m.groups[0]!.id).toBe('other');expect(m.groups[0]!.rows[0]!.text).toContain('other:works_with → Unlisted object (missing)');
  expect(m.summaries[0]!.contexts).toEqual(['Campaign longmont-c2 · Source episode session-22']);
 });
 it('does not invent temporal context from unrecognized structures',()=>{
  const a=assertion('a');a.metadata.scope=[];a.metadata.temporal_scope={episode:'session-99'};
  expect(sourceContexts(a)).toEqual(['Source episode unspecified']);
  expect(assertionStatus(a)).toBe('fact · asserted · provisional');
 });
 it('keeps self references and unrelated records without direction inference',()=>{
  const m=buildNodeExplorer(detail([assertion('self','lys','other:x',{kind:'entity_ref',entity_id:'lys'}),assertion('other','guard','other:x',{kind:'entity_ref',entity_id:'father'})]),'lys',labels);
  expect(m.groups[0]!.rows[0]!.direction).toBe('self');expect(m.relationshipRecordCount).toBe(1);
  expect(m.otherRecords).toHaveLength(1);expect(m.distinctNeighborCount).toBe(0);
 });
 it('is stable regardless of API assertion ordering',()=>{
  const a=assertion('2'),b=assertion('1');
  expect(buildNodeExplorer(detail([a,b]),'lys',labels)).toEqual(buildNodeExplorer(detail([b,a]),'lys',labels));
 });
});
