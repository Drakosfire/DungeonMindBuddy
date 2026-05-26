import type { LiveState, SurfaceModuleDefinition } from "../../api/types";

interface NowModuleProps {
  state: LiveState;
  catalogEntry?: SurfaceModuleDefinition;
}

export function NowModule({ state, catalogEntry }: NowModuleProps) {
  const title = catalogEntry?.title ?? "Now";
  const now = state.now;

  return (
    <div className="module-panel now-module" data-module-id="now">
      <h2 className="module-title">{title}</h2>
      <dl className="now-fields">
        <div>
          <dt>Day</dt>
          <dd>{now.day_label}</dd>
        </div>
        <div>
          <dt>Position</dt>
          <dd>{now.party_position}</dd>
        </div>
        <div>
          <dt>Route</dt>
          <dd>{now.route_intent}</dd>
        </div>
        <div>
          <dt>Weather</dt>
          <dd>{now.active_weather ?? "—"}</dd>
        </div>
        <div>
          <dt>Next beat</dt>
          <dd>{now.next_suggested_beat}</dd>
        </div>
      </dl>
    </div>
  );
}
