import {sameInspectionPin,type NativeAssertion,type NativeGraphEntity} from '../api/nativeGraphInspection';
import {inspectNativeGraph} from '../api/liveApi';
import type {CitationChoice} from '../planSurface/components/SourceCitationEvidence';

/** One source may support several records; that is not independent corroboration. */
export function nativeObjectEvidenceChoices(detail:NativeGraphEntity, records:readonly NativeAssertion[], entityOnly:boolean):CitationChoice[] {
 if(entityOnly) return [];
 const supporting=new Set(detail.entity.evidence.filter(e=>e.evidence_role==='support').map(e=>e.evidence_ref_id));
 const seen=new Set<string>();
 const choices:CitationChoice[]=[];
 for(const assertion of records) for(const id of assertion.metadata.evidence_ref_ids) {
  if(!supporting.has(id)||seen.has(id)) continue;
  seen.add(id);
  choices.push({key:id,number:choices.length+1,title:'Supporting source · exact excerpt',label:'Read supporting source',kind:'passage',load:async()=>{
   const packet=await inspectNativeGraph(detail.scope,{kind:'source',assertion_id:assertion.assertion_id,evidence_ref_id:id});
   if(packet.schema!=='dmb_native_graph_source_v1'||!sameInspectionPin(packet.scope,detail.scope)) throw new Error('Source unavailable');
   return packet.source.text;
  }});
 }
 return choices;
}
