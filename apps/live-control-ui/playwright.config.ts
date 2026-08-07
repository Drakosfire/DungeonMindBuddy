import { defineConfig } from "@playwright/test";

/**
 * OPT-BENCH02 surface experience bench — opt-in only.
 * Default CI must not require a live stack: leave DMB_BENCH_SURFACE unset.
 */
const enabled = process.env.DMB_BENCH_SURFACE === "1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  timeout: 120_000,
  use: {
    baseURL: process.env.DMB_BENCH_BASE_URL ?? "http://127.0.0.1:5173",
    trace: "off",
    screenshot: "only-on-failure",
  },
  // When disabled, no projects run — `npx playwright test` exits without live deps.
  projects: enabled
    ? [
        {
          name: "surface-bench",
          testMatch: /world-graph-surface-experience\.spec\.ts/,
        },
      ]
    : [],
});
