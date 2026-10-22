import type {SurfaceEvidenceCompletionV1} from "../../api/types";
import {WorldPlanAgentAnswer} from "./WorldPlanAgentAnswer";

type Composition = {text:string;ranges:{domain:string;base_segment_index:number|null;text_start:number;text_end:number}[]};
/** Same authority presentation in Plan, Play and an approved Rules composition. */
export function SurfaceEvidenceAnswer({completion,composition}:{completion:SurfaceEvidenceCompletionV1;composition?:Composition}) {
  const renderSegment=(s:SurfaceEvidenceCompletionV1['answer_segments'][number],i:number) =>
    s.kind === 'authored_quote' ? <figure key={i}><figcaption>{s.source_name} · quoted excerpt</figcaption>
      <blockquote><WorldPlanAgentAnswer answer={s.text}/></blockquote></figure>
    : <section key={i} aria-label={s.kind === 'graph_claim' ? 'World Graph fact' : s.kind === 'source_passage_claim' ? 'Source-supported statement' : s.kind === 'proposal' ? 'Proposed idea' : 'Evidence limitation'}>
      {s.kind === 'proposal' ? <small>Proposed idea</small> : null}<WorldPlanAgentAnswer answer={s.text}/>
    </section>;
  const chars=composition ? Array.from(composition.text) : [];
  return <div aria-label="Evidence-grounded answer">{composition ? composition.ranges.map((r,i)=>
    r.domain === 'base' && r.base_segment_index !== null
      ? renderSegment(completion.answer_segments[r.base_segment_index]!,i)
      : <section key={i} aria-label="Rules statement"><WorldPlanAgentAnswer answer={chars.slice(r.text_start,r.text_end).join('')}/></section>)
    : completion.answer_segments.map(renderSegment)}</div>;
}
