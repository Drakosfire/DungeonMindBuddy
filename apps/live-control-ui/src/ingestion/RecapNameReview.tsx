import {useState} from "react";
import type {RecapNameReview as Review} from "../api/recapIngestApi";
import type {RecapIngestRequest} from "../api/types";

export function RecapNameReview({review,onProceed,onCancel}:{review: Review;onProceed:(receipt:NonNullable<RecapIngestRequest["name_review"]>)=>void;onCancel:()=>void}) {
  const [decisions,setDecisions]=useState<Record<string,string>>({});
  const ready=review.suggestions.every(s=>decisions[s.id]!==undefined);
  return <section aria-label="Review character names" className="module-panel">
    <h3>Check names before extraction</h3>
    <p>{review.exact_mention_count} exact known-name mentions found. Review these possible typos. No model has been called.</p>
    <p>Approved corrections apply to the extraction copy. Your original text and decisions are retained.</p>
    {review.suggestions.map((s,i)=><label key={s.id} style={{display:"block",marginBottom:"1rem"}}>
      Name {i+1}: <strong>{s.surface}</strong>
      <select aria-label={`Correction for ${s.surface} (${i+1})`} value={decisions[s.id]??""} onChange={e=>setDecisions(d=>({...d,[s.id]:e.target.value}))}>
        <option value="" disabled>Choose a correction or keep original</option>
        <option value="keep">Keep original: {s.surface}</option>
        {s.options.map(option=><option key={option} value={`apply:${option}`}>Change to {option}</option>)}
      </select>
    </label>)}
    <button type="button" onClick={onCancel}>Back to editing</button>{" "}
    <button type="button" className="primary" disabled={!ready} onClick={()=>onProceed({review_id:review.review_id,decisions:review.suggestions.map(s=>({id:s.id,replacement:decisions[s.id]==="keep"?null:decisions[s.id].slice(6)}))})}>Apply decisions and extract</button>
  </section>;
}
