import {isSessionSummary} from '../../shared/surfaceEvidenceProtocol';
import {sessionSummaryMarkdown} from '../../shared/sessionEvidenceCitation';
import type {SavedCitationPreview} from '../../api/savedCitationPreview';
import {canonical,isRelatedPageClaim} from '../../shared/sourcePassageProtocol';
import {WorldPlanAgentAnswer} from './WorldPlanAgentAnswer';
import {SourceCitationEvidence} from './SourceCitationEvidence';
import {nativeChoices,nativeSavedChoices,relatedPageChoice} from './sourceCitationReads';
import {parseMarkdownAst} from '../../tiptap/markdown/parseMarkdownAst';

/** Keep independent prose blocks separate without breaking tables or fenced code. */
function restoredSegments(segments:string[]):string[] {
  if(segments.length<2)return segments;
  let root:ReturnType<typeof parseMarkdownAst>;
  try {root=parseMarkdownAst(segments.join('\n'));} catch {return segments;}
  const result=[...segments];let offset=0;
  for(let i=0;i<segments.length-1;i++){
    offset+=segments[i]!.length;
    const boundary=offset;
    const paragraph=root.children.find(node=>node.type==='paragraph'
      &&(node.position?.start.offset??Infinity)<boundary&&(node.position?.end.offset??-1)>boundary+1);
    if(paragraph?.type==='paragraph'&&!paragraph.children.some(node=>node.type!=='text'
      &&(node.position?.start.offset??Infinity)<boundary&&(node.position?.end.offset??-1)>boundary+1))result[i]+='\n';
    offset++;
  }
  return result;
}

/** Retained display metadata; executable work and admission stay in full history. */
export function SavedCitationAnswer({preview,answer,worldId,turnId}:{preview:SavedCitationPreview;answer:string;worldId:string;turnId:string}) {
  if(preview?.status!=='ready'||preview.answer_segments.map(s=>s.text).join('\n')!==answer)return <WorldPlanAgentAnswer answer={answer}/>;
  let next=0;
  const displaySegments:string[]=[],targets:string[]=[];
  const statements=preview.answer_segments.map((segment,index)=>{
    if(isSessionSummary(segment)) {
      const summary=sessionSummaryMarkdown(segment,worldId,next+1);
      next=summary.nextNumber-1;displaySegments.push(summary.text);targets.push(...summary.targets);
      return {text:summary.text,choices:[]};
    }
    displaySegments.push(segment.text);
    return {text:segment.text,choices:[
    ...nativeChoices(preview,worldId,turnId,index),
    ...(isRelatedPageClaim(segment,worldId)?[relatedPageChoice(segment,worldId,turnId,index)]:[]),
    ...(preview.source_basis?nativeSavedChoices(preview,preview.source_basis,worldId,turnId,index):[]),
  ].map(choice=>({...choice,segmentIndex:index,number:++next}))};});
  const display=restoredSegments(displaySegments);
  return <SourceCitationEvidence identity={canonical([worldId,turnId,preview])} statements={statements}
    answer={display.join("\n")} displaySegments={display} allowedInternalLinks={targets}/>;
}
