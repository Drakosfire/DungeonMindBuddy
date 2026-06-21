import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import type { ReferenceResolution } from "../reference/referenceResolver";

/** Ladder vocabulary: source artifact -> source anchor -> source unit */

export interface SourceArtifact {
  relpath: string;
  role?: string;
}

export interface SourceAnchor {
  kind: string;
  refId: string;
  label: string;
  href: string;
}

export interface SourceUnit {
  summary: string;
  fields: Record<string, string>;
  sourcePath?: string;
}

export function chipToSourceAnchor(ref: RunbookReferenceAttrs): SourceAnchor {
  const href = `#dmb-${ref.kind}:${ref.refType}:${ref.refId}`;
  return {
    kind: ref.kind,
    refId: ref.refId,
    label: ref.label,
    href,
  };
}

export function resolutionToSourceUnit(resolution: ReferenceResolution): SourceUnit {
  if (resolution.status !== "resolved" || !resolution.item) {
    return {
      summary: resolution.message,
      fields: {
        status: resolution.status,
        refType: resolution.ref.refType,
        refId: resolution.ref.refId,
      },
    };
  }

  const item = resolution.item as Record<string, unknown>;
  const fields: Record<string, string> = {};
  for (const [key, value] of Object.entries(item)) {
    if (value == null || value === "") continue;
    if (typeof value === "string" || typeof value === "number") {
      fields[key] = String(value);
    }
  }

  return {
    summary: resolution.message,
    fields,
    sourcePath: resolution.sourcePath,
  };
}

export interface DerivedViewsReader {
  resolveReference(ref: RunbookReferenceAttrs): Promise<ReferenceResolution>;
}

/** Corpus-on-disk reader today; shadow-retrieval swap replaces implementation only. */
export function createCorpusDerivedViewsReader(
  resolveReference: (ref: RunbookReferenceAttrs) => Promise<ReferenceResolution>,
): DerivedViewsReader {
  return { resolveReference };
}
