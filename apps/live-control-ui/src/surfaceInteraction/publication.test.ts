import { describe, expect, it, vi } from "vitest";

import {
  SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS,
  validateSurfaceInteractionPublication,
} from "./publication";
import { buildSurfaceInteractionIdentity } from "./surfaceIdentity";
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
    const publication = makePublication();
    const result = validateSurfaceInteractionPublication(publication);
    expect(result).toEqual({ valid: true, publication });
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
    if (result.valid) {
      // Canonical validated snapshot: deeply equal to the proven contract
      // fields, but re-materialized — no record or array aliases the input.
      expect(result.publication).not.toBe(publication);
      expect(result.publication).toEqual(publication);
      expect(result.publication.tools).not.toBe(publication.tools);
      expect(result.publication.tools[0]).not.toBe(publication.tools[0]);
      // Callback and binding-value identities are preserved by reference.
      expect(result.publication.projectionBindings[0]?.value).toBe(bindingValue);
      const commandActivation = result.publication.tools[1]?.activation;
      expect(
        commandActivation?.kind === "command" && commandActivation.invoke === invoke,
      ).toBe(true);
    }
    expect(invoke).not.toHaveBeenCalled();
  });

  it("treats relabeled publications as the same identity (labels never participate)", () => {
    const first = makePublication({ label: "Plan" });
    const second = makePublication({ label: "Renamed Plan" });
    expect(validateSurfaceInteractionPublication(first).valid).toBe(true);
    expect(validateSurfaceInteractionPublication(second).valid).toBe(true);
    expect(buildSurfaceInteractionIdentity({
      surfaceId: "plan",
      instanceParts: ["plan", "doc-1"],
    }).instanceKey).toBe(first.identity.instanceKey);
    expect(sameIdentity(first, second)).toBe(true);
  });
});

function sameIdentity(a: SurfaceInteractionPublication, b: SurfaceInteractionPublication): boolean {
  return a.identity.surfaceId === b.identity.surfaceId && a.identity.instanceKey === b.identity.instanceKey;
}

describe("validateSurfaceInteractionPublication — V13 untyped shape matrix", () => {
  const junkInputs: unknown[] = [
    "not-a-publication",
    null,
    undefined,
    [],
    42,
  ];

  it.each(junkInputs)("rejects %p with publication_shape_invalid without throwing", (junk) => {
    expect(() => validateSurfaceInteractionPublication(junk)).not.toThrow();
    const result = validateSurfaceInteractionPublication(junk);
    expect(result.valid).toBe(false);
    if (!result.valid) {
      expect(result.publication).toBe(junk);
      expect(codesOf(result)).toEqual(["publication_shape_invalid"]);
    }
  });

  it("rejects tools: {} as publication_shape_invalid — never coerces to empty array", () => {
    const junk = makePublication({ tools: {} as unknown as SurfaceInteractionToolContribution[] });
    expect(() => validateSurfaceInteractionPublication(junk)).not.toThrow();
    const result = validateSurfaceInteractionPublication(junk);
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toContain("publication_shape_invalid");
  });

  it("accepts an empty tools array on an otherwise valid publication", () => {
    const publication = makePublication({ tools: [] });
    expect(validateSurfaceInteractionPublication(publication).valid).toBe(true);
  });

  it("rejects each non-array collection independently", () => {
    for (const field of ["editCommands", "projections", "projectionBindings"] as const) {
      const junk = makePublication({ [field]: {} as never });
      const result = validateSurfaceInteractionPublication(junk);
      expect(result.valid).toBe(false);
      expect(codesOf(result)).toContain("publication_shape_invalid");
    }
  });

  it("rejects non-object collection entries and missing nested objects", () => {
    const publication = makePublication({
      tools: [null as unknown as SurfaceInteractionToolContribution, makeTool("ok")],
      editCommands: [
        {
          id: "e1",
          label: "Edit",
          placement: makePlacement(),
          availability: ENABLED,
          target: null,
          invoke: () => {},
        } as unknown as SurfaceInteractionEditCommandContribution,
      ],
      projections: [makeProjection("p1", { bindingIds: "not-array" as unknown as string[] })],
      projectionBindings: ["string-entry" as unknown as SurfaceInteractionProjectionBinding],
      canvas: { canvasId: "c1", workObject: null as unknown as { kind: string; id: string } },
      agentContext: {
        label: "Ctx",
        campaignId: null,
        documentId: null,
        sessionNumber: null,
        ambientSummary: null,
        pointers: [null as unknown as { kind: string; value: string }],
      },
      identity: null as unknown as SurfaceInteractionPublication["identity"],
    });

    expect(() => validateSurfaceInteractionPublication(publication)).not.toThrow();
    const result = validateSurfaceInteractionPublication(publication);
    expect(result.valid).toBe(false);
    expect(codesOf(result).every((code) => code === "contribution_shape_invalid")).toBe(true);
    expect(codesOf(result).length).toBeGreaterThanOrEqual(5);
  });

  it("accumulates field issues for shape-valid entries alongside shape-invalid ones", () => {
    const publication = makePublication({
      tools: [
        null as unknown as SurfaceInteractionToolContribution,
        makeTool("good-tool"),
        makeTool("", { label: "" }),
      ],
    });
    const result = validateSurfaceInteractionPublication(publication);
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(
      expect.arrayContaining([
        "contribution_shape_invalid",
        "contribution_id_blank",
        "contribution_label_blank",
      ]),
    );
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
    if (!result.valid) expect(result.publication).toBe(publication);
    expect(codesOf(result)).toContain("identity_surface_mismatch");
    expect(invoke).not.toHaveBeenCalled();
  });

  it("reports blank surface ID, blank instance key, and blank publication label", () => {
    const publication = makePublication({
      surfaceId: "  ",
      label: "",
      identity: { surfaceId: "  ", instanceKey: "" },
    });
    const result = validateSurfaceInteractionPublication(publication);

    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(
      expect.arrayContaining(["surface_id_blank", "instance_key_blank", "publication_label_blank"]),
    );
  });

  it("accumulates publication-field issues independently of malformed collections", () => {
    const publication = makePublication({
      tools: {} as unknown as SurfaceInteractionToolContribution[],
      surfaceId: "build",
      identity: { surfaceId: "plan", instanceKey: '["plan","doc-1"]' },
      label: "",
    });
    const result = validateSurfaceInteractionPublication(publication);
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(
      expect.arrayContaining([
        "publication_shape_invalid",
        "identity_surface_mismatch",
        "publication_label_blank",
      ]),
    );
  });
});

