import {useEffect,useState} from 'react';
import type {WorldPlayRunRecordV2} from '../api/types';
import {useGuidedTour,useTourOwnerReading,type TourDispatchScope} from './GuidedTour';
import {runPins} from './ownerPins';
import type {RunStateEvidence} from './protocol';
const PAGE_INSTANCE=crypto.randomUUID();
function ordered(value:unknown):unknown {
 if(Array.isArray(value))return value.map(ordered);
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>[key,ordered(item)]));
 return value;
}
export interface RunContentBasis {edition_revision:number;edition_revision_id:string|null;content_sha256:string}
/** Hash equality demonstrates retained state; the admitted Run and content owners supply authority. */
export function RunStateTourObservations({run,content,blocked,acknowledgedRun,pageInstanceId=PAGE_INSTANCE}:{run:WorldPlayRunRecordV2|null;content:RunContentBasis|null;blocked:boolean;acknowledgedRun:{worldId:string;runId:string;revision:number;dispatchScope?:TourDispatchScope|null}|null;pageInstanceId?:string}){
 const tour=useGuidedTour();
 const [hashFailure,setHashFailure]=useState<{key:string;message:string}|null>(null);
 const [hashed,setHashed]=useState<{key:string;proof:RunStateEvidence;observedAt:string}|null>(null);
 const key=tour?.tracking&&run&&content?JSON.stringify(ordered({target:runPins(run),revision:run.run_revision,progress:run.progress,content:{edition_revision:content.edition_revision,edition_revision_id:content.edition_revision_id,content_sha256:content.content_sha256}})):null;
 useEffect(()=>{
  let canceled=false;
  if(tour?.tracking&&key&&content&&!blocked)void (async()=>{try{const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(key));
   if(canceled)return;const stateDigest=Array.from(new Uint8Array(bytes),byte=>byte.toString(16).padStart(2,'0')).join('');
   setHashFailure(null);setHashed({key,observedAt:new Date().toISOString(),proof:{kind:'run-state',stateDigest,pageInstanceId,contentRevision:content.edition_revision,contentRevisionId:content.edition_revision_id,contentDigest:content.content_sha256}});
  }catch{if(!canceled)setHashFailure({key,message:'The saved state comparison could not be prepared. Ordinary Run controls remain available.'});}})();
  return()=>{canceled=true;};
 },[tour?.tracking,key,blocked,pageInstanceId]);
 const hashError=hashFailure?.key===key?hashFailure.message:null;
 const pins=run?runPins(run):null,proof=hashed?.key===key?hashed.proof:null;
 const ready=!!run&&!!pins&&!!proof&&!blocked&&!hashError;
 const progress=ready&&!!run.progress.current_scene_id&&Object.values(run.progress.notes_by_element_id).some(note=>note.trim())&&Object.keys(run.progress.selections).length>0;
 const fresh=!!run&&acknowledgedRun?.worldId===run.world_id&&acknowledgedRun.runId===run.run_id&&acknowledgedRun.revision===run.run_revision;
 useTourOwnerReading({step:'progress',dispatchScope:acknowledgedRun?.dispatchScope,target:pins?.target??null,...(pins?{parent:pins.parent}:{}),control:'progress',status:hashError?'failed':progress?'ready':ready?'pending':'unavailable',reason:hashError??(progress?undefined:'Use a scene choice and save nonempty scene notes. Finish pending edits and recorded commands before inspecting the saved Run.'),
  ...(progress?{observation:{step:'progress',target:pins.target,parent:pins.parent,origin:fresh?'acknowledged':'existing',observedAt:run.updated_at,receiptId:`progress:${proof.stateDigest}`,proof}}:{})});
 useTourOwnerReading({step:'recovery',target:pins?.target??null,...(pins?{parent:pins.parent}:{}),control:'recovery',status:hashError?'failed':ready?'ready':'unavailable',reason:hashError??(ready?undefined:'Open the saved Run and finish pending work before reloading. Guidance will compare the re-admitted saved state with its earlier observation.'),
  ...(ready?{observation:{step:'recovery',target:pins.target,parent:pins.parent,origin:'existing',observedAt:hashed!.observedAt,receiptId:`recovery:${proof.stateDigest}:${pageInstanceId}`,proof}}:{})});
 return null;
}
