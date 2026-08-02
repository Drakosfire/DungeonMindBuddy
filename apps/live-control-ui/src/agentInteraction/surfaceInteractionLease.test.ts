import { describe, expect, it, vi } from "vitest";

import { FIXTURE_DOC_ID } from "../planSurface/config/planSessionDescriptor";
import { validateSurfaceInteractionPublication } from "../surfaceInteraction/publication";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
import {
  adaptProjectionSurfaceToNeutralBase,
  buildAppChromeCompatibilityFragment,
} from "./surfaceInteractionCompat";
import { validateProjectionSurfacePublication } from "./projectionSurfacePublication";
import {
  bindSurfaceInteractionLease,
  createLeaseCallbackGate,
  createSurfaceInteractionLeaseToken,
  registerChromeCompatibilityFragment,
  unregisterChromeCompatibilityFragment,
  updateSurfaceInteractionLease,
  wrapPublicationCallbacks,
} from "./surfaceInteractionLease";

function makePublication(overrides: Partial<SurfaceInteractionPublication> = {}): SurfaceInteractionPublication {
  return {
    surfaceId: "plan",
    label: "Plan",
    identity: buildSurfaceInteractionIdentity({ surfaceId: "plan", instanceParts: ["plan", "doc-1"] }),
    canvas: null,
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
    ...overrides,
  };
}

function makeGate(getSnapshot: () => ReturnType<typeof bindSurfaceInteractionLease> | null) {
  return createLeaseCallbackGate(() => getSnapshot());
}