describe("validateSurfaceInteractionPublication — contribution_label_blank", () => {
  it("rejects blank Tool labels (empty and whitespace-only)", () => {
    for (const label of ["", "   "]) {
      const result = validateSurfaceInteractionPublication(
        makePublication({ tools: [makeTool("t1", { label })] }),
      );
      expect(codesOf(result)).toEqual(["contribution_label_blank"]);
    }
  });

  it("rejects blank Edit command labels (empty and whitespace-only)", () => {
    for (const label of ["", "  \t"]) {
      const result = validateSurfaceInteractionPublication(
        makePublication({ editCommands: [makeEditCommand("e1", { label })] }),
      );
      expect(codesOf(result)).toEqual(["contribution_label_blank"]);
    }
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

  it("rejects an enabled contribution supplying disabledReason at all — even null or undefined", () => {
    for (const disabledReason of [null, undefined]) {
      const availability = {
        status: "enabled",
        disabledReason,
      } as unknown as SurfaceInteractionAvailability;
      const result = validateSurfaceInteractionPublication(
        makePublication({ tools: [makeTool("t", { availability })] }),
      );
      expect(codesOf(result)).toEqual(["enabled_has_disabled_reason"]);
    }
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

describe("validateSurfaceInteractionPublication — placement_group_conflict", () => {
  it("rejects same groupId with different label across Tool and Edit (Tool canonical)", () => {
    const publication = makePublication({
      tools: [
        makeTool("a", {
          placement: makePlacement({ groupId: "graph", groupLabel: "Graph", groupOrder: 1, itemOrder: 0 }),
        }),
      ],
      editCommands: [
        makeEditCommand("b", {
          placement: makePlacement({ groupId: "graph", groupLabel: "World", groupOrder: 7, itemOrder: 0 }),
        }),
      ],
    });

    const result = validateSurfaceInteractionPublication(publication);
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["placement_group_conflict"]);
    if (!result.valid) {
      expect(result.issues[0]).toMatchObject({
        contributionId: "b",
        referencedId: "graph",
      });
      expect(result.issues[0]?.message).toContain("a");
    }
  });

  it("rejects same groupId with different order between two Tools", () => {
    const publication = makePublication({
      tools: [
        makeTool("first", {
          placement: makePlacement({ groupId: "g", groupLabel: "Group", groupOrder: 1, itemOrder: 0 }),
        }),
        makeTool("second", {
          placement: makePlacement({ groupId: "g", groupLabel: "Group", groupOrder: 2, itemOrder: 1 }),
        }),
      ],
    });
    const result = validateSurfaceInteractionPublication(publication);
    expect(codesOf(result)).toEqual(["placement_group_conflict"]);
    if (!result.valid) {
      expect(result.issues[0]).toMatchObject({ contributionId: "second", referencedId: "g" });
    }
  });

  it("produces two issues when two later entries conflict with the canonical declaration", () => {
    const publication = makePublication({
      tools: [
        makeTool("canonical", {
          placement: makePlacement({ groupId: "g", groupLabel: "G", groupOrder: 0, itemOrder: 0 }),
        }),
        makeTool("conflict-label", {
          placement: makePlacement({ groupId: "g", groupLabel: "Other", groupOrder: 0, itemOrder: 1 }),
        }),
        makeTool("conflict-order", {
          placement: makePlacement({ groupId: "g", groupLabel: "G", groupOrder: 9, itemOrder: 2 }),
        }),
      ],
    });
    const result = validateSurfaceInteractionPublication(publication);
    expect(codesOf(result)).toEqual(["placement_group_conflict", "placement_group_conflict"]);
  });

  it("never conflicts on null or blank groupId", () => {
    const publication = makePublication({
      tools: [
        makeTool("t1", { placement: makePlacement({ groupId: null, groupLabel: null }) }),
        makeTool("t2", { placement: makePlacement({ groupId: null, groupLabel: null }) }),
      ],
    });
    expect(validateSurfaceInteractionPublication(publication).valid).toBe(true);
  });

  it("does not produce group conflict for blank groupId even when labels differ", () => {
    const publication = makePublication({
      tools: [
        makeTool("t1", { placement: makePlacement({ groupId: "  ", groupLabel: "A" }) }),
        makeTool("t2", { placement: makePlacement({ groupId: "  ", groupLabel: "B" }) }),
      ],
    });
    const result = validateSurfaceInteractionPublication(publication);
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["placement_invalid", "placement_invalid"]);
    expect(codesOf(result)).not.toContain("placement_group_conflict");
  });

  it("does not participate entries with placement field failures in group conflict", () => {
    const publication = makePublication({
      tools: [
        makeTool("bad", { placement: makePlacement({ groupId: "g", groupLabel: null }) }),
        makeTool("also-bad", { placement: makePlacement({ groupId: "g", groupLabel: null, itemOrder: 1 }) }),
      ],
    });
    const result = validateSurfaceInteractionPublication(publication);
    expect(codesOf(result)).toEqual(["placement_invalid", "placement_invalid"]);
    expect(codesOf(result)).not.toContain("placement_group_conflict");
  });
});

describe("validateSurfaceInteractionPublication — agent_context_bounds_exceeded", () => {
  function agentContext(overrides: Partial<NonNullable<SurfaceInteractionPublication["agentContext"]>> = {}) {
    return {
      label: "Context",
      campaignId: null,
      documentId: null,
      sessionNumber: null,
      ambientSummary: null,
      pointers: [],
      ...overrides,
    };
  }

  it("rejects ambientSummary exceeding 500 characters", () => {
    const summary = "x".repeat(SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.ambientSummaryMaxChars + 1);
    const result = validateSurfaceInteractionPublication(
      makePublication({ agentContext: agentContext({ ambientSummary: summary }) }),
    );
    expect(codesOf(result)).toEqual(["agent_context_bounds_exceeded"]);
    if (!result.valid) {
      expect(result.issues[0]?.message).toContain("500");
    }
  });

  it("accepts ambientSummary at exactly 500 characters", () => {
    const summary = "x".repeat(SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.ambientSummaryMaxChars);
    expect(
      validateSurfaceInteractionPublication(
        makePublication({ agentContext: agentContext({ ambientSummary: summary }) }),
      ).valid,
    ).toBe(true);
  });

  it("rejects more than 16 pointers", () => {
    const pointers = Array.from({ length: SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointersMaxEntries + 1 }, (_, i) => ({
      kind: "k",
      value: `v${i}`,
    }));
    const result = validateSurfaceInteractionPublication(
      makePublication({ agentContext: agentContext({ pointers }) }),
    );
    expect(codesOf(result)).toEqual(["agent_context_bounds_exceeded"]);
    if (!result.valid) {
      expect(result.issues[0]?.message).toContain("16");
    }
  });

  it("accepts exactly 16 pointers", () => {
    const pointers = Array.from({ length: SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointersMaxEntries }, (_, i) => ({
      kind: "k",
      value: `v${i}`,
    }));
    expect(
      validateSurfaceInteractionPublication(
        makePublication({ agentContext: agentContext({ pointers }) }),
      ).valid,
    ).toBe(true);
  });

  it("rejects pointer kind exceeding 64 characters", () => {
    const kind = "k".repeat(SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointerKindMaxChars + 1);
    const result = validateSurfaceInteractionPublication(
      makePublication({ agentContext: agentContext({ pointers: [{ kind, value: "v" }] }) }),
    );
    expect(codesOf(result)).toEqual(["agent_context_bounds_exceeded"]);
    if (!result.valid) {
      expect(result.issues[0]?.message).toContain("64");
    }
  });

  it("accepts pointer kind at exactly 64 characters", () => {
    const kind = "k".repeat(SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointerKindMaxChars);
    expect(
      validateSurfaceInteractionPublication(
        makePublication({ agentContext: agentContext({ pointers: [{ kind, value: "v" }] }) }),
      ).valid,
    ).toBe(true);
  });

  it("rejects pointer value exceeding 256 characters", () => {
    const value = "v".repeat(SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointerValueMaxChars + 1);
    const result = validateSurfaceInteractionPublication(
      makePublication({ agentContext: agentContext({ pointers: [{ kind: "k", value }] }) }),
    );
    expect(codesOf(result)).toEqual(["agent_context_bounds_exceeded"]);
    if (!result.valid) {
      expect(result.issues[0]?.message).toContain("256");
    }
  });

  it("accepts pointer value at exactly 256 characters", () => {
    const value = "v".repeat(SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.pointerValueMaxChars);
    expect(
      validateSurfaceInteractionPublication(
        makePublication({ agentContext: agentContext({ pointers: [{ kind: "k", value }] }) }),
      ).valid,
    ).toBe(true);
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

  it("rejects a projection binding missing its required value field", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        projections: [makeProjection("p", { bindingIds: ["b"] })],
        projectionBindings: [{ id: "b" } as unknown as SurfaceInteractionProjectionBinding],
      }),
    );

    expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
    if (!result.valid) {
      expect(result.issues[0]).toMatchObject({ contributionId: "b", contributionIndex: 0 });
    }
  });

  it("accepts a binding whose value is explicitly undefined — presence is required, the value stays opaque", () => {
    const binding: Record<string, unknown> = { id: "b" };
    binding.value = undefined;
    const result = validateSurfaceInteractionPublication(
      makePublication({
        projections: [makeProjection("p", { bindingIds: ["b"] })],
        projectionBindings: [binding as SurfaceInteractionProjectionBinding],
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

  it("accumulates agent-context field and bounds issues when one pointer entry is shape-invalid", () => {
    const summary = "x".repeat(SURFACE_INTERACTION_AGENT_CONTEXT_BOUNDS.ambientSummaryMaxChars + 1);
    const result = validateSurfaceInteractionPublication(
      makePublication({
        agentContext: {
          label: " ",
          campaignId: null,
          documentId: null,
          sessionNumber: null,
          ambientSummary: summary,
          pointers: [null as unknown as { kind: string; value: string }],
        },
      }),
    );
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(
      expect.arrayContaining([
        "contribution_shape_invalid",
        "agent_context_invalid",
        "agent_context_bounds_exceeded",
      ]),
    );
  });

  it("reports agent_pointer_invalid at the original pointers-array index", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        agentContext: {
          label: "Context",
          campaignId: null,
          documentId: null,
          sessionNumber: null,
          ambientSummary: null,
          pointers: [
            null as unknown as { kind: string; value: string },
            { kind: "", value: "v" },
          ],
        },
      }),
    );
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["contribution_shape_invalid", "agent_pointer_invalid"]);
    if (!result.valid) {
      const pointerIssue = result.issues.find((issue) => issue.code === "agent_pointer_invalid");
      expect(pointerIssue).toMatchObject({ contributionIndex: 1 });
      const shapeIssue = result.issues.find((issue) => issue.code === "contribution_shape_invalid");
      expect(shapeIssue).toMatchObject({ contributionIndex: 0 });
    }
  });

  it("rejects agent context missing the sessionNumber key", () => {
    const agentContext = {
      label: "Context",
      campaignId: null,
      documentId: null,
      ambientSummary: null,
      pointers: [],
    };
    const result = validateSurfaceInteractionPublication(makePublication({ agentContext }));
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["agent_context_invalid"]);
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
    if (first.valid) {
      // Canonical snapshot: deeply equal to the proven input, sharing only
      // callback and binding-value references — never record/array identity.
      expect(first.publication).not.toBe(publication);
      expect(first.publication).toEqual(publication);
      expect(first.publication.projectionBindings[0]?.value).toBe(bindingValue);
      const commandActivation = first.publication.tools[1]?.activation;
      expect(
        commandActivation?.kind === "command" && commandActivation.invoke === invoke,
      ).toBe(true);
      expect(first.publication.editCommands[0]?.invoke).toBe(invoke);
    }
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
        makeTool("", { label: "" }),
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
      "contribution_label_blank",
      "placement_invalid",
      "enabled_has_disabled_reason",
      "tool_activation_invalid",
      "command_target_invalid",
      "edit_command_invoke_invalid",
      "projection_kind_unknown",
      "projection_size_unknown",
      "duplicate_tool_id",
      "tool_projection_missing",
      "projection_binding_duplicate_reference",
      "projection_binding_missing",
    ];
    expect(codesOf(result)).toEqual(expectedOrder);
  });
});

