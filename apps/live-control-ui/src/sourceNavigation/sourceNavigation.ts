import { getBuildSourceNavigation } from "../api/liveApi";
import type { BuildSourceNavigationResponse } from "../api/types";
import { buildDocumentSelectionSearch } from "../buildSurface/buildDocumentNavigation";

export type BuildSourceNavigationQuery = {
  sourceArtifactId: string;
  sourceSpanRefId: string;
};

/** Server-derived Build href with A/S locators for hard-reload re-resolution. */
export function buildBuildSourceNavigationHref(
  result: BuildSourceNavigationResponse,
  currentSearch?: string | null,
): string {
  const base = buildDocumentSelectionSearch(
    currentSearch ?? "",
    result.documentId,
    result.campaignId,
  );
  const params = new URLSearchParams(base.startsWith("?") ? base.slice(1) : base);
  params.set("sourceArtifactId", result.sourceArtifactId);
  params.set("sourceSpanRefId", result.sourceSpanRefId);
  const query = params.toString();
  return query ? `/build?${query}` : "/build";
}

export function parseBuildSourceNavigationQuery(
  search: string | null | undefined,
): BuildSourceNavigationQuery | null {
  const params = new URLSearchParams(search ?? "");
  const sourceArtifactId = params.get("sourceArtifactId")?.trim();
  const sourceSpanRefId = params.get("sourceSpanRefId")?.trim();
  if (!sourceArtifactId || !sourceSpanRefId) {
    return null;
  }
  return { sourceArtifactId, sourceSpanRefId };
}

export async function resolveAndNavigateToBuildSource(args: {
  sourceArtifactId: string;
  sourceSpanRefId: string;
  navigate: (href: string) => void;
  currentSearch?: string | null;
}): Promise<void> {
  const result = await getBuildSourceNavigation({
    sourceArtifactId: args.sourceArtifactId,
    sourceSpanRefId: args.sourceSpanRefId,
  });
  args.navigate(buildBuildSourceNavigationHref(result, args.currentSearch));
}
