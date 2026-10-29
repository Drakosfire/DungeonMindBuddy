import {render} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import type {TourOwnerReading} from './GuidedTour';
import {MechanicsTourObservation,AdoptionTourObservation,generatedMechanicsReading,type AcknowledgedMechanicsSave,type AcknowledgedMechanicsAdoption} from './MechanicsObservations';
import type {OpenSavedMechanicsVersion} from '../statblocks/revision/savedMechanicsRevisionTypes';
import type {TourEncounterScope} from './EncounterScope';
import {validObservation} from './protocol';
const readings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
vi.mock('./GuidedTour',()=>({useTourOwnerReading:(reading:TourOwnerReading|null)=>{if(reading)readings.set(reading.step,reading);}}));
const scope:TourEncounterScope={plan:{kind:'plan',worldId:'world',objectId:'plan',revision:2,revisionId:'work-2',digest:'a'.repeat(64)},sceneId:'scene',encounterId:'encounter'};
const locator={provider:'dungeonmind' as const,statblock_id:'creature',revision_id:'version',contract:'contract',contract_version:'1',definition_digest:'sha256:'+'b'.repeat(64)};
const opened={world_id:'world',draft_id:'draft',locator,resource:{}} as OpenSavedMechanicsVersion;
const acknowledged:AcknowledgedMechanicsSave={scope,draftId:'draft',operation:{operation_id:'save',state:'committed',base:{...locator,revision_id:'base'},result:locator,refusal_code:null,change_summary:'Manual HP',created_at:'2026-10-28T00:00:00Z'}};
beforeEach(()=>readings.clear());
it('requires exact reopened mechanics including digest and contract, not just revision ID',()=>{
 const mounted=render(<MechanicsTourObservation scope={scope} opened={opened} history={null} acknowledged={acknowledged} blocked={false}/>);
 const observation=readings.get('mechanics')?.observation;
 expect(observation?.proof).toMatchObject({kind:'mechanics',locator});expect(validObservation(observation,'world')).toBe(true);
 mounted.rerender(<MechanicsTourObservation scope={scope} opened={{...opened,locator:{...locator,definition_digest:'sha256:'+'c'.repeat(64)}}} history={null} acknowledged={acknowledged} blocked={false}/>);
 expect(readings.get('mechanics')?.observation).toBeUndefined();
});
it('does not transfer a mechanics acknowledgement to another scene or Plan version',()=>{
 render(<MechanicsTourObservation scope={{...scope,sceneId:'other'}} opened={opened} history={null} acknowledged={acknowledged} blocked={false}/>);
 expect(readings.get('mechanics')?.observation).toBeUndefined();
});
it('recognizes an older manual version as an example and blocks dirty or unknown saves',()=>{
 const history={world_id:'world',draft_id:'draft',name:'Creature',original:locator,operations:[acknowledged.operation],pending:null,next_offset:null};
 const mounted=render(<MechanicsTourObservation scope={scope} opened={opened} history={history} acknowledged={null} blocked={false}/>);
 expect(readings.get('mechanics')?.observation?.origin).toBe('existing');
 mounted.rerender(<MechanicsTourObservation scope={scope} opened={opened} history={history} acknowledged={acknowledged} blocked={true}/>);
 expect(readings.get('mechanics')?.observation).toBeUndefined();
});
it('does not publish encounter-specific mechanics outside an admitted encounter',()=>{
 render(<MechanicsTourObservation scope={null} opened={opened} history={null} acknowledged={acknowledged} blocked={false}/>);
 expect(readings.size).toBe(0);
});
const adoption={scope,outcome:{receipt:{world_id:'world',encounter_id:'encounter',state:'applied',operation_id:'adopt',committed_revision:5,created_at:'2026-10-28T00:00:00Z',source:locator,transitions:[{actor_id:'actor',before_snapshot_digest:'before',after_snapshot_digest:'after',ac_policy:'keep',hp_policy:'clamp_current'}]}}} as AcknowledgedMechanicsAdoption;
it('records the verified exact version and actor policies, and refuses canceled or pending outcomes',()=>{
 const mounted=render(<AdoptionTourObservation scope={scope} worldId='world' encounterId='encounter' acknowledged={adoption} blocked={false}/>);
 const observation=readings.get('adoption')?.observation;
 expect(validObservation(observation,'world')).toBe(true);
 expect(observation?.proof).toMatchObject({kind:'adoption',encounterRevision:5,locator,actors:[{actorId:'actor',hpPolicy:'clamp_current'}]});
 mounted.rerender(<AdoptionTourObservation scope={scope} worldId='world' encounterId='encounter' acknowledged={adoption} blocked={true}/>);
 expect(readings.get('adoption')?.observation).toBeUndefined();
 mounted.rerender(<AdoptionTourObservation scope={scope} worldId='world' encounterId='encounter' acknowledged={{...adoption,outcome:{...adoption.outcome,receipt:{...adoption.outcome.receipt,state:'canceled',committed_revision:null,transitions:[]}}}} blocked={false}/>);
 expect(readings.get('adoption')?.observation).toBeUndefined();
});
it('labels explicitly inspected receipts as existing and fences a different Plan pin or dirty encounter',()=>{
 const mounted=render(<AdoptionTourObservation scope={scope} worldId='world' encounterId='encounter' acknowledged={null} inspected={adoption} blocked={false}/>);
 expect(readings.get('adoption')?.observation?.origin).toBe('existing');
 mounted.rerender(<AdoptionTourObservation scope={{...scope,plan:{...scope.plan,revision:3,revisionId:'work-3'}}} worldId='world' encounterId='encounter' acknowledged={null} inspected={adoption} blocked={false}/>);
 expect(readings.get('adoption')?.observation).toBeUndefined();
 mounted.rerender(<AdoptionTourObservation scope={scope} worldId='world' encounterId='encounter' acknowledged={null} inspected={adoption} blocked={true}/>);
 expect(readings.get('adoption')?.observation).toBeUndefined();
});

