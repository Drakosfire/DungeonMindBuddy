import { useMemo, type ReactNode } from "react";
import { SurfaceContextModule, useSurfaceContextContribution } from "../../surfaceInteraction/contextHost";
import type { SurfaceInteractionIdentity } from "../../surfaceInteraction/types";
import type { AnyPlayRunRecord } from "../../api/types";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";

export function playSurfaceContextIdentity(run: AnyPlayRunRecord | null, fallbackRunId: string | null): SurfaceInteractionIdentity {
  const parts = run ? run.schema_version === "dmb_world_play_run_record_v2"
    ? ["play", run.world_id, run.run_id, run.playable_artifact_id, String(run.playable_revision), run.playable_work_revision_id, run.playable_content_sha256]
    : ["play", run.campaign_id, run.run_id, run.playable_artifact_id, String(run.playable_revision)]
    : ["play", fallbackRunId ?? "chooser"];
  return buildSurfaceInteractionIdentity({ surfaceId: "play", instanceParts: parts });
}

/** Owner-local contribution wrapper for Play's shared surface navbar. */
export function PlaySurfaceContext({
  id,
  order,
  identity,
  children,
}: {
  id: string;
  order: number;
  identity: SurfaceInteractionIdentity;
  children: ReactNode;
}) {
  const content = useMemo(() => (
    <SurfaceContextModule className="play-surface-context"><div className="play-surface-context__row">{children}</div></SurfaceContextModule>
  ), [children]);
  useSurfaceContextContribution({
    id,
    order,
    surfaceIdentity: identity,
    content,
  });
  return null;
}
