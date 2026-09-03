import { useSyncExternalStore, type ReactNode } from "react";

import type { WorldGraphProjection } from "../../api/types";
import { GraphReferenceSearch } from "../../graphReference/GraphReferenceSearch";
import type { GraphReferenceSearchItem } from "../../graphReference/types";
import type { SurfaceInformationChannel, SurfaceInformationSnapshot } from "../../surfaceInformation";
import { admitBuildObjectInsert } from "../../worldGraph/worldGraphSurfaceContext";
import type { BuildReferenceContextBinding } from "./buildBuildSurfaceInteractionPublication";
import {
  BUILD_REFERENCE_CONTEXT_BINDING_ID,
  BUILD_WORLD_GRAPH_INFORMATION_CHANNEL_BINDING_ID,
} from "./buildReferenceIds";
import type { BuildGraphLensResolution } from "./resolveBuildGraphLens";
import {
  BUILD_WORLD_GRAPH_FALLBACK_SNAPSHOT,
  observedIsHead,
  observedRevisionId,
  searchItemsFromWorldGraphState,
} from "./buildWorldGraphSurfaceInformation";

export interface BuildReferenceSearchProjectionProps {
  bindings: Readonly<Record<string, unknown>>;
}

function isBuildReferenceContextBinding(value: unknown): value is BuildReferenceContextBinding {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<BuildReferenceContextBinding>;
  return (
    candidate.schema === "dmb_build_reference_context_v2"
    && typeof candidate.documentId === "string"
    && typeof candidate.documentCampaignId === "string"
    && candidate.lens != null
    && typeof candidate.selectCampaign === "function"
    && typeof candidate.viewExact === "function"
    && typeof candidate.insertChip === "function"
    && typeof candidate.editorInsertDisabled === "boolean"
  );
}

function isWorldGraphChannel(
  value: unknown,
): value is SurfaceInformationChannel<WorldGraphProjection> {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<SurfaceInformationChannel<WorldGraphProjection>>;
  return (
    typeof candidate.subscribe === "function"
    && typeof candidate.getSnapshot === "function"
    && candidate.descriptor != null
  );
}

export function readBuildReferenceContextBinding(
  bindings: Readonly<Record<string, unknown>>,
): BuildReferenceContextBinding {
  if (!Object.prototype.hasOwnProperty.call(bindings, BUILD_REFERENCE_CONTEXT_BINDING_ID)) {
    throw new Error(`Missing required projection binding: ${BUILD_REFERENCE_CONTEXT_BINDING_ID}`);
  }
  const value = bindings[BUILD_REFERENCE_CONTEXT_BINDING_ID];
  if (value === null || value === undefined) {
    throw new Error(`Required projection binding is null: ${BUILD_REFERENCE_CONTEXT_BINDING_ID}`);
  }
  if (!isBuildReferenceContextBinding(value)) {
    throw new Error(
      "Malformed Build reference context binding: expected schema dmb_build_reference_context_v2.",
    );
  }
  return value;
}

export function readBuildWorldGraphInformationChannelBinding(
  bindings: Readonly<Record<string, unknown>>,
): SurfaceInformationChannel<WorldGraphProjection> | null {
  if (
    !Object.prototype.hasOwnProperty.call(
      bindings,
      BUILD_WORLD_GRAPH_INFORMATION_CHANNEL_BINDING_ID,
    )
  ) {
    throw new Error(
      `Missing required projection binding: ${BUILD_WORLD_GRAPH_INFORMATION_CHANNEL_BINDING_ID}`,
    );
  }
  const value = bindings[BUILD_WORLD_GRAPH_INFORMATION_CHANNEL_BINDING_ID];
  if (value === null || value === undefined) return null;
  if (!isWorldGraphChannel(value)) {
    throw new Error(
      "Malformed Build World Graph information-channel binding: expected a Surface Information channel or null.",
    );
  }
  return value;
}

function formatRevisionSummary(input: {
  requestedRevisionId: string | null;
  loadedRevisionId: string | null;
  revisionMode: "head" | "pinned";
  loadedIsHead: boolean;
}): string {
  if (input.revisionMode === "pinned" && input.requestedRevisionId) {
    const loaded = input.loadedRevisionId ?? "unknown";
    return `Pinned ${input.requestedRevisionId} · verified ${loaded}`;
  }
  const loaded = input.loadedRevisionId ?? "…";
  if (input.loadedIsHead) {
    return `Current head · loaded ${loaded}`;
  }
  return `Loaded ${loaded}`;
}

function lensCampaignLabel(lens: BuildGraphLensResolution): string | null {
  if (lens.status === "ready") return lens.campaignId;
  if (lens.status === "selection_required") return lens.worldId;
  return null;
}

function lensRevisionMode(lens: BuildGraphLensResolution): "head" | "pinned" {
  if (lens.status === "invalid") return "head";
  return lens.revision.kind === "pinned" ? "pinned" : "head";
}

function insertDeniedReasonForDocument(
  documentCampaignId: string,
  item: GraphReferenceSearchItem,
): string | null {
  const admission = admitBuildObjectInsert({
    documentCampaignId,
    objectCampaignScope: item.nodeView.campaign_scope,
  });
  return admission.ok ? null : admission.reason;
}

