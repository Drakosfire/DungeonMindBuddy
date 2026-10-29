import {describe,it,expect,vi} from 'vitest';
import {act,render} from '@testing-library/react';
import {createWalkthrough,type TargetPin} from './protocol';
import {navigationScope,tourDestination,TourNavigationRegistry,TourNavigationProvider,useTourNavigationOwner,useTourNavigationGuard,type NavigationOwner,type NavigationScope,type NavigationGuard} from './Navigation';
const pin:TargetPin={kind:'plan',worldId:'world',objectId:'plan',revision:2,revisionId:'version',digest:'a'.repeat(64)};
function setup(){const walk=createWalkthrough('world','conks','walk',new Date().toISOString());walk.index=2;walk.bindings.plan=pin;let scope:NavigationScope|null=navigationScope(walk,0);return {registry:new TourNavigationRegistry(()=>scope),scope:scope!,setScope:(next:NavigationScope|null)=>{scope=next;}};}
function owner(perform:NavigationOwner['inspections'][number]['perform']=vi.fn()):NavigationOwner{return {worldId:'world',surface:'plan',objectId:'plan',inspections:[{id:'preview',label:'Open saved Plan preview',step:'plan',target:pin,impact:'projection',perform}]};}
describe('tour navigation intent',()=>{
 it('uses explicit bound identities and normal choosers without inferring latest',()=>{const {scope}=setup();expect(tourDestination(scope)).toEqual({surface:'plan',pin,href:'/plan?world=world&documentId=plan'});expect(tourDestination({...scope,step:'source'})).toEqual({surface:'build',pin:null,href:'/build?world=world'});expect(tourDestination({...scope,step:'progress'})).toEqual({surface:'play',pin:null,href:'/play?world=world&choose=1'});expect(()=>tourDestination({...scope,bindings:{plan:{...pin,worldId:'other'}}})).toThrow('another World');});
 it('pausing has no live navigation scope',()=>{const walk=createWalkthrough('world','conks','walk',new Date().toISOString());walk.phase='paused';expect(navigationScope(walk,0)).toBeNull();});
 it.each(['worldId','walkthroughId','epoch','index','step'] as const)('rejects stale %s before dispatch',async field=>{const {registry,scope,setScope}=setup(),perform=vi.fn(),registration=registry.registerOwner(()=>owner(perform));setScope({...scope,[field]:typeof scope[field]==='number'?99:'changed'} as NavigationScope);await expect(registry.inspect(scope,registration.token,'preview')).rejects.toThrow();expect(perform).not.toHaveBeenCalled();});
 it('does not silently accept a newer revision',async()=>{const {registry,scope}=setup(),perform=vi.fn(),newer=owner(perform);newer.inspections=[{...newer.inspections[0],target:{...pin,revision:3}}];const registration=registry.registerOwner(()=>newer);await expect(registry.inspect(scope,registration.token,'preview')).rejects.toThrow();expect(perform).not.toHaveBeenCalled();});
 it('refuses duplicate owners',async()=>{const {registry,scope}=setup(),perform=vi.fn(),a=registry.registerOwner(()=>owner(perform));registry.registerOwner(()=>owner(perform));await expect(registry.inspect(scope,a.token,'preview')).rejects.toThrow();expect(perform).not.toHaveBeenCalled();});
 it.each(['unmount','guard','restart','pins'] as const)('rechecks %s after an asynchronous read',async kind=>{
  const {registry,scope,setScope}=setup();let reason:string|null=null;registry.registerGuard(()=>({worldId:'world',reason:()=>reason}));let release!:()=>void;const wait=new Promise<void>(resolve=>{release=resolve}),publish=vi.fn();
  const registration=registry.registerOwner(()=>owner(async request=>{await wait;if(request.isCurrent())publish();}));const result=registry.inspect(scope,registration.token,'preview');
  if(kind==='unmount')registration.release();if(kind==='guard')reason='The old editor now has unsaved edits.';if(kind==='restart')setScope({...scope,walkthroughId:'new'});if(kind==='pins')setScope({...scope,bindings:{plan:{...pin,revision:3}}});release();await result;expect(publish).not.toHaveBeenCalled();
 });
 it('leaves results and bindings untouched when opening an inspection',async()=>{const {registry,scope}=setup(),before=structuredClone(scope),perform=vi.fn(),registration=registry.registerOwner(()=>owner(perform));await registry.inspect(scope,registration.token,'preview');expect(perform).toHaveBeenCalledTimes(1);expect(scope).toEqual(before);});
 it('keeps registration stable through busy renders with current callbacks and guards',async()=>{
  const {registry,scope}=setup(),first=vi.fn(),second=vi.fn();function Owner({value,guard}:{value:NavigationOwner;guard:NavigationGuard}){useTourNavigationOwner(value);useTourNavigationGuard(guard);return null;}
  const mounted=render(<TourNavigationProvider registry={registry}><Owner value={owner(first)} guard={{worldId:'world',reason:()=>null}}/></TourNavigationProvider>);const token=registry.inspections(scope)[0].owner;
  mounted.rerender(<TourNavigationProvider registry={registry}><Owner value={owner(second)} guard={{worldId:'world',reason:()=>null}}/></TourNavigationProvider>);expect(registry.inspections(scope)[0].owner).toBe(token);await act(()=>registry.inspect(scope,token,'preview'));expect(first).not.toHaveBeenCalled();expect(second).toHaveBeenCalledTimes(1);
  mounted.rerender(<TourNavigationProvider registry={registry}><Owner value={owner(second)} guard={{worldId:'world',reason:()=> 'Saving an exact command.'}}/></TourNavigationProvider>);await expect(registry.inspect(scope,token,'preview')).rejects.toThrow();mounted.unmount();expect(registry.inspections(scope)).toHaveLength(0);
 });
 it('exempts only the selection reservation’s own loading state, retaining all other live holds',async()=>{
  const {registry,scope}=setup();let owned:symbol|null=null,busy=false,dirty=false;
  registry.registerGuard(()=>({worldId:'world',reason:(_impact,reservation)=>dirty?'New unsaved edits':busy&&reservation!==owned?'Another selection is loading':null}));
  let release!:()=>void;const wait=new Promise<void>(resolve=>{release=resolve}),publish=vi.fn();
  const live=owner();live.select=async(_pin,request)=>{owned=request.reservation;busy=true;expect(request.isCurrent()).toBe(true);await wait;if(request.isCurrent())publish();busy=false;};
  const registration=registry.registerOwner(()=>live);const result=registry.select(scope,registration.token,pin);
  expect(registry.departureReason(scope,'departure')).toBe('Another selection is loading');dirty=true;release();await result;expect(publish).not.toHaveBeenCalled();
 });
 it('refuses a Run inspection whose owner reports a different Plan parent',async()=>{
  const {registry,scope,setScope}=setup(),run={...pin,kind:'run' as const,objectId:'run'};const selected={...scope,step:'combat' as const,index:10,bindings:{plan:pin,run}};setScope(selected);
  const perform=vi.fn(),live:NavigationOwner={role:'panel',worldId:'world',surface:'play',objectId:'run',parent:{...pin,objectId:'foreign-plan'},inspections:[{id:'fight',step:'combat',label:'Open encounter',target:run,impact:'projection',perform}]};
  const registration=registry.registerOwner(()=>live);await expect(registry.inspect(selected,registration.token,'fight')).rejects.toThrow();expect(perform).not.toHaveBeenCalled();
 });
 it('tolerates owner removal during a layout update and rejects the retired registration',async()=>{
  const {registry,scope}=setup();let live:NavigationOwner|null=owner();const registration=registry.registerOwner(()=>live);live=null;expect(registry.inspections(scope)).toEqual([]);await expect(registry.inspect(scope,registration.token,'preview')).rejects.toThrow();registration.release();
 });

 it.each(['restart','step','epoch','pins'] as const)('invalidates a captured destination on %s while retaining its restriction',kind=>{
  const {registry,scope,setScope}=setup();window.history.replaceState({},'','/plan?world=world&documentId=plan');registry.beginDestination(scope);
  const first=registry.claimDestination('plan','world','plan')!,strictReplay=registry.claimDestination('plan','world','plan')!;
  expect(first.isCurrent()).toBe(true);expect(strictReplay.isCurrent()).toBe(true);
  setScope(kind==='restart'?{...scope,walkthroughId:'new'}:kind==='step'?{...scope,index:3,step:'encounter'}:kind==='epoch'?{...scope,epoch:1}:{...scope,bindings:{plan:{...pin,revision:3}}});
  expect(first.isCurrent()).toBe(false);first.complete();expect(registry.claimDestination('plan','world','plan')?.isCurrent()).toBe(false);
  registry.discardDestination('plan');expect(registry.claimDestination('plan','world','plan')).toBeNull();
 });
 it('does not consume a destination during an abandoned StrictMode load or source unmount',()=>{
  const {registry,scope}=setup();window.history.replaceState({},'','/plan?world=world&documentId=plan');const source=registry.registerOwner(()=>owner());registry.beginDestination(scope);
  const abandoned=registry.claimDestination('plan','world','plan')!;source.release();expect(abandoned.isCurrent()).toBe(true);
  const admitted=registry.claimDestination('plan','world','plan')!;expect(admitted.isCurrent()).toBe(true);admitted.complete();expect(registry.claimDestination('plan','world','plan')).toBeNull();
 });

});
