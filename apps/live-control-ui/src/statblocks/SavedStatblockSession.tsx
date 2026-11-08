import {createContext,useContext,useEffect,useMemo,useRef,useState,useSyncExternalStore,type ReactNode} from 'react';
import {deferredComponent} from '../ui/deferredComponent';
import {getAppLocationSnapshot,subscribeAppLocation} from '../chrome/appNavigation';
import {GenerationPlanProvider,useGenerationPlan} from '../guidedTour/GenerationObservations';
import {TourEncounterProvider,useTourEncounter,type TourEncounterScope} from '../guidedTour/EncounterScope';
import type {TargetPin} from '../guidedTour/protocol';
import './SavedStatblockDialog.css';

const Editor=deferredComponent(()=>import('./revision/SavedMechanicsRevisionEditor').then(module=>({default:module.SavedMechanicsRevisionEditor})),'saved statblock editor');
type Target={worldId:string;draftId:string};
type Presentation={encounter:TourEncounterScope|null;generationPlan:TargetPin|null};
type Session={worldId:string|null;openStatblock:(target:Target,presentation?:Presentation)=>void};
const Context=createContext<Session|null>(null);
const targetKey=(target:Target)=>JSON.stringify([target.worldId,target.draftId]);
export const useSavedStatblockSession=()=>useContext(Context);

/** One owner per managed World; triggers never own an editing copy. */
export function SavedStatblockProvider({worldId,children}:{worldId:string|null;children:ReactNode}) {
  if(useContext(Context))throw new Error('Saved statblock sessions must have one shared host.');
  return <WorldSession key={worldId??'unavailable'} worldId={worldId}>{children}</WorldSession>;
}
function WorldSession({worldId,children}:{worldId:string|null;children:ReactNode}) {
  const [target,setTarget]=useState<Target|null>(null),[open,setOpen]=useState(false),[expanded,setExpanded]=useState(false),[message,setMessage]=useState('');
  const [presentation,setPresentation]=useState<Presentation>({encounter:null,generationPlan:null});
  const current=useRef<Target|null>(null),reason=useRef<string|null>(null),dialog=useRef<HTMLDialogElement>(null);
  const location=useSyncExternalStore(subscribeAppLocation,getAppLocationSnapshot),lastLocation=useRef(location);
  useEffect(()=>{if(lastLocation.current!==location){lastLocation.current=location;setOpen(false);}},[location]);
  const session=useMemo<Session>(()=>({worldId,openStatblock:(next,context={encounter:null,generationPlan:null})=>{
    if(!worldId||next.worldId!==worldId){setMessage('This statblock is unavailable in the selected World.');return;}
    if(context.encounter&&context.encounter.plan.worldId!==worldId||context.generationPlan&&context.generationPlan.worldId!==worldId){setMessage('The statblock presentation belongs to another World.');return;}
    if(current.current&&targetKey(current.current)===targetKey(next)){if(!reason.current)setPresentation(structuredClone(context));setMessage('');setOpen(true);return;}
    if(current.current&&reason.current){setMessage(reason.current);setOpen(true);return;}
    current.current=next;reason.current='Opening saved mechanics. Wait before choosing another statblock.';
    setTarget(next);setPresentation(structuredClone(context));setMessage('');setOpen(true);
  }}),[worldId]);
  useEffect(()=>{
    const node=dialog.current;
    if(open&&node&&!node.open)node.showModal();else if(!open&&node?.open)node.close();
  },[open]);
  const key=target?targetKey(target):null;
  return <Context.Provider value={session}>
    {children}
    {!open&&message&&<p role="alert">{message}</p>}
    <dialog ref={dialog} className={`saved-statblock-dialog${expanded?' saved-statblock-dialog--expanded':''}`}
      aria-label="Saved statblock editor" onClose={()=>setOpen(false)} onKeyDown={event=>{if(event.key==='Escape')event.stopPropagation();}}>
      <header><strong>Statblock</strong><div>
        <button type="button" aria-pressed={expanded} onClick={()=>setExpanded(value=>!value)}>{expanded?'Restore size':'Expand statblock'}</button>
        <button type="button" autoFocus aria-label="Close statblock" onClick={()=>setOpen(false)}>×</button>
      </div></header>
      <div className="saved-statblock-dialog__body">
        {message&&<p role="alert">{message}</p>}
        {target&&<TourEncounterProvider scope={presentation.encounter}><GenerationPlanProvider pin={presentation.generationPlan}><Editor key={key!} worldId={target.worldId} draftId={target.draftId} autoLoad
          onSwitchGuardChange={value=>{if(current.current&&targetKey(current.current)===key)reason.current=value;}}/></GenerationPlanProvider></TourEncounterProvider>}
      </div>
    </dialog>
  </Context.Provider>;
}
export function SavedStatblockButton({worldId,draftId}:{worldId:string;draftId:string}) {
  const encounter=useTourEncounter(),generationPlan=useGenerationPlan();
  const session=useSavedStatblockSession(),available=session?.worldId===worldId;
  return <button type="button" disabled={!available} title={available?undefined:'Saved statblock editing is unavailable in this host.'}
    onClick={()=>session?.openStatblock({worldId,draftId},{encounter,generationPlan})}>Open statblock</button>;
}
