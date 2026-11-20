import { useState, type CSSProperties } from "react";
import { SceneLensReader, type SceneReadingLens } from "./SceneLensReader";
import "./tokens.css";

const situation=<><p>The main assault has broken.</p><p>Smoke, churned mud, broken wall timbers, burned flesh, and exhausted townsfolk fill the Ironveil Warehouse yard.</p><p>Two transformed refugees remain active. Each is dragging an unconscious victim away from the warehouse and toward broken ground or a tunnel route.</p></>;
const aloud=<blockquote><p>For the first time in what feels like hours, nothing new is crawling out of the ground.</p><p>The quiet almost lands. Then someone screams.</p></blockquote>;
const now=<p>They are getting away with people. What do you do?</p>;
const gm=<><p>Their objective is escape with victims, not defeating the party.</p><p>Do not immediately roll initiative unless it clarifies the players’ chosen approach.</p></>;
const sections:SceneReadingLens[]=[{id:'situation',label:'Situation',content:situation},{id:'aloud',label:'Read aloud',content:aloud},{id:'now',label:'Do now',content:now},{id:'gm',label:'GM only',content:gm}];
const full=<><h3>Situation</h3>{situation}<h3>Read aloud</h3>{aloud}<h3>Do now</h3>{now}<h3>GM only</h3>{gm}</>;
const fixtureCSS=`.scene-fixture{padding:16px;max-width:100%;}.scene-fixture label{display:flex;align-items:center;gap:8px;margin:8px 0}.scene-fixture textarea{display:block;width:100%;min-height:70px;padding:8px;font:inherit;color:inherit;background:transparent;border:1px solid currentColor;border-radius:4px}.scene-fixture input{font:inherit}.scene-fixture-footer button{margin-inline-end:8px;padding:6px 10px;color:inherit;background:transparent;border:1px solid currentColor;border-radius:4px}.scene-fixture-node{padding:1px 7px;border:0;border-radius:12px;background:#c5d3be;color:#2c4232;font:12px/1.6 system-ui}`;
function ReaderFixture({single=false,quiet=false}:{single?:boolean;quiet?:boolean}){
  const [active,setActive]=useState<string|null>('situation'),[other,setOther]=useState(''),[notes,setNotes]=useState('');
  const theme=quiet?{'--scene-reader-background':'#1e2c31','--scene-reader-foreground':'#e5eae5','--scene-reader-border':'#3c5058'} as CSSProperties:undefined;
  return <div className="scene-fixture"><style>{fixtureCSS}</style><SceneLensReader title="Something Is Still Moving" eyebrow="The Last Hands of the Siege" location={<button className="scene-fixture-node" type="button">Ironveil Warehouse</button>}
    lenses={single?sections.slice(0,1):sections} activeLensId={active} onLensChange={setActive} fullScene={full} style={theme}
    choices={<div><label><input type="checkbox"/>Prioritize the sleepers.</label><label><input type="checkbox"/>Destroy the transformed refugees.</label><label><input type="checkbox"/>Let one flee, then track it.</label><label><input type="checkbox"/>Something else</label><textarea aria-label="Another direction" placeholder="What did the players do?" value={other} onChange={e=>setOther(e.currentTarget.value)}/></div>}
    context={<><p>End the immediate crisis fast and show that the battle is actually ending.</p><p>Pressure: two transformed refugees are escaping with sleeping victims.</p></>}
    footer={<div className="scene-fixture-footer"><label>Scene notes<textarea aria-label="Scene notes" value={notes} onChange={e=>setNotes(e.currentTarget.value)} /></label><button type="button">Previous scene</button><button type="button">Next scene</button></div>} /></div>;
}
export const Parchment=()=> <ReaderFixture/>;
export const Quiet=()=> <ReaderFixture quiet/>;
export const PartialSections=()=> <ReaderFixture single/>;
export const FullOnly=()=> <div className="scene-fixture"><SceneLensReader title="Unsectioned authored scene" activeLensId={null} onLensChange={()=>{}} fullScene={<><p>This caller provides only the complete authored scene.</p><p>The reader does not generate missing lenses or a review warning.</p></>}/></div>;
