import { describe, expect, it, vi } from "vitest";

import { validateSurfaceInteractionPublication } from "./publication";
import { sameSurfaceInteractionIdentity } from "./surfaceIdentity";
import type {
  SurfaceInteractionAvailability,
  SurfaceInteractionEditCommandContribution,
  SurfaceInteractionPlacement,
  SurfaceInteractionProjectionBinding,
  SurfaceInteractionProjectionDescriptor,
  SurfaceInteractionPublication,
  SurfaceInteractionToolActivation,
  SurfaceInteractionToolContribution,
  SurfaceInteractionValidationIssueCode,
} from "./types";

function makePlacement(overrides: Partial<SurfaceInteractionPlacement> = {}): SurfaceInteractionPlacement {
  return { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0, ...overrides };
}

const ENABLED: SurfaceInteractionAvailability = { status: "enabled" };

function makeTool(
  id: string,
  overrides: Partial<SurfaceInteractionToolContribution> = {},
): SurfaceInteractionToolContribution {
  return {
    id,
    label: `${id} label`,
    placement: makePlacement(),
    availability: ENABLED,
    activation: { kind: "command", invoke: () => {} },
    ...overrides,
  };
}

function makeEditCommand(
  id: string,
  overrides: Partial<SurfaceInteractionEditCommandContribution> = {},
): SurfaceInteractionEditCommandContribution {
  return {
    id,
    label: `${id} label`,
    placement: makePlacement(),
    availability: ENABLED,
    target: { kind: "document", id: "doc-1" },
    invoke: () => {},
    ...overrides,
  };
}

function makeProjection(
  id: string,
  overrides: Partial<SurfaceInteractionProjectionDescriptor> = {},
): SurfaceInteractionProjectionDescriptor {
  return { id, kind: "tool", preferredSize: "compact", bindingIds: [], ...overrides };
}

function makeBinding(id: string, value: unknown = {}): SurfaceInteractionProjectionBinding {
  return { id, value };
}

function makePublication(
  overrides: Partial<SurfaceInteractionPublication> = {},
): SurfaceInteractionPublication {
  return {
    surfaceId: "plan",
    label: "Plan",
    identity: { surfaceId: "plan", instanceKey: '["plan","doc-1"]' },
    canvas: null,
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
    ...overrides,
  };
}

function codesOf(result: ReturnType<typeof validateSurfaceInteractionPublication>) {
  return result.valid ? [] : result.issues.map((issue) => issue.code);
}

function deepFreeze<T>(value: T): T {
  if (value && typeof value === "object") {
    Object.freeze(value);
    for (const key of Object.keys(value)) {
      deepFreeze((value as Record<string, unknown>)[key]);
    }
  }
  return value;
}

describe("validateSurfaceInteractionPublication — valid publications", () => {
  it("accepts an empty publication with nullable canvas and agent context", () => {
    const result = validateSurfaceInteractionPublication(makePublication());
    expect(result).toEqual({ valid: true, publication: expect.any(Object) });
  });

  it("accepts a fully coherent populated publication without cloning away identity", () => {
    const bindingValue = { token: "opaque-runtime-value" };
    const invoke = vi.fn();
    const publication = makePublication({
      canvas: { canvasId: "canvas-1", workObject: { kind: "document", id: "doc-1" } },
      agentContext: {
        label: "Plan agent context",
        campaignId: "camp-1",
        documentId: "doc-1",
        sessionNumber: 3,
        ambientSummary: "short ambient summary",
        pointers: [{ kind: "document", value: "doc-1" }],
      },
      tools: [
        makeTool("tool-open", {
          activation: { kind: "projection", projectionId: "proj-tool" },
        }),
        makeTool("tool-action", { activation: { kind: "command", invoke } }),
      ],
      editCommands: [makeEditCommand("edit-save")],
      projections: [makeProjection("proj-tool", { bindingIds: ["binding-graph"] })],
      projectionBindings: [makeBinding("binding-graph", bindingValue)],
    });

    const result = validateSurfaceInteractionPublication(publication);

    expect(result.valid).toBe(true);
    expect(result.publication).toBe(publication);
    expect(result.publication.projectionBindings[0]?.value).toBe(bindingValue);
    expect(invoke).not.toHaveBeenCalled();
  });

  it("treats relabeled publications as the same identity (labels never participate)", () => {
    const first = makePublication({ label: "Plan" });
    const second = makePublication({ label: "Renamed Plan" });
    expect(validateSurfaceInteractionPublication(first).valid).toBe(true);
    expect(validateSurfaceInteractionPublication(second).valid).toBe(true);
    expect(sameSurfaceInteractionIdentity(first.identity, second.identity)).toBe(true);
  });
});

