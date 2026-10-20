import {act,cleanup,renderHook} from '@testing-library/react';
import {useLayoutEffect} from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {hasWorldConversationRecovery,useWorldConversationActivation} from './worldConversationActivation';

afterEach(()=>{cleanup();vi.restoreAllMocks();localStorage.clear();sessionStorage.clear()});
const world='marsh:100%/み';
const encoded=encodeURIComponent(world);
const keys=[`dmb:world-plan-pending-ask:v1:${encoded}:any-document:pending`,
 `dmb:world-agent-new-conversation:v1:${encoded}:command`,
 `dmb:world-play-pending-turn:v1:${encoded}`,
 `dmb:world-command-resolution:v1:${encoded}:doc:command`];

it.each(keys)('activates on presence alone without reading or modifying %s',key=>{
 localStorage.setItem(key,'');const read=vi.spyOn(Storage.prototype,'getItem');
 const write=vi.spyOn(Storage.prototype,'setItem');const remove=vi.spyOn(Storage.prototype,'removeItem');
 expect(hasWorldConversationRecovery(world)).toBe(true);
 expect(read).not.toHaveBeenCalled();expect(write).not.toHaveBeenCalled();expect(remove).not.toHaveBeenCalled();
});
it('does not confuse other Worlds, unencoded keys, unrelated keys or suffixed Play keys',()=>{
 for(const key of [`dmb:world-plan-pending-ask:v1:${encoded}extra:doc:turn`,
  `dmb:world-agent-new-conversation:v1:${encoded}extra:command`,
  `dmb:world-play-pending-turn:v1:${encoded}:suffix`,
  `dmb:world-plan-pending-ask:v1:${world}:doc:turn`,'draft:other']) localStorage.setItem(key,'malformed');
 expect(hasWorldConversationRecovery(world)).toBe(false);
});
it.each(['inaccessible','overflow','key-error'])('conservatively activates for %s storage',mode=>{
 const key=vi.fn((index:number)=>{if(mode==='key-error'&&index===1)throw new Error('blocked');return 'unrelated'});
 vi.spyOn(window,'localStorage','get').mockImplementation(()=>{
  if(mode==='inaccessible')throw new Error('blocked');
  return {length:mode==='overflow'?257:2,key} as unknown as Storage;
 });
 expect(hasWorldConversationRecovery(world)).toBe(true);
 if(mode==='overflow')expect(key).not.toHaveBeenCalled();
});
it('stays activated after leaving a surface and clearing its marker',()=>{
 const view=renderHook(({active})=>useWorldConversationActivation(world,active),{initialProps:{active:false}});
 expect(view.result.current).toBe(false);view.rerender({active:true});expect(view.result.current).toBe(true);
 localStorage.clear();view.rerender({active:false});expect(view.result.current).toBe(true);
});
it('handles cross-tab storage and clear events, ignores provable sessionStorage',()=>{
 const view=renderHook(()=>useWorldConversationActivation(world,false));expect(view.result.current).toBe(false);
 localStorage.setItem(keys[0]!,'malformed');
 act(()=>window.dispatchEvent(new StorageEvent('storage',{key:keys[0],storageArea:sessionStorage})));
 expect(view.result.current).toBe(false);
 act(()=>window.dispatchEvent(new StorageEvent('storage',{key:'unrelated',storageArea:localStorage})));
 expect(view.result.current).toBe(false);
 act(()=>window.dispatchEvent(new StorageEvent('storage',{key:null,storageArea:localStorage})));
 expect(view.result.current).toBe(true);
});
it('observes relevant malformed marker creation in another tab',()=>{
 const view=renderHook(()=>useWorldConversationActivation(world,false));
 localStorage.setItem(keys[2]!,'{broken');
 act(()=>window.dispatchEvent(new StorageEvent('storage',{key:keys[2],storageArea:localStorage})));
 expect(view.result.current).toBe(true);expect(localStorage.getItem(keys[2]!)).toBe('{broken');
});
it('rescans after listener installation for a marker created between render and passive effects',()=>{
 const view=renderHook(()=>{
  const active=useWorldConversationActivation(world,false);
  useLayoutEffect(()=>{localStorage.setItem(keys[1]!,'{broken')},[]);
  return active;
 });
 expect(view.result.current).toBe(true);
});
