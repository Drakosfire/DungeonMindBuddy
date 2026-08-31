import { useMemo } from "react";

import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import {
  SurfaceContextAction,
  SurfaceContextModule,
  useSurfaceContextContribution,
} from "../surfaceInteraction/contextHost";

export interface PlaySurfaceContextProps {
  instanceId: string;
  onStartNewRun: () => void;
}

export function PlaySurfaceContext({ instanceId, onStartNewRun }: PlaySurfaceContextProps) {
  const surfaceIdentity = useMemo(
    () =>
      buildSurfaceInteractionIdentity({
        surfaceId: "play",
        instanceParts: ["play", instanceId],
      }),
    [instanceId],
  );

  const content = useMemo(
    () => (
      <SurfaceContextModule label="PLAY" className="play-surface-context">
        <SurfaceContextAction data-testid="play-start-new-run" onClick={onStartNewRun}>
          Start New Run
        </SurfaceContextAction>
      </SurfaceContextModule>
    ),
    [onStartNewRun],
  );

  useSurfaceContextContribution({
    id: "play-run",
    order: 10,
    surfaceIdentity,
    content,
  });

  return null;
}
