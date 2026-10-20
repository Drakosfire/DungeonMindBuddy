import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useMemo, useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { AgentInteractionProvider } from '../agentInteraction/AgentInteractionProvider';
import { usePublishSurfaceInteraction } from '../agentInteraction/usePublishSurfaceInteraction';
import { buildSurfaceInteractionIdentity } from '../surfaceInteraction/surfaceIdentity';
import type { SurfaceInteractionPublication } from '../surfaceInteraction/types';
import { buildWorldPlanSurfaceIdentity } from '../planSurface/worldPlanIdentity';
import { PeekRegionProvider, PeekRegionSlot } from '../surfaceInteraction/peekHost';
import { DocumentReferenceSurfaceHost } from './DocumentReferenceSurfaceHost';
import type { DocumentInspection } from './resolveDocumentReference';
import type { Editor } from '@tiptap/core';
import { MarkdownEditorCore } from '../tiptap/MarkdownEditorCore';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
const A='bba72416-9dfe-49bb-add0-21a346e9a421',B='2cd1f643-a070-4cec-bbb0-24c803e30b98';
const source=`# Local draft\n\n[Source](/build?world=elderwyld&documentId=${A})`;
const data:DocumentInspection={title:'Saved source',markdown:'# Retained source',digest:'a'.repeat(64),revisionLabel:'Saved revision'};

// The owner changes local state and publishes its actual identity convention,
// just like the picker paths. App and the host receive no changed route/props.
function Owner({ surface, onEditor }: {surface:string;onEditor:(editor:Editor|null)=>void}) {
  const [id,setId]=useState(A),[view,setView]=useState('document'),[ready,setReady]=useState(true);
  const publication=useMemo<SurfaceInteractionPublication|null>(()=>ready?{
    surfaceId:surface,label:`${surface} ${view}`,
    identity:surface==='plan'?buildWorldPlanSurfaceIdentity({worldId:'elderwyld',documentId:id,localDraftId:null})
      :buildSurfaceInteractionIdentity({surfaceId:surface,instanceParts:surface==='build'?['build',id]:['play',id]}),
    canvas:surface==='play'?null:{canvasId:'markdown-canvas',workObject:{kind:'document',id}},
    agentContext:null,tools:[],editCommands:[],projections:[],projectionBindings:[],
  }:null,[surface,id,view,ready]);
  usePublishSurfaceInteraction(publication);
  return <>
    <button onClick={()=>{window.history.pushState({},'',`/${surface}?world=elderwyld&${surface==='play'?'run':'documentId'}=${B}`);setId(B);}}>Choose other document</button>
    <button onClick={()=>setReady(false)}>Retire source</button>
    <button onClick={()=>setView('cards')}>Cards view</button>
    <MarkdownEditorCore content={markdownToTiptapDoc(source).doc} documentKey="retained-writer" onEditorChange={onEditor}/>
  </>;
}
function Harness({surface,load,onEditor}:{surface:string;load:typeof import('./resolveDocumentReference').resolveDocumentReference;onEditor:(editor:Editor|null)=>void}) {
  return <AgentInteractionProvider><PeekRegionProvider>
    <DocumentReferenceSurfaceHost worldId="elderwyld" surface={surface} load={load}><Owner surface={surface} onEditor={onEditor}/></DocumentReferenceSurfaceHost>
    <PeekRegionSlot/>
  </PeekRegionProvider></AgentInteractionProvider>;
}

describe('source publication lifecycle',()=>{
  it.each(['build','plan','play'])('retires %s inspection after a local picker/pushState-only identity change',async surface=>{
    let resolve!:(value:DocumentInspection)=>void,editor:Editor|null=null;
    const load=vi.fn().mockImplementation(()=>new Promise<DocumentInspection>(done=>{resolve=done;}));
    render(<Harness surface={surface} load={load} onEditor={value=>{editor=value;}}/>);
    await waitFor(()=>expect(editor).not.toBeNull());
    const original=editor! as Editor;original.setOptions({editorProps:{handleScrollToSelection:()=>true}});
    act(()=>{original.commands.insertContent('unsaved ');});const before=original.getJSON();
    fireEvent.click(screen.getByRole('link',{name:'Source'}));await waitFor(()=>expect(load).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByText('Choose other document'));
    await waitFor(()=>expect(screen.queryByRole('region',{name:'Document reference'})).not.toBeInTheDocument());
    await act(async()=>resolve({...data,title:'OLD SOURCE'}));expect(screen.queryByText('OLD SOURCE')).not.toBeInTheDocument();
    expect(editor).toBe(original);expect(original.getJSON()).toEqual(before);
  });
  it('retains inspection across view/publication-object changes but closes when the publisher retires',async()=>{
    const load=vi.fn().mockResolvedValue(data),onEditor=vi.fn();
    render(<Harness surface="plan" load={load} onEditor={onEditor}/>);
    fireEvent.click(screen.getByRole('link',{name:'Source'}));await screen.findByRole('heading',{name:'Saved source'});
    fireEvent.click(screen.getByText('Cards view'));expect(screen.getByRole('heading',{name:'Saved source'})).toBeInTheDocument();
    expect(load).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByText('Retire source'));await waitFor(()=>expect(screen.queryByRole('region',{name:'Document reference'})).not.toBeInTheDocument());
  });
});