describe("validateSurfaceInteractionPublication — exact nullability", () => {
  it("rejects undefined canvas and agentContext — undefined is not null", () => {
    const withUndefinedCanvas = validateSurfaceInteractionPublication(
      makePublication({ canvas: undefined as unknown as null }),
    );
    expect(codesOf(withUndefinedCanvas)).toEqual(["publication_shape_invalid"]);

    const withUndefinedAgentContext = validateSurfaceInteractionPublication(
      makePublication({ agentContext: undefined as unknown as null }),
    );
    expect(codesOf(withUndefinedAgentContext)).toEqual(["publication_shape_invalid"]);
  });

  it("rejects a missing canvas key", () => {
    const publication = makePublication();
    delete (publication as Record<string, unknown>).canvas;
    expect(codesOf(validateSurfaceInteractionPublication(publication))).toEqual([
      "publication_shape_invalid",
    ]);
  });

  it("rejects undefined placement group fields", () => {
    const undefinedGroupId = validateSurfaceInteractionPublication(
      makePublication({
        tools: [
          makeTool("t", {
            placement: makePlacement({ groupId: undefined as unknown as null, groupLabel: null }),
          }),
        ],
      }),
    );
    expect(codesOf(undefinedGroupId)).toEqual(["placement_invalid"]);

    const undefinedGroupLabel = validateSurfaceInteractionPublication(
      makePublication({
        tools: [
          makeTool("t", {
            placement: makePlacement({
              groupId: "g",
              groupLabel: undefined as unknown as null,
              groupOrder: 1,
            }),
          }),
        ],
      }),
    );
    expect(codesOf(undefinedGroupLabel)).toEqual(["placement_invalid"]);
  });
});

