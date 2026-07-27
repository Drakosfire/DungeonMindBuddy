export const GRAPH_REFERENCE_CAPABILITY_IDS = [
  "reference_render",
  "reference_insert_existing",
  "reference_project",
] as const;

export type GraphReferenceCapabilityId = (typeof GRAPH_REFERENCE_CAPABILITY_IDS)[number];

export type GraphReferenceResolution =
  | {
      kind: "resolved_graph";
      nodeId: string;
      revision?: string | null;
    }
  | {
      kind: "resolved_corpus_fallback";
      refId: string;
    }
  | {
      kind: "ambiguous";
      candidates: string[];
      refId?: string | null;
    }
  | {
      kind: "unresolved";
      refId: string;
    };
