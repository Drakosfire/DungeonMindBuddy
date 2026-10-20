import {fireEvent,render,screen} from '@testing-library/react';
import {useEffect,useMemo} from 'react';
import {expect,it,vi} from 'vitest';
import {AgentInteractionProvider,useAgentInteraction} from '../agentInteraction/AgentInteractionProvider';
import {usePublishSurfaceInteraction} from '../agentInteraction/usePublishSurfaceInteraction';
import {buildSurfaceInteractionIdentity} from '../surfaceInteraction/surfaceIdentity';
import {ToolHost} from '../surfaceInteraction/toolHost/ToolHost';
import {LegacyProjectionHostAdapter} from '../planSurface/projection/LegacyProjectionHostAdapter';
import {RULES_LOOKUP_PROJECTION,RULES_LOOKUP_TOOL,useRulesLookupProjection} from './rulesLookupProjection';
vi.mock('./RulesLookupTool',()=>({default:()=> <section aria-label="Rules body">Current Rules renderer</section>}));
let staleOpen!:(id:string)=>boolean;
function Publisher({id='A',surface='plan',enabled=true,registered=true}:{id?:string;surface?:string;enabled?:boolean;registered?:boolean}){
 const publication=useMemo(()=>({surfaceId:surface,label:surface,identity:buildSurfaceInteractionIdentity({surfaceId:surface,instanceParts:[id]}),canvas:null,agentContext:null,
  tools:enabled?[RULES_LOOKUP_TOOL]:[],editCommands:[],projections:enabled?[RULES_LOOKUP_PROJECTION]:[],projectionBindings:[]}),[id,surface,enabled]);
 usePublishSurfaceInteraction(publication);
 useRulesLookupProjection(surface,enabled&&registered);
 const {openTool}=useAgentInteraction();
 useEffect(()=>{staleOpen=openTool},[openTool]);
 return <><input aria-label="Source draft" defaultValue="retain"/><ToolHost/><LegacyProjectionHostAdapter/></>;
}
const fixture=(props:Parameters<typeof Publisher>[0])=><AgentInteractionProvider><Publisher {...props}/></AgentInteractionProvider>;
it.each(['plan','build'])('uses the shared current published host for explicit %s Rules capability',async surface=>{
 render(fixture({surface}));expect(screen.queryByRole('region',{name:'Rules body'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Tools',exact:true}));fireEvent.click(screen.getByRole('button',{name:'Rules Lookup',exact:true}));
 expect(await screen.findByRole('region',{name:'Rules body'})).toHaveTextContent('Current Rules renderer');
});
it('retires the active renderer on identity change and rejects stale open callbacks',async()=>{
 const view=render(fixture({}));fireEvent.click(screen.getByRole('button',{name:'Tools',exact:true}));fireEvent.click(screen.getByRole('button',{name:'Rules Lookup',exact:true}));await screen.findByRole('region',{name:'Rules body'});
 const old=staleOpen;const draft=screen.getByRole('textbox',{name:'Source draft'});
 view.rerender(fixture({id:'B'}));expect(screen.queryByRole('region',{name:'Rules body'})).not.toBeInTheDocument();
 expect(old('rules-lookup')).toBe(false);expect(screen.getByRole('textbox',{name:'Source draft'})).toBe(draft);
});
it('removing the published capability closes its renderer and launcher',async()=>{
 const view=render(fixture({}));fireEvent.click(screen.getByRole('button',{name:'Tools',exact:true}));fireEvent.click(screen.getByRole('button',{name:'Rules Lookup',exact:true}));await screen.findByRole('region',{name:'Rules body'});
 view.rerender(fixture({enabled:false}));expect(screen.queryByRole('region',{name:'Rules body'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Tools',exact:true})).not.toBeInTheDocument();
});
it('does not substitute a renderer when the current catalog is unregistered',async()=>{
 render(fixture({registered:false}));fireEvent.click(screen.getByRole('button',{name:'Tools',exact:true}));fireEvent.click(screen.getByRole('button',{name:'Rules Lookup',exact:true}));
 expect(await screen.findByText('Unknown tool: rules-lookup')).toBeInTheDocument();expect(screen.queryByRole('region',{name:'Rules body'})).not.toBeInTheDocument();
});
