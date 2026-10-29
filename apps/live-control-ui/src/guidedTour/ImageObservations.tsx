import {createContext,useCallback,useContext,useRef,useState,type ReactNode} from 'react';
import {MEDIA_ASSET_ID} from '../media/mediaReferences';
import {useGuidedTour,useTourOwnerReading,type TourDispatchScope} from './GuidedTour';
import type {TargetPin} from './protocol';
interface Generation {model:string;observedAt:string;scope:TourDispatchScope}
interface Placement {key:string;assetId:string;generation:Generation|null;observedAt:string}
export interface ImageInspection {status:'pending'|'unavailable'|'failed';reason:string}
interface ImageApi {inspect:(reading:ImageInspection|null)=>void;captureScope:()=>TourDispatchScope|null;generated:(assetIds:string[],model:string,scope:TourDispatchScope|null)=>void;placed:(assetId:string)=>void}
const Context=createContext<ImageApi|null>(null);
export const useTourImage=()=>useContext(Context);
export function collectTourMediaAssets(node:{type?:string;attrs?:Record<string,unknown>;content?:MediaNode[]}):string[]{
 return [...new Set([...(node.type==='mediaImage'&&typeof node.attrs?.assetId==='string'&&MEDIA_ASSET_ID.test(node.attrs.assetId)?[node.attrs.assetId]:[]),...(node.content??[]).flatMap(collectTourMediaAssets)])];
}
interface MediaNode {type?:string;attrs?:Record<string,unknown>;content?:MediaNode[]}
/** Generation and placement are observed separately; only verified saved content completes the step. */
export function TourImageProvider({worldId,documentId,verified,blockedReason=null,children}:{worldId:string;documentId:string|null;blockedReason?:string|null;verified:{pin:TargetPin;assetIds:string[]}|null;children:ReactNode}){
 const tour=useGuidedTour(),key=JSON.stringify([worldId,documentId]);
 const latest=useRef({key,tracking:tour?.tracking});latest.current={key,tracking:tour?.tracking};
 const generations=useRef(new Map<string,Generation>());
 const [inspection,setInspection]=useState<{key:string;reading:ImageInspection}|null>(null);
 const inspect=useCallback((reading:ImageInspection|null)=>{if(latest.current.key===key)setInspection(reading?{key,reading}:null);},[key]);
 const [placement,setPlacement]=useState<Placement|null>(null);
 const generated=useCallback((assetIds:string[],model:string,scope:TourDispatchScope|null)=>{
  if(!tour?.isScopeCurrent(scope)||latest.current.key!==key||!latest.current.tracking||!documentId||!model.trim())return;
  for(const assetId of assetIds)if(MEDIA_ASSET_ID.test(assetId))generations.current.set(`${key}:${assetId}`,{model,observedAt:new Date().toISOString(),scope:scope!});
 },[key,documentId,tour?.isScopeCurrent]);
 const placed=useCallback((assetId:string)=>{
  if(latest.current.key!==key||!latest.current.tracking||!documentId||!MEDIA_ASSET_ID.test(assetId))return;
  const generation=generations.current.get(`${key}:${assetId}`)??null;
  setPlacement({key,assetId,generation:generation&&tour?.isScopeCurrent(generation.scope)?generation:null,observedAt:new Date().toISOString()});
 },[key,documentId,tour?.isScopeCurrent]);
 const usable=!!placement&&placement.key===key&&!!verified&&verified.pin.kind==='plan'&&!!verified.pin.revisionId&&verified.pin.worldId===worldId&&verified.pin.objectId===documentId&&verified.assetIds.includes(placement.assetId);
 const currentInspection=inspection?.key===key?inspection.reading:null;
 const unavailable=blockedReason??(!documentId?'Open a Plan before using Image Studio.':null);
 const status=unavailable?'unavailable':currentInspection?.status==='failed'?'failed':currentInspection?.status==='unavailable'?'unavailable':usable?'ready':'pending';
 useTourOwnerReading({step:'image',dispatchScope:placement?.generation?.scope,target:verified?.pin??null,control:'image',status,reason:unavailable??(status==='ready'?undefined:currentInspection?.reason??'Open Image Studio to inspect generation controls. Generate and place artwork, then Save and inspect the exact saved Plan. This step has not been demonstrated yet.'),
  ...(usable&&status==='ready'?{observation:{step:'image',target:verified.pin,origin:placement.generation?'acknowledged':'existing',observedAt:placement.generation?.observedAt??placement.observedAt,receiptId:`image:${placement.assetId}:${verified.pin.revisionId}`,proof:{kind:'generated-image',assetId:placement.assetId,generation:placement.generation?'observed':'existing-library',model:placement.generation?.model??null,generationObservedAt:placement.generation?.observedAt??null,placementObservedAt:placement.observedAt,savedPlanVersionId:verified.pin.revisionId!}}}:{})});
 return <Context.Provider value={{inspect,captureScope:tour?.captureScope??(()=>null),generated,placed}}>{children}</Context.Provider>;
}
