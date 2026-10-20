import {useEffect,useRef,useState} from "react";
import {listSessionEvidence,readSessionEvidence,type SessionEvidenceIndexItem,type SessionEvidenceRef} from "./sessionEvidenceApi";
export function SessionEvidencePicker({worldId,targetKey,onChange,disabled=false}:{worldId:string;targetKey:string;onChange:(refs:SessionEvidenceRef[])=>void;disabled?:boolean}){
 const [items,setItems]=useState<SessionEvidenceIndexItem[]>([]),[selected,setSelected]=useState<SessionEvidenceRef[]>([]),[error,setError]=useState<string|null>(null),[loading,setLoading]=useState(true),[selecting,setSelecting]=useState<string|null>(null);
 const selectionEpoch=useRef(0);
 const hydrationEpoch=useRef(0);
 const key=`dmb.ingestion.session-evidence.${worldId}.${targetKey}`;
 useEffect(()=>{let cancelled=false;const requestEpoch=++hydrationEpoch.current;setLoading(true);setSelected([]);onChange([]);
  void (async()=>{try{const stored=JSON.parse(localStorage.getItem(key)??"[]");if(!Array.isArray(stored)||stored.length>3)throw new Error("Invalid saved session attachment selection");
   const refs:SessionEvidenceRef[]=stored.map(value=>{if(typeof value.run_id!=="string"||!Number.isInteger(value.review_revision)||value.review_revision<1||!/^[a-f0-9]{64}$/.test(value.sha256))throw new Error("Invalid saved session attachment");return value});
   if(cancelled)return;setSelected(refs);onChange(refs);
   const recentResult=await listSessionEvidence(worldId).then(recent=>({recent} as const),recentError=>({recentError} as const));
   if(cancelled)return;
   if("recentError" in recentResult){setError(recentResult.recentError instanceof Error?recentResult.recentError.message:"Session evidence unavailable");return}
   const recent=recentResult.recent;
   if(hydrationEpoch.current!==requestEpoch){setItems(recent);return}
   const pinnedIndex:SessionEvidenceIndexItem[]=refs.map(ref=>recent.find(item=>item.run_id===ref.run_id&&item.review_revision===ref.review_revision)??{
    run_id:ref.run_id,review_revision:ref.review_revision,title:`Saved session · ${ref.run_id.slice(0,8)}`,ended_at:"",source_count:0,
    citation_url:`/play?${new URLSearchParams({world:worldId,run:ref.run_id,evidence_revision:String(ref.review_revision)})}`,
   });
   setItems([...pinnedIndex,...recent.filter(item=>!refs.some(ref=>ref.run_id===item.run_id&&ref.review_revision===item.review_revision))]);setSelected(refs);onChange(refs);setError(null);
  }catch(cause){if(!cancelled&&hydrationEpoch.current===requestEpoch)setError(cause instanceof Error?cause.message:"Session evidence unavailable")}finally{if(!cancelled&&hydrationEpoch.current===requestEpoch)setLoading(false)}})();
  return()=>{cancelled=true;hydrationEpoch.current+=1;selectionEpoch.current+=1};
 },[worldId,key]);
 async function choose(item:SessionEvidenceIndexItem,checked:boolean){const rest=selected.filter(ref=>ref.run_id!==item.run_id);if(!checked){persist(rest);return}const identity=`${item.run_id}:${item.review_revision}`;const requestEpoch=++selectionEpoch.current;setSelecting(identity);setError(null);try{const pinned=await readSessionEvidence(worldId,item.run_id,item.review_revision);if(selectionEpoch.current!==requestEpoch)return;if(pinned.run_id!==item.run_id||pinned.review_revision!==item.review_revision)throw new Error("Selected session evidence changed; select it again");persist([...rest,{run_id:pinned.run_id,review_revision:pinned.review_revision,sha256:pinned.sha256}])}catch(cause){if(selectionEpoch.current===requestEpoch)setError(cause instanceof Error?cause.message:"Session evidence unavailable")}finally{if(selectionEpoch.current===requestEpoch)setSelecting(null)}}
 function persist(next:SessionEvidenceRef[]){try{localStorage.setItem(key,JSON.stringify(next))}catch{setError("Session attachment selection could not be saved in this browser");return}setSelected(next);onChange(next)}
 function clear(){selectionEpoch.current+=1;hydrationEpoch.current+=1;setSelecting(null);setLoading(false);try{localStorage.removeItem(key)}catch{}setSelected([]);onChange([])}
 return <details className="ingestion-session-supplements"><summary>Supplemental session evidence{selected.length?` (${selected.length} selected)`:""}</summary>
 <p>Optionally attach scene notes and closing reflections to the next extraction. Choose the matching played session explicitly. Your external recap stays the source text; these remain separately attributed context.</p>
 {selected.length?<button type="button" disabled={disabled} onClick={clear}>Clear selected session evidence</button>:null}
 {loading?<p role="status">Loading ended sessions…</p>:null}{error?<p role="alert">{error}</p>:null}
 {!loading&&!error&&items.length===0?<p>No ended sessions have saved evidence in this World yet.</p>:null}
 {items.map(item=>{const checked=selected.some(ref=>ref.run_id===item.run_id&&ref.review_revision===item.review_revision);const identity=`${item.run_id}:${item.review_revision}`;return <div key={identity}><label><input type="checkbox" checked={checked} disabled={disabled||loading||selecting!==null||(!checked&&selected.length>=3&&!selected.some(ref=>ref.run_id===item.run_id))} onChange={event=>void choose(item,event.target.checked)}/>{item.title}{item.ended_at?` · ended ${new Date(item.ended_at).toLocaleString()} · revision ${item.review_revision} · ${item.source_count} sources`:` · previously selected · revision ${item.review_revision}`}{selecting===identity?" · Loading source…":""}</label> <a href={item.citation_url} target="_blank" rel="noreferrer">Read saved evidence</a></div>})}
 </details>
}
