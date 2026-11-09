import { expect, test, type Browser, type BrowserContext, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

async function finalizeWitness(context: Pick<BrowserContext, "tracing" | "close">, path: string, witnessFailure?: unknown) {
  try {
    await context.tracing.stop({ path });
  } catch (error) {
    // A persistence negative control must not consume a missing mandatory trace.
    throw new Error("trace_finalization_failed", { cause: new AggregateError([witnessFailure, error]) });
  } finally {
    await context.close();
  }
}

async function navigate(page: Page, path: string) {
  const open = page.getByRole("button", { name: "Open navigation", exact: true });
  // The prior route closes its menu in an effect. Wait for that state instead of
  // sampling isVisible between the route update and its effect.
  await open.click();
  await page.locator(`a[href="${path}"]`).first().click();
  await expect(page).toHaveURL(new RegExp(`${path === "/" ? "/" : path}$`));
  await expect(open).toBeVisible();
}

async function witness(browser: Browser, denyPersistence: boolean) {
  const base = process.env.QUALIFICATION_BASE_URL!;
  // Every witness owns a fresh browser profile; no operator cookies or state.
  const context = await browser.newContext({ baseURL: base });
  await context.addCookies([{ name: "dungeonmind_session", value: "qualification-session", url: base }]);
  const output = process.env.QUALIFICATION_OUTPUT!;
  mkdirSync(output, { recursive: true });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
  const page = await context.newPage();
  page.on("dialog", (dialog) => void dialog.accept());
  let witnessFailure: unknown;
  try {
    await page.goto("/");
    const world = `Qualification ${Date.now()} ${denyPersistence ? "fault" : "good"}`;
    await page.getByLabel("Create a World", { exact: true }).fill(world);
    await page.getByRole("button", { name: "Create World", exact: true }).click();
    const example = page.getByRole("button", { name: "Start with an example graph", exact: true });
    try { await example.waitFor({ state: "visible", timeout: 5_000 }); }
    catch { throw new Error("graph_route_dependency_missing: requires reviewed real-main #2276 integration"); }
    await example.click();
    const canvas = page.locator('section[aria-label="Local World graph canvas"]');
    await expect(canvas).toBeVisible();
    await expect(canvas).toHaveAttribute("aria-busy", "false");
    await canvas.getByRole("button", { name: "Add object", exact: true }).click();
    const label = `Retained object ${denyPersistence ? "fault" : "good"}`;
    await canvas.getByLabel("Object name", { exact: true }).fill(label);
    // Exercise real same-document route clicks while the graph draft is unsaved.
    await navigate(page, "/plan");
    await navigate(page, "/");
    // The route returns to the local World chooser; resume the same World before
    // checking its preserved draft, as a user does after leaving the Surface.
    await page.getByRole("list", { name: "Resume a local World" }).getByRole("button", { name: new RegExp(`^${world}`) }).click();
    await expect(canvas.getByLabel("Object name", { exact: true })).toHaveValue(label);
    if (denyPersistence) {
      await page.evaluate(() => {
        const original = IDBDatabase.prototype.transaction;
        (window as unknown as { deniedWrites: number }).deniedWrites = 0;
        IDBDatabase.prototype.transaction = function (...args: Parameters<IDBDatabase["transaction"]>) {
          if (args[1] === "readwrite") {
            (window as unknown as { deniedWrites: number }).deniedWrites += 1;
            throw new DOMException("Deliberate qualification storage denial", "QuotaExceededError");
          }
          return original.apply(this, args);
        };
      });
    }
    await canvas.getByRole("button", { name: "Create object", exact: true }).click();
    await expect(canvas).toHaveAttribute("aria-busy", "false");
    if (denyPersistence) {
      const denied = await page.evaluate(() => (window as unknown as { deniedWrites: number }).deniedWrites);
      expect(denied, "persistence_fault_not_exercised").toBeGreaterThan(0);
    } else {
      await expect(canvas.getByRole("button", { name: `${label}, person`, exact: true })).toBeVisible();
    }
    await page.reload();
    await page.getByRole("list", { name: "Resume a local World" }).getByRole("button", { name: new RegExp(`^${world}`) }).click();
    await expect(canvas).toBeVisible();
    await expect(canvas).toHaveAttribute("aria-busy", "false");
    const retained = canvas.getByRole("button", { name: `${label}, person`, exact: true });
    if (!(await retained.isVisible())) throw new Error("persistence_witness_failed: graph object absent after save/reopen");
    await expect(retained).toBeVisible();
  } catch (error) {
    witnessFailure = error;
    throw error;
  } finally {
    await finalizeWitness(context, join(output, denyPersistence ? "fault-trace.zip" : "good-trace.zip"), witnessFailure);
  }
}

test("real image preserves graph draft through navigation and saved object through reopen", async ({ browser }) => {
  await witness(browser, false);
});

test("same save/reopen witness detects deliberately denied persistence", async ({ browser }) => {
  // Only the persistence-boundary failure counts. Missing graph/startup/navigation
  // or an unexercised fault cannot be relabelled as a successful negative probe.
  await expect(witness(browser, true)).rejects.toThrow("persistence_witness_failed:");
});

test("missing fault trace cannot satisfy the expected persistence failure", async () => {
  let closed = false;
  const persistenceFailure = new Error("persistence_witness_failed: graph object absent after save/reopen");
  const traceFailure = new Error("trace storage unavailable");
  const context = {
    tracing: { stop: async () => { throw traceFailure; } },
    close: async () => { closed = true; },
  } as unknown as Pick<BrowserContext, "tracing" | "close">;
  const failure = await finalizeWitness(context, "unused-trace.zip", persistenceFailure).catch((error: Error) => error);
  expect(failure).toBeInstanceOf(Error);
  expect((failure as Error).message).toBe("trace_finalization_failed");
  expect((failure as Error).message).not.toContain("persistence_witness_failed:");
  expect(((failure as Error).cause as AggregateError).errors).toEqual([persistenceFailure, traceFailure]);
  expect(closed).toBe(true);
});
