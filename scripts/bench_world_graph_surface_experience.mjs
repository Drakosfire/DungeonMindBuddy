#!/usr/bin/env node
/**
 * OPT-BENCH02: run the opt-in Playwright World Graph surface experience bench.
 *
 * Prerequisites:
 *   - Live control server on :8000 (or VITE proxy target)
 *   - UI: `cd apps/live-control-ui && npm run dev` (default http://127.0.0.1:5173)
 *   - World Graph projection must succeed for the Plan/Build campaign under test
 *
 * Usage:
 *   DMB_BENCH_SURFACE=1 node scripts/bench_world_graph_surface_experience.mjs
 *
 * Optional env:
 *   DMB_BENCH_BASE_URL          default http://127.0.0.1:5173
 *   DMB_BENCH_PLAN_PATH         default /plan
 *   DMB_BENCH_BUILD_PATH        default /build
 *   DMB_BENCH_CAMPAIGN_ID       default longmont-c2
 *   DMB_BENCH_SEARCH_QUERY      default Glowkindle
 *
 * Client instrumentation is enabled at runtime via Playwright addInitScript
 * (sessionStorage + window flag). Optionally also start Vite with
 * VITE_DMB_BENCH_SURFACE=1.
 */

import { execSync, spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const uiDir = path.resolve(__dirname, "../apps/live-control-ui");
const repoRoot = path.resolve(__dirname, "..");

if (process.env.DMB_BENCH_SURFACE !== "1") {
  console.error(
    "OPT-BENCH02 is opt-in. Re-run with DMB_BENCH_SURFACE=1 (and a live UI + L3 stack).",
  );
  process.exit(2);
}

function captureGitProvenance() {
  try {
    const gitHead = execSync("git rev-parse HEAD", {
      cwd: repoRoot,
      encoding: "utf8",
    }).trim();
    const porcelain = execSync("git status --porcelain", {
      cwd: repoRoot,
      encoding: "utf8",
    }).trim();
    return {
      gitHead,
      gitDirty: porcelain.length > 0,
      gitStatusPorcelain: porcelain || "",
    };
  } catch (error) {
    console.warn("Unable to capture git provenance:", error);
    return {
      gitHead: process.env.DMB_BENCH_GIT_HEAD ?? "unknown",
      gitDirty: true,
      gitStatusPorcelain: "(git provenance capture failed)",
    };
  }
}

const provenance = captureGitProvenance();

const env = {
  ...process.env,
  DMB_BENCH_SURFACE: "1",
  DMB_BENCH_BASE_URL: process.env.DMB_BENCH_BASE_URL ?? "http://127.0.0.1:5173",
  DMB_BENCH_GIT_HEAD: provenance.gitHead,
  DMB_BENCH_GIT_DIRTY: provenance.gitDirty ? "1" : "0",
  DMB_BENCH_GIT_STATUS: provenance.gitStatusPorcelain,
};

console.log(
  `OPT-BENCH02 provenance: ${provenance.gitHead}${provenance.gitDirty ? " (dirty)" : " (clean)"}`,
);

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
