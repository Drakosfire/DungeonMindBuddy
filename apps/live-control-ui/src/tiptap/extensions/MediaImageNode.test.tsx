import { afterEach, expect, it, vi } from 'vitest';
import { render, fireEvent, waitFor, cleanup, act } from '@testing-library/react';
import { Editor, EditorContent } from '@tiptap/react';
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from '../MarkdownEditorCore';
import { markdownToTiptapDoc } from '../markdown/markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from '../markdown/calloutMarkdown';
vi.mock('../../api/liveApi', () => ({getNativeGraphAccessGeneration:()=>0,NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT:'dmb:access-test',authenticatedApiFetch: vi.fn(async () => ({requestEpoch:0,response:{ok:true,json:async()=>({asset_id:id,state:'ready',delivery_url:'https://imagedelivery.net/account/map/public'})}}))}));
const id = 'ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
let editor: Editor;
vi.stubGlobal('PointerEvent', MouseEvent);
afterEach(() => { cleanup(); editor?.destroy(); vi.restoreAllMocks(); });
async function mount(editable=true) {
 editor = new Editor({editable, extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: markdownToTiptapDoc(`![Edge map](dmb-media:${id})`).doc});
 const view = render(<EditorContent editor={editor}/>);
 await waitFor(() => expect(view.getByRole('button',{name:'Collapse image'})).toBeInTheDocument());
 return view;
}
it('resizes by pointer and keyboard, persists collapse, preserves identity across Markdown and HTML', async () => {
 const view = await mount();
 const slider = view.getByRole('slider',{name:'Resize image'});
 const parent = view.container.querySelector('.document-media-image')!.parentElement!;
 vi.spyOn(parent, 'getBoundingClientRect').mockReturnValue({width: 1000} as DOMRect);
 slider.setPointerCapture = vi.fn();
 fireEvent.pointerDown(slider,{button:0,pointerId:1,clientX:1000});
 fireEvent.pointerMove(slider,{pointerId:1,clientX:500});
 fireEvent.pointerUp(slider,{pointerId:1,clientX:500});
 await waitFor(() => expect(slider).toHaveAttribute('aria-valuenow','50'));
 fireEvent.keyDown(slider,{key:'ArrowLeft'});
 await waitFor(() => expect(slider).toHaveAttribute('aria-valuenow','45'));
 fireEvent.click(view.getByRole('button',{name:'Collapse image'}));
 await waitFor(() => expect(view.getByRole('button',{name:'Expand image'})).toHaveAttribute('aria-expanded','false'));
 const saved = tiptapJsonToSemanticMarkdown(editor.getJSON());
 expect(saved).toContain('dmb-image:v1 width=45 collapsed=true');
 expect(saved).toContain(id);
 const reopened = markdownToTiptapDoc(saved);
 expect(reopened.diagnostics).toEqual([]);
 expect(tiptapJsonToSemanticMarkdown(reopened.doc)).toBe(saved);
 const copy = new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:editor.getHTML()});
 expect(tiptapJsonToSemanticMarkdown(copy.getJSON())).toBe(saved);
 copy.destroy();
});
it('cancels unfinished resize and does not write intermediate dimensions', async () => {
 const view = await mount();
 const before = tiptapJsonToSemanticMarkdown(editor.getJSON());
 const slider = view.getByRole('slider');
 vi.spyOn(view.container.querySelector('.document-media-image')!.parentElement!, 'getBoundingClientRect').mockReturnValue({width:1000} as DOMRect);
 slider.setPointerCapture=vi.fn();
 fireEvent.pointerDown(slider,{button:0,pointerId:1,clientX:1000});
 fireEvent.pointerMove(slider,{pointerId:1,clientX:200});
 expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(before);
 fireEvent.pointerCancel(slider,{pointerId:1});
 expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(before);
});

it('refuses stale control mutation after the editor becomes read-only', async () => {
 const view=await mount();
 const slider=view.getByRole('slider'); const collapse=view.getByRole('button',{name:'Collapse image'});
 const before=tiptapJsonToSemanticMarkdown(editor.getJSON());
 act(() => editor.setEditable(false, false));
 fireEvent.keyDown(slider,{key:'ArrowLeft'});
 fireEvent.click(collapse);
 fireEvent.pointerDown(slider,{button:0,pointerId:1,clientX:1000});
 fireEvent.pointerMove(slider,{pointerId:1,clientX:200});fireEvent.pointerUp(slider,{pointerId:1});
 expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(before);
});

it('shows disabled controls when initially read-only', async () => {
 const view=await mount(false); const before=editor.getJSON();
 expect(view.queryByRole('slider')).not.toBeInTheDocument();
 expect(view.getByRole('button',{name:'Collapse image'})).toBeDisabled();
 fireEvent.click(view.getByRole('button',{name:'Collapse image'}));
 expect(editor.getJSON()).toEqual(before);
});
it('cancels an active resize on a transition to read-only', async () => {
 const view=await mount();const slider=view.getByRole('slider');const before=editor.getJSON();
 vi.spyOn(view.container.querySelector('.document-media-image')!.parentElement!, 'getBoundingClientRect').mockReturnValue({width:1000} as DOMRect);
 slider.setPointerCapture=vi.fn();fireEvent.pointerDown(slider,{button:0,pointerId:1,clientX:1000});fireEvent.pointerMove(slider,{pointerId:1,clientX:200});
 act(() => editor.setEditable(false, false));fireEvent.pointerUp(slider,{pointerId:1});
 expect(editor.getJSON()).toEqual(before);
 await waitFor(() => expect(view.queryByRole('slider')).not.toBeInTheDocument());
 expect(view.getByRole('button',{name:'Collapse image'})).toBeDisabled();
});

it('reveals controls when production toggles Read to Edit without emitting an authored update', async () => {
 const view=await mount(false);const before=editor.getJSON();
 const updates=vi.fn();editor.on('update',updates);
 act(() => editor.setEditable(true, false));
 await waitFor(() => expect(view.getByRole('slider')).toBeInTheDocument());
 expect(view.getByRole('button',{name:'Collapse image'})).toBeEnabled();
 expect(editor.getJSON()).toEqual(before);expect(updates).not.toHaveBeenCalled();
});
