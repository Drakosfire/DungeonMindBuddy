import type {ReactNode} from 'react';
import {cleanup,render,screen} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {useGenerationPlan} from '../guidedTour/GenerationObservations';
import type {TargetPin} from '../guidedTour/protocol';
import {useStatblockWorkbenchProjection} from './statblockWorkbenchProjection';
const catalog=vi.hoisted(()=>({entry:null as null|{render:()=>ReactNode},register:vi.fn()}));
vi.mock('../agentInteraction/useAgentInteraction',()=>({useAgentInteraction:()=>({registerProjectionCatalog:catalog.register})}));
vi.mock('../ui/deferredComponent',()=>({deferredComponent:()=>function Probe(){const pin=useGenerationPlan();return <output data-testid='projected-plan'>{JSON.stringify(pin)}</output>;}}));
function Owner({pin}:{pin:TargetPin|null}){useStatblockWorkbenchProjection('plan',pin);return null;}
afterEach(()=>{cleanup();vi.clearAllMocks();});
it('carries the exact verified pin into a sibling app-level projection host and refreshes it on owner change',()=>{
 catalog.register.mockImplementation(entry=>{catalog.entry=entry;return()=>{};});
 const pin:TargetPin={kind:'plan',worldId:'world',objectId:'p',revision:2,revisionId:'wr2',digest:'a'.repeat(64)};
 const owner=render(<Owner pin={pin}/>);
 const projection=render(catalog.entry!.render());expect(screen.getByTestId('projected-plan')).toHaveTextContent(JSON.stringify(pin));projection.unmount();
 owner.rerender(<Owner pin={null}/>);render(catalog.entry!.render());expect(screen.getByTestId('projected-plan')).toHaveTextContent('null');
});
