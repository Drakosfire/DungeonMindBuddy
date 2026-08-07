import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

type LatencyRecord = {
  stage: string;
  t: number;
  epochMs?: number;
  durationMs?: number;
  meta?: Record<string, unknown>;
};

type BenchPayload = {
  measuredAt: string;
  baseURL: string;
  gitHead?: string;
  gitDirty?: boolean;
  gitStatusPorcelain?: string;
  contractOk: boolean;
  contractFailures: string[];
  navigation: {
    plan: { domContentLoadedMs: number | null; loadEventMs: number | null };
    build: { domContentLoadedMs: number | null; loadEventMs: number | null };
  };
  stages: LatencyRecord[];
  projectionMarks: string[];
  notes: string[];
  cleanupCandidates: string[];
};

/** Stages that must be present with successful outcomes for a merge-ready dogfood. */
const REQUIRED_CONTRACT: Array<{
  id: string;
  check: (stages: LatencyRecord[]) => string | null;
}> = [
  {
    id: "plan_projection_ready",
    check: (stages) => {
      const row = [...stages]
        .reverse()
        .find((s) => s.stage === "projection_ready" && s.meta?.surface === "plan");
      if (!row) return "missing projection_ready (plan)";
      if (row.meta?.outcome !== "ready") {
        return `plan projection_ready outcome=${String(row.meta?.outcome)} (required ready)`;
      }
      return null;
    },
  },
  {
    id: "first_chip_paint",
    check: (stages) =>
      stages.some((s) => s.stage === "first_chip_paint") ? null : "missing first_chip_paint",
  },
  {
    id: "detail_glance_open",
    check: (stages) =>
      stages.some((s) => s.stage === "detail_glance_open")
        ? null
        : "missing detail_glance_open",
  },
  {
    id: "detail_full_open",
    check: (stages) =>
      stages.some((s) => s.stage === "detail_full_open") ? null : "missing detail_full_open",
  },
  {
    id: "surface_switch_start",
    check: (stages) =>
      stages.some((s) => s.stage === "surface_switch_start")
        ? null
        : "missing surface_switch_start",
  },
  {
    id: "surface_switch_end",
    check: (stages) => {
      const row = [...stages].reverse().find((s) => s.stage === "surface_switch_end");
      if (!row) return "missing surface_switch_end";
      if (row.meta?.missingSwitchStart) {
        return "surface_switch_end missing persisted switch-start (cross-document clock broken)";
      }
      if (typeof row.durationMs !== "number" || row.durationMs < 0) {
        return "surface_switch_end lacks wall-epoch durationMs";
      }
      if (row.meta?.clock !== "wall_epoch") {
        return "surface_switch_end must use clock=wall_epoch";
      }
      return null;
    },
  },
  {
    id: "build_projection_ready",
    check: (stages) => {
      const row = [...stages]
        .reverse()
        .find((s) => s.stage === "build_projection_ready");
      if (!row) return "missing build_projection_ready";
      if (row.meta?.outcome !== "ready") {
        return `build_projection_ready outcome=${String(row.meta?.outcome)} (required ready)`;
      }
      return null;
    },
  },
  {
    id: "build_detail_open",
    check: (stages) =>
      stages.some((s) => s.stage === "build_detail_open")
        ? null
        : "missing build_detail_open",
  },
];

function evaluateContract(stages: LatencyRecord[]): string[] {
  return REQUIRED_CONTRACT.map((req) => req.check(stages)).filter(
    (msg): msg is string => msg != null,
  );
}

async function enableClientBenchInstrumentation(page: Page): Promise<void> {
  await page.addInitScript(() => {
    try {
      sessionStorage.setItem("dmb:bench-surface", "1");
    } catch {
      // ignore
    }
    (window as Window & { __DMB_BENCH_SURFACE__?: boolean }).__DMB_BENCH_SURFACE__ = true;
  });
}

