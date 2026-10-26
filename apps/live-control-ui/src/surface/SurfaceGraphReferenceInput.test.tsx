import {fireEvent,render,screen} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import type {AuthoredGraphReferenceV1,WorldGraphProjection} from '../api/types';
import {SurfaceGraphReferenceInput} from './SurfaceGraphReferenceInput';
const mocks=vi.hoisted(()=>({graph:vi.fn(),demand:vi.fn(),open:vi.fn()}));
vi.mock('../graphLens/useWorldGraphLensProjection',()=>({useOptionalWorldGraphLensProjection:mocks.graph,useWorldGraphLensProjectionDemand:mocks.demand}));
vi.mock('../agentInteraction/AgentInteractionProvider',()=>({useAgentInteraction:()=>({openGraphReference:mocks.open})}));
let projection:WorldGraphProjection;
beforeEach(()=>{vi.clearAllMocks();projection={schema:'dmb_world_graph_projection_v1',snapshot:{worldId:'native',campaignId:'',revisionId:'rev-a',headRevisionId:'rev-a',isHead:true,scopeMode:'world',focus:{kind:'none',sessionId:null},admissibility:'gm'},nodes:[{nodeId:'first-box',label:'Cedar box',kind:'object',role:'match',aliases:[],sourceDomains:[],anchoredToFocusSession:false,evidenceBadges:[],adjacency:[],suggestedExpansions:[],evidenceRefIds:[],sourceArtifactIds:[]},{nodeId:'second-box',label:'Cedar box',kind:'object',role:'match',aliases:[],sourceDomains:[],anchoredToFocusSession:false,evidenceBadges:[],adjacency:[],suggestedExpansions:[],evidenceRefIds:[],sourceArtifactIds:[]}],relationships:[],attributes:[],evidence:[],sourceArtifacts:[],diagnostics:[],summary:{nodeCount:2,relationshipCount:0,attributeCount:0,evidenceCount:0,sourceArtifactCount:0,projectionTruncated:false}};mocks.graph.mockReturnValue({projection,projectionState:'ready',projectionError:null,managedBinding:{managedWorldId:'quarry',nativeWorldId:'native',bindingVersion:3}});});
it('selects exact node identity from duplicate labels without inserting into the page',()=>{
 const change=vi.fn();render(<SurfaceGraphReferenceInput worldId="quarry" value={[]} onChange={change}/>);
 fireEvent.click(screen.getByRole('button',{name:'@ Reference'}));
 expect(mocks.demand).toHaveBeenLastCalledWith(true);
 expect(screen.queryByRole('button',{name:'Insert chip'})).toBeNull();
 fireEvent.click(screen.getAllByRole('button',{name:'Use as context'})[1]);
 expect(change).toHaveBeenCalledWith([{schema:'dmb_authored_graph_reference_v1',managed_world_id:'quarry',native_world_id:'native',binding_version:3,graph_revision:'rev-a',node_id:'second-box',label:'Cedar box'}]);
});
it('opens the existing inspector without treating View as selection',()=>{
 const change=vi.fn();render(<SurfaceGraphReferenceInput worldId="quarry" value={[]} onChange={change}/>);
 fireEvent.click(screen.getByRole('button',{name:'@ Reference'}));fireEvent.click(screen.getAllByRole('button',{name:'View'})[0]);
 expect(mocks.open).toHaveBeenCalledWith(expect.objectContaining({resolution:expect.objectContaining({graphNodeId:'first-box',graphScope:expect.objectContaining({worldId:'native',revisionId:'rev-a'})})}));expect(change).not.toHaveBeenCalled();
});
it('retains selected chips while a foreign or missing binding blocks new selections',()=>{
 mocks.graph.mockReturnValue({projection,projectionState:'ready',managedBinding:null});
 const ref:AuthoredGraphReferenceV1={schema:'dmb_authored_graph_reference_v1',managed_world_id:'quarry',native_world_id:'native',binding_version:3,graph_revision:'rev-a',node_id:'first-box',label:'Cedar box'},change=vi.fn();
 render(<SurfaceGraphReferenceInput worldId="quarry" value={[ref]} onChange={change}/>);
 fireEvent.click(screen.getByRole('button',{name:'@ Reference'}));expect(screen.getByRole('alert')).toHaveTextContent('no verified binding');expect(screen.queryByRole('button',{name:'Use as context'})).toBeNull();expect(screen.getByText('@Cedar box')).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Remove reference Cedar box'}));expect(change).toHaveBeenCalledWith([]);
});
