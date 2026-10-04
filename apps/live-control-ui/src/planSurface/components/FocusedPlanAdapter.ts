import type { JSONContent } from "@tiptap/core";
import type { WorldPlanCardNode, WorldPlanCardProjectionModel } from "./WorldPlanCardProjection";

export type FocusedLens = { id: string; title: string; nodes: JSONContent[]; target: WorldPlanCardNode };
export type FocusedScene = { scene: WorldPlanCardNode; group: string; lenses: FocusedLens[]; choices: WorldPlanCardNode[]; bodies: Map<string, JSONContent[]> };

// Read-only adapter: keep Buddy identity and original editor blocks. No copied Plan store.
export function adaptFocusedPlan(model: WorldPlanCardProjectionModel, document: JSONContent): FocusedScene[] {
  if (model.status !== "ready") return [];
  const blocks = document.content ?? [];
  const bodies = new Map<string, JSONContent[]>();
  let current: string | null = null;
  for (const block of blocks) {
    if ((block.type === "bulletList" || block.type === "orderedList") && block.content?.some(n => n.attrs?.playableElementKind === "option")) {
      for (const item of block.content ?? []) {
        if (item.attrs?.playableElementKind === "option" && item.attrs?.playableElementId) bodies.set(String(item.attrs.playableElementId), item.content ?? []);
      }
      current = null;
      continue;
    }
    if (block.type === "heading" && block.attrs?.playableElementId) {
      current = String(block.attrs.playableElementId);
      bodies.set(current, []);
    } else if (block.type === "heading" && Number(block.attrs?.level) <= 2) {
      current = null;
    } else if (current) bodies.get(current)?.push(block);
  }
  const result: FocusedScene[] = [];
  const walk = (nodes: WorldPlanCardNode[], group = "") => {
    for (const node of nodes) {
      if (node.kind === "scene") {
        const lenses: FocusedLens[] = [];
        const add = (target: WorldPlanCardNode, fallback: string) => {
          let lens: FocusedLens = { id: target.id, title: fallback, nodes: [], target };
          for (const block of bodies.get(target.id) ?? []) {
            const label = block.type === "paragraph" && block.content?.length === 1
              && block.content[0]?.marks?.some(m => m.type === "bold")
              ? block.content[0]?.text?.trim() : null;
            const knownLens = label && ["Situation", "Read aloud", "Do now", "GM only", "GM-only truth", "Relevant", "Missing reference", "Actionable details", "Name note", "Closing image if needed"].includes(label);
            if (block.type === "heading" || knownLens) {
              const title = knownLens ? label : block.content?.map(n => n.text ?? "").join("").trim();
              if (title) {
                if (lens.nodes.length) lenses.push(lens);
                lens = { id: `${target.id}:${lenses.length}`, title, nodes: [], target };
                continue;
              }
            }
            lens.nodes.push(block);
          }
          if (lens.nodes.length) lenses.push(lens);
        };
        add(node, "Situation");
        node.children.filter(n => n.kind === "beat").forEach(n => add(n, n.title));
        const siblingChoices = nodes.filter(n => n.kind === "choice" && n.sceneId === node.id);
        result.push({ scene: node, group, lenses, bodies, choices: [...node.children.filter(n => n.kind === "choice"), ...siblingChoices] });
      } else if (node.kind === "beat") walk(node.children, node.title);
    }
  };
  walk(model.roots);
  return result;
}
