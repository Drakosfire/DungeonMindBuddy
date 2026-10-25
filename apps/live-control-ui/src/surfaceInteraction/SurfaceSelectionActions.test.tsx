import {Editor} from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import {webcrypto} from 'node:crypto';
import {afterEach,expect,it,vi} from 'vitest';
import {captureSurfaceTextSelection} from './SurfaceSelectionActions';
vi.stubGlobal('crypto',webcrypto);
const editors:Editor[]=[];
afterEach(()=>{editors.splice(0).forEach(editor=>editor.destroy());});
function editor(content:string){const e=new Editor({extensions:[StarterKit],content});editors.push(e);return e;}
it('captures the actual marked UTF16 selection and exact editor snapshot',async()=>{
 const e=editor('<p>🔨 <strong>Brin’s Blacksmithy</strong>: repairs gear.</p>');
 e.commands.setTextSelection({from:4,to:4+'Brin’s Blacksmithy'.length});
 const result=await captureSurfaceTextSelection(e,()=>true);
 expect(result.selected_text).toBe('Brin’s Blacksmithy');expect(result.selection_from).toBe(4);
 expect(JSON.parse(result.editor_json)).toEqual(e.getJSON());expect(result.editor_sha256).toMatch(/^[a-f0-9]{64}$/);
});
it('refuses a retired document even when its selection still exists',async()=>{
 const e=editor('<p>Forge</p>');e.commands.setTextSelection({from:1,to:6});
 await expect(captureSurfaceTextSelection(e,()=>false)).rejects.toThrow('changed');
});
it('refuses selection changes during asynchronous hashing',async()=>{
 const e=editor('<p>Forge</p>');e.commands.setTextSelection({from:1,to:6});
 const pending=captureSurfaceTextSelection(e,()=>true);e.commands.setTextSelection(2);
 await expect(pending).rejects.toThrow('changed');
});
it('refuses cross-paragraph and mixed inline atom selections',async()=>{
 const e=editor('<p>Before</p><p>After</p>');e.commands.setTextSelection({from:1,to:12});
 await expect(captureSurfaceTextSelection(e,()=>true)).rejects.toThrow('one paragraph');
 e.commands.setContent('<p>Before<br>After</p>');e.commands.setTextSelection({from:1,to:5});
 await expect(captureSurfaceTextSelection(e,()=>true)).rejects.toThrow('containing text');
});
