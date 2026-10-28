import {createContext,useCallback,useContext,useRef,useState,type ReactNode} from 'react';
import {MEDIA_ASSET_ID} from '../media/mediaReferences';
import {useGuidedTour,useTourOwnerReading,type TourDispatchScope} from './GuidedTour';
import type {TargetPin} from './protocol';
interface Generation {model:string;observedAt:string;scope:TourDispatchScope}
interface Placement {key:string;assetId:string;generation:Generation|null;observedAt:string}
interface ImageApi {captureScope:()=>TourDispatchScope|null;generated:(assetIds:string[],model:string,scope:TourDispatchScope|null)=>void;placed:(assetId:string)=>void}
const Context=createContext<ImageApi|null>(null);
export const useTourImage=()=>useContext(Context);
export function collectTourMediaAssets(node:{type?:string;attrs?:Record<string,unknown>;content?:MediaNode[]}):string[]{
 return [...new Set([...(node.type==='mediaImage'&&typeof node.attrs?.assetId==='string'&&MEDIA_ASSET_ID.test(node.attrs.assetId)?[node.attrs.assetId]:[]),...(node.content??[]).flatMap(collectTourMediaAssets)])];
}
interface MediaNode {type?:string;attrs?:Record<string,unknown>;content?:MediaNode[]}
/** Generation and placement are observed separately; only verified saved content completes the step. */
export function TourImageProvider({worldId,documentId,verified,children}:{worldId:string;documentId:string|null;verified:{pin:TargetPin;assetIds:string[]}|null;children:ReactNode}){
 const tour=useGuidedTour(),key=JSON.stringify([worldId,documentId]);
 const latest=useRef({key,tracking:tour?.tracking});latest.current={key,tracking:tour?.tracking};
 const generations=useRef(new Map<string,Generation>());
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
 useTourOwnerReading({step:'image',dispatchScope:placement?.generation?.scope,target:verified?.pin??null,control:'image',status:usable?'ready':'unavailable',reason:usable?undefined:'Generate an image, place the retained artwork in this Plan, then Save the Plan. Start Play verifies its exact saved version without starting a session.',
  ...(usable?{observation:{step:'image',target:verified.pin,origin:placement.generation?'acknowledged':'existing',observedAt:placement.generation?.observedAt??placement.observedAt,receiptId:`image:${placement.assetId}:${verified.pin.revisionId}`,proof:{kind:'generated-image',assetId:placement.assetId,generation:placement.generation?'observed':'existing-library',model:placement.generation?.model??null,generationObservedAt:placement.generation?.observedAt??null,placementObservedAt:placement.observedAt,savedPlanVersionId:verified.pin.revisionId!}}}:{})});
 return <Context.Provider value={{captureScope:tour?.captureScope??(()=>null),generated,placed}}>{children}</Context.Provider>;
}
