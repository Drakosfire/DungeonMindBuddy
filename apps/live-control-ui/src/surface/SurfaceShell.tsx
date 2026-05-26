import { useMemo } from "react";

import type {
  LiveEvent,
  LiveJob,
  LiveQueryResponse,
  LiveState,
  SurfaceLayout,
  SurfaceModuleDefinition,
  SurfaceModuleInstance,
} from "../api/types";
import { enabledModules } from "./layoutUtils";
import { LayoutControls } from "./LayoutControls";
import { catalogTitle, ModuleContent, type ModuleRenderContext } from "./moduleRegistry";

interface SurfaceShellProps {
  catalog: SurfaceModuleDefinition[];
  layout: SurfaceLayout;
  state: LiveState;
  events: LiveEvent[];
  jobs: LiveJob[];
  onQuerySuccess: (response: LiveQueryResponse) => void | Promise<void>;
  onLayoutSaved: (layout: SurfaceLayout) => void | Promise<void>;
}

function modulesForSlot(
  modules: SurfaceModuleInstance[],
  slot: SurfaceModuleInstance["slot"],
): SurfaceModuleInstance[] {
  return modules.filter((row) => row.slot === slot);
}

export function SurfaceShell({
  catalog,
  layout,
  state,
  events,
  jobs,
  onQuerySuccess,
  onLayoutSaved,
}: SurfaceShellProps) {
  const catalogById = useMemo(
    () => new Map(catalog.map((row) => [row.module_id, row])),
    [catalog],
  );

  const activeModules = enabledModules(layout);

  const context: ModuleRenderContext = {
    catalogById,
    state,
    events,
    jobs,
    campaignId: layout.campaign_id,
    session: layout.session,
    onQuerySuccess,
  };

  function renderSlot(slot: SurfaceModuleInstance["slot"], className: string) {
    const rows = modulesForSlot(activeModules, slot);
    if (rows.length === 0) {
      return null;
    }
    return (
      <section className={className} data-slot={slot}>
        {rows.map((row) => (
          <article
            key={row.module_id}
            className={`surface-module ${row.collapsed ? "collapsed" : ""}`}
            data-module-id={row.module_id}
          >
            <header className="surface-module-header">
              <h3>{catalogTitle(catalogById, row.module_id)}</h3>
            </header>
            {!row.collapsed ? (
              <div className="surface-module-body">
                <ModuleContent row={row} context={context} />
              </div>
            ) : (
              <p className="module-muted">Collapsed</p>
            )}
          </article>
        ))}
      </section>
    );
  }

  return (
    <div className="surface-shell">
      <header className="surface-header">
        <h1>Live Control</h1>
        <p className="surface-subtitle">
          {layout.campaign_id} · session {layout.session} · {state.recent_event_count}{" "}
          events · {state.queued_job_count} queued jobs
        </p>
      </header>
      <LayoutControls layout={layout} catalog={catalog} onLayoutSaved={onLayoutSaved} />
      <div className="surface-grid">
        {renderSlot("main", "surface-slot surface-slot-main")}
        {renderSlot("sidebar", "surface-slot surface-slot-sidebar")}
        {renderSlot("bottom", "surface-slot surface-slot-bottom")}
        {renderSlot("overlay", "surface-slot surface-slot-overlay")}
      </div>
    </div>
  );
}