describe("validateSurfaceInteractionPublication — identity and publication shape", () => {
  it("invalidates the whole publication on identity surface mismatch without invoking callbacks", () => {
    const invoke = vi.fn();
    const publication = makePublication({
      surfaceId: "build",
      identity: { surfaceId: "plan", instanceKey: '["plan","doc-1"]' },
      tools: [makeTool("tool-action", { activation: { kind: "command", invoke } })],
    });

    const result = validateSurfaceInteractionPublication(publication);

    expect(result.valid).toBe(false);
    expect(codesOf(result)).toContain("identity_surface_mismatch");
    expect(invoke).not.toHaveBeenCalled();
  });

  it("reports blank surface ID, blank instance key, and blank publication label", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        surfaceId: "  ",
        label: "",
        identity: { surfaceId: "  ", instanceKey: "" },
      }),
    );

    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(
      expect.arrayContaining(["surface_id_blank", "instance_key_blank", "publication_label_blank"]),
    );
  });
});

describe("validateSurfaceInteractionPublication — duplicate identifiers", () => {
  it("reports duplicate tool IDs deterministically and never invokes either activation", () => {
    const firstInvoke = vi.fn();
    const secondInvoke = vi.fn();
    const publication = makePublication({
      tools: [
        makeTool("dup", { activation: { kind: "command", invoke: firstInvoke } }),
        makeTool("other"),
        makeTool("dup", { activation: { kind: "command", invoke: secondInvoke } }),
      ],
    });

    const first = validateSurfaceInteractionPublication(publication);
    const second = validateSurfaceInteractionPublication(publication);

    expect(first.valid).toBe(false);
    expect(codesOf(first)).toEqual(["duplicate_tool_id"]);
    expect(codesOf(second)).toEqual(codesOf(first));
    if (!first.valid) {
      expect(first.issues[0]).toMatchObject({ contributionId: "dup", contributionIndex: 0 });
    }
    expect(firstInvoke).not.toHaveBeenCalled();
    expect(secondInvoke).not.toHaveBeenCalled();
  });

  it("reports duplicate edit command, projection, and binding IDs", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        editCommands: [makeEditCommand("e"), makeEditCommand("e")],
        projections: [makeProjection("p"), makeProjection("p")],
        projectionBindings: [makeBinding("b"), makeBinding("b")],
      }),
    );

    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual([
      "duplicate_edit_command_id",
      "duplicate_projection_id",
      "duplicate_projection_binding_id",
    ]);
  });

  it("does not treat two blank IDs as duplicates", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({ tools: [makeTool(""), makeTool("")] }),
    );

    expect(codesOf(result)).toEqual(["contribution_id_blank", "contribution_id_blank"]);
  });
});