describe("validateSurfaceInteractionPublication — availability discriminant and eyebrow shape", () => {
  it("rejects availability objects with unrecognized status discriminants", () => {
    for (const availability of [{}, { status: "maybe" }, { status: null }, { status: 1 }]) {
      const result = validateSurfaceInteractionPublication(
        makePublication({
          tools: [
            makeTool("t", { availability: availability as unknown as SurfaceInteractionAvailability }),
          ],
        }),
      );
      expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
    }
  });

  it("rejects unrecognized Edit availability discriminants", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        editCommands: [
          makeEditCommand("e", {
            availability: { status: "maybe" } as unknown as SurfaceInteractionAvailability,
          }),
        ],
      }),
    );
    expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
  });

  it("rejects supplied non-string eyebrows and accepts absent or string eyebrows", () => {
    for (const eyebrow of [42, {}, null]) {
      const result = validateSurfaceInteractionPublication(
        makePublication({ tools: [makeTool("t", { eyebrow: eyebrow as unknown as string })] }),
      );
      expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
    }
    expect(validateSurfaceInteractionPublication(makePublication({ tools: [makeTool("t")] })).valid).toBe(true);
    expect(
      validateSurfaceInteractionPublication(
        makePublication({ tools: [makeTool("t", { eyebrow: "Group" })] }),
      ).valid,
    ).toBe(true);
  });
});

