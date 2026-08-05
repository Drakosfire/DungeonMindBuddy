import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";

import type { AppChromeAction } from "../chrome/AppChrome";
import { validateSurfaceInteractionPublication } from "../surfaceInteraction/publication";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../surfaceInteraction/projection/projectionCatalog";
import {
  buildPlanSurfaceIdentity,
  validateProjectionSurfacePublication,
} from "./projectionSurfacePublication";
import { FIXTURE_DOC_ID } from "../planSurface/config/planSessionDescriptor";
import {
  LEGACY_APPCHROME_DISABLED,
  LEGACY_CONTEXT_UNAVAILABLE,
  ROUTE_COMPATIBILITY_PUBLICATIONS,
  adaptProjectionSurfaceToNeutralBase,
  buildAppChromeCompatibilityFragment,
  buildIndexRouteCompatibilityPublication,
  buildSurfaceRouteCompatibilityPublication,
  buildTiptapCalloutSpikeRouteCompatibilityPublication,
} from "./surfaceInteractionCompat";

describe("surfaceInteractionCompat", () => {
  it("maps legacy Plan publication fields exactly", () => {
    const validated = validateProjectionSurfacePublication({
      identity: buildPlanSurfaceIdentity({
        documentId: FIXTURE_DOC_ID,
        campaignId: "longmont-c2",
        liveSession: 22,
        memorySession: 21,
      }),
      config: {
        id: "plan",
        label: "Plan",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Plan",
        },
        tools: [{ id: "recap", label: "Recap", size: "wide" }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: { themeId: "mireward" },
      },
    });
    const neutral = adaptProjectionSurfaceToNeutralBase(validated);
    expect(neutral.surfaceId).toBe("plan");
    expect(neutral.identity.surfaceId).toBe("plan");
    expect(neutral.canvas).toEqual({
      canvasId: "markdown-canvas",
      workObject: { kind: "document", id: FIXTURE_DOC_ID },
    });
    expect(neutral.agentContext).toMatchObject({
      label: "Plan",
      campaignId: "longmont-c2",
      documentId: FIXTURE_DOC_ID,
      sessionNumber: 22,
      pointers: [],
    });
    expect(neutral.tools[0]).toMatchObject({
      id: "recap",
      label: "Recap",
      activation: { kind: "projection", projectionId: "recap" },
    });
    expect(neutral.projections[0]).toEqual({
      id: "recap",
      kind: "tool",
      preferredSize: "wide",
      bindingIds: [],
    });
    expect(neutral.projections).toContainEqual({
      id: GRAPH_REFERENCE_PROJECTION_ID,
      kind: "content",
      preferredSize: "wide",
      bindingIds: [],
    });
    expect(neutral.projectionBindings).toEqual([]);
    expect(validateSurfaceInteractionPublication(neutral).valid).toBe(true);
  });

  it("adds graph-reference content descriptor only for authorized Plan publications", () => {
    const planValidated = validateProjectionSurfacePublication({
      identity: buildPlanSurfaceIdentity({
        documentId: FIXTURE_DOC_ID,
        campaignId: "longmont-c2",
        liveSession: 22,
        memorySession: 21,
      }),
      config: {
        id: "plan",
        label: "Plan",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Plan",
        },
        tools: [{ id: "recap", label: "Recap", size: "wide" }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: {},
      },
    });
    const planNeutral = adaptProjectionSurfaceToNeutralBase(planValidated);
    expect(planNeutral.projections.some(
      (entry) => entry.id === GRAPH_REFERENCE_PROJECTION_ID && entry.kind === "content",
    )).toBe(true);

    // Compat still emits the descriptor without context; Provider lease gate revokes authority.
    const planWithoutContext = validateProjectionSurfacePublication({
      identity: { surfaceId: "plan", instanceKey: "plan\u001fno-context" },
      config: {
        id: "plan",
        label: "Plan",
        context: null,
        tools: [{ id: "recap", label: "Recap", size: "wide" }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: {},
      },
    });
    const planWithoutContextNeutral = adaptProjectionSurfaceToNeutralBase(planWithoutContext);
    expect(
      planWithoutContextNeutral.projections.some(
        (entry) => entry.id === GRAPH_REFERENCE_PROJECTION_ID,
      ),
    ).toBe(true);

    const ingestValidated = validateProjectionSurfacePublication({
      identity: { surfaceId: "ingest", instanceKey: "ingest\u001ftest" },
      config: {
        id: "ingest",
        label: "Ingest",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Ingest",
        },
        tools: [{ id: "ingest-recap", label: "Recap", size: "wide" }],
        canvas: { documentId: null },
        theme: {},
      },
    });
    const ingestNeutral = adaptProjectionSurfaceToNeutralBase(ingestValidated);
    expect(ingestNeutral.projections.some((entry) => entry.id === GRAPH_REFERENCE_PROJECTION_ID)).toBe(false);

    const buildValidated = validateProjectionSurfacePublication({
      identity: { surfaceId: "build", instanceKey: "build\u001ftest" },
      config: {
        id: "build",
        label: "Build",
        context: null,
        tools: [],
        canvas: { documentId: null },
        theme: {},
      },
    });
    const buildNeutral = adaptProjectionSurfaceToNeutralBase(buildValidated);
    expect(buildNeutral.projections.some((entry) => entry.id === GRAPH_REFERENCE_PROJECTION_ID)).toBe(false);
  });

  it("does not add graph-reference content when Plan identity and config disagree", () => {
    const contradictory = validateProjectionSurfacePublication({
      identity: { surfaceId: "plan", instanceKey: "plan\u001fcontradiction" },
      config: {
        id: "ingest",
        label: "Mismatched",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Ingest",
        },
        tools: [{ id: "ingest-recap", label: "Recap", size: "wide" }],
        canvas: { documentId: null },
        theme: {},
      },
    });
    const neutral = adaptProjectionSurfaceToNeutralBase(contradictory);
    expect(neutral.projections.some((entry) => entry.id === GRAPH_REFERENCE_PROJECTION_ID)).toBe(false);
  });

  it("disables legacy tools without render context using the stable reason", () => {
    const validated = validateProjectionSurfacePublication({
      identity: { surfaceId: "build", instanceKey: '["build","doc-1"]' },
      config: {
        id: "build",
        label: "Build",
        context: null,
        tools: [{ id: "find", label: "Find", size: "compact" }],
        canvas: { documentId: "doc-1" },
        theme: {},
      },
    });
    const neutral = adaptProjectionSurfaceToNeutralBase(validated);
    expect(neutral.tools[0]?.availability).toEqual({
      status: "disabled",
      disabledReason: LEGACY_CONTEXT_UNAVAILABLE,
    });
    expect(validateSurfaceInteractionPublication(neutral).valid).toBe(true);
  });

  it("maps AppChrome page actions and editor sections in predecessor order", () => {
    const pageClick = vi.fn();
    const editClick = vi.fn();
    const pageActions: AppChromeAction[] = [{
      id: "surface-inspector",
      label: "Inspector",
      onClick: pageClick,
    }];
    const fragment = buildAppChromeCompatibilityFragment({
      pageActions,
      editorTools: {
        pinnedActions: [{ id: "bold", label: "Bold", onClick: editClick, pressed: true }],
        sections: [{
          id: "callouts",
          title: "Callouts",
          defaultOpen: true,
          actions: [{ id: "note", label: "Note", onClick: editClick }],
          panel: "panel-never-published",
        }],
      },
      basePublication: {
        ...buildIndexRouteCompatibilityPublication(),
        canvas: {
          canvasId: "markdown-canvas",
          workObject: { kind: "document", id: "doc-1" },
        },
      },
      editCommandTarget: { kind: "document", id: "doc-1" },
    });
    expect(fragment.tools[0]?.placement).toMatchObject({
      groupId: "legacy-page-tools",
      groupLabel: "Page tools",
      groupOrder: 100,
      itemOrder: 0,
    });
    expect(fragment.editCommands.map((entry) => entry.id)).toEqual(["bold", "note"]);
    expect(fragment.editCommands[0]?.pressed).toBe(true);
    expect(fragment.editCommands[1]?.placement.groupDefaultOpen).toBe(true);
    expect(fragment.editCommands[0]?.target).toEqual({ kind: "document", id: "doc-1" });
    expect(fragment.tools[0]?.activation).toEqual({ kind: "command", invoke: pageClick });
    expect(JSON.stringify(fragment)).not.toContain("panel-never-published");
  });

  it("publishes no Edit commands when editCommandTarget is null", () => {
    const pageClick = vi.fn();
    const fragment = buildAppChromeCompatibilityFragment({
      pageActions: [{ id: "inspector", label: "Inspector", onClick: pageClick }],
      editorTools: {
        pinnedActions: [{ id: "bold", label: "Bold", onClick: () => {} }],
      },
      basePublication: {
        ...buildIndexRouteCompatibilityPublication(),
        canvas: {
          canvasId: "markdown-canvas",
          workObject: { kind: "document", id: "doc-canvas" },
        },
      },
      editCommandTarget: null,
    });
    expect(fragment.editCommands).toEqual([]);
    expect(fragment.tools).toHaveLength(1);
    expect(fragment.tools[0]?.id).toBe("inspector");
    expect(fragment.tools[0]?.activation).toEqual({ kind: "command", invoke: pageClick });
  });

  it("never infers Edit targets from basePublication canvas", () => {
    const source = readFileSync(join(__dirname, "surfaceInteractionCompat.ts"), "utf8");
    expect(source).toMatch(
      /editCommandTarget:\s*SurfaceInteractionWorkObjectIdentity\s*\|\s*null/,
    );
    expect(source).not.toMatch(/editCommandTarget\?:/);
    expect(source).not.toMatch(/canvasWorkObject\(/);
    expect(source).not.toMatch(
      /editCommandTarget\s*!==\s*undefined[\s\S]*canvasWorkObject|canvasWorkObject[\s\S]*editCommandTarget/,
    );

    const fragment = buildAppChromeCompatibilityFragment({
      pageActions: [],
      editorTools: {
        pinnedActions: [{ id: "bold", label: "Bold", onClick: () => {} }],
      },
      basePublication: {
        ...buildIndexRouteCompatibilityPublication(),
        canvas: {
          canvasId: "markdown-canvas",
          workObject: { kind: "document", id: "doc-canvas" },
        },
      },
      editCommandTarget: null,
    });
    expect(fragment.editCommands).toEqual([]);
  });

  it("maps disabled AppChrome actions to deterministic compatibility reasons", () => {
    const fragment = buildAppChromeCompatibilityFragment({
      pageActions: [{ id: "x", label: "X", disabled: true, onClick: () => {} }],
      editorTools: null,
      basePublication: buildSurfaceRouteCompatibilityPublication(),
      editCommandTarget: null,
    });
    expect(fragment.tools[0]?.availability).toEqual({
      status: "disabled",
      disabledReason: LEGACY_APPCHROME_DISABLED,
    });
  });

  it("stamps explicit editCommandTarget even when basePublication canvas differs", () => {
    const fragment = buildAppChromeCompatibilityFragment({
      pageActions: [],
      editorTools: {
        pinnedActions: [{ id: "bold", label: "Bold", onClick: () => {} }],
      },
      basePublication: {
        ...buildIndexRouteCompatibilityPublication(),
        canvas: {
          canvasId: "markdown-canvas",
          workObject: { kind: "document", id: "doc-b" },
        },
      },
      editCommandTarget: { kind: "document", id: "doc-a" },
    });
    expect(fragment.editCommands[0]?.target).toEqual({ kind: "document", id: "doc-a" });
  });

  it("builds exact route compatibility publications", () => {
    expect(buildIndexRouteCompatibilityPublication()).toMatchObject({
      surfaceId: "index",
      label: "Command Board",
      identity: ROUTE_COMPATIBILITY_PUBLICATIONS.index.identity,
      canvas: null,
    });
    expect(buildSurfaceRouteCompatibilityPublication()).toMatchObject({
      surfaceId: "surface",
      label: "Live Control",
      identity: ROUTE_COMPATIBILITY_PUBLICATIONS.surface.identity,
    });
    expect(buildTiptapCalloutSpikeRouteCompatibilityPublication()).toMatchObject({
      surfaceId: "tiptap-callout-spike",
      canvas: {
        canvasId: "tiptap-callout-spike",
        workObject: { kind: "spike", id: "tiptap-callout-spike" },
      },
    });
  });
});
