import { useMemo } from "react";

import { useOptionalSurfaceContext } from "./useSurfaceContext";
import type { SurfaceContextContribution } from "./surfaceContextTypes";
import "./surfaceContext.css";

function compareContributions(
  left: SurfaceContextContribution,
  right: SurfaceContextContribution,
): number {
  if (left.order !== right.order) {
    return left.order - right.order;
  }
  return left.id.localeCompare(right.id);
}

export function SurfaceContextHost() {
  const store = useOptionalSurfaceContext();
  const contributions = store?.contributions ?? {};

  const sortedContributions = useMemo(
    () => Object.values(contributions).sort(compareContributions),
    [contributions],
  );

  if (!store || sortedContributions.length === 0) {
    return null;
  }

  return (
    <div className="surface-context-host" data-testid="surface-context-host">
      {sortedContributions.map((contribution) => (
        <div key={contribution.id} className="surface-context-host__slot">
          {contribution.content}
        </div>
      ))}
    </div>
  );
}
