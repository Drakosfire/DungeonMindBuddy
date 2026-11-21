import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { GuestReleasePage } from "./GuestReleasePage";

const point = (id: string, label: string) => ({ id, label, kind: "character", name_citations: [], kind_citations: [], name_basis: "asserted", kind_basis: "asserted" });
const copy = (nodes = [point("a", "Shared point")], release = "copy") => ({ release_id: release, manifest: { graph: { nodes, edges: [] }, sources: [], assets: [] } });
const response = (data: unknown) => new Response(JSON.stringify(data), { status: 200 });
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); window.history.replaceState({}, "", "/"); });

it("adds a clearly temporary connected point, keeps it out of URLs and storage, then resets", async () => {
  const data = copy();
  const original = JSON.stringify(data);
  const fetchMock = vi.fn(async () => response(data));
  const storage = vi.spyOn(Storage.prototype, "setItem");
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" />);
  await screen.findByRole("button", { name: /Shared point/ });
  await user.type(screen.getByLabelText("Point name"), "<img src=x>");
  await user.selectOptions(screen.getByLabelText("Connect to a shared point"), "a");
  await user.click(screen.getByRole("button", { name: "Add temporary point" }));
  expect(screen.getByRole("heading", { name: "<img src=x>" })).toBeInTheDocument();
  expect(screen.getByText(/your temporary addition, not part of the shared World/i)).toBeInTheDocument();
  expect(screen.getByText(/Your temporary connection · not sourced/i)).toBeInTheDocument();
  expect(document.querySelector("img[src=x]")).toBeNull();
  expect(window.location.hash).toBe("#copy/copy");
  expect(window.location.href).not.toContain("guest-local");
  expect(screen.queryByRole("link", { name: "Link to this point" })).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(storage).not.toHaveBeenCalled();
  expect(JSON.stringify(data)).toBe(original);
  await user.click(screen.getByRole("button", { name: "Reset my additions" }));
  expect(screen.queryByRole("heading", { name: "<img src=x>" })).not.toBeInTheDocument();
  expect(screen.getByText("Every story has a trail.")).toBeInTheDocument();
  expect(window.location.hash).toBe("#copy/copy");
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(storage).not.toHaveBeenCalled();
});

it("keeps duplicate labels separate and avoids collisions with released identifiers", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => response(copy([point("guest-local-1", "Same"), point("other", "Same")]))));
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" />);
  expect(await screen.findAllByRole("button", { name: /Same character/ })).toHaveLength(2);
  await user.type(screen.getByLabelText("Point name"), "Same");
  await user.selectOptions(screen.getByLabelText("Connect to a shared point"), "guest-local-1");
  await user.click(screen.getByRole("button", { name: "Add temporary point" }));
  expect(screen.getAllByRole("button", { name: /Same/ })).toHaveLength(4);
  expect(screen.getByText(/Your temporary connection · not sourced/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Explore Same" })).toBeInTheDocument();
  expect(window.location.hash).toBe("#copy/copy");
});

it("clears a selected released fragment and all drafts on reset", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => response(copy())));
  window.history.replaceState({}, "", "/#copy/copy/point/a");
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" />);
  expect(await screen.findByRole("heading", { name: "Shared point" })).toBeInTheDocument();
  await user.type(screen.getByLabelText("Point name"), "unfinished");
  await user.click(screen.getByRole("button", { name: "Reset my additions" }));
  expect(screen.getByLabelText("Point name")).toHaveValue("");
  expect(screen.getByText("Every story has a trail.")).toBeInTheDocument();
  expect(window.location.hash).toBe("#copy/copy");
  act(() => window.dispatchEvent(new PopStateEvent("popstate")));
  expect(screen.getByText("Every story has a trail.")).toBeInTheDocument();
});

it("keeps additions while shared history changes but loses them on remount", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => response(copy())));
  const user = userEvent.setup();
  const view = render(<GuestReleasePage publicId="public" />);
  await screen.findByRole("button", { name: /Shared point/ });
  await user.type(screen.getByLabelText("Point name"), "My clue");
  await user.selectOptions(screen.getByLabelText("Connect to a shared point"), "a");
  await user.click(screen.getByRole("button", { name: "Add temporary point" }));
  await user.click(screen.getByRole("button", { name: "Shared point character" }));
  act(() => { window.history.pushState({}, "", "#copy/copy"); window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(screen.getByRole("button", { name: /My clue/ })).toBeInTheDocument();
  expect(window.location.href).not.toContain("guest-local");
  view.unmount();
  render(<GuestReleasePage publicId="public" />);
  await screen.findByRole("button", { name: /Shared point/ });
  expect(screen.queryByText("My clue")).not.toBeInTheDocument();
});

