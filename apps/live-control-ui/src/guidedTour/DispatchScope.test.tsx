import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {useRef,useState} from 'react';
import {beforeEach,expect,it,vi} from 'vitest';
import {GuidedTourProvider,useGuidedTour,useTourOwnerReading,type TourDispatchScope} from './GuidedTour';
import {TourImageProvider,useTourImage} from './ImageObservations';
import {createWalkthrough,reduceTour,type TargetPin} from './protocol';
import {pointerKey,readWalkthrough,writeWalkthrough} from './storage';
const plan:TargetPin={kind:'plan',worldId:'world',objectId:'plan',revision:1,revisionId:'work',digest:'a'.repeat(64)};
const source:TargetPin={kind:'source',worldId:'world',objectId:'source',revision:1,digest:plan.digest};
const page:TargetPin={...source,kind:'page'};
const asset='ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
function Driver(){
 const tour=useGuidedTour()!,image=useTourImage()!,finish=useRef(()=>{});
 const [saved,setSaved]=useState<{scope:TourDispatchScope|null;at:string}|null>(null);
 useTourOwnerReading({step:'authoring',target:page,control:'save',status:'ready',dispatchScope:saved?.scope,...(saved?{observation:{step:'authoring',target:page,origin:'acknowledged',observedAt:saved.at,receiptId:'source-save'}}:{})});
 useTourOwnerReading({step:'source',target:source,control:'source',status:'ready'});
 useTourOwnerReading({step:'plan',target:plan,control:'plan',status:'ready'});
 return <><button onClick={tour.open}>Open guidance</button><button onClick={()=>{const scope=tour.captureScope();finish.current=()=>{setSaved({scope,at:new Date().toISOString()});tour.recordRunCreation({step:'play',target:{kind:'run',worldId:'world',objectId:'run',revision:1,digest:plan.digest},parent:plan,origin:'acknowledged',observedAt:new Date().toISOString(),receiptId:'created',proof:{kind:'run-creation',entrySceneId:'scene',preparedSceneIds:['scene']}},scope);image.generated([asset],'model',scope);};}}>Dispatch ordinary work</button><button onClick={()=>finish.current()}>Resolve ordinary work</button><button onClick={()=>image.placed(asset)}>Place image</button></>;
}
beforeEach(()=>{localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:vi.fn(async(_name:string,callback:()=>unknown)=>callback())}});});
it.each(['restart','cross-tab'] as const)('does not credit pending Run/image work to a replacement walkthrough: %s',async mode=>{
 let a=createWalkthrough('world','conks','A','2026-01-01T00:00:00Z');a=reduceTour(a,{kind:'bind',pin:plan});a=reduceTour(a,{kind:'bind',pin:source});a=reduceTour(a,{kind:'bind',pin:page});writeWalkthrough(localStorage,a,null);
 render(<GuidedTourProvider worldId='world'><TourImageProvider worldId='world' documentId='plan' verified={{pin:plan,assetIds:[asset]}}><Driver/></TourImageProvider></GuidedTourProvider>);
 fireEvent.click(screen.getByText('Open guidance'));fireEvent.click(screen.getByText('Dispatch ordinary work'));
 if(mode==='restart'){
  fireEvent.click(screen.getByText('Restart guidance'));
  await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.id).not.toBe('A'));
  fireEvent.click(screen.getByRole('button',{name:'Use this source'}));
  await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.bindings.source).toEqual(source));
  fireEvent.click(screen.getByRole('button',{name:'Next'}));
  await screen.findByRole('button',{name:'Use this page'});fireEvent.click(screen.getByRole('button',{name:'Use this page'}));
  await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.bindings.page).toEqual(page));
  fireEvent.click(screen.getByText('Steps and demonstrated results'));
  fireEvent.click(screen.getByRole('button',{name:'Prepare the Plan'}));
  await screen.findByRole('button',{name:'Use this plan'});fireEvent.click(screen.getByRole('button',{name:'Use this plan'}));
  await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.bindings.plan).toEqual(plan));
 }else{
  await act(async()=>{const previous=readWalkthrough(localStorage,'world')!;let b=createWalkthrough('world','conks','B',new Date().toISOString());b=reduceTour(b,{kind:'bind',pin:plan});b=reduceTour(b,{kind:'bind',pin:source});b=reduceTour(b,{kind:'bind',pin:page});writeWalkthrough(localStorage,b,previous);window.dispatchEvent(new StorageEvent('storage',{key:pointerKey('world')}));});
 }
 fireEvent.click(screen.getByText('Resolve ordinary work'));fireEvent.click(screen.getByText('Place image'));
 await act(async()=>{});
 const b=readWalkthrough(localStorage,'world')!.record;
 expect(b.bindings.run).toBeUndefined();expect(b.steps.play.state).toBe('pending');expect(b.steps.authoring.state).toBe('existing');expect(b.steps.image.state).not.toBe('completed');
 // The same asset can still be inspected as an existing example in the new walkthrough.
 expect(b.steps.image.evidence.every(item=>item.origin==='existing')).toBe(true);
});

it('credits an owner acknowledgment only when its captured dispatch still belongs to this walkthrough',async()=>{
 let a=createWalkthrough('world','conks','A','2026-01-01T00:00:00Z');a=reduceTour(a,{kind:'bind',pin:plan});a=reduceTour(a,{kind:'bind',pin:source});a=reduceTour(a,{kind:'bind',pin:page});writeWalkthrough(localStorage,a,null);
 render(<GuidedTourProvider worldId='world'><TourImageProvider worldId='world' documentId='plan' verified={{pin:plan,assetIds:[asset]}}><Driver/></TourImageProvider></GuidedTourProvider>);
 fireEvent.click(screen.getByText('Dispatch ordinary work'));fireEvent.click(screen.getByText('Resolve ordinary work'));
 await waitFor(()=>expect(readWalkthrough(localStorage,'world')?.record.steps.authoring.state).toBe('completed'));
 expect(readWalkthrough(localStorage,'world')?.record.steps.play.state).toBe('completed');
});
