import {decodeWalkthrough,upgradeWalkthroughV1,type Walkthrough} from './protocol';
export interface TourStorage {getItem(key:string):string|null;setItem(key:string,value:string):void}
// Keep storage addresses stable; pointer/record schemas define the one-way upgrade.
const root=(world:string)=>`dmb:guided-journey:v1:${encodeURIComponent(world)}:`;
export const pointerKey=(world:string)=>root(world)+'current';
export const recordKey=(world:string,id:string)=>root(world)+'record:'+encodeURIComponent(id);
export interface StoredWalkthrough {record:Walkthrough;bytes:string;pointer:string;legacy?:{id:string}}
export function readWalkthrough(storage:TourStorage,world:string):StoredWalkthrough|null {
 const pointer=storage.getItem(pointerKey(world));
 if(pointer===null)return null;
 const value:unknown=JSON.parse(pointer);
 if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).length!==2||!('schema' in value)||!['dmb_guided_journey_pointer_v1','dmb_guided_journey_pointer_v2','dmb_guided_journey_pointer_v3'].includes(String(value.schema))||!('id' in value)||typeof value.id!=='string'||!value.id.trim())throw new Error('The saved tour selection is damaged. Its original record was preserved.');
 const bytes=storage.getItem(recordKey(world,value.id));
 if(bytes===null)throw new Error('The selected walkthrough is missing. Nothing was replaced.');
 const legacy=value.schema==='dmb_guided_journey_pointer_v1';
 const record=legacy?upgradeWalkthroughV1(bytes,world):decodeWalkthrough(bytes,world);
 if(!legacy&&value.schema!==`dmb_guided_journey_pointer_v${record.version}`)throw new Error('The walkthrough selection has a different version.');
 if((legacy?record.upgradedFrom?.id:record.id)!==value.id)throw new Error('The walkthrough record differs from its selection.');
 return {record,bytes,pointer,...(legacy?{legacy:{id:value.id}}:{})};
}
/** Caller holds the World guidance Web Lock. CAS also detects external storage changes. */
export function writeWalkthrough(storage:TourStorage,next:Walkthrough,expected:StoredWalkthrough|null):StoredWalkthrough {
 if(next.version!==3)throw new Error('Historical guidance is read-only. Restart guidance to create a new walkthrough.');
 const key=recordKey(next.worldId,next.id),pointer=JSON.stringify({schema:'dmb_guided_journey_pointer_v3',id:next.id});
 if(storage.getItem(pointerKey(next.worldId))!==(expected?.pointer??null))throw new Error('Another tab changed this walkthrough. Reload its guidance; your records were preserved.');
 if(expected?.legacy&&storage.getItem(recordKey(next.worldId,expected.legacy.id))!==expected.bytes)throw new Error('The original walkthrough changed before upgrade. Its records were preserved.');
 const old=storage.getItem(key);
 if(old!==(!expected?.legacy&&expected?.record.id===next.id?expected.bytes:null))throw new Error('The walkthrough changed. Its original record was preserved.');
 const bytes=JSON.stringify(next);decodeWalkthrough(bytes,next.worldId);
 storage.setItem(key,bytes);
 if(storage.getItem(key)!==bytes)throw new Error('The walkthrough could not be retained. Keep this page open.');
 if(storage.getItem(pointerKey(next.worldId))!==(expected?.pointer??null))throw new Error('Another tab changed the tour selection. Both walkthrough records were preserved.');
 if(expected?.legacy&&storage.getItem(recordKey(next.worldId,expected.legacy.id))!==expected.bytes)throw new Error('The original walkthrough changed during upgrade. Both records were preserved.');
 storage.setItem(pointerKey(next.worldId),pointer);
 if(storage.getItem(pointerKey(next.worldId))!==pointer)throw new Error('The walkthrough selection could not be retained.');
 return {record:next,bytes,pointer};
}
