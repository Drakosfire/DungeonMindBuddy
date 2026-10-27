import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HostedAuthGate } from "./HostedAuthGate";

function response(status: number, payload: Record<string, string>): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/");
});

describe("HostedAuthGate", () => {
  it("keeps the intended Buddy route in the sign-in link when signed out", async () => {
    window.history.replaceState({}, "", "/play/run-7?panel=history#turn-3");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(401, { status: "signed_out" })));

    render(
      <HostedAuthGate enabled>
        <div>Protected Buddy screen</div>
      </HostedAuthGate>,
    );

    const link = await screen.findByRole("link", { name: "Sign in with DungeonMind" });
    expect(link.getAttribute("href")).toBe(
      "/api/auth/login?return_to=%2Fplay%2Frun-7%3Fpanel%3Dhistory%23turn-3",
    );
    expect(screen.queryByText("Protected Buddy screen")).not.toBeInTheDocument();
  });

  it("distinguishes a cancelled sign-in from a service outage", async () => {
    window.history.replaceState({}, "", "/play?auth_error=cancelled");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(401, { status: "signed_out" })));

    render(<HostedAuthGate enabled><div>Protected</div></HostedAuthGate>);

    expect(await screen.findByText(/Sign-in was cancelled/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in with DungeonMind" }).getAttribute("href"))
      .toBe("/api/auth/login?return_to=%2Fplay");
  });

  it("offers retry while DMS session status is unavailable", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(503, { status: "unavailable" }))
      .mockResolvedValueOnce(response(200, { status: "authenticated" }));
    vi.stubGlobal("fetch", fetchMock);

    render(<HostedAuthGate enabled><div>Protected Buddy screen</div></HostedAuthGate>);

    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Protected Buddy screen")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("preserves the local operator experience", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(200, { status: "local_operator" })));

    render(<HostedAuthGate enabled><div>Local operator screen</div></HostedAuthGate>);

    expect(await screen.findByText("Local operator screen")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign in with DungeonMind" })).not.toBeInTheDocument();
  });

  it("shows the app after prior authentication if status refresh is temporarily unavailable", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(200, { status: "authenticated" }))
      .mockResolvedValueOnce(response(503, { status: "unavailable" }));
    vi.stubGlobal("fetch", fetchMock);

    render(<HostedAuthGate enabled><div>Authenticated screen</div></HostedAuthGate>);
    expect(await screen.findByText("Authenticated screen")).toBeInTheDocument();
    fireEvent(window, new Event("focus"));

    expect(await screen.findByRole("status")).toHaveTextContent(/could not refresh your session status/i);
    expect(screen.getByText("Authenticated screen")).toBeInTheDocument();
  });

  it("returns to signed-out recovery when a focused tab discovers an expired session", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(200, { status: "authenticated" }))
      .mockResolvedValueOnce(response(401, { status: "signed_out" }));
    vi.stubGlobal("fetch", fetchMock);

    render(<HostedAuthGate enabled><div>Authenticated screen</div></HostedAuthGate>);
    expect(await screen.findByText("Authenticated screen")).toBeInTheDocument();
    fireEvent(window, new Event("focus"));

    await waitFor(() => expect(screen.getByRole("link", { name: "Sign in with DungeonMind" })).toBeInTheDocument());
    expect(screen.queryByText("Authenticated screen")).not.toBeInTheDocument();
  });

  it("does not call the session endpoint in local development", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<HostedAuthGate enabled={false}><div>Local screen</div></HostedAuthGate>);

    expect(screen.getByText("Local screen")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
