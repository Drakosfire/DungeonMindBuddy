import { useState, type ReactNode } from "react";
import type { JSONContent } from "@tiptap/core";
import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import { useGraphNodeChipRuntime } from "../../graphReference";
import { adaptFocusedPlan } from "./FocusedPlanAdapter";
import { worldPlanCardTargetKey, type WorldPlanCardProjectionModel, type WorldPlanCardTarget } from "./WorldPlanCardProjection";
import "./FocusedPlanPrototype.css";

function RichBlock({ node }: { node: JSONContent }): ReactNode {
  const graph = useGraphNodeChipRuntime();
  const children = node.content?.map((child, i) => <RichBlock key={i} node={child} />);
  if (node.type === "text") {
    let text: ReactNode = node.text;
    for (const mark of node.marks ?? []) {
      if (mark.type === "bold") text = <strong>{text}</strong>;
      if (mark.type === "italic") text = <em>{text}</em>;
      if (mark.type === "code") text = <code>{text}</code>;
    }
    return text;
  }
  if (node.type === "graphNodeReference") return <button className="focused-node" onClick={() => graph.onSelectNode(String(node.attrs?.nodeId))}>{node.attrs?.label || node.attrs?.nodeId}</button>;
  if (node.type === "paragraph") return <p>{children}</p>;
  if (node.type === "bulletList") return <ul>{children}</ul>;
  if (node.type === "orderedList") return <ol>{children}</ol>;
  if (node.type === "listItem") return <li>{children}</li>;
  if (node.type === "blockquote") return <blockquote>{children}</blockquote>;
  if (node.type === "heading") return <h3>{children}</h3>;
  if (node.type === "hardBreak") return <br />;
  if (node.type === "horizontalRule") return <hr />;
  if (node.type === "table") return <table><tbody>{children}</tbody></table>;
  if (node.type === "tableRow") return <tr>{children}</tr>;
  if (node.type === "tableHeader") return <th>{children}</th>;
  if (node.type === "tableCell") return <td>{children}</td>;
  return <>{children ?? (node.attrs?.label ? String(node.attrs.label) : null)}</>;
}

export function FocusedPlanPrototype({ model, document, isDirty, selectableTargetKeys, editableTargetKeys, onSelectTarget, onSelectEditTarget, onReturnToDocument }: {
  model: WorldPlanCardProjectionModel; document: JSONContent; isDirty: boolean;
  selectableTargetKeys: ReadonlySet<string>; editableTargetKeys: ReadonlySet<string>;
  onSelectTarget?: (target: WorldPlanCardTarget) => void; onSelectEditTarget?: (target: WorldPlanCardTarget) => void; onReturnToDocument: () => void;
}) {
  const { setPaneOpen } = useAgentInteraction();
  const scenes = adaptFocusedPlan(model, document);
  const [sceneId, setSceneId] = useState(() => new URLSearchParams(location.search).get("scene"));
  const [lensId, setLensId] = useState<string | null>(null);
  const [outline, setOutline] = useState(true);
  const index = Math.max(0, scenes.findIndex(s => s.scene.id === sceneId));
  const current = scenes[index];
  if (!current) return <section className="focused-prototype"><p>This Plan has no supported scenes. Document remains available.</p><button onClick={onReturnToDocument}>Document</button></section>;
  const lens = current.lenses.find(l => l.id === lensId) ?? current.lenses[0];
  const targetNode = current.scene;
  const target = { kind: targetNode.kind, id: targetNode.id };
  const go = (id: string) => {
    setSceneId(id); setLensId(null);
    const url = new URL(location.href); url.searchParams.set("scene", id); history.replaceState(history.state, "", url);
  };
  return <section className={`focused-prototype ${outline ? "" : "focused-prototype--collapsed"}`} aria-label="Focused Plan prototype">
    <nav className="focused-toolbar" aria-label="Focused scene navigation">
      <button aria-expanded={outline} onClick={() => setOutline(!outline)}>Outline</button>
      <div><small>{current.group}</small><h2>{current.scene.title}</h2></div>
      <span>{index + 1} / {scenes.length}</span><span>{isDirty ? "Unsaved draft" : "Saved Plan"}</span>
      <button disabled={!selectableTargetKeys.has(worldPlanCardTargetKey(target))} onClick={() => { onSelectTarget?.(target); setPaneOpen(true); }}>Discuss scene</button>
      <button disabled={!editableTargetKeys.has(worldPlanCardTargetKey(target))} onClick={() => { onSelectEditTarget?.(target); setPaneOpen(true); }}>Revise scene</button>
      <button onClick={onReturnToDocument}>Document</button>
    </nav>
    {outline && <aside aria-label="Scene outline">{scenes.map(s => <button key={s.scene.id} aria-current={current.scene.id === s.scene.id ? "step" : undefined} onClick={() => go(s.scene.id)}>{s.scene.title}</button>)}</aside>}
    <div className="focused-reading">
      <article className="focused-paper">
        <nav className="focused-lenses" aria-label="Scene lenses">{current.lenses.map(l => <button key={l.id} aria-pressed={lens?.id === l.id} onClick={() => setLensId(l.id)}>{l.title}</button>)}</nav>
        <section className="focused-body">{lens?.nodes.map((node, i) => <RichBlock key={i} node={node} />)}</section>
        {current.choices.map(choice => <details className="focused-choices" key={choice.id}><summary>Choices <span>{choice.title}</span></summary>{current.bodies.get(choice.id)?.map((n,i) => <RichBlock key={i} node={n} />)}{choice.children.map(option => <div key={option.id}>{current.bodies.has(option.id) ? current.bodies.get(option.id)!.map((n,i) => <RichBlock key={i} node={n} />) : <><strong>{option.title}</strong>{option.bodyText && <p>{option.bodyText}</p>}</>}<details><summary>Connections</summary>{option.activates?.map(id => <p key={id}>Leads to {scenes.find(s => s.scene.id === id)?.scene.title ?? id}</p>)}{option.suppresses?.map(id => <p key={id}>Closes {scenes.find(s => s.scene.id === id)?.scene.title ?? id}</p>)}</details></div>)}</details>)}
        <footer><button disabled={index === 0} onClick={() => go(scenes[index - 1]!.scene.id)}>← Previous scene</button><button disabled={index === scenes.length - 1} onClick={() => go(scenes[index + 1]!.scene.id)}>Next scene →</button></footer>
      </article>
      <details className="focused-advanced"><summary>Advanced · exploration adapter</summary><p>Uses Buddy's current mounted Plan and existing Ask/Edit contracts. Ask uses the committed revision; revision proposals use the current draft. Apply and Save stay in Buddy. No separate content store or synthetic conversation.</p><code>{current.scene.id}</code></details>
    </div>
  </section>;
}
