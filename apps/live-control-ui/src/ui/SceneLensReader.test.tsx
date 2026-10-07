import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SceneLensReader } from "./SceneLensReader";

const lenses=[{id:'situation',label:'Situation',content:<p>Authored situation</p>},{id:'aloud',label:'Read aloud',content:<p>Authored narration</p>},{id:'gm',label:'GM only',content:<p>Authored GM note</p>}];
const full=<div><p>Authored situation</p><p>Authored narration</p><p>Authored GM note</p><p>Unclassified authored paragraph</p></div>;
function Fixture(){const [active,setActive]=useState<string|null>('situation');return <SceneLensReader title="Warehouse" lenses={lenses} activeLensId={active} onLensChange={setActive} fullScene={full} choices={<label>Direction<input aria-label="Direction note" defaultValue="Rescue first" /></label>} context={<p>Authored Beat context</p>} footer={<input aria-label="Shared note" defaultValue="Remember this" />} />;}
afterEach(()=>vi.restoreAllMocks());

describe('SceneLensReader',()=>{
  it('shows only the chosen caller section and provides the unmodified full view',async()=>{
    const user=userEvent.setup();render(<Fixture />);
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Authored situation');
    expect(screen.queryByText('Authored narration')).toBeNull();
    await user.click(screen.getByRole('tab',{name:'Read aloud'}));
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Authored narration');
    expect(screen.queryByText('Authored situation')).toBeNull();
    await user.click(screen.getByRole('tab',{name:'Full scene'}));
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Unclassified authored paragraph');
    expect(screen.getByRole('tab',{name:'Full scene'})).toHaveAttribute('aria-selected','true');
  });
  it('keeps choices and notes mounted while changing reading lenses',async()=>{
    const user=userEvent.setup();render(<Fixture />);
    await user.click(screen.getByText('Choices',{exact:true}));
    const direction=screen.getByLabelText('Direction note'),note=screen.getByLabelText('Shared note');
    await user.type(direction,' together');await user.type(note,' locally');
    await user.click(screen.getByRole('tab',{name:'GM only'}));
    expect(screen.getByLabelText('Direction note')).toBe(direction);
    expect(direction).toHaveValue('Rescue first together');expect(note).toHaveValue('Remember this locally');
    expect(direction.closest('details')).toHaveAttribute('open');
  });
  it('supports arrow, Home and End selection with focus on the chosen tab',()=>{
    render(<Fixture />);const first=screen.getByRole('tab',{name:'Situation'});
    fireEvent.keyDown(first,{key:'ArrowRight'});
    expect(screen.getByRole('tab',{name:'Read aloud'})).toHaveFocus();
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Authored narration');
    fireEvent.keyDown(screen.getByRole('tab',{name:'Read aloud'}),{key:'End'});
    expect(screen.getByRole('tab',{name:'Full scene'})).toHaveFocus();
    fireEvent.keyDown(screen.getByRole('tab',{name:'Full scene'}),{key:'Home'});
    expect(first).toHaveFocus();
  });
  it('requests only a visual selection and does not alter controlled selection itself',async()=>{
    const user=userEvent.setup(),change=vi.fn();
    render(<SceneLensReader title="Warehouse" lenses={lenses} activeLensId="situation" onLensChange={change} fullScene={full} />);
    expect(change).not.toHaveBeenCalled();await user.click(screen.getByRole('tab',{name:'GM only'}));
    expect(change).toHaveBeenCalledExactlyOnceWith('gm');
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Authored situation');
  });
  it('falls back honestly to supplied full content for a missing selection',()=>{
    const change=vi.fn();render(<SceneLensReader title="Warehouse" lenses={lenses} activeLensId="absent" onLensChange={change} fullScene={full} />);
    expect(screen.getByRole('tab',{name:'Full scene'})).toHaveAttribute('aria-selected','true');
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Unclassified authored paragraph');
    expect(screen.queryByRole('alert')).toBeNull();expect(change).not.toHaveBeenCalled();
  });
  it('does not invent sections, warnings or optional disclosures when none are supplied',()=>{
    render(<SceneLensReader title="Simple scene" activeLensId={null} onLensChange={vi.fn()} fullScene={<p>All authored prose</p>} />);
    expect(screen.getByText('All authored prose')).toBeInTheDocument();
    expect(screen.queryByRole('tablist')).toBeNull();expect(screen.queryByText('Choices')).toBeNull();expect(screen.queryByRole('alert')).toBeNull();
  });
  it('uses supplied full content rather than choosing between ambiguous lens identifiers',()=>{
    render(<SceneLensReader title="Warehouse" lenses={[...lenses,{id:'situation',label:'Other',content:'Other'}]} activeLensId="situation" onLensChange={vi.fn()} fullScene={full} />);
    expect(screen.queryByRole('tablist')).toBeNull();expect(screen.getByText('Unclassified authored paragraph')).toBeInTheDocument();
  });
  it('accepts a lens named full without colliding with the full-scene control',async()=>{
    const user=userEvent.setup(),change=vi.fn();render(<SceneLensReader title="Warehouse" lenses={[{id:'full',label:'Detail',content:'Detail content'}]} activeLensId="full" onLensChange={change} fullScene="Complete content" />);
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Detail content');await user.click(screen.getByRole('tab',{name:'Full scene'}));expect(change).toHaveBeenCalledWith(null);
  });
});
