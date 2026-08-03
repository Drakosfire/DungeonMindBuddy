import { describe, expect, it, vi } from "vitest";

import { buildSurfaceInteractionIdentity } from "../surfaceIdentity";
import type { SurfaceInteractionPublication, SurfaceInteractionToolContribution } from "../types";
import { activateToolContribution } from "./activateToolContribution";

function makePublication(
  tools: readonly SurfaceInteractionToolContribution[],
): SurfaceInteractionPublication {
  return {
    surfaceId: "test",
    label: "Test",
    identity: buildSurfaceInteractionIdentity({ surfaceId: "test", instanceParts: ["test"] }),
    canvas: null,
    agentContext: null,
    tools,
    editCommands: [],
    projections: [],
    projectionBindings: [],
  };
}

function commandTool(
  id: string,
  invoke: () => void,
  availability: SurfaceInteractionToolContribution["availability"] = { status: "enabled" },
): SurfaceInteractionToolContribution {
  return {
    id,
    label: id,
    placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
    availability,
    activation: { kind: "command", invoke },
  };
}

function projectionTool(id: string, projectionId: string): SurfaceInteractionToolContribution {
  return {
    id,
    label: id,
    placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
    availability: { status: "enabled" },
    activation: { kind: "projection", projectionId },
  };
}

describe("activateToolContribution", () => {
  it("returns stale when publication is null", () => {
    const openProjectionTool = vi.fn();
    expect(
      activateToolContribution({
        publication: null,
        toolId: "recap",
        openProjectionTool,
      }),
    ).toEqual({ status: "ignored", reason: "stale" });
    expect(openProjectionTool).not.toHaveBeenCalled();
  });

  it("returns missing when the tool id is absent from the publication", () => {
    const openProjectionTool = vi.fn();
    const publication = makePublication([projectionTool("recap", "recap")]);
    expect(
      activateToolContribution({
        publication,
        toolId: "party-registry",
        openProjectionTool,
      }),
    ).toEqual({ status: "ignored", reason: "missing" });
    expect(openProjectionTool).not.toHaveBeenCalled();
  });

  it("returns disabled when the tool availability is not enabled", () => {
    const openProjectionTool = vi.fn();
    const publication = makePublication([
      commandTool("inspector", vi.fn(), {
        status: "disabled",
        disabledReason: "Unavailable",
      }),
    ]);
    expect(
      activateToolContribution({
        publication,
        toolId: "inspector",
        openProjectionTool,
      }),
    ).toEqual({ status: "ignored", reason: "disabled" });
    expect(openProjectionTool).not.toHaveBeenCalled();
  });

  it("invokes command tools through the current publication snapshot", () => {
    const invoke = vi.fn();
    const publication = makePublication([commandTool("inspector", invoke)]);
    const openProjectionTool = vi.fn();

    expect(
      activateToolContribution({
        publication,
        toolId: "inspector",
        openProjectionTool,
      }),
    ).toEqual({ status: "invoked", mode: "command" });
    expect(invoke).toHaveBeenCalledTimes(1);
    expect(openProjectionTool).not.toHaveBeenCalled();
  });

  it("opens projection tools via the host callback", () => {
    const openProjectionTool = vi.fn();
    const publication = makePublication([projectionTool("recap", "recap")]);

    expect(
      activateToolContribution({
        publication,
        toolId: "recap",
        openProjectionTool,
      }),
    ).toEqual({ status: "opened", mode: "projection", projectionId: "recap" });
    expect(openProjectionTool).toHaveBeenCalledWith("recap");
  });

  it("returns unsupported for unknown activation kinds", () => {
    const publication = makePublication([
      {
        id: "mystery",
        label: "Mystery",
        placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
        availability: { status: "enabled" },
        activation: { kind: "unsupported" } as never,
      },
    ]);

    expect(
      activateToolContribution({
        publication,
        toolId: "mystery",
        openProjectionTool: vi.fn(),
      }),
    ).toEqual({ status: "ignored", reason: "unsupported" });
  });
});
