import { Editor } from '@tiptap/core';
import { describe, expect, it, vi } from 'vitest';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../tiptap/MarkdownEditorCore';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { createDocumentMediaBridge, type DocumentMediaState } from './documentMediaBridge';
const assetId = 'ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
function setup() {
  const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: '<p>Before</p><p>After</p>' });
  const state: DocumentMediaState = { editor, identity: 'world:session:scene', version: 'edition:5:draft:0', canEdit: true };
  const bridge = createDocumentMediaBridge(() => state);
  vi.spyOn(editor.view, 'posAtCoords').mockReturnValue({ pos: 2, inside: 0 });
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

describe('whole-block image placement', () => {
  it.each([1, 7, 8, 13])('preserves complete prose when clicked at %i', async position => {
    const {editor, bridge}=setup(); const abort=new AbortController();
    editor.commands.setContent('<p>Before and after</p><p>Following</p>');
    const original=editor.getJSON();
    vi.mocked(editor.view.posAtCoords).mockReturnValue({pos:position,inside:0});
    try {
      const capture=await choose(editor,bridge,abort.signal);
      bridge.insert(capture,assetId,'Village');
      const result=editor.getJSON(), blocks=result.content!;
      expect(blocks[0]).toEqual(original.content![0]);
      expect(blocks[2]).toEqual(original.content![1]);
      expect(blocks[1].content![0]).toMatchObject({type:'mediaImage',attrs:{assetId}});
      const markdown=tiptapJsonToSemanticMarkdown(result);
      expect(tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(markdown).doc)).toBe(markdown);
      editor.commands.undo(); expect(editor.getJSON()).toEqual(original);
    } finally {abort.abort();editor.destroy();}
  });
  it.each(['heading','table','callout'] as const)('places after the entire %s and preserves its identity', async kind => {
    const {editor, bridge}=setup();const abort=new AbortController();
    const source=kind==='heading'
      ? '<!-- dmb-playable-element:v2 kind=scene id=scene:2446965f-c562-481d-87ee-dc3437b03df8 -->\n### Scene\n\nFollowing'
      : kind==='table' ? '| A | B |\n| --- | --- |\n| Text | More |\n\nFollowing'
      : '> [!NOTE] Reminder\n> Keep this entire passage.\n\nFollowing';
    editor.commands.setContent(markdownToTiptapDoc(source).doc);
    const original=editor.getJSON(); let position=1;
    editor.state.doc.descendants((node,pos)=>{if(position===1&&node.isText)position=pos+1;});
    vi.mocked(editor.view.posAtCoords).mockReturnValue({pos:position,inside:0});
    try {
      const capture=await choose(editor,bridge,abort.signal);
      bridge.insert(capture,assetId,'Village');
      const result=editor.getJSON();
      expect(result.content![0]).toEqual(original.content![0]);
      expect(result.content![2]).toEqual(original.content![1]);
      const markdown=tiptapJsonToSemanticMarkdown(result);
      expect(tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(markdown).doc)).toBe(markdown);
      editor.commands.undo();expect(editor.getJSON()).toEqual(original);
    } finally {abort.abort();editor.destroy();}
  });
});
