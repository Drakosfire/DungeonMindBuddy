import type {SurfaceEvidenceCompletion} from "../../api/types";
import {WorldPlanAgentAnswer} from "./WorldPlanAgentAnswer";
import {BuildSourcePassageEvidence} from "./BuildSourcePassageEvidence";

type Composition = {text:string;ranges:{domain:string;base_segment_index:number|null;text_start:number;text_end:number}[]};
/** Same visible authority and exact passage selector in Plan, Play and Rules compositions. */
export function SurfaceEvidenceAnswer({completion,composition,worldId,turnId}:{
  completion:SurfaceEvidenceCompletion;composition?:Composition;worldId?:string|null;turnId?:string;
}) {
  const renderSegment=(s:SurfaceEvidenceCompletion['answer_segments'][number],index:number,key:number) => {
    if(s.kind === 'authored_quote' || s.kind === 'authored_excerpt') return <figure key={key}><figcaption>{s.source_name} · quoted excerpt</figcaption>
      <blockquote><WorldPlanAgentAnswer answer={s.text}/></blockquote></figure>;
    const graph=s.kind === 'graph_claim', source=s.kind === 'source_passage_claim';
    const selected=completion.source_citations.filter(c=>c.segment_index === index);
    return <section key={key} aria-label={graph ? 'World Graph fact' : source ? 'Source-supported statement' : s.kind === 'proposal' ? 'Proposed idea' : 'Evidence limitation'}>
      {graph ? <small>{selected.length ? 'World Graph' : 'World Graph · source passage not opened'}</small> : null}
      {s.kind === 'proposal' ? <small>Proposed idea</small> : null}<WorldPlanAgentAnswer answer={s.text}/>
      {selected.length ? worldId && turnId
        ? <BuildSourcePassageEvidence completion={completion} worldId={worldId} turnId={turnId} segmentIndex={index} showClaimText={false}/>
        : selected.map((c,i)=><cite key={i}>{c.source_name}</cite>) : null}
    </section>;
  };
  const chars=composition ? Array.from(composition.text) : [];
  return <div aria-label="Evidence-grounded answer">{composition ? composition.ranges.map((r,i)=>
    r.domain === 'base' && r.base_segment_index !== null
      ? renderSegment(completion.answer_segments[r.base_segment_index]!,r.base_segment_index,i)
      : <section key={i} aria-label="Rules statement"><WorldPlanAgentAnswer answer={chars.slice(r.text_start,r.text_end).join('')}/></section>)
    : completion.answer_segments.map((s,i)=>renderSegment(s,i,i))}</div>;
}
