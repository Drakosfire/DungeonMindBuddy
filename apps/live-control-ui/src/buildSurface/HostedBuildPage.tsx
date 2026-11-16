import { LocalWorkspace } from "../LocalWorkspace";
import { BuildSurfacePage } from "./BuildSurfacePage";

export function HostedBuildPage() {
  return (
    <LocalWorkspace route="build" pageAdmitted>
      <BuildSurfacePage />
    </LocalWorkspace>
  );
}
