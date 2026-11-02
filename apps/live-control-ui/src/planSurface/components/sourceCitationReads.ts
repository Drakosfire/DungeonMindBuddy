import {getAgentNativeAssertionSource,getAgentNativeSourceClause,getAgentSourcePassage,getAgentNativeSourceSection,getAgentNativeBodyExcerpt,getAgentRelatedPage} from '../../api/liveApi';
import type {WorldBuildSourceCompletion,SurfaceSourceCompletionV1,SurfaceEvidenceCompletion,SurfaceEvidenceCompletionV3,SurfaceEvidenceCompletionV5,SurfaceEvidenceCompletionV6,SurfaceEvidenceCompletionV7,SurfaceNativeCompletionV1} from '../../api/types';
import {exact,canonical} from '../../shared/sourcePassageProtocol';
import type {CitationChoice} from './SourceCitationEvidence';
export type PassageCompletion=WorldBuildSourceCompletion|SurfaceSourceCompletionV1|SurfaceEvidenceCompletion|SurfaceNativeCompletionV1;
async function hash(content:string){
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(content));
  return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
}
export function passageChoices(completion:PassageCompletion,worldId:string,turnId:string,segmentIndex?:number):CitationChoice[] {
  const seen=new Set<string>();
  const passages: CitationChoice[]=('source_citations' in completion ? completion.source_citations : []).flatMap((citation,index)=>{
    if(segmentIndex!==undefined && citation.segment_index!==segmentIndex)return [];
    const r=citation.receipt;
    const key=canonical([citation.segment_index,r.source_artifact_id,r.source_revision_id,r.content_sha256,r.line_start,r.line_end]);
    if(seen.has(key))return [];seen.add(key);
    const title='source_name' in citation ? `${citation.source_name} · ${r.line_start===null ? 'passage' : `lines ${r.line_start}–${r.line_end}`}` : `Passage ${index+1}`;
    return [{key:`passage:${index}`,number:index+1,segmentIndex:citation.segment_index,title,label:'source_name' in citation ? `Read ${title}` : `Read passage ${index+1}`,kind:'passage' as const,load:async()=>{
      const result=await getAgentSourcePassage(worldId,turnId,index);
      if(!exact(result,['schema','target','citation','content']) || result.schema!=='dmb_agent_source_passage_read_v1'
        || !exact(result.target,['schema','kind','world_id','turn_id','citation_index'])
        || result.target.schema!=='dmb_agent_source_passage_open_target_v1' || result.target.kind!=='source_passage'
        || result.target.world_id!==worldId || result.target.turn_id!==turnId || result.target.citation_index!==index
        || canonical(result.citation)!==canonical(citation) || typeof result.content!=='string'
        || [...result.content].length!==r.returned_chars || await hash(result.content)!==r.content_sha256)throw new Error('Source binding differs');
      return result.content;
    }}];
  });
  const pages: CitationChoice[]=completion.answer_segments.flatMap((segment,index)=>{
    if(segment.kind!=='related_page_claim' || segmentIndex!==undefined && index!==segmentIndex)return [];
    const page=segment.page;
    const title=`${page.title} · saved revision ${page.registry_revision}`;
    return [{key:`related:${segment.read_id}:${index}`,number:('source_citations' in completion ? completion.source_citations.length : 0)+index+1,segmentIndex:index,
      title,label:`Read ${title}`,kind:'section' as const,load:async()=>{
        const result=await getAgentRelatedPage(worldId,turnId,segment.read_id);
        if(page.world_id!==worldId || !exact(result,['schema','world_id','turn_id','read_id','page','markdown'])
          || result.schema!=='dmb_agent_related_page_read_v1' || result.world_id!==worldId || result.turn_id!==turnId
          || result.read_id!==segment.read_id || canonical(result.page)!==canonical(page)
          || typeof result.markdown!=='string' || await hash(result.markdown)!==page.content_sha256)throw new Error('Related page binding differs');
        return result.markdown;
      }}];
  });
  return [...passages,...pages];
}
export function nativeChoices(completion:Partial<Pick<SurfaceEvidenceCompletionV3,"native_source_citations"> & Pick<SurfaceEvidenceCompletionV5,"native_body_citations"> & Pick<SurfaceEvidenceCompletionV6,"native_clause_citations"> & Pick<SurfaceEvidenceCompletionV7,"native_assertion_citations">>,worldId:string,turnId:string,segmentIndex:number):CitationChoice[] {
  const sections=(completion.native_source_citations??[]).flatMap((citation,index)=>citation.segment_index!==segmentIndex ? [] : [{
    key:`section:${index}`,number:index+1,title:`${citation.source_name} · ${citation.section_title}`,
    label:`${citation.source_name} · ${citation.section_title}`,kind:'section' as const,load:async()=>{
      const result=await getAgentNativeSourceSection(worldId,turnId,index);
      if(!exact(result,['schema','world_id','turn_id','citation_index','citation','content'])
        || result.schema!=='dmb_agent_native_source_section_read_v1' || result.world_id!==worldId
        || result.turn_id!==turnId || result.citation_index!==index || canonical(result.citation)!==canonical(citation)
        || typeof result.content!=='string' || !result.content || await hash(result.content)!==citation.excerpt_sha256)throw new Error('Source section binding differs');
      return result.content;
    },
  }]);
  return [...sections,...(completion.native_body_citations??[]).flatMap((citation,index)=>citation.segment_index!==segmentIndex?[]:[{
    key:`body:${index}`,number:sections.length+index+1,title:`${citation.source_name} · ${citation.section_title}`,
    label:`${citation.source_name} · ${citation.section_title}`,kind:'section' as const,load:async()=>{
      const result=await getAgentNativeBodyExcerpt(worldId,turnId,index);
      if(!exact(result,['schema','world_id','turn_id','citation_index','citation','content'])
        || result.schema!=='dmb_agent_native_body_excerpt_read_v1' || result.world_id!==worldId
        || result.turn_id!==turnId || result.citation_index!==index || canonical(result.citation)!==canonical(citation)
        || typeof result.content!=='string' || !result.content || await hash(result.content)!==citation.excerpt_sha256)
        throw new Error('Source excerpt binding differs');
      return result.content;
    },
  }]),...(completion.native_clause_citations??[]).flatMap((citation,index)=>citation.segment_index!==segmentIndex?[]:[{
    key:`statement:${index}`,number:sections.length+index+1,title:`Source statement · ${citation.campaign_id}`,
    label:`Read source statement · ${citation.campaign_id}`,kind:'section' as const,load:async()=>{
      const result=await getAgentNativeSourceClause(worldId,turnId,index);
      if(!exact(result,['schema','world_id','turn_id','citation_index','citation','content'])
        ||result.schema!=='dmb_native_statement_clause_read_v1'||result.world_id!==worldId||result.turn_id!==turnId
        ||result.citation_index!==index||canonical(result.citation)!==canonical(citation)||typeof result.content!=='string'
        ||new TextEncoder().encode(result.content).length!==citation.end_byte-citation.start_byte
        ||await hash(result.content)!==citation.clause_sha256)throw new Error('Native statement source binding differs');
      return result.content;
    },
  }]),...(completion.native_assertion_citations??[]).flatMap((citation,index)=>citation.segment_index!==segmentIndex?[]:[{
    key:`assertion:${index}`,number:sections.length+index+1,title:'Reviewed Graph · supporting source',label:'Read Graph assertion source',kind:'section' as const,load:async()=>{
      const result=await getAgentNativeAssertionSource(worldId,turnId,index);
      if(!exact(result,['schema','world_id','turn_id','citation_index','citation','content'])
        ||result.schema!=='dmb_native_assertion_source_read_v1'||result.world_id!==worldId||result.turn_id!==turnId
        ||result.citation_index!==index||canonical(result.citation)!==canonical(citation)||typeof result.content!=='string'
        ||new TextEncoder().encode(result.content).length!==citation.end_byte-citation.start_byte
        ||await hash(result.content)!==citation.span_sha256)throw new Error('Native assertion source binding differs');
      return result.content;
    },
  }])];
}
