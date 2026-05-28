import type { ComponentType } from "react";

import type {
  LiveEvent,
  LiveJob,
  PlanViewProjection,
  LiveQueryResponse,
  LiveState,
  SurfaceModuleDefinition,
  SurfaceModuleInstance,
} from "../api/types";
import { ChatModule } from "./modules/ChatModule";
import { NowModule } from "./modules/NowModule";
import { RecordModule } from "./modules/RecordModule";
import { RollStackModule } from "./modules/RollStackModule";
import { TimelineModule } from "./modules/TimelineModule";
import { UnsupportedModule } from "./modules/UnsupportedModule";

export interface ModuleRenderContext {
  catalogById: Map<string, SurfaceModuleDefinition>;
  state: LiveState;
  events: LiveEvent[];
  jobs: LiveJob[];
  planView: PlanViewProjection;
  campaignId: string;
  session: number;
  onQuerySuccess: (response: LiveQueryResponse) => void | Promise<void>;
}

export function catalogTitle(
  catalogById: Map<string, SurfaceModuleDefinition>,
  moduleId: string,
): string {
  return catalogById.get(moduleId)?.title ?? moduleId;
}

export function renderModule(
  row: SurfaceModuleInstance,
  context: ModuleRenderContext,
): ComponentType | null {
  switch (row.module_id) {
    case "chat":
      return () => (
        <ChatModule
          campaignId={context.campaignId}
          session={context.session}
          onQuerySuccess={context.onQuerySuccess}
        />
      );
    case "record":
      return () => <RecordModule events={context.events} />;
    case "roll_stack":
      return () => (
        <RollStackModule
          state={context.state}
          catalogEntry={context.catalogById.get("roll_stack")}
          events={context.events}
        />
      );
    case "now":
      return () => (
        <NowModule
          state={context.state}
          catalogEntry={context.catalogById.get("now")}
        />
      );
    case "timeline":
      return () => (
        <TimelineModule
          planView={context.planView}
          catalogEntry={context.catalogById.get("timeline")}
        />
      );
    default:
      return null;
  }
}

export function ModuleContent({
  row,
  context,
}: {
  row: SurfaceModuleInstance;
  context: ModuleRenderContext;
}) {
  const Component = renderModule(row, context);
  if (Component) {
    return <Component />;
  }
  return (
    <UnsupportedModule
      moduleId={row.module_id}
      title={catalogTitle(context.catalogById, row.module_id)}
    />
  );
}
