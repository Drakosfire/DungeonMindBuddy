import { guestBuildActive } from "./guestWorld/guestBuildSession";
import {SavedStatblockProvider} from './statblocks/SavedStatblockSession';
import {WorldGuidedTour} from './guidedTour/WorldGuidedTour';
import { DocumentReferenceSurfaceHost } from './documentReference/DocumentReferenceSurfaceHost';
import type { ReactNode } from "react";
import { WarmWorldGraphProvider } from "./appEntryShared";
import { useHostedAuthStatus } from "./auth/HostedAuthGate";
import type { AppRouteKey } from "./chrome/appChromeConfig";
import { WorkspacePrimaryNavigation } from "./chrome/WorkspacePrimaryNavigation";
import { useSelectedWorld } from "./selectedWorld/SelectedWorldContext";
import { AgentInteractionProvider } from "./agentInteraction/AgentInteractionProvider";
import { WorldAgentConversation, WorldAgentConversationProvider } from "./agentInteraction/WorldAgentConversation";
import { AskPluginSlotProvider } from "./agentInteraction/AskPluginSlot";
import { AgentInteractionChrome } from "./agentInteraction/AgentInteractionChrome";
import { LegacyProjectionHostAdapter } from "./planSurface/projection/LegacyProjectionHostAdapter";
import { ToolHost } from "./surfaceInteraction/toolHost/ToolHost";
import { PeekRegionProvider } from "./surfaceInteraction/peekHost";
import { SurfaceContextProvider } from "./surfaceInteraction/contextHost";
import { WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID } from "./chrome/appChromeConfig";
import {
  WorldGraphLensProvider,
  WorldGraphLensProjectionProvider,
} from "./graphLens";

export function LocalWorkspace({ route, pageAdmitted, children }: {
  route: AppRouteKey;
  pageAdmitted: boolean;
  children: ReactNode;
}) {
  const selectedWorld = useSelectedWorld();
  const guestBuild = guestBuildActive();
  const auth = useHostedAuthStatus();
  const worldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const graphOwner = auth.status === "authenticated" ? auth.subject : auth.status;
  const graphWorldId = auth.status === "local_operator" || (auth.status === "authenticated" && auth.subject)
    ? worldId : null;
  return (
    <AgentInteractionProvider>
      <AskPluginSlotProvider>
        <WorldAgentConversationProvider key={selectedWorld.kind === "managed" ? selectedWorld.worldId : "legacy"}
          worldId={selectedWorld.kind === "managed" ? selectedWorld.worldId : null}>
          <WorldGuidedTour worldId={selectedWorld.kind === "managed" ? selectedWorld.worldId : null} worldName={selectedWorld.kind === "managed" ? selectedWorld.name : undefined}>
          <WorldGraphLensProvider
            key={selectedWorld.kind === "managed" ? selectedWorld.worldId : "legacy"}
            loadFocusOptions={pageAdmitted && route !== "graph" && !guestBuild}
            planCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}
            managedWorldId={selectedWorld.kind === "managed" ? selectedWorld.worldId : null}
          >
            <WorldGraphLensProjectionProvider defaultCampaignId={WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID}>
              <SavedStatblockProvider worldId={selectedWorld.kind === 'managed' ? selectedWorld.worldId : null}>
              <SurfaceContextProvider>
                <PeekRegionProvider key={selectedWorld.kind === "managed" ? selectedWorld.worldId : "legacy"}>
                  <DocumentReferenceSurfaceHost worldId={selectedWorld.kind === "managed" ? selectedWorld.worldId : null} surface={pageAdmitted ? route : "pending"}>
                  <WarmWorldGraphProvider key={JSON.stringify([graphOwner, worldId])} worldId={graphWorldId}>
                    <WorkspacePrimaryNavigation route={route}>{children}</WorkspacePrimaryNavigation>
                  </WarmWorldGraphProvider>
                  {pageAdmitted ? <>
                    <ToolHost />
                    <LegacyProjectionHostAdapter />
                    {!guestBuild && <AgentInteractionChrome />}
                  </> : null}
                  {!guestBuild && <WorldAgentConversation surface={pageAdmitted && (route === "plan" || route === "play" || route === "build") ? route : "other"}
                    worldId={selectedWorld.kind === "managed" ? selectedWorld.worldId : null}
                    worldName={selectedWorld.kind === "managed" ? selectedWorld.name : undefined} />}
                  </DocumentReferenceSurfaceHost>
                </PeekRegionProvider>
              </SurfaceContextProvider>
              </SavedStatblockProvider>
            </WorldGraphLensProjectionProvider>
          </WorldGraphLensProvider>
          </WorldGuidedTour>
        </WorldAgentConversationProvider>
      </AskPluginSlotProvider>
    </AgentInteractionProvider>
  );
}
