import {useCallback,useState} from 'react';
import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {flushSync} from 'react-dom';
import type {Editor} from '@tiptap/core';
import {closeHistory} from '@tiptap/pm/history';
import {AgentInteractionProvider} from '../agentInteraction/AgentInteractionProvider';
import type {AppChromeToolsGeneration} from '../chrome/AppChrome';
import {BuildCanvasTestProvider} from './buildCanvasTestProvider';
import {BuildSurfaceShell} from './BuildSurfaceShell';
import {useMarkdownCanvasSession} from '../markdownCanvas/MarkdownCanvasSession';
import * as api from '../api/liveApi';

// Keep the real editor, authoring session, autosave and Surface publication.
vi.mock('../api/liveApi',async original=>({...await original<typeof api>(),getWorkspaceDocumentSnapshot:vi.fn(),getBuildSourceNavigation:vi.fn(),prepareTiptapMarkdownWrite:vi.fn(),commitTiptapMarkdownWrite:vi.fn()}));
afterEach(cleanup);

it('keeps rapid edits, cursor, outline, formatting and undo in one live Build editor without republishing its tools',async()=>{
 localStorage.clear();sessionStorage.clear();
 const doc='11111111-1111-4111-8111-111111111111';
 vi.mocked(api.getWorkspaceDocumentSnapshot).mockResolvedValue({schema_version:'dmb_workspace_document_snapshot_v1',record:{schema_version:'dmb_workspace_document_record_v1',document_id:doc,title:'Cursor probe',world_id:'synthetic-editor-test',campaign_id:'synthetic-editor-test',target_session:null,kind:'worldbuilding_source',target_relpath:'out/workspace/worldbuilding/'+doc+'.md',status:'active',content_status:'committed',revision:1,created_at:'2026-10-25T00:00:00Z',updated_at:'2026-10-25T00:00:00Z',source_domain:'worldbuilding',document_class:'lore',authority_state:'draft',visibility_state:'internal'},markdown:'# Cursor probe\n\nA paragraph.\n\n## Roster\n\n| Name | Detail |\n| --- | --- |\n| Keeper | Temporarily here |\n',content_sha256:'a'.repeat(64),file_fingerprint:'present',file_exists:true,loaded_revision:1} as any);
 let editor:Editor|null=null;
 const published=vi.fn();
 function Probe(){editor=useMarkdownCanvasSession().editor;return null;}
 function Host(){
  const [tools,setTools]=useState<AppChromeToolsGeneration|null>(null);
  const publish=useCallback((next:AppChromeToolsGeneration|null)=>{published(next);setTools(next);},[]);
  return <AgentInteractionProvider><BuildCanvasTestProvider documentId={doc}><Probe/><BuildSurfaceShell onEditorTools={publish}/><aside aria-label="Published editor tools">{tools?.tools.sections[0]?.panel}</aside></BuildCanvasTestProvider></AgentInteractionProvider>;
 }
 render(<Host/>);await waitFor(()=>expect(editor).not.toBeNull());
 const originalEditor=editor!;
 await screen.findByRole('button',{name:'Cursor probe',exact:true});
 let end=0;editor!.state.doc.descendants((node,pos)=>{if(node.type.name==='paragraph'&&node.textContent==='A paragraph.')end=pos+node.nodeSize-1;});
 act(()=>editor!.commands.setTextSelection(end));
 const publications=published.mock.calls.length;
 // One synchronous input burst reproduces the original passive-update cascade.
 act(()=>{for(let n=0;n<180;n++)flushSync(()=>editor!.commands.insertContent('x'));});
 expect(editor).toBe(originalEditor);
 expect(editor!.getText()).toContain('A paragraph.'+'x'.repeat(180));
 expect(editor!.state.selection.from).toBe(end+180);
 expect(editor!.getText()).toContain('Keeper');
 expect(published).toHaveBeenCalledTimes(publications);
 const panel=within(screen.getByRole('complementary',{name:'Published editor tools'}));
 act(()=>editor!.commands.toggleBold());
 expect(panel.getByRole('button',{name:'Bold',exact:true})).toHaveAttribute('aria-pressed','true');
 act(()=>{editor!.view.dispatch(closeHistory(editor!.state.tr));editor!.commands.insertContentAt({from:1,to:13},'Updated outline');});
 expect(await panel.findByRole('button',{name:'Updated outline',exact:true})).toBeEnabled();
 fireEvent.click(panel.getByRole('button',{name:'Undo',exact:true}));
 expect(await panel.findByRole('button',{name:'Cursor probe',exact:true})).toBeEnabled();
 fireEvent.click(panel.getByRole('button',{name:'Redo',exact:true}));
 expect(await panel.findByRole('button',{name:'Updated outline',exact:true})).toBeEnabled();
 expect(editor).toBe(originalEditor);
 expect(published).toHaveBeenCalledTimes(publications);
});
