import {useEffect,useState} from "react";
import {readSessionEvidence,type SessionEvidence} from "./sessionEvidenceApi";
import {verifiedSessionEntryTargets} from "../../shared/sessionEvidenceCitation";
function currentFragment(){try{return decodeURIComponent(window.location.hash.slice(1))}catch{return "invalid-fragment"}}
export function SessionEvidenceViewer({worldId,runId,revision}:{worldId:string;runId:string;revision:number}){
 const [value,setValue]=useState<SessionEvidence|null>(null),[error,setError]=useState<string|null>(null);
 const [targets,setTargets]=useState<string[]>([]),[fragment,setFragment]=useState(currentFragment);
 useEffect(()=>{const update=()=>setFragment(currentFragment());window.addEventListener('hashchange',update);return()=>window.removeEventListener('hashchange',update)},[]);
 useEffect(()=>{let cancelled=false;setValue(null);setTargets([]);setError(null);
  void readSessionEvidence(worldId,runId,revision).then(async value=>({value,targets:await verifiedSessionEntryTargets(value)}))
   .then(result=>{if(!cancelled){setValue(result.value);setTargets(result.targets)}})
   .catch(cause=>{if(!cancelled)setError(cause.message)});return()=>{cancelled=true}
 },[worldId,runId,revision]);
 const fragments=targets.map(target=>target.split('#')[1]!);
 const mismatch=!!value && !!fragment && !fragments.includes(fragment);
 useEffect(()=>{if(value && fragment && fragments.includes(fragment))document.getElementById(fragment)?.scrollIntoView?.({block:'center'})},[value,fragment,targets]);
 return <main className="play-surface"><h1>Saved session evidence</h1><p>This is the exact saved revision cited by Buddy. Scene notes and closing reflections are GM-authored evidence, separate from an external recap and published Graph facts.</p>
 {error?<p role="alert">{error}</p>:!value?<p role="status">Loading cited evidence…</p>:mismatch?
 <p role="alert">This entry reference does not match the saved session evidence. No neighboring entry has been substituted.</p>:<>
 <p><strong>{value.title??"Played session"}</strong> · ended {new Date(value.ended_at).toLocaleString()} · review revision {revision}</p>
 {value.sources.map((source,index)=><section id={fragments[index]} key={index} className="play-session-review" aria-label={source.kind==='closing_reflections'?'Closing reflections':'Scene notes'}>
 <h2>{source.kind==="closing_reflections"?"Closing reflections":`Scene notes · ${source.element_id}`}</h2><p style={{whiteSpace:"pre-wrap"}}>{source.text}</p></section>)}
 <a href={`/play?world=${encodeURIComponent(worldId)}&run=${encodeURIComponent(runId)}&review=1`}>Open current session reflections</a></>}
 </main>
}
