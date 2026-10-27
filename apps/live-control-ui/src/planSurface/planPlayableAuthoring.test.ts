import { Editor } from '@tiptap/core';
import { afterEach, expect, it } from 'vitest';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../tiptap/MarkdownEditorCore';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { indexPlayableStructureV2 } from '../tiptap/playable/playableStructureIndex';
import { insertPlanStructure, planStructureActions, promotePlanHeading } from './planPlayableAuthoring';
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


function selectHeading(text:string) {
  let position=-1;editor.state.doc.forEach((node,pos)=>{if(node.type.name==='heading'&&node.textContent===text)position=pos+1;});
  expect(position).toBeGreaterThan(0);editor.commands.setTextSelection(position);
}
function promote(kind:'scene'|'beat') {return promotePlanHeading(editor,kind,editor.state);}
it('registers authored Beat/Scene headings in place, preserving body/table and exact IDs through undo and reload',()=>{
 mount('A preparation note.\n\n## Village preparation\n\n### Arrival\n\nLet the party choose.\n\n| Lead | Possibility |\n| --- | --- |\n| Tavern | Meet the keeper |\n\n### Tree\n\nIf investigated, it may react.');
 const original=editor.getJSON();selectHeading('Village preparation');
 expect(planStructureActions(editor)[0]).toMatchObject({operation:'promote',label:'Make this a Beat'});
 const beat=promote('beat');selectHeading('Arrival');expect(planStructureActions(editor)[1].label).toBe('Make this a Scene');const scene=promote('scene');
 selectHeading('Tree');const second=promote('scene');
 const typed=editor.getJSON(),source=tiptapJsonToSemanticMarkdown(typed);
 expect(typed.content?.map(node=>node.content)).toEqual(original.content?.map(node=>node.content));
 expect(indexPlayableStructureV2(typed)).toMatchObject({status:'ready',index:{beatOrder:[beat],scenes:[{sceneId:scene,beatId:beat},{sceneId:second,beatId:beat}]}});
 editor.commands.undo();expect(editor.getJSON().content?.at(-2)?.attrs?.playableElementId).toBeNull();
 editor.commands.redo();expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(source);
 editor.commands.setContent(markdownToTiptapDoc(source).doc);expect(editor.getJSON()).toEqual(typed);
 expect(source).toContain('| Tavern | Meet the keeper |');
});
it('refuses Scene promotion across an ordinary root heading without attaching to an earlier Beat',()=>{
 mount('<!-- dmb-playable-element:v2 kind=beat id=beat:first -->\n## First\n\n### Inside\n\nBody.\n\n## Unrelated notes\n\n### Outside\n\nKeep this.');
 selectHeading('Outside');const before=editor.getJSON();
 expect(planStructureActions(editor)[1]).toMatchObject({operation:'promote',disabledReason:'Place the cursor inside a Beat first.'});
 expect(()=>promote('scene')).toThrow('cursor');expect(editor.getJSON()).toEqual(before);
 selectHeading('Inside');expect(()=>promote('scene')).not.toThrow();
});
it('refuses an otherwise valid Beat promotion that would reparent an existing Scene and its Choice',()=>{
 mount('<!-- dmb-playable-element:v2 kind=beat id=beat:first -->\n## First\n\n## Notes\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:existing -->\n### Existing\n\nBody.\n\n<!-- dmb-playable-element:v2 kind=choice id=choice:existing scene=scene:existing -->\n#### Current choice');
 selectHeading('Notes');const before=editor.getJSON();expect(()=>promote('beat')).toThrow('relationship');expect(editor.getJSON()).toEqual(before);
});
it('preserves other Beats and existing Scene ownership when registering a new child before them',()=>{
 mount('<!-- dmb-playable-element:v2 kind=beat id=beat:first -->\n## First\n\n### Authored arrival\n\nTable or prose.\n\n<!-- dmb-playable-element:v2 kind=beat id=beat:second -->\n## Second\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:existing -->\n### Existing\n\nKeep this.');
 selectHeading('Authored arrival');const id=promote('scene');
 expect(indexPlayableStructureV2(editor.getJSON())).toMatchObject({status:'ready',index:{scenes:[{sceneId:id,beatId:'beat:first'},{sceneId:'scene:existing',beatId:'beat:second'}]}});
});
it('refuses stale, nested, marked, multi-heading and v1 promotion with no document mutation',()=>{
 mount('## Session\n\n### Arrival\n\nBody.');selectHeading('Session');const stale=editor.state;selectHeading('Arrival');
 expect(()=>promotePlanHeading(editor,'beat',stale)).toThrow('changed');
 editor.commands.setTextSelection({from:1,to:editor.state.doc.content.size-1});let before=editor.getJSON();expect(()=>promote('beat')).toThrow('heading');expect(editor.getJSON()).toEqual(before);
 editor.commands.setContent(markdownToTiptapDoc('<!-- dmb-playable-element:v1 kind=scene id=scene:old -->\n## Old\n\n## Ordinary').doc);
 selectHeading('Ordinary');before=editor.getJSON();expect(()=>promote('beat')).toThrow('Beat-first');expect(editor.getJSON()).toEqual(before);
 selectHeading('Old');expect(()=>promote('scene')).toThrow();expect(editor.getJSON()).toEqual(before);
 editor.commands.setContent({type:'doc',content:[{type:'blockquote',content:[{type:'heading',attrs:{level:2},content:[{type:'text',text:'Nested'}]}]}]});editor.commands.setTextSelection(2);
 before=editor.getJSON();expect(()=>promote('beat')).toThrow('heading');expect(editor.getJSON()).toEqual(before);
 editor.setEditable(false,false);expect(()=>promote('beat')).toThrow('editable');
});
it('refuses promotion in a card-scoped editor instead of claiming an identity was applied',async()=>{
 const {PlanCardEditing,setPlanCardScope}=await import('./planCardEditing');
 mount();editor.destroy();editor=new Editor({element:document.body.appendChild(document.createElement('div')),extensions:[...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,PlanCardEditing],editorProps:{handleScrollToSelection:()=>true},content:markdownToTiptapDoc('<!-- dmb-playable-element:v2 kind=beat id=beat:first -->\n## First\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:existing -->\n### Existing\n\n### Ordinary\n\nBody.').doc});
 setPlanCardScope(editor,{active:true,sceneId:'scene:existing'});selectHeading('Ordinary');const before=editor.getJSON();
 expect(planStructureActions(editor)[1].disabledReason).toContain('Open Document');expect(()=>promote('scene')).toThrow('Open Document');expect(editor.getJSON()).toEqual(before);
});

