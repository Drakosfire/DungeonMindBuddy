import {useLayoutEffect,useRef,useState} from 'react';
import type {SurfaceEvidenceCompletionV3} from '../../api/types';
import {getAgentNativeSourceSection} from '../../api/liveApi';
import {canonical,exact} from '../../shared/sourcePassageProtocol';
import {WorldPlanAgentAnswer} from './WorldPlanAgentAnswer';

export function NativeSourceSectionEvidence({completion,worldId,turnId,segmentIndex}:{
  completion:SurfaceEvidenceCompletionV3;worldId:string;turnId:string;segmentIndex:number;
}) {
  const epoch=useRef(0);
  const [opened,setOpened]=useState<{status:'loading'|'ready'|'unavailable';content?:string}|null>(null);
  const identity=canonical([worldId,turnId,segmentIndex,completion.native_source_citations]);
  useLayoutEffect(()=>{epoch.current++;setOpened(null);return ()=>{epoch.current++;};},[identity]);
  async function open(index:number) {
    const current=++epoch.current;setOpened({status:'loading'});
    try {
      const expected=completion.native_source_citations[index]!;
      const result=await getAgentNativeSourceSection(worldId,turnId,index);
      if(current!==epoch.current)return;
      if(!exact(result,['schema','world_id','turn_id','citation_index','citation','content'])
        || result.schema!=='dmb_agent_native_source_section_read_v1' || result.world_id!==worldId
        || result.turn_id!==turnId || result.citation_index!==index || canonical(result.citation)!==canonical(expected)
        || typeof result.content!=='string' || !result.content) throw new Error('Source section binding changed');
      const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(result.content));
      const hash=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
      if(hash!==expected.excerpt_sha256)throw new Error('Source section bytes changed');
      if(current===epoch.current)setOpened({status:'ready',content:result.content});
    } catch {if(current===epoch.current)setOpened({status:'unavailable'});}
  }
  return <section aria-label="Source sections">
    {completion.native_source_citations.flatMap((c,i)=>c.segment_index===segmentIndex
      ? <button key={i} type="button" onClick={()=>{void open(i);}}>{c.source_name} · {c.section_title}</button>:[])}
    {opened ? <section aria-label="Opened source section" aria-live="polite">
      <button type="button" onClick={()=>{epoch.current++;setOpened(null);}}>Close section</button>
      {opened.status==='loading' ? <p>Opening section…</p> : opened.status==='unavailable'
        ? <p>The exact cited section is unavailable. No newer text has been substituted.</p>
        : <WorldPlanAgentAnswer answer={opened.content ?? ''}/>}
    </section>:null}
  </section>;
}
