import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeAll,expect,it,vi} from 'vitest';
import * as api from '../api/liveApi';
import {SelectedWorldProvider} from '../selectedWorld/SelectedWorldContext';
import {WorldGraphLensProvider} from './WorldGraphLensContext';
import {WorldGraphLensProjectionProvider,useWorldGraphLensProjection} from './useWorldGraphLensProjection';
import {LoadedWorldGraphExplorer} from './LoadedWorldGraphExplorer';
import type {ManagedWorldGraphProjectionResponse} from '../api/types';

beforeAll(()=>{
 HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','')};
 HTMLDialogElement.prototype.close=function(){this.removeAttribute('open')};
});
afterEach(()=>{cleanup();vi.restoreAllMocks();api.setNativeGraphAccessToken(null)});
function Observer(){const value=useWorldGraphLensProjection();return <output data-testid="resource-state">{value.projectionState}</output>}
const packet:ManagedWorldGraphProjectionResponse={schema:'dmb_managed_world_graph_projection_v1',managedWorldId:'demand-world',nativeWorldId:'native-world',bindingVersion:1,
 projection:{schema:'dmb_world_graph_projection_v1',snapshot:{worldId:'native-world',campaignId:'',revisionId:'r1',headRevisionId:'r1',isHead:true,focus:{kind:'none',sessionId:null},scopeMode:'world',admissibility:'gm'},
 summary:{nodeCount:0,relationshipCount:0,attributeCount:0,evidenceCount:0,sourceArtifactCount:0,projectionTruncated:true},nodes:[],relationships:[],attributes:[],evidence:[],sourceArtifacts:[],diagnostics:[]}};

it('opens from idle, loads only on user demand, releases on dialog close and preserves partial coverage',async()=>{
 window.history.replaceState({},'','/?world=demand-world');api.setNativeGraphAccessToken('explorer');
 vi.spyOn(api,'listWorldContainers').mockResolvedValue({schema_version:'dmb_world_container_registry_v1',records:[{schema_version:'dmb_world_container_record_v1',world_id:'demand-world',name:'Demand World',source_root_relpath:'corpus/world',created_at:'2026-01-01'}]} as never);
 const load=vi.spyOn(api,'postManagedWorldGraphProjection').mockResolvedValue(packet);
 render(<SelectedWorldProvider locationSnapshot={window.location.href}><WorldGraphLensProvider planCampaignId="demand-world"><WorldGraphLensProjectionProvider defaultCampaignId="demand-world"><Observer/><LoadedWorldGraphExplorer/></WorldGraphLensProjectionProvider></WorldGraphLensProvider></SelectedWorldProvider>);
 const launcher=await screen.findByRole('button',{name:'Explore graph'});
 expect(launcher).toBeEnabled();expect(screen.getByTestId('resource-state')).toHaveTextContent('idle');expect(load).not.toHaveBeenCalled();
 fireEvent.click(launcher);await waitFor(()=>expect(screen.getByTestId('resource-state')).toHaveTextContent('ready'));
 expect(screen.getByRole('dialog',{name:'Demand World loaded graph'})).toBeVisible();expect(screen.getByText(/projection is truncated/)).toBeInTheDocument();expect(load).toHaveBeenCalledTimes(1);
 fireEvent.click(screen.getByRole('button',{name:'Close graph'}));
 expect(screen.getByTestId('resource-state')).toHaveTextContent('idle');expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 fireEvent.click(launcher);await waitFor(()=>expect(load).toHaveBeenCalledTimes(2));
 await act(async()=>{});
 expect(screen.getByTestId('resource-state')).toHaveTextContent('ready');
});
