import {describe,it,expect,vi} from 'vitest';
import {nativeObjectSubjectKey,projectNativeObject,type NativeObjectSubject} from './nativeObjectProjection';
import {nativeObjectEvidenceChoices} from './nativeObjectEvidence';
import {inspectNativeGraph} from '../api/liveApi';
import type {NativeGraphEntity,NativeAssertion} from '../api/nativeGraphInspection';
vi.mock('../api/liveApi',()=>({inspectNativeGraph:vi.fn()}));
const pin={managed_world_id:'w',native_world_id:'n',binding_version:1,revision_id:'r',scope_mode:'world' as const,campaign_id:null};
const subject:NativeObjectSubject={kind:'admitted-native',entityId:'a',pin};
const a:NativeAssertion={assertion_id:'claim',subject_entity_id:'a',predicate:'dnd5e:holds',value:{kind:'entity_ref',entity_id:'b'},metadata:{scope:[],visibility:null,epistemic_basis:'asserted',claim_mode:'fact',standing:'provisional',evidence_ref_ids:['source'],temporal_scope:null,domain_metadata:[]}};
const detail:NativeGraphEntity={schema:'dmb_native_graph_entity_v1',scope:pin,entity:{found:true,assertions:[a],evidence:[{evidence_ref_id:'source',evidence_role:'support'}],completeness:{status:'partial',reason:'bounded'}}};
describe('shared pinned native projection',()=>{
 it('preserves records and completeness without IO or write authority',()=>{
  const p=projectNativeObject(subject,detail,new Map([['b','Bow']]));
  expect(p.records).toBe(detail.entity.assertions);expect(p.completeness).toEqual(detail.entity.completeness);
  expect(p.dossier.groups[0]?.rows[0]?.text).toBe('Holds Bow');expect(p).not.toHaveProperty('commands');expect(inspectNativeGraph).not.toHaveBeenCalled();
 });
 it.each([{managed_world_id:'other'},{native_world_id:'other'},{binding_version:2},{revision_id:'other'},{scope_mode:'campaign' as const,campaign_id:'c'},{campaign_id:'c'}])('separates and rejects changed pin %j',change=>{
  const changed={...subject,pin:{...pin,...change}};
  expect(nativeObjectSubjectKey(changed)).not.toBe(nativeObjectSubjectKey(subject));
  expect(()=>projectNativeObject(changed,detail,new Map())).toThrow('does not match');
 });
 it('keeps evidence lazy, deduplicated and prohibited for entity-only views',async()=>{
  expect(nativeObjectEvidenceChoices(detail,[a],true)).toEqual([]);
  const choices=nativeObjectEvidenceChoices(detail,[a,{...a,assertion_id:'inverse'}],false);
  expect(choices).toHaveLength(1);expect(inspectNativeGraph).not.toHaveBeenCalled();
  vi.mocked(inspectNativeGraph).mockResolvedValueOnce({schema:'dmb_native_graph_source_v1',scope:{...pin,binding_version:2},source:{text:'wrong'}} as never);
  await expect(choices[0]!.load!()).rejects.toThrow('Source unavailable');
 });
});
