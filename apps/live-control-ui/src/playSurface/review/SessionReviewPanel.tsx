import {useEffect,useMemo,useRef,useState} from "react";
import type {PlayRunContent} from "../playRunContentTypes";
import {SurfaceContextAction,useSurfaceContextContribution} from "../../surfaceInteraction/contextHost";
import {buildSurfaceInteractionIdentity} from "../../surfaceInteraction/surfaceIdentity";
import {readSessionReview,saveSessionReview,type SessionReview,type ReviewCommand} from "./sessionReviewApi";

export function SessionReviewPanel({runId,worldId,runRevision,content,blocked,sceneTitles}:{runId:string;worldId:string;runRevision:number;content:PlayRunContent;blocked:boolean;sceneTitles:Record<string,string>}){
 const [review,setReview]=useState<SessionReview|null>(null);
 const [earlierBrowserText,setEarlierBrowserText]=useState<string|null>(null);
 const [open,setOpen]=useState(new URLSearchParams(window.location.search).get("review")==="1");
 const [loaded,setLoaded]=useState(false),[text,setText]=useState(""),[error,setError]=useState<string|null>(null),[saving,setSaving]=useState(false),[changed,setChanged]=useState(false);
 const mounted=useRef(true),latestText=useRef(text);latestText.current=text;
 const pending=useRef<{id:string;body:ReviewCommand}|null>(null);
 const key=`dmb.session-reflections.${worldId}.${runId}`;
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false}},[]);
 useEffect(()=>{let cancelled=false;
  try{const prior=JSON.parse(localStorage.getItem(`dmb.session-review.${worldId}.${runId}`)??"null");if(prior&&typeof prior.text==="string")setEarlierBrowserText(prior.text)}catch{/* Earlier browser copies remain untouched. */}
  // Recover before any network dependency: an initial failed GET must not hide a browser draft.
  try{const local=JSON.parse(localStorage.getItem(key)??"null");if(local&&typeof local.text==="string")setText(local.text)}catch{setError("Browser draft could not be read. The saved review is still available.")}
  void readSessionReview(runId,worldId).then(value=>{
  if(cancelled)return;setReview(value.review);setChanged(value.source_changed);
  let draft=value.review?.final_thoughts??"";
  try{const local=JSON.parse(localStorage.getItem(key)??"null");if(local&&typeof local.text==="string"){
   draft=local.text;if(local.revision!==(value.review?.revision??0)&&draft!==value.review?.final_thoughts)setError("A saved review changed while this browser had a draft. Your text is retained. Compare the saved review before continuing.");
  }}catch{setError("Browser draft could not be read. The saved review is still available.");}
  setText(draft);setLoaded(true);if(value.review?.status==="ended")setOpen(true);
 }).catch(cause=>{if(!cancelled)setError(String(cause.message??cause))});return()=>{cancelled=true}},[runId,worldId,key]);
 const write=async(action:ReviewCommand["action"],retry=false)=>{
  if(saving||!loaded||action==="end"&&blocked)return;
  const attempt=retry?pending.current:{id:crypto.randomUUID(),body:{action,expected_revision:review?.revision??0,expected_run_revision:runRevision,expected_content_sha256:content.content_sha256,final_thoughts:latestText.current}};
  if(!attempt)return;pending.current=attempt;setSaving(true);setError(null);
  try{const accepted=await saveSessionReview(runId,worldId,attempt.id,attempt.body);if(!mounted.current)return;
   setReview(accepted);pending.current=null;if(action==="end")setChanged(false);
   if(action==="end")setText(accepted.final_thoughts);
   if(action==="reopen")setOpen(false);
   try{if(action!=="save"||latestText.current===attempt.body.final_thoughts)localStorage.removeItem(key);
    else localStorage.setItem(key,JSON.stringify({revision:accepted.revision,text:latestText.current}));}catch{setError("Saved on server; browser draft cleanup failed.")}
  }catch(cause){if(mounted.current)setError(cause instanceof Error?cause.message:"Review could not be saved. Your draft is retained.")}
  finally{if(mounted.current)setSaving(false)}
 };
 useEffect(()=>{
  if(!loaded||!review||review.status!=="ended"||text===review.final_thoughts||error||saving)return;
  const timer=window.setTimeout(()=>{void write("save")},700);return()=>window.clearTimeout(timer);
 },[text,loaded,review,error,saving]);
 const dirty=Boolean(review&&text!==review.final_thoughts);
 useEffect(()=>{if(!dirty)return;const guard=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue=""};window.addEventListener("beforeunload",guard);return()=>window.removeEventListener("beforeunload",guard)},[dirty]);
 const identity=useMemo(()=>buildSurfaceInteractionIdentity({surfaceId:"play",instanceParts:["session-review",worldId,runId]}),[runId,worldId]);
 const nav=useMemo(()=><SurfaceContextAction onClick={()=>setOpen(value=>!value)}>{review?.status==="ended"?"Session reflections":"End session"}</SurfaceContextAction>,[review?.status]);
 useSurfaceContextContribution({id:"play-session-review",order:25,surfaceIdentity:identity,content:nav});
 if(!open)return null;
 return <section className="play-session-review" aria-label="Session review">
  <header><h2>{review?.status==="ended"?"Session reflections":"Finish at the table"}</h2><button onClick={()=>setOpen(false)}>Close review</button></header>
  {!loaded&&!error?<p role="status">Loading saved session review…</p>:null}
  {error?<div role="alert"><p>{error}</p>{pending.current?<button disabled={saving} onClick={()=>void write(pending.current!.body.action,true)}>Retry same save</button>:null}
   <details><summary>Compare saved reflections</summary><pre>{review?.final_thoughts??"No saved thoughts yet."}</pre></details>
   <button disabled={saving} onClick={()=>{void readSessionReview(runId,worldId).then(value=>{if(!mounted.current)return;setReview(value.review);setChanged(value.source_changed);pending.current=null;setLoaded(true);setError("Latest saved review loaded. Your browser text is retained above. Choose whether to keep it or use the saved reflections.")}).catch(cause=>setError(String(cause.message??cause)))}}>Reload saved review, keep my text</button>
   {review&&!pending.current?<><button onClick={()=>{try{localStorage.setItem(key,JSON.stringify({revision:review.revision,text}))}catch{}setError(null)}}>Keep my draft</button><button onClick={()=>{setText(review.final_thoughts);try{localStorage.removeItem(key)}catch{}setError(null)}}>Use saved reflections</button></>:null}</div>:null}
  {loaded&&review?.status!=="ended"?<><p>End play and keep a checkpoint of the saved session copy, choices and scene notes. You can reopen play later. The Plan stays intact.</p>
   <p>Anything you want to remember? What surprised you, what changed, or what should you pick up next time? These thoughts are saved with the session. Recaps are separate external documents.</p>
   <label>Final thoughts and recollections (optional)<textarea rows={7} value={text} onChange={event=>{setText(event.target.value);try{localStorage.setItem(key,JSON.stringify({revision:review?.revision??0,text:event.target.value}))}catch{setError("Browser recovery copy could not be saved.")}}}/></label>
   {blocked?<p role="status">Finish saving session edits and scene notes before ending play.</p>:null}
   <button disabled={blocked||saving} onClick={()=>void write("end")}>Finish session</button></>:null}
  {review?.status==="ended"?<>
   <p>Play ended. Add final thoughts or recollections while they are fresh. These are session notes; your recap remains an external document.</p>
   {changed || review.checkpoint.run_revision!==runRevision || review.checkpoint.content.content_sha256!==content.content_sha256 ?<p role="status">The session has changed since this checkpoint. These original notes are retained; reopen and end play again to capture a new checkpoint.</p>:null}
   <label>Final thoughts and recollections<textarea rows={14} value={text} onChange={event=>{const next=event.target.value;setText(next);try{localStorage.setItem(key,JSON.stringify({revision:review.revision,text:next}))}catch{setError("Browser recovery copy could not be saved. Keep this page open until the server saves.")}}}/></label>
   <p role="status">{saving?"Saving thoughts…":dirty?"Unsaved thoughts":"Thoughts saved"}</p>
   <div className="play-review-actions"><button disabled={dirty||saving||Boolean(error)} onClick={()=>void write("reopen")}>Reopen play</button></div>
   <p className="play-muted">Original scene notes and the saved session checkpoint are retained separately. Nothing here publishes to the graph or creates a recap.</p>
   {earlierBrowserText?<details><summary>Earlier browser text (retained)</summary><pre>{earlierBrowserText}</pre></details>:null}
   {review.draft_markdown?<details><summary>Earlier review text (retained)</summary><pre>{review.draft_markdown}</pre></details>:null}
   <details><summary>Original saved notes ({Object.values(review.checkpoint.progress.notes_by_element_id).filter(note=>note.trim()).length})</summary>
    {Object.entries(review.checkpoint.progress.notes_by_element_id).map(([id,note])=><article key={id}><h3>{sceneTitles[id]??id}</h3><p style={{whiteSpace:"pre-wrap"}}>{note}</p></article>)}
   </details>
  </>:null}
 </section>;
}
