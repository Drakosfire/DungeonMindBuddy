import {useEffect,useState} from "react";
import {listSessionEvidence,readSessionEvidence,type SessionEvidence,type SessionEvidenceRef} from "./sessionEvidenceApi";
export function SessionEvidencePicker({worldId,targetKey,onChange,disabled=false}:{worldId:string;targetKey:string;onChange:(refs:SessionEvidenceRef[])=>void;disabled?:boolean}){
 const [items,setItems]=useState<SessionEvidence[]>([]),[selected,setSelected]=useState<SessionEvidenceRef[]>([]),[error,setError]=useState<string|null>(null),[loading,setLoading]=useState(true);
 const key=`dmb.ingestion.session-evidence.${worldId}.${targetKey}`;
 useEffect(()=>{let cancelled=false;setLoading(true);setSelected([]);onChange([]);
  void (async()=>{try{const stored=JSON.parse(localStorage.getItem(key)??"[]");if(!Array.isArray(stored)||stored.length>3)throw new Error("Invalid saved session attachment selection");
   const refs:SessionEvidenceRef[]=stored.map(value=>{if(typeof value.run_id!=="string"||!Number.isInteger(value.review_revision)||value.review_revision<1||!/^[a-f0-9]{64}$/.test(value.sha256))throw new Error("Invalid saved session attachment");return value});
   if(cancelled)return;setSelected(refs);onChange(refs);
   const [recent,pinned]=await Promise.all([listSessionEvidence(worldId),Promise.all(refs.map(ref=>readSessionEvidence(worldId,ref.run_id,ref.review_revision)))]);
   for(let i=0;i<refs.length;i++)if(pinned[i].sha256!==refs[i].sha256)throw new Error("Saved session evidence changed; select it again deliberately");
   if(cancelled)return;setItems([...pinned,...recent.filter(item=>!pinned.some(old=>old.run_id===item.run_id&&old.review_revision===item.review_revision))]);setSelected(refs);onChange(refs);setError(null);
  }catch(cause){if(!cancelled)setError(cause instanceof Error?cause.message:"Session evidence unavailable")}finally{if(!cancelled)setLoading(false)}})();
  return()=>{cancelled=true};
 },[worldId,key]);
 function choose(item:SessionEvidence,checked:boolean){const rest=selected.filter(ref=>ref.run_id!==item.run_id);const next=checked?[...rest,{run_id:item.run_id,review_revision:item.review_revision,sha256:item.sha256}]:rest;try{localStorage.setItem(key,JSON.stringify(next))}catch{setError("Session attachment selection could not be saved in this browser")};setSelected(next);onChange(next)}
 return <details className="ingestion-session-supplements"><summary>Supplemental session evidence{selected.length?` (${selected.length} selected)`:""}</summary>
 <p>Optionally attach scene notes and closing reflections to the next extraction. Choose the matching played session explicitly. Your external recap stays the source text; these remain separately attributed context.</p>
 {selected.length?<button type="button" disabled={disabled} onClick={()=>{try{localStorage.removeItem(key)}catch{}setSelected([]);onChange([])}}>Clear selected session evidence</button>:null}
 {loading?<p role="status">Loading ended sessions…</p>:null}{error?<p role="alert">{error}</p>:null}
 {!loading&&!error&&items.length===0?<p>No ended sessions have saved evidence in this World yet.</p>:null}
 {items.map(item=>{const checked=selected.some(ref=>ref.run_id===item.run_id&&ref.review_revision===item.review_revision);return <div key={`${item.run_id}:${item.review_revision}`}><label><input type="checkbox" checked={checked} disabled={disabled||(!checked&&selected.length>=3&&!selected.some(ref=>ref.run_id===item.run_id))} onChange={event=>choose(item,event.target.checked)}/>{item.title??"Played session"} · ended {new Date(item.ended_at).toLocaleString()} · revision {item.review_revision} · {item.sources.length} sources</label> <a href={item.citation_url} target="_blank" rel="noreferrer">Read saved evidence</a></div>})}
 </details>
}
