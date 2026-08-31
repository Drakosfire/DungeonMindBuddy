/**
 * A7: build lease-scoped Play current-moment identity for SurfaceInteraction publication.
 *
 * Witnesses only — never titles, body text, digest, selections, notes, or inspection.
 */

import type { PlayRunRecord } from "../api/types";
import type { SurfaceInteractionAgentContextContribution } from "../surfaceInteraction/types";

export function buildPlaySurfaceAgentContext(
  run: PlayRunRecord | null,
): SurfaceInteractionAgentContextContribution {
  const base: SurfaceInteractionAgentContextContribution = {
    label: "Play",
    campaignId: run?.campaign_id ?? null,
    documentId: run?.playable_artifact_id ?? null,
    sessionNumber: null,
    ambientSummary: run ? `Play · run ${run.run_id}` : null,
    pointers: [],
  };

  const currentBeatId = run?.progress.current_beat_id ?? null;
  if (run == null || currentBeatId == null || currentBeatId.trim() === "") {
    return base;
  }

  const pointers = [
    { kind: "play_run", value: run.run_id },
    { kind: "playable_revision", value: String(run.playable_revision) },
    { kind: "current_beat", value: currentBeatId },
  ];

  const currentSceneId = run.progress.current_scene_id;
  if (currentSceneId != null && currentSceneId.trim() !== "") {
    pointers.push({ kind: "current_scene", value: currentSceneId });
  }

  return {
    ...base,
    pointers,
  };
}
