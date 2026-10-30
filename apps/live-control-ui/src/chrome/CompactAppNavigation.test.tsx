import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { CompactAppNavigation } from "./CompactAppNavigation";
import userEvent from '@testing-library/user-event';
import {GuidedTourProvider,useGuidedTour} from '../guidedTour/GuidedTour';
import {createWalkthrough} from '../guidedTour/protocol';
import {writeWalkthrough,pointerKey,recordKey} from '../guidedTour/storage';

vi.mock("../selectedWorld/SelectedWorldContext", () => ({ useSelectedWorld: () => ({ kind: "managed", worldId: "elderwyld", name: "Elderwyld" }) }));
vi.mock("../selectedWorld/WorldSelector", () => ({ WorldSelector: () => <button>Switch World: Elderwyld</button> }));
vi.mock("./AppChromeWorldGraphStatus", () => ({ AppChromeWorldGraphStatus: () => <button>World graph: Elderwyld · Ready</button> }));

describe("compact command-board navigation", () => {
  it("starts collapsed with World selection and graph health always reachable", () => {
    render(<CompactAppNavigation activeRoute="plan" />);
    expect(screen.getByRole("button", { name: "Open navigation" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("link", { name: "Build" })).not.toBeInTheDocument();
    expect(document.querySelector(".app-nav-current")).toHaveTextContent("Plan");
    expect(within(screen.getByRole("navigation",{name:"Command board navigation"})).getByRole("button",{name:"Trash",exact:true})).toBeVisible();
    expect(screen.getByRole("button", { name: "Switch World: Elderwyld" })).toBeVisible();
    expect(screen.getByRole("button", { name: "World graph: Elderwyld · Ready" })).toBeVisible();
  });
  it("reveals World-scoped routes and dismisses them with Escape without navigation", () => {
    render(<CompactAppNavigation activeRoute="plan" />);
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    const nav = screen.getByRole("navigation", { name: "Command board navigation" });
    expect(within(nav).getByRole("link", { name: "Plan" })).toHaveAttribute("href", "/plan?world=elderwyld");
    expect(within(nav).getByRole("link", { name: "Plan" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Combat Tracker" })).toHaveAttribute("href", "/combat?world=elderwyld");
    fireEvent.keyDown(within(nav).getByRole("link", { name: "Build" }), { key: "Escape" });
    expect(screen.getByRole("button", { name: "Open navigation" })).toHaveFocus();
    expect(screen.queryByRole("link", { name: "Build" })).not.toBeInTheDocument();
  });
  it("preserves same-document World navigation and collapses after a normal click", () => {
    window.history.replaceState({}, "", "/plan?world=elderwyld");
    const history = vi.spyOn(window.history, "pushState");
    render(<CompactAppNavigation activeRoute="plan" />);
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    fireEvent.click(screen.getByRole("link", { name: "Build" }));
    expect(history).toHaveBeenCalledTimes(1);
    expect(window.location.pathname + window.location.search).toBe("/build?world=elderwyld");
    expect(screen.getByRole("button", { name: "Open navigation" })).toHaveAttribute("aria-expanded", "false");
    history.mockRestore();
  });
  it("collapses on a surface change without remounting the workspace", () => {
    const view = render(<CompactAppNavigation activeRoute="plan" />);
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    view.rerender(<CompactAppNavigation activeRoute="build" />);
    expect(screen.getByRole("button", { name: "Open navigation" })).toHaveAttribute("aria-expanded", "false");
    expect(document.querySelector(".app-nav-current")).toHaveTextContent("Build");
  });
});

// Exercise the real storage owner; navigation must not create its own tour state.
describe('visible tour entry',()=>{
  beforeEach(()=>{localStorage.clear();vi.spyOn(HTMLElement.prototype,'getClientRects').mockReturnValue([new DOMRect(0,0,100,24)] as unknown as DOMRectList);});
  afterEach(()=>vi.restoreAllMocks());
  function seed(phase:'running'|'paused'|'exited'='running',worldId='elderwyld'){
    const record=createWalkthrough(worldId,'conks','walk-'+worldId,'2026-10-30T00:00:00Z');record.phase=phase;
    writeWalkthrough(localStorage,record,null);return record;
  }
  function Workspace({worldId='elderwyld'}:{worldId?:string|null}){return <GuidedTourProvider worldId={worldId}><CompactAppNavigation activeRoute="build"/></GuidedTourProvider>;}
  it('offers Start without opening navigation; keyboard opening creates no guidance or domain request',async()=>{
    const write=vi.spyOn(Storage.prototype,'setItem'),fetch=vi.spyOn(globalThis,'fetch');
    render(<Workspace/>);
    const entry=screen.getByRole('button',{name:'Start tour'});expect(entry).toBeVisible();
    entry.focus();await userEvent.keyboard('{Enter}');
    expect(screen.getByRole('complementary',{name:'Guided journey'})).toBeVisible();
    expect(screen.getByRole('button',{name:'Close tour panel'})).toHaveFocus();
    fireEvent.click(screen.getByRole('button',{name:'Close tour panel'}));expect(entry).toHaveFocus();
    expect(write).not.toHaveBeenCalled();expect(fetch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Open navigation'}));
    expect(screen.getAllByRole('button',{name:'Start tour'})).toHaveLength(1);
    expect(screen.queryByRole('button',{name:'Guided journey'})).not.toBeInTheDocument();
  });
  it.each(['running','paused','exited'] as const)('offers Resume for %s guidance without changing its phase',phase=>{
    seed(phase);const bytes=localStorage.getItem(recordKey('elderwyld','walk-elderwyld'));
    const write=vi.spyOn(Storage.prototype,'setItem');render(<Workspace/>);
    fireEvent.click(screen.getByRole('button',{name:'Resume tour'}));
    expect(screen.getByRole('complementary',{name:'Guided journey'})).toBeVisible();
    expect(localStorage.getItem(recordKey('elderwyld','walk-elderwyld'))).toBe(bytes);expect(write).not.toHaveBeenCalled();
  });
  it('offers Review for historical guidance and retains its original bytes',()=>{
    const record=JSON.parse(JSON.stringify(seed()));delete record.steps.generation;delete record.dispatchRevision;
    record.schema='dmb_guided_journey_v2';record.version=2;
    localStorage.setItem(recordKey('elderwyld',record.id),JSON.stringify(record));
    localStorage.setItem(pointerKey('elderwyld'),JSON.stringify({schema:'dmb_guided_journey_pointer_v2',id:record.id}));
    const write=vi.spyOn(Storage.prototype,'setItem');render(<Workspace/>);
    fireEvent.click(screen.getByRole('button',{name:'Review tour'}));expect(screen.getByText(/This is a read-only record/)).toBeInTheDocument();
    expect(write).not.toHaveBeenCalled();
  });
  it('offers neutral Open for damaged guidance or no managed World',()=>{
    localStorage.setItem(pointerKey('elderwyld'),'damaged');const write=vi.spyOn(Storage.prototype,'setItem');
    const view=render(<Workspace/>);fireEvent.click(screen.getByRole('button',{name:'Open tour'}));
    expect(screen.getByRole('alert')).toBeVisible();expect(write).not.toHaveBeenCalled();
    view.rerender(<Workspace worldId={null}/>);expect(screen.getByRole('button',{name:'Open tour'})).toBeVisible();
    expect(screen.getByText('Select a managed World before starting a walkthrough.')).toBeVisible();
  });
  it('does not advertise Start or the prior World record while a new World resolves',()=>{
    seed();const labels:string[]=[];
    function Probe(){labels.push(useGuidedTour()!.entryLabel);return null;}
    const view=render(<GuidedTourProvider worldId="elderwyld"><Probe/><CompactAppNavigation activeRoute="build"/></GuidedTourProvider>);
    expect(labels[0]).toBe('Open tour');expect(screen.getByRole('button',{name:'Resume tour'})).toBeVisible();
    labels.length=0;
    view.rerender(<GuidedTourProvider worldId="new-world"><Probe/><CompactAppNavigation activeRoute="build"/></GuidedTourProvider>);
    expect(labels[0]).toBe('Open tour');expect(screen.getByRole('button',{name:'Start tour'})).toBeVisible();
    labels.length=0;
    view.rerender(<GuidedTourProvider worldId="elderwyld"><Probe/><CompactAppNavigation activeRoute="build"/></GuidedTourProvider>);
    expect(labels[0]).toBe('Open tour');expect(screen.getByRole('button',{name:'Resume tour'})).toBeVisible();
  });
});
