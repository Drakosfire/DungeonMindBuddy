import {render,screen} from '@testing-library/react';
import {it,expect} from 'vitest';
import {SurfaceEvidenceAnswer} from './SurfaceEvidenceAnswer';
import type {SurfaceEvidenceCompletionV1} from '../../api/types';
function evidence():SurfaceEvidenceCompletionV1 {
 return {schema:'dmb_surface_evidence_completion_v1',surface_id:'plan',context_receipt_sha256:'a'.repeat(64),
 answer_basis:'mixed_evidence',answer_context_status:'authored_grounded',citation_map:null,source_citations:[],answer_segments:[
 {kind:'authored_quote',text:'A proposed outing.',source_kind:'plan',source_name:'Committed Plan',source_handle:'q1',object_id:'p',revision:'1',body_sha256:'b'.repeat(64),owner_sha256:'b'.repeat(64)},
 {kind:'source_passage_claim',text:'The journal describes a walkway.'}]};
}
it('keeps quoted Plan material visibly separate from source-supported prose',()=>{
  render(<SurfaceEvidenceAnswer completion={evidence()}/>);
  expect(screen.getByText('Committed Plan · quoted excerpt')).toBeTruthy();
  expect(screen.getByText('A proposed outing.').closest('blockquote')).not.toBeNull();
  expect(screen.getByLabelText('Source-supported statement').textContent).toContain('journal describes');
});
