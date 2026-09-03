import { useEffect, useMemo, useState } from "react";

import { postWorldGraphProjection } from "../../api/liveApi";
import type { WorldGraphProjection, WorldGraphProjectionRequest } from "../../api/types";
import type { WorldGraphLensProjectionValue } from "../../graphLens/useWorldGraphLensProjection";
import {
  mapWorldGraphLensObservation,
  worldGraphLensInformationDescriptor,
} from "../../graphLens/worldGraphLensSurfaceInformation";
import {
  createSurfaceInformationChannel,
  type SurfaceInformationChannel,
} from "../../surfaceInformation";
import { worldGraphProjectionRequestKey } from "../../worldGraph/worldGraphProjectionRequestKey";
import { buildBuildWorldGraphProjectionRequest } from "../../worldGraph/worldGraphSurfaceContext";
import {
  buildWorldGraphInformationDescriptor,
} from "./buildWorldGraphSurfaceInformation";
import type { BuildGraphLensResolution } from "./resolveBuildGraphLens";

export { verifyWorldGraphProjectionResponse } from "../../worldGraph/verifyWorldGraphProjectionResponse";
export { formatProjectionSearchScopeLabel } from "./buildWorldGraphSurfaceInformation";

export interface UseBuildWorldGraphProjectionInput {
  lens: BuildGraphLensResolution;
  documentIdentity: { documentId: string; campaignId: string };
  /** App-level shared desired request identity — reused only when exact keys match. */
  sharedProjection?: WorldGraphLensProjectionValue | null;
  /** App-level shared Surface Information channel for the currently installed lens request. */
  sharedChannel?: SurfaceInformationChannel<WorldGraphProjection> | null;
}

export type BuildWorldGraphInformationSource =
  | "none"
  | "shared_pending"
  | "shared"
  | "secondary";

export interface UseBuildWorldGraphInformationResult {
  request: WorldGraphProjectionRequest | null;
  requestKey: string | null;
  loadKey: string;
  revisionMode: "head" | "pinned";
  requestedRevisionId: string | null;
  channel: SurfaceInformationChannel<WorldGraphProjection> | null;
  source: BuildWorldGraphInformationSource;
}

function resolveRevisionFields(lens: BuildGraphLensResolution): {
  revisionMode: "head" | "pinned";
  requestedRevisionId: string | null;
} {
  if (lens.status === "invalid") {
    return { revisionMode: "head", requestedRevisionId: null };
  }
  if (lens.revision.kind === "pinned") {
    return { revisionMode: "pinned", requestedRevisionId: lens.revision.revisionId };
  }
  return { revisionMode: "head", requestedRevisionId: null };
}

export function buildBuildWorldGraphRequestFromLens(
  lens: Extract<BuildGraphLensResolution, { status: "ready" }>,
): WorldGraphProjectionRequest | null {
  const revisionPin =
    lens.revision.kind === "pinned" ? lens.revision.revisionId : null;
  return buildBuildWorldGraphProjectionRequest({
    campaignId: lens.campaignId,
    revisionPin,
    scopeMode: lens.scopeMode,
    focus: lens.focus,
  });
}

/**
 * Structured load identity. Includes scope/focus so Find auth cannot cross lenses.
 * Revision mode and opaque revision id are separate fields so current-head mode
 * never collides with a pinned revision whose id is literally "head".
 */
export function buildBuildGraphProjectionLoadKey(input: {
  documentIdentity: { documentId: string; campaignId: string };
  lens: BuildGraphLensResolution;
}): string {
  const { documentIdentity, lens } = input;
  if (lens.status === "invalid") {
    return JSON.stringify([
      "dmb_build_graph_load_v1",
      documentIdentity.documentId,
      documentIdentity.campaignId,
      "invalid",
      null,
      null,
      null,
      null,
      null,
      lens.reason,
    ]);
  }
  if (lens.status === "selection_required") {
    return JSON.stringify([
      "dmb_build_graph_load_v1",
      lens.documentId,
      lens.documentCampaignId,
      "selection_required",
      null,
      lens.revision.kind,
      lens.revision.kind === "pinned" ? lens.revision.revisionId : null,
      lens.scopeMode,
      lens.focus.kind === "session" ? lens.focus.sessionId : null,
      lens.reason,
    ]);
  }
  return JSON.stringify([
    "dmb_build_graph_load_v1",
    lens.documentId,
    lens.documentCampaignId,
    "ready",
    lens.campaignId,
    lens.revision.kind,
    lens.revision.kind === "pinned" ? lens.revision.revisionId : null,
    lens.scopeMode,
    lens.focus.kind === "session"
      ? `${lens.focus.sessionId}@${lens.focus.focusCampaignId}`
      : null,
  ]);
}