describe("validateSurfaceInteractionPublication — availability and placement", () => {
  it("rejects a disabled contribution with a missing or blank reason", () => {
    for (const disabledReason of [undefined, "   "]) {
      const availability = (
        disabledReason === undefined
          ? { status: "disabled" }
          : { status: "disabled", disabledReason }
      ) as SurfaceInteractionAvailability;
      const result = validateSurfaceInteractionPublication(
        makePublication({ tools: [makeTool("t", { availability })] }),
      );
      expect(codesOf(result)).toEqual(["disabled_reason_missing"]);
    }
  });

  it("rejects an enabled contribution carrying a disabled reason", () => {
    const availability = {
      status: "enabled",
      disabledReason: "stale reason",
    } as unknown as SurfaceInteractionAvailability;
    const result = validateSurfaceInteractionPublication(
      makePublication({ editCommands: [makeEditCommand("e", { availability })] }),
    );

    expect(codesOf(result)).toEqual(["enabled_has_disabled_reason"]);
  });

  it("rejects incoherent placement states", () => {
    const cases: SurfaceInteractionPlacement[] = [
      makePlacement({ groupId: null, groupLabel: "Tools" }),
      makePlacement({ groupId: "g1", groupLabel: null }),
      makePlacement({ groupId: "  ", groupLabel: "Tools" }),
      makePlacement({ groupId: "g1", groupLabel: "" }),
      makePlacement({ groupOrder: Number.NaN }),
      makePlacement({ itemOrder: Number.POSITIVE_INFINITY }),
      makePlacement({ groupOrder: 1.5 }),
    ];
    for (const placement of cases) {
      const result = validateSurfaceInteractionPublication(
        makePublication({ tools: [makeTool("t", { placement })] }),
      );
      expect(codesOf(result)).toEqual(["placement_invalid"]);
    }
  });

  it("accepts grouped and pinned coherent placements", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        tools: [
          makeTool("pinned"),
          makeTool("grouped", {
            placement: makePlacement({ groupId: "g1", groupLabel: "Tools", groupOrder: 1, itemOrder: 2 }),
          }),
        ],
      }),
    );
    expect(result.valid).toBe(true);
  });
});

describe("validateSurfaceInteractionPublication — tool/projection cross-references", () => {
  it("rejects a tool targeting a missing projection and never falls back to callbacks", () => {
    const elsewhereInvoke = vi.fn();
    const publication = makePublication({
      tools: [
        makeTool("tool-open", { activation: { kind: "projection", projectionId: "ghost" } }),
        makeTool("tool-command", { activation: { kind: "command", invoke: elsewhereInvoke } }),
      ],
      projections: [makeProjection("real-projection")],
    });

    const result = validateSurfaceInteractionPublication(publication);

    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["tool_projection_missing"]);
    if (!result.valid) {
      expect(result.issues[0]).toMatchObject({
        contributionId: "tool-open",
        referencedId: "ghost",
      });
    }
    expect(elsewhereInvoke).not.toHaveBeenCalled();
  });

  it("rejects a tool targeting a content projection", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        tools: [makeTool("tool-open", { activation: { kind: "projection", projectionId: "p" } })],
        projections: [makeProjection("p", { kind: "content" })],
      }),
    );

    expect(codesOf(result)).toEqual(["tool_projection_kind_mismatch"]);
  });

  it("rejects unknown projection kinds and sizes from untyped input without coercing", () => {
    const weird = makeProjection("p", {
      kind: "hologram",
      preferredSize: "huge",
    } as unknown as Partial<SurfaceInteractionProjectionDescriptor>);
    const result = validateSurfaceInteractionPublication(
      makePublication({ projections: [weird] }),
    );

    expect(codesOf(result)).toEqual(["projection_kind_unknown", "projection_size_unknown"]);
  });

  it("rejects a blank projection target as missing, never matching blank declarations", () => {
    const activation: SurfaceInteractionToolActivation = { kind: "projection", projectionId: "" };
    const result = validateSurfaceInteractionPublication(
      makePublication({
        tools: [makeTool("tool-open", { activation })],
        projections: [makeProjection("")],
      }),
    );

    expect(codesOf(result)).toEqual(
      expect.arrayContaining(["contribution_id_blank", "tool_projection_missing"]),
    );
  });
});

