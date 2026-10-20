import { fireEvent, render, screen } from "@testing-library/react";
import { useState, type ComponentType } from "react";
import { describe, expect, it, vi } from "vitest";
import { deferredComponent } from "./deferredComponent";

function Counter({ label }: { label: string }) {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(value => value + 1)}>{label} {count}</button>;
}

describe("deferred renderer ownership", () => {
  it("loads only when mounted, preserves props and child state through parent rerenders", async () => {
    const load = vi.fn(async () => ({ default: Counter }));
    const Deferred = deferredComponent(load, "tool");
    expect(load).not.toHaveBeenCalled();
    const view = render(<Deferred label="first" />);
    fireEvent.click(await screen.findByRole("button", { name: "first 0" }));
    view.rerender(<Deferred label="updated" />);
    expect(screen.getByRole("button", { name: "updated 1" })).toBeInTheDocument();
    expect(load).toHaveBeenCalledTimes(1);
  });

  it("keeps surrounding draft owners mounted while code is pending", async () => {
    let resolve!: (value: { default: ComponentType<{ label: string }> }) => void;
    const Deferred = deferredComponent(() => new Promise(done => { resolve = done; }), "Plan");
    function Host() {
      const [draft, setDraft] = useState("");
      return <><input aria-label="Draft" value={draft} onChange={event => setDraft(event.target.value)} /><Deferred label="ready" /></>;
    }
    render(<Host />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading Plan…");
    fireEvent.change(screen.getByLabelText("Draft"), { target: { value: "Retained" } });
    resolve({ default: Counter });
    await screen.findByRole("button", { name: "ready 0" });
    expect(screen.getByLabelText("Draft")).toHaveValue("Retained");
  });

  it("retries a failed child load without replacing its surrounding owner", async () => {
    const errorLog = vi.spyOn(console, "error").mockImplementation(() => undefined);
    try {
      const load = vi.fn<() => Promise<{ default: typeof Counter }>>()
        .mockRejectedValueOnce(new Error("Unavailable chunk"))
        .mockResolvedValueOnce({ default: Counter });
      const Deferred = deferredComponent(load, "Play");
      function Host() {
        const [draft, setDraft] = useState("");
        return <><input aria-label="Draft" value={draft} onChange={event => setDraft(event.target.value)} /><Deferred label="recovered" /></>;
      }
      render(<Host />);
      const retry = await screen.findByRole("button", { name: "Retry Play" });
      fireEvent.change(screen.getByLabelText("Draft"), { target: { value: "Keep pending work" } });
      fireEvent.click(retry);
      await screen.findByRole("button", { name: "recovered 0" });
      expect(screen.getByLabelText("Draft")).toHaveValue("Keep pending work");
      expect(load).toHaveBeenCalledTimes(2);
    } finally { errorLog.mockRestore(); }
  });
});
