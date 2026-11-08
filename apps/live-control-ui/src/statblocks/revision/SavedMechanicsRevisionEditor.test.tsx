import {GenerationPlanProvider} from '../../guidedTour/GenerationObservations';
import {render,screen,waitFor,cleanup,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import * as api from '../../api/liveApi';
import {SavedMechanicsRevisionEditor} from './SavedMechanicsRevisionEditor';
import {TourEncounterProvider,type TourEncounterScope} from '../../guidedTour/EncounterScope';
import type {TourOwnerReading} from '../../guidedTour/GuidedTour';
const tourReadings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
const generatedBinding=vi.hoisted(()=>({current:null as import('../../guidedTour/protocol').GeneratedMechanicsScope|null}));
vi.mock('../../guidedTour/GuidedTour',()=>({useGuidedTour:()=>({captureScope:()=>null,captureMechanicsScope:()=>generatedBinding.current}),useTourOwnerReading:(reading:TourOwnerReading|null)=>{if(reading)tourReadings.set(reading.step,reading);}}));
import {baseCandidateDefinition} from '../editor/editorFixtures';
import type {OpenSavedMechanicsVersion,RevisionSaveOutcome,SavedMechanicsVersionList} from './savedMechanicsRevisionTypes';
vi.mock('../../api/liveApi',()=>({listSavedMechanicsVersions:vi.fn(),openSavedMechanicsVersion:vi.fn(),saveMechanicsRevision:vi.fn(),recoverMechanicsRevision:vi.fn(),inspectMechanicsRevision:vi.fn(),validateStatblockDefinition:vi.fn()}));
const portrait='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const studio=vi.hoisted(()=>({props:null as any}));
vi.mock('../../media/MediaImageWizard',()=>({MediaImageWizard:(props:any)=>{
 studio.props=props;
 return <section aria-label="Portrait studio"><p>{props.initialPrompt}</p><button onClick={()=>props.onChoose({asset_id:portrait},null,{signal:new AbortController().signal,mode:'click'})}>Choose saved portrait</button><button onClick={props.onClose}>Close studio</button></section>;
}}));
vi.mock('../../media/SavedMediaImage',()=>({SavedMediaImage:({assetId}:{assetId:string})=><span>Selected asset {assetId}</span>}));
const world='test-world',draft='11111111-1111-4111-8111-111111111111';
const base={provider:'dungeonmind' as const,statblock_id:'sb_one',revision_id:'rev_original',contract:'dungeonmind.dungeonbuddy-statblocks',contract_version:'1.0.0',definition_digest:'sha256:'+'a'.repeat(64)};
const next={...base,revision_id:'rev_next',definition_digest:'sha256:'+'b'.repeat(64)};
const tourScope:TourEncounterScope={plan:{kind:'plan',worldId:world,objectId:'plan',revision:2,revisionId:'work-2',digest:'d'.repeat(64)},sceneId:'scene',encounterId:'encounter'};
let outcome:RevisionSaveOutcome;
function page():SavedMechanicsVersionList{return {world_id:world,draft_id:draft,name:'Keeper',original:base,operations:[],pending:null,next_offset:null};}
function opened(revision=base.revision_id):OpenSavedMechanicsVersion{
  const definition=baseCandidateDefinition();if(revision===next.revision_id)definition.identity.name='Stronger keeper';
  return {world_id:world,draft_id:draft,locator:revision===next.revision_id?next:base,
    resource:{statblock_id:base.statblock_id,revision_id:revision,definition} as OpenSavedMechanicsVersion['resource']};
}
beforeEach(()=>{
  vi.resetAllMocks();generatedBinding.current=null;tourReadings.clear();localStorage.clear();
  outcome={operation_id:'22222222-2222-4222-8222-222222222222',state:'committed',base,result:next,refusal_code:null,change_summary:'Stronger',created_at:'2026-10-22T00:00:00Z'};
  vi.mocked(api.listSavedMechanicsVersions).mockResolvedValue(page());
  vi.mocked(api.openSavedMechanicsVersion).mockImplementation(async(_d,_w,rev)=>opened(rev));
  vi.mocked(api.validateStatblockDefinition).mockResolvedValue({schema:'dmb_statblock_definition_validation_v1',outcome:'success',definition_digest:next.definition_digest,validation_receipt:{status:'valid',issues:[],definition_digest:next.definition_digest}} as Awaited<ReturnType<typeof api.validateStatblockDefinition>>);
});
afterEach(cleanup);
async function load(){await userEvent.click(screen.getByRole('button',{name:'Open saved mechanics'}));await screen.findByLabelText('Creature name');}
async function edit(){const name=screen.getByLabelText('Creature name');await userEvent.clear(name);await userEvent.type(name,'Stronger keeper');}
async function validate(){await userEvent.click(screen.getByRole('button',{name:'Validate new version'}));await waitFor(()=>expect((screen.getByRole('button',{name:'Save new version'}) as HTMLButtonElement).disabled).toBe(false));}

it('validates edited exact source and saves a successor without an encounter mutation',async()=>{
  vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>({...outcome,operation_id:body.operation_id}));
  render(<TourEncounterProvider scope={tourScope}><SavedMechanicsRevisionEditor worldId={world} draftId={draft}/></TourEncounterProvider>);await load();await edit();
  expect((screen.getByRole('button',{name:'Save new version'}) as HTMLButtonElement).disabled).toBe(true);
  await validate();await userEvent.click(screen.getByRole('button',{name:'Save new version'}));
  await screen.findByText('New mechanics version saved. Encounters and World associations are unchanged.');
  expect(within(screen.getByRole('region',{name:'Saved statblock'})).getByRole('heading',{name:'Stronger keeper'})).toBeInTheDocument();
  const [owner,body]=vi.mocked(api.saveMechanicsRevision).mock.calls[0]!;
  expect(owner).toBe(draft);expect(body.base).toEqual(base);expect(body.definition.identity.name).toBe('Stronger keeper');
  expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);expect(api.recoverMechanicsRevision).not.toHaveBeenCalled();
  expect(tourReadings.get('mechanics')?.observation).toMatchObject({origin:'acknowledged',observedAt:outcome.created_at,target:tourScope.plan,proof:{kind:'mechanics',sceneId:'scene',encounterId:'encounter',draftId:draft,operationId:body.operation_id,locator:next}});
});