describe("surfaceInteractionLease", () => {
  it("bind allocates a fresh token for valid, invalid, and null inputs", () => {
    const gate = makeGate(() => null);
    const valid = bindSurfaceInteractionLease(makePublication(), "legacy_projection", gate);
    const invalid = bindSurfaceInteractionLease({ surfaceId: "" }, "legacy_projection", gate);
    const empty = bindSurfaceInteractionLease(null, "legacy_projection", gate);
    expect(valid.token).not.toBe(invalid.token);
    expect(valid.token).not.toBe(empty.token);
    expect(valid.effectivePublication).not.toBeNull();
    expect(invalid.effectivePublication).toBeNull();
    expect(empty.effectivePublication).toBeNull();
  });

  it("bind always creates a fresh token even for the same identity", () => {
    const gate = makeGate(() => null);
    const publication = makePublication();
    const first = bindSurfaceInteractionLease(publication, "legacy_projection", gate);
    const second = bindSurfaceInteractionLease(publication, "legacy_projection", gate);
    expect(first.token).not.toBe(second.token);
  });

  it("update preserves token on same-identity valid update and rejects stale token", () => {
    let current = bindSurfaceInteractionLease(makePublication({ label: "Plan A" }), "legacy_projection", makeGate(() => current));
    const staleToken = createSurfaceInteractionLeaseToken();
    const updated = updateSurfaceInteractionLease(current, current.token, makePublication({ label: "Plan B" }), makeGate(() => current));
    expect(updated?.token).toBe(current.token);
    expect(updated?.effectivePublication?.label).toBe("Plan B");
    expect(updateSurfaceInteractionLease(current, staleToken, makePublication(), makeGate(() => current))).toBeNull();
    current = updated!;
  });

  it("invalid same-identity update preserves token and bound identity but clears effective publication", () => {
    let current = bindSurfaceInteractionLease(makePublication(), "legacy_projection", makeGate(() => current));
    const identity = current.boundIdentity;
    const updated = updateSurfaceInteractionLease(current, current.token, { surfaceId: "" }, makeGate(() => current));
    expect(updated?.token).toBe(current.token);
    expect(updated?.boundIdentity).toEqual(identity);
    expect(updated?.effectivePublication).toBeNull();
    current = updated!;
    const recovered = updateSurfaceInteractionLease(current, current.token, makePublication(), makeGate(() => current));
    expect(recovered?.token).toBe(current.token);
    expect(recovered?.effectivePublication).not.toBeNull();
  });

  it("different-identity update fails closed under current lease", () => {
    let current = bindSurfaceInteractionLease(makePublication(), "legacy_projection", makeGate(() => current));
    const other = makePublication({
      identity: buildSurfaceInteractionIdentity({ surfaceId: "build", instanceParts: ["build"] }),
      surfaceId: "build",
    });
    const updated = updateSurfaceInteractionLease(current, current.token, other, makeGate(() => current));
    expect(updated?.effectivePublication).toBeNull();
    expect(updated?.boundIdentity?.surfaceId).toBe("plan");
  });

  it("native lease ignores Chrome fragment register and cleanup", () => {
    let current = bindSurfaceInteractionLease(makePublication(), "native", makeGate(() => current));
    const fragmentToken = Symbol("fragment");
    const fragment = {
      tools: [{
        id: "page-action",
        label: "Action",
        placement: { groupId: "legacy-page-tools", groupLabel: "Page tools", groupOrder: 100, itemOrder: 0 },
        availability: { status: "enabled" as const },
        activation: { kind: "command" as const, invoke: () => {} },
      }],
      editCommands: [],
    };
    const registered = registerChromeCompatibilityFragment(
      current,
      current.token,
      fragmentToken,
      fragment,
      makeGate(() => current),
    );
    expect(registered?.chromeFragment).toBeNull();
    current = registered!;
    const unregistered = unregisterChromeCompatibilityFragment(
      current,
      current.token,
      fragmentToken,
      makeGate(() => current),
    );
    expect(unregistered).toEqual(current);
  });

  it("compatibility lease composes Chrome tools and invalidates duplicate IDs", () => {
    let current = bindSurfaceInteractionLease(makePublication({
      tools: [{
        id: "dup",
        label: "Base",
        placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
        availability: { status: "enabled" },
        activation: { kind: "command", invoke: () => {} },
      }],
    }), "legacy_route", makeGate(() => current));
    const invoke = vi.fn();
    const fragmentToken = Symbol("fragment");
    current = registerChromeCompatibilityFragment(
      current,
      current.token,
      fragmentToken,
      {
        tools: [{
          id: "dup",
          label: "Chrome",
          placement: { groupId: "legacy-page-tools", groupLabel: "Page tools", groupOrder: 100, itemOrder: 0 },
          availability: { status: "enabled" },
          activation: { kind: "command", invoke },
        }],
        editCommands: [],
      },
      makeGate(() => current),
    )!;
    expect(current.effectivePublication).toBeNull();
    expect(current.validationIssues.some((issue) => issue.code === "duplicate_tool_id")).toBe(true);
  });

  it("lease-guarded callbacks reject stale token, removed, and replaced callbacks", () => {
    const original = vi.fn();
    const replacement = vi.fn();
    let current = bindSurfaceInteractionLease(makePublication({
      tools: [{
        id: "action",
        label: "Action",
        placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
        availability: { status: "enabled" },
        activation: { kind: "command", invoke: original },
      }],
    }), "legacy_route", makeGate(() => current));
    const staleWrapped = current.effectivePublication!.tools[0]!.activation;
    expect(staleWrapped.kind).toBe("command");
    if (staleWrapped.kind !== "command") throw new Error("expected command activation");
    staleWrapped.invoke();
    expect(original).toHaveBeenCalledTimes(1);

    current = bindSurfaceInteractionLease(makePublication(), "legacy_route", makeGate(() => current));
    staleWrapped.invoke();
    expect(original).toHaveBeenCalledTimes(1);

    current = bindSurfaceInteractionLease(makePublication({
      tools: [{
        id: "action",
        label: "Action",
        placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
        availability: { status: "enabled" },
        activation: { kind: "command", invoke: original },
      }],
    }), "legacy_route", makeGate(() => current));
    const removedWrapped = current.effectivePublication!.tools[0]!.activation;
    current = updateSurfaceInteractionLease(current, current.token, makePublication(), makeGate(() => current))!;
    if (removedWrapped.kind !== "command") throw new Error("expected command activation");
    removedWrapped.invoke();
    expect(original).toHaveBeenCalledTimes(1);

    current = bindSurfaceInteractionLease(makePublication({
      tools: [{
        id: "action",
        label: "Action",
        placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
        availability: { status: "enabled" },
        activation: { kind: "command", invoke: replacement },
      }],
    }), "legacy_route", makeGate(() => current));
    const replacedWrapped = current.effectivePublication!.tools[0]!.activation;
    if (replacedWrapped.kind !== "command") throw new Error("expected command activation");
    replacedWrapped.invoke();
    expect(original).toHaveBeenCalledTimes(1);
    expect(replacement).toHaveBeenCalledTimes(1);
  });

  it("composes legacy projection base tools with Chrome page tools", () => {
    const planPublication = {
      identity: { surfaceId: "plan", instanceKey: "plan\u001fchrome-fragment" },
      config: {
        id: "plan",
        label: "Plan",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Plan",
        },
        tools: [{ id: "recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: {},
      },
    };
    const validated = validateProjectionSurfacePublication(planPublication);
    const neutralBase = adaptProjectionSurfaceToNeutralBase(validated);
    let current = bindSurfaceInteractionLease(neutralBase, "legacy_projection", makeGate(() => current));
    const fragment = buildAppChromeCompatibilityFragment({
      pageActions: [{ id: "page-tool", label: "Page tool", onClick: () => {} }],
      editorTools: null,
      basePublication: current.rawBasePublication,
    });
    current = registerChromeCompatibilityFragment(
      current,
      current.token,
      Symbol("fragment"),
      fragment,
      makeGate(() => current),
    )!;
    expect(current.effectivePublication?.tools.map((entry) => entry.id)).toEqual(["recap", "page-tool"]);
  });

  it("wrapPublicationCallbacks validates through SIH-01", () => {
    const gate = makeGate(() => null);
    const wrapped = wrapPublicationCallbacks(makePublication(), createSurfaceInteractionLeaseToken(), gate);
    expect(validateSurfaceInteractionPublication(wrapped).valid).toBe(true);
  });

  it("rejects wrapped callback invoke when invalid chrome fragment nullifies effective publication", () => {
    const original = vi.fn();
    let current = bindSurfaceInteractionLease(makePublication({
      tools: [{
        id: "action",
        label: "Action",
        placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
        availability: { status: "enabled" },
        activation: { kind: "command", invoke: original },
      }],
    }), "legacy_route", makeGate(() => current));
    const wrapped = current.effectivePublication!.tools[0]!.activation;
    expect(wrapped.kind).toBe("command");
    if (wrapped.kind !== "command") throw new Error("expected command activation");
    wrapped.invoke();
    expect(original).toHaveBeenCalledTimes(1);

    current = registerChromeCompatibilityFragment(
      current,
      current.token,
      Symbol("fragment"),
      {
        tools: [],
        editCommands: [{
          id: "bold",
          label: "Bold",
          placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
          availability: { status: "enabled" },
          target: { kind: "", id: "" },
          invoke: () => {},
        }],
      },
      makeGate(() => current),
    )!;
    expect(current.effectivePublication).toBeNull();
    expect(current.rawEffectivePublication).not.toBeNull();

    wrapped.invoke();
    expect(original).toHaveBeenCalledTimes(1);
  });
});
