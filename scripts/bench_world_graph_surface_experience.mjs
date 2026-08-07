#!/usr/bin/env node
/**
 * OPT-BENCH02: run the opt-in Playwright World Graph surface experience bench.
 *
 * Prerequisites:
 *   - Live control server on :8000 (or VITE proxy target)
 *   - UI: `cd apps/live-control-ui && npm run dev` (default http://127.0.0.1:5173)
 *   - Plan session with at least one graph-native chip
 *
 * Usage:
 *   DMB_BENCH_SURFACE=1 node scripts/bench_world_graph_surface_experience.mjs
 *
 * Optional env:
 *   DMB_BENCH_BASE_URL          default http://127.0.0.1:5173
 *   DMB_BENCH_PLAN_PATH         default /plan
 *   DMB_BENCH_BUILD_PATH        default /build
 *   DMB_BENCH_SEARCH_QUERY      optional Find-existing query text
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const uiDir = path.resolve(__dirname, "../apps/live-control-ui");

if (process.env.DMB_BENCH_SURFACE !== "1") {
  console.error(
    "OPT-BENCH02 is opt-in. Re-run with DMB_BENCH_SURFACE=1 (and a live UI + L3 stack).",
  );
  process.exit(2);
}

const env = {
  ...process.env,
  DMB_BENCH_SURFACE: "1",
  DMB_BENCH_BASE_URL: process.env.DMB_BENCH_BASE_URL ?? "http://127.0.0.1:5173",
};

const child = spawn(
  "npx",
  ["playwright", "test", "-c", "playwright.config.ts"],
  {
    cwd: uiDir,
    env,
    stdio: "inherit",
    shell: true,
  },
);

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
