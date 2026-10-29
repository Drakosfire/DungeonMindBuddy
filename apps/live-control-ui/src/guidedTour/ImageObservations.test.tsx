import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import {TourImageProvider,useTourImage,collectTourMediaAssets} from './ImageObservations';
import {MediaImageWizard,type ImageGenerationPort} from '../media/MediaImageWizard';
import type {TourOwnerReading} from './GuidedTour';
import {validObservation} from './protocol';
const readings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
vi.mock('./GuidedTour',()=>({useGuidedTour:()=>({tracking:true,captureScope:()=>({worldId:"world",walkthroughId:"walk",epoch:0}),isScopeCurrent:()=>true}),useTourOwnerReading:(reading:TourOwnerReading)=>readings.set(reading.step,reading)}));
const assetId='ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
const pin={kind:'plan' as const,worldId:'world',objectId:'plan',revision:3,revisionId:'work-3',digest:'a'.repeat(64)};
function Controls(){const image=useTourImage();return <><button onClick={()=>image?.inspect({status:"pending",reason:"Generate and place an image."})}>Ready Studio</button><button onClick={()=>image?.inspect({status:"unavailable",reason:"Missing provider credential."})}>Blocked Studio</button><button onClick={()=>image?.inspect({status:"failed",reason:"Provider failed."})}>Failed Studio</button><button onClick={()=>image?.generated([assetId],'actual-model',image.captureScope())}>Observed generation</button><button onClick={()=>image?.placed(assetId)}>Verified placement</button></>;}
beforeEach(()=>readings.clear());
it('requires generation, verified placement and the saved Plan asset together',()=>{
 const mounted=render(<TourImageProvider worldId='world' documentId='plan' verified={null}><Controls/></TourImageProvider>);
 fireEvent.click(screen.getByText('Observed generation'));expect(readings.get('image')?.observation).toBeUndefined();
 fireEvent.click(screen.getByText('Verified placement'));expect(readings.get('image')?.observation).toBeUndefined();
 mounted.rerender(<TourImageProvider worldId='world' documentId='plan' verified={{pin,assetIds:[assetId]}}><Controls/></TourImageProvider>);
 const observation=readings.get('image')?.observation;expect(observation?.origin).toBe('acknowledged');expect(validObservation(observation,'world')).toBe(true);
 expect(observation?.proof).toMatchObject({kind:'generated-image',assetId,generation:'observed',savedPlanVersionId:'work-3'});
 mounted.rerender(<TourImageProvider worldId='world' documentId='plan' verified={{pin,assetIds:[]}}><Controls/></TourImageProvider>);
 expect(readings.get('image')?.observation).toBeUndefined();
});
it('labels a selected library image as an existing example',()=>{
 render(<TourImageProvider worldId='world' documentId='plan' verified={{pin,assetIds:[assetId]}}><Controls/></TourImageProvider>);
 fireEvent.click(screen.getByText('Verified placement'));expect(readings.get('image')?.observation?.origin).toBe('existing');
});
it('does not transfer selected images to another Plan',()=>{
 const mounted=render(<TourImageProvider worldId='world' documentId='plan' verified={{pin,assetIds:[assetId]}}><Controls/></TourImageProvider>);
 fireEvent.click(screen.getByText('Observed generation'));fireEvent.click(screen.getByText('Verified placement'));
 mounted.rerender(<TourImageProvider worldId='world' documentId='other' verified={{pin:{...pin,objectId:'other'},assetIds:[assetId]}}><Controls/></TourImageProvider>);
 expect(readings.get('image')?.observation).toBeUndefined();
});
it('collects only structured media nodes, not text mentioning an asset',()=>{
 expect(collectTourMediaAssets({type:'doc',content:[{type:'paragraph',content:[{type:'text',attrs:{assetId}}]},{type:'mediaImage',attrs:{assetId}}]})).toEqual([assetId]);
});

it('keeps missing demonstration pending and preserves actual Studio or host blocks',()=>{
 const mounted=render(<TourImageProvider worldId='world' documentId='plan' verified={{pin,assetIds:[]}}><Controls/></TourImageProvider>);
 expect(readings.get('image')?.status).toBe('pending');expect(readings.get('image')?.observation).toBeUndefined();
 fireEvent.click(screen.getByText('Ready Studio'));expect(readings.get('image')).toMatchObject({status:'pending',reason:'Generate and place an image.'});
 fireEvent.click(screen.getByText('Blocked Studio'));expect(readings.get('image')).toMatchObject({status:'unavailable',reason:'Missing provider credential.'});
 fireEvent.click(screen.getByText('Failed Studio'));expect(readings.get('image')).toMatchObject({status:'failed',reason:'Provider failed.'});
 mounted.rerender(<TourImageProvider worldId='world' documentId='plan' blockedReason='Recover the Plan first.' verified={{pin,assetIds:[]}}><Controls/></TourImageProvider>);
 expect(readings.get('image')).toMatchObject({status:'unavailable',reason:'Recover the Plan first.'});expect(readings.get('image')?.observation).toBeUndefined();
});

it('reads actual mounted Studio capability without generating or crediting artwork',async()=>{
 const port:ImageGenerationPort={capabilities:vi.fn().mockResolvedValue({configured:true,library_ready:true,storage_configured:false,models:[{id:'model',label:'Model',formats:['png'],controls:[]}]}),generate:vi.fn(),list:vi.fn(),get:vi.fn(),save:vi.fn()};
 const mounted=render(<TourImageProvider worldId='world' documentId='plan' verified={{pin,assetIds:[]}}><MediaImageWizard onClose={()=>{}} port={port}/></TourImageProvider>);
 await waitFor(()=>expect(readings.get('image')).toMatchObject({status:'pending',reason:expect.stringContaining('Generate an image')}));
 expect(readings.get('image')?.observation).toBeUndefined();expect(port.generate).not.toHaveBeenCalled();expect(port.save).not.toHaveBeenCalled();
 mounted.unmount();
 const blocked={...port,capabilities:vi.fn().mockResolvedValue({configured:false,library_ready:true,storage_configured:false,models:[{id:'model',label:'Model',formats:['png'],controls:[]}]})};
 render(<TourImageProvider worldId='world' documentId='plan' verified={{pin,assetIds:[]}}><MediaImageWizard onClose={()=>{}} port={blocked}/></TourImageProvider>);
 await waitFor(()=>expect(readings.get('image')).toMatchObject({status:'unavailable',reason:expect.stringContaining('fal credential')}));expect(port.generate).not.toHaveBeenCalled();
});
