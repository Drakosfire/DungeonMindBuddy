import { useEffect } from "react";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import type { SurfaceInteractionToolContribution, SurfaceInteractionProjectionDescriptor } from "../surfaceInteraction/types";
import { deferredComponent } from "../ui/deferredComponent";

export const STATBLOCK_WORKBENCH_ID = "statblock-workbench";
export const STATBLOCK_WORKBENCH_TOOL: SurfaceInteractionToolContribution = {
  id: STATBLOCK_WORKBENCH_ID, label: "Statblocks",
  placement: { groupId: "assets", groupLabel: "Assets", groupOrder: 30, itemOrder: 0 },
  availability: { status: "enabled" },
  activation: { kind: "projection", projectionId: STATBLOCK_WORKBENCH_ID },
};
export const STATBLOCK_WORKBENCH_PROJECTION: SurfaceInteractionProjectionDescriptor = {
  id: STATBLOCK_WORKBENCH_ID, kind: "tool", preferredSize: "wide", bindingIds: [],
};
const DeferredWorkbench = deferredComponent(
  () => import("../surface/modules/StatblockWorkbenchModule").then(module => ({ default: module.StatblockWorkbenchModule })),
  "statblock workbench",
);

/** Surface opt-in; the existing workbench admits its verified selected-World scope. */
export function useStatblockWorkbenchProjection(surfaceId: string) {
  const { registerProjectionCatalog } = useAgentInteraction();
  useEffect(() => registerProjectionCatalog({
    projectionId: STATBLOCK_WORKBENCH_ID, surfaceId, kind: "tool", preferredSize: "wide",
    requiredBindingIds: [], render: () => <DeferredWorkbench />,
  }), [registerProjectionCatalog, surfaceId]);
}
