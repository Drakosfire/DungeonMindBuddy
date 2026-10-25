import {StrictMode,type ReactNode} from 'react';
import {act,cleanup,renderHook} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {composerDraftStorageKey,useConversationComposerDrafts,COMPOSER_DRAFT_READ_WARNING,COMPOSER_DRAFT_WRITE_WARNING} from './conversationComposerDrafts';
beforeEach(()=>sessionStorage.clear());
afterEach(()=>{cleanup();vi.restoreAllMocks();sessionStorage.clear();});
const wrap=({children}:{children:ReactNode})=><StrictMode>{children}</StrictMode>;

it('persists exact text synchronously, isolates work slots, and restores after remount',()=>{
 const first=renderHook(()=>useConversationComposerDrafts('world'),{wrapper:wrap});
 const text='  lantern 🕯️\nunfinished thought  ';
 act(()=>first.result.current.setComposerDrafts({'build:doc':text,'plan:plan':'Plan thought','play:run':'Run thought'}));
 const stored=JSON.parse(sessionStorage.getItem(composerDraftStorageKey('world'))!);
 expect(stored.drafts['build:doc']).toBe(text);
 first.unmount();
 const next=renderHook(()=>useConversationComposerDrafts('world'),{wrapper:wrap});
 expect(next.result.current.composerDrafts).toEqual(stored.drafts);
 act(()=>next.result.current.setComposerDrafts(d=>({...d,'build:doc':''})));
 expect(JSON.parse(sessionStorage.getItem(composerDraftStorageKey('world'))!).drafts).toEqual({'plan:plan':'Plan thought','play:run':'Run thought'});
 act(()=>next.result.current.setComposerDrafts({}));
 expect(sessionStorage.getItem(composerDraftStorageKey('world'))).toBeNull();
});

it('retains consecutive functional edits once each under Strict Mode',()=>{
 const hook=renderHook(()=>useConversationComposerDrafts('world'),{wrapper:wrap});
 const writes=vi.spyOn(Storage.prototype,'setItem');
 act(()=>{
  hook.result.current.setComposerDrafts(d=>({...d,'build:doc':'first'}));
  hook.result.current.setComposerDrafts(d=>({...d,'play:run':'next'}));
 });
 expect(hook.result.current.composerDrafts).toEqual({'build:doc':'first','play:run':'next'});
 expect(writes).toHaveBeenCalledTimes(2);
 expect(JSON.parse(sessionStorage.getItem(composerDraftStorageKey('world'))!).drafts).toEqual(hook.result.current.composerDrafts);
});

it('warns if storage silently fails to retain a write',()=>{
 const hook=renderHook(()=>useConversationComposerDrafts('world'));
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>undefined);
 act(()=>hook.result.current.setComposerDrafts({'build:doc':'keep locally'}));
 expect(hook.result.current.composerDraftWarning).toBe(COMPOSER_DRAFT_WRITE_WARNING);
 expect(hook.result.current.composerDrafts['build:doc']).toBe('keep locally');
});

it('loads each World on a prop change and rejects a retired World setter',()=>{
 const hook=renderHook(({world})=>useConversationComposerDrafts(world),{initialProps:{world:'A'}});
 act(()=>hook.result.current.setComposerDrafts({'build:doc':'A only'}));
 const retired=hook.result.current.setComposerDrafts;
 hook.rerender({world:'B'});
 expect(hook.result.current.composerDrafts).toEqual({});
 act(()=>hook.result.current.setComposerDrafts({'build:doc':'B only'}));
 act(()=>retired({'build:doc':'late A callback'}));
 expect(hook.result.current.composerDrafts).toEqual({'build:doc':'B only'});
 hook.rerender({world:'A'});
 expect(hook.result.current.composerDrafts).toEqual({'build:doc':'A only'});
});