const generatedScope={plan:scope.plan,walkthroughId:'tour',draftId:'draft',acceptOperationId:'accept',original:acknowledged.operation.base,dispatchRevision:3};
it('recognizes a reopened standalone successor rooted in the accepted generated creature without an encounter',()=>{
 const history={world_id:'world',draft_id:'draft',name:'Creature',original:generatedScope.original,operations:[acknowledged.operation],pending:null,next_offset:null};
 const reading=generatedMechanicsReading(generatedScope,opened,history,null,false)!;
 expect(reading.observation).toMatchObject({origin:'existing',proof:{kind:'generated-mechanics-revision',scope:generatedScope,lineage:[{operationId:'save',base:generatedScope.original,locator}]}});
 expect(validObservation(reading.observation,'world')).toBe(true);
 expect(reading.observation?.proof).not.toHaveProperty('encounterId');
});
it.each(['draft','world','original-digest','result-digest','base','pending','dirty','cycle','foreign-statblock'] as const)('does not recognize a standalone revision with %s mismatch',fault=>{
 const h={world_id:'world',draft_id:'draft',name:'Creature',original:generatedScope.original,operations:[structuredClone(acknowledged.operation)],pending:null as typeof acknowledged.operation|null,next_offset:null};
 let o=structuredClone(opened),blocked=false;
 if(fault==='draft')o.draft_id='other';if(fault==='world')o.world_id='other';
 if(fault==='original-digest')h.original={...h.original,definition_digest:'sha256:'+'c'.repeat(64)};
 if(fault==='result-digest')o.locator={...o.locator,definition_digest:'sha256:'+'c'.repeat(64)};
 if(fault==='base')h.operations[0].base={...h.operations[0].base,revision_id:'missing'};
 if(fault==='pending')h.pending={...h.operations[0],state:'outcome_unknown'};
 if(fault==='dirty')blocked=true;
 if(fault==='cycle')h.operations[0].base=locator;
 if(fault==='foreign-statblock'){o.locator={...o.locator,statblock_id:'other'};h.operations[0].result=o.locator;}
 expect(generatedMechanicsReading(generatedScope,o,h,null,blocked)?.observation).toBeUndefined();
});
it('proves complete multi-operation lineage and refuses a missing ancestor',()=>{
 const mid={...locator,revision_id:'middle',definition_digest:'sha256:'+'d'.repeat(64)};
 const h={world_id:'world',draft_id:'draft',name:'Creature',original:generatedScope.original,operations:[{...acknowledged.operation,operation_id:'first',result:mid},{...acknowledged.operation,operation_id:'second',base:mid}],pending:null,next_offset:null};
 expect(generatedMechanicsReading(generatedScope,opened,h,null,false)?.observation?.proof).toMatchObject({lineage:[{operationId:'first'},{operationId:'second'}]});
 h.operations.shift();expect(generatedMechanicsReading(generatedScope,opened,h,null,false)?.observation).toBeUndefined();
});
it('fresh credit requires exact dispatch scope; revisiting verified history remains existing',()=>{
 const h={world_id:'world',draft_id:'draft',name:'Creature',original:generatedScope.original,operations:[acknowledged.operation],pending:null,next_offset:null};
 const ack={scope:generatedScope,dispatchScope:null,operation:acknowledged.operation};
 expect(generatedMechanicsReading(generatedScope,opened,h,ack,false)?.observation?.origin).toBe('acknowledged');
 for(const changed of [{...generatedScope,dispatchRevision:4},{...generatedScope,walkthroughId:'new'},{...generatedScope,plan:{...scope.plan,revision:3,revisionId:'work-3'}}])expect(generatedMechanicsReading(changed,opened,h,ack,false)?.observation?.origin).toBe('existing');
});
