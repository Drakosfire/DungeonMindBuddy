import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildBuildSourceNavigationHref,
  parseBuildSourceNavigationQuery,
  resolveAndNavigateToBuildSource,
} from "./sourceNavigation";
import type { BuildSourceNavigationResponse } from "../api/types";

vi.mock("../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../api/liveApi")>("../api/liveApi");
  return {
    ...actual,
    getBuildSourceNavigation: vi.fn(),
  };
});

import { getBuildSourceNavigation } from "../api/liveApi";

const DOC_ID = "11111111-1111-4111-8111-111111111111";
const ARTIFACT_ID = "artifact-glass-hesta";
const SPAN_ID = "span-hesta-second-paragraph";

const exactResult: BuildSourceNavigationResponse = {
  schema: "dmb_build_source_navigation_v1",
  status: "exact",
  sourceArtifactId: ARTIFACT_ID,
  sourceSpanRefId: SPAN_ID,
  documentId: DOC_ID,
  worldId: "the-glass-orchard",
  campaignId: "the-glass-orchard",
  artifactDocumentRevision: 2,
  currentDocumentRevision: 2,
  artifactContentSha256: "sha256:artifact",
  currentContentSha256: "sha256:artifact",
  startLine: 5,
  endLine: 7,
  canHighlight: true,
  message: "",
  diagnostics: [],
};

describe("buildBuildSourceNavigationHref", () => {
  it("builds governed Build href with document, campaign, and A/S params", () => {
    const href = buildBuildSourceNavigationHref(exactResult, "?dogfood=1&tool=recap");
    const url = new URL(href, "http://localhost");
    expect(url.pathname).toBe("/build");
    expect(url.searchParams.get("documentId")).toBe(DOC_ID);
    expect(url.searchParams.get("campaign")).toBe("the-glass-orchard");
    expect(url.searchParams.get("sourceArtifactId")).toBe(ARTIFACT_ID);
    expect(url.searchParams.get("sourceSpanRefId")).toBe(SPAN_ID);
    expect(url.searchParams.get("dogfood")).toBe("1");
    expect(url.searchParams.get("tool")).toBe("recap");
    expect(url.searchParams.get("startLine")).toBeNull();
    expect(url.searchParams.get("endLine")).toBeNull();
  });
});

describe("parseBuildSourceNavigationQuery", () => {
  it("returns A/S pair when both query params are present", () => {
    expect(
      parseBuildSourceNavigationQuery(
        `?documentId=${DOC_ID}&sourceArtifactId=${ARTIFACT_ID}&sourceSpanRefId=${SPAN_ID}`,
      ),
    ).toEqual({
      sourceArtifactId: ARTIFACT_ID,
      sourceSpanRefId: SPAN_ID,
    });
  });

  it("returns null when either locator is missing", () => {
    expect(parseBuildSourceNavigationQuery(`?sourceArtifactId=${ARTIFACT_ID}`)).toBeNull();
    expect(parseBuildSourceNavigationQuery(`?sourceSpanRefId=${SPAN_ID}`)).toBeNull();
    expect(parseBuildSourceNavigationQuery("")).toBeNull();
  });
});

describe("resolveAndNavigateToBuildSource", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("resolves server authority then navigates to derived href", async () => {
    vi.mocked(getBuildSourceNavigation).mockResolvedValue(exactResult);
    const navigate = vi.fn();

    await resolveAndNavigateToBuildSource({
      sourceArtifactId: ARTIFACT_ID,
      sourceSpanRefId: SPAN_ID,
      navigate,
      currentSearch: "?dogfood=1",
    });

    expect(getBuildSourceNavigation).toHaveBeenCalledWith({
      sourceArtifactId: ARTIFACT_ID,
      sourceSpanRefId: SPAN_ID,
    });
    expect(navigate).toHaveBeenCalledOnce();
    const href = String(navigate.mock.calls[0][0]);
    expect(href).toContain("/build?");
    expect(href).toContain(`documentId=${DOC_ID}`);
    expect(href).toContain(`sourceArtifactId=${ARTIFACT_ID}`);
    expect(href).toContain(`sourceSpanRefId=${SPAN_ID}`);
  });

  it("propagates resolver failures without inventing a document href", async () => {
    vi.mocked(getBuildSourceNavigation).mockRejectedValue(new Error("Source span not found."));
    const navigate = vi.fn();

    await expect(
      resolveAndNavigateToBuildSource({
        sourceArtifactId: ARTIFACT_ID,
        sourceSpanRefId: "missing-span",
        navigate,
      }),
    ).rejects.toThrow("Source span not found.");
    expect(navigate).not.toHaveBeenCalled();
  });
});
