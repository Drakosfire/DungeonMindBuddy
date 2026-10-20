import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useState } from 'react';
import type { Editor } from '@tiptap/core';
import { DocumentReferenceProvider } from './DocumentReferenceProvider';
import type { DocumentInspection } from './resolveDocumentReference';
import { PeekClaim, PeekRegionProvider, PeekRegionSlot } from '../surfaceInteraction/peekHost';
import { MarkdownEditorCore } from '../tiptap/MarkdownEditorCore';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { tiptapJsonToSemanticMarkdown } from '../tiptap/markdown/calloutMarkdown';
import { MarkdownDocumentReader } from '../markdownReader/MarkdownDocumentReader';
import { ReadOnlyBodyContent } from '../markdownReader/ReadOnlyBodyContent';
const A='bba72416-9dfe-49bb-add0-21a346e9a421', B='2cd1f643-a070-4cec-bbb0-24c803e30b98';
const href=(id=A)=>`/build?world=elderwyld&documentId=${id}`;
const source=`# Draft\n\nRead [**Edge**](${href()}).`;
const saved: DocumentInspection={title:'Saved Edge',markdown:`# Exact source\n\n[Nested](${href(B)})`,digest:'a'.repeat(64),revisionLabel:'Saved page · registry revision 8'};
const wrapper=(node: React.ReactNode)=><PeekRegionProvider>{node}<PeekRegionSlot/></PeekRegionProvider>;

