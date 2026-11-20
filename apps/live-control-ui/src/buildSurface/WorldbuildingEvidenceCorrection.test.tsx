import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {WorldbuildingEvidenceCorrection,validWorldbuildingCorrection} from './WorldbuildingEvidenceCorrection';
import type {ExactRunReviewPackage,WorldbuildingFrozenSpanCatalog,WorldbuildingEvidenceCorrectionRequest} from '../api/types';
const catalog:WorldbuildingFrozenSpanCatalog={schema:'dmb_worldbuilding_frozen_span_catalog_v1',parentRunId:'run',parentRevision:7,parentStatus:'reviewable',
 worldId:'world',sourceArtifactId:'source',sourceSha256:'b'.repeat(64),spanIndexSha256:'c'.repeat(64),parentCandidateSha256:'a'.repeat(64),
 spans:[{sourceSpanRefId:'heading',startLine:1,endLine:1,paragraphText:'A heading'},
 {sourceSpanRefId:'road',startLine:2,endLine:2,paragraphText:'Mara repairs the road.'},
 {sourceSpanRefId:'tower',startLine:3,endLine:3,paragraphText:'Nell keeps a lantern.'}],
 evidenceRefs:[{assertionId:'keepers',evidenceIndex:0,refSha256:'d'.repeat(64)}]};
const review={assertions:[{assertionId:'keepers',kind:'object',label:'Keepers',summary:'Two keepers',evidence:[{
 sourceArtifactId:'source',sourceSpanRefId:'heading',paragraphText:'A heading',anchorQuotes:['Mara repairs road','Nell keeps a lantern.'],
 invalidAnchorQuotes:['Mara repairs road','Nell keeps a lantern.']}]}]} as ExactRunReviewPackage;
afterEach(cleanup);
function props(){return {review,catalog,busy:false,recovery:null,hasRecovery:false,error:null,onSubmit:vi.fn(),onRetry:vi.fn(),onAbandon:vi.fn()};}
it('previews explicit paragraphs and complete quote assignments without mutation before confirmation',()=>{
 const p=props();render(<WorldbuildingEvidenceCorrection {...p}/>);
 fireEvent.change(screen.getByLabelText('Source paragraph for Keepers quote 1'),{target:{value:'road'}});
 fireEvent.change(screen.getByLabelText('Literal replacement for Keepers quote 1'),{target:{value:'Mara repairs the road.'}});
 fireEvent.change(screen.getByLabelText('Source paragraph for Keepers quote 2'),{target:{value:'tower'}});
 fireEvent.change(screen.getByLabelText('Literal replacement for Keepers quote 2'),{target:{value:'Nell keeps a lantern.'}});
 fireEvent.click(screen.getByRole('button',{name:'Preview evidence corrections'}));expect(p.onSubmit).not.toHaveBeenCalled();
 expect(screen.getByRole('region',{name:'Preview evidence corrections'})).toHaveTextContent('Lines 3–3');
 fireEvent.click(screen.getByRole('button',{name:'Create reviewed child candidate'}));
 const request=p.onSubmit.mock.calls[0][0] as WorldbuildingEvidenceCorrectionRequest;
 expect(request.corrections[0].parts).toEqual([
 {sourceSpanRefId:'road',quoteAssignments:[{originalQuoteIndex:0,replacementQuote:'Mara repairs the road.'}]},
 {sourceSpanRefId:'tower',quoteAssignments:[{originalQuoteIndex:1,replacementQuote:'Nell keeps a lantern.'}]}]);
 expect(validWorldbuildingCorrection(request,catalog,review)).toBe(true);
 const broken=structuredClone(request);broken.corrections[0].parts[1].quoteAssignments[0].originalQuoteIndex=0;
 expect(validWorldbuildingCorrection(broken,catalog,review)).toBe(false);
 broken.corrections[0].parts.pop();expect(validWorldbuildingCorrection(broken,catalog,review)).toBe(false);
});
it('does not infer a paragraph or submit incomplete quote assignments',()=>{
 const p=props();render(<WorldbuildingEvidenceCorrection {...p}/>);
 expect(screen.getByLabelText('Source paragraph for Keepers quote 1')).toHaveValue('heading');
 expect(screen.getByRole('button',{name:'Preview evidence corrections'})).toBeDisabled();
 expect(p.onSubmit).not.toHaveBeenCalled();
});
