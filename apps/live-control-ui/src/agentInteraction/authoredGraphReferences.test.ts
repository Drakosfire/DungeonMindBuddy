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

import {readComposerReferences,writeComposerReferences,composerReferenceKey} from './authoredGraphReferences';
it('retains exact composer selections by World and page across readback',()=>{
 sessionStorage.clear();const saved=writeComposerReferences(sessionStorage,'workshop','page',null,[ref]);
 expect(readComposerReferences(sessionStorage,'workshop','page')).toEqual(saved);
 expect(readComposerReferences(sessionStorage,'workshop','other')).toEqual({serialized:null,references:[],submittedTurnId:null});
 expect(()=>writeComposerReferences(sessionStorage,'foreign','page',null,[ref])).toThrow('different World');
});
it('preserves newer composer selections and unreadable copies',()=>{
 sessionStorage.clear();const saved=writeComposerReferences(sessionStorage,'workshop','page',null,[ref]);
 const newer=writeComposerReferences(sessionStorage,'workshop','page',saved.serialized,[{...ref,node_id:'newer-box'}]);
 expect(()=>writeComposerReferences(sessionStorage,'workshop','page',saved.serialized,[])).toThrow('changed');
 expect(readComposerReferences(sessionStorage,'workshop','page')).toEqual(newer);
 const key=composerReferenceKey('workshop','page');sessionStorage.setItem(key,'unreadable bytes');
 expect(()=>readComposerReferences(sessionStorage,'workshop','page')).toThrow();expect(sessionStorage.getItem(key)).toBe('unreadable bytes');
});

it('clears submission ownership even when author edits return to an empty reference list',()=>{
 sessionStorage.clear();const turn='11111111-1111-4111-8111-111111111111';
 const submitted=writeComposerReferences(sessionStorage,'workshop','page',null,[],turn);
 const selected=writeComposerReferences(sessionStorage,'workshop','page',submitted.serialized,[ref]);
 const cleared=writeComposerReferences(sessionStorage,'workshop','page',selected.serialized,[]);
 expect(readComposerReferences(sessionStorage,'workshop','page')).toEqual(cleared);
 expect(cleared.submittedTurnId).toBeNull();expect(cleared.serialized).not.toBe(submitted.serialized);
});

it('reads an older retained copy without granting submission ownership',()=>{
 sessionStorage.clear();const key=composerReferenceKey('workshop','page');
 const bytes=JSON.stringify({schema:'dmb_authored_graph_composer_v1',world_id:'workshop',document_id:'page',references:[]});sessionStorage.setItem(key,bytes);
 expect(readComposerReferences(sessionStorage,'workshop','page')).toEqual({serialized:bytes,references:[],submittedTurnId:null});
});


import {recoverComposerReferences,readComposerReferenceRecoveries} from './authoredGraphReferences';
import {webcrypto} from 'node:crypto';
it('retains exact malformed bytes before explicit replacement, including repeated crash recovery',async()=>{
 Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});sessionStorage.clear();const key=composerReferenceKey('workshop','page'),raw='unreadable { bytes';sessionStorage.setItem(key,raw);
 const recovered=await recoverComposerReferences(sessionStorage,'workshop','page',raw);
 expect(recovered.references).toEqual([]);expect(readComposerReferenceRecoveries(sessionStorage,'workshop','page').map(copy=>copy.raw)).toEqual([raw]);
 sessionStorage.setItem(key,raw);await recoverComposerReferences(sessionStorage,'workshop','page',raw);expect(readComposerReferenceRecoveries(sessionStorage,'workshop','page')).toHaveLength(1);
 expect(readComposerReferenceRecoveries(sessionStorage,'workshop','other')).toEqual([]);
 await expect(recoverComposerReferences(sessionStorage,'workshop','page',raw)).rejects.toThrow('changed');
});
it('does not replace malformed or newer bytes if preservation fails or the copy changes during recovery',async()=>{
 Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});const key=composerReferenceKey('workshop','page'),raw='broken',data=new Map([[key,raw]]);
 const failed={getItem:(k:string)=>data.get(k)??null,setItem:()=>{throw new Error('storage denied');}};
 await expect(recoverComposerReferences(failed,'workshop','page',raw)).rejects.toThrow('storage denied');expect(data.get(key)).toBe(raw);
 const changed={getItem:(k:string)=>data.get(k)??null,setItem:(k:string,value:string)=>{data.set(k,value);if(k!==key)data.set(key,'newer author bytes');}};
 await expect(recoverComposerReferences(changed,'workshop','page',raw)).rejects.toThrow('changed');expect(data.get(key)).toBe('newer author bytes');expect(data.size).toBe(2);
});

it('refuses resetting a readable selection and refuses a conflicting retained recovery record',async()=>{
 Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});sessionStorage.clear();
 const saved=writeComposerReferences(sessionStorage,'workshop','page',null,[ref]);
 await expect(recoverComposerReferences(sessionStorage,'workshop','page',saved.serialized!)).rejects.toThrow('readable');
 expect(readComposerReferences(sessionStorage,'workshop','page')).toEqual(saved);
 const key=composerReferenceKey('workshop','page');sessionStorage.setItem(key,'broken');await recoverComposerReferences(sessionStorage,'workshop','page','broken');
 const retained=readComposerReferenceRecoveries(sessionStorage,'workshop','page')[0];sessionStorage.setItem(retained.key,'different archived bytes');sessionStorage.setItem(key,'broken');
 await expect(recoverComposerReferences(sessionStorage,'workshop','page','broken')).rejects.toThrow('differs');expect(sessionStorage.getItem(key)).toBe('broken');expect(sessionStorage.getItem(retained.key)).toBe('different archived bytes');
});