it('recovers local edits for the same exact source after remount',async()=>{
  const first=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();first.unmount();
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).toBe('Stronger keeper');
  expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});

it('retains an unknown Save across remount and explicitly recovers the original key',async()=>{
  let id='';vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>{id=body.operation_id;throw new Error('lost acknowledgement');});
  vi.mocked(api.inspectMechanicsRevision).mockImplementation(async()=>({operation:{...outcome,operation_id:id,state:'outcome_unknown',result:null}}));
  vi.mocked(api.recoverMechanicsRevision).mockImplementation(async()=>({...outcome,operation_id:id}));
  const first=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();await validate();
  await userEvent.click(screen.getByRole('button',{name:'Save new version'}));await screen.findByText(/Save outcome is unknown/);first.unmount();
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
  expect(screen.getByLabelText('Creature name').matches(':disabled')).toBe(true);
  await userEvent.click(screen.getByRole('button',{name:'Recover Save'}));await screen.findByText('New mechanics version saved. Encounters and World associations are unchanged.');
  expect(api.recoverMechanicsRevision).toHaveBeenCalledWith(draft,world,id);expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);
});

it('does not treat an unrelated outcome as this Save acknowledgement',async()=>{
  vi.mocked(api.saveMechanicsRevision).mockResolvedValue({...outcome,operation_id:'other'});
  vi.mocked(api.inspectMechanicsRevision).mockRejectedValue(new Error('unavailable'));
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();await validate();
  await userEvent.click(screen.getByRole('button',{name:'Save new version'}));
  await screen.findByText(/Save outcome could not be checked/);expect(screen.queryByText(/New mechanics version saved/)).toBeNull();
  expect((screen.getByRole('button',{name:'Save new version'}) as HTMLButtonElement).disabled).toBe(true);
});


