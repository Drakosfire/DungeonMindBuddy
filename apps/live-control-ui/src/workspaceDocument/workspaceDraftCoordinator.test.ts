import {waitFor} from '@testing-library/react';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {buildInitialWorkspaceDocumentLocalState,workspaceDocumentStorageKey} from '../tiptap/state/tiptapLocalState';
import {appendDraftRecoveryCopies,draftRecoveryJournalKey,draftRecoveryKey,readDraftRecoveryCopies} from './workspaceDocumentRecovery';
import {WorkspaceDraftCoordinator} from './workspaceDraftCoordinator';

function state(text='current') {
 return {...buildInitialWorkspaceDocumentLocalState({documentId:'journal-source',title:'Source',campaignId:'test-world',kind:'worldbuilding_source',targetSession:null,surface:'build',baseRevision:3,baseContentSha256:'saved-digest',starterContent:{type:'doc',content:[{type:'paragraph',content:[{type:'text',text}]}]},now:'2026-10-26T00:00:00Z'}),exported_markdown:'# Sealed source',exported_markdown_authoritative:true,dirty:true};
}
beforeEach(()=>{localStorage.clear();vi.restoreAllMocks();});
describe('full-state recovery journal',()=>{
 it('imports retained V1 without changing its bytes, appends newer full JSON and dedupes across reload',()=>{
  const original=state('old protected'),replacement={...original,exported_markdown_authoritative:false};
  const old=JSON.stringify({schema:'dmb_workspace_draft_recovery_v1',original,replacement});
  localStorage.setItem(draftRecoveryKey(original.document_id),old);
  const newer=state('new unique table and image context');
  const first=appendDraftRecoveryCopies(localStorage,original.document_id,[{label:'Latest protected draft',state:newer}]);
  expect(first).toHaveLength(3);expect(first[2].state).toEqual(newer);
  const bytes=localStorage.getItem(draftRecoveryJournalKey(original.document_id));
  const again=appendDraftRecoveryCopies(localStorage,original.document_id,[{label:'Repeat',state:{...newer,updated_at:'later'}}]);
  expect(again.map(c=>c.id)).toEqual(first.map(c=>c.id));
  expect(localStorage.getItem(draftRecoveryJournalKey(original.document_id))).toBe(bytes);
  expect(localStorage.getItem(draftRecoveryKey(original.document_id))).toBe(old);
 });
 it.each(['malformed','foreign','duplicate'])('preserves and refuses %s retained history',kind=>{
  const s=state();const copies=[{id:'one',label:'copy',state:s}];
  if(kind==='foreign')copies[0].state={...s,document_id:'another-source'};
  if(kind==='duplicate')copies.push(copies[0]);
  const raw=kind==='malformed'?'broken':JSON.stringify({schema:'dmb_workspace_draft_recovery_v2',documentId:s.document_id,copies});
  localStorage.setItem(draftRecoveryJournalKey(s.document_id),raw);
  expect(()=>appendDraftRecoveryCopies(localStorage,s.document_id,[{label:'Current',state:s}])).toThrow();
  expect(localStorage.getItem(draftRecoveryJournalKey(s.document_id))).toBe(raw);
 });
 it('refuses ID collision without replacing earlier history',()=>{
  vi.spyOn(crypto,'randomUUID').mockReturnValue('00000000-0000-4000-8000-000000000001');
  const s=state();appendDraftRecoveryCopies(localStorage,s.document_id,[{label:'First',state:s}]);
  const before=localStorage.getItem(draftRecoveryJournalKey(s.document_id));
  expect(()=>appendDraftRecoveryCopies(localStorage,s.document_id,[{label:'Second',state:state('newer')}])).toThrow(/collided/);
  expect(localStorage.getItem(draftRecoveryJournalKey(s.document_id))).toBe(before);
 });
 it.each(['quota','readback'])('refuses replacement when history %s verification fails',async failure=>{
  const s=state();const primary=workspaceDocumentStorageKey(s.document_id),journal=draftRecoveryJournalKey(s.document_id);
  localStorage.setItem(primary,JSON.stringify(s));
  const storage={getItem:(key:string)=>key===journal&&failure==='readback'?null:localStorage.getItem(key),setItem:(key:string,value:string)=>{if(key===journal&&failure==='quota')throw Error('quota');localStorage.setItem(key,value);},removeItem:(key:string)=>localStorage.removeItem(key)};
  const writer=new WorkspaceDraftCoordinator(storage,s.document_id,()=>{});
  await writer.run(()=>{}, {expectedRaw:JSON.stringify(s)});
  await expect(writer.run(()=>{appendDraftRecoveryCopies(storage,s.document_id,[{label:'Current',state:s}]);storage.setItem(primary,'replacement');})).rejects.toThrow();
  expect(localStorage.getItem(primary)).toBe(JSON.stringify(s));
 });
});
describe('shared document draft coordinator',()=>{
 it('serializes two mounted owners, refuses unseen primary writes and retains the refused full draft',async()=>{
  const s=state();const primary=workspaceDocumentStorageKey(s.document_id),raw=JSON.stringify(s);
  localStorage.setItem(primary,raw);
  const a=new WorkspaceDraftCoordinator(localStorage,s.document_id,()=>{}),b=new WorkspaceDraftCoordinator(localStorage,s.document_id,()=>{});
  await a.run(()=>{}, {expectedRaw:raw});await b.run(()=>{}, {expectedRaw:raw});
  const first=state('tab A'),second=state('tab B');
  const writes=await Promise.allSettled([a.write(first),b.write(second)]);
  expect(writes.map(r=>r.status)).toEqual(['fulfilled','rejected']);
  expect(JSON.parse(localStorage.getItem(primary)!)).toEqual(first);
  expect(readDraftRecoveryCopies(localStorage,s.document_id).map(c=>c.state)).toContainEqual(second);
  await expect(b.drain()).rejects.toThrow(/another tab/);
 });
 it('exposes pending work, skips superseded edits, then drains the latest full draft',async()=>{
  const s=state();let release!:()=>void;
  const held=navigator.locks.request('dmb:workspace-draft:'+s.document_id,()=>new Promise<void>(resolve=>release=resolve));
  await waitFor(()=>expect(release).toBeTypeOf("function"));
  const statuses:boolean[]=[];const writer=new WorkspaceDraftCoordinator(localStorage,s.document_id,status=>statuses.push(status.pending));
  const old=writer.write(s,()=>false),latest=writer.write(state('latest'));
  expect(writer.status.pending).toBe(true);release();await held;await Promise.all([old,latest]);await writer.drain();
  expect(writer.status).toEqual({pending:false,error:null});expect(statuses.at(-1)).toBe(false);
  expect(JSON.parse(localStorage.getItem(workspaceDocumentStorageKey(s.document_id))!).tiptap_json).toEqual(state('latest').tiptap_json);
 });
 it('fails closed without Web Locks and preserves the original primary bytes',async()=>{
  const locks=navigator.locks;Object.defineProperty(navigator,'locks',{configurable:true,value:undefined});
  try{const s=state();const writer=new WorkspaceDraftCoordinator(localStorage,s.document_id,()=>{});
   await expect(writer.write(s)).rejects.toThrow(/coordinate safe draft writes/);
   expect(localStorage.getItem(workspaceDocumentStorageKey(s.document_id))).toBeNull();
  }finally{Object.defineProperty(navigator,'locks',{configurable:true,value:locks});}
 });
 it('refuses a stale discard rather than silently proceeding',async()=>{
  const s=state();const raw=JSON.stringify(s);localStorage.setItem(workspaceDocumentStorageKey(s.document_id),raw);
  const writer=new WorkspaceDraftCoordinator(localStorage,s.document_id,()=>{});await writer.run(()=>{},{expectedRaw:raw});
  await expect(writer.clear(()=>false)).rejects.toThrow(/changed before discard/);
  expect(localStorage.getItem(workspaceDocumentStorageKey(s.document_id))).toBe(raw);
 });
});
