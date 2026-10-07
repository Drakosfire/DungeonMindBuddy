import { useState, type CSSProperties } from "react";
import { ConversationDock } from "./ConversationDock";
import "./tokens.css";

const fixtureStyle = `
.dock-fixture { height: min(760px, calc(100dvh - 120px)); min-height: 320px; }
.dock-fixture-paper { max-width: 720px; margin: 20px auto; padding: 24px; background: var(--ui-background-paper); color: var(--ui-text-on-paper); font: 16px/1.6 Georgia,serif; border-radius: 8px; }
.dock-fixture-paper h1 { margin: 0 0 18px; font-size: 24px; font-weight: 400; }
.dock-fixture-paper button { background: #c5d3be; color: #2c4232; border: 0; border-radius: 12px; padding: 2px 7px; }
.dock-fixture-messages { max-width: 900px; margin: 0 auto; font-size: 14px; line-height: 1.5; }
.dock-fixture-messages p { margin: 7px 0; }
.dock-fixture-question { text-align: right; color: var(--ui-text-secondary); }
.dock-fixture-composer { display:flex; gap:8px; align-items:center; max-width:900px; margin:auto; padding:7px 10px; background:var(--ui-background-ops); border:1px solid var(--ui-border-strong); border-radius:9px; }
.dock-fixture-composer textarea { flex:1; min-width:0; height:44px; resize:none; border:0; padding:6px; font:16px/1.4 system-ui; color:var(--ui-text-primary); background:transparent; }
.dock-fixture-composer button { flex:none; border:0; border-radius:6px; padding:8px 12px; background:#c5d3be; color:#2c4232; }
.dock-fixture-context { display:flex; align-items:center; flex-wrap:wrap; gap:8px; font-size:12px; }
.dock-fixture-context select,.dock-fixture-context button { min-height:32px; font:inherit; }
.dock-fixture-failure { border-inline-start:2px solid var(--ui-accent-danger); padding-inline-start:12px; }
@media(max-width:520px) { .dock-fixture-paper { margin:12px; padding:18px; } }
`;

function DockFixture({ expanded = false, paper = false, failed = false }: {expanded?:boolean;paper?:boolean;failed?:boolean}) {
  const [draft, setDraft] = useState("");
  const [scope, setScope] = useState("This scene");
  const [messages, setMessages] = useState<string[]>([]);
  const theme = paper ? {
    "--conversation-dock-chat-background": "#f7ebd7",
    "--conversation-dock-foreground": "#332d25",
    "--conversation-dock-muted": "#6b614f",
    "--conversation-dock-border": "#c0ad6a",
    "--conversation-dock-color-scheme": "light",
  } as CSSProperties : undefined;
  return <div className="dock-fixture"><style>{fixtureStyle}</style>
    <ConversationDock initialExpanded={expanded} contextLabel={scope} style={theme}
      reader={<article className="dock-fixture-paper"><h1>Something Is Still Moving</h1><p>The main assault has broken.</p><p>Smoke, churned mud, broken wall timbers, burned flesh, and exhausted townsfolk fill the <button type="button">Ironveil Warehouse</button> yard.</p><p>Two transformed refugees remain active. Each is dragging an unconscious victim away from the warehouse and toward broken ground or a tunnel route.</p><p>The document keeps its own reading space when chat opens. This is an isolated composition fixture, with no campaign or provider connection.</p><label>Reader note <input aria-label="Reader note" defaultValue="Keep the rescue brief" /></label></article>}
      messages={<div className="dock-fixture-messages"><p className="dock-fixture-question">How could I give this scene a quieter ending?</p>{failed?<div className="dock-fixture-failure" role="alert"><strong>Buddy couldn’t complete this answer.</strong><p>Your question is kept. It hasn’t been sent again.</p><details><summary>Details</summary><p>This fixture represents a terminal failed answer. A real caller must provide the exact diagnostic and captured source attribution without automatically replaying the request.</p></details><details><summary>Older recovery items · 4</summary><p>Saved recovery records remain inspectable; hiding them does not erase them.</p></details></div>:<><p>Let the sound of fighting fall away. Bring attention to the people the party saved: a blanket offered, someone counting survivors, a voice asking for water.</p><p>Then give the players room to decide what comes next.</p></>}{messages.map((m,i)=><p key={i}>{m}</p>)}</div>}
      collapsedPreview={<div className="dock-fixture-messages">{failed?'The last question couldn’t be completed.':'Give the players room to decide what comes next.'}</div>}
      contextDetails={<div className="dock-fixture-context"><label>Scope <select aria-label="Conversation scope" value={scope} onChange={e=>setScope(e.currentTarget.value)}><option>This scene</option><option>Session 29 Plan</option></select></label><details><summary>Included context</summary><p>Selected source, version and evidence remain inspectable here.</p><p>This fixture makes no Graph availability claim.</p></details></div>}
      composer={<form className="dock-fixture-composer" onSubmit={e=>{e.preventDefault();if(draft.trim()){setMessages(x=>[...x,draft.trim()]);setDraft("");}}}><textarea aria-label="Message Buddy" placeholder="Message Buddy…" value={draft} onChange={e=>setDraft(e.currentTarget.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();e.currentTarget.form?.requestSubmit();}}} /><button type="submit" disabled={!draft.trim()}>Send</button></form>} />
  </div>;
}

export const Compact = () => <DockFixture />;
export const Expanded = () => <DockFixture expanded />;
export const Paper = () => <DockFixture expanded paper />;
export const FailedTurn = () => <DockFixture expanded failed />;
