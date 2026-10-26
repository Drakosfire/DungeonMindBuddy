import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import {Editor} from '@tiptap/core';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../tiptap/MarkdownEditorCore';
import {tiptapJsonToSemanticMarkdown} from '../tiptap/markdown/calloutMarkdown';
import {getWorkspaceDocumentSnapshot} from '../api/liveApi';
import {fixtureWorkspaceDocumentRecord} from '../planSurface/config/planSessionDescriptor';
import type {WorkspaceDocumentSnapshot} from '../api/types';
import {saveBuildProposal} from './saveBuildProposal';
import {createBuildComposeBridge} from './buildComposeBridge';
vi.mock('../api/liveApi',()=>({getWorkspaceDocumentSnapshot:vi.fn()}));
let editor:Editor;
async function digest(value:string){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))),b=>b.toString(16).padStart(2,'0')).join('');}
beforeEach(()=>{vi.clearAllMocks();Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<p>Saved insertion</p>'});});
afterEach(()=>editor.destroy());
async function setup(frontmatter=''){
 const body=tiptapJsonToSemanticMarkdown(editor.getJSON());const markdown=frontmatter+body;
 const record=fixtureWorkspaceDocumentRecord({document_id:'doc',world_id:'world',kind:'worldbuilding_source',revision:2,content_status:'committed'});
 const saved:WorkspaceDocumentSnapshot={schema_version:'dmb_workspace_document_snapshot_v1',record,markdown,content_sha256:await digest(markdown),file_fingerprint:'exact',file_exists:true,loaded_revision:2};
 const before={...saved,markdown:frontmatter+'Old page\n',content_sha256:await digest(frontmatter+'Old page\n'),record:{...record,revision:1},loaded_revision:1};
 const saveMarkdown=vi.fn(async()=>undefined);
 const owner={documentId:'doc',editor,snapshot:before,saveMarkdown};
 const bridge=createBuildComposeBridge(()=>({editor,documentId:'doc',worldId:'world',revision:1,contentSha256:before.content_sha256,visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true}),()=>undefined);
 const basis=(await bridge.capture()).basis;
 const args=[basis,await digest(JSON.stringify(editor.getJSON())),await digest(body)] as const;
 vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(saved);
 return {owner,saved,before,args,saveMarkdown};
}
it('uses the page owner and requires exact committed readback, preserving frontmatter',async()=>{
 const x=await setup('---\nname: Original\n---\n');
 await saveBuildProposal(()=>x.owner,...x.args);
 expect(x.saveMarkdown).toHaveBeenCalledTimes(1);expect(getWorkspaceDocumentSnapshot).toHaveBeenCalledWith('doc');
 expect(x.saveMarkdown.mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(getWorkspaceDocumentSnapshot).mock.invocationCallOrder[0]);
});
it('recognizes an already saved insertion after reload without another write',async()=>{
 const x=await setup();x.owner.snapshot=x.saved;await saveBuildProposal(()=>x.owner,...x.args);
 expect(x.saveMarkdown).not.toHaveBeenCalled();expect(getWorkspaceDocumentSnapshot).toHaveBeenCalledTimes(1);
});
it('does not acknowledge a resolved save no-op or stale readback',async()=>{
 const x=await setup();vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(x.before);
 await expect(saveBuildProposal(()=>x.owner,...x.args)).rejects.toThrow('not verified');
});
it('does not acknowledge a foreign World, document or mismatched content hash',async()=>{
 const x=await setup();
 for(const saved of [{...x.saved,record:{...x.saved.record,world_id:'other'}},{...x.saved,record:{...x.saved.record,document_id:'other'}},{...x.saved,content_sha256:'f'.repeat(64)}]){
  vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(saved);await expect(saveBuildProposal(()=>x.owner,...x.args)).rejects.toThrow('not verified');
 }
});
it('keeps newer typing made during saving while acknowledging only the exact saved insertion',async()=>{
 const x=await setup();x.saveMarkdown.mockImplementation(async()=>{editor.commands.insertContent('Newer writing');});
 await saveBuildProposal(()=>x.owner,...x.args);expect(editor.getText()).toContain('Newer writing');
});
it('rejects changed editor before writing and navigation during saving',async()=>{
 const x=await setup();editor.commands.insertContent('Changed');await expect(saveBuildProposal(()=>x.owner,...x.args)).rejects.toThrow('changed before');expect(x.saveMarkdown).not.toHaveBeenCalled();
 const y=await setup();y.saveMarkdown.mockImplementation(async()=>{y.owner.documentId='different';});
 await expect(saveBuildProposal(()=>y.owner,...y.args)).rejects.toThrow('page changed while saving');
});
it('retains recovery when the owner or verification read fails',async()=>{
 const x=await setup();x.saveMarkdown.mockRejectedValueOnce(new Error('CAS conflict'));await expect(saveBuildProposal(()=>x.owner,...x.args)).rejects.toThrow('CAS conflict');expect(getWorkspaceDocumentSnapshot).not.toHaveBeenCalled();
 vi.mocked(getWorkspaceDocumentSnapshot).mockRejectedValueOnce(new Error('read unavailable'));await expect(saveBuildProposal(()=>x.owner,...x.args)).rejects.toThrow('read unavailable');
});

it.each(['','---\nname: Preserved author metadata\n---\n'])('verifies a saved projection with frontmatter %j without writing or changing the receipt',async frontmatter=>{
 const x=await setup(frontmatter);x.owner.snapshot=x.saved;
 const originalEditor='e'.repeat(64),projection={editorSha256:x.args[1],assertCurrent:vi.fn()};
 const before=editor.getJSON();const transaction=vi.fn();editor.on('transaction',transaction);
 await saveBuildProposal(()=>x.owner,x.args[0],originalEditor,x.args[2],projection);
 expect(x.saveMarkdown).not.toHaveBeenCalled();expect(transaction).not.toHaveBeenCalled();expect(editor.getJSON()).toEqual(before);
 expect(projection.assertCurrent).toHaveBeenCalledTimes(3);expect(originalEditor).toBe('e'.repeat(64));
});
it('refuses the saved-projection path when the intended source is not already saved',async()=>{
 const x=await setup();const projection={editorSha256:x.args[1],assertCurrent:vi.fn()};
 await expect(saveBuildProposal(()=>x.owner,x.args[0],'e'.repeat(64),x.args[2],projection)).rejects.toThrow('not already saved');
 expect(x.saveMarkdown).not.toHaveBeenCalled();expect(getWorkspaceDocumentSnapshot).not.toHaveBeenCalled();
});
it.each(['markdown','frontmatter','hash','revision','foreign','uncommitted','missing','visibility'] as const)('refuses %s saved-projection readback without writing',async failure=>{
 const x=await setup('---\nname: Author\n---\n');x.owner.snapshot=x.saved;
 const changed={...x.saved,record:{...x.saved.record}};
 if(failure==='markdown')changed.markdown+='Changed text';
 if(failure==='frontmatter')changed.markdown=changed.markdown.replace('name: Author','name: Other');
 if(failure==='hash')changed.content_sha256='f'.repeat(64);
 if(failure==='revision'){changed.loaded_revision++;changed.record.revision++;}
 if(failure==='foreign')changed.record.world_id='other-world';
 if(failure==='uncommitted')changed.record.content_status='draft';
 if(failure==='missing')changed.file_exists=false;
 if(failure==='visibility')changed.record.visibility_state='player_safe';
 vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(changed);
 await expect(saveBuildProposal(()=>x.owner,x.args[0],'e'.repeat(64),x.args[2],{editorSha256:x.args[1],assertCurrent:()=>{}})).rejects.toThrow();
 expect(x.saveMarkdown).not.toHaveBeenCalled();
});
it.each(['editor','snapshot','admission','document'] as const)('refuses %s changes during saved-projection readback',async failure=>{
 const x=await setup();x.owner.snapshot=x.saved;
 let release!:(snapshot:WorkspaceDocumentSnapshot)=>void;let allowed=true;
 vi.mocked(getWorkspaceDocumentSnapshot).mockImplementation(()=>new Promise(resolve=>release=resolve));
 const proof={editorSha256:x.args[1],assertCurrent:()=>{if(!allowed)throw Error('Edit admission changed');}};
 const pending=saveBuildProposal(()=>x.owner,x.args[0],'e'.repeat(64),x.args[2],proof);
 const {waitFor}=await import('@testing-library/react');await waitFor(()=>expect(release).toBeTypeOf('function'));
 if(failure==='editor')editor.commands.insertContent('Newer author writing');
 if(failure==='snapshot')x.owner.snapshot={...x.saved};
 if(failure==='admission')allowed=false;
 if(failure==='document')x.owner.documentId='another-page';
 const rejected=expect(pending).rejects.toThrow();release(x.saved);await rejected;
 expect(x.saveMarkdown).not.toHaveBeenCalled();
});
