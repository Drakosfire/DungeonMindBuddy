import { useEffect } from 'react';
import { useAgentInteraction } from '../agentInteraction/useAgentInteraction';
import type { SurfaceInteractionToolContribution, SurfaceInteractionProjectionDescriptor } from '../surfaceInteraction/types';
import { deferredComponent } from '../ui/deferredComponent';

export const RULES_LOOKUP_ID = 'rules-lookup';
export const RULES_LOOKUP_TOOL: SurfaceInteractionToolContribution = {
  id: RULES_LOOKUP_ID, label: 'Rules Lookup',
  placement: { groupId: 'reference', groupLabel: 'Reference', groupOrder: 40, itemOrder: 0 },
  availability: { status: 'enabled' }, activation: { kind: 'projection', projectionId: RULES_LOOKUP_ID },
};
export const RULES_LOOKUP_PROJECTION: SurfaceInteractionProjectionDescriptor = {
  id: RULES_LOOKUP_ID, kind: 'tool', preferredSize: 'wide', bindingIds: [],
};
const DeferredRulesLookup = deferredComponent(() => import('./RulesLookupTool'), 'rules lookup');

/** Publisher opt-in only. Registration is admitted against the current surface lease. */
export function useRulesLookupProjection(surfaceId: string, enabled: boolean) {
  const { registerProjectionCatalog } = useAgentInteraction();
  useEffect(() => {
    if (!enabled) return;
    return registerProjectionCatalog({
      projectionId: RULES_LOOKUP_ID, surfaceId, kind: 'tool', preferredSize: 'wide',
      requiredBindingIds: [], render: () => <DeferredRulesLookup />,
    });
  }, [registerProjectionCatalog, surfaceId, enabled]);
}
