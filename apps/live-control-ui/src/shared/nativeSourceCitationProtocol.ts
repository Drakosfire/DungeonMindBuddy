import type {NativeSourceSectionCitationV1} from '../api/types';
import {exact} from './sourcePassageProtocol';
const text=(v:unknown):v is string=>typeof v==='string' && !!v.trim();
const hash=(v:unknown)=>typeof v==='string' && /^[a-f0-9]{64}$/.test(v);
const uuid=(v:unknown)=>typeof v==='string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(v);
export function isNativeSourceCitation(v:unknown):v is NativeSourceSectionCitationV1 {
  return exact(v,['segment_index','text_sha256','provider_attempt_id','envelope_sha256','read_event_id',
    'catalog_event_id','source_artifact_id','native_source_revision_id','app_source_revision_id','content_sha256',
    'excerpt_sha256','section_id','selector_policy','source_name','section_title','line_start','line_end'])
    && Number.isSafeInteger(v.segment_index) && Number(v.segment_index)>=0
    && [v.text_sha256,v.envelope_sha256,v.content_sha256,v.excerpt_sha256,v.section_id].every(hash)
    && [v.provider_attempt_id,v.read_event_id,v.catalog_event_id,v.app_source_revision_id].every(uuid)
    && [v.source_artifact_id,v.native_source_revision_id,v.source_name,v.section_title].every(text)
    && v.selector_policy==='markdown_sections_v1' && Number.isSafeInteger(v.line_start)
    && Number(v.line_start)>0 && Number.isSafeInteger(v.line_end) && Number(v.line_end)>=Number(v.line_start);
}
