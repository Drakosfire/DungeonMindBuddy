import {useEffect,useRef,useState} from 'react';
import {ContextualAgentMenu} from '../contextualActions/ContextualAgentMenu';
import {getNativeGraphAccessGeneration,NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT} from '../api/liveApi';
import {imageEditContext,regenerateImage,type ImageContext,type ImageCandidate,type ImageEditMode} from './imageContextApi';
import {SavedMediaImage} from './SavedMediaImage';
import {useTourImage} from '../guidedTour/ImageObservations';

export function ImageContextEdit({assetId,editable,captureApply}:{assetId:string;editable:boolean;captureApply:()=>((assetId:string)=>void)}) {
 const [open,setOpen]=useState(false);const [mode,setMode]=useState<ImageEditMode>('image_to_image');
 const [instructions,setInstructions]=useState('');const [context,setContext]=useState<ImageContext|null>(null);
 const [busy,setBusy]=useState(false);const [applying,setApplying]=useState(false);const [error,setError]=useState('');const [storageWarning,setStorageWarning]=useState('');
 const [candidate,setCandidate]=useState<ImageCandidate|null>(null);
 const pending=useRef<AbortController|null>(null);const active=useRef(true);const apply=useRef<((id:string)=>void)|null>(null);
 const candidateGeneration=useRef<number|null>(null);const tour=useTourImage();
 const key=`dmb:image-context-instructions:v1:${assetId}`;
 useEffect(()=>{
  active.current=true;
  const reset=()=>{pending.current?.abort();pending.current=null;setBusy(false);setApplying(false);setOpen(false);setContext(null);setCandidate(null);setInstructions('');setMode('image_to_image');setError('');apply.current=null;};
  reset();window.addEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT,reset);
  return()=>{active.current=false;pending.current?.abort();window.removeEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT,reset);};
 },[assetId]);
 useEffect(()=>{if(!editable){setOpen(false);pending.current?.abort();}},[editable]);
 useEffect(()=>{
  if(!open)return;
  const abort=new AbortController();const generation=getNativeGraphAccessGeneration();
  setContext(null);
  imageEditContext(assetId,generation,abort.signal).then(value=>{
   if(abort.signal.aborted||!active.current||generation!==getNativeGraphAccessGeneration())return;
   setContext(value);
   try {const raw=localStorage.getItem(key);if(raw!==null){const saved=JSON.parse(raw);if(saved.schema!=='dmb_image_context_draft_v1'||!['image_to_image','new'].includes(saved.mode)||typeof saved.instructions!=='string')throw new Error('Invalid draft');setInstructions(saved.instructions);setMode(saved.mode);}}
   catch {setStorageWarning('These instructions are kept while this page is open; browser draft storage is unavailable.');}
  }).catch(reason=>{if(!abort.signal.aborted)setError(reason instanceof Error?reason.message:'Image unavailable.');});
  return()=>abort.abort();
 },[open,assetId,key]);
 function saveDraft(nextMode:ImageEditMode,text:string){
  if(context)try{localStorage.setItem(key,JSON.stringify({schema:'dmb_image_context_draft_v1',mode:nextMode,instructions:text}));setStorageWarning('');}catch{setStorageWarning('Keep this page open: these instructions could not be stored for reload.');}
 }
 function changeInstructions(text:string){setInstructions(text);saveDraft(mode,text);}
 function changeMode(next:string){const value=next as ImageEditMode;setMode(value);saveDraft(value,instructions);}
 async function generate(){
  if(!context||pending.current||!editable)return;
  const generation=getNativeGraphAccessGeneration();const abort=new AbortController();
  let captured:(id:string)=>void;
  try{captured=captureApply();}catch(reason){setError(reason instanceof Error?reason.message:'The page changed.');return;}
  const scope=tour?.captureScope()??null;
  pending.current=abort;setBusy(true);setError('');setCandidate(null);apply.current=null;
  try{
   const result=await regenerateImage(context,mode,instructions,generation,abort.signal);
   if(!active.current||abort.signal.aborted||generation!==getNativeGraphAccessGeneration())return;
   apply.current=captured;candidateGeneration.current=generation;setCandidate(result);
   tour?.generated([result.asset_id],result.model,scope);
  }catch(reason){if(active.current&&!abort.signal.aborted)setError(reason instanceof Error?reason.message:'Generation could not be confirmed. Check your library before trying again.');}
  finally{if(pending.current===abort){pending.current=null;if(active.current)setBusy(false);}}
 }
 async function useCandidate(){
  const generation=candidateGeneration.current;
  if(!candidate||generation!==getNativeGraphAccessGeneration()||!editable||pending.current)return;
  const abort=new AbortController();pending.current=abort;setApplying(true);setError('');
  try{
   await imageEditContext(candidate.asset_id,generation,abort.signal);
   if(!active.current||abort.signal.aborted||generation!==getNativeGraphAccessGeneration())return;
   if(!apply.current)throw new Error('The page changed. The image remains in your library.');
   apply.current(candidate.asset_id);tour?.placed(candidate.asset_id);setOpen(false);
  }catch(reason){if(active.current&&!abort.signal.aborted)setError(reason instanceof Error?reason.message:'The page changed. The image remains in your library.');}
  finally{if(pending.current===abort){pending.current=null;if(active.current)setApplying(false);}}
 }
 if(!editable)return null;
 return <ContextualAgentMenu label="image" open={open} onOpen={()=>setOpen(true)} onClose={()=>setOpen(false)} mode={mode}
  modes={[{value:'image_to_image',label:'Image to image'},{value:'new',label:'New image'}]} onMode={changeMode}
  instructions={instructions} onInstructions={changeInstructions} onSubmit={()=>void generate()} busy={busy} canSubmit={!!context&&!applying} submitLabel="Generate" busyLabel="Generating…">
  {!context&&!error&&<p role="status">Checking image access…</p>}
  <p>{mode==='image_to_image'?'Uses this image and your instructions · FLUX 2 Pro.':'Uses your instructions to create a fresh image · GPT Image 2.5 Flare.'} Generation uses the configured fal account.</p>
  {storageWarning&&<p role="status">{storageWarning}</p>}
  {error&&<p role="alert">{error}</p>}
  {candidate&&<><SavedMediaImage assetId={candidate.asset_id} alt="Generated alternative"/><p>Retained privately. Your current image is unchanged.</p><button type="button" disabled={applying} onClick={()=>void useCandidate()}>{applying?'Checking image…':'Use this version'}</button></>}
 </ContextualAgentMenu>;
}