describe("validateSurfaceInteractionPublication — no conversion of untrusted values", () => {
  it("rejects boxed projection discriminants instead of accepting them via coercion", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        projections: [
          makeProjection("p", {
            kind: new String("tool") as unknown as "tool",
            preferredSize: new String("compact") as unknown as "compact",
          }),
        ],
      }),
    );
    expect(codesOf(result)).toEqual(["projection_kind_unknown", "projection_size_unknown"]);
  });

  it("never invokes toString/Symbol.toPrimitive on projection discriminants", () => {
    const nullProto = Object.create(null) as unknown as "tool";
    const throwing = {
      toString() {
        throw new Error("must not be called");
      },
      [Symbol.toPrimitive]() {
        throw new Error("must not be called");
      },
    } as unknown as "tool";

    for (const kind of [nullProto, throwing]) {
      let result: ReturnType<typeof validateSurfaceInteractionPublication> | undefined;
      expect(() => {
        result = validateSurfaceInteractionPublication(
          makePublication({ projections: [makeProjection("p", { kind })] }),
        );
      }).not.toThrow();
      expect(result?.valid).toBe(false);
      expect(codesOf(result as NonNullable<typeof result>)).toEqual(["projection_kind_unknown"]);
    }
  });

  it("never converts untrusted contribution IDs or binding reference elements", () => {
    const throwing = {
      toString() {
        throw new Error("must not be called");
      },
      [Symbol.toPrimitive]() {
        throw new Error("must not be called");
      },
    } as unknown as string;

    let result: ReturnType<typeof validateSurfaceInteractionPublication> | undefined;
    expect(() => {
      result = validateSurfaceInteractionPublication(
        makePublication({
          tools: [makeTool("a", { id: throwing }), makeTool("a")],
          projections: [makeProjection("p", { bindingIds: [throwing] })],
          projectionBindings: [makeBinding("b")],
        }),
      );
    }).not.toThrow();
    expect(result?.valid).toBe(false);
    expect(codesOf(result as NonNullable<typeof result>)).toEqual(
      expect.arrayContaining(["contribution_id_blank", "contribution_shape_invalid"]),
    );
  });
});

describe("validateSurfaceInteractionPublication — sparse arrays fail closed", () => {
  it("rejects a sparse tools collection at the hole index", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({ tools: new Array(1) as unknown as SurfaceInteractionToolContribution[] }),
    );
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
    if (!result.valid) {
      expect(result.issues[0]).toMatchObject({ contributionIndex: 0 });
    }
  });

  it("rejects holes in every collection at each hole index", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        tools: new Array(1) as unknown as SurfaceInteractionToolContribution[],
        editCommands: new Array(2) as unknown as SurfaceInteractionEditCommandContribution[],
        projections: new Array(1) as unknown as SurfaceInteractionProjectionDescriptor[],
        projectionBindings: new Array(3) as unknown as SurfaceInteractionProjectionBinding[],
      }),
    );
    expect(codesOf(result)).toEqual([
      "contribution_shape_invalid",
      "contribution_shape_invalid",
      "contribution_shape_invalid",
      "contribution_shape_invalid",
      "contribution_shape_invalid",
      "contribution_shape_invalid",
      "contribution_shape_invalid",
    ]);
  });

  it("rejects sparse Agent-context pointers", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        agentContext: {
          label: "Ctx",
          campaignId: null,
          documentId: null,
          sessionNumber: null,
          ambientSummary: null,
          pointers: new Array(2) as unknown as { kind: string; value: string }[],
        },
      }),
    );
    expect(codesOf(result)).toEqual(["contribution_shape_invalid", "contribution_shape_invalid"]);
  });

  it("rejects sparse Projection bindingIds", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({
        projections: [
          makeProjection("p", { bindingIds: new Array(1) as unknown as string[] }),
        ],
      }),
    );
    expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
  });

  it("still validates present entries around holes", () => {
    const tools = [makeTool("", { label: "" }), , makeTool("ok")] as unknown as SurfaceInteractionToolContribution[];
    const result = validateSurfaceInteractionPublication(makePublication({ tools }));
    expect(codesOf(result)).toEqual([
      "contribution_shape_invalid",
      "contribution_id_blank",
      "contribution_label_blank",
    ]);
  });
});

