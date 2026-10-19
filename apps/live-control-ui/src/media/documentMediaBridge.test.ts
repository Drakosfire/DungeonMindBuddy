import { Editor } from '@tiptap/core';
import { describe, expect, it, vi } from 'vitest';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../tiptap/MarkdownEditorCore';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { createDocumentMediaBridge, type DocumentMediaState } from './documentMediaBridge';
const assetId = 'ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
function setup() {
  const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: '<p>Before</p><p>After</p>' });
  const state: DocumentMediaState = { editor, identity: 'world:session:scene', version: 'edition:5:draft:0', canEdit: true };
  const bridge = createDocumentMediaBridge(() => state);
  vi.spyOn(editor.view, 'posAtCoords').mockReturnValue({ pos: 9, inside: 8 });
  return { editor, state, bridge };
}
async function choose(editor: Editor, bridge: ReturnType<typeof createDocumentMediaBridge>, signal: AbortSignal, mode: 'click' | 'drag' = 'click') {
  const pending = bridge.pickInsertion({ assetId, signal, mode });
  const event = new MouseEvent(mode === 'click' ? 'pointerup' : 'drop', { bubbles: true, cancelable: true, clientX: 10, clientY: 10 });
  if (mode === 'drag') Object.defineProperty(event, 'dataTransfer', { value: { getData: () => assetId } });
  editor.view.dom.dispatchEvent(event);return pending;
}
describe('document-owned saved media insertion', () => {
  it.each(['click', 'drag'] as const)('inserts once at an explicit %s position with one Undo', async mode => {
    const { editor, bridge } = setup();const abort = new AbortController();const original = editor.getJSON();
    try {
      const capture = await choose(editor, bridge, abort.signal, mode);
      bridge.insert(capture, assetId, 'Lake map');
      const markdown = tiptapJsonToSemanticMarkdown(editor.getJSON());
      expect(markdown.indexOf('Before')).toBeLessThan(markdown.indexOf('![Lake map]'));
      expect(markdown.indexOf('![Lake map]')).toBeLessThan(markdown.indexOf('After'));
      expect(() => bridge.insert(capture, assetId, 'Lake map')).toThrow(/already/);
      editor.commands.undo();expect(editor.getJSON()).toEqual(original);
    } finally { abort.abort();editor.destroy(); }
  });
  it.each(['identity', 'version', 'canEdit', 'json', 'caret'] as const)('refuses a stale %s after point capture without inserting', async field => {
    const { editor, state, bridge } = setup();const abort = new AbortController();
    try {
      const capture = await choose(editor, bridge, abort.signal);
      if (field === 'identity') state.identity = 'world:other-session';
      if (field === 'version') state.version = 'edition:6:draft:1';
      if (field === 'canEdit') state.canEdit = false;
      if (field === 'json') editor.commands.insertContent('changed');
      if (field === 'caret') editor.commands.setTextSelection(1);
      const before = editor.getJSON();expect(() => bridge.insert(capture, assetId, 'Lake map')).toThrow(/changed/);
      expect(editor.getJSON()).toEqual(before);
    } finally { abort.abort();editor.destroy(); }
  });
});