describe("validateSurfaceInteractionPublication — projection binding cross-references", () => {
  it("rejects a projection requiring an undeclared binding, with exact IDs in the issue", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        projections: [makeProjection("p", { bindingIds: ["graph"] })],
        projectionBindings: [makeBinding("other")],
      }),
    );

    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["projection_binding_missing"]);
    if (!result.valid) {
      expect(result.issues[0]).toMatchObject({ contributionId: "p", referencedId: "graph" });
    }
  });

  it("rejects a projection repeating the same binding reference", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        projections: [makeProjection("p", { bindingIds: ["b", "b"] })],
        projectionBindings: [makeBinding("b")],
      }),
    );

    expect(codesOf(result)).toEqual(["projection_binding_duplicate_reference"]);
  });

  it("never inspects binding values while validating references", () => {
    const explosive = new Proxy(
      {},
      {
        get() {
          throw new Error("binding value must not be read");
        },
      },
    );
    const result = validateSurfaceInteractionPublication(
      makePublication({
        projections: [makeProjection("p", { bindingIds: ["b"] })],
        projectionBindings: [makeBinding("b", explosive)],
      }),
    );

    expect(result.valid).toBe(true);
  });
});

describe("validateSurfaceInteractionPublication — canvas, agent context, edit commands", () => {
  it("rejects blank canvas identity fields", () => {
    const cases = [
      { canvasId: " ", workObject: { kind: "document", id: "doc-1" } },
      { canvasId: "c1", workObject: { kind: "", id: "doc-1" } },
      { canvasId: "c1", workObject: { kind: "document", id: " " } },
    ];
    for (const canvas of cases) {
      const result = validateSurfaceInteractionPublication(makePublication({ canvas }));
      expect(codesOf(result)).toEqual(["canvas_identity_invalid"]);
    }
  });

  it("rejects invalid agent-context scalar shape and blank pointers", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        agentContext: {
          label: " ",
          campaignId: 7 as unknown as string,
          documentId: null,
          sessionNumber: Number.NaN,
          ambientSummary: null,
          pointers: [{ kind: "", value: "doc-1" }],
        },
      }),
    );

    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["agent_context_invalid", "agent_pointer_invalid"]);
  });

  it("accepts a minimal agent context with all-null optional fields", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        agentContext: {
          label: "Context",
          campaignId: null,
          documentId: null,
          sessionNumber: null,
          ambientSummary: null,
          pointers: [],
        },
      }),
    );
    expect(result.valid).toBe(true);
  });

  it("rejects edit commands with blank targets or a missing invoke callback", () => {
    const blankTarget = validateSurfaceInteractionPublication(
      makePublication({
        editCommands: [makeEditCommand("e", { target: { kind: "document", id: "" } })],
      }),
    );
    expect(codesOf(blankTarget)).toEqual(["command_target_invalid"]);

    const missingInvoke = validateSurfaceInteractionPublication(
      makePublication({
        editCommands: [
          makeEditCommand("e", { invoke: undefined } as unknown as Partial<SurfaceInteractionEditCommandContribution>),
        ],
      }),
    );
    expect(codesOf(missingInvoke)).toEqual(["edit_command_invoke_invalid"]);
  });

  it("rejects tool command activations missing their invoke callback", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        tools: [
          makeTool("t", {
            activation: { kind: "command" } as unknown as SurfaceInteractionToolActivation,
          }),
        ],
      }),
    );
    expect(codesOf(result)).toEqual(["tool_activation_invalid"]);
  });

  it("rejects unknown tool activation discriminants", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        tools: [
          makeTool("t", {
            activation: { kind: "teleport" } as unknown as SurfaceInteractionToolActivation,
          }),
        ],
      }),
    );
    expect(codesOf(result)).toEqual(["tool_activation_invalid"]);
  });
});

describe("validateSurfaceInteractionPublication — purity and determinism", () => {
  it("validates a deeply frozen publication twice with equivalent results and no side effects", () => {
    const invoke = vi.fn();
    const bindingValue = { nested: { opaque: true } };
    const publication = deepFreeze(
      makePublication({
        tools: [
          makeTool("tool-open", { activation: { kind: "projection", projectionId: "p" } }),
          makeTool("tool-command", { activation: { kind: "command", invoke } }),
        ],
        editCommands: [makeEditCommand("e", { invoke })],
        projections: [makeProjection("p", { bindingIds: ["b"] })],
        projectionBindings: [makeBinding("b", bindingValue)],
      }),
    );

    const first = validateSurfaceInteractionPublication(publication);
    const second = validateSurfaceInteractionPublication(publication);

    expect(first.valid).toBe(true);
    expect(second).toEqual(first);
    expect(first.publication).toBe(publication);
    expect(first.publication.projectionBindings[0]?.value).toBe(bindingValue);
    expect(invoke).not.toHaveBeenCalled();
  });

  it("returns deeply equivalent issue arrays for repeated validation of the same input", () => {
    const publication = makePublication({
      surfaceId: "build",
      tools: [makeTool("dup"), makeTool("dup"), makeTool("t", {
        activation: { kind: "projection", projectionId: "ghost" },
      })],
    });

    const first = validateSurfaceInteractionPublication(publication);
    const second = validateSurfaceInteractionPublication(publication);

    expect(first.valid).toBe(false);
    expect(second).toEqual(first);
  });
});

