import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import * as api from '../api/liveApi';
import fixture from '../../../../tests/fixtures/statblocks/v1/exact-revision-response.json';
import type {OpenSavedMechanicsVersion} from './revision/savedMechanicsRevisionTypes';
import {SavedStatblockFullView,StatblockPage} from './StatblockPage';
vi.mock('../api/liveApi',()=>({getThreatDraft:vi.fn(),openSavedMechanicsVersion:vi.fn(),listSavedMechanicsVersions:vi.fn(),saveMechanicsRevision:vi.fn()}));
vi.mock('../chrome/AppChrome',()=>({AppChrome:({children}:{children:React.ReactNode})=><>{children}</>}));
vi.mock('../selectedWorld/SelectedWorldContext',()=>({useSelectedWorld:()=>({kind:'managed',worldId:'test-world'})}));
const target={worldId:'test-world',draftId:'draft-a',revisionId:fixture.revision_id};
const packet=():OpenSavedMechanicsVersion=>({world_id:target.worldId,draft_id:target.draftId,locator:{provider:'dungeonmind',statblock_id:fixture.statblock_id,revision_id:fixture.revision_id,definition_digest:fixture.definition_digest,contract:fixture.contract,contract_version:fixture.contract_version},resource:structuredClone(fixture) as OpenSavedMechanicsVersion['resource']});
beforeEach(()=>{vi.resetAllMocks();localStorage.clear();vi.mocked(api.openSavedMechanicsVersion).mockResolvedValue(packet());});
afterEach(cleanup);
it('reads only the explicit revision despite a different local selected-version hint',async()=>{
 localStorage.setItem('dmb-manual-mechanics:hint:selected','some-other-revision');render(<SavedStatblockFullView target={target}/>);
 await screen.findByRole('heading',{name:fixture.definition.identity.name});
 expect(api.openSavedMechanicsVersion).toHaveBeenCalledExactlyOnceWith(target.draftId,target.worldId,target.revisionId);
 expect(api.listSavedMechanicsVersions).not.toHaveBeenCalled();expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
 expect(screen.queryByLabelText('Creature name')).toBeNull();
 expect(screen.getByRole('button',{name:'Edit this version'})).toBeDisabled();
});
it('keeps read failure explicit and retries the same target',async()=>{
 vi.mocked(api.openSavedMechanicsVersion).mockRejectedValueOnce(new Error('Exact revision unavailable'));render(<SavedStatblockFullView target={target}/>);
 expect(await screen.findByRole('alert')).toHaveTextContent('Exact revision unavailable');fireEvent.click(screen.getByRole('button',{name:'Retry statblock'}));
 await screen.findByRole('heading',{name:fixture.definition.identity.name});expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(2);expect(api.listSavedMechanicsVersions).not.toHaveBeenCalled();
});
it('ignores a delayed previous-target read and hides the prior render immediately',async()=>{
 let finish!:(value:OpenSavedMechanicsVersion)=>void;vi.mocked(api.openSavedMechanicsVersion).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve}));
 const view=render(<SavedStatblockFullView target={target}/>);await waitFor(()=>expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1));
 const next={...target,revisionId:'rev_next'},value=packet();value.locator.revision_id=next.revisionId;value.resource.revision_id=next.revisionId;value.resource.definition.identity.name='Next exact creature';
 vi.mocked(api.openSavedMechanicsVersion).mockResolvedValueOnce(value);view.rerender(<SavedStatblockFullView target={next}/>);await screen.findByRole('heading',{name:'Next exact creature'});
 await act(async()=>finish(packet()));expect(screen.queryByRole('heading',{name:fixture.definition.identity.name})).toBeNull();expect(screen.getByRole('heading',{name:'Next exact creature'})).toBeVisible();
});
it.each(['/statblock?world=foreign&draft=d&revision=r','/statblock?world=test-world&draft=d','/statblock?world=test-world&draft=d&revision=r&revision=s'])(
 'does not read an inadmissible page target %s',url=>{window.history.replaceState({},'',url);render(<StatblockPage/>);expect(screen.getByRole('alert')).toBeInTheDocument();expect(api.openSavedMechanicsVersion).not.toHaveBeenCalled();});

it.each([true,false])('opens creature review for a saved revision on the matching World draft (%s)',async matches=>{
 const current=packet();
 vi.mocked(api.getThreatDraft).mockResolvedValue({
  schema:'dmb_threat_draft_v2',world_id:matches?target.worldId:'foreign',draft_id:target.draftId,version:2,
  workflow_state:'mechanics_saved',accepted_mechanics_ref:{
   ...current.locator,revision_id:'rev_original',
  },
 } as Awaited<ReturnType<typeof api.getThreatDraft>>);
 render(<SavedStatblockFullView target={target}/>);
 const open=await screen.findByRole('button',{name:'Open creature review'});
 expect(api.getThreatDraft).not.toHaveBeenCalled();
 fireEvent.click(open);
 if(matches) expect(await screen.findByRole('button',{name:'Review creature creation'})).toBeInTheDocument();
 else expect(await screen.findByRole('alert')).toHaveTextContent('The saved statblock and creature draft no longer match');
 expect(api.getThreatDraft).toHaveBeenCalledExactlyOnceWith(target.draftId);
});
