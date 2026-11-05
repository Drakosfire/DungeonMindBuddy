import {exact} from '../shared/sourcePassageProtocol';
import type {InspectionPin} from './nativeGraphInspection';
export type NativeSourceMetadata={
 source_artifact:{source_artifact_id:string;source_classification:string};
 source_revision:{source_revision_id:string;content_sha256:string};evidence_ref_ids:string[];
 origin:{namespace:string;object_id:string;revision_id:string}|null;
 navigation:{label:string|null;kind:'recap'|'worldbuilding'|'other';campaign_id:string|null;
 session_id:string|null;status:'available'|'unavailable';metadata_revision:string|null;
 origin_matches_current_metadata:boolean|null};
};
export type NativeSourceCatalog={schema:'dmb_native_source_catalog_v1';scope:InspectionPin;
 catalogue:{space_id:string;revision_id:string;source_authority_epoch:number;
 sources:NativeSourceMetadata[];complete:boolean};navigation_complete:boolean};
export type NativeSourceSelection={source_artifact_id:string;source_revision_id:string;evidence_ref_id:string};
export type NativeSourceSection={section_id:string;label:string;line_start:number;line_end:number;char_start:number;char_end:number};
export type NativeSourceSections={selector_policy:'markdown_sections_v1';sections:NativeSourceSection[]};
/** The existing native selector uses code-point offsets; never UTF-16 indices. */
export function isNativeSourceSections(value:unknown,body:string):value is NativeSourceSections {
 if(!exact(value,['selector_policy','sections'])||value.selector_policy!=='markdown_sections_v1'||!Array.isArray(value.sections)||!value.sections.length)return false;
 // Match Python splitlines(keepends=True), without parsing Markdown again.
 const lines=body.match(/[^\n\r\v\f\x1c-\x1e\x85\u2028\u2029]*(?:\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]|$)/gu)??[];
 const lineEnds=[0];for(const text of lines)if(text)lineEnds.push(lineEnds[lineEnds.length-1]+Array.from(text).length);
 let line=0,char=0;const ids=new Set<string>();
 for(const section of value.sections){
  if(!exact(section,['section_id','label','line_start','line_end','char_start','char_end'])
   ||typeof section.section_id!=='string'||!(/^[a-f0-9]{64}$/).test(section.section_id)||ids.has(section.section_id)
   ||typeof section.label!=='string'||!section.label.trim()
   ||!['line_start','line_end','char_start','char_end'].every(k=>Number.isSafeInteger(section[k]))
   ||section.line_start!==line+1||Number(section.line_end)<Number(section.line_start)
   ||section.char_start!==char||Number(section.char_end)<=char
   ||lineEnds[Number(section.line_start)-1]!==section.char_start
   ||lineEnds[Number(section.line_end)]!==section.char_end)return false;
  ids.add(section.section_id);line=Number(section.line_end);char=Number(section.char_end);
 }
 return char===Array.from(body).length;
}
export type NativeSourceBody={section_catalog:NativeSourceSections|null;schema:'dmb_native_source_body_v1';scope:InspectionPin;
 source:{status:'available';source_artifact_id:string;source_revision_id:string;
 body_text:string;body_sha256:string;evidence_ref_id:string;source_authority_epoch:number}};
