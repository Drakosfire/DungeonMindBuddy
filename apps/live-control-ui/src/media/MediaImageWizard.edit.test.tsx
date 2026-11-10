import {act, cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {MediaImageWizard, type ImageGenerationPort, type MediaRecord} from './MediaImageWizard';
import * as api from '../api/liveApi';
const tour = vi.hoisted(() => ({inspect:vi.fn(), generated:vi.fn(), placed:vi.fn(), captureScope:()=>null}));
vi.mock('../guidedTour/ImageObservations', () => ({useTourImage:()=>tour}));
vi.mock('./SavedMediaImage', () => ({SavedMediaImage:()=> <span>Candidate preview</span>}));
vi.mock('./OriginalImageDownload', () => ({OriginalImageDownload:()=> <span>Original download</span>}));
const parent = 'ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
const child = 'bc6c15cc-8c68-4732-8ae2-d9f3f051393a';
const record = (id:string):MediaRecord => ({asset_id:id, state:'staged', mime_type:'image/png', data_url:'data:image/png;base64,iVBORw0KGgo=', created_at:'2026-11-10T12:00:00Z', provenance:{prompt:id === child ? 'Edited artwork' : 'Original artwork', model:'flux-2-pro'}});
let generation = 0;
beforeEach(() => {
  generation = 0; localStorage.clear(); vi.clearAllMocks();
  vi.spyOn(api, 'getNativeGraphAccessGeneration').mockImplementation(()=>generation);
  vi.spyOn(api, 'authenticatedApiFetch').mockImplementation(async path => ({csrf:null, requestEpoch:generation, response:Response.json(path.endsWith('/regenerate')
    ? {asset_id:child, parent_asset_id:parent, state:'staged', model:'flux-2-pro'}
    : {asset_id:path.includes(child) ? child : parent, state:'staged', content_sha256:'a'.repeat(64)})}));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
async function setup(modal=false) {
  const port:ImageGenerationPort = {capabilities:vi.fn().mockResolvedValue({configured:true, library_ready:true, storage_configured:true, models:[{id:'flux-2-pro', label:'FLUX 2 Pro', formats:['png'], controls:[]}]}),
    list:vi.fn().mockResolvedValue({items:[record(parent)]}), get:vi.fn(async id=>record(id)), save:vi.fn(), generate:vi.fn()};
  const choose = vi.fn();
  const wizard = <MediaImageWizard port={port} onClose={()=>{}} onChoose={choose} selectionOnly={modal}/>;
  const view = render(modal ? <dialog open aria-label="Statblock portrait">{wizard}</dialog> : wizard);
  await waitFor(()=>expect(screen.getByRole('button',{name:'Image library'})).toBeEnabled());
  fireEvent.click(screen.getByRole('button',{name:'Image library'}));
  fireEvent.click(await screen.findByRole('button',{name:'Original artwork · Not yet on CDN'}));
  await screen.findByAltText('Original artwork');
  expect(screen.getByRole('toolbar',{name:'Image Studio controls'})).toContainElement(screen.getByRole('button',{name:'Edit image'}));
  fireEvent.click(screen.getByRole('button',{name:'Edit image'}));
  await waitFor(()=>expect(screen.getByLabelText('Instructions')).toBeEnabled());
  return {port, choose, view};
}
async function candidate(mode:string) {
  fireEvent.change(screen.getByLabelText('Action'),{target:{value:mode}});
  fireEvent.change(screen.getByLabelText('Instructions'),{target:{value:'Bring out the old stonework.'}});
  fireEvent.click(screen.getByRole('button',{name:'Generate',exact:true}));
  await screen.findByRole('button',{name:'Use this version'});
}
it.each(['image_to_image','new'])('reuses %s editing and adopts only the preview until explicit placement',async mode=>{
  const {port, choose}=await setup(); await candidate(mode);
  expect(choose).not.toHaveBeenCalled(); expect(screen.getByAltText('Original artwork')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Use this version'}));
  await screen.findByAltText('Edited artwork');
  expect(screen.queryByRole('dialog',{name:'Edit image'})).not.toBeInTheDocument();
  const fetcher=vi.mocked(api.authenticatedApiFetch);
  const call=fetcher.mock.calls.find(([path])=>path.endsWith('/regenerate'))!;
  expect(JSON.parse(String(call[1]?.body))).toEqual({mode,instructions:'Bring out the old stonework.',expected_content_sha256:'a'.repeat(64)});
  expect(port.save).not.toHaveBeenCalled(); expect(port.generate).not.toHaveBeenCalled(); expect(choose).not.toHaveBeenCalled(); expect(tour.placed).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Place on page'}));
  await waitFor(()=>expect(choose).toHaveBeenCalledWith(expect.objectContaining({asset_id:child,state:'staged'}),expect.anything(),expect.objectContaining({mode:'click'})));
});
it('keeps the original and candidate available when the preview read fails',async()=>{
  const {port}=await setup(); await candidate('image_to_image');
  vi.mocked(port.get).mockRejectedValueOnce(new Error('Preview unavailable'));
  fireEvent.click(screen.getByRole('button',{name:'Use this version'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Preview unavailable');
  expect(screen.getByAltText('Original artwork')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Use this version'}));
  await screen.findByAltText('Edited artwork');
  expect(vi.mocked(api.authenticatedApiFetch).mock.calls.filter(([path])=>path.endsWith('/regenerate'))).toHaveLength(1);
});
it('rejects a late preview read after library navigation',async()=>{
  const {port}=await setup(); await candidate('image_to_image');
  let finish!:(record:MediaRecord)=>void;
  vi.mocked(port.get).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  fireEvent.click(screen.getByRole('button',{name:'Use this version'}));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Checking image…'})).toBeDisabled());
  fireEvent.click(screen.getByRole('button',{name:'Image library'}));
  await screen.findByRole('heading',{name:'Your images'});
  await act(async()=>finish(record(child)));
  expect(screen.queryByAltText('Edited artwork')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Back to studio'}));
  expect(screen.getByAltText('Original artwork')).toBeInTheDocument();
  expect(tour.placed).not.toHaveBeenCalled();
});
it('does not adopt a candidate after access changes during the preview read',async()=>{
  const {port}=await setup(); await candidate('image_to_image');
  let finish!:(record:MediaRecord)=>void;
  vi.mocked(port.get).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  fireEvent.click(screen.getByRole('button',{name:'Use this version'}));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Checking image…'})).toBeDisabled());
  act(()=>{generation++;window.dispatchEvent(new Event(api.NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT));});
  await act(async()=>finish(record(child)));
  expect(screen.getByAltText('Original artwork')).toBeInTheDocument();
  expect(screen.queryByAltText('Edited artwork')).not.toBeInTheDocument();
  expect(tour.placed).not.toHaveBeenCalled();
});

it('keeps portrait edit controls inside their native modal owner',async()=>{
  await setup(true);
  const menu=screen.getByRole('dialog',{name:'Edit image'});
  expect(screen.getByRole('dialog',{name:'Statblock portrait'})).toContainElement(menu);
  expect(menu).toContainElement(screen.getByLabelText('Instructions'));
  fireEvent.change(screen.getByLabelText('Action'),{target:{value:'new'}});
  fireEvent.change(screen.getByLabelText('Instructions'),{target:{value:'A fresh portrait.'}});
  expect(screen.getByRole('button',{name:'Generate',exact:true})).toBeEnabled();
  fireEvent.keyDown(menu,{key:'Escape'});
  expect(screen.queryByRole('dialog',{name:'Edit image'})).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Edit image'})).toHaveFocus();
});
