import {nativeTextDigest} from '../shared/nativeStatementAnswerProtocol';
import type {SavedCitationPreview} from '../api/savedCitationPreview';
export async function savedCitationPreviewFixture(surface:'build'|'plan'|'play'='plan') {
  const answer='The bridge was ruined.',body='The bridge was ruined in the flood.',h='a'.repeat(64);
  const citation={segment_index:0,text_sha256:await nativeTextDigest(answer),
    provider_attempt_id:'11111111-1111-4111-8111-111111111111',envelope_sha256:h,
    read_event_id:'22222222-2222-4222-8222-222222222222',catalog_sha256:h,
    source_artifact_id:'source:bridge',native_source_revision_id:'srev:bridge',
    content_sha256:await nativeTextDigest(body),excerpt_sha256:await nativeTextDigest(body),
    section_id:h,selector_policy:'native_full_document_v1' as const,source_name:'Bridge recap',section_title:'Full document',line_start:1,line_end:1};
  const preview:Extract<SavedCitationPreview,{status:'ready'}>={schema:'dmb_saved_native_citation_preview_v1',status:'ready',surface_id:surface,
    answer_segments:[{kind:'source_passage_claim',text:answer}],native_source_citations:[],native_body_citations:[citation],
    native_clause_citations:[],native_assertion_citations:[],saved_source_citations:[],source_basis:null};
  return {preview,answer,body,citation};
}