it('pages history metadata without rereading mechanics or replacing dirty edits',async()=>{
  vi.mocked(api.listSavedMechanicsVersions).mockResolvedValueOnce({...page(),next_offset:50}).mockResolvedValue(page());
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();
  await userEvent.click(screen.getByRole('button',{name:'More saved versions'}));
  await waitFor(()=>expect(api.listSavedMechanicsVersions).toHaveBeenCalledWith(draft,world,50));
  expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).toBe('Stronger keeper');
});

it('keeps independent browser writers from overwriting each other’s recovered edits',async()=>{
  const first=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();
  const firstWriter=sessionStorage.getItem('dmb-manual-mechanics-writer')!;first.unmount();sessionStorage.removeItem('dmb-manual-mechanics-writer');
  const second=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).not.toBe('Stronger keeper');
  second.unmount();sessionStorage.setItem('dmb-manual-mechanics-writer',firstWriter);
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).toBe('Stronger keeper');
});

it('does not unlock an absent Save until explicit recovery fences the original request',async()=>{
  vi.mocked(api.saveMechanicsRevision).mockRejectedValue(new Error('request interrupted'));
  vi.mocked(api.inspectMechanicsRevision).mockResolvedValue({operation:null});
  vi.mocked(api.recoverMechanicsRevision).mockResolvedValue(null);
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();await validate();
  await userEvent.click(screen.getByRole('button',{name:'Save new version'}));
  await screen.findByText(/Save has no durable result yet/);
  expect(screen.getByLabelText('Creature name').matches(':disabled')).toBe(true);
  await userEvent.click(screen.getByRole('button',{name:'Recover Save'}));
  await screen.findByText(/Save was safely canceled before dispatch/);
  expect(screen.getByLabelText('Creature name').matches(':disabled')).toBe(false);
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).toBe('Stronger keeper');
});

it('reports unavailable validation without blaming or discarding edited mechanics',async()=>{
  vi.mocked(api.validateStatblockDefinition).mockResolvedValue({schema:'dmb_statblock_definition_validation_v1',outcome:'failure',failure_category:'downstream_timeout',failure_message:'timeout'});
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();
  await userEvent.click(screen.getByRole('button',{name:'Validate new version'}));
  await screen.findByText('Mechanics validation is unavailable. Your edits are retained; try again when it is available.');
  expect((screen.getByLabelText('Creature name') as HTMLInputElement).value).toBe('Stronger keeper');
  expect(screen.getByLabelText('Creature name').matches(':disabled')).toBe(false);
  expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});


it('shows actionable producer issues and clears them when mechanics change',async()=>{
  vi.mocked(api.validateStatblockDefinition).mockResolvedValue({schema:'dmb_statblock_definition_validation_v1',outcome:'success',validation_receipt:{status:'invalid',issues:[{code:'HP_DISPLAYED_AVERAGE_MISMATCH',severity:'error',field_path:'vitality.hit_points.displayed_average',message:'Displayed HP average does not match the typed dice formula.'}]}} as Awaited<ReturnType<typeof api.validateStatblockDefinition>>);
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
  await userEvent.click(screen.getByRole('button',{name:'Validate new version'}));
  expect((await screen.findByRole('list',{name:'Mechanics validation issues'})).textContent).toContain('Displayed HP average does not match the typed dice formula.');
  expect(screen.getByRole('list',{name:'Mechanics validation issues'}).textContent).toContain('vitality.hit_points.displayed_average');
  expect(api.saveMechanicsRevision).not.toHaveBeenCalled();await edit();
  expect(screen.queryByRole('list',{name:'Mechanics validation issues'})).toBeNull();
});