describe("validateSurfaceInteractionPublication — identity surface ID blankness", () => {
  it("reports surface_id_blank for a blank identity surface ID alongside the mismatch", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({ identity: { surfaceId: "", instanceKey: "valid" } }),
    );
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["surface_id_blank", "identity_surface_mismatch"]);
  });

  it("reports surface_id_blank once per blank field", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({ surfaceId: "", identity: { surfaceId: "  ", instanceKey: "k" } }),
    );
    const codes = codesOf(result);
    expect(codes.filter((code) => code === "surface_id_blank")).toHaveLength(2);
  });
});

describe("validateSurfaceInteractionPublication — data-record boundary", () => {
  it("never invokes a throwing getter on a publication collection field and fails closed", () => {
    const publication = makePublication();
    let invoked = 0;
    Object.defineProperty(publication, "tools", {
      get() {
        invoked += 1;
        throw new Error("boom");
      },
    });

    let result: ReturnType<typeof validateSurfaceInteractionPublication> | undefined;
    expect(() => {
      result = validateSurfaceInteractionPublication(publication);
    }).not.toThrow();

    expect(invoked).toBe(0);
    expect(result?.valid).toBe(false);
    const resolved = result as NonNullable<typeof result>;
    if (!resolved.valid) {
      expect(resolved.publication).toBe(publication);
      expect(codesOf(resolved)).toContain("publication_shape_invalid");
    }
  });

  it("rejects accessor canvas/agentContext fields at the publication level without invoking them", () => {
    for (const field of ["canvas", "agentContext"] as const) {
      const publication = makePublication();
      let invoked = 0;
      Object.defineProperty(publication, field, {
        get() {
          invoked += 1;
          throw new Error("boom");
        },
      });
      let result: ReturnType<typeof validateSurfaceInteractionPublication> | undefined;
      expect(() => {
        result = validateSurfaceInteractionPublication(publication);
      }).not.toThrow();
      expect(invoked).toBe(0);
      expect(result?.valid).toBe(false);
      expect(codesOf(result as NonNullable<typeof result>)).toContain("publication_shape_invalid");
    }
  });

  it("rejects accessor fields on contribution entries without invoking them", () => {
    const tool = makeTool("t");
    let invoked = 0;
    Object.defineProperty(tool, "placement", {
      get() {
        invoked += 1;
        throw new Error("boom");
      },
    });
    const result = validateSurfaceInteractionPublication(makePublication({ tools: [tool] }));
    expect(invoked).toBe(0);
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
  });

  it("rejects an accessor availability status discriminant without invoking it", () => {
    const availability: Record<string, unknown> = { status: "enabled" };
    let invoked = 0;
    Object.defineProperty(availability, "status", {
      get() {
        invoked += 1;
        throw new Error("boom");
      },
    });
    const result = validateSurfaceInteractionPublication(
      makePublication({
        tools: [
          makeTool("t", {
            availability: availability as unknown as SurfaceInteractionAvailability,
          }),
        ],
      }),
    );
    expect(invoked).toBe(0);
    expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
  });

  it("rejects an enabled availability whose disabledReason is inherited from the prototype", () => {
    const availability = Object.assign(Object.create({ disabledReason: "inherited" }), {
      status: "enabled",
    }) as unknown as SurfaceInteractionAvailability;
    const result = validateSurfaceInteractionPublication(
      makePublication({ tools: [makeTool("t", { availability })] }),
    );
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
  });

  it("rejects contribution records with non-standard prototypes even when own fields look complete", () => {
    class ToolRecord {}
    const tool = Object.assign(new ToolRecord(), makeTool("t"));
    const result = validateSurfaceInteractionPublication(makePublication({ tools: [tool] }));
    expect(result.valid).toBe(false);
    expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
  });

  it("rejects a publication record with a non-standard prototype", () => {
    class PublicationRecord {}
    const publication = Object.assign(new PublicationRecord(), makePublication());
    const result = validateSurfaceInteractionPublication(publication);
    expect(codesOf(result)).toEqual(["publication_shape_invalid"]);
  });

  it("accepts null-prototype records as plain data records", () => {
    const publication = Object.assign(Object.create(null), makePublication());
    expect(validateSurfaceInteractionPublication(publication).valid).toBe(true);

    const tool = Object.assign(Object.create(null), makeTool("t"));
    expect(
      validateSurfaceInteractionPublication(makePublication({ tools: [tool] })).valid,
    ).toBe(true);
  });

  it("guards throwing proxy traps into shape issues instead of propagating them", () => {
    const descriptorBomb = new Proxy(makePublication(), {
      getOwnPropertyDescriptor() {
        throw new Error("trap must be guarded");
      },
    });
    let result: ReturnType<typeof validateSurfaceInteractionPublication> | undefined;
    expect(() => {
      result = validateSurfaceInteractionPublication(descriptorBomb);
    }).not.toThrow();
    expect(result?.valid).toBe(false);
    expect(
      codesOf(result as NonNullable<typeof result>).every(
        (code) => code === "publication_shape_invalid",
      ),
    ).toBe(true);

    const prototypeBomb = new Proxy(makePublication(), {
      getPrototypeOf() {
        throw new Error("trap must be guarded");
      },
    });
    expect(() => {
      result = validateSurfaceInteractionPublication(prototypeBomb);
    }).not.toThrow();
    expect(result?.valid).toBe(false);
    expect(codesOf(result as NonNullable<typeof result>)).toEqual(["publication_shape_invalid"]);
  });

  it("rejects a revoked proxy publication without throwing", () => {
    const { proxy, revoke } = Proxy.revocable(makePublication(), {});
    revoke();
    let result: ReturnType<typeof validateSurfaceInteractionPublication> | undefined;
    expect(() => {
      result = validateSurfaceInteractionPublication(proxy);
    }).not.toThrow();
    expect(result?.valid).toBe(false);
    expect(codesOf(result as NonNullable<typeof result>)).toEqual(["publication_shape_invalid"]);
  });

  it("rejects accessor elements in collections without invoking them", () => {
    const tools = [makeTool("t")];
    let invoked = 0;
    Object.defineProperty(tools, "0", {
      get() {
        invoked += 1;
        throw new Error("boom");
      },
    });
    const result = validateSurfaceInteractionPublication(makePublication({ tools }));
    expect(invoked).toBe(0);
    expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
    if (!result.valid) {
      expect(result.issues[0]).toMatchObject({ contributionIndex: 0 });
    }
  });

  it("rejects accessor elements in bindingIds and pointers arrays", () => {
    const bindingIds = ["b"];
    Object.defineProperty(bindingIds, "0", {
      get() {
        throw new Error("boom");
      },
    });
    const withBindingIds = validateSurfaceInteractionPublication(
      makePublication({
        projections: [makeProjection("p", { bindingIds })],
        projectionBindings: [makeBinding("b")],
      }),
    );
    expect(codesOf(withBindingIds)).toEqual(["contribution_shape_invalid"]);

    const pointers = [{ kind: "document", value: "doc-1" }];
    Object.defineProperty(pointers, "0", {
      get() {
        throw new Error("boom");
      },
    });
    const withPointers = validateSurfaceInteractionPublication(
      makePublication({
        agentContext: {
          label: "Ctx",
          campaignId: null,
          documentId: null,
          sessionNumber: null,
          ambientSummary: null,
          pointers,
        },
      }),
    );
    expect(codesOf(withPointers)).toEqual(["contribution_shape_invalid"]);
  });

  it("rejects a binding whose value is an accessor — presence must be an own data property", () => {
    const binding: Record<string, unknown> = { id: "b" };
    let invoked = 0;
    Object.defineProperty(binding, "value", {
      get() {
        invoked += 1;
        return {};
      },
    });
    const result = validateSurfaceInteractionPublication(
      makePublication({
        projections: [makeProjection("p", { bindingIds: ["b"] })],
        projectionBindings: [binding as SurfaceInteractionProjectionBinding],
      }),
    );
    expect(invoked).toBe(0);
    expect(codesOf(result)).toEqual(["contribution_shape_invalid"]);
  });

  it("rejects an identity record with accessor fields without throwing", () => {
    const publication = makePublication();
    Object.defineProperty(publication.identity, "surfaceId", {
      get() {
        throw new Error("boom");
      },
    });
    let result: ReturnType<typeof validateSurfaceInteractionPublication> | undefined;
    expect(() => {
      result = validateSurfaceInteractionPublication(publication);
    }).not.toThrow();
    expect(result?.valid).toBe(false);
    expect(codesOf(result as NonNullable<typeof result>)).toEqual(["contribution_shape_invalid"]);
  });

  it("treats an unreadable collection length as a shape failure without throwing", () => {
    const tools = new Proxy([makeTool("t")], {
      get(target, property) {
        if (property === "length") throw new Error("length trap must be guarded");
        return Reflect.get(target, property);
      },
    });
    let result: ReturnType<typeof validateSurfaceInteractionPublication> | undefined;
    expect(() => {
      result = validateSurfaceInteractionPublication(makePublication({ tools }));
    }).not.toThrow();
    expect(result?.valid).toBe(false);
    expect(codesOf(result as NonNullable<typeof result>)).toEqual(["publication_shape_invalid"]);
  });

  it("still accumulates independent field issues alongside accessor-malformed entries", () => {
    const badTool = makeTool("bad");
    Object.defineProperty(badTool, "availability", {
      get() {
        throw new Error("boom");
      },
    });
    const result = validateSurfaceInteractionPublication(
      makePublication({ tools: [badTool, makeTool("", { label: "" })] }),
    );
    expect(codesOf(result)).toEqual([
      "contribution_shape_invalid",
      "contribution_id_blank",
      "contribution_label_blank",
    ]);
  });
});

