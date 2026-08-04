import { GraphReferenceSearch } from "../../graphReference/GraphReferenceSearch";
import type { BuildReferenceContextBinding } from "./buildBuildSurfaceInteractionPublication";
import { BUILD_REFERENCE_CONTEXT_BINDING_ID } from "./buildReferenceIds";
import type { BuildGraphLensResolution } from "./resolveBuildGraphLens";

export interface BuildReferenceSearchProjectionProps {
  bindings: Readonly<Record<string, unknown>>;
}

function isBuildReferenceContextBinding(value: unknown): value is BuildReferenceContextBinding {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<BuildReferenceContextBinding>;
  return (
    candidate.schema === "dmb_build_reference_context_v1"
    && typeof candidate.documentId === "string"
    && typeof candidate.documentCampaignId === "string"
    && candidate.lens != null
    && typeof candidate.loadedIsHead === "boolean"
    && typeof candidate.selectCampaign === "function"
    && typeof candidate.viewExact === "function"
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
      "Malformed Build reference context binding: expected schema dmb_build_reference_context_v1.",
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

export function BuildReferenceSearchProjection({ bindings }: BuildReferenceSearchProjectionProps) {
  const context = readBuildReferenceContextBinding(bindings);
  const { lens } = context;

  if (lens.status === "invalid") {
    return (
      <section
        className="build-reference-search-projection"
        aria-label="World Graph search"
        data-testid="build-reference-search-projection"
      >
        <p className="build-reference-search-projection__status" role="alert">
          {lens.reason}
        </p>
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
        <p className="build-reference-search-projection__status">{lens.reason}</p>
        <label className="build-reference-search-projection__label" htmlFor="build-reference-campaign-select">
          Campaign
        </label>
        <select
          id="build-reference-campaign-select"
          className="build-reference-search-projection__select"
          data-testid="build-reference-campaign-select"
          defaultValue=""
          onChange={(event) => {
            const campaignId = event.target.value.trim();
            if (campaignId) {
              context.selectCampaign(campaignId);
            }
          }}
        >
          <option value="" disabled>
            Select campaign…
          </option>
          {lens.availableCampaignIds.map((campaignId) => (
            <option key={campaignId} value={campaignId}>
              {campaignId}
            </option>
          ))}
        </select>
      </section>
    );
  }

  const campaignLabel = lensCampaignLabel(lens);
  const revisionMode = lensRevisionMode(lens);
  const revisionSummary = formatRevisionSummary({
    requestedRevisionId: context.requestedRevisionId,
    loadedRevisionId: context.loadedRevisionId,
    revisionMode,
    loadedIsHead: context.loadedIsHead,
  });

  if (context.projectionState === "loading") {
    return (
      <section
        className="build-reference-search-projection"
        aria-label="World Graph search"
        data-testid="build-reference-search-projection"
      >
        <p className="build-reference-search-projection__lens" data-testid="build-reference-lens-summary">
          {campaignLabel} · {revisionMode === "pinned" ? "pinned" : "head"} · loading
        </p>
        <p className="build-reference-search-projection__status" role="status">
          Loading World Graph projection…
        </p>
      </section>
    );
  }

  if (context.projectionState === "error") {
    return (
      <section
        className="build-reference-search-projection"
        aria-label="World Graph search"
        data-testid="build-reference-search-projection"
      >
        <p className="build-reference-search-projection__lens" data-testid="build-reference-lens-summary">
          {campaignLabel} · {revisionSummary}
        </p>
        <p className="build-reference-search-projection__status build-reference-search-projection__status--error" role="alert">
          {context.projectionError ?? "Could not load World Graph projection."}
        </p>
      </section>
    );
  }

  return (
    <section
      className="build-reference-search-projection"
      aria-label="World Graph search"
      data-testid="build-reference-search-projection"
    >
      <p className="build-reference-search-projection__lens" data-testid="build-reference-lens-summary">
        {campaignLabel} · {revisionSummary}
      </p>
      <GraphReferenceSearch
        items={context.items}
        projectionState={context.projectionState}
        projectionError={context.projectionError}
        onView={context.viewExact}
      />
    </section>
  );
}