it('standalone saved editor observes the generated creature manual successor without changing any encounter',async()=>{
 generatedBinding.current={plan:tourScope.plan,walkthroughId:'tour',draftId:draft,acceptOperationId:'accept',original:base,dispatchRevision:4};
 vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>({...outcome,operation_id:body.operation_id}));
 render(<GenerationPlanProvider pin={tourScope.plan}><SavedMechanicsRevisionEditor worldId={world} draftId={draft}/></GenerationPlanProvider>);await load();await edit();await validate();
 await userEvent.click(screen.getByRole('button',{name:'Save new version'}));await screen.findByText('New mechanics version saved. Encounters and World associations are unchanged.');
 expect(tourReadings.get('mechanics')?.observation).toMatchObject({origin:'acknowledged',target:tourScope.plan,proof:{kind:'generated-mechanics-revision',scope:generatedBinding.current,lineage:[{base,locator:next}]}});
 expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);expect(api.openSavedMechanicsVersion).toHaveBeenLastCalledWith(draft,world,next.revision_id);
});
it('standalone editor inspects the existing successor without another Save',async()=>{
 generatedBinding.current={plan:tourScope.plan,walkthroughId:'tour',draftId:draft,acceptOperationId:'accept',original:base,dispatchRevision:4};
 vi.mocked(api.listSavedMechanicsVersions).mockResolvedValue({...page(),operations:[outcome]});
 render(<GenerationPlanProvider pin={tourScope.plan}><SavedMechanicsRevisionEditor worldId={world} draftId={draft}/></GenerationPlanProvider>);await load();
 await userEvent.selectOptions(screen.getByRole('combobox',{name:'Saved mechanics version'}),next.revision_id);
 await waitFor(()=>expect(tourReadings.get('mechanics')?.observation?.origin).toBe('existing'));
 expect(api.saveMechanicsRevision).not.toHaveBeenCalled();expect(api.recoverMechanicsRevision).not.toHaveBeenCalled();
});
it('standalone unknown-save recovery verifies the retained result without another Save',async()=>{
 generatedBinding.current={plan:tourScope.plan,walkthroughId:'tour',draftId:draft,acceptOperationId:'accept',original:base,dispatchRevision:4};
 let id='';vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>{id=body.operation_id;return {...outcome,operation_id:id,state:'outcome_unknown',result:null};});
 vi.mocked(api.recoverMechanicsRevision).mockImplementation(async()=>({...outcome,operation_id:id}));
 render(<GenerationPlanProvider pin={tourScope.plan}><SavedMechanicsRevisionEditor worldId={world} draftId={draft}/></GenerationPlanProvider>);await load();await edit();await validate();await userEvent.click(screen.getByRole('button',{name:'Save new version'}));await screen.findByText(/Save outcome is unknown/);
 expect(tourReadings.get('mechanics')?.observation).toBeUndefined();
 await userEvent.click(screen.getByRole('button',{name:'Recover Save'}));await screen.findByText('New mechanics version saved. Encounters and World associations are unchanged.');
 expect(tourReadings.get('mechanics')?.observation?.origin).toBe('acknowledged');expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);
});

it('does not transfer an interrupted generated Save acknowledgement after guidance changes',async()=>{
 generatedBinding.current={plan:tourScope.plan,walkthroughId:'tour',draftId:draft,acceptOperationId:'accept',original:base,dispatchRevision:4};
 let id='';vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>{id=body.operation_id;return {...outcome,operation_id:id,state:'outcome_unknown',result:null};});
 vi.mocked(api.recoverMechanicsRevision).mockImplementation(async()=>{vi.mocked(api.listSavedMechanicsVersions).mockResolvedValue({...page(),operations:[{...outcome,operation_id:id}]});return {...outcome,operation_id:id};});
 const mounted=render(<GenerationPlanProvider pin={tourScope.plan}><SavedMechanicsRevisionEditor worldId={world} draftId={draft}/></GenerationPlanProvider>);await load();await edit();await validate();await userEvent.click(screen.getByRole('button',{name:'Save new version'}));await screen.findByText(/Save outcome is unknown/);
 generatedBinding.current={...generatedBinding.current!,dispatchRevision:6};mounted.rerender(<GenerationPlanProvider pin={tourScope.plan}><SavedMechanicsRevisionEditor worldId={world} draftId={draft}/></GenerationPlanProvider>);
 await userEvent.click(screen.getByRole('button',{name:'Recover Save'}));await screen.findByText('New mechanics version saved. Encounters and World associations are unchanged.');
 expect(tourReadings.get('mechanics')?.observation?.origin).toBe('existing');expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);
});