async function scrapeLatency(page: Page): Promise<LatencyRecord[]> {
  return page.evaluate(() => {
    const w = window as Window & {
      __DMB_WG_SURFACE_LATENCY__?: LatencyRecord[];
      __DMB_WG_SURFACE_LATENCY_API__?: { getRecords: () => LatencyRecord[] };
    };
    const fromApi = w.__DMB_WG_SURFACE_LATENCY_API__?.getRecords?.() ?? [];
    if (fromApi.length) return fromApi;
    if (w.__DMB_WG_SURFACE_LATENCY__?.length) {
      return [...w.__DMB_WG_SURFACE_LATENCY__];
    }
    try {
      const raw = sessionStorage.getItem("dmb:wg-surface-latency-ring");
      if (raw) {
        const parsed = JSON.parse(raw) as LatencyRecord[];
        if (Array.isArray(parsed) && parsed.length) return parsed;
      }
    } catch {
      // ignore
    }
    return [];
  });
}

async function clearClientCaches(page: Page): Promise<void> {
  await page.evaluate(() => {
    const w = window as Window & {
      __DMB_WG_SURFACE_LATENCY_API__?: {
        reset: () => void;
        clearProjectionCache: () => void;
      };
    };
    w.__DMB_WG_SURFACE_LATENCY_API__?.clearProjectionCache();
    w.__DMB_WG_SURFACE_LATENCY_API__?.reset();
  });
}

async function navigationTiming(page: Page): Promise<{
  domContentLoadedMs: number | null;
  loadEventMs: number | null;
}> {
  return page.evaluate(() => {
    const nav = performance.getEntriesByType("navigation")[0] as
      | PerformanceNavigationTiming
      | undefined;
    if (!nav) return { domContentLoadedMs: null, loadEventMs: null };
    return {
      domContentLoadedMs: Math.round(nav.domContentLoadedEventEnd),
      loadEventMs: Math.round(nav.loadEventEnd),
    };
  });
}

async function projectionMarkNames(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    performance
      .getEntriesByType("mark")
      .map((entry) => entry.name)
      .filter((name) => name.startsWith("dmb:wg-projection:") || name.startsWith("dmb:wg-surface:"))
      .concat(
        performance
          .getEntriesByType("measure")
          .map((entry) => entry.name)
          .filter((name) => name.startsWith("dmb:wg-projection:") || name.startsWith("dmb:wg-surface:")),
      ),
  );
}

function deriveCleanupCandidates(payload: BenchPayload): string[] {
  const stages = new Set(payload.stages.map((s) => s.stage));
  const candidates: string[] = [];
  const switchStart = payload.stages.find((s) => s.stage === "surface_switch_start");
  if (switchStart?.meta?.navigation === "full_document_anchor") {
    candidates.push(
      "Plan↔Build uses full-document `<a href>` navigation (`navigation: full_document_anchor`); SPA routing would retain the client projection TTL cache across surfaces.",
    );
  }
  if (stages.has("client_cache_miss") && !stages.has("client_cache_hit")) {
    candidates.push(
      "Cold path observed client_cache_miss with no client_cache_hit in this run — warm client TTL and/or OPT03 server completed-cache should be re-measured on a second pass without clear.",
    );
  }
  if (stages.has("detail_glance_open") && stages.has("detail_full_open")) {
    candidates.push(
      "Chip glance → Expand path is instrumented; compare detail_glance_open vs detail_full_open wall deltas vs projection re-fetch marks to see if Expand re-resolves unnecessarily.",
    );
  }
  const switchEnd = [...payload.stages].reverse().find((s) => s.stage === "surface_switch_end");
  const buildReady = [...payload.stages].reverse().find((s) => s.stage === "build_projection_ready");
  if (
    switchEnd?.durationMs != null
    && buildReady?.durationMs != null
    && switchEnd.durationMs > buildReady.durationMs * 2
  ) {
    candidates.push(
      `Surface switch wall time (${switchEnd.durationMs}ms) dwarfs Build projection fetch (${buildReady.durationMs}ms) — admission UI / full reload dominate over projection build.`,
    );
  }
  if (payload.stages.some((s) => s.meta && "seeded" in (s.meta as object))) {
    candidates.push(
      "Bench chip host seeded a GraphNodeHoverToken because the Plan doc lacked native chips; re-measure on a chip-bearing session doc to include TipTap parse/paint cost.",
    );
  }
  if (candidates.length === 0) {
    candidates.push("Re-run a warm second pass without client cache clear to rank cache vs navigation costs.");
  }
  return candidates;
}

