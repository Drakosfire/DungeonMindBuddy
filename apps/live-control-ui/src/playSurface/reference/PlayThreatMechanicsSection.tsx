import {
  buildThreatSheetViewModel,
  shouldRenderThreatCampaignSheet,
} from "../../statblocks/projection/threatSheetViewModel";
import { ThreatMechanicsPanel } from "../../statblocks/projection/ThreatMechanicsPanel";
import { useExactThreatMechanics } from "../../statblocks/projection/useExactThreatMechanics";
import type { GraphReferenceResolution } from "../../graphReference/types";

export interface PlayThreatMechanicsSectionProps {
  resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }>;
}

/**
 * Play-owned mechanics wrapper. No Plan session/actions and no Combat.
 */
export function PlayThreatMechanicsSection({ resolution }: PlayThreatMechanicsSectionProps) {
  const enabled = shouldRenderThreatCampaignSheet(resolution);
  const { loadStatus, hit, message } = useExactThreatMechanics(resolution, { enabled });
  const model = buildThreatSheetViewModel({
    resolution,
    hit,
    loadStatus,
    message,
  });

  if (!enabled) return null;

  return (
    <section
      className="play-threat-mechanics-section"
      aria-label="Mechanics"
      data-testid="play-threat-mechanics-section"
    >
      <h3>Mechanics</h3>
      <ThreatMechanicsPanel
        loadStatus={model.loadStatus}
        bindings={model.bindings}
        message={model.message}
      />
    </section>
  );
}