it("never renders old additions against a changing public copy", async () => {
  let resolveNext!: (value: Response) => void;
  const next = new Promise<Response>(resolve => { resolveNext = resolve; });
  vi.stubGlobal("fetch", vi.fn(async (url: RequestInfo | URL) => String(url).endsWith("/first") ? response(copy()) : next));
  const user = userEvent.setup();
  const view = render(<GuestReleasePage publicId="first" />);
  await screen.findByRole("button", { name: /Shared point/ });
  await user.type(screen.getByLabelText("Point name"), "Old scratch");
  await user.selectOptions(screen.getByLabelText("Connect to a shared point"), "a");
  await user.click(screen.getByRole("button", { name: "Add temporary point" }));
  view.rerender(<GuestReleasePage publicId="second" />);
  expect(screen.queryByText("Old scratch")).not.toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("Opening this guest World");
  await act(async () => { resolveNext(response(copy([point("b", "Other point")], "other-copy"))); await next; });
  expect(await screen.findByRole("button", { name: /Other point/ })).toBeInTheDocument();
  expect(screen.queryByText("Old scratch")).not.toBeInTheDocument();
});

it("explains why a copy without shared points cannot add a connected point", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => response(copy([]))));
  render(<GuestReleasePage publicId="public" />);
  expect(await screen.findByText("This copy has no shared points to connect to yet.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Add temporary point" })).not.toBeInTheDocument();
});

it("rejects control characters and enforces the ten-point limit", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => response(copy())));
  const user = userEvent.setup();
  render(<GuestReleasePage publicId="public" />);
  await screen.findByRole("button", { name: /Shared point/ });
  fireEvent.change(screen.getByLabelText("Point name"), { target: { value: "bad\u202ename" } });
  await user.selectOptions(screen.getByLabelText("Connect to a shared point"), "a");
  await user.click(screen.getByRole("button", { name: "Add temporary point" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Avoid control characters");
  for (let index = 0; index < 10; index++) {
    fireEvent.change(screen.getByLabelText("Point name"), { target: { value: `Guest ${index}` } });
    await user.selectOptions(screen.getByLabelText("Connect to a shared point"), "a");
    await user.click(screen.getByRole("button", { name: "Add temporary point" }));
  }
  expect(screen.getByRole("button", { name: "Add temporary point" })).toBeDisabled();
  expect(screen.getByText(/ten-point limit/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reset my additions" }));
  expect(screen.getByRole("button", { name: "Add temporary point" })).toBeEnabled();
});

it("bounds rapid submissions and rejects overlong text even if browser limits are bypassed", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => response(copy())));
  render(<GuestReleasePage publicId="public" />);
  await screen.findByRole("button", { name: /Shared point/ });
  const name = screen.getByLabelText("Point name"), link = screen.getByLabelText("Connection"), target = screen.getByLabelText("Connect to a shared point");
  const form = screen.getByRole("button", { name: "Add temporary point" }).closest("form")!;
  fireEvent.change(name, { target: { value: "x".repeat(81) } });
  fireEvent.change(target, { target: { value: "a" } });
  fireEvent.submit(form);
  expect(screen.getByRole("alert")).toBeInTheDocument();
  fireEvent.change(name, { target: { value: "Rapid" } });
  fireEvent.change(link, { target: { value: "x".repeat(61) } });
  fireEvent.submit(form);
  expect(screen.getByRole("alert")).toBeInTheDocument();
  fireEvent.change(link, { target: { value: "connected to" } });
  act(() => { for (let index = 0; index < 12; index++) fireEvent.submit(form); });
  expect(screen.getAllByRole("button", { name: /Rapid Your addition/ })).toHaveLength(10);
  expect(screen.getByRole("button", { name: "Add temporary point" })).toBeDisabled();
});

it("isolates additions in separate mounts", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => response(copy())));
  const user = userEvent.setup();
  const first = render(<GuestReleasePage publicId="first" />);
  const second = render(<GuestReleasePage publicId="second" />);
  const one = within(first.container), two = within(second.container);
  await one.findByRole("button", { name: /Shared point/ });
  await two.findByRole("button", { name: /Shared point/ });
  await user.type(one.getByLabelText("Point name"), "Only here");
  await user.selectOptions(one.getByLabelText("Connect to a shared point"), "a");
  await user.click(one.getByRole("button", { name: "Add temporary point" }));
  expect(one.getByRole("heading", { name: "Only here" })).toBeInTheDocument();
  expect(two.queryByText("Only here")).not.toBeInTheDocument();
});
