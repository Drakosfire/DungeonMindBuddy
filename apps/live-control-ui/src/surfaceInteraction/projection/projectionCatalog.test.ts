import { describe, expect, it, vi } from "vitest";

import type { SurfaceInteractionPublication } from "../types";
import {
  GRAPH_REFERENCE_PROJECTION_ID,
  normalizeProjectionCatalogRegistration,
  resolveProjectionCatalog,
  type ProjectionCatalogLiveEntry,
  type ProjectionCatalogRegistration,
} from "./projectionCatalog";
import type { ActiveProjection } from "./types";

const leaseA = Symbol("lease-a");
const leaseB = Symbol("lease-b");

function makePublication(overrides: Partial<SurfaceInteractionPublication> = {}): SurfaceInteractionPublication {
  return {
    surfaceId: "plan",
    label: "Plan",
    identity: { surfaceId: "plan", instanceKey: "plan\u001fdoc" },
    canvas: null,
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [
      { id: "recap", kind: "tool", preferredSize: "wide", bindingIds: [] },
      {
        id: GRAPH_REFERENCE_PROJECTION_ID,
        kind: "content",
        preferredSize: "wide",
        bindingIds: [],
      },
    ],
    projectionBindings: [],
    ...overrides,
  };
}

function makeRegistration(
  overrides: Partial<ProjectionCatalogRegistration> = {},
): ProjectionCatalogRegistration {
  return {
    projectionId: "recap",
    surfaceId: "plan",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: ["plan-context"],
    render: () => "rendered",
    ...overrides,
  };
}

function entry(
  registration: ProjectionCatalogRegistration,
  leaseToken: symbol = leaseA,
): ProjectionCatalogLiveEntry {
  const normalized = normalizeProjectionCatalogRegistration(registration);
  if (!normalized) throw new Error("expected valid registration");
  return {
    registrationToken: Symbol("reg"),
    leaseToken,
    registration: normalized,
  };
}

const toolActive: ActiveProjection = {
  kind: "tool",
  key: "recap",
  size: "wide",
  title: "Recap",
};

