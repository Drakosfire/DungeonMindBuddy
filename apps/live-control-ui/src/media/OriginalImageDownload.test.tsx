import { StrictMode } from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { OriginalImageDownload } from './OriginalImageDownload';

const createDescriptor = Object.getOwnPropertyDescriptor(URL, 'createObjectURL');
const revokeDescriptor = Object.getOwnPropertyDescriptor(URL, 'revokeObjectURL');
const create = vi.fn<(blob: Blob) => string>();
const revoke = vi.fn();
beforeEach(() => {
  create.mockReset().mockImplementation(() => `blob:original-${create.mock.calls.length}`);
  revoke.mockReset();
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: create });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revoke });
});
afterEach(() => {
  cleanup();
  for (const [key, descriptor] of [['createObjectURL', createDescriptor], ['revokeObjectURL', revokeDescriptor]] as const) {
    if (descriptor) Object.defineProperty(URL, key, descriptor); else Reflect.deleteProperty(URL, key);
  }
});
function bytes(blob: Blob): Promise<Uint8Array> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(new Uint8Array(reader.result as ArrayBuffer));
    reader.onerror = reject;
    reader.readAsArrayBuffer(blob);
  });
}
describe('OriginalImageDownload', () => {
  it.each(['png', 'jpeg', 'webp'])('preserves original binary bytes, MIME and %s filename', async format => {
    render(<OriginalImageDownload dataUrl={`data:image/${format};base64,AP8Bfw==`} mediaType={`image/${format}`} filename={`world-image-1.${format}`} />);
    const link = await screen.findByRole('link', { name: 'Download image' });
    expect(link).toHaveAttribute('href', 'blob:original-1');
    expect(link).toHaveAttribute('download', `world-image-1.${format}`);
    const blob = create.mock.calls[0][0];
    expect(blob.type).toBe(`image/${format}`);
    expect(Array.from(await bytes(blob))).toEqual([0, 255, 1, 127]);
    expect(revoke).not.toHaveBeenCalled();
  });
  it('replaces and cleans up owned URLs without revoking on click', async () => {
    const { rerender, unmount } = render(<OriginalImageDownload dataUrl="data:image/png;base64,AA==" mediaType="image/png" filename="first.png" />);
    const link = await screen.findByRole('link', { name: 'Download image' });
    link.addEventListener('click', event => event.preventDefault());
    link.click();
    expect(revoke).not.toHaveBeenCalled();
    rerender(<OriginalImageDownload dataUrl="data:image/png;base64,AQ==" mediaType="image/png" filename="second.png" />);
    expect(await screen.findByRole('link', { name: 'Download image' })).toHaveAttribute('href', 'blob:original-2');
    expect(revoke).toHaveBeenCalledExactlyOnceWith('blob:original-1');
    unmount();
    expect(revoke.mock.calls).toEqual([['blob:original-1'], ['blob:original-2']]);
  });
  it('balances React StrictMode setup and cleanup', async () => {
    const { unmount } = render(<StrictMode><OriginalImageDownload dataUrl="data:image/png;base64,AA==" mediaType="image/png" filename="image.png" /></StrictMode>);
    const url = (await screen.findByRole('link', { name: 'Download image' })).getAttribute('href');
    expect(revoke.mock.calls.some(([value]) => value === url)).toBe(false);
    unmount();
    expect(revoke.mock.calls.map(([value]) => value).sort()).toEqual(create.mock.results.map(result => result.value).sort());
  });
  it.each([
    ['data:image/png;base64,%%%', 'image/png'],
    ['data:image/png;base64,', 'image/png'],
    ['data:image/jpeg;base64,AA==', 'image/png'],
    ['https://cdn.example/image.png', 'image/png'],
    ['data:text/html;base64,AA==', 'text/html'],
  ])('keeps malformed or conflicting originals local: %s', async (dataUrl, mediaType) => {
    render(<OriginalImageDownload dataUrl={dataUrl} mediaType={mediaType} filename="image.png" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be prepared for download');
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });
});