it('does not regenerate an existing current identity or register non-roundtrippable content',()=>{
 mount('<!-- dmb-playable-element:v2 kind=beat id=beat:kept beat_kind=optional -->\n## Kept\n\nBody.');selectHeading('Kept');let before=editor.getJSON();
 expect(()=>promote('beat')).toThrow('heading');expect(editor.getJSON()).toEqual(before);
 editor.commands.setContent(markdownToTiptapDoc('## Authored heading\n\nBody.').doc);selectHeading('Authored heading');
 editor.commands.insertContentAt(editor.state.doc.content.size,{type:'paragraph'});selectHeading('Authored heading');before=editor.getJSON();
 expect(()=>promote('beat')).toThrow('round-trip');expect(editor.getJSON()).toEqual(before);
});


it('keeps a named table inside the current Beat without offering to promote its caption',()=>{
 mount('<!-- dmb-playable-element:v2 kind=beat id=beat:first beat_kind=spine -->\n## First\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:first -->\n### Arrival\n\n## Tactics\n\n| Actor | Move |\n| --- | --- |\n| Guard | Wait |\n\nAfter the table.');
 selectHeading('Tactics');
 expect(planStructureActions(editor)[0].operation).toBe('insert');
 editor.commands.setTextSelection(editor.state.doc.content.size-1);
 expect(planStructureActions(editor)[1].disabledReason).toBeNull();
 const scene=insert('scene');
 const indexed=indexPlayableStructureV2(editor.getJSON());
 expect(indexed).toMatchObject({status:'ready',index:{scenes:[{sceneId:'scene:first',beatId:'beat:first'},{sceneId:scene,beatId:'beat:first'}]}});
 expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toContain('## Tactics');
});
