import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeAll,expect,it,vi} from 'vitest';
import * as api from '../api/liveApi';
import {SelectedWorldProvider} from '../selectedWorld/SelectedWorldContext';
import {WorldGraphLensProvider} from './WorldGraphLensContext';
import {WorldGraphLensProjectionProvider,useWorldGraphLensProjection} from './useWorldGraphLensProjection';
import {LoadedWorldGraphExplorer} from './LoadedWorldGraphExplorer';
import type {NativeGraphCatalog} from '../api/nativeGraphInspection';

beforeAll(()=>{
 HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','')};
 HTMLDialogElement.prototype.close=function(){this.removeAttribute('open')};
});
afterEach(()=>{cleanup();vi.restoreAllMocks();api.setNativeGraphAccessToken(null)});
function Observer(){const value=useWorldGraphLensProjection();return <output data-testid="resource-state">{value.projectionState}</output>}
const packet:NativeGraphCatalog={schema:'dmb_native_graph_catalog_v1',scope:{managed_world_id:'demand-world',native_world_id:'native-world',binding_version:1,revision_id:'r1',scope_mode:'world',campaign_id:null},
 catalogue:{identity:{space_id:'native-world',revision_id:'r1'},entities:[{entity_id:'e1'}],admitted_assertion_ids:[],completeness:{status:'partial',reason:'incomplete'},request_sha256:'hash',result_digest:'digest'},assertions:[]};

it('loads only native inspection on demand and never acquires the classic projection',async()=>{
 window.history.replaceState({},'','/?world=demand-world');api.setNativeGraphAccessToken('explorer');
 vi.spyOn(api,'listWorldContainers').mockResolvedValue({schema_version:'dmb_world_container_registry_v1',records:[{schema_version:'dmb_world_container_record_v1',world_id:'demand-world',name:'Demand World',source_root_relpath:'corpus/world',created_at:'2026-01-01'}]} as never);
 const classic=vi.spyOn(api,'postManagedWorldGraphProjection');
 const native=vi.spyOn(api,'getNativeGraphCatalog').mockResolvedValue(packet);
 render(<SelectedWorldProvider locationSnapshot={window.location.href}><WorldGraphLensProvider planCampaignId="demand-world"><WorldGraphLensProjectionProvider defaultCampaignId="demand-world"><Observer/><LoadedWorldGraphExplorer/></WorldGraphLensProjectionProvider></WorldGraphLensProvider></SelectedWorldProvider>);
 const launcher=await screen.findByRole('button',{name:'Explore graph'});
 expect(screen.getByTestId('resource-state')).toHaveTextContent('idle');expect(native).not.toHaveBeenCalled();expect(classic).not.toHaveBeenCalled();
 fireEvent.click(launcher);expect(await screen.findByText(/1 objects.*Partial view/)).toBeInTheDocument();
 expect(screen.getByRole('dialog',{name:'Demand World World graph'})).toBeVisible();
 expect(native).toHaveBeenCalledTimes(1);expect(native).toHaveBeenLastCalledWith({managed_world_id:'demand-world',scope_mode:'world',campaign_id:null},expect.any(AbortSignal));
 expect(classic).not.toHaveBeenCalled();expect(screen.getByTestId('resource-state')).toHaveTextContent('idle');
 fireEvent.click(screen.getByRole('button',{name:'Close graph'}));expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 fireEvent.click(launcher);await waitFor(()=>expect(native).toHaveBeenCalledTimes(2));
 expect(classic).not.toHaveBeenCalled();expect(screen.getByTestId('resource-state')).toHaveTextContent('idle');
});
