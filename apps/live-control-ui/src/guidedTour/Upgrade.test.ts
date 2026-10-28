import {expect,it} from 'vitest';
import {createWalkthrough,decodeWalkthrough,reduceTour,upgradeWalkthroughV1,type TargetPin} from './protocol';
import {pointerKey,recordKey,readWalkthrough,writeWalkthrough,type TourStorage} from './storage';
const stamp='2026-10-28T00:00:00Z';
const source:TargetPin={kind:'source',worldId:'world',objectId:'original',revision:3,digest:'a'.repeat(64)};
const page:TargetPin={...source,kind:'page'};
const plan:TargetPin={kind:'plan',worldId:'world',objectId:'plan',revision:2,revisionId:'work-2',digest:'b'.repeat(64)};
function legacy(){
 let record=createWalkthrough('world','conks','old',stamp);
 for(const pin of [source,page,plan])record=reduceTour(record,{kind:'bind',pin});
 record=reduceTour(record,{kind:'observe',observation:{step:'authoring',target:{...page,revision:2,digest:'c'.repeat(64)},origin:'acknowledged',observedAt:stamp,receiptId:'saved-page-2'}});
 // Historical evidence may precede the selected later revision.
 record.steps.authoring={state:'completed',reason:null,evidence:[{step:'authoring',target:{...page,revision:2,digest:'c'.repeat(64)},origin:'acknowledged',observedAt:stamp,receiptId:'saved-page-2'}]};
 record=reduceTour(record,{kind:'bind',pin:{kind:'run',worldId:'world',objectId:'run',revision:1,digest:plan.digest},parent:plan});
 record=reduceTour(record,{kind:'disposition',step:'roll',state:'unavailable',reason:'Physical roll pending.'});
 record=reduceTour(record,{kind:'move',index:13});
 const value=JSON.parse(JSON.stringify(record));value.schema='dmb_guided_journey_v1';value.version=1;delete value.bindings.page;
 value.steps.authoring.evidence=value.steps.authoring.evidence.map((e:Record<string,unknown>)=>({...e,target:{...(e.target as object),kind:'source'}}));
 return JSON.stringify(value);
}
function storage(bytes=legacy()){
 const values=new Map<string,string>([[pointerKey('world'),JSON.stringify({schema:'dmb_guided_journey_pointer_v1',id:'old'})],[recordKey('world','old'),bytes]]);
 const store:TourStorage={getItem:k=>values.get(k)??null,setItem:(k,v)=>{values.set(k,v);}};
 return store;
}
it('upgrades active guidance once without changing evidence freshness or Run lineage',()=>{
 const bytes=legacy(),old=JSON.parse(bytes),next=upgradeWalkthroughV1(bytes,'world');
 expect(next.id).toBe('old-v2');expect(next.upgradedFrom).toEqual({id:'old',version:1});expect(next.startedAt).toBe(old.startedAt);expect(next.index).toBe(13);
 expect(next.bindings.source).toEqual(source);expect(next.bindings.page).toEqual(page);expect(next.bindings.plan).toEqual(plan);expect(next.bindings.run).toEqual(old.bindings.run);
 expect(next.steps.authoring).toEqual({...old.steps.authoring,evidence:old.steps.authoring.evidence.map((e:Record<string,unknown>)=>({...e,target:{...(e.target as object),kind:'page'}}))});
 for(const key of Object.keys(old.steps))if(key!=='authoring')expect(next.steps[key as keyof typeof next.steps]).toEqual(old.steps[key]);
 expect(decodeWalkthrough(JSON.stringify(next),'world')).toEqual(next);
});
it('retains original bytes and selects a separate successor only on a CAS-protected write',()=>{
 const bytes=legacy(),s=storage(bytes),before=readWalkthrough(s,'world')!;
 expect(s.getItem(recordKey('world','old-v2'))).toBeNull();expect(before.legacy).toEqual({id:'old'});
 const saved=writeWalkthrough(s,reduceTour(before.record,{kind:'phase',phase:'paused'}),before);
 expect(s.getItem(recordKey('world','old'))).toBe(bytes);expect(readWalkthrough(s,'world')).toEqual(saved);expect(saved.record.phase).toBe('paused');
 expect(()=>writeWalkthrough(s,before.record,before)).toThrow('Another tab');
});
it.each(['corrupt-original','changed-original','conflicting-successor','changed-pointer'] as const)('refuses %s without selecting an older authority',mode=>{
 const s=storage(),before=readWalkthrough(s,'world')!;
 if(mode==='corrupt-original'){s.setItem(recordKey('world','old'),'broken');expect(()=>readWalkthrough(s,'world')).toThrow();}
 else if(mode==='changed-original')s.setItem(recordKey('world','old'),legacy()+' ');
 else if(mode==='conflicting-successor')s.setItem(recordKey('world','old-v2'),'other retained record');
 else s.setItem(pointerKey('world'),'other tab selection');
 expect(()=>writeWalkthrough(s,before.record,before)).toThrow();
});
it('does not fall back to legacy guidance after a selected successor is corrupt',()=>{
 const s=storage(),before=readWalkthrough(s,'world')!;writeWalkthrough(s,before.record,before);s.setItem(recordKey('world','old-v2'),'broken');expect(()=>readWalkthrough(s,'world')).toThrow();expect(s.getItem(recordKey('world','old'))).toBe(legacy());
});
it('preserves a paused record and refuses foreign or forged migration evidence',()=>{
 const v=JSON.parse(legacy());v.phase='paused';expect(upgradeWalkthroughV1(JSON.stringify(v),'world').phase).toBe('paused');
 expect(()=>upgradeWalkthroughV1(JSON.stringify(v),'foreign')).toThrow();v.steps.authoring.evidence[0].target.objectId='unbound';expect(()=>upgradeWalkthroughV1(JSON.stringify(v),'world')).toThrow();
});

it('refuses an old-tab edit made between successor write and pointer selection',()=>{
 const s=storage(),before=readWalkthrough(s,'world')!,set=s.setItem;
 s.setItem=(key,value)=>{set(key,value);if(key===recordKey('world','old-v2'))set(recordKey('world','old'),legacy()+' ');};
 expect(()=>writeWalkthrough(s,before.record,before)).toThrow('during upgrade');
 expect(JSON.parse(s.getItem(pointerKey('world'))!).id).toBe('old');expect(s.getItem(recordKey('world','old-v2'))).not.toBeNull();
});
