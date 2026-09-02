import { act, render, screen } from "@testing-library/react";
import { useSyncExternalStore } from "react";
import { describe, expect, it, vi } from "vitest";

import {
  createSurfaceInformationChannel,
  type SurfaceInformationChannel,
  type SurfaceInformationDescriptor,
  type SurfaceInformationObservedMetadata,
  type SurfaceInformationState,
} from "./index";

const metadata: SurfaceInformationObservedMetadata = {
  revision: { kind: "exact", value: "rev:1" },
  provenance: [{ kind: "world", id: "eldyrwild" }],
  inspectionTargets: [{ kind: "node", id: "npc:alpha" }],
  diagnostics: [],
};

function descriptor(
  overrides: Partial<SurfaceInformationDescriptor> = {},
): SurfaceInformationDescriptor {
  return {
    channelId: "ch-plan-world-graph",
    informationKind: "world_graph_projection",
    providerId: "plan_world_graph_projection",
    authority: "dungeonmind",
    subject: { kind: "world", id: "eldyrwild" },
    scope: [{ kind: "campaign", id: "longmont-c1" }],
    ...overrides,
  };
}

function ready(value: string): Exclude<SurfaceInformationState<string>, { status: "loading" }> {
  return { status: "ready", value, ...metadata };
}

describe("createSurfaceInformationChannel", () => {
  it("starts at generation 0 loading with an immutable descriptor", () => {
    const desc = descriptor();
    const channel = createSurfaceInformationChannel<string>(desc);
    const first = channel.getSnapshot();
    expect(first.generation).toBe(0);
    expect(first.state.status).toBe("loading");
    expect(channel.getSnapshot()).toBe(first);
    expect(channel.descriptor).toEqual(desc);
    expect(channel.descriptor).toBe(channel.descriptor);
    desc.channelId = "mutated";
    expect(channel.descriptor.channelId).toBe("ch-plan-world-graph");
  });

  it("rejects blank required descriptor identity", () => {
    expect(() =>
      createSurfaceInformationChannel(descriptor({ channelId: "  " })),
    ).toThrow(/channelId/);
  });

  it("keeps getSnapshot referentially stable until an accepted observation", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());
    const a = channel.getSnapshot();
    const b = channel.getSnapshot();
    expect(Object.is(a, b)).toBe(true);
  });

  it("subscribe and unsubscribe: notifications stop after unsubscribe and unsubscribe is idempotent", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());
    const listener = vi.fn();
    const unsubscribe = channel.subscribe(listener);
    const ticket = channel.beginObservation();
    expect(ticket).not.toBeNull();
    expect(listener).toHaveBeenCalledTimes(1);
    unsubscribe();
    unsubscribe();
    channel.commit(ticket!, ready("alpha"));
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("accepts READY with a new generation and snapshot object", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());
    const before = channel.getSnapshot();
    const ticket = channel.beginObservation({ publishLoading: false });
    expect(channel.getSnapshot()).toBe(before);
    expect(channel.commit(ticket!, ready("alpha"))).toBe(true);
    const after = channel.getSnapshot();
    expect(after.generation).toBe(1);
    expect(after.state.status).toBe("ready");
    if (after.state.status === "ready") {
      expect(after.state.value).toBe("alpha");
      expect(after.state.revision).toEqual({ kind: "exact", value: "rev:1" });
    }
    expect(Object.is(before, after)).toBe(false);
  });

  it("accepts EMPTY, STALE, UNAVAILABLE, and INTEGRITY_ERROR as distinct states", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());

    const emptyTicket = channel.beginObservation({ publishLoading: false });
    expect(
      channel.commit(emptyTicket!, { status: "empty", ...metadata }),
    ).toBe(true);
    expect(channel.getSnapshot().state.status).toBe("empty");
    expect("value" in channel.getSnapshot().state).toBe(false);

    const staleTicket = channel.beginObservation({ publishLoading: false });
    expect(
      channel.commit(staleTicket!, {
        status: "stale",
        value: "last",
        reason: "refreshing against a newer head",
        ...metadata,
      }),
    ).toBe(true);
    const stale = channel.getSnapshot().state;
    expect(stale.status).toBe("stale");
    if (stale.status === "stale") {
      expect(stale.value).toBe("last");
      expect(stale.reason).toContain("refreshing");
      expect(stale.revision).toEqual({ kind: "exact", value: "rev:1" });
    }

    const unavailableTicket = channel.beginObservation({ publishLoading: false });
    expect(
      channel.commit(unavailableTicket!, {
        status: "unavailable",
        reason: "authority database is unreachable",
        diagnostics: [{ code: "authority_unavailable", message: "connection refused" }],
      }),
    ).toBe(true);
    expect(channel.getSnapshot().state.status).toBe("unavailable");
    expect("value" in channel.getSnapshot().state).toBe(false);

    const integrityTicket = channel.beginObservation({ publishLoading: false });
    expect(
      channel.commit(integrityTicket!, {
        status: "integrity_error",
        reason: "genesis receipt without head",
        diagnostics: [{ code: "genesis_receipt_without_head", message: "orphan world" }],
      }),
    ).toBe(true);
    expect(channel.getSnapshot().state.status).toBe("integrity_error");
    expect("value" in channel.getSnapshot().state).toBe(false);
  });

  it("treats an equivalent semantic observation as a new generation and notifies", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());
    const listener = vi.fn();
    channel.subscribe(listener);
    const first = channel.beginObservation({ publishLoading: false });
    expect(channel.commit(first!, ready("same"))).toBe(true);
    const afterFirst = channel.getSnapshot();
    listener.mockClear();
    const second = channel.beginObservation({ publishLoading: false });
    expect(channel.commit(second!, ready("same"))).toBe(true);
    const afterSecond = channel.getSnapshot();
    expect(afterSecond.generation).toBe(afterFirst.generation + 1);
    expect(Object.is(afterFirst, afterSecond)).toBe(false);
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("rejects a late A commit after B has been accepted (out-of-order completion)", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());
    const listener = vi.fn();
    channel.subscribe(listener);
    const ticketA = channel.beginObservation({ publishLoading: false });
    const ticketB = channel.beginObservation({ publishLoading: false });
    expect(channel.commit(ticketB!, ready("bravo"))).toBe(true);
    const current = channel.getSnapshot();
    listener.mockClear();
    expect(channel.commit(ticketA!, ready("alpha"))).toBe(false);
    expect(channel.getSnapshot()).toBe(current);
    expect(channel.getSnapshot().generation).toBe(current.generation);
    if (current.state.status === "ready") {
      expect(current.state.value).toBe("bravo");
    }
    expect(listener).not.toHaveBeenCalled();
  });

  it("rejects consumed-ticket replay", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());
    const ticket = channel.beginObservation({ publishLoading: false });
    expect(channel.commit(ticket!, ready("once"))).toBe(true);
    const current = channel.getSnapshot();
    expect(channel.commit(ticket!, ready("twice"))).toBe(false);
    expect(channel.getSnapshot()).toBe(current);
  });

  it("publishLoading=false retains the visible snapshot while superseding the prior ticket", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());
    const first = channel.beginObservation({ publishLoading: false });
    channel.commit(first!, ready("kept"));
    const visible = channel.getSnapshot();
    const superseded = channel.beginObservation({ publishLoading: false });
    const refresh = channel.beginObservation({ publishLoading: false });
    expect(channel.getSnapshot()).toBe(visible);
    expect(channel.commit(superseded!, ready("old"))).toBe(false);
    expect(channel.commit(refresh!, ready("next"))).toBe(true);
    expect(channel.getSnapshot().generation).toBe(visible.generation + 1);
  });

  it("default beginObservation publishes loading as a visible generation", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());
    const listener = vi.fn();
    channel.subscribe(listener);
    const ticket = channel.beginObservation();
    const loading = channel.getSnapshot();
    expect(loading.generation).toBe(1);
    expect(loading.state.status).toBe("loading");
    expect(listener).toHaveBeenCalledTimes(1);
    expect(channel.commit(ticket!, ready("done"))).toBe(true);
    expect(channel.getSnapshot().generation).toBe(2);
  });

  it("rejects a reconstructed lookalike of the current ticket", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());
    const listener = vi.fn();
    channel.subscribe(listener);
    const ticket = channel.beginObservation({ publishLoading: false });
    expect(ticket).not.toBeNull();

    const TicketCtor = Object.getPrototypeOf(ticket).constructor as new (
      ...args: unknown[]
    ) => object;
    const reconstructed = new TicketCtor(
      ...(Object.values(ticket as object) as unknown[]),
    );
    const cloned = Object.create(
      Object.getPrototypeOf(ticket),
      Object.getOwnPropertyDescriptors(ticket as object),
    ) as typeof ticket;

    const before = channel.getSnapshot();
    listener.mockClear();
    expect(channel.commit(reconstructed as typeof ticket, ready("forged-ctor"))).toBe(
      false,
    );
    expect(channel.commit(cloned, ready("forged-clone"))).toBe(false);
    expect(channel.getSnapshot()).toBe(before);
    expect(listener).not.toHaveBeenCalled();
    expect(channel.commit(ticket!, ready("real"))).toBe(true);
    expect(channel.getSnapshot().generation).toBe(before.generation + 1);
    if (channel.getSnapshot().state.status === "ready") {
      expect(channel.getSnapshot().state.value).toBe("real");
    }
  });

  it("rejects a foreign channel ticket", () => {
    const a = createSurfaceInformationChannel<string>(descriptor({ channelId: "a" }));
    const b = createSurfaceInformationChannel<string>(descriptor({ channelId: "b" }));
    const foreign = a.beginObservation({ publishLoading: false });
    const before = b.getSnapshot();
    expect(b.commit(foreign!, ready("nope"))).toBe(false);
    expect(b.getSnapshot()).toBe(before);
  });

  it("dispose rejects in-flight work and later subscribe/begin/commit", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());
    const listener = vi.fn();
    channel.subscribe(listener);
    const ticket = channel.beginObservation({ publishLoading: false });
    const before = channel.getSnapshot();
    listener.mockClear();
    channel.dispose();
    channel.dispose();
    expect(channel.beginObservation()).toBeNull();
    expect(channel.commit(ticket!, ready("late"))).toBe(false);
    expect(channel.getSnapshot()).toBe(before);
    expect(listener).not.toHaveBeenCalled();
    const lateListener = vi.fn();
    const unsub = channel.subscribe(lateListener);
    unsub();
    expect(lateListener).not.toHaveBeenCalled();
  });
});

function GenerationView({
  channel,
}: {
  channel: SurfaceInformationChannel<string>;
}) {
  const snapshot = useSyncExternalStore(channel.subscribe, channel.getSnapshot);
  const status = snapshot.state.status;
  const value = snapshot.state.status === "ready" ? snapshot.state.value : "";
  return (
    <div>
      <span data-testid="generation">{snapshot.generation}</span>
      <span data-testid="status">{status}</span>
      <span data-testid="value">{value}</span>
    </div>
  );
}

describe("React useSyncExternalStore interoperability", () => {
  it("rerenders from the production channel without a wrapper store", () => {
    const channel = createSurfaceInformationChannel<string>(descriptor());
    render(<GenerationView channel={channel} />);
    expect(screen.getByTestId("generation").textContent).toBe("0");
    expect(screen.getByTestId("status").textContent).toBe("loading");

    const ticket = channel.beginObservation({ publishLoading: false });
    expect(screen.getByTestId("generation").textContent).toBe("0");
    act(() => {
      channel.commit(ticket!, ready("live"));
    });

    expect(screen.getByTestId("generation").textContent).toBe("1");
    expect(screen.getByTestId("status").textContent).toBe("ready");
    expect(screen.getByTestId("value").textContent).toBe("live");
  });
});
