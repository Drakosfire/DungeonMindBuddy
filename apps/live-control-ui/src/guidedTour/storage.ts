import {decodeWalkthrough,type Walkthrough} from './protocol';
export interface TourStorage {getItem(key:string):string|null;setItem(key:string,value:string):void}
const root=(world:string)=>`dmb:guided-journey:v1:${encodeURIComponent(world)}:`;
export const pointerKey=(world:string)=>root(world)+'current';
export const recordKey=(world:string,id:string)=>root(world)+'record:'+encodeURIComponent(id);
export interface StoredWalkthrough {record:Walkthrough;bytes:string;pointer:string}
export function readWalkthrough(storage:TourStorage,world:string):StoredWalkthrough|null {
 const pointer=storage.getItem(pointerKey(world));
 if(pointer===null)return null;
 const value:unknown=JSON.parse(pointer);
 if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).length!==2||!('schema' in value)||value.schema!=='dmb_guided_journey_pointer_v1'||!('id' in value)||typeof value.id!=='string'||!value.id.trim())throw new Error('The saved tour selection is damaged. Its original record was preserved.');
 const bytes=storage.getItem(recordKey(world,value.id));
 if(bytes===null)throw new Error('The selected walkthrough is missing. Nothing was replaced.');
 const record=decodeWalkthrough(bytes,world);
 if(record.id!==value.id)throw new Error('The walkthrough record differs from its selection.');
 return {record,bytes,pointer};
}
/** Caller holds the World guidance Web Lock. CAS also detects external storage changes. */
export function writeWalkthrough(storage:TourStorage,next:Walkthrough,expected:StoredWalkthrough|null):StoredWalkthrough {
 const key=recordKey(next.worldId,next.id),pointer=JSON.stringify({schema:'dmb_guided_journey_pointer_v1',id:next.id});
 if(storage.getItem(pointerKey(next.worldId))!==(expected?.pointer??null))throw new Error('Another tab changed this walkthrough. Reload its guidance; your records were preserved.');
 const old=storage.getItem(key);
 if(old!==(expected?.record.id===next.id?expected.bytes:null))throw new Error('The walkthrough changed. Its original record was preserved.');
 const bytes=JSON.stringify(next);decodeWalkthrough(bytes,next.worldId);
 storage.setItem(key,bytes);
 if(storage.getItem(key)!==bytes)throw new Error('The walkthrough could not be retained. Keep this page open.');
 if(storage.getItem(pointerKey(next.worldId))!==(expected?.pointer??null))throw new Error('Another tab changed the tour selection. Both walkthrough records were preserved.');
 storage.setItem(pointerKey(next.worldId),pointer);
 if(storage.getItem(pointerKey(next.worldId))!==pointer)throw new Error('The walkthrough selection could not be retained.');
 return {record:next,bytes,pointer};
}
