import type {NativeStatementAnswerContextV1} from '../../api/types';
import {getAgentNativeSourceClause} from '../../api/liveApi';
import {canonical,exact} from '../../shared/sourcePassageProtocol';
import {nativeTextDigest} from '../../shared/nativeStatementAnswerProtocol';
import {SourceCitationEvidence} from './SourceCitationEvidence';
import {WorldPlanAgentAnswer} from './WorldPlanAgentAnswer';

export function NativeStatementAnswer({context,worldId,turnId}:{context:NativeStatementAnswerContextV1;worldId:string;turnId:string}){
  const c=context.completion;if(!c)return null;
  const prefixes={source_report:'Source reports: ',proposal:'Possibility: ',limitation:'Limitation: '};
  return <div aria-label="Source-attributed answer">{c.answer_segments.map((s,i)=>{
    const choices=c.native_clause_citations.flatMap((citation,index)=>citation.segment_index!==i?[]:[{
      key:`native-clause:${index}`,number:index+1,title:'Original source passage',label:`Read source ${index+1}`,kind:'passage' as const,
      load:async()=>{
        const read=await getAgentNativeSourceClause(worldId,turnId,index);
        if(!exact(read,['schema','world_id','turn_id','citation_index','citation','content'])||read.schema!=='dmb_native_statement_clause_read_v1'
          ||read.world_id!==worldId||read.turn_id!==turnId||read.citation_index!==index||canonical(read.citation)!==canonical(citation)
          ||typeof read.content!=='string'||await nativeTextDigest(read.content)!==citation.clause_sha256
          ||new TextEncoder().encode(read.content).length!==citation.end_byte-citation.start_byte)throw new Error('Original source clause is unavailable or its identity differs.');
        return read.content;
      },
    }]);
    const text=prefixes[s.kind]+s.text;
    return <section key={i} aria-label={s.kind==='source_report'?'Source report':s.kind==='proposal'?'Proposed possibility':'Evidence limitation'}>
      {choices.length?<SourceCitationEvidence identity={canonical([c,worldId,turnId,i])} statements={[{text,choices}]}/>:<WorldPlanAgentAnswer answer={text}/>}
    </section>;
  })}</div>;
}
