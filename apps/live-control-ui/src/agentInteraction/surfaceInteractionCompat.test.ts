import { describe, expect, it, vi } from "vitest";

import type { AppChromeAction } from "../chrome/AppChrome";
import { validateSurfaceInteractionPublication } from "../surfaceInteraction/publication";
import {
  buildPlanSurfaceIdentity,
  validateProjectionSurfacePublication,
} from "./projectionSurfacePublication";
import { FIXTURE_DOC_ID } from "../planSurface/config/planSessionDescriptor";
import {
  BLANK_COMMAND_TARGET,
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
    expect(neutral.projectionBindings).toEqual([]);
    expect(validateSurfaceInteractionPublication(neutral).valid).toBe(true);
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
        pinnedActions: [{ id: "bold", label: "Bold", onClick: editClick }],
        sections: [{
          id: "callouts",
          title: "Callouts",
          actions: [{ id: "note", label: "Note", onClick: editClick }],
        }],
      },
      basePublication: buildIndexRouteCompatibilityPublication(),
    });
    expect(fragment.tools[0]?.placement).toMatchObject({
      groupId: "legacy-page-tools",
      groupLabel: "Page tools",
      groupOrder: 100,
      itemOrder: 0,
    });
    expect(fragment.editCommands.map((entry) => entry.id)).toEqual(["bold", "note"]);
    expect(fragment.tools[0]?.activation).toEqual({ kind: "command", invoke: pageClick });
  });

  it("uses blank edit targets when base canvas work object is missing", () => {
    const fragment = buildAppChromeCompatibilityFragment({
      pageActions: [],
      editorTools: {
        pinnedActions: [{ id: "bold", label: "Bold", onClick: () => {} }],
      },
      basePublication: buildIndexRouteCompatibilityPublication(),
    });
    expect(fragment.editCommands[0]?.target).toEqual(BLANK_COMMAND_TARGET);
    const composed = {
      ...buildIndexRouteCompatibilityPublication(),
      editCommands: fragment.editCommands,
    };
    const result = validateSurfaceInteractionPublication(composed);
    expect(result.valid).toBe(false);
    expect(
      result.issues.some((issue) =>
        issue.code === "command_target_invalid" || issue.code === "contribution_shape_invalid"),
    ).toBe(true);
  });

  it("maps disabled AppChrome actions to deterministic compatibility reasons", () => {
    const fragment = buildAppChromeCompatibilityFragment({
      pageActions: [{ id: "x", label: "X", disabled: true, onClick: () => {} }],
      editorTools: null,
      basePublication: buildSurfaceRouteCompatibilityPublication(),
    });
    expect(fragment.tools[0]?.availability).toEqual({
      status: "disabled",
      disabledReason: LEGACY_APPCHROME_DISABLED,
    });
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
