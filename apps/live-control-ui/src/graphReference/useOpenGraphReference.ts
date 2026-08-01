import { useCallback } from "react";

import type {
  GraphReferenceProjectionState,
  GraphReferenceResolution,
  OpenGraphReferenceArgs,
} from "./types";

export interface UseOpenGraphReferenceOptions {
  openGraphReference: (args: OpenGraphReferenceArgs) => void;
}

export function useOpenGraphReference({ openGraphReference }: UseOpenGraphReferenceOptions) {
  const openResolution = useCallback(
    (
      resolution: GraphReferenceResolution,
      options?: {
        projectionState?: GraphReferenceProjectionState | null;
        glanceOnly?: boolean;
        reference?: OpenGraphReferenceArgs["reference"];
      },
    ) => {
      openGraphReference({
        resolution,
        projectionState: options?.projectionState ?? resolution.projectionState ?? null,
        glanceOnly: options?.glanceOnly,
        reference: options?.reference ?? resolution.reference,
      });
    },
    [openGraphReference],
  );

  return { openResolution, openGraphReference };
}
