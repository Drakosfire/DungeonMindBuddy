import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HostedAuthGate, useHostedAuthStatus } from "./HostedAuthGate";

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

  it("permits signed-out children only when the caller marks the index playground exception", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(401, { status: "signed_out" })));

    render(<HostedAuthGate enabled allowSignedOutChildren><div>Separate playground</div></HostedAuthGate>);

    expect(await screen.findByText("Separate playground")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign in with DungeonMind" })).not.toBeInTheDocument();
  });

  it("keeps unknown session status blocked even when signed-out children are permitted", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(503, { status: "unavailable" })));

    render(<HostedAuthGate enabled allowSignedOutChildren><div>Separate playground</div></HostedAuthGate>);

    expect(await screen.findByText("Sign-in status is unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Separate playground")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign in with DungeonMind" })).not.toBeInTheDocument();
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
      .mockResolvedValueOnce(response(200, { status: "authenticated", subject: "owner-a" }));
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

  it("unmounts sensitive children when an authenticated refresh becomes unavailable", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(200, { status: "authenticated", subject: "owner-a" }))
      .mockResolvedValueOnce(response(503, { status: "unavailable" }));
    vi.stubGlobal("fetch", fetchMock);

    render(<HostedAuthGate enabled><div>Authenticated screen</div></HostedAuthGate>);
    expect(await screen.findByText("Authenticated screen")).toBeInTheDocument();
    fireEvent(window, new Event("focus"));

    expect(await screen.findByRole("heading", { name: "Sign-in status is unavailable" })).toBeInTheDocument();
    expect(screen.queryByText("Authenticated screen")).not.toBeInTheDocument();
  });

  it("returns to signed-out recovery when a focused tab discovers an expired session", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(200, { status: "authenticated", subject: "owner-a" }))
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

function AccountState({ onUnmount }: { onUnmount?: () => void }) {
  const { subject } = useHostedAuthStatus();
  const [draft, setDraft] = useState("");
  useEffect(() => () => onUnmount?.(), [onUnmount]);
  return <><p>{subject}</p><input aria-label="Account draft" value={draft} onChange={event => setDraft(event.target.value)} /></>;
}

it("replaces the whole account subtree on subject change and preserves it for the same subject", async () => {
  const onUnmount = vi.fn();
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(response(200, { status: "authenticated", subject: "owner-a" }))
    .mockResolvedValueOnce(response(200, { status: "authenticated", subject: "owner-a" }))
    .mockResolvedValueOnce(response(200, { status: "authenticated", subject: "owner-b" }));
  vi.stubGlobal("fetch", fetchMock);
  render(<HostedAuthGate enabled><AccountState onUnmount={onUnmount} /></HostedAuthGate>);
  await screen.findByText("owner-a");
  fireEvent.change(screen.getByLabelText("Account draft"), { target: { value: "Private A draft" } });
  await act(async () => { fireEvent(window, new Event("focus")); });
  expect(screen.getByLabelText("Account draft")).toHaveValue("Private A draft");
  expect(onUnmount).not.toHaveBeenCalled();
  fireEvent(window, new Event("focus"));
  await screen.findByText("owner-b");
  expect(screen.getByLabelText("Account draft")).toHaveValue("");
  expect(onUnmount).toHaveBeenCalledTimes(1);
});

it.each([undefined, "", "   ", " owner-a ", 42, null])("rejects an authenticated session with invalid subject %s", async subject => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(200, { status: "authenticated", subject } as Record<string, string>)));
  render(<HostedAuthGate enabled><div>Private graph</div></HostedAuthGate>);
  await screen.findByText("Sign-in status is unavailable");
  expect(screen.queryByText("Private graph")).not.toBeInTheDocument();
});

it("ignores an older account response after a newer logout response", async () => {
  let resolveOld!: (value: Response) => void;
  const fetchMock = vi.fn()
    .mockReturnValueOnce(new Promise<Response>(resolve => { resolveOld = resolve; }))
    .mockResolvedValueOnce(response(401, { status: "signed_out" }));
  vi.stubGlobal("fetch", fetchMock);
  render(<HostedAuthGate enabled><div>Private graph</div></HostedAuthGate>);
  fireEvent(window, new Event("focus"));
  await screen.findByRole("link", { name: "Sign in with DungeonMind" });
  await act(async () => resolveOld(response(200, { status: "authenticated", subject: "old-owner" })));
  expect(screen.queryByText("Private graph")).not.toBeInTheDocument();
});
