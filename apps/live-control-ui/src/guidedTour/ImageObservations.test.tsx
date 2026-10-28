import {fireEvent,render,screen} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import {TourImageProvider,useTourImage,collectTourMediaAssets} from './ImageObservations';
import type {TourOwnerReading} from './GuidedTour';
import {validObservation} from './protocol';
const readings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
vi.mock('./GuidedTour',()=>({useGuidedTour:()=>({tracking:true}),useTourOwnerReading:(reading:TourOwnerReading)=>readings.set(reading.step,reading)}));
const assetId='ac6c15cc-8c68-4732-8ae2-d9f3f051393a';
const pin={kind:'plan' as const,worldId:'world',objectId:'plan',revision:3,revisionId:'work-3',digest:'a'.repeat(64)};
function Controls(){const image=useTourImage();return <><button onClick={()=>image?.generated([assetId],'actual-model')}>Observed generation</button><button onClick={()=>image?.placed(assetId)}>Verified placement</button></>;}
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
