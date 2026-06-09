import type {
  LiveEvent,
  LiveJob,
  PlanViewProjection,
  LiveQueryResponse,
  LiveState,
  SurfaceModuleDefinition,
  SurfaceModuleInstance,
} from "../api/types";
import { IngestionModule } from "../modules/IngestionModule";
import { SourcesModule } from "../modules/SourcesModule";
import { ChatModule } from "./modules/ChatModule";
import { NowModule } from "./modules/NowModule";
import { RecordModule } from "./modules/RecordModule";
import { RollStackModule } from "./modules/RollStackModule";
import { StatblockWorkbenchModule } from "./modules/StatblockWorkbenchModule";
import { TimelineModule } from "./modules/TimelineModule";
import { UnsupportedModule } from "./modules/UnsupportedModule";
import type { PaneTarget } from "./targetTypes";

export interface ModuleRenderContext {
  catalogById: Map<string, SurfaceModuleDefinition>;
  state: LiveState;
  events: LiveEvent[];
  jobs: LiveJob[];
  planView: PlanViewProjection;
  campaignId: string;
  session: number;
  onQuerySuccess: (response: LiveQueryResponse) => void | Promise<void>;
  onSelectTarget?: (target: PaneTarget) => void;
}

export function catalogTitle(
  catalogById: Map<string, SurfaceModuleDefinition>,
  moduleId: string,
): string {
  return catalogById.get(moduleId)?.title ?? moduleId;
}

export function ModuleContent({
  row,
  context,
}: {
  row: SurfaceModuleInstance;
  context: ModuleRenderContext;
}) {
  switch (row.module_id) {
    case "chat":
      return (
        <ChatModule
          campaignId={context.campaignId}
          session={context.session}
          onQuerySuccess={context.onQuerySuccess}
        />
      );
    case "record":
      return <RecordModule events={context.events} />;
    case "roll_stack":
      return (
        <RollStackModule
          state={context.state}
          catalogEntry={context.catalogById.get("roll_stack")}
          events={context.events}
        />
      );
    case "now":
      return (
        <NowModule state={context.state} catalogEntry={context.catalogById.get("now")} />
      );
    case "timeline":
      return (
        <TimelineModule
          planView={context.planView}
          catalogEntry={context.catalogById.get("timeline")}
          onSelectTarget={context.onSelectTarget}
        />
      );
    case "ingestion":
      return <IngestionModule campaignId={context.campaignId} session={context.session} />;
    case "sources":
      return <SourcesModule campaignId={context.campaignId} session={context.session} />;
    case "statblock_workbench":
      return <StatblockWorkbenchModule />;
    default:
      return (
        <UnsupportedModule
          moduleId={row.module_id}
          title={catalogTitle(context.catalogById, row.module_id)}
        />
      );
  }
}
