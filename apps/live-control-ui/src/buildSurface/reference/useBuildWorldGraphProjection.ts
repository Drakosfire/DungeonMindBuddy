import { useEffect, useMemo, useRef, useState } from "react";

import { LiveApiError, postWorldGraphProjection } from "../../api/liveApi";
import type { WorldGraphProjection } from "../../api/types";
import { referenceFromGraphNode } from "../../graphReference/referenceFromGraphNode";
import type {
  GraphReferenceProjectionState,
  GraphReferenceSearchItem,
} from "../../graphReference/types";
import { adaptWorldGraphNodeView } from "../../worldGraph/worldGraphNodeViewAdapter";
import { buildBuildWorldGraphProjectionRequest } from "../../worldGraph/worldGraphSurfaceContext";
import type { BuildGraphLensResolution } from "./resolveBuildGraphLens";

export interface UseBuildWorldGraphProjectionInput {
  lens: BuildGraphLensResolution;
  documentIdentity: { documentId: string; campaignId: string };
}

export interface UseBuildWorldGraphProjectionResult {
  projection: WorldGraphProjection | null;
  state: GraphReferenceProjectionState;
  error: string | null;
  requestedRevisionId: string | null;
  loadedRevisionId: string | null;
  revisionMode: "head" | "pinned";
  generation: number;
  items: readonly GraphReferenceSearchItem[];
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

function adaptProjectionSearchItems(
  projection: WorldGraphProjection,
  scopeCampaignId: string,
): GraphReferenceSearchItem[] {
  return projection.nodes.map((node) => {
    const nodeView = adaptWorldGraphNodeView(node);
    return {
      nodeId: nodeView.node_id,
      label: nodeView.label,
      kind: nodeView.kind,
      role: nodeView.role,
      summary: nodeView.summary ?? null,
      aliases: nodeView.aliases ?? [],
      scopeLabel: nodeView.campaign_scope ?? scopeCampaignId,
      reference: referenceFromGraphNode(nodeView),
      nodeView,
    };
  });
}

function formatProjectionLoadError(error: unknown): string {
  if (error instanceof LiveApiError) {
    return error.code ? `${error.message} (${error.code})` : error.message;
  }
  return error instanceof Error ? error.message : "Failed to load World Graph projection.";
}

export function useBuildWorldGraphProjection(
  input: UseBuildWorldGraphProjectionInput,
): UseBuildWorldGraphProjectionResult {
  const { lens, documentIdentity } = input;
  const revisionFields = useMemo(() => resolveRevisionFields(lens), [lens]);

  const [projection, setProjection] = useState<WorldGraphProjection | null>(null);
  const [state, setState] = useState<GraphReferenceProjectionState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [loadedRevisionId, setLoadedRevisionId] = useState<string | null>(null);
  const [generation, setGeneration] = useState(0);
  const requestGenerationRef = useRef(0);

  const loadKey = useMemo(() => {
    const docKey = `${documentIdentity.documentId}:${documentIdentity.campaignId}`;
    if (lens.status === "invalid") {
      return `${docKey}:invalid:${lens.reason}`;
    }
    if (lens.status === "selection_required") {
      const revisionKey =
        lens.revision.kind === "pinned" ? lens.revision.revisionId : "head";
      return `${docKey}:selection:${lens.documentCampaignId}:${revisionKey}`;
    }
    const revisionKey =
      lens.revision.kind === "pinned" ? lens.revision.revisionId : "head";
    return `${docKey}:ready:${lens.campaignId}:${revisionKey}`;
  }, [documentIdentity.campaignId, documentIdentity.documentId, lens]);

  useEffect(() => {
    const currentGeneration = ++requestGenerationRef.current;
    setGeneration(currentGeneration);
    const isCurrent = () => currentGeneration === requestGenerationRef.current;

    if (lens.status === "selection_required") {
      setProjection(null);
      setState("unavailable");
      setError(lens.reason);
      setLoadedRevisionId(null);
      return () => {
        requestGenerationRef.current += 1;
      };
    }

    if (lens.status === "invalid") {
      setProjection(null);
      setState("error");
      setError(lens.reason);
      setLoadedRevisionId(null);
      return () => {
        requestGenerationRef.current += 1;
      };
    }

    const revisionPin =
      lens.revision.kind === "pinned" ? lens.revision.revisionId : null;
    const request = buildBuildWorldGraphProjectionRequest({
      campaignId: lens.campaignId,
      revisionPin,
    });

    if (!request) {
      setProjection(null);
      setState("error");
      setError(`Unknown campaign mapping for ${lens.campaignId}.`);
      setLoadedRevisionId(null);
      return () => {
        requestGenerationRef.current += 1;
      };
    }

    setProjection(null);
    setState("loading");
    setError(null);
    setLoadedRevisionId(null);

    void (async () => {
      try {
        const response = await postWorldGraphProjection(request);
        if (!isCurrent()) return;

        const responseRevisionId = response.snapshot.revisionId;
        if (lens.revision.kind === "pinned") {
          if (responseRevisionId !== lens.revision.revisionId) {
            setProjection(null);
            setState("error");
            setError(
              `Pinned revision ${lens.revision.revisionId} does not match loaded revision ${responseRevisionId}.`,
            );
            setLoadedRevisionId(null);
            return;
          }
        }

        setProjection(response);
        setState("ready");
        setError(null);
        setLoadedRevisionId(responseRevisionId);
      } catch (loadError) {
        if (!isCurrent()) return;
        setProjection(null);
        setState("error");
        setError(formatProjectionLoadError(loadError));
        setLoadedRevisionId(null);
      }
    })();

    return () => {
      requestGenerationRef.current += 1;
    };
  }, [lens, loadKey]);

  const items = useMemo(() => {
    if (state !== "ready" || !projection || lens.status !== "ready") {
      return [];
    }
    return adaptProjectionSearchItems(projection, lens.campaignId);
  }, [lens, projection, state]);

  return {
    projection,
    state,
    error,
    requestedRevisionId: revisionFields.requestedRevisionId,
    loadedRevisionId,
    revisionMode: revisionFields.revisionMode,
    generation,
    items,
  };
}