describe('one surface document inspection capability',()=>{
  it.each(['build','plan','play'])('keeps the %s writer mounted with draft, selection and undo intact',async surface=>{
    let editor:Editor|null=null;
    const update=vi.fn(), load=vi.fn().mockResolvedValue(saved), open=vi.spyOn(window,'open').mockReturnValue(null);
    const view=render(wrapper(<DocumentReferenceProvider worldId="elderwyld" sourceIdentity={surface} load={load}>
      <div data-testid="source-scroll"><MarkdownEditorCore documentKey={surface} content={markdownToTiptapDoc(source).doc} onEditorChange={value=>{editor=value;}} onUpdate={update}/></div>
    </DocumentReferenceProvider>));
    await waitFor(()=>expect(editor).not.toBeNull());
    const mounted=editor! as Editor;
    mounted.setOptions({editorProps:{handleScrollToSelection:()=>true}});
    act(()=>{mounted.commands.setTextSelection(2);mounted.commands.insertContent('local edit ');});
    const before=mounted.getJSON(), selection=mounted.state.selection.toJSON(), count=update.mock.calls.length;
    const scroll=screen.getByTestId('source-scroll'); scroll.scrollTop=212;
    const origin=screen.getByRole('link',{name:'Edge'}); origin.focus(); fireEvent.click(origin);
    await screen.findByRole('heading',{name:'Saved Edge'});
    expect(editor).toBe(mounted); expect(mounted.getJSON()).toEqual(before);
    expect(mounted.state.selection.toJSON()).toEqual(selection); expect(update).toHaveBeenCalledTimes(count);
    expect(open).not.toHaveBeenCalled();
    scroll.scrollTop=99;
    fireEvent.click(screen.getByRole('button',{name:'Close reference'}));
    expect(scroll.scrollTop).toBe(212);
    expect(origin).toHaveFocus(); expect(mounted.getJSON()).toEqual(before);
    act(()=>{mounted.commands.undo();});
    expect(tiptapJsonToSemanticMarkdown(mounted.getJSON())).not.toContain('local edit');
    view.unmount();open.mockRestore();
  });
  it.each(['markdown','body'])('activates %s read-only references with Enter and restores focus',async kind=>{
    const load=vi.fn().mockResolvedValue(saved);
    render(wrapper(<DocumentReferenceProvider worldId="elderwyld" sourceIdentity="play-run" load={load}>
      {kind==='markdown'?<MarkdownDocumentReader markdown={source}/>:<ReadOnlyBodyContent content={markdownToTiptapDoc(source).doc.content}/>}
    </DocumentReferenceProvider>));
    const link=screen.getByRole('link',{name:'Edge'});link.focus();fireEvent.keyDown(link,{key:'Enter'});
    await screen.findByRole('heading',{name:'Saved Edge'}); fireEvent.keyDown(document,{key:'Escape'});
    expect(link).toHaveFocus();expect(screen.queryByRole('region',{name:'Document reference'})).not.toBeInTheDocument();
  });
  it('keeps nested inspector history without changing source position or tool ownership',async()=>{
    const load=vi.fn().mockImplementation(target=>Promise.resolve(target.documentId===A?saved:{...saved,title:'Nested source',markdown:'# Nested body'}));
    const dismiss=vi.fn();
    render(wrapper(<DocumentReferenceProvider worldId="elderwyld" sourceIdentity="plan" load={load}>
      <PeekClaim kind="tools" active label="Tool draft" onDismiss={dismiss}><input aria-label="Tool draft" defaultValue="unsaved"/></PeekClaim>
      <MarkdownDocumentReader markdown={source}/>
    </DocumentReferenceProvider>));
    fireEvent.click(screen.getByRole('link',{name:'Edge'}));await screen.findByRole('heading',{name:'Saved Edge'});
    const pane=screen.getByRole('region',{name:'Document reference'});await within(pane).findByRole('link',{name:'Nested'});pane.scrollTop=143;
    fireEvent.click(await within(pane).findByRole('link',{name:'Nested'}));await screen.findByRole('heading',{name:'Nested source'});
    fireEvent.click(screen.getByRole('button',{name:'← Previous reference'}));await screen.findByRole('heading',{name:'Saved Edge'});await within(pane).findByRole('link',{name:'Nested'});
    expect(pane.scrollTop).toBe(143);expect(dismiss).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Close reference'}));expect(screen.getByLabelText('Tool draft')).toHaveValue('unsaved');
  });
  it('retires late A/B/A responses and results after dismissal or source change',async()=>{
    const pending:((value:DocumentInspection)=>void)[]=[];
    const load=vi.fn().mockImplementation(()=>new Promise(resolve=>pending.push(resolve)));
    function Harness(){const [identity,setIdentity]=useState('plan-a');return <><button onClick={()=>setIdentity('plan-b')}>Switch source</button>
      <DocumentReferenceProvider worldId="elderwyld" sourceIdentity={identity} load={load}><MarkdownDocumentReader markdown={source}/></DocumentReferenceProvider></>;}
    render(wrapper(<Harness/>));
    fireEvent.click(screen.getByRole('link',{name:'Edge'}));await waitFor(()=>expect(load).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole('link',{name:'Edge'}));await waitFor(()=>expect(load).toHaveBeenCalledTimes(2));
    await act(async()=>pending[0]({...saved,title:'STALE'}));expect(screen.queryByText('STALE')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Switch source'));await act(async()=>pending[1]({...saved,title:'LATE'}));
    expect(screen.queryByText('LATE')).not.toBeInTheDocument();expect(screen.queryByRole('region',{name:'Document reference'})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('link',{name:'Edge'}));await waitFor(()=>expect(load).toHaveBeenCalledTimes(3));
    fireEvent.click(screen.getByRole('button',{name:'Close reference'}));await act(async()=>pending[2](saved));
    expect(screen.queryByRole('heading',{name:'Saved Edge'})).not.toBeInTheDocument();
  });
  it('shows invalid local references instead of falling through to new-tab navigation',async()=>{
    const load=vi.fn();const open=vi.spyOn(window,'open').mockReturnValue(null);
    render(wrapper(<DocumentReferenceProvider worldId="elderwyld" sourceIdentity="build" load={load}>
      <a data-web-source-link href={`${window.location.origin}${href()}&revision=1&revision_n=2`}>Invalid</a>
    </DocumentReferenceProvider>));
    fireEvent.click(screen.getByText('Invalid'));expect(await screen.findByRole('alert')).toHaveTextContent('conflicting selectors');
    expect(load).not.toHaveBeenCalled();expect(open).not.toHaveBeenCalled();open.mockRestore();
  });
});
