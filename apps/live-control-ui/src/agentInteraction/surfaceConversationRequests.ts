import {useSyncExternalStore} from 'react';
import {SELECTED_WORLD_LOCATION_CHANGED_EVENT} from '../selectedWorld/SelectedWorldContext';

export interface SurfaceConversationRequest {
  id:string;worldId:string;surfaceId:string;objectId:string;message:string;clientThreadId:string;turnId:string;
  status:'pending'|'claimed'|'failed';isCurrent:()=>boolean;prepare?:(context:unknown)=>Promise<void>;
}
let requests:readonly SurfaceConversationRequest[]=[];
const listeners=new Set<()=>void>();
const emit=()=>{for(const listener of listeners)listener();};
const subscribe=(listener:()=>void)=>{listeners.add(listener);return()=>{listeners.delete(listener);};};
export const useSurfaceConversationRequests=()=>useSyncExternalStore(subscribe,()=>requests,()=>requests);
const remove=(id:string)=>{requests=requests.filter(item=>item.id!==id);emit();};
export function queueSurfaceConversationRequest(request:Omit<SurfaceConversationRequest,'status'>){
  if(!request.isCurrent())throw new Error('The authoring destination changed. Open its page to continue.');
  const existing=requests.find(item=>item.id===request.id);
  if(existing){
    if(existing.worldId!==request.worldId||existing.surfaceId!==request.surfaceId||existing.objectId!==request.objectId||existing.message!==request.message)
      throw new Error('A different authoring request already owns this action.');
    if(existing.status==='failed')retrySurfaceConversationRequest(existing.id);
    return;
  }
  requests=[...requests,{...request,status:'pending'}];emit();
}
export function claimSurfaceConversationRequest(id:string):SurfaceConversationRequest|null{
  const item=requests.find(item=>item.id===id);
  if(!item||item.status!=='pending')return null;
  if(!item.isCurrent()){remove(id);return null;}
  const claimed={...item,status:'claimed' as const};requests=requests.map(value=>value.id===id?claimed:value);emit();return claimed;
}
/** Called only after the existing pending-turn owner verifies durable request storage. */
export const acceptSurfaceConversationRequest=remove;
export function failSurfaceConversationRequest(id:string){
  requests=requests.map(item=>item.id===id&&item.status==='claimed'?{...item,status:'failed'}:item);emit();
}
export function retrySurfaceConversationRequest(id:string){
  requests=requests.map(item=>item.id===id&&item.status==='failed'?{...item,status:'pending'}:item);emit();
}
export const cancelSurfaceConversationRequest=remove;
function retireChangedTargets(){const next=requests.filter(item=>item.isCurrent());if(next.length!==requests.length){requests=next;emit();}}
if(typeof window!=='undefined'){
  window.addEventListener('popstate',retireChangedTargets);
  window.addEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT,retireChangedTargets);
}
