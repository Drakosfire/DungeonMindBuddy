import type {
  LiveEvent,
  LiveJob,
  PlanViewProjection,
  LiveQueryResponse,
  LiveState,
  SurfaceLayout,
  SurfaceModuleDefinition,
  SurfaceModuleInstance,
} from "../api/types";
import { LayoutDraftProvider, useLayoutDraft } from "./LayoutDraftContext";
import { enabledModules } from "./layoutUtils";
import { ModuleLayoutControls } from "./ModuleLayoutControls";
import { catalogTitle, ModuleContent, type ModuleRenderContext } from "./moduleRegistry";
import { SurfaceLayoutPanel } from "./SurfaceLayoutPanel";
import type { PaneTarget } from "./targetTypes";

interface SurfaceShellProps {
  catalog: SurfaceModuleDefinition[];
  layout: SurfaceLayout;
  state: LiveState;
  events: LiveEvent[];
  jobs: LiveJob[];
  planView: PlanViewProjection;
  onQuerySuccess: (response: LiveQueryResponse) => void | Promise<void>;
  onLayoutSaved: (layout: SurfaceLayout) => void | Promise<void>;
  onSelectTarget?: (target: PaneTarget) => void;
}

function modulesForSlot(
  modules: SurfaceModuleInstance[],
  slot: SurfaceModuleInstance["slot"],
): SurfaceModuleInstance[] {
  return modules.filter((row) => row.slot === slot);
}

function SurfaceShellBody({
  state,
  events,
  jobs,
  planView,
  onQuerySuccess,
  onSelectTarget,
}: {
  state: LiveState;
  events: LiveEvent[];
  jobs: LiveJob[];
  planView: PlanViewProjection;
  onQuerySuccess: (response: LiveQueryResponse) => void | Promise<void>;
  onSelectTarget?: (target: PaneTarget) => void;
}) {
  const { draft, catalogById } = useLayoutDraft();

  const context: ModuleRenderContext = {
    catalogById,
    state,
    events,
    jobs,
    planView,
    campaignId: draft.campaign_id,
    session: draft.session,
    onQuerySuccess,
    onSelectTarget,
  };

  const surfaceModules = enabledModules(draft);

  function renderSlot(slot: SurfaceModuleInstance["slot"], className: string) {
    const rows = modulesForSlot(surfaceModules, slot);
    if (rows.length === 0) {
      return null;
    }
    return (
      <section className={className} data-slot={slot}>
        {rows.map((row) => {
          const showBody = !row.collapsed;
          return (
            <article
              key={row.module_id}
              className={`surface-module ${row.collapsed ? "collapsed" : ""}`}
              data-module-id={row.module_id}
            >
              <header className="surface-module-header">
                <h3>{catalogTitle(catalogById, row.module_id)}</h3>
                <ModuleLayoutControls moduleId={row.module_id} />
              </header>
              {row.collapsed ? <p className="module-muted">Collapsed</p> : null}
              {showBody ? (
                <div className="surface-module-body">
                  <ModuleContent row={row} context={context} />
                </div>
              ) : null}
            </article>
          );
        })}
      </section>
    );
  }

  return (
    <div className="surface-shell">
      <header className="surface-header">
        <h1>Live Control</h1>
        <p className="surface-subtitle">
          {draft.campaign_id} · session {draft.session} · {state.recent_event_count} events ·{" "}
          {state.queued_job_count} queued jobs
        </p>
      </header>
      <div className="surface-grid">
        {renderSlot("main", "surface-slot surface-slot-main")}
        {renderSlot("sidebar", "surface-slot surface-slot-sidebar")}
        {renderSlot("bottom", "surface-slot surface-slot-bottom")}
        {renderSlot("overlay", "surface-slot surface-slot-overlay")}
      </div>
      <SurfaceLayoutPanel />
    </div>
  );
}

export function SurfaceShell({
  catalog,
  layout,
  state,
  events,
  jobs,
  planView,
  onQuerySuccess,
  onLayoutSaved,
  onSelectTarget,
}: SurfaceShellProps) {
  return (
    <LayoutDraftProvider layout={layout} catalog={catalog} onLayoutSaved={onLayoutSaved}>
      <SurfaceShellBody
        state={state}
        events={events}
        jobs={jobs}
        planView={planView}
        onQuerySuccess={onQuerySuccess}
        onSelectTarget={onSelectTarget}
      />
    </LayoutDraftProvider>
  );
}
