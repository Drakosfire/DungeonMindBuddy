import {useEffect,useMemo,useRef,useState} from "react";
import type {PlayRunContent} from "../playRunContentTypes";
import {SurfaceContextAction,useSurfaceContextContribution} from "../../surfaceInteraction/contextHost";
import {buildSurfaceInteractionIdentity} from "../../surfaceInteraction/surfaceIdentity";
import {exportSessionReview,readSessionReview,saveSessionReview,type SessionReview,type ReviewCommand} from "./sessionReviewApi";

export function SessionReviewPanel({runId,worldId,runRevision,content,blocked,sceneTitles}:{runId:string;worldId:string;runRevision:number;content:PlayRunContent;blocked:boolean;sceneTitles:Record<string,string>}){
 const [review,setReview]=useState<SessionReview|null>(null);
 const [open,setOpen]=useState(new URLSearchParams(window.location.search).get("review")==="1");
 const [loaded,setLoaded]=useState(false),[text,setText]=useState(""),[error,setError]=useState<string|null>(null),[saving,setSaving]=useState(false),[changed,setChanged]=useState(false);
 const mounted=useRef(true),latestText=useRef(text);latestText.current=text;
 const pending=useRef<{id:string;body:ReviewCommand}|null>(null);
 const key=`dmb.session-review.${worldId}.${runId}`;
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false}},[]);
 useEffect(()=>{let cancelled=false;
  // Recover before any network dependency: an initial failed GET must not hide a browser draft.
  try{const local=JSON.parse(localStorage.getItem(key)??"null");if(local&&typeof local.text==="string")setText(local.text)}catch{setError("Browser draft could not be read. The saved review is still available.")}
  void readSessionReview(runId,worldId).then(value=>{
  if(cancelled)return;setReview(value.review);setChanged(value.source_changed);
  let draft=value.review?.draft_markdown??"";
  try{const local=JSON.parse(localStorage.getItem(key)??"null");if(local&&typeof local.text==="string"){
   draft=local.text;if(local.revision!==(value.review?.revision??0)&&draft!==value.review?.draft_markdown)setError("A saved review changed while this browser had a draft. Your text is retained. Compare the saved review before continuing.");
  }}catch{setError("Browser draft could not be read. The saved review is still available.");}
  setText(draft);setLoaded(true);if(value.review?.status==="ended")setOpen(true);
 }).catch(cause=>{if(!cancelled)setError(String(cause.message??cause))});return()=>{cancelled=true}},[runId,worldId,key]);
 const write=async(action:ReviewCommand["action"],retry=false)=>{
  if(saving||!loaded||action==="end"&&blocked)return;
  const attempt=retry?pending.current:{id:crypto.randomUUID(),body:{action,expected_revision:review?.revision??0,expected_run_revision:runRevision,expected_content_sha256:content.content_sha256,draft_markdown:latestText.current}};
  if(!attempt)return;pending.current=attempt;setSaving(true);setError(null);
  try{const accepted=await saveSessionReview(runId,worldId,attempt.id,attempt.body);if(!mounted.current)return;
   setReview(accepted);pending.current=null;if(action==="end")setChanged(false);
   if(action==="end")setText(accepted.draft_markdown);
   if(action==="reopen")setOpen(false);
   try{if(action!=="save"||latestText.current===attempt.body.draft_markdown)localStorage.removeItem(key);
    else localStorage.setItem(key,JSON.stringify({revision:accepted.revision,text:latestText.current}));}catch{setError("Saved on server; browser draft cleanup failed.")}
  }catch(cause){if(mounted.current)setError(cause instanceof Error?cause.message:"Review could not be saved. Your draft is retained.")}
  finally{if(mounted.current)setSaving(false)}
 };
 useEffect(()=>{
  if(!loaded||!review||review.status!=="ended"||text===review.draft_markdown||error||saving)return;
  const timer=window.setTimeout(()=>{void write("save")},700);return()=>window.clearTimeout(timer);
 },[text,loaded,review,error,saving]);
 const dirty=Boolean(review&&text!==review.draft_markdown);
 useEffect(()=>{if(!dirty)return;const guard=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue=""};window.addEventListener("beforeunload",guard);return()=>window.removeEventListener("beforeunload",guard)},[dirty]);
 const identity=useMemo(()=>buildSurfaceInteractionIdentity({surfaceId:"play",instanceParts:["session-review",worldId,runId]}),[runId,worldId]);
 const nav=useMemo(()=><SurfaceContextAction onClick={()=>setOpen(value=>!value)}>{review?.status==="ended"?"Review session":"End session"}</SurfaceContextAction>,[review?.status]);
 useSurfaceContextContribution({id:"play-session-review",order:25,surfaceIdentity:identity,content:nav});
 if(!open)return null;
 return <section className="play-session-review" aria-label="Session review">
  <header><h2>{review?.status==="ended"?"Review your session":"Finish at the table"}</h2><button onClick={()=>setOpen(false)}>Close review</button></header>
  {!loaded&&!error?<p role="status">Loading saved session review…</p>:null}
  {error?<div role="alert"><p>{error}</p>{pending.current?<button disabled={saving} onClick={()=>void write(pending.current!.body.action,true)}>Retry same save</button>:null}
   <details><summary>Compare saved recap</summary><pre>{review?.draft_markdown??"No saved recap draft yet."}</pre></details>
   <button disabled={saving} onClick={()=>{void readSessionReview(runId,worldId).then(value=>{if(!mounted.current)return;setReview(value.review);setChanged(value.source_changed);pending.current=null;setLoaded(true);setError("Latest saved review loaded. Your browser text is retained above. Choose whether to keep it or use the saved recap.")}).catch(cause=>setError(String(cause.message??cause)))}}>Reload saved review, keep my text</button>
   {review&&!pending.current?<><button onClick={()=>{try{localStorage.setItem(key,JSON.stringify({revision:review.revision,text}))}catch{}setError(null)}}>Keep my draft</button><button onClick={()=>{setText(review.draft_markdown);try{localStorage.removeItem(key)}catch{}setError(null)}}>Use saved recap</button></>:null}</div>:null}
  {loaded&&review?.status!=="ended"?<><p>End play and keep a checkpoint of the saved session copy, choices and scene notes. You can reopen play later. The Plan stays intact.</p>
   <p>The recap starts with your saved notes. Prepared scenes do not establish what happened.</p>
   {blocked?<p role="status">Finish saving session edits and scene notes before ending play.</p>:null}
   <button disabled={blocked||saving} onClick={()=>void write("end")}>End session and review notes</button></>:null}
  {review?.status==="ended"?<>
   <p>Play ended. Review what actually happened, add what you remember, and mark uncertainties. Nothing here has been published to the graph.</p>
   {changed || review.checkpoint.run_revision!==runRevision || review.checkpoint.content.content_sha256!==content.content_sha256 ?<p role="status">The session has changed since this checkpoint. These original notes are retained; reopen and end play again to capture a new checkpoint.</p>:null}
   <label>Recap draft<textarea rows={14} value={text} onChange={event=>{const next=event.target.value;setText(next);try{localStorage.setItem(key,JSON.stringify({revision:review.revision,text:next}))}catch{setError("Browser recovery copy could not be saved. Keep this page open until the server saves.")}}}/></label>
   <p role="status">{saving?"Saving recap…":dirty?"Unsaved recap draft":"Recap saved"}</p>
   <div className="play-review-actions"><button disabled={dirty||saving||Boolean(error)} onClick={()=>{const blob=new Blob([exportSessionReview(review)],{type:"text/markdown;charset=utf-8"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=`session-${runId}-recap.md`;a.click();URL.revokeObjectURL(url)}}>Download recap with source notes</button>
   <button disabled={dirty||saving||Boolean(error)} onClick={()=>void write("reopen")}>Reopen play</button></div>
   <p className="play-muted">Review the recap before using it as an ingestion source. Download includes original notes and checkpoint references; it does not publish facts.</p>
   <details><summary>Original saved notes ({Object.values(review.checkpoint.progress.notes_by_element_id).filter(note=>note.trim()).length})</summary>
    {Object.entries(review.checkpoint.progress.notes_by_element_id).map(([id,note])=><article key={id}><h3>{sceneTitles[id]??id}</h3><p style={{whiteSpace:"pre-wrap"}}>{note}</p></article>)}
   </details>
  </>:null}
 </section>;
}
