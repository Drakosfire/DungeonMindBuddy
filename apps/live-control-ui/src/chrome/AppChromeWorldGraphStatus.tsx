import { LoadedWorldGraphExplorer } from "../graphLens/LoadedWorldGraphExplorer";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import type { AppRouteKey } from "./appChromeConfig";

/** Index targets its loaded canvas; other surfaces retain the published Graph browser. */
export function AppChromeWorldGraphStatus({ activeRoute = "surface" }: { activeRoute?: AppRouteKey } = {}) {
  const world = useSelectedWorld();
  if (activeRoute === "index") {
    if (world.kind !== "managed") return null;
    return <button className="app-world-graph-status__trigger" data-testid="app-chrome-world-graph-status"
      type="button" aria-label={`Focus ${world.name} graph canvas`}
      title={`Go to ${world.name}’s graph workspace`}
      onClick={() => document.getElementById("loaded-native-graph-canvas")?.focus()}>
      <svg className="app-world-graph-status__glyph" viewBox="0 0 16 14" width="14" height="12" aria-hidden="true" focusable="false">
        <line className="app-world-graph-status__edge" x1="8" y1="3" x2="3" y2="11" />
        <line className="app-world-graph-status__edge" x1="8" y1="3" x2="13" y2="11" />
        <line className="app-world-graph-status__edge" x1="3" y1="11" x2="13" y2="11" />
        <circle className="app-world-graph-status__node" cx="8" cy="3" r="2" />
        <circle className="app-world-graph-status__node" cx="3" cy="11" r="2" />
        <circle className="app-world-graph-status__node" cx="13" cy="11" r="2" />
      </svg><span>Graph</span>
    </button>;
  }
  return <LoadedWorldGraphExplorer compact />;
}
