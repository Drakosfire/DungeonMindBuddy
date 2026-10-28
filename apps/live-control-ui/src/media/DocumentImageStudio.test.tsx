import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { DocumentImageStudio } from './DocumentImageStudio';
import * as api from '../api/liveApi';
import type { DocumentMediaBridge, DocumentMediaCapture } from './documentMediaBridge';
const tourImage=vi.hoisted(()=>({generated:vi.fn(),placed:vi.fn()}));
vi.mock('../guidedTour/ImageObservations',()=>({useTourImage:()=>tourImage}));
beforeEach(()=>{tourImage.placed.mockClear();});
const wizard = vi.hoisted(() => ({ props: null as any }));
vi.mock('./MediaImageWizard', () => ({ MediaImageWizard: (props: any) => { wizard.props = props;return <button onClick={props.onClose}>Close studio</button>; } }));
const image = { asset_id: 'ac6c15cc-8c68-4732-8ae2-d9f3f051393a', state: 'ready' };
const result = { prompt: 'Multiline prompt\nretained in the library' };
function setup() {
  const capture = {} as DocumentMediaCapture;
  const bridge: DocumentMediaBridge = { pickInsertion: vi.fn(async () => capture), insert: vi.fn() };
  const onClose = vi.fn();const view = render(<DocumentImageStudio bridge={bridge} targetLabel="session copy" onClose={onClose} />);
  return { ...view, bridge, capture, onClose };
}
afterEach(() => vi.restoreAllMocks());
it.each(['staged', 'ready'])('verifies a %s saved asset before one document-owned insert and closes afterward', async state => {
  const request = vi.spyOn(api, 'authenticatedApiFetch').mockResolvedValue({ response: Response.json({ ...image, state }), csrf: null, requestEpoch: 0 });
  const { bridge, capture, onClose } = setup();
  await act(async () => { await wizard.props.onChoose(image, result, { signal: new AbortController().signal, mode: 'click' }); });
  expect(request).toHaveBeenCalledWith(expect.stringContaining(image.asset_id + '/metadata'), expect.objectContaining({ cache: 'no-store' }));
  expect(bridge.insert).toHaveBeenCalledExactlyOnceWith(capture, image.asset_id, 'Saved artwork');expect(onClose).toHaveBeenCalledOnce();expect(tourImage.placed).toHaveBeenCalledExactlyOnceWith(image.asset_id);
});
it.each(['uploading', 'unknown', 'other asset', 'unmount', 'abort'] as const)('does not insert after %s while verifying metadata', async scenario => {
  let release!: (value: Awaited<ReturnType<typeof api.authenticatedApiFetch>>) => void;
  vi.spyOn(api, 'authenticatedApiFetch').mockImplementation(() => new Promise(resolve => { release = resolve; }));
  const { bridge, unmount } = setup();const abort = new AbortController();
  const pending = wizard.props.onChoose(image, result, { signal: abort.signal, mode: 'click' });
  const rejected = expect(pending).rejects.toThrow();
  await act(async () => { await Promise.resolve(); });
  if (scenario === 'unmount') unmount();
  if (scenario === 'abort') abort.abort();
  await act(async () => { release({ response: Response.json({ ...image, state: ['uploading', 'unknown'].includes(scenario) ? scenario : 'ready', asset_id: scenario === 'other asset' ? 'different' : image.asset_id }), csrf: null, requestEpoch: 0 });await rejected; });
  expect(bridge.insert).not.toHaveBeenCalled();expect(tourImage.placed).not.toHaveBeenCalled();
});
it('forwards close without placing or saving', () => {
  const { bridge, onClose } = setup();fireEvent.click(screen.getByRole('button', { name: 'Close studio' }));
  expect(onClose).toHaveBeenCalledOnce();expect(bridge.pickInsertion).not.toHaveBeenCalled();expect(bridge.insert).not.toHaveBeenCalled();
});

it('seeds the existing wizard without generating, saving or inserting', () => {
  const bridge = { pickInsertion: vi.fn(), insert: vi.fn() };
  render(<DocumentImageStudio bridge={bridge} targetLabel="Plan" initialPrompt={"Exact prompt\nSecond line"} onClose={vi.fn()} />);
  expect(wizard.props.initialPrompt).toBe("Exact prompt\nSecond line");
  expect(bridge.pickInsertion).not.toHaveBeenCalled();
  expect(bridge.insert).not.toHaveBeenCalled();
});
