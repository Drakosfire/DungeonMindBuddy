import { Editor } from '@tiptap/core';
import { expect, it, vi } from 'vitest';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../tiptap/MarkdownEditorCore';
import { pickMediaInsertion } from './pickMediaInsertion';
const assetId = 'ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
it.each(['abort', 'outside', 'wrong payload', 'stale'] as const)('cleans up %s placement without capture or mutation', async scenario => {
  const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: '<p>Before</p>' });
  const abort = new AbortController();const capture = vi.fn(async () => 'captured');let current = true;
  vi.spyOn(editor.view, 'posAtCoords').mockReturnValue(scenario === 'outside' ? null : { pos: 1, inside: 0 });
  const before = editor.getJSON();
  try {
    const pending = pickMediaInsertion({ editor, assetId, signal: abort.signal, mode: 'drag', isCurrent: () => current, capture });
    const rejected = expect(pending).rejects.toThrow();
    if (scenario === 'abort') abort.abort();
    else {
      if (scenario === 'stale') current = false;
      const event = new MouseEvent('drop', { bubbles: true, cancelable: true });
      Object.defineProperty(event, 'dataTransfer', { value: { getData: () => scenario === 'wrong payload' ? 'foreign image' : assetId } });
      editor.view.dom.dispatchEvent(event);expect(event.defaultPrevented).toBe(true);
    }
    await rejected;expect(capture).not.toHaveBeenCalled();expect(editor.getJSON()).toEqual(before);
    expect(editor.view.dom).not.toHaveClass('is-media-placement-target');
  } finally { abort.abort();editor.destroy(); }
});
it('checks abort after an asynchronous owning capture', async () => {
  const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: '<p>Before</p>' });
  const abort = new AbortController();let release!: (value: string) => void;
  const capture = vi.fn(() => new Promise<string>(resolve => { release = resolve; }));
  vi.spyOn(editor.view, 'posAtCoords').mockReturnValue({ pos: 1, inside: 0 });
  try {
    const pending = pickMediaInsertion({ editor, assetId, signal: abort.signal, mode: 'click', isCurrent: () => true, capture });
    editor.view.dom.dispatchEvent(new MouseEvent('pointerup', { bubbles: true }));
    await vi.waitFor(() => expect(capture).toHaveBeenCalledOnce());
    const rejected = expect(pending).rejects.toThrow(/cancelled/);abort.abort();release('captured');await rejected;
  } finally { abort.abort();editor.destroy(); }
});