function StatusShell({
  children,
  alert,
}: {
  children: ReactNode;
  alert?: boolean;
}) {
  return (
    <p
      className={
        alert
          ? "build-reference-search-projection__status build-reference-search-projection__status--error"
          : "build-reference-search-projection__status"
      }
      role={alert ? "alert" : "status"}
    >
      {children}
    </p>
  );
}

export function BuildReferenceSearchProjection({ bindings }: BuildReferenceSearchProjectionProps) {
  const context = readBuildReferenceContextBinding(bindings);
  const channel = readBuildWorldGraphInformationChannelBinding(bindings);
  const { lens } = context;
  const snapshot = useSyncExternalStore(
    channel?.subscribe ?? BUILD_WORLD_GRAPH_FALLBACK_SNAPSHOT_SUBSCRIBE,
    channel?.getSnapshot ?? getFallbackSnapshot,
    channel?.getSnapshot ?? getFallbackSnapshot,
  ) as SurfaceInformationSnapshot<WorldGraphProjection>;

  if (lens.status === "invalid") {
    return (
      <section
        className="build-reference-search-projection"
        aria-label="World Graph search"
        data-testid="build-reference-search-projection"
      >
        <StatusShell alert>{lens.reason}</StatusShell>
      </section>
    );
  }

  if (lens.status === "selection_required") {
    return (
      <section
        className="build-reference-search-projection"
        aria-label="World Graph search"
        data-testid="build-reference-search-projection"
      >
        <StatusShell>
          {lens.reason} Select a campaign in the World Graph lens in the site navigation.
        </StatusShell>
      </section>
    );
  }

  const campaignLabel = lensCampaignLabel(lens);
  const revisionMode = lensRevisionMode(lens);
  const state = snapshot.state;
  const loadedRevisionId = observedRevisionId(state);
  const loadedIsHead = observedIsHead(state, revisionMode);
  const requestedRevisionId =
    lens.status === "ready" && lens.revision.kind === "pinned"
      ? lens.revision.revisionId
      : null;
  const revisionSummary = formatRevisionSummary({
    requestedRevisionId,
    loadedRevisionId,
    revisionMode,
    loadedIsHead,
  });
  const waitingForChannel = channel == null;

  if (waitingForChannel || state.status === "loading") {
    return (
      <section
        className="build-reference-search-projection"
        aria-label="World Graph search"
        data-testid="build-reference-search-projection"
      >
        <p className="build-reference-search-projection__lens" data-testid="build-reference-lens-summary">
          {campaignLabel} · {revisionMode === "pinned" ? "pinned" : "head"} · loading
        </p>
        <StatusShell>
          {waitingForChannel
            ? "Waiting for exact World Graph information…"
            : "Loading World Graph projection…"}
        </StatusShell>
      </section>
    );
  }

  if (state.status === "unavailable") {
    return (
      <section
        className="build-reference-search-projection"
        aria-label="World Graph search"
        data-testid="build-reference-search-projection"
      >
        <p className="build-reference-search-projection__lens" data-testid="build-reference-lens-summary">
          {campaignLabel} · {revisionSummary}
        </p>
        <StatusShell>World Graph is unavailable. {state.reason}</StatusShell>
      </section>
    );
  }

  if (state.status === "integrity_error") {
    return (
      <section
        className="build-reference-search-projection"
        aria-label="World Graph search"
        data-testid="build-reference-search-projection"
      >
        <p className="build-reference-search-projection__lens" data-testid="build-reference-lens-summary">
          {campaignLabel} · {revisionSummary}
        </p>
        <StatusShell alert>{state.reason}</StatusShell>
      </section>
    );
  }

  if (state.status === "stale") {
    return (
      <section
        className="build-reference-search-projection"
        aria-label="World Graph search"
        data-testid="build-reference-search-projection"
      >
        <p className="build-reference-search-projection__lens" data-testid="build-reference-lens-summary">
          {campaignLabel} · {revisionSummary}
        </p>
        <StatusShell alert>
          World Graph observation is stale. {state.reason} Insert is disabled.
        </StatusShell>
      </section>
    );
  }

  const items = searchItemsFromWorldGraphState(state);
  const insertDisabled =
    context.editorInsertDisabled || (state.status !== "ready" && state.status !== "empty");
  // EMPTY is a successful zero-result observation. Insert buttons cannot appear
  // without items, so do not reuse the editor-lock banner for emptiness.

  return (
    <section
      className="build-reference-search-projection"
      aria-label="World Graph search"
      data-testid="build-reference-search-projection"
    >
      <p className="build-reference-search-projection__lens" data-testid="build-reference-lens-summary">
        {campaignLabel} · {revisionSummary}
      </p>
      {state.status === "empty" ? (
        <StatusShell>World Graph projection is empty for this exact request.</StatusShell>
      ) : null}
      <GraphReferenceSearch
        items={items}
        projectionState="ready"
        projectionError={null}
        insertDisabled={insertDisabled}
        insertDeniedReason={(item) =>
          insertDeniedReasonForDocument(context.documentCampaignId, item)
        }
        onInsert={(item) => context.insertChip(item.nodeId)}
        onView={(item) => context.viewExact(item.nodeId)}
      />
    </section>
  );
}

function getFallbackSnapshot(): SurfaceInformationSnapshot<WorldGraphProjection> {
  return BUILD_WORLD_GRAPH_FALLBACK_SNAPSHOT;
}

function BUILD_WORLD_GRAPH_FALLBACK_SNAPSHOT_SUBSCRIBE(): () => void {
  return () => undefined;
}
