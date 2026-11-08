import {createContext,useContext,useEffect,useLayoutEffect,useMemo,useRef,useState,useSyncExternalStore,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {deferredComponent} from '../ui/deferredComponent';
import {getAppLocationSnapshot,subscribeAppLocation} from '../chrome/appNavigation';
import {GenerationPlanProvider,useGenerationPlan} from '../guidedTour/GenerationObservations';
import {TourEncounterProvider,useTourEncounter,type TourEncounterScope} from '../guidedTour/EncounterScope';
import type {TargetPin} from '../guidedTour/protocol';
import './SavedStatblockDialog.css';
import type {SavedMechanicsSessionState} from './revision/SavedMechanicsRevisionEditor';

const Editor=deferredComponent(()=>import('./revision/SavedMechanicsRevisionEditor').then(module=>({default:module.SavedMechanicsRevisionEditor})),'saved statblock editor');
type Target={worldId:string;draftId:string;revisionId?:string};
type Selection={target:Target;serial:number};
type Presentation={encounter:TourEncounterScope|null;generationPlan:TargetPin|null};
type Placement={kind:'hidden'}|{kind:'dialog'}|{kind:'inline';host:HTMLElement};
type Session={worldId:string|null;openStatblock:(target:Target,presentation?:Presentation,inlineHost?:HTMLElement)=>boolean;registerInlineHost:(host:HTMLElement,worldId:string)=>boolean;releaseInlineHost:(host:HTMLElement)=>void};
const Context=createContext<Session|null>(null);
const sameDraft=(a:Target,b:Target)=>a.worldId===b.worldId&&a.draftId===b.draftId;
export const useSavedStatblockSession=()=>useContext(Context);

/** One owner per managed World; triggers never own an editing copy. */
export function SavedStatblockProvider({worldId,children}:{worldId:string|null;children:ReactNode}) {
  if(useContext(Context))throw new Error('Saved statblock sessions must have one shared host.');
  return <WorldSession key={worldId??'unavailable'} worldId={worldId}>{children}</WorldSession>;
}
function WorldSession({worldId,children}:{worldId:string|null;children:ReactNode}) {
  const [selection,setSelection]=useState<Selection|null>(null),[placement,setPlacement]=useState<Placement>({kind:'hidden'}),[expanded,setExpanded]=useState(false),[message,setMessage]=useState('');
  const [presentation,setPresentation]=useState<Presentation>({encounter:null,generationPlan:null});
  const [editorMount]=useState(()=>{const node=document.createElement('div');node.className='saved-statblock-mount';node.tabIndex=-1;return node;});
  const parking=useRef<HTMLDivElement>(null),hosts=useRef(new Set<HTMLElement>()),returnHost=useRef<HTMLElement|null>(null);
  const placementRef=useRef(placement);placementRef.current=placement;
  const scrollReturn=useRef<{host:HTMLElement;positions:{node:HTMLElement;top:number;left:number}[]}|null>(null);
  function rememberInlineScroll(){
    const currentPlacement=placementRef.current;if(currentPlacement.kind!=='inline')return;
    const positions:{node:HTMLElement;top:number;left:number}[]=[];
    for(let node:HTMLElement|null=currentPlacement.host.parentElement;node;node=node.parentElement)positions.push({node,top:node.scrollTop,left:node.scrollLeft});
    scrollReturn.current={host:currentPlacement.host,positions};
  }
  const current=useRef<Selection|null>(null),observed=useRef<SavedMechanicsSessionState>({revisionId:null,busy:true,switchReason:'Opening saved mechanics. Wait before choosing another statblock.'}),dialog=useRef<HTMLDialogElement>(null);
  const location=useSyncExternalStore(subscribeAppLocation,getAppLocationSnapshot),lastLocation=useRef(location);
  useEffect(()=>{if(lastLocation.current!==location){lastLocation.current=location;returnHost.current=null;scrollReturn.current=null;setPlacement({kind:'hidden'});}},[location]);
  const session=useMemo<Session>(()=>({worldId,
    registerInlineHost:(host,owner)=>{if(owner!==worldId||!host.isConnected||host.closest('form'))return false;hosts.current.add(host);return true;},
    releaseInlineHost:host=>{
      hosts.current.delete(host);if(returnHost.current===host)returnHost.current=null;if(scrollReturn.current?.host===host)scrollReturn.current=null;
      if(placementRef.current.kind==='inline'&&placementRef.current.host===host){
        // Move before React removes the message. The portal destination and editor stay alive.
        parking.current?.appendChild(editorMount);placementRef.current={kind:'hidden'};setPlacement({kind:'hidden'});
      }
    },
    openStatblock:(next,context={encounter:null,generationPlan:null},inlineHost)=>{
      if(!worldId||next.worldId!==worldId){setMessage('This statblock is unavailable in the selected World.');return false;}
      if(context.encounter&&context.encounter.plan.worldId!==worldId||context.generationPlan&&context.generationPlan.worldId!==worldId){setMessage('The statblock presentation belongs to another World.');return false;}
      if(inlineHost&&(!hosts.current.has(inlineHost)||!inlineHost.isConnected||inlineHost.closest('form'))){setMessage('Inline statblock editing is unavailable here. Open the popup instead.');return false;}
      const show=()=>{scrollReturn.current=null;returnHost.current=inlineHost??null;setPlacement(inlineHost?{kind:'inline',host:inlineHost}:{kind:'dialog'});};
      if(current.current&&sameDraft(current.current.target,next)&&(!next.revisionId||!observed.current.busy&&next.revisionId===observed.current.revisionId)){
        if(!observed.current.switchReason)setPresentation(structuredClone(context));setMessage('');show();return true;
      }
      if(current.current&&observed.current.switchReason){rememberInlineScroll();setMessage(observed.current.switchReason);setPlacement({kind:'dialog'});return false;}
      const selected={target:next,serial:(current.current?.serial??0)+1};
      current.current=selected;observed.current={revisionId:null,busy:true,switchReason:'Opening saved mechanics. Wait before choosing another statblock.'};
      setSelection(selected);setPresentation(structuredClone(context));setMessage('');show();return true;
    },
  }),[worldId,editorMount]);
  useLayoutEffect(()=>{
    const destination=placement.kind==='inline'?placement.host:placement.kind==='dialog'?dialog.current:parking.current;
    destination?.appendChild(editorMount);
    if(placement.kind==='inline'){
      const snapshot=scrollReturn.current?.host===placement.host?scrollReturn.current:null;
      const restore=()=>{for(const row of snapshot?.positions??[])if(row.node.isConnected){row.node.scrollTop=row.top;row.node.scrollLeft=row.left;}};
      restore();
      const frame=requestAnimationFrame(()=>{if(editorMount.isConnected)editorMount.focus({preventScroll:Boolean(snapshot)});restore();if(scrollReturn.current===snapshot)scrollReturn.current=null;});
      return()=>cancelAnimationFrame(frame);
    }
  },[placement,editorMount]);
  useLayoutEffect(()=>()=>{editorMount.remove();},[editorMount]);
  useEffect(()=>{
    const node=dialog.current;
    if(placement.kind==='dialog'&&node&&!node.open)node.showModal();else if(placement.kind!=='dialog'&&node?.open)node.close();
  },[placement.kind]);
  function closePresentation(){
    const host=returnHost.current;
    if(placementRef.current.kind==='dialog'&&host&&hosts.current.has(host)&&host.isConnected)setPlacement({kind:'inline',host});
    else {returnHost.current=null;scrollReturn.current=null;setPlacement({kind:'hidden'});}
  }
  const target=selection?.target,key=selection?.serial;
  return <Context.Provider value={session}>
    {children}
    {placement.kind==='hidden'&&message&&<p role="alert">{message}</p>}
    <div ref={parking} hidden/>
    <dialog ref={dialog} className={`saved-statblock-dialog${expanded?' saved-statblock-dialog--expanded':''}`}
      aria-label="Saved statblock editor" onClose={()=>{if(placementRef.current.kind==='dialog')closePresentation();}} onKeyDown={event=>{if(event.key==='Escape')event.stopPropagation();}}/>
    {target&&createPortal(<div className="saved-statblock-frame" onKeyDown={event=>{if(event.key==='Escape')event.stopPropagation();}}>
      <header><strong>Statblock</strong><div>
        {placement.kind==='inline'?<button type="button" onClick={()=>{rememberInlineScroll();setPlacement({kind:'dialog'});}}>Open statblock popup</button>:<button type="button" aria-pressed={expanded} onClick={()=>setExpanded(value=>!value)}>{expanded?'Restore size':'Expand statblock'}</button>}
        <button type="button" autoFocus aria-label="Close statblock" onClick={closePresentation}>×</button>
      </div></header>
      <div className="saved-statblock-dialog__body">
        {message&&<p role="alert">{message}</p>}
        <TourEncounterProvider scope={presentation.encounter}><GenerationPlanProvider pin={presentation.generationPlan}><Editor key={key!} worldId={target.worldId} draftId={target.draftId} initialRevisionId={target.revisionId} autoLoad
          onSessionStateChange={state=>{if(current.current?.serial===key)observed.current=state;}}/></GenerationPlanProvider></TourEncounterProvider>
      </div>
    </div>,editorMount)}
  </Context.Provider>;
}

/** An outlet owns placement only. The World session retains every editing state. */
export function SavedStatblockInlineHost({worldId,onHost}:{worldId:string;onHost:(host:HTMLElement|null)=>void}) {
  const session=useSavedStatblockSession(),[node,setNode]=useState<HTMLDivElement|null>(null);
  useLayoutEffect(()=>{
    if(!node||!session?.registerInlineHost(node,worldId)){onHost(null);return;}
    onHost(node);return()=>{onHost(null);session.releaseInlineHost(node);};
  },[node,session,worldId,onHost]);
  return <div ref={setNode} className="saved-statblock-inline-slot"/>;
}
export function SavedStatblockButton({worldId,draftId,revisionId,label='Open statblock',inlineHost,onOpened}:{worldId:string;draftId:string;revisionId?:string;label?:string;inlineHost?:HTMLElement;onOpened?:()=>void}) {
  const encounter=useTourEncounter(),generationPlan=useGenerationPlan();
  const session=useSavedStatblockSession(),available=session?.worldId===worldId;
  return <button type="button" disabled={!available} title={available?undefined:'Saved statblock editing is unavailable in this host.'}
    onClick={()=>{if(session?.openStatblock({worldId,draftId,revisionId},{encounter,generationPlan},inlineHost))onOpened?.();}}>{label}</button>;
}
