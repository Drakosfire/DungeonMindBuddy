import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MediaImageWizard, type ImageGenerationPort } from './MediaImageWizard';
const tourImage=vi.hoisted(()=>({generated:vi.fn(),placed:vi.fn(),captureScope:()=>null}));
vi.mock('../guidedTour/ImageObservations',()=>({useTourImage:()=>tourImage}));
const createUrlDescriptor = Object.getOwnPropertyDescriptor(URL, 'createObjectURL');
const revokeUrlDescriptor = Object.getOwnPropertyDescriptor(URL, 'revokeObjectURL');
beforeEach(() => {
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:original-image') });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });
});
afterEach(() => {
  cleanup();
  for (const [key, descriptor] of [['createObjectURL', createUrlDescriptor], ['revokeObjectURL', revokeUrlDescriptor]] as const) {
    if (descriptor) Object.defineProperty(URL, key, descriptor); else Reflect.deleteProperty(URL, key);
  }
});
beforeEach(()=>{tourImage.generated.mockClear();tourImage.placed.mockClear();});
const createPort = (): ImageGenerationPort => ({ capabilities: vi.fn().mockResolvedValue({ configured: true, library_ready: true, storage_configured: true, models: [
  { id: 'flux-2-pro', label: 'FLUX 2 Pro', formats: ['png', 'jpeg'], controls: ['seed'] },
  { id: 'gpt-image-1.5', label: 'GPT Image 1.5', formats: ['png', 'jpeg', 'webp'], controls: ['quality', 'background'] },
] }), list: vi.fn().mockResolvedValue({ items: [] }), get: vi.fn(), save: vi.fn().mockResolvedValue({ asset_id: 'asset-1', state: 'ready', delivery_url: 'https://imagedelivery.net/test/asset-1/public' }), generate: vi.fn().mockResolvedValue({ images: [{ data_url: 'data:image/png;base64,iVBORw0KGgo=', media_type: 'image/png', asset_id: 'asset-1', state: 'staged' }], prompt: 'Edge', model: 'flux-2-pro' }) });
async function settings(api: ImageGenerationPort) {
  render(<MediaImageWizard onClose={() => {}} port={api} />);
  fireEvent.change(screen.getByRole('textbox', { name: /What would you like/ }), { target: { value: 'Edge' } });

  await screen.findByRole('option', { name: 'FLUX 2 Pro' });
}
describe('MediaImageWizard', () => {
  it('submits only explicit Generate with model-supported controls', async () => {
    const api = createPort(); await settings(api);
    expect(api.generate).not.toHaveBeenCalled();expect(tourImage.generated).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/Seed/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'gpt-image-1.5' } });
    expect(screen.queryByLabelText(/Seed/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Quality'), { target: { value: 'low' } });
    fireEvent.click(screen.getByRole('button', { name: 'Generate image' }));
    await screen.findByRole('link', { name: 'Download image' });
    expect(api.generate).toHaveBeenCalledTimes(1);expect(tourImage.generated).toHaveBeenCalledExactlyOnceWith(['asset-1'],'flux-2-pro',null);
    expect(api.generate).toHaveBeenCalledWith(expect.objectContaining({ options: { quality: 'low', background: 'auto', output_format: 'png' } }));
  });
  it('blocks duplicate submission and retains preview after failure', async () => {
    const api = createPort(); await settings(api);
    fireEvent.click(screen.getByRole('button', { name: 'Generate image' }));
    await screen.findByRole('link', { name: 'Download image' });
    let reject!: (error: Error) => void;
    vi.mocked(api.generate).mockImplementationOnce(() => new Promise((_resolve, fail) => { reject = fail; }));
    const button = screen.getByRole('button', { name: 'Generate another image' });
    fireEvent.click(button); fireEvent.click(button);
    expect(api.generate).toHaveBeenCalledTimes(2);
    expect(screen.getByRole('button', { name: 'Close image studio' })).toBeDisabled();
    reject(new Error('Provider unavailable'));
    await screen.findByRole('alert');
    expect(screen.getByRole('link', { name: 'Download image' })).toBeInTheDocument();
    expect(api.generate).toHaveBeenCalledTimes(2);
  });
  it('saves once and reopens from the library without generation', async () => {
    const api = createPort(); await settings(api);
    fireEvent.click(screen.getByRole('button', { name: 'Generate image' }));
    await screen.findByRole('button', { name: 'Save image' });
    fireEvent.click(screen.getByRole('button', { name: 'Save image' }));
    await screen.findByText('Saved to CDN');
    expect(api.save).toHaveBeenCalledWith('asset-1');
    const record = { asset_id: 'asset-1', state: 'ready', mime_type: 'image/png', data_url: 'data:image/png;base64,original', delivery_url: 'https://imagedelivery.net/test/asset-1/public', created_at: '2026-10-16T00:00:00Z', provenance: { prompt: 'Saved swamp', model: 'flux-2-pro', settings: { width: 1536, height: 1024, options: { seed: 42, output_format: 'png' } } } };
    vi.mocked(api.list).mockResolvedValue({ items: [record] });
    vi.mocked(api.get).mockResolvedValue(record);
    fireEvent.click(screen.getByRole('button', { name: 'Image library' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Saved swamp · Saved' }));
    await screen.findByAltText('Saved swamp');
    expect(api.generate).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Create image' }));
    expect(screen.getByLabelText(/Seed/)).toHaveValue('42');
    expect(screen.getByLabelText('Shape')).toHaveValue('1536x1024');
  });
  it('retains the preview and reconciles an uncertain Save without regenerating', async () => {
    const api = createPort(); await settings(api);
    fireEvent.click(screen.getByRole('button', { name: 'Generate image' }));
    await screen.findByRole('button', { name: 'Save image' });
    vi.mocked(api.save).mockRejectedValue(new Error('Outcome unknown'));
    vi.mocked(api.get).mockResolvedValue({ asset_id: 'asset-1', state: 'unknown', mime_type: 'image/png', created_at: '', provenance: {} });
    fireEvent.click(screen.getByRole('button', { name: 'Save image' }));
    await screen.findByRole('button', { name: 'Check Save status' });
    expect(screen.getByRole('link', { name: 'Download image' })).toBeInTheDocument();
    expect(api.generate).toHaveBeenCalledTimes(1);
    expect(api.save).toHaveBeenCalledTimes(1);
    expect(api.get).toHaveBeenCalledWith('asset-1');
  });
  it('rejects invalid seed without a call', async () => {
    const api = createPort(); await settings(api);
    fireEvent.change(screen.getByLabelText(/Seed/), { target: { value: '-3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Generate image' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Seed must be');
    expect(api.generate).not.toHaveBeenCalled();
  });
  it('uses the server default and keeps provider discovery explicit and non-generating', async () => {
    const api = createPort();
    vi.mocked(api.capabilities).mockResolvedValue({ configured: true, library_ready: true, storage_configured: true, default_model_id: 'gpt-image-2.5-flare', models: [
      { id: 'gpt-image-2.5-flare', label: 'Flare', formats: ['png','jpeg','webp'], controls: ['quality','background'] },
      { id: 'seedream-v5-pro', label: 'Seedream', formats: ['png','jpeg'], controls: [] },
    ] });
    api.catalog = vi.fn().mockResolvedValue({ models: [
      { endpoint_id: 'bytedance/seedream/v5/pro/text-to-image', metadata: { display_name: 'Remote Seedream' }, executable_model: 'seedream-v5-pro', selectable: true },
      { endpoint_id: 'future/model', metadata: { display_name: 'Future Model' }, executable_model: null, selectable: false },
    ], next_cursor: 'next', has_more: true, fetched_at: '2026-10-17T20:00:00Z' });
    render(<MediaImageWizard onClose={() => {}} initialPrompt="Map of Edge" port={api} />);

    await screen.findByRole('option', { name: 'Flare' });
    expect(screen.getByLabelText('Model')).toHaveValue('gpt-image-2.5-flare');
    expect(api.catalog).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText('Explore the fal model catalog'));
    fireEvent.click(screen.getByRole('button', { name: 'Load catalog' }));
    await screen.findByText('Remote Seedream');
    expect(screen.getByText('Not supported by this studio')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Use this model' })).toHaveLength(1);
    fireEvent.change(screen.getByLabelText('Format'), { target: { value: 'webp' } });
    fireEvent.click(screen.getByRole('button', { name: 'Use this model' }));
    expect(screen.getByLabelText('Model')).toHaveValue('seedream-v5-pro');
    expect(screen.getByLabelText('Format')).toHaveValue('png');
    expect(screen.queryByLabelText('Quality')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'More models' }));
    await screen.findByText('Remote Seedream');
    expect(api.catalog).toHaveBeenLastCalledWith('next');
    expect(api.generate).not.toHaveBeenCalled();
  });

  it('keeps a selected model and prompt usable when catalog discovery fails', async () => {
    const api = createPort(); api.catalog = vi.fn().mockRejectedValue(new Error('Catalog unavailable'));
    await settings(api);
    fireEvent.click(screen.getByText('Explore the fal model catalog'));
    fireEvent.click(screen.getByRole('button', { name: 'Load catalog' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Catalog unavailable');
    expect(screen.getByLabelText('Model')).toHaveValue('flux-2-pro');
    expect(screen.getByRole('button', { name: 'Generate image' })).toBeEnabled();
    expect(api.generate).not.toHaveBeenCalled();
  });

  it('collapses during generation and retains its completed image without another call', async () => {
    const api=createPort();let finish!: (value: any)=>void;
    vi.mocked(api.generate).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
    await settings(api);fireEvent.click(screen.getByRole('button',{name:'Generate image'}));
    fireEvent.click(screen.getByRole('button',{name:'Collapse image studio'}));
    expect(screen.queryByRole('button',{name:'Generate image'})).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Expand image studio'})).toBeEnabled();
    await act(async()=>finish({images:[{data_url:'data:image/png;base64,original',media_type:'image/png',asset_id:'asset-1',state:'staged'}],prompt:'Edge',model:'flux-2-pro'}));
    expect(screen.getByText('Image ready')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Expand image studio'}));
    expect(await screen.findByRole('link',{name:'Download image'})).toHaveAttribute('href','blob:original-image');
    expect(api.generate).toHaveBeenCalledTimes(1);
  });

  it('exposes Map framing and sends explicit purpose without rewriting the authored prompt',async()=>{
    const api=createPort();const caps=await api.capabilities();
    vi.mocked(api.capabilities).mockResolvedValue({...caps,map_framing:'Top-down orthographic map framing.'});
    await settings(api);
    fireEvent.change(screen.getByLabelText('Image purpose'),{target:{value:'map'}});
    expect(screen.getByText('Map framing added to your prompt')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Generate image'}));
    await screen.findByRole('link',{name:'Download image'});
    expect(api.generate).toHaveBeenCalledWith(expect.objectContaining({purpose:'map',prompt:'Edge'}));
    expect(screen.getByText(/DungeonBuddy’s configured fal account/)).toBeInTheDocument();
  });

  it('keeps placement errors inside studio and cancellation prevents a late placement',async()=>{
    const api=createPort();let signal:AbortSignal|undefined;
    const choose=vi.fn((_image,_result,placement)=>{signal=placement.signal;return new Promise<void>((_resolve,reject)=>placement.signal.addEventListener('abort',()=>reject(new DOMException('Cancelled','AbortError'))));});
    render(<MediaImageWizard initialPrompt="Edge" onClose={()=>{}} onChoose={choose} port={api}/>);

    fireEvent.click(await screen.findByRole('button',{name:'Generate image'}));
    fireEvent.click(await screen.findByRole('button',{name:'Save image'}));
    fireEvent.click(await screen.findByRole('button',{name:'Place on page'}));
    expect(screen.getByRole('button',{name:'Cancel placement'})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Cancel placement'}));
    await waitFor(()=>expect(signal?.aborted).toBe(true));
    expect(choose).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('link',{name:'Download image'})).toBeInTheDocument();
    expect(api.generate).toHaveBeenCalledTimes(1);
  });

  it('browses library while generating and announces completion without stealing selection', async () => {
    const api = createPort();
    const old = { asset_id: 'old', state: 'ready', mime_type: 'image/png', delivery_url: 'https://imagedelivery.net/test/old/public', created_at: '2026-10-16', provenance: { prompt: 'Earlier image' } };
    const fresh = { asset_id: 'new', state: 'staged', mime_type: 'image/png', data_url: 'data:image/png;base64,new', created_at: '2026-10-17', provenance: { prompt: 'Edge' } };
    vi.mocked(api.list).mockResolvedValue({ items: [old] });
    vi.mocked(api.get).mockImplementation(async id => id === 'old' ? old : fresh);
    let finish!: (value: any) => void;
    vi.mocked(api.generate).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    await settings(api);
    expect(screen.queryByRole('navigation', { name: 'Image creation steps' })).not.toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /What would you like/ })).toBeInTheDocument();
    expect(screen.getByLabelText('Model')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Generate image' }));
    expect(screen.getByRole('button', { name: 'Image library' })).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: 'Image library' }));
    const card = await screen.findByRole('button', { name: 'Earlier image · Saved' });
    expect(card.querySelector('img')).toHaveAttribute('src', old.delivery_url);
    fireEvent.click(card);
    await screen.findByAltText('Earlier image');
    vi.mocked(api.list).mockResolvedValue({ items: [fresh, old] });
    await act(async () => finish({ images: [{ asset_id: 'new', state: 'staged', data_url: fresh.data_url, media_type: 'image/png' }], prompt: 'Edge', model: 'flux-2-pro' }));
    expect(screen.getByAltText('Earlier image')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Open generated image in library' }));
    await screen.findByAltText('Edge');
    expect(api.get).toHaveBeenCalledWith('new');
    expect(api.generate).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Create image' }));
    expect(screen.getByRole('textbox', { name: /What would you like/ })).toHaveValue('Edge');
  });

  it('reads private staged thumbnails through the port without generation or upload', async () => {
    const api = createPort();
    vi.mocked(api.list).mockResolvedValue({ items: [{ asset_id: 'private', state: 'staged', mime_type: 'image/png', created_at: '', provenance: { prompt: 'Private map' } }] });
    vi.mocked(api.get).mockResolvedValue({ asset_id: 'private', state: 'staged', mime_type: 'image/png', data_url: 'data:image/png;base64,private', created_at: '', provenance: { prompt: 'Private map' } });
    await settings(api);
    fireEvent.click(screen.getByRole('button', { name: 'Image library' }));
    const card = await screen.findByRole('button', { name: 'Private map · Not yet on CDN' });
    await waitFor(() => expect(card.querySelector('img')).toHaveAttribute('src', 'data:image/png;base64,private'));
    expect(api.generate).not.toHaveBeenCalled();
    expect(api.save).not.toHaveBeenCalled();
  });

});

 it.each(['map','illustration'] as const)('uses explicit %s purpose and preserves manual override',async(purpose)=>{
  const api=createPort();
  vi.mocked(api.capabilities).mockResolvedValue({configured:true,library_ready:true,storage_configured:true,map_framing:'Overhead map',models:[{id:'model',label:'Model',formats:['png'],controls:[]}]});
  render(<MediaImageWizard initialPrompt='A town' initialPurpose={purpose} onClose={()=>{}} port={api}/>);
  await screen.findByRole('option',{name:'Model'});
  expect(screen.getByLabelText('Image purpose')).toHaveValue(purpose);
  expect(api.generate).not.toHaveBeenCalled();
  const override=purpose==='map'?'illustration':'map';
  fireEvent.change(screen.getByLabelText('Image purpose'),{target:{value:override}});
  fireEvent.click(screen.getByRole('button',{name:'Generate image'}));
  await waitFor(()=>expect(api.generate).toHaveBeenCalledWith(expect.objectContaining({purpose:override})));
 });

it('keeps preview and explicit Save usable when original download metadata conflicts', async () => {
  const api = createPort();
  vi.mocked(api.generate).mockResolvedValue({
    images: [{ data_url: 'data:image/jpeg;base64,AA==', media_type: 'image/png', asset_id: 'asset-1', state: 'staged' }],
    prompt: 'Edge', model: 'flux-2-pro',
  });
  await settings(api);
  fireEvent.click(screen.getByRole('button', { name: 'Generate image' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be prepared for download');
  expect(screen.getByAltText('Edge')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Save image' })).toBeEnabled();
  expect(screen.queryByRole('link', { name: 'Download image' })).not.toBeInTheDocument();
  expect(api.save).not.toHaveBeenCalled();
});
