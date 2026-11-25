import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import * as api from '../api/liveApi';
import * as variantApi from '../api/conversationDraftApi';
import fixture from '../../../../tests/fixtures/statblocks/v1/exact-revision-response.json';
import type {OpenSavedMechanicsVersion} from './revision/savedMechanicsRevisionTypes';
import {SavedStatblockFullView,StatblockPage} from './StatblockPage';
vi.mock('../api/liveApi',()=>({getThreatDraft:vi.fn(),openSavedMechanicsVersion:vi.fn(),listSavedMechanicsVersions:vi.fn(),saveMechanicsRevision:vi.fn()}));
vi.mock('../api/conversationDraftApi',()=>({openSavedConversationVariant:vi.fn(),saveConversationVariantPortrait:vi.fn()}));
vi.mock('../media/DeferredMediaImageWizard',()=>({DeferredMediaImageWizard:({onChoose}:{
 onChoose:(image:{asset_id:string},result:undefined,placement:{signal:AbortSignal})=>void;
})=><button onClick={()=>onChoose(
 {asset_id:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'},undefined,{signal:new AbortController().signal}
)}>Choose saved test portrait</button>}));
vi.mock('../media/SavedMediaImage',()=>({SavedMediaImage:()=>null}));
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

it('places the retained PDF portrait inside the left column of the saved statblock', async () => {
 const saved = packet();
 saved.resource.asset_bindings = [];
 saved.pdf_portrait = 'retained-jpeg';
 vi.mocked(api.openSavedMechanicsVersion).mockResolvedValueOnce(saved);
 const {container} = render(<SavedStatblockFullView target={target}/>);
 const portrait = await screen.findByRole('img', {name: `Source artwork for ${fixture.definition.identity.name}`});
 expect(portrait).toHaveAttribute('src', 'data:image/jpeg;base64,retained-jpeg');
 expect(container.querySelector('.statblock-campaign-grid > .statblock-campaign-col')).toContainElement(portrait);
});

it('retains the exact portrait command until the new revision reopens',async()=>{
 const review='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
 const url=`/statblock?world=test-world&conversation=${review}&turn=${review}&variantReview=${review}`;
 window.history.replaceState({},'',url);
 const {locator,resource}=packet();
 const illustrated={...locator,revision_id:'rev_portrait'};
 vi.mocked(variantApi.openSavedConversationVariant)
  .mockResolvedValueOnce({locator,revision:resource})
  .mockRejectedValueOnce(new Error('Revision temporarily unavailable'))
  .mockResolvedValue({locator:illustrated,revision:{...resource,revision_id:illustrated.revision_id}});
 vi.mocked(variantApi.saveConversationVariantPortrait).mockResolvedValue(illustrated);
 render(<StatblockPage/>);
 const picker=await screen.findByRole('button',{name:'Generate or choose portrait'});
 await waitFor(()=>expect(picker).toBeEnabled());
 fireEvent.click(picker);
 fireEvent.click(await screen.findByRole('button',{name:'Choose saved test portrait'}));
 fireEvent.click(await screen.findByRole('button',{name:'Save new portrait version'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Revision temporarily unavailable');
 const command=vi.mocked(variantApi.saveConversationVariantPortrait).mock.calls[0][2];
 expect(command.base).toEqual(locator);
 fireEvent.click(screen.getByRole('button',{name:'Retry portrait Save'}));
 await waitFor(()=>expect(window.location.search).toContain(`variantPortrait=${command.operation_id}`));
 expect(vi.mocked(variantApi.saveConversationVariantPortrait).mock.calls[1][2]).toEqual(command);
 expect(variantApi.openSavedConversationVariant).toHaveBeenLastCalledWith(
  expect.objectContaining({reviewId:review,portraitOperationId:command.operation_id}),review,command.operation_id,
 );
});
