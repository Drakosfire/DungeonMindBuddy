import {Editor,EditorContent} from '@tiptap/react';
import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import * as api from '../api/liveApi';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../tiptap/MarkdownEditorCore';
import {markdownToTiptapDoc} from '../tiptap/markdown/markdownToTiptap';
import {tiptapJsonToSemanticMarkdown} from '../tiptap/markdown/calloutMarkdown';
const parent='ac6c15cc-8c68-4732-8ae2-d9f3f051393a';const child='bc6c15cc-8c68-4732-8ae2-d9f3f051393a';
const draftKey=`dmb:image-context-instructions:v1:${parent}`;
let editor:Editor;let generation=0;let fetcher:ReturnType<typeof vi.spyOn<typeof api,'authenticatedApiFetch'>>;
const reply=(body:unknown,status=200)=>({response:Response.json(body,{status}),csrf:null,requestEpoch:generation});
beforeEach(()=>{
 generation=0;localStorage.clear();vi.spyOn(api,'getNativeGraphAccessGeneration').mockImplementation(()=>generation);
 fetcher=vi.spyOn(api,'authenticatedApiFetch').mockImplementation(async path=>path.endsWith('/regenerate')
  ?reply({asset_id:child,parent_asset_id:parent,state:'staged',model:'flux-2-pro'})
  :reply({asset_id:path.includes(child)?child:parent,state:'ready',content_sha256:'a'.repeat(64),delivery_url:'https://imagedelivery.net/account/image/public'}));
});
afterEach(()=>{cleanup();editor?.destroy();vi.restoreAllMocks();});
function mount(editable=true){
 editor=new Editor({editable,extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:markdownToTiptapDoc(`![First](dmb-media:${parent} "dmb-image:v1 width=45 collapsed=false")\n\n![Second](dmb-media:${parent})`).doc});
 return render(<EditorContent editor={editor}/>);
}
async function open(){fireEvent.click((await screen.findAllByRole('button',{name:'Edit image'}))[0]);await waitFor(()=>expect(screen.getByLabelText('Instructions')).toBeEnabled());}
async function submit(mode='image_to_image'){
 fireEvent.change(screen.getByLabelText('Action'),{target:{value:mode}});
 fireEvent.change(screen.getByLabelText('Instructions'),{target:{value:'Keep the retreat path clear.'}});
 fireEvent.click(screen.getByRole('button',{name:'Generate',exact:true}));
}
it('uses the hovered occurrence only, preserves presentation and offers one Undo',async()=>{
 mount();const before=editor.getJSON();await open();await submit();
 fireEvent.click(await screen.findByRole('button',{name:'Use this version'}));
 await waitFor(()=>expect(JSON.stringify(editor.getJSON())).toContain(child));
 const images:any[]=[];editor.state.doc.descendants(node=>{if(node.type.name==='mediaImage')images.push(node.attrs);});
 expect(images[0]).toMatchObject({assetId:child,alt:'First',width:45,collapsed:false});expect(images[1].assetId).toBe(parent);
 const call=fetcher.mock.calls.find(([path])=>path.endsWith('/regenerate'))!;
 expect(JSON.parse(String(call[1]?.body))).toEqual({mode:'image_to_image',instructions:'Keep the retreat path clear.',expected_content_sha256:'a'.repeat(64)});
 act(()=>{editor.commands.undo();});expect(editor.getJSON()).toEqual(before);
});
it('retains mode and text on close and remount after owner authorization',async()=>{
 const view=mount();await open();fireEvent.change(screen.getByLabelText('Action'),{target:{value:'new'}});
 fireEvent.change(screen.getByLabelText('Instructions'),{target:{value:'A fresh scene.'}});
 fireEvent.keyDown(screen.getByRole('dialog',{name:'Edit image'}),{key:'Escape'});
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(screen.getAllByRole('button',{name:'Edit image'})[0]).toHaveFocus();
 view.unmount();editor.destroy();mount();await open();expect(screen.getByLabelText('Instructions')).toHaveValue('A fresh scene.');expect(screen.getByLabelText('Action')).toHaveValue('new');
});
it('keeps a late generated child but refuses applying over newer document edits',async()=>{
 let finish!:(value:Awaited<ReturnType<typeof api.authenticatedApiFetch>>)=>void;
 const fallback=fetcher.getMockImplementation()!;
 fetcher.mockImplementation((path,init)=>path.endsWith('/regenerate')?new Promise(resolve=>{finish=resolve;}):fallback(path,init));
 mount();await open();await submit();expect(screen.getByRole('button',{name:'Generating…'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Generating…'}));
 expect(fetcher.mock.calls.filter(([path])=>path.endsWith('/regenerate'))).toHaveLength(1);
 act(()=>{editor.commands.insertContent('Newer draft');});const newer=editor.getJSON();
 await act(async()=>finish(reply({asset_id:child,parent_asset_id:parent,state:'staged',model:'flux-2-pro'})));
 fireEvent.click(await screen.findByRole('button',{name:'Use this version'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('page changed');expect(editor.getJSON()).toEqual(newer);
 expect(screen.getByText('Retained privately. Your current image is unchanged.')).toBeInTheDocument();
});
it('does not reveal stored notes when a changed owner cannot read the asset',async()=>{
 mount();await open();fireEvent.change(screen.getByLabelText('Instructions'),{target:{value:'Private instruction'}});
 fetcher.mockResolvedValue(reply({detail:'Unavailable'},403));
 act(()=>{generation=1;window.dispatchEvent(new Event(api.NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT));});
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 fireEvent.click(screen.getAllByRole('button',{name:'Edit image'})[0]);
 await screen.findByRole('alert');expect(screen.getByLabelText('Instructions')).toHaveValue('');
 expect(localStorage.getItem(draftKey)).toContain('Private instruction');
});
it('keeps current instructions when browser storage fails',async()=>{
 mount();await open();vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('Quota');});
 fireEvent.change(screen.getByLabelText('Instructions'),{target:{value:'Keep this text'}});
 expect(screen.getByLabelText('Instructions')).toHaveValue('Keep this text');expect(screen.getByText(/could not be stored/)).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Close edit menu'}));await open();expect(screen.getByLabelText('Instructions')).toHaveValue('Keep this text');
});
it('offers no image editing in read-only views',async()=>{
 mount(false);await screen.findAllByRole('button',{name:'Collapse image'});
 expect(screen.queryByRole('button',{name:'Edit image'})).not.toBeInTheDocument();
 expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toContain(parent);
});

it('sends the explicit new-image choice and text without a browser image payload',async()=>{
 mount();await open();await submit('new');await screen.findByRole('button',{name:'Use this version'});
 const call=fetcher.mock.calls.find(([path])=>path.endsWith('/regenerate'))!;
 expect(JSON.parse(String(call[1]?.body))).toEqual({mode:'new',instructions:'Keep the retreat path clear.',expected_content_sha256:'a'.repeat(64)});
});
it('rechecks candidate ownership before Apply and preserves the document on denial',async()=>{
 mount();await open();await submit();const button=await screen.findByRole('button',{name:'Use this version'});
 const before=editor.getJSON();fetcher.mockResolvedValue(reply({detail:'Image unavailable'},403));
 fireEvent.click(button);expect(await screen.findByRole('alert')).toHaveTextContent('unavailable');
 expect(editor.getJSON()).toEqual(before);
});
it('fences a generation result after the authenticated owner changes',async()=>{
 let finish!:(value:Awaited<ReturnType<typeof api.authenticatedApiFetch>>)=>void;
 const fallback=fetcher.getMockImplementation()!;
 fetcher.mockImplementation((path,init)=>path.endsWith('/regenerate')?new Promise(resolve=>{finish=resolve;}):fallback(path,init));
 mount();await open();await submit();const before=editor.getJSON();
 act(()=>{generation=1;window.dispatchEvent(new Event(api.NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT));});
 await act(async()=>finish(reply({asset_id:child,parent_asset_id:parent,state:'staged',model:'flux-2-pro'})));
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(editor.getJSON()).toEqual(before);
});