describe("validateSurfaceInteractionPublication — canonical validated snapshot", () => {
  it("returns proven values even when a proxy's property access disagrees with its descriptors", () => {
    const target = makePublication({ tools: [makeTool("t")] });
    const proxy = new Proxy(target, {
      get(object, key, receiver) {
        if (key === "tools") return "not-an-array";
        return Reflect.get(object, key, receiver);
      },
    });

    const result = validateSurfaceInteractionPublication(proxy);

    expect(result.valid).toBe(true);
    if (result.valid) {
      // The descriptor-proven values are what the narrowed publication
      // observes — the proxy's hostile get trap is never consulted.
      expect(result.publication).not.toBe(proxy);
      expect(result.publication).not.toBe(target);
      expect(Array.isArray(result.publication.tools)).toBe(true);
      expect(result.publication.tools).toHaveLength(1);
      expect(result.publication.tools[0]?.id).toBe("t");
    }
  });

  it("carries each position's own proven values when one record is aliased across positions", () => {
    let itemOrderReads = 0;
    const aliased = new Proxy(makePlacement(), {
      getOwnPropertyDescriptor(object, key) {
        const descriptor = Reflect.getOwnPropertyDescriptor(object, key);
        if (key === "itemOrder" && descriptor && "value" in descriptor) {
          itemOrderReads += 1;
          return { ...descriptor, value: itemOrderReads };
        }
        return descriptor;
      },
    });

    const result = validateSurfaceInteractionPublication(
      makePublication({
        tools: [makeTool("a", { placement: aliased }), makeTool("b", { placement: aliased })],
      }),
    );

    expect(result.valid).toBe(true);
    if (result.valid) {
      // Each position was proven against its own inspection, and the
      // snapshot carries exactly those per-position values.
      expect(result.publication.tools[0]?.placement.itemOrder).toBe(1);
      expect(result.publication.tools[1]?.placement.itemOrder).toBe(2);
    }
  });

  it("rejects an explicit undefined eyebrow as a supplied non-string optional (Tool and Edit)", () => {
    const toolResult = validateSurfaceInteractionPublication(
      makePublication({ tools: [makeTool("t", { eyebrow: undefined })] }),
    );
    expect(codesOf(toolResult)).toEqual(["contribution_shape_invalid"]);

    const editResult = validateSurfaceInteractionPublication(
      makePublication({ editCommands: [makeEditCommand("e", { eyebrow: undefined })] }),
    );
    expect(codesOf(editResult)).toEqual(["contribution_shape_invalid"]);
  });

  it("drops non-contract extra fields from the returned snapshot", () => {
    const tool = makeTool("t") as SurfaceInteractionToolContribution & { extra?: string };
    tool.extra = "not-in-the-contract";
    const result = validateSurfaceInteractionPublication(makePublication({ tools: [tool] }));
    expect(result.valid).toBe(true);
    if (result.valid) {
      expect(result.publication.tools[0]).not.toHaveProperty("extra");
      expect(result.publication.tools[0]?.id).toBe("t");
    }
  });

  it("carries no disabledReason key on enabled availability in the snapshot", () => {
    const result = validateSurfaceInteractionPublication(
      makePublication({ tools: [makeTool("t")] }),
    );
    expect(result.valid).toBe(true);
    if (result.valid) {
      const availability = result.publication.tools[0]?.availability;
      expect(availability).toEqual({ status: "enabled" });
      expect(Object.hasOwn(availability ?? {}, "disabledReason")).toBe(false);
    }
  });

  it("does not alias input records or arrays anywhere in the returned snapshot", () => {
    const pointer = { kind: "document", value: "doc-1" };
    const tool = makeTool("t");
    const publication = makePublication({
      agentContext: {
        label: "Ctx",
        campaignId: null,
        documentId: null,
        sessionNumber: null,
        ambientSummary: null,
        pointers: [pointer],
      },
      tools: [tool],
    });

    const result = validateSurfaceInteractionPublication(publication);

    expect(result.valid).toBe(true);
    if (result.valid) {
      expect(result.publication.identity).not.toBe(publication.identity);
      expect(result.publication.tools).not.toBe(publication.tools);
      expect(result.publication.tools[0]).not.toBe(tool);
      expect(result.publication.tools[0]?.placement).not.toBe(tool.placement);
      expect(result.publication.tools[0]?.availability).not.toBe(tool.availability);
      expect(result.publication.agentContext).not.toBe(publication.agentContext);
      expect(result.publication.agentContext?.pointers).not.toBe(
        publication.agentContext?.pointers,
      );
      expect(result.publication.agentContext?.pointers[0]).not.toBe(pointer);
    }
  });
});
