import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MediaImageWizard, type ImageGenerationPort } from './MediaImageWizard';
const createPort = (): ImageGenerationPort => ({ capabilities: vi.fn().mockResolvedValue({ configured: true, models: [
  { id: 'flux-2-pro', label: 'FLUX 2 Pro', formats: ['png', 'jpeg'], controls: ['seed'] },
  { id: 'gpt-image-1.5', label: 'GPT Image 1.5', formats: ['png', 'jpeg', 'webp'], controls: ['quality', 'background'] },
] }), generate: vi.fn().mockResolvedValue({ images: [{ data_url: 'data:image/png;base64,iVBORw0KGgo=', media_type: 'image/png' }], prompt: 'Edge', model: 'flux-2-pro' }) });
async function settings(api: ImageGenerationPort) {
  render(<MediaImageWizard onClose={() => {}} port={api} />);
  fireEvent.change(screen.getByRole('textbox', { name: /What would you like/ }), { target: { value: 'Edge' } });
  fireEvent.click(screen.getByRole('button', { name: /Choose model/ }));
  await screen.findByRole('option', { name: 'FLUX 2 Pro' });
}
describe('MediaImageWizard', () => {
  it('submits only explicit Generate with model-supported controls', async () => {
    const api = createPort(); await settings(api);
    expect(api.generate).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/Seed/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'gpt-image-1.5' } });
    expect(screen.queryByLabelText(/Seed/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Quality'), { target: { value: 'low' } });
    fireEvent.click(screen.getByRole('button', { name: 'Generate image' }));
    await screen.findByRole('link', { name: 'Download image' });
    expect(api.generate).toHaveBeenCalledTimes(1);
    expect(api.generate).toHaveBeenCalledWith(expect.objectContaining({ options: { quality: 'low', background: 'opaque', output_format: 'png' } }));
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
  it('rejects invalid seed without a call', async () => {
    const api = createPort(); await settings(api);
    fireEvent.change(screen.getByLabelText(/Seed/), { target: { value: '-3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Generate image' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Seed must be');
    expect(api.generate).not.toHaveBeenCalled();
  });
});
