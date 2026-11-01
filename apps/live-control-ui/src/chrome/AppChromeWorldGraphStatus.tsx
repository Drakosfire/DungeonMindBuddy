import { LoadedWorldGraphExplorer } from "../graphLens/LoadedWorldGraphExplorer";

/** The chrome opens the published Graph; it does not infer readiness from another projection. */
export function AppChromeWorldGraphStatus() {
  return <LoadedWorldGraphExplorer compact />;
}