it.each(['not json',JSON.stringify({schema:'dmb_conversation_composer_drafts_v1',world_id:'other',drafts:{'build:doc':'foreign'}}),
 JSON.stringify({schema:'dmb_conversation_composer_drafts_v1',world_id:'world',drafts:{'build:doc':42}})])('preserves unreadable or foreign bytes without exposing them: %s',raw=>{
 const key=composerDraftStorageKey('world');sessionStorage.setItem(key,raw);
 const hook=renderHook(()=>useConversationComposerDrafts('world'));
 expect(hook.result.current.composerDrafts).toEqual({});
 expect(hook.result.current.composerDraftWarning).toBe(COMPOSER_DRAFT_READ_WARNING);
 act(()=>hook.result.current.setComposerDrafts({'build:doc':'new in-memory text'}));
 expect(hook.result.current.composerDrafts['build:doc']).toBe('new in-memory text');
 expect(sessionStorage.getItem(key)).toBe(raw);
});

it('keeps typing on write failure, then records the latest text after access recovers',()=>{
 const hook=renderHook(()=>useConversationComposerDrafts('world'));
 const denied=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new DOMException('quota','QuotaExceededError');});
 act(()=>hook.result.current.setComposerDrafts({'build:doc':'first'}));
 expect(hook.result.current.composerDrafts['build:doc']).toBe('first');
 expect(hook.result.current.composerDraftWarning).toBe(COMPOSER_DRAFT_WRITE_WARNING);
 denied.mockRestore();
 act(()=>hook.result.current.setComposerDrafts(d=>({...d,'build:doc':'latest'})));
 expect(hook.result.current.composerDraftWarning).toBeNull();
 expect(JSON.parse(sessionStorage.getItem(composerDraftStorageKey('world'))!).drafts['build:doc']).toBe('latest');
});

it('does not overwrite unknown stored work after a denied read',()=>{
 const key=composerDraftStorageKey('world');sessionStorage.setItem(key,'retained bytes');
 const denied=vi.spyOn(Storage.prototype,'getItem').mockImplementation(()=>{throw new DOMException('denied','SecurityError');});
 const hook=renderHook(()=>useConversationComposerDrafts('world'));
 expect(hook.result.current.composerDraftWarning).toBe(COMPOSER_DRAFT_READ_WARNING);
 denied.mockRestore();
 act(()=>hook.result.current.setComposerDrafts({'build:doc':'new'}));
 expect(sessionStorage.getItem(key)).toBe('retained bytes');
});

it('keeps independent tab session stores separate for the same World and work',()=>{
 const descriptor=Object.getOwnPropertyDescriptor(window,'sessionStorage')!;
 function store():Storage{const values=new Map<string,string>();return {get length(){return values.size;},clear:()=>values.clear(),key:i=>[...values.keys()][i]??null,
  getItem:key=>values.get(key)??null,setItem:(key,value)=>{values.set(key,value);},removeItem:key=>{values.delete(key);}};}
 const a=store(),b=store();
 try{
  Object.defineProperty(window,'sessionStorage',{value:a,configurable:true});
  const first=renderHook(()=>useConversationComposerDrafts('world'));
  act(()=>first.result.current.setComposerDrafts({'build:doc':'Tab A'}));first.unmount();
  Object.defineProperty(window,'sessionStorage',{value:b,configurable:true});
  const second=renderHook(()=>useConversationComposerDrafts('world'));
  expect(second.result.current.composerDrafts).toEqual({});
  act(()=>second.result.current.setComposerDrafts({'build:doc':'Tab B'}));second.unmount();
  Object.defineProperty(window,'sessionStorage',{value:a,configurable:true});
  const restored=renderHook(()=>useConversationComposerDrafts('world'));
  expect(restored.result.current.composerDrafts['build:doc']).toBe('Tab A');restored.unmount();
  expect(JSON.parse(b.getItem(composerDraftStorageKey('world'))!).drafts['build:doc']).toBe('Tab B');
 }finally{Object.defineProperty(window,'sessionStorage',descriptor);}
});
