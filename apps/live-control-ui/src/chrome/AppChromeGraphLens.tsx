import { GraphLoadPanel } from "../graphLens/GraphLoadPanel";
import { useOptionalWorldGraphLensProjection } from "../graphLens/useWorldGraphLensProjection";
import type { AppRouteKey } from "./appChromeConfig";

const GRAPH_LENS_NAV_ROUTES = new Set<AppRouteKey>(["plan", "build"]);

/** Site-nav World Graph lens strip for Plan + Build. */
export function AppChromeGraphLens({ activeRoute }: { activeRoute: AppRouteKey }) {
  const projection = useOptionalWorldGraphLensProjection();

  if (!GRAPH_LENS_NAV_ROUTES.has(activeRoute) || !projection) {
    return null;
  }

  return (
    <div className="app-site-nav__graph-lens" data-testid="app-chrome-graph-lens">
      <GraphLoadPanel
        projectionState={projection.projectionState}
        projectionError={projection.projectionError}
        nodeCount={projection.nodeCount}
      />
    </div>
  );
}