function writeArtifacts(payload: BenchPayload): void {
  const repoRoot = path.resolve(__dirname, "../../..");
  const reportDir = path.join(repoRoot, "report");
  const docsReport = path.join(
    repoRoot,
    "Docs/Reports/REPORT-world-graph-surface-experience-benchmark.md",
  );
  fs.mkdirSync(reportDir, { recursive: true });
  const jsonPath = path.join(reportDir, "world-graph-surface-experience-bench.json");
  fs.writeFileSync(jsonPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");

  const byStage = new Map<string, LatencyRecord[]>();
  for (const row of payload.stages) {
    const list = byStage.get(row.stage) ?? [];
    list.push(row);
    byStage.set(row.stage, list);
  }
  const summaryRows = [...byStage.entries()]
    .map(([stage, rows]) => {
      const withDur = rows.filter((r) => r.durationMs != null).map((r) => r.durationMs as number);
      const last = rows[rows.length - 1];
      const dur =
        withDur.length > 0
          ? String(Math.round(withDur.reduce((a, b) => a + b, 0) / withDur.length))
          : "—";
      return `| ${stage} | ${rows.length} | ${dur} | ${last.t.toFixed(1)} |`;
    })
    .join("\n");

  const detailRows = payload.stages
    .map((row) => {
      const dur = row.durationMs != null ? String(row.durationMs) : "—";
      const meta = row.meta ? `\`${JSON.stringify(row.meta)}\`` : "—";
      const epoch = row.epochMs != null ? row.epochMs.toFixed(1) : "—";
      return `| ${row.stage} | ${dur} | ${row.t.toFixed(1)} | ${epoch} | ${meta} |`;
    })
    .join("\n");

  const dirtyLabel = payload.gitDirty ? "dirty" : "clean";
  const contractLabel = payload.contractOk ? "PASS" : "FAIL";

  const md = `# World Graph surface experience benchmark (OPT-BENCH02)

**Measured at:** ${payload.measuredAt}  
**Base URL:** ${payload.baseURL}  
**Code SHA:** ${payload.gitHead ?? "unknown"} (${dirtyLabel})  
**Contract:** ${contractLabel}  
**Latency scope:** browser experience (navigation + \`dmb:wg-surface:*\` / \`dmb:wg-projection:*\` marks). Service-level warm-path numbers remain OPT-BENCH01.

${
  payload.contractOk
    ? ""
    : `## Contract failures

This run is **not** a valid dogfood proof. Artifacts are retained for diagnostics only.

${payload.contractFailures.map((f) => `- ${f}`).join("\n")}

`
}## Navigation timing

| Surface | DOMContentLoaded (ms) | loadEventEnd (ms) |
| --- | ---: | ---: |
| Plan (cold) | ${payload.navigation.plan.domContentLoadedMs ?? "—"} | ${payload.navigation.plan.loadEventMs ?? "—"} |
| Build (after switch) | ${payload.navigation.build.domContentLoadedMs ?? "—"} | ${payload.navigation.build.loadEventMs ?? "—"} |

## Stage summary

| Stage | count | avg durationMs | last t |
| --- | ---: | ---: | ---: |
${summaryRows || "| _(none)_ | — | — | — |"}

## Stage detail (ring buffer order)

| Stage | durationMs | t (perf.now) | epochMs | meta |
| --- | ---: | ---: | ---: | --- |
${detailRows || "| _(none)_ | — | — | — | — |"}

## Projection / surface performance marks

${payload.projectionMarks.map((name) => `- \`${name}\``).join("\n") || "_none_"}

## Notes

${payload.notes.map((n) => `- ${n}`).join("\n") || "- (none)"}

## Cleanup candidates (measurement only — do not fix in OPT-BENCH02)

${
  payload.contractOk
    ? payload.cleanupCandidates.map((c, i) => `${i + 1}. ${c}`).join("\n")
    : "_Omitted — contract failed; do not treat cleanup candidates from a partial run as ranked evidence._"
}

