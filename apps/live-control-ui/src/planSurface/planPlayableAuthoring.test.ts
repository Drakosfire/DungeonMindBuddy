import { Editor } from '@tiptap/core';
import { afterEach, expect, it } from 'vitest';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../tiptap/MarkdownEditorCore';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { indexPlayableStructureV2 } from '../tiptap/playable/playableStructureIndex';
import { insertPlanStructure, planStructureActions } from './planPlayableAuthoring';
let editor: Editor;
afterEach(()=>{editor?.destroy();document.body.replaceChildren();});
function mount(markdown='') {editor=new Editor({element:document.body.appendChild(document.createElement('div')),extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,editorProps:{handleScrollToSelection:()=>true},content:markdownToTiptapDoc(markdown).doc});return editor;}
function insert(kind:'scene'|'beat') {return insertPlanStructure(editor,kind,editor.state);}
it('explicitly creates a v2 Beat and Scene on a blank Plan, preserving IDs through rename/undo/redo/reload',()=>{
 mount();const beat=insert('beat');expect(beat).toMatch(/^beat:/);
 const scene=insert('scene');expect(scene).toMatch(/^scene:/);
 editor.commands.insertContent('Eastern approach');
 const source=tiptapJsonToSemanticMarkdown(editor.getJSON());expect(source).toContain(`kind=beat id=${beat} beat_kind=spine`);expect(source).toContain(`kind=scene id=${scene}`);expect(source).toContain('Eastern approach');
 expect(indexPlayableStructureV2(editor.getJSON()).status).toBe('ready');
 editor.commands.undo();editor.commands.redo();expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(source);
 editor.commands.setContent(markdownToTiptapDoc(source).doc);expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(source);
});
it('keeps ordinary headings ordinary and appends a fresh typed Beat after authored source material',()=>{
 mount('# Session\n\n## Ordinary heading\n\nSource: [Mirathorn](https://example.com/source)\n\nA saved quotation.');
 const before=editor.getJSON().content!;insert('beat');expect(editor.getJSON().content?.slice(0,before.length)).toEqual(before);
 expect(editor.getJSON().content?.[1].attrs?.playableElementKind).toBeNull();
});
it('preserves legacy v1 and inserts Beats only within the current Scene before the next root heading',()=>{
 mount('<!-- dmb-playable-element:v1 kind=scene id=scene:first -->\n## First\n\nBody.\n\n## GM instructions\n\nKeep this.');
 expect(planStructureActions(editor).map(x=>x.label)).toEqual(['Add Scene','Add Beat to this Scene']);
 editor.commands.setTextSelection(3);const id=insert('beat');const saved=tiptapJsonToSemanticMarkdown(editor.getJSON());
 expect(saved.indexOf(`id=${id}`)).toBeLessThan(saved.indexOf('## GM instructions'));expect(saved).not.toContain('v2');
 editor.commands.setTextSelection(editor.state.doc.content.size-1);expect(()=>insert('beat')).toThrow('cursor');
});
it('does not attach a Scene to a previous Beat across an ordinary root heading',()=>{
 mount('<!-- dmb-playable-element:v2 kind=beat id=beat:first beat_kind=spine -->\n## First\n\nBody.\n\n## Notes\n\nKeep notes.');
 editor.commands.setTextSelection(editor.state.doc.content.size-1);const before=editor.getJSON();expect(()=>insert('scene')).toThrow('cursor');expect(editor.getJSON()).toEqual(before);
});
it('rejects stale selection, silent read-only transition and malformed or mixed identities without edits',()=>{
 mount();const old=editor.state;editor.commands.insertContent('A');expect(()=>insertPlanStructure(editor,'beat',old)).toThrow('changed');
 editor.setEditable(false,false);const before=editor.getJSON();expect(()=>insert('beat')).toThrow('editable');expect(editor.getJSON()).toEqual(before);
});
it.each([
 '<!-- dmb-playable-element:v1 kind=scene id=scene:first -->\n## First\n\n<!-- dmb-playable-element:v2 kind=beat id=beat:second -->\n## Second',
 '<!-- dmb-playable-element:v1 kind=scene id=scene:first -->\n## First\n\n<!-- dmb-playable-element:v1 kind=scene id=scene:first -->\n## Duplicate',
])('blocks unsupported structure without regenerating identities',source=>{
 mount(source);const before=editor.getJSON();expect(()=>insert('beat')).toThrow();expect(editor.getJSON()).toEqual(before);
});
it('preserves sibling Beat order and existing Scene identity when appending a child',()=>{
 mount('<!-- dmb-playable-element:v2 kind=beat id=beat:first beat_kind=spine -->\n## First\n\nBody.\n\n<!-- dmb-playable-element:v2 kind=beat id=beat:second beat_kind=optional -->\n## Second\n\nOther body.');
 editor.commands.setTextSelection(3);const id=insert('scene');const source=tiptapJsonToSemanticMarkdown(editor.getJSON());
 expect(source.indexOf(`id=${id}`)).toBeLessThan(source.indexOf('id=beat:second'));expect(source).toContain('Other body.');
});

it('rejects a stale caret and selection spanning distinct root Beats',()=>{
 mount('<!-- dmb-playable-element:v2 kind=beat id=beat:first -->\n## First\n\nBody.\n\n<!-- dmb-playable-element:v2 kind=beat id=beat:second -->\n## Second\n\nOther.');
 const state=editor.state;editor.commands.setTextSelection(editor.state.doc.content.size-1);expect(()=>insertPlanStructure(editor,'scene',state)).toThrow('changed');
 editor.commands.setTextSelection({from:3,to:editor.state.doc.content.size-1});const before=editor.getJSON();expect(()=>insert('scene')).toThrow('cursor');expect(editor.getJSON()).toEqual(before);
});
it('keeps protected non-roundtrippable spacer content unchanged',()=>{
 mount('# Notes');editor.commands.insertContentAt(editor.state.doc.content.size,{type:'paragraph'});const before=editor.getJSON();expect(()=>insert('beat')).toThrow('round-trip');expect(editor.getJSON()).toEqual(before);
});
it('preserves media references while adding structure',()=>{
 mount('![Map](dmb-media:73b40978-e638-4ab3-992d-5dc493e8d229 "dmb-image:v1 width=60 collapsed=true")');const before=editor.getJSON().content![0];insert('beat');expect(editor.getJSON().content![0]).toEqual(before);
});

it('rejects nested typed structure without changing it',()=>{
 mount();editor.commands.setContent({type:'doc',content:[{type:'blockquote',content:[{type:'heading',attrs:{level:2,playableElementKind:'beat',playableElementId:'beat:nested',playableElementVersion:'v2'},content:[{type:'text',text:'Nested'}]}]}]});const before=editor.getJSON();expect(()=>insert('beat')).toThrow();expect(editor.getJSON()).toEqual(before);
});
