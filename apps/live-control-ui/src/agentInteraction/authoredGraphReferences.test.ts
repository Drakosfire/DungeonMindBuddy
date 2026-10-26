import {expect,it} from 'vitest';
import type {AuthoredGraphReferenceV1} from '../api/types';
import {isAuthoredGraphReferences,mergeAuthoredReferences,authoredGraphReferences} from './authoredGraphReferences';
const ref:AuthoredGraphReferenceV1={schema:'dmb_authored_graph_reference_v1',managed_world_id:'workshop',native_world_id:'native-world',binding_version:1,graph_revision:'revision-a',node_id:'cedar-box',label:'Cedar box'};
it('deduplicates scoped identities without treating labels as authority',()=>{
 expect(mergeAuthoredReferences([ref],[{...ref,label:'Renamed display'}])).toEqual([ref]);
 expect(mergeAuthoredReferences([ref],[{...ref,node_id:'other'}])).toHaveLength(2);
 expect(mergeAuthoredReferences([ref],[{...ref,managed_world_id:'other-world'}])).toHaveLength(2);
});
it.each([{graph_revision:'revision-b'},{binding_version:2}])('refuses conflicting origin snapshots: %j',delta=>{
 expect(()=>mergeAuthoredReferences([ref],[{...ref,...delta}])).toThrow('conflicting');
});
it('checks closed identities, tenancy and duplicate inputs at reload',()=>{
 const value=authoredGraphReferences([ref]);expect(isAuthoredGraphReferences(value,'workshop')).toBe(true);
 expect(isAuthoredGraphReferences(value,'foreign')).toBe(false);
 expect(isAuthoredGraphReferences({...value,references:[ref,ref]})).toBe(false);
 expect(isAuthoredGraphReferences({...value,references:[{...ref,extra:'untrusted'}]})).toBe(false);
 expect(isAuthoredGraphReferences({...value,references:[{...ref,binding_version:1.5}]})).toBe(false);
 expect(isAuthoredGraphReferences({...value,references:[{...ref,node_id:' '}]})).toBe(false);
});
