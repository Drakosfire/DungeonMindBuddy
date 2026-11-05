import {useEffect,useState} from "react";
import {getIngestUsage,type ExtractionUsage,type UsageMetrics} from "../api/ingestUsageApi";
import "./IngestionUsage.css";
const count=(v:number|null)=>v===null?"Not reported":v.toLocaleString();
const usd=(v:number)=>v>0&&v<0.000001?"<$0.000001 USD":`$${v.toFixed(6)} USD`;
function price(m:UsageMetrics):string {
  if(m.costStatus==="reported" && m.costUsd!==null)return `${usd(m.costUsd)} · provider reported`;
  if(m.costStatus==="partial" && m.knownCostUsd!==null)return `${usd(m.knownCostUsd)} known · partial`;
  if(m.costStatus==="not_dispatched")return "No provider calls";
  return "Price unavailable";
}
const names:Record<string,string>={actor_pass:"Actors",location_pass:"Locations",collective_pass:"Groups",object_pass:"Objects",thread_pass:"Threads",beat_pass:"Story beats",edge_pass:"Relationships"};
export function IngestionUsage({world,runId,revision}:{world:string;runId:string;revision:number}) {
  const key=JSON.stringify([world,runId,revision]);
  const [state,setState]=useState<{key:string;data?:ExtractionUsage;error?:boolean}>();
  const [refresh,setRefresh]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();let active=true;
    setState({key});
    void getIngestUsage(world,runId,revision,controller.signal).then(data=>{
      if(active)setState({key,data});
    }).catch(()=>{if(active)setState({key,error:true});});
    return ()=>{active=false;controller.abort();};
  },[key,world,runId,revision,refresh]);
  const current=state?.key===key?state:undefined;
  return <section className="ingestion-usage" aria-label="Extraction tokens and price">
    <h3>Tokens &amp; price</h3>
    {current?.error?<><p role="status">Usage could not be loaded.</p><button onClick={()=>setRefresh(v=>v+1)}>Retry usage</button></>:current?.data?<>
      <dl><dt>Input tokens</dt><dd>{count(current.data.totals.inputTokens)}</dd>
      <dt>Output tokens</dt><dd>{count(current.data.totals.outputTokens)}</dd>
      <dt>Provider attempts</dt><dd>{count(current.data.totals.providerAttempts)}</dd>
      <dt>Price</dt><dd>{price(current.data.totals)}</dd></dl>
      {current.data.totals.costStatus==="partial"?<p>Other attempt prices are unavailable. The known amount is not the full run price.</p>:null}
      <p>Cached input: {count(current.data.totals.cachedInputTokens)}. Reasoning output: {count(current.data.totals.reasoningTokens)}. These are included in input and output, not added again.</p>
      {current.data.totals.inputTokens===null && current.data.totals.knownInputTokens!==null?<p>Known input subtotal: {count(current.data.totals.knownInputTokens)}; some usage is unavailable.</p>:null}
      {current.data.totals.outputTokens===null && current.data.totals.knownOutputTokens!==null?<p>Known output subtotal: {count(current.data.totals.knownOutputTokens)}; some usage is unavailable.</p>:null}
      <details><summary>Per-pass usage</summary><div className="ingestion-usage__table"><table><thead><tr><th>Pass</th><th>Input</th><th>Output</th><th>Price</th></tr></thead><tbody>
      {current.data.passes.map((p,i)=><tr key={`${i}:${p.passName}`}><th scope="row">{names[p.passName]??p.passName.replaceAll("_"," ")}</th><td>{count(p.inputTokens)}</td><td>{count(p.outputTokens)}</td><td>{price(p)}</td></tr>)}
      </tbody></table></div></details>
      {current.data.totals.costStatus==="unavailable"?<p>No dollar price was retained for this extraction. Token counts are not a bill.</p>:null}
    </>:<p role="status">Loading usage…</p>}
  </section>;
}
