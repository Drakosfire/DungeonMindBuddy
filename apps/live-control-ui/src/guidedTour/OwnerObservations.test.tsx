import {render} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import type {MarkdownCanvasSessionValue} from '../markdownCanvas/MarkdownCanvasSession';
import type {SavedWorldBuildConversationContext} from '../agentInteraction/WorldAgentConversation';
import {BuildTourObservations,PlanTourObservation,PlayTourObservation} from './OwnerObservations';
import type {TourOwnerReading} from './GuidedTour';
const readings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
vi.mock('./GuidedTour',()=>({useTourOwnerReading:(reading:TourOwnerReading)=>{readings.set(reading.step,reading);}}));
const source={worldId:'world',documentId:'page',revision:2,contentSha256:'a'.repeat(64),dirty:false} as SavedWorldBuildConversationContext;
function session(receipt:unknown=null,extra:Partial<MarkdownCanvasSessionValue>={}):MarkdownCanvasSessionValue {
 return {phase:'ready_clean',activeCommand:null,lastCommitReceipt:receipt,saveDisabledReason:null,...extra} as MarkdownCanvasSessionValue;
}
const receipt={writer_ok:true,world_id:'world',committed_record:{updated_at:'2026-10-28T00:00:00Z'},document_id:'page',registry_revision:2,normalized_content_sha256:'a'.repeat(64)};
beforeEach(()=>readings.clear());
it('explains an empty Build surface without requiring an editor session',()=>{
 render(<BuildTourObservations source={null} session={null}/>);
 expect(readings.get('source')?.status).toBe('unavailable');
 expect(readings.get('authoring')?.observation).toBeUndefined();
});
it('labels a retained save receipt on first mount as an existing example',()=>{
 render(<BuildTourObservations source={source} session={session(receipt)}/>);
 expect(readings.get('authoring')?.observation?.origin).toBe('existing');
});
it('recognizes a new matching verified Save receipt, without sending a command',()=>{
 const mounted=render(<BuildTourObservations source={source} session={session()}/>);
 mounted.rerender(<BuildTourObservations source={source} session={session(receipt)}/>);
 expect(readings.get('authoring')?.observation).toMatchObject({origin:'acknowledged',target:{worldId:'world',objectId:'page',revision:2,digest:source.contentSha256}});
});
it.each([
 {...receipt,writer_ok:false},
 {...receipt,world_id:'another-world'},
 {...receipt,committed_record:{updated_at:'invalid'}},
 {...receipt,document_id:'another-page'},
 {...receipt,registry_revision:1},
 {...receipt,normalized_content_sha256:'b'.repeat(64)},
])('does not credit a mismatched or failed receipt as new authoring',wrong=>{
 const mounted=render(<BuildTourObservations source={source} session={session()}/>);
 mounted.rerender(<BuildTourObservations source={source} session={session(wrong)}/>);
 expect(readings.get('authoring')?.observation?.origin).toBe('existing');
});
it.each([
 {phase:'committed_verification_pending' as const},
 {phase:'ready_dirty' as const},
 {activeCommand:{id:'pending'} as unknown as MarkdownCanvasSessionValue['activeCommand']},
])('does not record completion while the owner has pending or dirty work',extra=>{
 const mounted=render(<BuildTourObservations source={source} session={session()}/>);
 mounted.rerender(<BuildTourObservations source={source} session={session(receipt,extra)}/>);
 expect(readings.get('authoring')?.status).toBe('unavailable');
 expect(readings.get('authoring')?.observation).toBeUndefined();
});
it('uses the immutable Plan version identity from the verified preflight',()=>{
 render(<PlanTourObservation verified={{worldId:'world',documentId:'plan',pin:{revisionN:3,workRevisionId:'immutable-version-3',contentSha256:'b'.repeat(64)}}} error={null}/>);
 expect(readings.get('plan')?.observation).toMatchObject({origin:'existing',target:{kind:'plan',revision:3,revisionId:'immutable-version-3'}});
});
it('withdraws the current Plan observation when its verified preview is no longer usable',()=>{
 const mounted=render(<PlanTourObservation verified={{worldId:'world',documentId:'plan',pin:{revisionN:3,workRevisionId:'immutable-version-3',contentSha256:'b'.repeat(64)}}} error={null}/>);
 mounted.rerender(<PlanTourObservation verified={null} error={null}/>);
 expect(readings.get('plan')?.status).toBe('unavailable');
 expect(readings.get('plan')?.observation).toBeUndefined();
});

it('credits Plan Save only when the acknowledged registry revision and verified immutable preview match',()=>{
 const verified={worldId:'world',documentId:'plan',pin:{revisionN:3,workRevisionId:'immutable-version-3',contentSha256:'b'.repeat(64)}};
 const saved={worldId:'world',documentId:'plan',revision:9,digest:'b'.repeat(64),observedAt:'2026-10-28T00:00:00Z'};
 const mounted=render(<PlanTourObservation verified={verified} saved={saved} registryRevision={9} error={null}/>);
 expect(readings.get('plan')?.observation).toMatchObject({origin:'acknowledged',observedAt:saved.observedAt,target:{revision:3,revisionId:'immutable-version-3'}});
 mounted.rerender(<PlanTourObservation verified={verified} saved={saved} registryRevision={10} error={null}/>);
 expect(readings.get('plan')?.observation?.origin).toBe('existing');
 mounted.rerender(<PlanTourObservation verified={verified} saved={saved} registryRevision={9} error='Verification failed'/>);
 expect(readings.get('plan')?.status).toBe('failed');expect(readings.get('plan')?.observation).toBeUndefined();
});
it('pins an admitted Run to its exact parent Plan and never credits a load as new creation',()=>{
 const run={world_id:'world',run_id:'run',run_revision:7,playable_artifact_id:'plan',playable_revision:3,playable_work_revision_id:'immutable-version-3',playable_content_sha256:'b'.repeat(64),updated_at:'2026-10-28T00:00:00Z'} as import('../api/types').WorldPlayRunRecordV2;
 const mounted=render(<PlayTourObservation run={run} blocked={false} error={null}/>);
 expect(readings.get('play')?.observation).toMatchObject({origin:'existing',target:{kind:'run',objectId:'run',revision:7},parent:{kind:'plan',objectId:'plan',revision:3,revisionId:'immutable-version-3',digest:run.playable_content_sha256}});
 mounted.rerender(<PlayTourObservation run={run} blocked={true} error={null}/>);
 expect(readings.get('play')?.status).toBe('unavailable');expect(readings.get('play')?.observation).toBeUndefined();
 mounted.rerender(<PlayTourObservation run={null} blocked={false} error='Run integrity failure'/>);
 expect(readings.get('play')?.status).toBe('failed');expect(readings.get('play')?.observation).toBeUndefined();
});