describe("projectionCatalog", () => {
  it("exports the stable graph-reference content ID", () => {
    expect(GRAPH_REFERENCE_PROJECTION_ID).toBe("graph-reference");
  });

  it("snapshots requiredBindingIds so caller mutation cannot alter live requirements", () => {
    const requiredBindingIds = ["plan-context"];
    const normalized = normalizeProjectionCatalogRegistration(
      makeRegistration({ requiredBindingIds }),
    );
    expect(normalized).not.toBeNull();
    requiredBindingIds.push("extra");
    expect(normalized!.requiredBindingIds).toEqual(["plan-context"]);
  });

  it("rejects blank IDs, duplicate bindings, and invalid kind/size", () => {
    expect(normalizeProjectionCatalogRegistration(makeRegistration({ projectionId: "" }))).toBeNull();
    expect(normalizeProjectionCatalogRegistration(makeRegistration({ surfaceId: "" }))).toBeNull();
    expect(
      normalizeProjectionCatalogRegistration(
        makeRegistration({ requiredBindingIds: ["a", "a"] }),
      ),
    ).toBeNull();
    expect(
      normalizeProjectionCatalogRegistration(
        makeRegistration({ preferredSize: "huge" as "wide" }),
      ),
    ).toBeNull();
  });

  it("resolves ready only when every exact check passes and invokes render once", () => {
    const render = vi.fn(() => "ok");
    const result = resolveProjectionCatalog({
      leaseToken: leaseA,
      entries: [entry(makeRegistration({ render }))],
      publication: makePublication(),
      projectionId: "recap",
      active: toolActive,
      bindings: { "plan-context": { campaignId: "c2" } },
    });
    expect(result).toEqual({ status: "ready", body: "ok" });
    expect(render).toHaveBeenCalledTimes(1);
  });

  it("fails closed for missing lease, unregistered, duplicate, descriptor, mismatches, and bindings", () => {
    const render = vi.fn(() => "ok");
    const live = entry(makeRegistration({ render }));

    expect(
      resolveProjectionCatalog({
        leaseToken: null,
        entries: [live],
        publication: makePublication(),
        projectionId: "recap",
        active: toolActive,
        bindings: { "plan-context": {} },
      }).status,
    ).toBe("stale_lease");

    expect(
      resolveProjectionCatalog({
        leaseToken: leaseA,
        entries: [],
        publication: makePublication(),
        projectionId: "recap",
        active: toolActive,
        bindings: { "plan-context": {} },
      }).status,
    ).toBe("unregistered");

    expect(
      resolveProjectionCatalog({
        leaseToken: leaseA,
        entries: [live, entry(makeRegistration({ render }))],
        publication: makePublication(),
        projectionId: "recap",
        active: toolActive,
        bindings: { "plan-context": {} },
      }).status,
    ).toBe("duplicate_registration");

    expect(
      resolveProjectionCatalog({
        leaseToken: leaseA,
        entries: [live],
        publication: makePublication({ projections: [] }),
        projectionId: "recap",
        active: toolActive,
        bindings: { "plan-context": {} },
      }).status,
    ).toBe("descriptor_missing");

    expect(
      resolveProjectionCatalog({
        leaseToken: leaseA,
        entries: [entry(makeRegistration({ surfaceId: "ingest", render }))],
        publication: makePublication(),
        projectionId: "recap",
        active: toolActive,
        bindings: { "plan-context": {} },
      }).status,
    ).toBe("surface_mismatch");

    expect(
      resolveProjectionCatalog({
        leaseToken: leaseA,
        entries: [entry(makeRegistration({ kind: "content", render }))],
        publication: makePublication(),
        projectionId: "recap",
        active: toolActive,
        bindings: { "plan-context": {} },
      }).status,
    ).toBe("kind_mismatch");

    expect(
      resolveProjectionCatalog({
        leaseToken: leaseA,
        entries: [entry(makeRegistration({ preferredSize: "compact", render }))],
        publication: makePublication(),
        projectionId: "recap",
        active: toolActive,
        bindings: { "plan-context": {} },
      }).status,
    ).toBe("preferred_size_mismatch");

    const missing = resolveProjectionCatalog({
      leaseToken: leaseA,
      entries: [live],
      publication: makePublication(),
      projectionId: "recap",
      active: toolActive,
      bindings: { "plan-context": null },
    });
    expect(missing.status).toBe("binding_missing");
    if (missing.status === "binding_missing") {
      expect(missing.missingBindingIds).toEqual(["plan-context"]);
    }

    expect(render).not.toHaveBeenCalled();
  });

  it("ignores registrations from a different lease even when IDs match", () => {
    const render = vi.fn(() => "ok");
    const result = resolveProjectionCatalog({
      leaseToken: leaseB,
      entries: [entry(makeRegistration({ render }), leaseA)],
      publication: makePublication(),
      projectionId: "recap",
      active: toolActive,
      bindings: { "plan-context": {} },
    });
    expect(result.status).toBe("unregistered");
    expect(render).not.toHaveBeenCalled();
  });

  it("permits extra bindings and ignores them", () => {
    const result = resolveProjectionCatalog({
      leaseToken: leaseA,
      entries: [entry(makeRegistration())],
      publication: makePublication(),
      projectionId: "recap",
      active: toolActive,
      bindings: { "plan-context": {}, extra: 1 },
    });
    expect(result.status).toBe("ready");
  });

  it("does not evaluate unused enumerable binding getters while resolving ready", () => {
    const render = vi.fn(() => "ok");
    const bindings: Record<string, unknown> = { "plan-context": { campaignId: "c2" } };
    Object.defineProperty(bindings, "extra", {
      enumerable: true,
      configurable: true,
      get() {
        throw new Error("unused binding getter must not run");
      },
    });
    const result = resolveProjectionCatalog({
      leaseToken: leaseA,
      entries: [entry(makeRegistration({ render }))],
      publication: makePublication(),
      projectionId: "recap",
      active: toolActive,
      bindings,
    });
    expect(result).toEqual({ status: "ready", body: "ok" });
    expect(render).toHaveBeenCalledTimes(1);
  });

  it("fails closed for a required binding accessor that yields null without invoking render", () => {
    const render = vi.fn(() => "ok");
    const bindings: Record<string, unknown> = {};
    Object.defineProperty(bindings, "plan-context", {
      enumerable: true,
      configurable: true,
      get() {
        return null;
      },
    });
    const result = resolveProjectionCatalog({
      leaseToken: leaseA,
      entries: [entry(makeRegistration({ render }))],
      publication: makePublication(),
      projectionId: "recap",
      active: toolActive,
      bindings,
    });
    expect(result.status).toBe("binding_missing");
    expect(render).not.toHaveBeenCalled();
  });

  it("evaluates each required binding accessor once for both authorization and render", () => {
    let reads = 0;
    const payload = { campaignId: "c2" };
    const bindings: Record<string, unknown> = {};
    Object.defineProperty(bindings, "plan-context", {
      enumerable: true,
      configurable: true,
      get() {
        reads += 1;
        if (reads > 1) {
          throw new Error("required binding must not be read a second time");
        }
        return payload;
      },
    });
    const render = vi.fn((request) => {
      expect(request.bindings["plan-context"]).toBe(payload);
      return "ok";
    });
    const result = resolveProjectionCatalog({
      leaseToken: leaseA,
      entries: [entry(makeRegistration({ render }))],
      publication: makePublication(),
      projectionId: "recap",
      active: toolActive,
      bindings,
    });
    expect(result).toEqual({ status: "ready", body: "ok" });
    expect(reads).toBe(1);
    expect(render).toHaveBeenCalledTimes(1);
  });

  it("fails closed when a tool active.key does not match projectionId", () => {
    const render = vi.fn(() => "ok");
    const result = resolveProjectionCatalog({
      leaseToken: leaseA,
      entries: [entry(makeRegistration({ render }))],
      publication: makePublication(),
      projectionId: "recap",
      active: { ...toolActive, key: "statblock" },
      bindings: { "plan-context": {} },
    });
    expect(result.status).toBe("active_key_mismatch");
    expect(render).not.toHaveBeenCalled();
  });

  it("allows content active.key to differ from the fixed catalog projectionId", () => {
    const render = vi.fn(() => "content-ok");
    const result = resolveProjectionCatalog({
      leaseToken: leaseA,
      entries: [
        entry(
          makeRegistration({
            projectionId: GRAPH_REFERENCE_PROJECTION_ID,
            kind: "content",
            requiredBindingIds: [],
            render,
          }),
        ),
      ],
      publication: makePublication(),
      projectionId: GRAPH_REFERENCE_PROJECTION_ID,
      active: {
        kind: "content",
        key: "doc:session-12",
        size: "wide",
        title: "Session 12",
      },
      bindings: {},
    });
    expect(result).toEqual({ status: "ready", body: "content-ok" });
    expect(render).toHaveBeenCalledTimes(1);
  });
});