JSON artifact: \`report/world-graph-surface-experience-bench.json\`.
`;

  fs.writeFileSync(docsReport, md, "utf8");
  // eslint-disable-next-line no-console
  console.log(`Wrote ${jsonPath} (contract=${contractLabel})`);
  // eslint-disable-next-line no-console
  console.log(`Wrote ${docsReport}`);
}

test.describe("OPT-BENCH02 World Graph surface experience", () => {
  test("Plan cold → chip → detail → Build switch → View", async ({ page }) => {
    test.setTimeout(180_000);
    const notes: string[] = [];
    const planPath = process.env.DMB_BENCH_PLAN_PATH ?? "/plan";
    const campaignId = process.env.DMB_BENCH_CAMPAIGN_ID ?? "longmont-c2";
    const searchQuery = process.env.DMB_BENCH_SEARCH_QUERY ?? "Glowkindle";
    let planNav = { domContentLoadedMs: null as number | null, loadEventMs: null as number | null };
    let buildNav = { domContentLoadedMs: null as number | null, loadEventMs: null as number | null };
    let stages: LatencyRecord[] = [];
    let marks: string[] = [];
    let contractFailures: string[] = [];
    let planStages: LatencyRecord[] = [];

    await enableClientBenchInstrumentation(page);

    try {
      await page.goto(planPath, { waitUntil: "load" });
      await clearClientCaches(page);
      await page.reload({ waitUntil: "load" });
      planNav = await navigationTiming(page);

      await page.waitForFunction(
        () => {
          const w = window as Window & { __DMB_WG_SURFACE_LATENCY__?: { stage: string; meta?: { outcome?: string; surface?: string } }[] };
          return (w.__DMB_WG_SURFACE_LATENCY__ ?? []).some(
            (r) =>
              r.stage === "projection_ready"
              && r.meta?.surface === "plan"
              && r.meta?.outcome === "ready",
          );
        },
        null,
        { timeout: 45_000 },
      );

      // Prefer a native TipTap chip; fall back to bench-seeded chip host once projection nodes exist.
      const chip = page.getByTestId("graph-node-chip").first();
      await chip.waitFor({ state: "visible", timeout: 20_000 });
      const seeded = await page.getByTestId("surface-latency-bench-chip-host").count();
      if (seeded > 0) {
        notes.push("Used SurfaceLatencyBenchChipHost (Plan doc had no native graph chip).");
      }
      // Agent chrome can intercept bottom-of-viewport clicks; force is intentional for bench.
      await chip.click({ force: true });

      const expand = page.getByTestId("projection-expand");
      await expand.waitFor({ state: "visible", timeout: 15_000 });
      await expand.click({ force: true });

      await page
        .waitForFunction(
          () => {
            const w = window as Window & {
              __DMB_WG_SURFACE_LATENCY__?: { stage: string }[];
            };
            return (w.__DMB_WG_SURFACE_LATENCY__ ?? []).some((r) => r.stage === "detail_full_open");
          },
          null,
          { timeout: 10_000 },
        )
        .catch(() => {
          notes.push("Timed out waiting for detail_full_open after Expand.");
        });

      // Close full detail so the ProjectionHost overlay does not intercept surface nav.
      const closeProjection = page.getByTestId("projection-close");
      if (
        await closeProjection
          .waitFor({ state: "visible", timeout: 5_000 })
          .then(() => true)
          .catch(() => false)
      ) {
        await closeProjection.click({ force: true });
      } else {
        await page.keyboard.press("Escape");
      }

      // Checkpoint Plan-side marks before full-document navigation.
      planStages = await scrapeLatency(page);
      notes.push(`Plan checkpoint stages: ${planStages.map((s) => s.stage).join(",") || "(none)"}`);

      // Full-document nav to Build (intentional product path under measurement).
      await page.locator('nav.app-site-nav a[href="/build"]').click({ force: true });
      await page.waitForURL(/\/build/, { timeout: 30_000 });
      await page.waitForLoadState("domcontentloaded");
      buildNav = await navigationTiming(page);

      const campaignPick = page.getByRole("button", { name: campaignId });
      if (
        await campaignPick
          .waitFor({ state: "visible", timeout: 8_000 })
          .then(() => true)
          .catch(() => false)
      ) {
        notes.push(`Build required campaign pick (${campaignId}) after surface switch.`);
        await campaignPick.click();
      }

      await page
        .getByTestId("build-markdown-editor")
        .waitFor({ state: "visible", timeout: 30_000 });

      await page.waitForFunction(
        () => {
          const w = window as Window & {
            __DMB_WG_SURFACE_LATENCY__?: { stage: string; meta?: { outcome?: string } }[];
          };
          return (w.__DMB_WG_SURFACE_LATENCY__ ?? []).some(
            (r) => r.stage === "build_projection_ready" && r.meta?.outcome === "ready",
          );
        },
        null,
        { timeout: 45_000 },
      );

      const findExisting = page.getByRole("button", { name: /Find existing object/i }).first();
      await findExisting.waitFor({ state: "attached", timeout: 15_000 });
      // Build Edit host is overlay-collapsed by default; open it so Find existing is interactable.
      const editToggle = page.locator('[data-testid="surface-edit-host"] > button.app-edit-toolbox-toggle');
      if (
        await editToggle
          .waitFor({ state: "visible", timeout: 5_000 })
          .then(() => true)
          .catch(() => false)
      ) {
        const expanded = await editToggle.getAttribute("aria-expanded");
        if (expanded !== "true") {
          await editToggle.click({ force: true });
        }
      }
      // Tool-host buttons can sit outside the Playwright viewport; DOM click is intentional for bench.
      await findExisting.evaluate((el) => (el as HTMLButtonElement).click());

      const searchInput = page.locator("#graph-reference-search-input");
      await searchInput.waitFor({ state: "visible", timeout: 10_000 });
      if (searchQuery) {
        await searchInput.fill(searchQuery);
      }

      await page.waitForTimeout(400);
      const viewBtn = page.getByTestId("graph-reference-view").first();
      await viewBtn.waitFor({ state: "visible", timeout: 15_000 });
      await viewBtn.evaluate((el) => (el as HTMLButtonElement).click());

      await page.waitForFunction(
        () => {
          const w = window as Window & {
            __DMB_WG_SURFACE_LATENCY__?: { stage: string }[];
          };
          return (w.__DMB_WG_SURFACE_LATENCY__ ?? []).some((r) => r.stage === "build_detail_open");
        },
        null,
        { timeout: 10_000 },
      );
      stages = await scrapeLatency(page);
      // Prefer the longer ring (sessionStorage should already merge Plan+Build).
      if (stages.length < planStages.length) {
        stages = planStages;
        notes.push("Final scrape shorter than Plan checkpoint; retained Plan checkpoint ring.");
      }
      marks = await projectionMarkNames(page);
    } catch (error) {
      notes.push(
        `Script error before contract evaluation: ${
          error instanceof Error ? error.message : String(error)
        }`,
      );
      try {
        stages = await scrapeLatency(page);
        marks = await projectionMarkNames(page);
      } catch {
        // page may be closed
      }
    } finally {
      contractFailures = evaluateContract(stages);
      const payload: BenchPayload = {
        measuredAt: new Date().toISOString(),
        baseURL: process.env.DMB_BENCH_BASE_URL ?? "http://127.0.0.1:5173",
        gitHead: process.env.DMB_BENCH_GIT_HEAD,
        gitDirty: process.env.DMB_BENCH_GIT_DIRTY === "1",
        gitStatusPorcelain: process.env.DMB_BENCH_GIT_STATUS || undefined,
        contractOk: contractFailures.length === 0,
        contractFailures,
        navigation: { plan: planNav, build: buildNav },
        stages,
        projectionMarks: marks,
        notes,
        cleanupCandidates: [],
      };
      if (payload.contractOk) {
        payload.cleanupCandidates = deriveCleanupCandidates(payload);
      }
      writeArtifacts(payload);
    }

    expect(
      contractFailures,
      `OPT-BENCH02 contract failed:\n${contractFailures.map((f) => `  - ${f}`).join("\n")}`,
    ).toEqual([]);
  });
});