it('renders the exact saved statblock while keeping local edits out of its saved projection',async()=>{
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);
  expect(screen.queryByRole('region',{name:'Saved statblock'})).toBeNull();
  await load();
  const saved=screen.getByRole('region',{name:'Saved statblock'});
  expect(within(saved).getByRole('heading',{name:'Ironhide Brute'})).toBeInTheDocument();
  expect(within(saved).getByRole('table',{name:'Ability scores'})).toBeInTheDocument();
  await edit();
  expect(within(saved).getByRole('heading',{name:'Ironhide Brute'})).toBeInTheDocument();
  expect(within(saved).queryByRole('heading',{name:'Stronger keeper'})).toBeNull();
  expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
  expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});

it('does not show a statblock before a delayed exact read resolves',async()=>{
  let resolve!:(value:OpenSavedMechanicsVersion)=>void;
  vi.mocked(api.openSavedMechanicsVersion).mockImplementationOnce(()=>new Promise(done=>{resolve=done}));
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);
  await userEvent.click(screen.getByRole('button',{name:'Open saved mechanics'}));
  await waitFor(()=>expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1));
  expect(screen.queryByRole('region',{name:'Saved statblock'})).toBeNull();
  resolve(opened());
  expect(await screen.findByRole('region',{name:'Saved statblock'})).toBeInTheDocument();
});

it('does not render a source rejected by the shared response reader',async()=>{
  vi.mocked(api.openSavedMechanicsVersion).mockRejectedValueOnce(new Error('Saved version identity changed.'));
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);
  await userEvent.click(screen.getByRole('button',{name:'Open saved mechanics'}));
  await screen.findByText('Saved version identity changed.');
  expect(screen.queryByRole('region',{name:'Saved statblock'})).toBeNull();
  expect(screen.queryByLabelText('Creature name')).toBeNull();
});

it('keeps the failed read actionable without fabricating a statblock',async()=>{
  vi.mocked(api.openSavedMechanicsVersion).mockRejectedValueOnce(new Error('Exact mechanics unavailable'));
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);
  await userEvent.click(screen.getByRole('button',{name:'Open saved mechanics'}));
  await screen.findByText('Exact mechanics unavailable');
  expect(screen.queryByRole('region',{name:'Saved statblock'})).toBeNull();
  await load();
  expect(screen.getByRole('region',{name:'Saved statblock'})).toBeInTheDocument();
  expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});


it.each(['unavailable','identity'])('keeps a committed Save distinct from a failed successor read (%s)',async failure=>{
  vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>({...outcome,operation_id:body.operation_id}));
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();await validate();
  if(failure==='unavailable')vi.mocked(api.openSavedMechanicsVersion).mockRejectedValueOnce(new Error('Saved successor temporarily unavailable'));
  else vi.mocked(api.openSavedMechanicsVersion).mockRejectedValueOnce(new Error('Saved version identity changed.'));
  await userEvent.click(screen.getByRole('button',{name:'Save new version'}));
  await screen.findByText(failure==='unavailable'?'Saved successor temporarily unavailable':'Saved version identity changed.');
  expect(screen.queryByText('New mechanics version saved. Encounters and World associations are unchanged.')).toBeNull();
  expect(within(screen.getByRole('region',{name:'Saved statblock'})).getByRole('heading',{name:'Ironhide Brute'})).toBeInTheDocument();
  expect(screen.getByLabelText('Creature name')).toBeDisabled();
  await userEvent.click(screen.getByRole('button',{name:'Open saved successor'}));
  await waitFor(()=>expect(within(screen.getByRole('region',{name:'Saved statblock'})).getByRole('heading',{name:'Stronger keeper'})).toBeInTheDocument());
  expect(screen.queryByRole('button',{name:'Open saved successor'})).toBeNull();
  expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);expect(api.recoverMechanicsRevision).not.toHaveBeenCalled();
});

