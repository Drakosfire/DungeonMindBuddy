import type {SessionSummarySegment,SessionSummarySupport} from "../api/types";
import type {SessionEvidence} from "../playSurface/review/sessionEvidenceApi";
import {canonical} from "./sourcePassageProtocol";

type Locator=Pick<SessionSummarySupport,"source_ordinal"|"entry_identity"|"body_sha256"|"owner_sha256"|"checkpoint_content_sha256"|"object_id"|"revision">;
const digest=(value:string)=>/^[a-f0-9]{64}$/.test(value);
async function sha(text:string):Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(text))))
    .map(b=>b.toString(16).padStart(2,"0")).join("");
}
export function sessionCitationTarget(worldId:string,support:Locator):string {
  const fragment=`source-${support.source_ordinal}-${support.entry_identity}-${support.body_sha256}-${support.owner_sha256}-${support.checkpoint_content_sha256}`;
  return `/play?${new URLSearchParams({world:worldId,run:support.object_id,evidence_revision:support.revision})}#${fragment}`;
}
export function sessionSummaryMarkdown(segment:SessionSummarySegment,worldId:string,firstNumber:number) {
  const seen=new Set<string>(),links:string[]=[],targets:string[]=[];
  for(const support of segment.supports) {
    const target=sessionCitationTarget(worldId,support);
    if(seen.has(target))continue;
    seen.add(target);targets.push(target);
    const label=support.entry_kind==='closing_reflections'?'Closing reflections':'Scene notes';
    const title=(support.source_name+' · '+label).replaceAll('\\','\\\\').replaceAll('"','\\"');
    links.push(`[${firstNumber++}](${target} "${title}")`);
  }
  return {text:segment.text+' '+links.join(' '),nextNumber:firstNumber,targets};
}
/** Rebuild locators from the actual immutable packet, never from an ordinal alone. */
export async function verifiedSessionEntryTargets(value:SessionEvidence):Promise<string[]> {
  const {sha256:packetSha,...packet}=value;
  if(!digest(packetSha) || !digest(value.session_content_sha256)
    || await sha(canonical(packet))!==packetSha)throw new Error('Saved session evidence packet differs from its digest');
  return Promise.all(value.sources.map(async(source,ordinal)=>{
    const body=await sha(source.text);
    if(body!==source.sha256 || !['scene_note','closing_reflections'].includes(source.kind)
      || (source.kind==='scene_note' ? !source.element_id : source.element_id!=null))
      throw new Error('Saved session entry differs from its identity or body digest');
    const entry=await sha(canonical({kind:source.kind,element_id:source.element_id??null,ordinal}));
    return sessionCitationTarget(value.world_id,{source_ordinal:ordinal,entry_identity:entry,body_sha256:body,
      owner_sha256:packetSha,checkpoint_content_sha256:value.session_content_sha256,
      object_id:value.run_id,revision:String(value.review_revision)});
  }));
}
