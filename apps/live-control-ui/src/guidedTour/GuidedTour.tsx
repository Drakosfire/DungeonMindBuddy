import {TourNavigationRegistry,TourNavigationProvider,TourNavigationActions,navigationScope} from './Navigation';
import type {WorldAgentConversationHistoryResponse} from '../api/types';
import {useSessionMemoryReading} from './MemoryObservations';
import {createContext,useCallback,useContext,useEffect,useLayoutEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {ADVENTURES,JOURNEY_STEPS,journeySteps,type Adventure,type StepId} from './definition';
import {createWalkthrough,generationScope,sameGenerationScope,type GenerationScope,reduceTour,samePin,validObservation,type Observation,type TargetPin,type TourAction} from './protocol';
import {pointerKey,readWalkthrough,writeWalkthrough,type StoredWalkthrough} from './storage';
import './guidedTour.css';
export interface TourOwnerReading {
 step:StepId;target:TargetPin|null;parent?:TargetPin;control:string;label?:string;
 status:'ready'|'unavailable'|'failed';reason?:string;observation?:Observation;generationScope?:GenerationScope|null;dispatchScope?:TourDispatchScope|null;
}
export interface TourDispatchScope {worldId:string;walkthroughId:string;epoch:number;/** Present only when a page was explicitly selected before dispatch. */page?:TargetPin}
interface TourApi {
 tracking:boolean;captureGenerationScope:()=>GenerationScope|null;isGenerationScopeCurrent:(scope:GenerationScope|null)=>boolean;open:()=>void;recordConversationDispatch:(correlationKey:string,scope:TourDispatchScope|null)=>void;captureScope:()=>TourDispatchScope|null;isScopeCurrent:(scope:TourDispatchScope|null)=>boolean;recordRunCreation:(observation:Observation,scope:TourDispatchScope|null)=>void;publish:(token:symbol,reading:TourOwnerReading|null)=>void;
}
const TourContext=createContext<TourApi|null>(null);
function usableControl(target:HTMLElement):boolean {
 if(!target.isConnected||target.closest('[hidden],[inert],[aria-hidden="true"]')||target.matches(':disabled,[aria-disabled="true"]'))return false;
 for(let node:HTMLElement|null=target;node;node=node.parentElement){const style=window.getComputedStyle(node);if(style.display==='none'||style.visibility==='hidden'||style.visibility==='collapse')return false;}
 return target.getClientRects().length>0;
}
interface FocusedControl {target:HTMLElement;worldId:string;walkthroughId:string;stepId:StepId;epoch:number}

export const useGuidedTour=()=>useContext(TourContext);
/** Owners call this only with admitted current state, never optimistic button state. */
export function useTourOwnerReading(reading:TourOwnerReading|null){
 const api=useGuidedTour(),token=useRef(Symbol('tour-owner'));
 const signature=JSON.stringify(reading);
 useEffect(()=>{api?.publish(token.current,reading);return()=>api?.publish(token.current,null);},[api?.publish,signature]);
}
export function GuidedTourProvider({worldId,worldName,children,history=null}:{worldId:string|null;worldName?:string;children:ReactNode;history?:WorldAgentConversationHistoryResponse|null}){
 const [visible,setVisible]=useState(false),[stored,setStored]=useState<StoredWalkthrough|null>(null),[error,setError]=useState<string|null>(null);
 const [owners,setOwners]=useState<Map<symbol,TourOwnerReading>>(new Map());
 const [focusedControl,setFocusedControl]=useState<FocusedControl|null>(null);
 const open=useCallback(()=>{setFocusedControl(null);setVisible(true);},[]);
 const current=useRef(stored);current.current=stored;
 const runCreationReceipts=useRef(new Map<string,Observation>());
 const mounted=useRef(true),queue=useRef(Promise.resolve()),externalEpoch=useRef(0);
 const navigationWorld=useRef(worldId);navigationWorld.current=worldId;
 const [navigationRegistry]=useState(()=>new TourNavigationRegistry(()=>{
  const world=navigationWorld.current;if(!world)return null;
  try{return navigationScope(readWalkthrough(localStorage,world)?.record??null,externalEpoch.current);}catch{return null;}
 }));
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;}},[]);
 const reload=useCallback(()=>{
  if(!worldId){setStored(null);return;}
  try{const value=readWalkthrough(localStorage,worldId);current.current=value;setStored(value);setError(null);}
  catch(cause){setError(cause instanceof Error?cause.message:'The walkthrough could not be read.');}
 },[worldId]);
 useEffect(()=>{reload();const changed=(e:StorageEvent)=>{if(worldId&&(e.key===pointerKey(worldId)||e.key?.startsWith(`dmb:guided-journey:v1:${encodeURIComponent(worldId)}:`))){externalEpoch.current++;reload();}};window.addEventListener('storage',changed);return()=>window.removeEventListener('storage',changed);},[reload,worldId]);
 const change=useCallback((action:TourAction|{kind:'start';adventure:Adventure},expectedId:string|null=current.current?.record.id??null,expectedEpoch=externalEpoch.current)=>{
  if(!worldId||!mounted.current)return;
  const epoch=expectedEpoch;
  queue.current=queue.current.catch(()=>{}).then(async()=>{
   if(!navigator.locks)throw new Error('This browser cannot coordinate saved tour guidance across tabs. Ordinary Buddy controls remain available.');
   await navigator.locks.request(`dmb:guided-journey:${worldId}`,()=>{
    if(!mounted.current)return;
    if(epoch!==externalEpoch.current)throw new Error('Another tab changed this guidance while the action was pending. Reload its saved record.');
    const actual=readWalkthrough(localStorage,worldId),expected=current.current;
    if((expected?.record.id??null)!==expectedId)throw new Error('The selected walkthrough changed before this action. Reload its guidance.');
    if(actual?.bytes!==expected?.bytes||actual?.pointer!==expected?.pointer)throw new Error('Another tab changed the walkthrough. Reload its guidance before continuing.');
    if(action.kind!=='start'&&expected?.record.version!==3)throw new Error('Historical guidance is read-only. Restart guidance to create a new walkthrough.');
    const next=action.kind==='start'?createWalkthrough(worldId,action.adventure,crypto.randomUUID(),new Date().toISOString()):expected?reduceTour(expected.record,action):null;
    if(!next)return;
    const value=writeWalkthrough(localStorage,next,expected);current.current=value;setStored(value);setError(null);
   });
  }).catch(cause=>{if(mounted.current)setError(cause instanceof Error?cause.message:'The walkthrough could not be retained.');});
 },[worldId]);
 const scopeWorld=useRef(worldId);scopeWorld.current=worldId;
 const isScopeCurrent=useCallback((scope:TourDispatchScope|null)=>{
  if(!scope||scopeWorld.current!==scope.worldId||externalEpoch.current!==scope.epoch||current.current?.record.id!==scope.walkthroughId||current.current.record.version!==3||current.current.record.phase!=='running')return false;
  try{return readWalkthrough(localStorage,scope.worldId)?.record.id===scope.walkthroughId;}catch{return false;}
 },[]);
 const captureGenerationScope=useCallback(()=>generationScope(current.current?.record??null),[]);
 const isGenerationScopeCurrent=useCallback((scope:GenerationScope|null)=>{if(!scope||scopeWorld.current!==scope.worldId||!sameGenerationScope(scope,generationScope(current.current?.record??null)))return false;try{return sameGenerationScope(scope,generationScope(readWalkthrough(localStorage,scope.worldId)?.record??null));}catch{return false;}},[]);
 const captureScope=useCallback(()=>{const record=current.current?.record;const scope=worldId&&record?{worldId,walkthroughId:record.id,epoch:externalEpoch.current,...(record.bindings.page?{page:record.bindings.page}:{})}:null;return isScopeCurrent(scope)?scope:null;},[worldId,isScopeCurrent]);
 const publish=useCallback((token:symbol,incoming:TourOwnerReading|null)=>{
  const boundPage=current.current?.record.bindings.page;
  const pageAtDispatch=incoming?.dispatchScope?.page;
  const pageSelectedAtDispatch=incoming?.step!=='authoring'||!!boundPage&&!!pageAtDispatch&&samePin(boundPage,pageAtDispatch);
  const reading=incoming?.observation?.origin==='acknowledged'&&(incoming.step==='generation'?!isGenerationScopeCurrent(incoming.generationScope??null):!isScopeCurrent(incoming.dispatchScope??null)||!pageSelectedAtDispatch)?{...incoming,observation:{...incoming.observation,origin:'existing' as const}}:incoming;
  if(!mounted.current)return;
  setOwners(previous=>{const next=new Map(previous);if(reading&&worldId&&(!reading.target||reading.target.worldId===worldId))next.set(token,reading);else next.delete(token);return next;});
  if(reading?.observation&&reading.target?.worldId===worldId&&current.current?.record.version===3&&current.current.record.phase==='running')change({kind:'observe',observation:reading.observation});
 },[change,worldId,isScopeCurrent,isGenerationScopeCurrent]);
 const recordRunCreation=useCallback((observation:Observation,scope:TourDispatchScope|null)=>{
  const walk=current.current?.record;
  if(!isScopeCurrent(scope)||!worldId||!walk||walk.phase!=='running'||observation.step!=='play'||observation.origin!=='acknowledged'||!validObservation(observation,worldId))return;
  runCreationReceipts.current.set(observation.receiptId,observation);
  if(!walk.bindings.run&&walk.bindings.plan&&observation.parent&&samePin(walk.bindings.plan,observation.parent))change({kind:'bind',pin:observation.target,parent:observation.parent},scope!.walkthroughId,scope!.epoch);
  change({kind:'observe',observation},scope!.walkthroughId,scope!.epoch);
 },[change,worldId,isScopeCurrent]);
 const conversationDispatches=useRef(new Map<string,TourDispatchScope|null>());
 // The conversation owner supplies its existing World-scoped idempotency key.
 // The first dispatch owns this request even if guidance restarts before retry.
 const recordConversationDispatch=useCallback((correlationKey:string,scope:TourDispatchScope|null)=>{if(!conversationDispatches.current.has(correlationKey))conversationDispatches.current.set(correlationKey,scope);},[]);
 const memoryReading=useSessionMemoryReading(history,stored?.record??null,conversationDispatches.current),memoryToken=useRef(Symbol('session-memory'));
 const memorySignature=JSON.stringify(memoryReading);
 useEffect(()=>{publish(memoryToken.current,memoryReading);return()=>publish(memoryToken.current,null);},[publish,memorySignature]);
 const api=useMemo(()=>({tracking:stored?.record.version===3&&stored.record.phase==='running',captureGenerationScope,isGenerationScopeCurrent,open,publish,recordRunCreation,captureScope,isScopeCurrent,recordConversationDispatch}),[captureGenerationScope,isGenerationScopeCurrent,open,publish,recordRunCreation,captureScope,isScopeCurrent,recordConversationDispatch,stored?.record.phase,stored?.record.id,externalEpoch.current]);
 const walkthrough=stored?.record;
 const renderedEpoch=externalEpoch.current;
 const userChange=(action:TourAction|{kind:'start';adventure:Adventure})=>change(action,stored?.record.id??null,renderedEpoch);
 const steps=journeySteps(walkthrough?.version??3);
 const historical=!!walkthrough&&walkthrough.version!==3;
 const step=steps[walkthrough?.index??0];
 const candidates=Array.from(owners.values()).filter(r=>r.step===step.id);
 const reading=candidates.length===1?candidates[0]:null;
 const readingSignature=JSON.stringify(reading);
 const row=walkthrough?.steps[step.id];
 const newerPlans=Array.from(owners.values()).flatMap(r=>r.step==='plan'&&r.status==='ready'&&r.target?[r.target]:r.step==='play'&&r.status==='ready'&&r.parent?[r.parent]:[]).filter(pin=>walkthrough?.bindings.plan&&pin.objectId===walkthrough.bindings.plan.objectId&&pin.revision>walkthrough.bindings.plan.revision);
 const revisedPlan=newerPlans.length&&newerPlans.every(pin=>samePin(pin,newerPlans[0]))?newerPlans[0]:null;
 useEffect(()=>{
  if(!walkthrough||walkthrough.version!==3||walkthrough.phase!=='running'||!reading||reading.status==='ready'||!reading.reason||!row
   ||!['pending','failed','unavailable'].includes(row.state))return;
  const bound=reading.target?walkthrough.bindings[reading.target.kind]:null;
  if(bound&&reading.target&&bound.objectId!==reading.target.objectId)return;
  if(row.state===reading.status&&row.reason===reading.reason)return;
  change({kind:'disposition',step:step.id,state:reading.status,reason:reading.reason},walkthrough.id);
 },[walkthrough?.id,walkthrough?.phase,step.id,readingSignature,row?.state,row?.reason,change]);
 const bind=()=>{
  if(!reading?.target)return;
  userChange({kind:'bind',pin:reading.target,...(reading.parent?{parent:reading.parent}:{})});
  // Capture the other admitted capabilities already visible for this same exact object.
  // Multiple candidates for one capability remain ambiguous.
  for(const candidate of owners.values())if(candidate.observation&&candidate.target&&samePin(candidate.target,reading.target)
   &&Array.from(owners.values()).filter(other=>other.step===candidate.step).length===1)userChange({kind:'observe',observation:reading.target.kind==='page'||candidate.observation.origin==='acknowledged'&&!isScopeCurrent(candidate.dispatchScope??null)?{...candidate.observation,origin:'existing'}:candidate.observation});
  for(const receipt of runCreationReceipts.current.values())if(samePin(receipt.target,reading.target))userChange({kind:'observe',observation:receipt});
 };
 const showControl=()=>{
  const targets=document.querySelectorAll<HTMLElement>(`[data-guided-control~="${step.control}"]`);
  if(targets.length!==1){setError(targets.length?'More than one control is available. Open the intended object first.':'Open the surface and controls described in this step.');return;}
  if(!worldId||!walkthrough||!usableControl(targets[0])){setError('This control is not currently available. Open the surface and controls described in this step.');return;}
  setFocusedControl({target:targets[0],worldId,walkthroughId:walkthrough.id,stepId:step.id,epoch:renderedEpoch});
  setVisible(false);
 };
 useLayoutEffect(()=>{
  if(!focusedControl)return;
  const {target}=focusedControl;
  const selector=`[data-guided-control~="${JOURNEY_STEPS.find(item=>item.id===focusedControl.stepId)!.control}"]`;
  const stillCurrent=()=>{
   const targets=document.querySelectorAll<HTMLElement>(selector);
   return focusedControl.worldId===scopeWorld.current&&focusedControl.walkthroughId===current.current?.record.id
    &&focusedControl.stepId===JOURNEY_STEPS[current.current?.record.index??0].id&&focusedControl.epoch===externalEpoch.current
    &&targets.length===1&&targets[0]===target&&usableControl(target);
  };
  const refuse=()=>{setFocusedControl(null);setVisible(true);setError('The control changed or is unavailable. Reopen the intended controls before highlighting them.');};
  if(!stillCurrent()){refuse();return;}
  target.scrollIntoView({block:'center',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
  if(!stillCurrent()){refuse();return;}
  target.setAttribute('data-guided-highlight','true');target.focus({preventScroll:true});
  const observer=new MutationObserver(()=>{if(!stillCurrent())refuse();});
  observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['hidden','inert','aria-hidden','disabled','aria-disabled','class','style','data-guided-control']});
  return()=>{observer.disconnect();target.removeAttribute('data-guided-highlight');};
 },[focusedControl,worldId,walkthrough?.id,walkthrough?.index,renderedEpoch]);
 const retainedResult=row?.state==='completed'||row?.state==='existing';
 const availabilityMessage=reading?.status==='ready'?null:reading?.status==='failed'
  ?`Current inspection failed: ${reading.reason??'Open the ordinary controls to inspect the failure.'}`
  :retainedResult?'The recorded result is retained. Open its ordinary controls to inspect the current state.'
  :reading?.reason??(candidates.length>1?'Open one intended object to identify the control.':'Open the ordinary controls for this step. This walkthrough has not verified its result yet.');
 const exportRecord=()=>{
  if(!walkthrough)return;
  const url=URL.createObjectURL(new Blob([JSON.stringify({definition:{id:'buddy-live-journey',version:walkthrough.version,steps},walkthrough},null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download=`buddy-walkthrough-${walkthrough.id}.json`;link.click();URL.revokeObjectURL(url);
 };
 return <TourContext.Provider value={api}><TourNavigationProvider registry={navigationRegistry}>{children}{visible&&<aside className="guided-tour" aria-label="Guided journey">
  <header><strong>Guided journey</strong><button type="button" aria-label="Close tour panel" onClick={()=>setVisible(false)}>×</button></header>
  <p className="guided-tour__scope">Guidance uses the ordinary controls. It never repeats your actions.</p>
  {!worldId?<p>Select a managed World before starting a walkthrough.</p>:!walkthrough?<><p>Choose the adventure you are walking through in this World.</p>{Object.entries(ADVENTURES).map(([id,label])=><button key={id} type="button" disabled={!!error} onClick={()=>userChange({kind:'start',adventure:id as Adventure})}>{label}</button>)}</>:<>
   <p>{ADVENTURES[walkthrough.adventure]} · {worldName??'Selected World'}</p>
   <p role="status">{walkthrough.phase==='running'?`${walkthrough.index+1} of ${steps.length}`:walkthrough.phase==='paused'?'Guidance paused':'Walkthrough exited. Its record is retained.'}</p>
   {historical&&<p>This is a read-only record of the earlier 14-step tour. Restart guidance to begin a new walkthrough that includes creature generation. Its original record is retained.</p>}
   <fieldset disabled={historical} style={{border:0,padding:0,margin:0,minWidth:0}}>
   {revisedPlan&&!walkthrough.bindings.run&&<p>The selected Plan has a newer verified saved version. <button type="button" onClick={()=>userChange({kind:'bind',pin:revisedPlan})}>Use saved Plan version {revisedPlan.revision}</button></p>}
   <h2>{step.title}</h2><p>{step.purpose}</p><p><strong>Expected:</strong> {step.expected}</p><p>{step.action}</p>
   <p role="status">{walkthrough.steps[step.id].state==='completed'?'Demonstrated during this walkthrough':walkthrough.steps[step.id].state==='existing'?'Existing example inspected':walkthrough.steps[step.id].state}{walkthrough.steps[step.id].reason?` · ${walkthrough.steps[step.id].reason}`:''}</p>
   {availabilityMessage?<p>{availabilityMessage}</p>:null}
   {reading?.status==='ready'&&reading.target&&(!walkthrough.bindings[reading.target.kind]||reading.target.objectId===walkthrough.bindings[reading.target.kind]!.objectId&&reading.target.revision>walkthrough.bindings[reading.target.kind]!.revision&&reading.target.kind!=='run'&&!(reading.target.kind==='plan'&&walkthrough.bindings.run))?<button type="button" onClick={bind}>Use this {reading.target.kind}{reading.label?` · ${reading.label}`:''}</button>:null}
   {reading?.target&&walkthrough.bindings[reading.target.kind]&&!samePin(walkthrough.bindings[reading.target.kind]!,reading.target)&&reading.target.objectId!==walkthrough.bindings[reading.target.kind]!.objectId?<p>This is a different target. Reopen the bound object or restart guidance; the earlier record will be kept.</p>:null}
   <TourNavigationActions scope={navigationScope(walkthrough??null,renderedEpoch)} onOpened={()=>{setFocusedControl(null);setVisible(false);}}/>
   <p>Show control hides this panel and highlights the control. Reopen Guided journey from navigation to continue.</p>
   <button type="button" onClick={showControl}>Show control</button>
   <div className="guided-tour__actions"><button type="button" disabled={!walkthrough.index} onClick={()=>userChange({kind:'move',index:walkthrough.index-1})}>Back</button><button type="button" disabled={walkthrough.index===steps.length-1} onClick={()=>userChange({kind:'move',index:walkthrough.index+1})}>Next</button>
    <button type="button" onClick={()=>userChange({kind:'phase',phase:walkthrough.phase==='running'?'paused':'running'})}>{walkthrough.phase==='running'?'Pause':'Resume'}</button>
    <button type="button" disabled={walkthrough.phase!=='running'} onClick={()=>userChange({kind:'disposition',step:step.id,state:'skipped',reason:'Explicitly skipped in guidance; no product action was performed.'})}>Skip</button>
   </div>
   <details><summary>Steps and demonstrated results</summary><ol>{steps.map((s,index)=><li key={s.id}><button type="button" onClick={()=>userChange({kind:'move',index})}>{s.title}</button> · {walkthrough.steps[s.id].state}</li>)}</ol></details>
   </fieldset>
   <div className="guided-tour__actions"><button type="button" onClick={exportRecord}>Export walkthrough</button><button type="button" disabled={historical} onClick={()=>userChange({kind:'phase',phase:'exited'})}>Exit</button><button type="button" onClick={()=>userChange({kind:'start',adventure:walkthrough.adventure})}>Restart guidance</button></div>
  </>}
  {error?<div role="alert"><p>{error}</p><button type="button" onClick={reload}>Reload saved guidance</button></div>:null}
 </aside>}</TourNavigationProvider></TourContext.Provider>;
}