it('retains a committed successor selection through reload after its read fails',async()=>{
  vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>({...outcome,operation_id:body.operation_id}));
  const first=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();await validate();
  vi.mocked(api.openSavedMechanicsVersion).mockRejectedValueOnce(new Error('Saved successor temporarily unavailable'));
  await userEvent.click(screen.getByRole('button',{name:'Save new version'}));await screen.findByText('Saved successor temporarily unavailable');first.unmount();
  render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
  expect(within(screen.getByRole('region',{name:'Saved statblock'})).getByRole('heading',{name:'Stronger keeper'})).toBeInTheDocument();
  expect(api.openSavedMechanicsVersion).toHaveBeenLastCalledWith(draft,world,next.revision_id);expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);
});

it('links the opened saved revision without copying local edits into the full-view target',async()=>{
 render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
 const link=screen.getByRole('link',{name:'Open full saved statblock'}),href=link.getAttribute('href');
 const url=new URL(href!,'http://localhost');expect(url.pathname).toBe('/statblock');
 expect(Object.fromEntries(url.searchParams)).toEqual({world,draft,revision:base.revision_id});
 await userEvent.clear(screen.getByLabelText('Creature name'));await userEvent.type(screen.getByLabelText('Creature name'),'Local only creature');
 expect(link).toHaveAttribute('href',href);expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});

it('keeps the independent original-history join check after shared response admission',async()=>{
 const exact=structuredClone(opened());exact.locator.statblock_id='sb_other';exact.resource.statblock_id='sb_other';
 vi.mocked(api.openSavedMechanicsVersion).mockResolvedValueOnce(exact);render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);
 await userEvent.click(screen.getByRole('button',{name:'Open saved mechanics'}));
 await screen.findByText('Saved version differs from this creature’s history.');expect(screen.queryByRole('region',{name:'Saved statblock'})).toBeNull();
});