describe("validateSurfaceInteractionPublication — whole-publication accumulation", () => {
  it("accumulates independent contradictions in one pass without enabling partial state", () => {
    const commandSpy = vi.fn();
    const editSpy = vi.fn();
    const publication = makePublication({
      surfaceId: "build",
      identity: { surfaceId: "plan", instanceKey: '["plan","doc-1"]' },
      tools: [
        makeTool("dup", { activation: { kind: "command", invoke: commandSpy } }),
        makeTool("dup"),
        makeTool("tool-open", { activation: { kind: "projection", projectionId: "ghost" } }),
      ],
      editCommands: [makeEditCommand("e", { invoke: editSpy })],
    });

    const result = validateSurfaceInteractionPublication(publication);

    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual([
      "identity_surface_mismatch",
      "duplicate_tool_id",
      "tool_projection_missing",
    ]);
    expect(commandSpy).not.toHaveBeenCalled();
    expect(editSpy).not.toHaveBeenCalled();
  });

  it("documents the deterministic issue order across every boundary", () => {
    const publication = makePublication({
      surfaceId: "",
      label: "",
      identity: { surfaceId: "plan", instanceKey: " " },
      canvas: { canvasId: "", workObject: { kind: "document", id: "doc-1" } },
      agentContext: {
        label: "",
        campaignId: null,
        documentId: null,
        sessionNumber: null,
        ambientSummary: null,
        pointers: [{ kind: "", value: "v" }],
      },
      tools: [
        makeTool(""),
        makeTool("t1", {
          placement: makePlacement({ groupId: null, groupLabel: "Tools" }),
          availability: {
            status: "enabled",
            disabledReason: "stale",
          } as unknown as SurfaceInteractionAvailability,
          activation: { kind: "teleport" } as unknown as SurfaceInteractionToolActivation,
        }),
        makeTool("t1"),
        makeTool("t2", { activation: { kind: "projection", projectionId: "ghost" } }),
      ],
      editCommands: [
        makeEditCommand("e1", {
          target: { kind: "", id: "" },
          invoke: undefined,
        } as unknown as Partial<SurfaceInteractionEditCommandContribution>),
      ],
      projections: [
        makeProjection("p1", {
          kind: "hologram",
          preferredSize: "huge",
          bindingIds: ["b1", "b1", "b2"],
        } as unknown as Partial<SurfaceInteractionProjectionDescriptor>),
      ],
      projectionBindings: [makeBinding("b1")],
    });

    const result = validateSurfaceInteractionPublication(publication);

    expect(result.valid).toBe(false);
    const expectedOrder: SurfaceInteractionValidationIssueCode[] = [
      "surface_id_blank",
      "instance_key_blank",
      "identity_surface_mismatch",
      "publication_label_blank",
      "canvas_identity_invalid",
      "agent_context_invalid",
      "agent_pointer_invalid",
      "contribution_id_blank",
      "placement_invalid",
      "enabled_has_disabled_reason",
      "tool_activation_invalid",
      "duplicate_tool_id",
      "command_target_invalid",
      "edit_command_invoke_invalid",
      "projection_kind_unknown",
      "projection_size_unknown",
      "tool_projection_missing",
      "projection_binding_duplicate_reference",
      "projection_binding_missing",
    ];
    expect(codesOf(result)).toEqual(expectedOrder);
  });
});
