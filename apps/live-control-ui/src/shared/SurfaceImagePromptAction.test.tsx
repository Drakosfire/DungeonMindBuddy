import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { SurfaceImagePromptAction } from './SurfaceImagePromptAction';
it('passes the exact prompt only after an explicit user action', () => {
  const open = vi.fn(); const prompt = 'A broken boardwalk\nDark water and tendrils.';
  const view = render(<SurfaceImagePromptAction prompt={prompt} unavailableReason={null} onOpen={open} />);
  expect(open).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Open Image Studio' }));
  expect(open).toHaveBeenCalledExactlyOnceWith(prompt);
  view.rerender(<SurfaceImagePromptAction prompt={prompt} unavailableReason="Studio already open" onOpen={open} />);
  fireEvent.click(screen.getByRole('button', { name: 'Open Image Studio' }));
  expect(open).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('note')).toHaveTextContent('Studio already open');
});
