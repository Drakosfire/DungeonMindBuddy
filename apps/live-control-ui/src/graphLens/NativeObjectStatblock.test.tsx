import {act,cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {NativeObjectStatblock} from './NativeObjectStatblock';
import {listWorldMechanicsAssociations} from '../api/liveApi';
import type {WorldMechanicsAssociation} from '../api/worldMechanicsTypes';
import type {InspectionPin} from '../api/nativeGraphInspection';
const opened=vi.hoisted(()=>vi.fn());
vi.mock('../api/liveApi',()=>({listWorldMechanicsAssociations:vi.fn()}));
vi.mock('../statblocks/SavedStatblockSession',()=>({SavedStatblockButton:({worldId,draftId,revisionId,label}:any)=><button onClick={()=>opened({worldId,draftId,revisionId})}>{label}</button>}));
const pin:InspectionPin={managed_world_id:'world',native_world_id:'native',binding_version:3,revision_id:'current-graph',scope_mode:'world',campaign_id:null};
function record(id:string,campaign:string|null=null):WorldMechanicsAssociation{return {association_id:id,version:1,previous_association_id:null,request_digest:'digest',actor:'gm',created_at:'now',request:{request_id:id,draft_id:'saved-draft',expected_draft_version:2,expected_version:0,target:{managed_world_id:'world',native_world_id:'native',binding_version:3,graph_revision_id:'linked-graph',node_id:'ooze',label:'Ooze',kind:'creature',role:'',campaign_scope:campaign}},proof:{locator:{provider:'dungeonmind',statblock_id:'sb',revision_id:'portrait-version',contract:'dungeonbuddy.statblock',contract_version:'1',definition_digest:'digest'},acceptance_operation_id:'operation',accepted_from_draft_version:1,accepted_from_candidate_id:null,acceptance_request_digest:'digest'}};}
afterEach(cleanup);beforeEach(()=>{vi.resetAllMocks();vi.mocked(listWorldMechanicsAssociations).mockResolvedValue([]);});
it('opens the associated saved portrait version through the shared owner, never latest',async()=>{
 vi.mocked(listWorldMechanicsAssociations).mockResolvedValue([record('link')]);render(<NativeObjectStatblock pin={pin} entityId="ooze"/>);
 fireEvent.click(await screen.findByRole('button',{name:'Preview and edit statblock'}));expect(opened).toHaveBeenCalledWith({worldId:'world',draftId:'saved-draft',revisionId:'portrait-version'});
 expect(screen.getByRole('link',{name:'Open full statblock'})).toHaveAttribute('href','/statblock?world=world&draft=saved-draft&revision=portrait-version');expect(screen.getByText('Linked at Graph revision: linked-graph')).toBeInTheDocument();
});
it('keeps campaign links distinct and rejects foreign World, binding and entity matches',async()=>{
 const invalid=['managed_world_id','native_world_id','binding_version','node_id'].map(field=>{const row=record(field);Object.assign(row.request.target,{[field]:field==='binding_version'?2:'foreign'});return row;});
 vi.mocked(listWorldMechanicsAssociations).mockResolvedValue([...invalid,record('world'),record('a','c1'),record('b','c2')]);
 const view=render(<NativeObjectStatblock pin={pin} entityId="ooze"/>);await screen.findByRole('region',{name:'Statblock · c2'});expect(screen.getAllByRole('button',{name:'Preview and edit statblock'})).toHaveLength(3);
 view.rerender(<NativeObjectStatblock pin={{...pin,scope_mode:'campaign',campaign_id:'c1'}} entityId="ooze"/>);await screen.findByRole('region',{name:'Statblock · c1'});expect(screen.queryByRole('region',{name:'Statblock · c2'})).toBeNull();expect(screen.getAllByRole('button',{name:'Preview and edit statblock'})).toHaveLength(2);
});
it('discards delayed reads when the binding changes and supports explicit failure recovery',async()=>{
 let finish!:(v:WorldMechanicsAssociation[])=>void;vi.mocked(listWorldMechanicsAssociations).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve}));
 const view=render(<NativeObjectStatblock pin={pin} entityId="ooze"/>);
 vi.mocked(listWorldMechanicsAssociations).mockRejectedValueOnce(new Error('Admission unavailable'));view.rerender(<NativeObjectStatblock pin={{...pin,binding_version:4}} entityId="ooze"/>);
 expect(await screen.findByRole('alert')).toHaveTextContent('Admission unavailable');await act(async()=>finish([record('old')]));expect(screen.queryByRole('link')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Retry linked statblocks'}));await screen.findByText('No statblock linked in this view.');expect(within(screen.getByRole('region',{name:'Linked statblocks'})).queryByRole('alert')).toBeNull();
});
