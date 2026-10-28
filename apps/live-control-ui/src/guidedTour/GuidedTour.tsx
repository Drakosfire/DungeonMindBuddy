import type {WorldAgentConversationHistoryResponse} from '../api/types';
import {useSessionMemoryReading} from './MemoryObservations';
import {createContext,useCallback,useContext,useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {ADVENTURES,JOURNEY_STEPS,type Adventure,type StepId} from './definition';
import {createWalkthrough,reduceTour,samePin,validObservation,type Observation,type TargetPin,type TourAction} from './protocol';
import {pointerKey,readWalkthrough,writeWalkthrough,type StoredWalkthrough} from './storage';
import './guidedTour.css';
export interface TourOwnerReading {
 step:StepId;target:TargetPin|null;parent?:TargetPin;control:string;label?:string;
 status:'ready'|'unavailable'|'failed';reason?:string;observation?:Observation;
}
interface TourApi {
 tracking:boolean;open:()=>void;recordRunCreation:(observation:Observation)=>void;publish:(token:symbol,reading:TourOwnerReading|null)=>void;
}
const TourContext=createContext<TourApi|null>(null);
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
 const current=useRef(stored);current.current=stored;
 const runCreationReceipts=useRef(new Map<string,Observation>());
 const mounted=useRef(true),queue=useRef(Promise.resolve()),externalEpoch=useRef(0);
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
    const next=action.kind==='start'?createWalkthrough(worldId,action.adventure,crypto.randomUUID(),new Date().toISOString()):expected?reduceTour(expected.record,action):null;
    if(!next)return;
    const value=writeWalkthrough(localStorage,next,expected);current.current=value;setStored(value);setError(null);
   });
  }).catch(cause=>{if(mounted.current)setError(cause instanceof Error?cause.message:'The walkthrough could not be retained.');});
 },[worldId]);
 const publish=useCallback((token:symbol,reading:TourOwnerReading|null)=>{
  if(!mounted.current)return;
  setOwners(previous=>{const next=new Map(previous);if(reading&&worldId&&(!reading.target||reading.target.worldId===worldId))next.set(token,reading);else next.delete(token);return next;});
  if(reading?.observation&&reading.target?.worldId===worldId&&current.current?.record.phase==='running')change({kind:'observe',observation:reading.observation});
 },[change,worldId]);
 const recordRunCreation=useCallback((observation:Observation)=>{
  const walk=current.current?.record;
  if(!worldId||!walk||walk.phase!=='running'||observation.step!=='play'||observation.origin!=='acknowledged'||!validObservation(observation,worldId))return;
  runCreationReceipts.current.set(observation.receiptId,observation);
  if(!walk.bindings.run&&walk.bindings.plan&&observation.parent&&samePin(walk.bindings.plan,observation.parent))change({kind:'bind',pin:observation.target,parent:observation.parent});
  change({kind:'observe',observation});
 },[change,worldId]);
 const memoryReading=useSessionMemoryReading(history,stored?.record??null),memoryToken=useRef(Symbol('session-memory'));
 const memorySignature=JSON.stringify(memoryReading);
 useEffect(()=>{publish(memoryToken.current,memoryReading);return()=>publish(memoryToken.current,null);},[publish,memorySignature]);
 const api=useMemo(()=>({tracking:stored?.record.phase==='running',open:()=>setVisible(true),publish,recordRunCreation}),[publish,recordRunCreation,stored?.record.phase]);
 const walkthrough=stored?.record;
 const renderedEpoch=externalEpoch.current;
 const userChange=(action:TourAction|{kind:'start';adventure:Adventure})=>change(action,stored?.record.id??null,renderedEpoch);
 const step=JOURNEY_STEPS[walkthrough?.index??0];
 const candidates=Array.from(owners.values()).filter(r=>r.step===step.id);
 const reading=candidates.length===1?candidates[0]:null;
 const readingSignature=JSON.stringify(reading);
 const row=walkthrough?.steps[step.id];
 const newerPlans=Array.from(owners.values()).flatMap(r=>r.step==='plan'&&r.status==='ready'&&r.target?[r.target]:r.step==='play'&&r.status==='ready'&&r.parent?[r.parent]:[]).filter(pin=>walkthrough?.bindings.plan&&pin.objectId===walkthrough.bindings.plan.objectId&&pin.revision>walkthrough.bindings.plan.revision);
 const revisedPlan=newerPlans.length&&newerPlans.every(pin=>samePin(pin,newerPlans[0]))?newerPlans[0]:null;
 useEffect(()=>{
  if(!walkthrough||walkthrough.phase!=='running'||!reading||reading.status==='ready'||!reading.reason||!row
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
   &&Array.from(owners.values()).filter(other=>other.step===candidate.step).length===1)userChange({kind:'observe',observation:candidate.observation});
  for(const receipt of runCreationReceipts.current.values())if(samePin(receipt.target,reading.target))userChange({kind:'observe',observation:receipt});
 };
 const showControl=()=>{
  const targets=document.querySelectorAll<HTMLElement>(`[data-guided-control~="${step.control}"]`);
  if(targets.length!==1){setError(targets.length?'More than one control is available. Open the intended object first.':'Open the surface and controls described in this step.');return;}
  const target=targets[0];
  target.scrollIntoView({block:'center',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
  target.setAttribute('data-guided-highlight','true');
  target.focus({preventScroll:true});
 };
 useEffect(()=>()=>{document.querySelectorAll('[data-guided-highlight]').forEach(node=>node.removeAttribute('data-guided-highlight'));},[step.id,visible]);
 const exportRecord=()=>{
  if(!walkthrough)return;
  const url=URL.createObjectURL(new Blob([JSON.stringify({definition:{id:'buddy-live-journey',version:1,steps:JOURNEY_STEPS},walkthrough},null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download=`buddy-walkthrough-${walkthrough.id}.json`;link.click();URL.revokeObjectURL(url);
 };
 return <TourContext.Provider value={api}>{children}{visible&&<aside className="guided-tour" aria-label="Guided journey">
  <header><strong>Guided journey</strong><button type="button" aria-label="Close tour panel" onClick={()=>setVisible(false)}>×</button></header>
  <p className="guided-tour__scope">Guidance uses the ordinary controls. It never repeats your actions.</p>
  {!worldId?<p>Select a managed World before starting a walkthrough.</p>:!walkthrough?<><p>Choose the adventure you are walking through in this World.</p>{Object.entries(ADVENTURES).map(([id,label])=><button key={id} type="button" disabled={!!error} onClick={()=>userChange({kind:'start',adventure:id as Adventure})}>{label}</button>)}</>:<>
   <p>{ADVENTURES[walkthrough.adventure]} · {worldName??'Selected World'}</p>
   <p role="status">{walkthrough.phase==='running'?`${walkthrough.index+1} of ${JOURNEY_STEPS.length}`:walkthrough.phase==='paused'?'Guidance paused':'Walkthrough exited. Its record is retained.'}</p>
   {revisedPlan&&!walkthrough.bindings.run&&<p>The selected Plan has a newer verified saved version. <button type="button" onClick={()=>userChange({kind:'bind',pin:revisedPlan})}>Use saved Plan version {revisedPlan.revision}</button></p>}
   <h2>{step.title}</h2><p>{step.purpose}</p><p><strong>Expected:</strong> {step.expected}</p><p>{step.action}</p>
   <p role="status">{walkthrough.steps[step.id].state==='completed'?'Demonstrated during this walkthrough':walkthrough.steps[step.id].state==='existing'?'Existing example inspected':walkthrough.steps[step.id].state}{walkthrough.steps[step.id].reason?` · ${walkthrough.steps[step.id].reason}`:''}</p>
   {reading?.status!=='ready'?<p>{reading?.reason??(candidates.length>1?'Open one intended object to identify the control.':'Open the ordinary controls for this step. This walkthrough has not verified its result yet.')}</p>:null}
   {reading?.status==='ready'&&reading.target&&(!walkthrough.bindings[reading.target.kind]||reading.target.objectId===walkthrough.bindings[reading.target.kind]!.objectId&&reading.target.revision>walkthrough.bindings[reading.target.kind]!.revision&&reading.target.kind!=='run'&&!(reading.target.kind==='plan'&&walkthrough.bindings.run))?<button type="button" onClick={bind}>Use this {reading.target.kind}{reading.label?` · ${reading.label}`:''}</button>:null}
   {reading?.target&&walkthrough.bindings[reading.target.kind]&&!samePin(walkthrough.bindings[reading.target.kind]!,reading.target)&&reading.target.objectId!==walkthrough.bindings[reading.target.kind]!.objectId?<p>This is a different target. Reopen the bound object or restart guidance; the earlier record will be kept.</p>:null}
   <button type="button" onClick={showControl}>Show control</button>
   <div className="guided-tour__actions"><button type="button" disabled={!walkthrough.index} onClick={()=>userChange({kind:'move',index:walkthrough.index-1})}>Back</button><button type="button" disabled={walkthrough.index===JOURNEY_STEPS.length-1} onClick={()=>userChange({kind:'move',index:walkthrough.index+1})}>Next</button>
    <button type="button" onClick={()=>userChange({kind:'phase',phase:walkthrough.phase==='running'?'paused':'running'})}>{walkthrough.phase==='running'?'Pause':'Resume'}</button>
    <button type="button" disabled={walkthrough.phase!=='running'} onClick={()=>userChange({kind:'disposition',step:step.id,state:'skipped',reason:'Explicitly skipped in guidance; no product action was performed.'})}>Skip</button>
   </div>
   <details><summary>Steps and demonstrated results</summary><ol>{JOURNEY_STEPS.map((s,index)=><li key={s.id}><button type="button" onClick={()=>userChange({kind:'move',index})}>{s.title}</button> · {walkthrough.steps[s.id].state}</li>)}</ol></details>
   <div className="guided-tour__actions"><button type="button" onClick={exportRecord}>Export walkthrough</button><button type="button" onClick={()=>userChange({kind:'phase',phase:'exited'})}>Exit</button><button type="button" onClick={()=>userChange({kind:'start',adventure:walkthrough.adventure})}>Restart guidance</button></div>
  </>}
  {error?<div role="alert"><p>{error}</p><button type="button" onClick={reload}>Reload saved guidance</button></div>:null}
 </aside>}</TourContext.Provider>;
}
