import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {useEffect,useId,useLayoutEffect,useRef,useState} from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import type {WorldPlanAgentConversationProps} from '../planSurface/components/WorldPlanAgentConversation';
import {WorldAgentConversation,WorldAgentConversationProvider,WorldPlanConversationRegistration,useWorldAgentConversationState} from './WorldAgentConversation';

const moduleState=vi.hoisted(()=>{
 let resolve!:()=>void;const ready=new Promise<void>(r=>{resolve=r});
 return {ready,resolve,loads:0,attempts:0,mounts:[] as string[],unmounts:[] as string[]};
});
vi.mock('../ui/deferredComponent',async importOriginal=>{
 const actual=await importOriginal<typeof import('../ui/deferredComponent')>();
 return {...actual,deferredComponent:(load:()=>Promise<any>,label:string)=>{
  let loading:Promise<any>|undefined;
  return actual.deferredComponent(()=>{
   moduleState.attempts++;
   // Share the controlled module load, as native imports do, across World remounts.
   const pending=loading??=(async()=>{await moduleState.ready;return load()})();
   void pending.finally(()=>{if(loading===pending)loading=undefined});
   return pending;
  },label);
 }};
});
vi.mock('../planSurface/components/WorldPlanAgentConversation',()=>{
 moduleState.loads++;
 return {WorldPlanAgentConversation:(props:WorldPlanAgentConversationProps)=>{
  const [draft,setDraft]=useState('');const id=useId();
  useEffect(()=>{moduleState.mounts.push(props.worldId);return()=>{moduleState.unmounts.push(props.worldId)}},[]);
  return <section data-testid="controller" data-world={props.worldId} data-document={props.documentId??''}
    data-visible={String(props.visible)} data-mode={props.playMode?'play':props.buildMode?'build':'plan'}>
    <input id={id} aria-label={`Draft ${props.worldId}`} value={draft} onChange={event=>setDraft(event.target.value)}/>
  </section>;
 }};
});
afterEach(()=>{cleanup();localStorage.clear()});
function props(worldId:string,documentId:string):WorldPlanAgentConversationProps{return{
 worldId,worldName:worldId,documentId,surfaceInstanceId:`surface-${documentId}`,revision:1,editBridge:null,
 draftGeneration:0,selectionGeneration:0,savedDirty:false,pageReady:true,saveInFlight:false,
}}
function Publish({world,document,surface,hold}:{world:string;document:string;surface:string;hold:string|null}){
 const registry=useWorldAgentConversationState();const token=useRef(Symbol('test-plan'));
 useLayoutEffect(()=>{
  if(surface!=='plan')return;
  registry!.registerPlan(token.current,props(world,document));
  return()=>registry!.unregisterPlan(token.current);
 },[registry?.registerPlan,registry?.unregisterPlan,world,document,surface]);
 useLayoutEffect(()=>{
  registry!.registerPlay(token.current,null,hold);
  return()=>registry!.unregisterPlay(token.current);
 },[registry?.registerPlay,registry?.unregisterPlay,hold]);
 return null;
}
function Fixture({world='A',document='plan-A',surface='other',hold=null}:{world?:string;document?:string;surface?:'plan'|'play'|'build'|'other';hold?:string|null}){
 return <WorldAgentConversationProvider worldId={world}><Publish world={world} document={document} surface={surface} hold={hold}/>
  <WorldAgentConversation surface={surface} worldId={world} worldName={world}/></WorldAgentConversationProvider>;
}
it('does not import inactive code; a suspended load uses latest World/context, then stays mounted across surfaces',async()=>{
 const view=render(<Fixture/>);await act(async()=>{});
 expect(moduleState.loads).toBe(0);expect(screen.queryByTestId('controller')).not.toBeInTheDocument();
 view.rerender(<Fixture surface="plan"/>);await waitFor(()=>expect(moduleState.attempts).toBe(1));
 view.rerender(<Fixture world="B" document="plan-B" surface="plan"/>);
 await act(async()=>{moduleState.resolve()});
 const input=await screen.findByRole('textbox',{name:'Draft B'});
 expect(screen.getByTestId('controller')).toHaveAttribute('data-document','plan-B');
 expect(moduleState.mounts).toEqual(['B']);expect(screen.queryByRole('textbox',{name:'Draft A'})).not.toBeInTheDocument();
 fireEvent.change(input,{target:{value:'Keep this draft'}});
 for(const surface of ['other','play','build','plan'] as const){
  view.rerender(<Fixture world="B" document="plan-B" surface={surface}/>);
  expect(screen.getByRole('textbox',{name:'Draft B'})).toBe(input);
  expect(input).toHaveValue('Keep this draft');
 }
 expect(moduleState.mounts).toEqual(['B']);
});
it('resets activation and cached Plan scope on a World change even without a parent provider key',async()=>{
 const view=render(<Fixture surface="plan"/>);const old=await screen.findByRole('textbox',{name:'Draft A'});
 fireEvent.change(old,{target:{value:'A only'}});
 view.rerender(<Fixture world="B" surface="other"/>);
 expect(screen.queryByTestId('controller')).not.toBeInTheDocument();
 view.rerender(<Fixture world="B" document="plan-B" surface="plan"/>);
 const fresh=await screen.findByRole('textbox',{name:'Draft B'});
 expect(fresh).toHaveValue('');expect(screen.getByTestId('controller')).toHaveAttribute('data-document','plan-B');
});
it('activates for an empty recovery marker without changing its bytes',async()=>{
 const key='dmb:world-play-pending-turn:v1:A';localStorage.setItem(key,'');
 render(<Fixture/>);await screen.findByRole('textbox',{name:'Draft A'});expect(localStorage.getItem(key)).toBe('');
});
it('activates on a cross-tab malformed marker, leaving validation to the controller',async()=>{
 render(<Fixture/>);expect(screen.queryByTestId('controller')).not.toBeInTheDocument();
 const key='dmb:world-agent-new-conversation:v1:A:command';localStorage.setItem(key,'{broken');
 act(()=>window.dispatchEvent(new StorageEvent('storage',{key,storageArea:localStorage})));
 await screen.findByRole('textbox',{name:'Draft A'});expect(localStorage.getItem(key)).toBe('{broken');
});
it('preserves the explicit unavailable-Play transport unmount and fresh clear behavior',async()=>{
 const view=render(<Fixture surface="plan"/>);const old=await screen.findByRole('textbox',{name:'Draft A'});
 view.rerender(<Fixture surface="play" hold="Session copy is not admitted"/>);
 expect(screen.getByRole('status')).toHaveTextContent('Session copy is not admitted');
 expect(screen.queryByTestId('controller')).not.toBeInTheDocument();
 view.rerender(<Fixture surface="play"/>);
 const fresh=await screen.findByRole('textbox',{name:'Draft A'});expect(fresh).not.toBe(old);
});
it('loads the same deferred component for a direct registration without a registry',async()=>{
 render(<WorldPlanConversationRegistration {...props('A','direct-plan')}/>);
 await screen.findByRole('textbox',{name:'Draft A'});
 expect(screen.getByTestId('controller')).toHaveAttribute('data-document','direct-plan');
});