async function choosePortrait(){
 await userEvent.click(screen.getByRole('button',{name:'Generate or choose portrait'}));
 expect(studio.props.selectionOnly).toBe(true);expect(studio.props.requireSaved).toBe(true);
 expect(studio.props.initialPrompt).toContain('Portrait of ');
 expect(studio.props.initialPrompt).not.toContain(draft);expect(studio.props.initialPrompt).not.toContain(world);
 await userEvent.click(screen.getByRole('button',{name:'Choose saved portrait'}));
 await screen.findByText(`Selected asset ${portrait}`);
}
it('retains only the portrait UUID with exact-source edits across remount and sends it on explicit Save',async()=>{
 vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>({...outcome,operation_id:body.operation_id}));
 const first=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();await choosePortrait();
 expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
 const key=Object.keys(localStorage).find(k=>k.endsWith(':version:rev_original'))!;
 const record=JSON.parse(localStorage.getItem(key)!);expect(record.schema).toBe('dmb_manual_mechanics_work_v2');expect(record.portraitAssetId).toBe(portrait);
 expect(localStorage.getItem(key)).not.toContain('data:image');
 first.unmount();render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();
 expect(screen.getByText(`Selected asset ${portrait}`)).toBeInTheDocument();expect(screen.getByLabelText('Creature name')).toHaveValue('Stronger keeper');
 await validate();await userEvent.click(screen.getByRole('button',{name:'Save new version'}));
 await screen.findByText(/New mechanics version saved/);
 expect(vi.mocked(api.saveMechanicsRevision).mock.calls[0][1]).toMatchObject({base,portrait_asset_id:portrait});
 expect(screen.queryByText(`Selected asset ${portrait}`)).toBeNull();
});
it('keeps the saved portrait by omitting an unsaved choice rather than removing native bindings',async()=>{
 vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>({...outcome,operation_id:body.operation_id}));
 render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await choosePortrait();
 await userEvent.click(screen.getByRole('button',{name:'Keep saved portrait'}));expect(screen.queryByText(`Selected asset ${portrait}`)).toBeNull();
 await validate();await userEvent.click(screen.getByRole('button',{name:'Save new version'}));await screen.findByText(/New mechanics version saved/);
 expect(vi.mocked(api.saveMechanicsRevision).mock.calls[0][1]).not.toHaveProperty('portrait_asset_id');
});
it('adopts retained V1 mechanical edits without inventing a portrait',async()=>{
 const first=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await edit();first.unmount();
 const key=Object.keys(localStorage).find(k=>k.endsWith(':version:rev_original'))!;
 const record=JSON.parse(localStorage.getItem(key)!);record.schema='dmb_manual_mechanics_work_v1';delete record.portraitAssetId;localStorage.setItem(key,JSON.stringify(record));
 render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();expect(screen.getByLabelText('Creature name')).toHaveValue('Stronger keeper');
 await choosePortrait();expect(JSON.parse(localStorage.getItem(key)!).schema).toBe('dmb_manual_mechanics_work_v2');
});
it('recovers an uncertain portrait Save with its original operation instead of resubmitting',async()=>{
 let id='';vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>{id=body.operation_id;throw new Error('lost acknowledgement');});
 vi.mocked(api.inspectMechanicsRevision).mockImplementation(async()=>({operation:{...outcome,operation_id:id,state:'outcome_unknown',result:null}}));
 vi.mocked(api.recoverMechanicsRevision).mockImplementation(async()=>({...outcome,operation_id:id}));
 const first=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await choosePortrait();await validate();
 await userEvent.click(screen.getByRole('button',{name:'Save new version'}));await screen.findByText(/Save outcome is unknown/);first.unmount();
 render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await userEvent.click(screen.getByRole('button',{name:'Recover Save'}));
 await screen.findByText(/New mechanics version saved/);expect(api.recoverMechanicsRevision).toHaveBeenCalledWith(draft,world,id);
 expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);expect(vi.mocked(api.saveMechanicsRevision).mock.calls[0][1].portrait_asset_id).toBe(portrait);
});

it('rejects an old studio callback after source-version change and keeps choices scoped to the original',async()=>{
 vi.mocked(api.listSavedMechanicsVersions).mockResolvedValue({...page(),operations:[outcome]});
 render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await choosePortrait();
 const previous=studio.props.onChoose;
 await userEvent.selectOptions(screen.getByLabelText('Saved mechanics version'),next.revision_id);
 await waitFor(()=>expect(screen.getByLabelText('Creature name')).toHaveValue('Stronger keeper'));
 expect(screen.queryByText(`Selected asset ${portrait}`)).toBeNull();
 expect(()=>previous({asset_id:portrait},null,{signal:new AbortController().signal,mode:'click'})).toThrow('The source changed');
 await userEvent.selectOptions(screen.getByLabelText('Saved mechanics version'),base.revision_id);
 await screen.findByText(`Selected asset ${portrait}`);
});
it.each(['not-a-uuid',{data_url:'do not accept'}])('retains malformed portrait recovery %j without replacing it or enabling an unverified source',async invalid=>{
 const first=render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await load();await choosePortrait();first.unmount();
 const key=Object.keys(localStorage).find(k=>k.endsWith(':version:rev_original'))!;
 const record=JSON.parse(localStorage.getItem(key)!);record.portraitAssetId=invalid;
 const raw=JSON.stringify(record);localStorage.setItem(key,raw);
 render(<SavedMechanicsRevisionEditor worldId={world} draftId={draft}/>);await userEvent.click(screen.getByRole('button',{name:'Open saved mechanics'}));
 await screen.findByText(/Saved portrait choice could not be verified/);
 expect(localStorage.getItem(key)).toBe(raw);expect(screen.queryByLabelText('Creature name')).toBeNull();expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});
