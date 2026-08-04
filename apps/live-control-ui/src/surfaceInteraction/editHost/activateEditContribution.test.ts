import { describe, expect, it, vi } from "vitest";

import { buildSurfaceInteractionIdentity } from "../surfaceIdentity";
import type {
  SurfaceInteractionEditCommandContribution,
  SurfaceInteractionPublication,
} from "../types";
import { activateEditContribution } from "./activateEditContribution";

function makePublication(
  overrides: Partial<SurfaceInteractionPublication> = {},
): SurfaceInteractionPublication {
  return {
    surfaceId: "test",
    label: "Test",
    identity: buildSurfaceInteractionIdentity({ surfaceId: "test", instanceParts: ["test"] }),
    canvas: {
      canvasId: "markdown-canvas",
      workObject: { kind: "document", id: "doc-1" },
    },
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
    ...overrides,
  };
}

function makeEdit(
  id: string,
  overrides: Partial<SurfaceInteractionEditCommandContribution> = {},
): SurfaceInteractionEditCommandContribution {
  return {
    id,
    label: id,
    placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
    availability: { status: "enabled" },
    target: { kind: "document", id: "doc-1" },
    invoke: vi.fn(),
    ...overrides,
  };
}

describe("activateEditContribution", () => {
  it("returns stale when publication is null", () => {
    expect(
      activateEditContribution({
        publication: null,
        commandId: "save",
        expectedTarget: { kind: "document", id: "doc-1" },
      }),
    ).toEqual({ status: "ignored", reason: "stale" });
  });

  it("returns missing when the command id is absent", () => {
    const publication = makePublication({
      editCommands: [makeEdit("save")],
    });
    expect(
      activateEditContribution({
        publication,
        commandId: "lock",
        expectedTarget: { kind: "document", id: "doc-1" },
      }),
    ).toEqual({ status: "ignored", reason: "missing" });
  });

  it("returns disabled when availability is not enabled", () => {
    const invoke = vi.fn();
    const publication = makePublication({
      editCommands: [
        makeEdit("save", {
          availability: { status: "disabled", disabledReason: "Busy" },
          invoke,
        }),
      ],
    });
    expect(
      activateEditContribution({
        publication,
        commandId: "save",
        expectedTarget: { kind: "document", id: "doc-1" },
      }),
    ).toEqual({ status: "ignored", reason: "disabled" });
    expect(invoke).not.toHaveBeenCalled();
  });

  it("returns no_canvas when the publication has no canvas work object", () => {
    const invoke = vi.fn();
    const publication = makePublication({
      canvas: null,
      editCommands: [makeEdit("save", { invoke })],
    });
    expect(
      activateEditContribution({
        publication,
        commandId: "save",
        expectedTarget: { kind: "document", id: "doc-1" },
      }),
    ).toEqual({ status: "ignored", reason: "no_canvas" });
    expect(invoke).not.toHaveBeenCalled();
  });

  it("returns target_mismatch when expected, command, and canvas disagree", () => {
    const invoke = vi.fn();
    const publication = makePublication({
      editCommands: [
        makeEdit("save", {
          target: { kind: "document", id: "doc-other" },
          invoke,
        }),
      ],
    });
    expect(
      activateEditContribution({
        publication,
        commandId: "save",
        expectedTarget: { kind: "document", id: "doc-1" },
      }),
    ).toEqual({ status: "ignored", reason: "target_mismatch" });
    expect(invoke).not.toHaveBeenCalled();
  });

  it("returns target_mismatch when expectedTarget alone disagrees with canvas", () => {
    const invoke = vi.fn();
    const publication = makePublication({
      editCommands: [makeEdit("save", { invoke })],
    });
    expect(
      activateEditContribution({
        publication,
        commandId: "save",
        expectedTarget: { kind: "document", id: "doc-stale" },
      }),
    ).toEqual({ status: "ignored", reason: "target_mismatch" });
    expect(invoke).not.toHaveBeenCalled();
  });

  it("invokes through the current publication when all targets match", () => {
    const invoke = vi.fn();
    const publication = makePublication({
      editCommands: [makeEdit("save", { invoke })],
    });
    expect(
      activateEditContribution({
        publication,
        commandId: "save",
        expectedTarget: { kind: "document", id: "doc-1" },
      }),
    ).toEqual({ status: "invoked" });
    expect(invoke).toHaveBeenCalledTimes(1);
  });

  it("returns target_mismatch when expectedTarget is null despite canvas", () => {
    const invoke = vi.fn();
    const publication = makePublication({
      editCommands: [makeEdit("save", { invoke })],
    });
    expect(
      activateEditContribution({
        publication,
        commandId: "save",
        expectedTarget: null,
      }),
    ).toEqual({ status: "ignored", reason: "target_mismatch" });
    expect(invoke).not.toHaveBeenCalled();
  });
});