function sharedChannelMatchesRequest(
  channel: SurfaceInformationChannel<WorldGraphProjection> | null,
  request: WorldGraphProjectionRequest | null,
): channel is SurfaceInformationChannel<WorldGraphProjection> {
  if (!channel || !request) return false;
  return channel.descriptor.channelId === worldGraphLensInformationDescriptor(request).channelId;
}

function secondaryChannelMatchesRequest(
  channel: SurfaceInformationChannel<WorldGraphProjection> | null,
  request: WorldGraphProjectionRequest | null,
): channel is SurfaceInformationChannel<WorldGraphProjection> {
  if (!channel || !request) return false;
  return channel.descriptor.channelId === buildWorldGraphInformationDescriptor(request).channelId;
}

/**
 * Build exact World Graph request ownership: reuse the app Surface Information
 * channel when request keys match, otherwise own one secondary exact channel.
 */
export function useBuildWorldGraphProjection(
  input: UseBuildWorldGraphProjectionInput,
): UseBuildWorldGraphInformationResult {
  const {
    lens,
    documentIdentity,
    sharedProjection = null,
    sharedChannel = null,
  } = input;
  const revisionFields = useMemo(() => resolveRevisionFields(lens), [lens]);

  const loadKey = useMemo(
    () => buildBuildGraphProjectionLoadKey({ documentIdentity, lens }),
    [documentIdentity, lens],
  );

  // When following the shared nav, use the resident request as canonical (head)
  // or clone it with the Build revision pin — never re-derive a divergent union anchor.
  const request = useMemo(() => {
    if (lens.status !== "ready") return null;
    const sharedRequest = sharedProjection?.request ?? null;
    if (sharedRequest && sharedRequest.worldId === lens.worldId) {
      if (lens.revision.kind === "pinned") {
        return {
          ...sharedRequest,
          revisionPin: lens.revision.revisionId,
        };
      }
      return {
        ...sharedRequest,
        revisionPin: sharedRequest.revisionPin ?? null,
      };
    }
    return buildBuildWorldGraphRequestFromLens(lens);
  }, [lens, sharedProjection?.request]);

  const requestKey = useMemo(
    () => (request ? worldGraphProjectionRequestKey(request) : null),
    [request],
  );

  const desiredKeysMatch =
    Boolean(requestKey)
    && sharedProjection?.requestKey != null
    && sharedProjection.requestKey === requestKey;

  const ownsSecondary = Boolean(request && requestKey && !desiredKeysMatch);

  const [secondaryChannel, setSecondaryChannel] = useState<
    SurfaceInformationChannel<WorldGraphProjection> | null
  >(null);

  useEffect(() => {
    if (!ownsSecondary || !request || !requestKey) {
      setSecondaryChannel(null);
      return;
    }
    const ownedRequest = request;
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      buildWorldGraphInformationDescriptor(ownedRequest),
    );
    setSecondaryChannel(channel);
    return () => {
      channel.dispose();
      setSecondaryChannel(null);
    };
    // requestKey is exact-request identity; `request` is recovered from that render.
  }, [ownsSecondary, requestKey]);

  useEffect(() => {
    if (!ownsSecondary || !request || !secondaryChannelMatchesRequest(secondaryChannel, request)) {
      return;
    }
    const loadRequest = request;
    const loadChannel = secondaryChannel;
    const ticket = loadChannel.beginObservation();
    if (!ticket) {
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const response = await postWorldGraphProjection(loadRequest);
        if (cancelled) return;
        loadChannel.commit(
          ticket,
          mapWorldGraphLensObservation({ request: loadRequest, response }),
        );
      } catch (error) {
        if (cancelled) return;
        loadChannel.commit(
          ticket,
          mapWorldGraphLensObservation({ request: loadRequest, response: null, error }),
        );
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ownsSecondary, requestKey, secondaryChannel]);

  const matchingSharedChannel = desiredKeysMatch && sharedChannelMatchesRequest(sharedChannel, request)
    ? sharedChannel
    : null;
  const matchingSecondaryChannel =
    ownsSecondary && secondaryChannelMatchesRequest(secondaryChannel, request)
      ? secondaryChannel
      : null;

  let source: BuildWorldGraphInformationSource = "none";
  let channel: SurfaceInformationChannel<WorldGraphProjection> | null = null;
  if (lens.status === "ready" && request && requestKey) {
    if (desiredKeysMatch) {
      if (matchingSharedChannel) {
        source = "shared";
        channel = matchingSharedChannel;
      } else {
        source = "shared_pending";
        channel = null;
      }
    } else {
      source = "secondary";
      channel = matchingSecondaryChannel;
    }
  }

  return {
    request,
    requestKey,
    loadKey,
    revisionMode: revisionFields.revisionMode,
    requestedRevisionId: revisionFields.requestedRevisionId,
    channel,
    source,
  };
}
