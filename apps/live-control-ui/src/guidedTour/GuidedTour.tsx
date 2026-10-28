import {createContext,useCallback,useContext,useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {ADVENTURES,JOURNEY_STEPS,type Adventure,type StepId} from './definition';
import {createWalkthrough,reduceTour,samePin,type Observation,type TargetPin,type TourAction} from './protocol';
import {pointerKey,readWalkthrough,writeWalkthrough,type StoredWalkthrough} from './storage';
import './guidedTour.css';
export interface TourOwnerReading {
 step:StepId;target:TargetPin|null;parent?:TargetPin;control:string;
 status:'ready'|'unavailable'|'failed';reason?:string;observation?:Observation;
}
interface TourApi {
 open:()=>void;publish:(token:symbol,reading:TourOwnerReading|null)=>void;
}
const TourContext=createContext<TourApi|null>(null);
export const useGuidedTour=()=>useContext(TourContext);
/** Owners call this only with admitted current state, never optimistic button state. */
export function useTourOwnerReading(reading:TourOwnerReading|null){
 const api=useGuidedTour(),token=useRef(Symbol('tour-owner'));
 const signature=JSON.stringify(reading);
 useEffect(()=>{api?.publish(token.current,reading);return()=>api?.publish(token.current,null);},[api?.publish,signature]);
}
export function GuidedTourProvider({worldId,children}:{worldId:string|null;children:ReactNode}){
 const [visible,setVisible]=useState(false),[stored,setStored]=useState<StoredWalkthrough|null>(null),[error,setError]=useState<string|null>(null);
 const [owners,setOwners]=useState<Map<symbol,TourOwnerReading>>(new Map());
 const current=useRef(stored);current.current=stored;
 const mounted=useRef(true),queue=useRef(Promise.resolve()),externalEpoch=useRef(0);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;}},[]);
 const reload=useCallback(()=>{
  if(!worldId){setStored(null);return;}
  try{const value=readWalkthrough(localStorage,worldId);current.current=value;setStored(value);setError(null);}
  catch(cause){setError(cause instanceof Error?cause.message:'The walkthrough could not be read.');}
 },[worldId]);
 useEffect(()=>{reload();const changed=(e:StorageEvent)=>{if(worldId&&(e.key===pointerKey(worldId)||e.key?.startsWith(`dmb:guided-journey:v1:${encodeURIComponent(worldId)}:`))){externalEpoch.current++;reload();}};window.addEventListener('storage',changed);return()=>window.removeEventListener('storage',changed);},[reload,worldId]);
 const change=useCallback((action:TourAction|{kind:'start';adventure:Adventure})=>{
  if(!worldId||!mounted.current)return;
  const epoch=externalEpoch.current;
  queue.current=queue.current.catch(()=>{}).then(async()=>{
   if(!navigator.locks)throw new Error('This browser cannot coordinate saved tour guidance across tabs. Ordinary Buddy controls remain available.');
   await navigator.locks.request(`dmb:guided-journey:${worldId}`,()=>{
    if(!mounted.current)return;
    if(epoch!==externalEpoch.current)throw new Error('Another tab changed this guidance while the action was pending. Reload its saved record.');
    const actual=readWalkthrough(localStorage,worldId),expected=current.current;
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
 const api=useMemo(()=>({open:()=>setVisible(true),publish}),[publish]);
 const walkthrough=stored?.record;
 const step=JOURNEY_STEPS[walkthrough?.index??0];
 const candidates=Array.from(owners.values()).filter(r=>r.step===step.id);
 const reading=candidates.length===1?candidates[0]:null;
 const bind=()=>{
  if(!reading?.target)return;
  change({kind:'bind',pin:reading.target,...(reading.parent?{parent:reading.parent}:{})});
  if(reading.observation)change({kind:'observe',observation:reading.observation});
 };
 const showControl=()=>{
  const targets=document.querySelectorAll<HTMLElement>(`[data-guided-control="${step.control}"]`);
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
  {!worldId?<p>Select a managed World before starting a walkthrough.</p>:!walkthrough?<><p>Choose the adventure you are walking through in this World.</p>{Object.entries(ADVENTURES).map(([id,label])=><button key={id} type="button" disabled={!!error} onClick={()=>change({kind:'start',adventure:id as Adventure})}>{label}</button>)}</>:<>
   <p>{ADVENTURES[walkthrough.adventure]} · {walkthrough.worldId}</p>
   <p role="status">{walkthrough.phase==='running'?`${walkthrough.index+1} of ${JOURNEY_STEPS.length}`:walkthrough.phase==='paused'?'Guidance paused':'Walkthrough exited. Its record is retained.'}</p>
   <h2>{step.title}</h2><p>{step.purpose}</p><p><strong>Expected:</strong> {step.expected}</p><p>{step.action}</p>
   <p role="status">{walkthrough.steps[step.id].state==='completed'?'Demonstrated during this walkthrough':walkthrough.steps[step.id].state==='existing'?'Existing example inspected':walkthrough.steps[step.id].state}{walkthrough.steps[step.id].reason?` · ${walkthrough.steps[step.id].reason}`:''}</p>
   {reading?.status!=='ready'?<p>{reading?.reason??(candidates.length>1?'Open one intended object to identify the control.':'Open the ordinary controls for this step. This walkthrough has not verified its result yet.')}</p>:null}
   {reading?.target&&(!walkthrough.bindings[reading.target.kind]||reading.target.objectId===walkthrough.bindings[reading.target.kind]!.objectId&&reading.target.revision>walkthrough.bindings[reading.target.kind]!.revision&&reading.target.kind!=='run'&&!(reading.target.kind==='plan'&&walkthrough.bindings.run))?<button type="button" onClick={bind}>Use this {reading.target.kind} · {reading.target.objectId}</button>:null}
   {reading?.target&&walkthrough.bindings[reading.target.kind]&&!samePin(walkthrough.bindings[reading.target.kind]!,reading.target)&&reading.target.objectId!==walkthrough.bindings[reading.target.kind]!.objectId?<p>This is a different target. Reopen the bound object or restart guidance; the earlier record will be kept.</p>:null}
   <button type="button" onClick={showControl}>Show control</button>
   <div className="guided-tour__actions"><button type="button" disabled={!walkthrough.index} onClick={()=>change({kind:'move',index:walkthrough.index-1})}>Back</button><button type="button" disabled={walkthrough.index===JOURNEY_STEPS.length-1} onClick={()=>change({kind:'move',index:walkthrough.index+1})}>Next</button>
    <button type="button" onClick={()=>change({kind:'phase',phase:walkthrough.phase==='running'?'paused':'running'})}>{walkthrough.phase==='running'?'Pause':'Resume'}</button>
    <button type="button" disabled={walkthrough.phase!=='running'} onClick={()=>change({kind:'disposition',step:step.id,state:'skipped',reason:'Explicitly skipped in guidance; no product action was performed.'})}>Skip</button>
   </div>
   <details><summary>Steps and demonstrated results</summary><ol>{JOURNEY_STEPS.map((s,index)=><li key={s.id}><button type="button" onClick={()=>change({kind:'move',index})}>{s.title}</button> · {walkthrough.steps[s.id].state}</li>)}</ol></details>
   <div className="guided-tour__actions"><button type="button" onClick={exportRecord}>Export walkthrough</button><button type="button" onClick={()=>change({kind:'phase',phase:'exited'})}>Exit</button><button type="button" onClick={()=>change({kind:'start',adventure:walkthrough.adventure})}>Restart guidance</button></div>
  </>}
  {error?<div role="alert"><p>{error}</p><button type="button" onClick={reload}>Reload saved guidance</button></div>:null}
 </aside>}</TourContext.Provider>;
}
