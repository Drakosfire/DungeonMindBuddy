import { Contents } from "../../shared/Contents";
import type { WorldPlanCardNode } from "./WorldPlanCardProjection";
import "./PlanCardDeck.css";

export function PlanCardDeck({ scenes, nodes, sceneId, onSelect, visible }: {
  visible: boolean;
  scenes: readonly WorldPlanCardNode[];
  nodes: readonly WorldPlanCardNode[];
  sceneId: string | null;
  onSelect: (id: string | null) => void;
}) {
  return <Contents visible={visible} selectedId={sceneId} onSelect={onSelect}
    outlineAction={{ label: "Scene outline", selected: sceneId === null, onClick: () => onSelect(null) }}
    entries={scenes.map(scene => ({ ...scene,
      groupTitle: nodes.find(node => node.kind === "beat" && node.id === scene.parentId)?.title,
    }))} />;
}
