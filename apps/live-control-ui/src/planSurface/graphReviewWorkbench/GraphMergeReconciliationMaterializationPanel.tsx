import type { UnionSupergraphProjectionResponse } from "../../api/types";

export interface GraphMergeReconciliationMaterializationPanelProps {
  campaignId: string;
  sessionId: string;
  campaignRel?: string | null;
  previewUnionStorePath?: string | null;
  onRefreshProjection?: () => Promise<UnionSupergraphProjectionResponse>;
}

/**
 * File-store merge materialization is retired (CUTOVER D.3A).
 * Graph Review prepare/commit remains the governed DungeonMind publication path.
 */
export function GraphMergeReconciliationMaterializationPanel({
  campaignId,
  sessionId,
}: GraphMergeReconciliationMaterializationPanelProps) {
  return (
    <div
      className="graph-merge-reconciliation-materialization-panel graph-merge-reconciliation-materialization-panel--retired"
      data-testid="graph-merge-reconciliation-materialization-panel"
      data-retired-code="graph_authoring_store_retired"
    >
      <h5>Durable identity materialization</h5>
      <p className="graph-merge-reconciliation-materialization-lead">
        Union-store merge materialization for {campaignId} / {sessionId} is retired
        (HTTP 410 <code>graph_authoring_store_retired</code>). This is not a missing
        ingest artifact. Use Graph Review prepare/commit on DungeonMind World Graph
        authority for governed corrections.
      </p>
    </div>
  );
}
