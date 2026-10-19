import {useEffect,useState} from "react";
import {readSessionEvidence,type SessionEvidence} from "./sessionEvidenceApi";
export function SessionEvidenceViewer({worldId,runId,revision}:{worldId:string;runId:string;revision:number}){
 const [value,setValue]=useState<SessionEvidence|null>(null),[error,setError]=useState<string|null>(null);
 useEffect(()=>{let cancelled=false;setValue(null);setError(null);void readSessionEvidence(worldId,runId,revision).then(value=>{if(!cancelled)setValue(value)}).catch(cause=>{if(!cancelled)setError(cause.message)});return()=>{cancelled=true}},[worldId,runId,revision]);
 return <main className="play-surface"><h1>Saved session evidence</h1><p>This is the exact saved revision cited by Buddy. Scene notes and closing reflections are GM-authored evidence, separate from an external recap and published Graph facts.</p>
 {error?<p role="alert">{error}</p>:!value?<p role="status">Loading cited evidence…</p>:<><p><strong>{value.title??"Played session"}</strong> · ended {new Date(value.ended_at).toLocaleString()} · review revision {revision}</p>
 {value.sources.map((source,index)=><section key={index} className="play-session-review"><h2>{source.kind==="closing_reflections"?"Closing reflections":`Scene notes · ${source.element_id}`}</h2><p style={{whiteSpace:"pre-wrap"}}>{source.text}</p></section>)}
 <a href={`/play?world=${encodeURIComponent(worldId)}&run=${encodeURIComponent(runId)}&review=1`}>Open current session reflections</a></>}
 </main>
}
